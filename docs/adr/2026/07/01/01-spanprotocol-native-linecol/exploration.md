# Exploration: `TODO(spanprotocol-native-linecol)`

Adversarial verification of the TODO text in `TODO.md` (section `spanprotocol-native-linecol`) and
the code comment at `fltk/fegen/pyrt/span_protocol.py:87-95`. Facts only, no prescriptions.

## 1. All locations of the TODO

- `TODO.md:70-75` — the master-list entry (description + the added "Constraint when closing this"
  paragraph).
- `fltk/fegen/pyrt/span_protocol.py:87` — the code comment, directly above `def line_col(self) ->
  "LineColPos | None":` (line 97) inside the `SpanProtocol` class body. The comment also encodes the
  constraint text inline (lines 91-95).
- No other `TODO(spanprotocol-native-linecol)` code comments exist anywhere in the tree (checked via
  repo-wide grep). All other hits are prose references in `docs/adr/2026/06/26-pure-python-span-native-probe/*.md`
  (design-delta doc, judge verdicts, dispositions, reviewer notes) and in
  `fltk/fegen/pyrt/test_span_protocol_assignability.py:15` (docstring reference, not a TODO comment
  itself).

## 2. Are the two `LineColPos` types actually distinct? Confirmed yes.

- Python: `fltk/fegen/pyrt/terminalsrc.py:238-242` — `@dataclass(frozen=True, eq=True, slots=True)
  class LineColPos: line: int; col: int; line_span: Span` (the `Span` here is `terminalsrc.Span`,
  same module).
- Native: `fltk/_native/__init__.pyi:14-28` — `class LineColPos` (a PyO3-compiled class), with
  `line`, `col`, `line_span` as properties. `line_span` here is typed as the *native* `Span` (same
  `.pyi` file, line 41-78), not `terminalsrc.Span`.
- Rust source backing the native class: `crates/fltk-cst-core/src/span.rs` defines `LineColPos`
  (PyO3 `#[pyclass]`), re-exported through `src/span.rs:2` (`pub use fltk_cst_core::{LineColPos,
  SourceText, Span};`) and registered in `src/lib.rs:16` (`m.add_class::<LineColPos>()?;`) — i.e. it
  is a genuinely separate compiled type, not an alias or subclass of the Python dataclass.
- The two classes are structurally similar (same three field names) but not identical: `line_span`'s
  type differs per backend (`terminalsrc.Span` vs. native `Span`), and there is no shared base class,
  `Protocol`, or type alias unifying them anywhere in the tree (grep for `LineColPos` across
  `*.py`/`*.pyi` turns up only the two independent definitions plus their construction/usage sites).

## 3. Is the static non-conformance real? Confirmed yes, reproduced with pyright directly.

Probe (assigns a concrete native `Span` value into a `SpanProtocol`-typed slot, the same shape as
the existing `_span_slot: SpanProtocol = PySpan(0, 1)` pin in
`fltk/fegen/pyrt/test_span_protocol_assignability.py:32`, but with the native backend):

```python
from fltk.fegen.pyrt.span_protocol import SpanProtocol
import fltk._native as _native
_slot: SpanProtocol = _native.Span(0, 1)
```

`uv run pyright` on this file reports:

```
error: Type "Span" is not assignable to declared type "SpanProtocol"
  "Span" is incompatible with protocol "SpanProtocol"
    "line_col" is an incompatible type
      Type "() -> (fltk._native.LineColPos | None)" is not assignable to type "() -> (fltk.fegen.pyrt.terminalsrc.LineColPos | None)"
        Function return type "LineColPos | None" is incompatible with type "LineColPos | None"
          Type "fltk._native.LineColPos | None" is not assignable to type "fltk.fegen.pyrt.terminalsrc.LineColPos | None"
  ... (reportAssignmentType)
```

The only incompatible member pyright names is `line_col` (return-type covariance failure on the
nominal `LineColPos` mismatch), consistent with the TODO's diagnosis. `merge`/`intersect` (typed
`Self` per D3.1) and `line_col_or_raise` are not flagged as separate incompatibilities in this run —
pyright appears to stop enumerating after the first failing member (the diagnostic ends in `...`
truncation) rather than reporting all incompatible members, so this run does not prove
`line_col_or_raise` alone is clean, only that `line_col` alone is already sufficient to break
assignability.

## 4. Is the "only place a span value is statically assigned into a SpanProtocol slot" claim accurate?

- `pyproject.toml:49-53` — `[tool.pyright]` config: `include = ["fltk", "*.py"]`. This is a
  non-recursive glob for `*.py` (root-level files only) plus the recursive `fltk` directory. `tests/`
  is neither `fltk` nor a root-level `*.py` file.
- Verified empirically: added an undefined-name line to `tests/test_span_protocol.py`, ran `uv run
  pyright` (no path arg, i.e. the same invocation `make check` uses at `Makefile:89`: `uv run
  --group lint --group test pyright`) — zero diagnostics referencing the file, confirming `tests/` is
  outside pyright's scan (then reverted the file; `git diff --stat tests/test_span_protocol.py`
  shows no change).
- Repo-wide grep for files under `fltk/` that reference both `_native` and `SpanProtocol` finds only
  dynamic/runtime lookups: every generated CST module (`fltk/fegen/fltk_cst.py`,
  `bootstrap_cst.py`, `regex_cst.py`, `fltk/unparse/toy_cst.py`, `unparsefmt_cst.py`) defines a
  `_get_native_span_type()` helper that does `sys.modules.get("fltk._native")` (e.g.
  `fltk/fegen/fltk_cst.py:62-63`) and uses the result for `isinstance` checks — this is untyped
  (`ModuleType | None`) at the pyright level, not a static assignment of a concrete
  `fltk._native.Span`-typed value into a `SpanProtocol` slot. No other in-scope (`fltk/`) file
  performs such a static assignment.
- `fltk/fegen/pyrt/test_span_protocol_assignability.py` is the one file (in-scope, under `fltk/`)
  that does the static assignment, and it does so only for the Python backend (`_span_slot:
  SpanProtocol = PySpan(0, 1)` at line 32); the native case is deliberately *not* assigned there,
  per its own docstring (lines 14-16: "Native `fltk._native.Span` is deliberately NOT assigned into a
  `SpanProtocol` slot here: it is not *statically* conformant... and conforms only at runtime").
- Net: the TODO's and design-delta's claim (`docs/adr/2026/06/26-pure-python-span-native-probe/design-delta-python-rust-isolation.md:349-357`,
  D5 item 2) that pyright's in-scope surface has exactly one static-assignment site, and it's the
  Python-backend one, holds up under grep + empirical scope-boundary check.

## 5. Is the stub-stability constraint accurate?

- `SpanProtocol`'s class body (`fltk/fegen/pyrt/span_protocol.py:17-125`) names no `fltk._native`
  symbol anywhere — confirmed by reading the full class definition. The only `fltk._native`
  reference in the module is below the class, in the `AnySpan` union block
  (`span_protocol.py:118-123`: `try: from fltk._native import Span as _RustSpan; AnySpan = ... except
  Exception: AnySpan = _pymod.Span`), which is structurally separate from `SpanProtocol` itself.
- The generated-pipeline "names no native" tests are parametrized over fixed file lists, neither of
  which includes `span_protocol.py`:
  - `ALL_PROTOCOL_MODULES` (`fltk/fegen/test_cst_protocol.py:567-573`): `bootstrap_cst_protocol.py`,
    `fltk_cst_protocol.py`, `regex_cst_protocol.py`, `toy_cst_protocol.py`,
    `unparsefmt_cst_protocol.py`.
  - `ALL_CONCRETE_CST_MODULES` (`fltk/fegen/test_cst_protocol.py:575-581`): `bootstrap_cst.py`,
    `fltk_cst.py`, `regex_cst.py`, `toy_cst.py`, `unparsefmt_cst.py`.
  - `fltk/fegen/test_genparser.py:227-229` and `tests/test_gsm2tree_rs.py:1203-1204` similarly assert
    `"fltk._native" not in <generated source/stub text>` for generated parser/CST-stub output, not
    for `span_protocol.py`.
  - `fltk/unparse/test_is_span_guard.py` checks that the generated *unparser* source names neither
    `fltk._native` nor the `span` selector (line 108 docstring), again about generated output, not
    `span_protocol.py`.
- So the constraint's claim — that none of these four test files would catch a regression where
  `span_protocol.py`'s own definition of `SpanProtocol` became native-referencing — is accurate:
  they scan generated-file text/paths that structurally cannot include `span_protocol.py` (it is a
  hand-written runtime-support module under `fltk/fegen/pyrt/`, not one of the generated `*_cst.py`
  / `*_cst_protocol.py` / parser artifacts in those lists).
- Design-delta grounding for why this matters: `docs/adr/2026/06/26-pure-python-span-native-probe/design-delta-python-rust-isolation.md:337-340`
  (D5 item 1) states pyright stability on the generated pipeline holds "because `SpanProtocol`
  resolves through `span_protocol.py`'s `SpanProtocol` class, which depends only on `terminalsrc`" —
  i.e. the stability argument is transitive through `span_protocol.py`'s current native-free
  definition, so a change that adds a native dependency there would propagate to every generated
  consumer without any existing test noticing.

## 6. What would unification "look like" — shape constraints found in code (no design decision made)

No implementation or design for the unification exists anywhere in the tree (grep for `LineColPos`
across `*.py`/`*.pyi`/`*.rs` shows only the two independent definitions and their direct
construction/usage sites; no protocol, alias, or wrapper attempting to bridge them).

Facts relevant to shape, gathered from the current definitions:

- The native `LineColPos` (`crates/fltk-cst-core/src/span.rs`, exposed via `fltk/_native/__init__.pyi:14-28`)
  is a compiled PyO3 class registered in the extension module (`src/lib.rs:16`). It cannot be made
  the same Python object identity as `terminalsrc.LineColPos` (a pure-Python `@dataclass`) without
  either backend depending on the other at import time — `terminalsrc.py` currently has no import of
  `fltk._native` anywhere (grep confirms), and introducing one would break the documented
  pure-Python/native isolation this delta series (`docs/adr/2026/06/26-pure-python-span-native-probe/`)
  established.
- Both classes currently expose the identical field triple (`line: int`, `col: int`, `line_span:
  <backend's own Span type>`), so the mismatch is confined to `line_span`'s nominal type, which
  mirrors the exact same "distinct nominal `Span` per backend, unified only via `SpanProtocol`"
  pattern this delta series already applied to spans themselves — that pattern (an agnostic
  structural `Protocol` in `span_protocol.py`, with `line_span` retyped from a concrete `Span` to
  `SpanProtocol` on both backends) is one shape consistent with "keep `span_protocol.py` free of
  `fltk._native` names": it would add a `LineColPosProtocol`-style structural type to
  `span_protocol.py` without importing anything from `fltk._native`, exactly as `SpanProtocol` itself
  does today for spans. This is an observation about the existing pattern already used for `Span`,
  not a recommendation — no such type currently exists, and whether it, a `TYPE_CHECKING`-only
  native import, or some other shape is chosen is an open design decision.
- Whatever shape is chosen, the return annotations that would change are exactly the two the TODO
  names: `SpanProtocol.line_col` / `line_col_or_raise` (`span_protocol.py:97,105`), plus (to keep
  both backends' concrete methods assignable to the new SpanProtocol member types)
  `terminalsrc.Span.line_col` / `line_col_or_raise` (`terminalsrc.py:113,160`) and the native `.pyi`
  declarations (`fltk/_native/__init__.pyi:67-68`). No generated file (`*_cst.py`,
  `*_cst_protocol.py`, parser, or unparser output) references `LineColPos` anywhere (confirmed by
  grep — the only non-test hits are in `span_protocol.py` and `terminalsrc.py`), so the generated
  public-API annotation surface is not directly touched by this change; only the two hand-written
  `SpanProtocol`/`terminalsrc` definitions and the native `.pyi` stub are.

## 7. Downstream/public-API surface implicated (per CLAUDE.md's out-of-tree-consumer framing)

- `SpanProtocol` itself (`fltk/fegen/pyrt/span_protocol.py`) is the public, backend-agnostic type
  downstream code is told to annotate with (per its own docstring, lines 18-23: "Backend-agnostic
  code should annotate with `SpanProtocol` rather than a concrete `Span` type"). Its `line_col`/
  `line_col_or_raise` signatures are therefore public API surface a downstream consumer's own
  type annotations could reference (e.g. `def f(span: SpanProtocol) -> ...: reveal_type(span.line_col())`).
  Changing what `line_col()` is declared to return changes what such downstream annotations resolve
  to.
- `terminalsrc.LineColPos` (`fltk/fegen/pyrt/terminalsrc.py:239`) and `fltk._native.LineColPos`
  (`fltk/_native/__init__.pyi:14`) are each independently public — both are importable, documented
  classes returned by their respective backends' `Span.line_col()`. Any consumer that pattern-matches
  or type-narrows on a concrete `LineColPos` class (rather than going through `SpanProtocol`) is
  pinned to whichever backend's class it imports.
- No generated CST/protocol/parser/unparser module (the classes CLAUDE.md calls out as public API:
  node classes, accessor methods, label enums) names `LineColPos` at all — confirmed by grep across
  `fltk/fegen/*_cst.py`, `*_cst_protocol.py`, `fltk/unparse/*_cst.py`, `*_cst_protocol.py`. So the
  generated-artifact annotation surface (the primary CLAUDE.md concern — forcing downstream
  consumers to edit generated-derived call sites) is not implicated by this TODO; the surface at risk
  is limited to the two hand-written runtime-support definitions plus the native `.pyi` stub.
