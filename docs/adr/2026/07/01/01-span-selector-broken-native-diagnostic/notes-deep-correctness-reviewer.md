# Deep correctness review — span-selector-broken-native-diagnostic

Reviewed: f71a765..0fddc5a (`TODO.md`, `fltk/fegen/pyrt/span.py`, `fltk/fegen/pyrt/span_protocol.py`, `tests/test_span_protocol.py`)

No findings.

Verification performed:

- **Lockstep completeness.** Grepped all `fltk._native` references: the only two import-probe
  `try/except` sites are the two changed ones. Remaining references (`fltk/fegen/fltk_cst.py:63`,
  `fltk/unparse/toy_cst.py:45`) use `sys.modules.get("fltk._native")` — a different mechanism that
  cannot swallow a broken-extension exception — so no third site diverges.
- **Catch width.** `ModuleNotFoundError` ⊂ `ImportError`, so the legitimate absent-native fallback
  (genuinely missing module, `None` in `sys.modules`, or a shim package lacking `Span`) still falls
  back silently; empirically confirmed `None`-entry probe raises `ModuleNotFoundError`.
- **Test technique.** Empirically confirmed on this interpreter that with a `_BrokenNative` object
  (attribute access raises `OSError`) installed at `sys.modules["fltk._native"]`,
  `from fltk._native import Span` propagates the `OSError` uncaught by `except ImportError` — the
  import machinery swallows only `AttributeError`. So the new tests exercise exactly the
  present-but-broken path and would fail against the base `except Exception`.
- **Reload-state hygiene.** All three new tests restore the saved original `fltk._native` module
  object (`sys.modules.update(saved)`) before the restorative reload in `finally`, matching the
  existing `TestBackendSelectorSilentFallback` pattern and avoiding the PyO3 double-init panic. A
  failed `importlib.reload` leaves the module in `sys.modules` with prior bindings (span.py fails
  at its first statement; span_protocol.py rebinds `SpanProtocol` before failing), and the
  finally-block reload restores a fully consistent state either way. Identity assertions elsewhere
  (`_span_selector.Span is _fltk_native.Span`) hold post-restore because the same native module
  object is reinstalled.
- **Runtime check.** `uv run pytest tests/test_span_protocol.py`: 49 passed.
