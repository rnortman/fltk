# Design: Narrow the backend-selector catch (`span-selector-broken-native-diagnostic`)

Requirements: `request.md` (this directory). Exploration: `exploration.md` (this directory).
Base commit: c03a801. (Exploration was written at 8fd5ecf; the only relevant drift is
`TODO.md` renumbering — all cited code in `span.py`, `span_protocol.py`, and
`tests/test_span_protocol.py` is byte-identical between the two commits.)

## Root cause / context

Two sites probe for the Rust native extension and fall back to pure-Python with a bare
`except Exception:`:

1. `fltk/fegen/pyrt/span.py:13-19` — the backend selector re-exporting
   `SourceText`/`Span`/`UnknownSpan` from `fltk._native`, falling back to
   `fltk.fegen.pyrt.terminalsrc`.
2. `fltk/fegen/pyrt/span_protocol.py:119-124` — the `AnySpan` union, falling back to
   `AnySpan = _pymod.Span`.

`except Exception` catches far more than the one legitimate fallback condition (native
extension absent → `ImportError`/`ModuleNotFoundError`). A *present but broken* extension —
corrupted `.so`, C-level init crash, ABI mismatch surfacing as `OSError`/`SystemError` — is
silently swallowed, and a downstream install that thinks it is running the Rust backend
degrades to pure-Python with zero diagnostic. The TODO comment at `span.py:8-12` and
the `TODO.md` entry (header at `TODO.md:35`) record this; the requirements select option (a): narrow the catch at both
sites in lockstep. No logging is added — the absent-native fallback stays silent by design
(pinned by `tests/test_span_protocol.py::TestBackendSelectorSilentFallback`).

In-tree, only `tests/test_span_protocol.py` imports the selector module or `AnySpan`
(exploration §"Who imports"), but the selector is downstream-facing public API, so the
change is evaluated from the out-of-tree consumer's perspective: a broken native install
should fail loudly at import time, not silently lose the backend the consumer built.

## Proposed approach

### `fltk/fegen/pyrt/span.py`

- Change `except Exception:` → `except ImportError:`.
- Delete the `TODO(span-selector-broken-native-diagnostic)` comment block (lines 8-12).
- Update the fallback comment to state the new contract: `ImportError` means the native
  backend is simply absent (pure-Python install) and the fallback is intentionally silent;
  any other exception from importing `fltk._native` means a present-but-broken extension
  and propagates.

### `fltk/fegen/pyrt/span_protocol.py`

- Change `except Exception:` → `except ImportError:` on the `AnySpan` block (line 123),
  keeping the two sites in lockstep as the TODO requires. Add a one-line comment mirroring
  the span.py contract (absent → silent fallback; broken → propagate).
- The existing `# type: ignore[assignment,misc]` on the fallback assignment is unaffected.

### `TODO.md`

- Remove the `span-selector-broken-native-diagnostic` entry (header at `TODO.md:35`;
  locate by slug, not line number, in case of further drift). After this
  change no `TODO(span-selector-broken-native-diagnostic)` marker remains anywhere
  (exploration confirms `span.py:8` holds the only code comment).

No public symbol is renamed and no type-annotation surface changes; the only behavioral
change is that a broken native extension now raises at import time instead of silently
falling back. That is the deliberate, called-out point of the change.

### Considered and rejected: narrowing further to `ModuleNotFoundError`

Some ABI breaks surface as plain `ImportError` (e.g. `undefined symbol` from the dynamic
loader) and would still fall back silently under `except ImportError`. Narrowing to
`ModuleNotFoundError` would catch those loudly too (verified: both a genuinely absent
module and the test technique of `sys.modules["fltk._native"] = None` raise
`ModuleNotFoundError` on this interpreter, so the legitimate fallback would survive the
stricter catch). But the requirements explicitly accept the ImportError-shaped-break
limitation ("some ABI breaks surface as ImportError anyway") and prescribe
`except ImportError`; going stricter is a separate decision, not this change. Stick with
`ImportError`.

## Edge cases / failure modes

- **Pure-Python install (native genuinely absent):** `from fltk._native import ...` raises
  `ModuleNotFoundError`, a subclass of `ImportError` — still caught, still silent. No
  behavior change for the supported fallback path.
- **Broken extension raising non-ImportError (`OSError`, `SystemError`,
  `AttributeError`, …):** now propagates from module import. This converts silent
  degradation into a loud failure at the point of damage — the intended outcome.
- **Broken extension raising `ImportError`** (loader-level `undefined symbol`, or a broken
  Python-level import inside `fltk/_native`'s init): still falls back silently. Accepted
  limitation per requirements; see "Considered and rejected" above.
- **Site divergence:** if only one site were narrowed, a broken extension could raise from
  `span.py` while `span_protocol.py` silently built a Python-only `AnySpan` (or vice
  versa, import-order dependent). Both sites change in the same commit, and the test plan
  covers both.
- **`KeyboardInterrupt`/`SystemExit`:** already propagated under `except Exception`;
  unchanged.
- **Test-induced reload state:** the new tests reload `span.py`/`span_protocol.py` with a
  fake broken `fltk._native` in `sys.modules`. When `importlib.reload` raises, the module
  stays in `sys.modules` with its prior bindings; each test restores `sys.modules` and
  re-reloads the real module in a `finally` block, following the existing pattern in
  `TestBackendSelectorSilentFallback` (restoring the saved original `fltk._native` object,
  never re-importing it fresh — see the test plan's PyO3 double-init constraint). Names
  imported at the test module's top level
  (e.g. `AnySpan`) keep pointing at the pre-reload objects, which remain functionally
  equivalent after restore — same as today.

## Test plan

All in `tests/test_span_protocol.py`, alongside `TestBackendSelectorSilentFallback`.

Shared fixture/helper: a fake "broken native" object installed at
`sys.modules["fltk._native"]` whose attribute access raises
`OSError("simulated broken native extension")`. The `from ... import` machinery only
swallows `AttributeError`, so the `OSError` propagates out of
`from fltk._native import ...` (verified on this interpreter), faithfully simulating a
present-but-broken extension.
Each test saves/restores `sys.modules` and re-reloads the touched module in `finally`.
The cleanup **must restore the saved original `fltk._native` module object** into
`sys.modules` before the restorative reload — never delete-and-reimport (e.g.
`sys.modules.pop("fltk._native", None)` followed by a reload that re-imports it fresh).
The native extension cannot be initialized twice in one process: a second genuine import
panics (`pyo3_runtime.PanicException: UNKNOWN_SPAN already set; module initialized twice`,
`src/lib.rs:21`), and `PanicException` derives from `BaseException`, so it escapes
`except Exception` handling and poisons the rest of the pytest process. The existing
`TestBackendSelectorSilentFallback` cleanup (`tests/test_span_protocol.py:36-39`) is safe
precisely because it `sys.modules.update(saved)`s the captured real module object back
before its restorative reload — follow that exactly.

New tests (fail before the fix — the bare `except Exception` swallows the `OSError` — and
pass after):

1. `span.py`, broken-native path: with the fake installed,
   `importlib.reload(fltk.fegen.pyrt.span)` raises `OSError` (asserted with
   `pytest.raises(OSError)`). Under the old code it silently fell back to `PySpan`.
2. `span_protocol.py`, broken-native path: same fake, `importlib.reload(span_protocol)`
   raises `OSError`. Keeps the lockstep site honest.
3. `span_protocol.py`, absent-native path: with `sys.modules["fltk._native"] = None`
   (raises `ModuleNotFoundError`, an `ImportError` subclass), reload succeeds silently (no warning, via
   `warnings.simplefilter("error")`) and the reloaded module's `AnySpan` is
   `terminalsrc.Span`. This is the `AnySpan` analog of the existing
   `test_reload_without_native_emits_no_warning`, which stays as-is and continues to pin
   the silent `ImportError` fallback in `span.py`.

Existing tests (`TestBackendSelector*`, `TestAnySpanPython`, silent-fallback test) must
keep passing unmodified.

## Open questions

None. The requirements pre-decided the narrow-vs-log choice (narrow, no logging) and the
catch width (`ImportError`).
