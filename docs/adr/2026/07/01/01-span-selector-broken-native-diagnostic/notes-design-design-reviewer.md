# Design review findings: span-selector-broken-native-diagnostic

Verification performed against HEAD c03a801 (the task's base commit). Summary of checks
that PASSED before the findings:

- Both cited sites exist exactly as quoted: `fltk/fegen/pyrt/span.py:13-19`
  (`except Exception:` at line 15) and `fltk/fegen/pyrt/span_protocol.py:119-124`
  (`except Exception:` at line 123). A repo-wide grep confirms these are the only two
  `fltk._native` probe sites with a fallback — no third site missed.
- Requirements coverage is complete: narrow to `except ImportError` at both sites in
  lockstep, test for the non-ImportError path, TODO comment + TODO.md entry removal, no
  logging added, no public symbols renamed. The "Considered and rejected:
  ModuleNotFoundError" section correctly honors the request's explicit acceptance of the
  ImportError-shaped-break limitation.
- Load-bearing runtime claims verified empirically on this interpreter (Python 3.10):
  - A fake `sys.modules["fltk._native"]` object whose attribute access raises `OSError`
    makes `from fltk._native import ...` propagate `OSError` (the import machinery
    swallows only `AttributeError`). Design's test-fixture technique is sound.
  - `sys.modules["fltk._native"] = None` yields `ModuleNotFoundError` (an `ImportError`
    subclass), so the existing silent-fallback test and new test 3 keep passing after
    the narrowing.
  - Under current code (`except Exception`), the fake-broken reload of `span.py` is
    silently swallowed (falls back to `terminalsrc.Span`), so tests 1-2 genuinely fail
    before the fix and pass after — the TDD ordering claim holds.
  - When `importlib.reload` raises, the module stays in `sys.modules` with prior
    bindings, as the design's edge-case section states.
- Existing test `TestBackendSelectorSilentFallback.test_reload_without_native_emits_no_warning`
  (`tests/test_span_protocol.py:22-39`) matches the design's description and is
  correctly left unmodified.

## design-1: Stale base commit and TODO.md line number

- **Section:** header ("Base commit: 8fd5ecf") and "### TODO.md" ("Remove the
  `span-selector-broken-native-diagnostic` entry (line 77 onward)").
- **What's wrong:** The design (and exploration) are pinned to 8fd5ecf, but HEAD — and
  the task's stated base — is c03a801 ("TODO burndown: Delete bad/stale TODOs"), which
  removed 50 lines from `TODO.md`. The entry now lives at `TODO.md:35`, not line 77.
- **Why:** `git diff --stat 8fd5ecf..c03a801` touches only `TODO.md` and
  `fltk/fegen/pyrt/terminalsrc.py` (4 deleted lines, unrelated to these sites);
  `grep -n "span-selector-broken-native-diagnostic" TODO.md` at HEAD returns line 35.
  All other cited code (`span.py`, `span_protocol.py`, `tests/test_span_protocol.py`)
  is byte-identical between the two commits, so nothing else in the design is
  invalidated.
- **Consequence:** Low. An implementer navigating by "line 77 onward" lands in the
  wrong place in `TODO.md`; since the slug is given, the realistic worst case is minor
  confusion, not a wrong deletion. The design should cite the entry by slug/header only
  or update to line 35 / base c03a801.
- **Suggested fix:** Update the base-commit line to c03a801 and drop or correct the
  hard-coded TODO.md line number.

## design-2: Test-cleanup constraint missing — `fltk._native` panics on genuine re-import

- **Section:** "Test plan" ("Each test saves/restores `sys.modules` and re-reloads the
  touched module in `finally`") and "Edge cases / failure modes" ("Test-induced reload
  state").
- **What's wrong:** The design says to follow the existing save/restore pattern but does
  not state *why the exact pattern is load-bearing*: the cleanup must restore the
  **original saved `fltk._native` module object** into `sys.modules` before the final
  restorative reload. If a test instead pops the fake and lets the subsequent reload
  trigger a fresh, genuine import of `fltk._native`, the native extension re-initializes
  and panics.
- **Why:** Verified empirically at HEAD: after removing `fltk._native` from
  `sys.modules` (rather than restoring the saved object) and reloading
  `fltk.fegen.pyrt.span`, the process gets
  `pyo3_runtime.PanicException: UNKNOWN_SPAN already set; module initialized twice`
  (panic at `src/lib.rs:21`). `PanicException` derives from `BaseException`, so it
  escapes ordinary `except Exception` handling. The existing test at
  `tests/test_span_protocol.py:27,36-39` is safe only because it captures the real
  module object in `saved` and `sys.modules.update(saved)`s it back before the
  restorative reload.
- **Consequence:** An implementer who deviates slightly from the pattern (e.g. cleanup
  via `sys.modules.pop("fltk._native", None)` followed by reload, on the reasonable
  belief that "reimporting fresh" is equivalent) gets a hard `PanicException` crash in
  the test's `finally`, which can mask the actual test outcome and leave the module
  state poisoned for every later test in the same pytest process. The three new tests
  all manipulate `sys.modules["fltk._native"]`, so the exposure is per-test.
- **Suggested fix:** Add one sentence to the test plan: cleanup must restore the saved
  original `fltk._native` module object (never delete-and-reimport), because the native
  extension cannot be initialized twice in one process (PyO3 panic, `BaseException`).

No other findings. The design is internally consistent, scope-disciplined (the extra
absent-native `AnySpan` test is a justified lockstep pin, not scope creep), and every
other substantive claim checked out against source.
