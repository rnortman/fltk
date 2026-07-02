# Quality review notes — span-selector-broken-native-diagnostic

Reviewed: `git diff f71a765..0fddc5a` (HEAD 0fddc5a, "span-selector: narrow broken-native catch to ImportError").

## quality-1

- **ID:** quality-1
- **Location:** `tests/test_span_protocol.py:59-99` (the three new tests in `TestBackendSelectorBrokenNative`), pattern originating at `tests/test_span_protocol.py:28-40` (`TestBackendSelectorSilentFallback`).
- **Issue:** Copy-paste with slight variation. The save/replace/restore-and-reload dance is now duplicated four times, byte-for-byte except for the fake installed and the module reloaded:

  ```python
  saved = {name: mod for name, mod in sys.modules.items() if name == "fltk._native"}
  try:
      sys.modules["fltk._native"] = <fake>
      ...
  finally:
      sys.modules.pop("fltk._native", None)
      sys.modules.update(saved)
      importlib.reload(<module>)
  ```

  This is not ordinary boilerplate: the cleanup carries a load-bearing, non-obvious safety invariant that the design itself calls out at length (design.md "Test plan") — the restore **must** put the saved original `fltk._native` module object back before the restorative reload, never delete-and-reimport, because a second genuine PyO3 init panics with a `BaseException`-derived `PanicException` that poisons the rest of the pytest process. That invariant currently lives only in the design doc and in the shape of four hand-copied `finally` blocks; nothing in the test file states it or enforces it.
- **Consequence:** The next person who adds a selector/backend test (this file clearly accretes them — a third fallback-shaped test was added in this very diff) will copy one of the four blocks and may "simplify" the cleanup to `pop` + fresh import, which passes locally in a pure-Python env and detonates the whole test session in a native build, with a `PanicException` far from the offending test. Four copies also means any future fix to the pattern (e.g. a second native module name to save) must be applied in four places. Classic propagating-workaround shape: the hazard is real, the guard against it is duplicated and undocumented in the code.
- **Fix:** Extract one context manager in `tests/test_span_protocol.py`, e.g.:

  ```python
  @contextlib.contextmanager
  def _native_replaced(fake: object, module_to_reload: types.ModuleType):
      # PyO3 native ext must NEVER be re-imported fresh in-process (second init
      # panics with a BaseException-derived PanicException); always restore the
      # saved original module object before the restorative reload.
      saved = sys.modules.get("fltk._native")
      try:
          sys.modules["fltk._native"] = fake
          yield
      finally:
          if saved is not None:
              sys.modules["fltk._native"] = saved
          else:
              sys.modules.pop("fltk._native", None)
          importlib.reload(module_to_reload)
  ```

  and rewrite all four tests (including the pre-existing `test_reload_without_native_emits_no_warning`) on top of it, with the PyO3 double-init rationale as the helper's comment so the invariant lives in the code, once. This also retires the roundabout one-key dict-comprehension (`{name: mod for ... if name == "fltk._native"}`) in favor of a plain `sys.modules.get`.

## Non-findings (checked, deliberately not flagged)

- Comment hygiene: the new comments in `span.py:11-16` and `span_protocol.py:124-126` state the current contract (ImportError = absent = silent; anything else propagates), not history, and reference no design/ADR docs. Verbose-ish but load-bearing; fine.
- Lockstep comment duplication between the two selector sites is intentional and small; unifying the two probe sites into a shared helper module would change the public import surface for marginal gain — not worth it.
- `_BrokenNative` relying on the import machinery swallowing only `AttributeError` is implementation-detail-adjacent but verified, documented in its docstring, and the cheapest faithful simulation available.
- TODO.md entry removal matches the TODO-system contract: the only `TODO(span-selector-broken-native-diagnostic)` marker was the `span.py` comment block, and it is gone.
