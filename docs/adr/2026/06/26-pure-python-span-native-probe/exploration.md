# Native Warning Removal — Exploration

## Warning emission sites

**One site only:** `fltk/fegen/pyrt/span.py:8-18`

```python
import warnings

from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan

try:
    from fltk._native import SourceText, Span, UnknownSpan  # type: ignore[assignment]
except Exception:
    warnings.warn(
        "fltk._native could not be loaded; falling back to pure-Python Span backend.",
        stacklevel=1,
    )
```

Emitted via `warnings.warn` (no category specified → defaults to `UserWarning`). Fires every time
`fltk.fegen.pyrt.span` is imported when `fltk._native` is not loadable.

No other file calls `warnings.warn` anywhere in `fltk/`.

## Where the warning lives

Hand-written library code (`fltk/fegen/pyrt/span.py`). Not in a code-generator template, not in
a generated file.

## What `fltk._native` is

`fltk._native` is a Rust/PyO3 compiled extension module, built by maturin. Its compiled binary is
`fltk/_native.abi3.so`. It exposes `Span`, `SourceText`, `UnknownSpan`, and `LineColPos` — a faster
alternative to the pure-Python equivalents in `fltk/fegen/pyrt/terminalsrc.py`.

`fltk/fegen/pyrt/span.py` is the "backend selector": it re-exports whichever `Span`/`SourceText`/
`UnknownSpan` is active. If the Rust extension is available, the Rust objects win; otherwise the
pure-Python objects from `terminalsrc` are used.

The stub package at `fltk/_native/__init__.pyi` (no `__init__.py` — intentional, to avoid shadowing
the `.so`) provides type annotations for pyright.

## How the warning is triggered by a generated parser

`fltk/iir/context.py:120-122`: the `Span` and `SourceText` types are registered in the type
registry with `module=pyreg.Module(("fltk", "fegen", "pyrt", "span"))`.

```python
pyreg.TypeInfo(
    typ=terminal_span_type,
    module=pyreg.Module(("fltk", "fegen", "pyrt", "span")),
    name="Span",
)
```

The code generator therefore emits `import fltk.fegen.pyrt.span` as a **runtime import** at the
top of every generated parser file (not under `TYPE_CHECKING`).

Evidence — `fltk/fegen/fltk_parser.py:7`:
```python
import fltk.fegen.pyrt.span
```

Same pattern in every other committed generated parser:
- `fltk/fegen/bootstrap_parser.py`
- `fltk/fegen/bootstrap_trivia_parser.py`
- `fltk/fegen/regex_parser.py`
- `fltk/fegen/regex_trivia_parser.py`
- `fltk/unparse/toy_parser.py`
- `fltk/unparse/toy_trivia_parser.py`
- `fltk/unparse/unparsefmt_parser.py`
- `fltk/unparse/unparsefmt_trivia_parser.py`

When any of these parsers is imported, Python executes `import fltk.fegen.pyrt.span`, which runs
the `try/except` block and emits the warning.

## Generated CST files do NOT trigger the warning

`fltk/fegen/gsm2tree.py:190-201` shows that generated CST node files (e.g. `bootstrap_cst.py`,
`fltk_cst.py`) guard `import fltk._native` and `import fltk.fegen.pyrt.span` under
`if typing.TYPE_CHECKING`. These imports are invisible at runtime, so CST node files never
trigger the warning.

## Parallel: `span_protocol.py` silently falls back without warning

`fltk/fegen/pyrt/span_protocol.py:89-94`:
```python
try:
    from fltk._native import Span as _RustSpan
    AnySpan = _pymod.Span | _RustSpan
except Exception:
    AnySpan = _pymod.Span  # type: ignore[assignment,misc]
```

No warning emitted here — silent fallback is already the pattern elsewhere in the same `pyrt/`
package.

## When `fltk._native` is required

A "pure-Python" generated parser is one whose parser file imports `fltk.fegen.pyrt.span.Span`
and `fltk.fegen.pyrt.span.SourceText`. These resolve to the pure-Python backend if `_native`
is absent. `terminalsrc.Span` satisfies
`SpanProtocol` and all generated node classes accept it (the `span` field annotation
`terminalsrc.Span | fltk._native.Span` covers both).

`fltk._native` is **required** when the **Rust-backend parser** (`fegen_rust_cst`)
is in use — that is, when the CST nodes are produced by the compiled Rust extension rather than the
Python parser. In that scenario the spans in the returned nodes are `fltk._native.Span` instances.

When `_native` is absent, a pure-Python generated parser uses the pure-Python `Span`
implementation.

## Effect of removing the warning

The warning does not gate any logic.
The fallback path after the `except` block is identical whether or not the `warnings.warn` call
executes. Removing the call leaves the fallback intact.

The `import warnings` statement and the `warnings.warn(...)` call are at
`fltk/fegen/pyrt/span.py:8-18`. Removing both leaves the `try/except` block structure and its
fallback untouched.

## Tests asserting on the warning

None. A search for `pytest.warns`, `recwarn`, `filterwarnings`, `"could not be loaded"`, and
`"falling back"` across all `tests/` and `fltk/` Python files found no assertions on this
specific warning text or on `UserWarning` from this module.

`tests/test_native.py` tests that `fltk._native` is importable (would fail/skip if the compiled
extension is absent), but does not assert on the warning.
