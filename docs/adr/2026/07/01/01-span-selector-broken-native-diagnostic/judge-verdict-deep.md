# Judge verdict — deep review

Phase: deep. Base f71a765ec6300c23e5aa69a64df95b980e1dfbc9..HEAD 16e15fe04a1c5307030a38781a3f2f582d17b1c0. Round 1.
Notes: 7 reviewer files. Five (error-handling, correctness, security, test, efficiency) returned no findings; two (reuse, quality) each raised one finding, which are the same defect and were dispositioned together.

## Added TODOs walk

No findings were dispositioned TODO. No new `TODO(slug)` comments appear in the diff; the diff *removes* the `span-selector-broken-native-diagnostic` entry from `TODO.md` and its code-comment marker in `span.py`, matching the design's instruction and the TODO-system contract (slug fully retired, verified no remaining `TODO(span-selector-broken-native-diagnostic)` in the diff or notes).

## Other findings walk

### reuse-1 / quality-1 — Fixed
Claim (both reviewers, same defect): the four-line sys.modules save/replace/restore-and-reload dance was copy-pasted four times in `tests/test_span_protocol.py`, and the copies carry a load-bearing, non-obvious safety invariant (restore the saved original `fltk._native` module object before the restorative reload; never delete-and-reimport, because a second genuine PyO3 init panics with a `BaseException`-derived `PanicException` that poisons the pytest session). Consequence: the next copy-paster "simplifies" the cleanup and detonates the whole session far from the offending test; any future fix to the pattern must land in four places.

Evidence, diff at HEAD (commit 16e15fe, "test(span-selector): extract _native_replaced context manager for backend-reload tests"):
- `tests/test_span_protocol.py:22-46`: new `_native_replaced(fake, module_to_reload)` context manager. Its docstring states the PyO3 double-init invariant explicitly ("must NEVER be re-imported fresh in-process... `PanicException`... escapes `except Exception` and poisons the rest of the pytest session"), exactly what quality-1 asked to move from the design doc into the code, once.
- All four backend-reload tests now route through it: the pre-existing `test_reload_without_native_emits_no_warning` (rewritten onto the helper), `test_span_selector_broken_native_propagates`, `test_span_protocol_broken_native_propagates`, `test_span_protocol_absent_native_falls_back_silently`. No hand-copied `finally` blocks remain in the diff.
- The roundabout one-key dict-comprehension is replaced by `sys.modules.get`, per quality-1's suggested shape. Semantics preserved: saved-present → reassign saved object then reload; saved-absent → pop then reload. (Edge note: an original entry that is literally `None` would be treated as absent, but that state only ever exists *inside* the helper's own block; not a real divergence.)
- Context-manager ordering in the broken-native tests is correct: `with _native_replaced(...), pytest.raises(OSError):` — `pytest.raises` exits (catches) first, then the helper's `finally` restores and reloads.
- Behavior-preserving: assertions and exercised paths unchanged from the reviewed commit 0fddc5a; `uv run pytest tests/test_span_protocol.py` at HEAD: 49 passed (run by me, not just claimed).

Assessment: fix fully addresses both reviewers' finding, including the "invariant lives in the code, once" requirement. Accept.

### Reviewer notes with no findings
Error-handling, correctness, security, test, and efficiency reviewers each returned "No findings" with substantive verification bases (correctness empirically confirmed the `_BrokenNative` technique and lockstep completeness via grep; test reviewer confirmed the new tests fail against the pre-fix code, i.e. non-vacuous). The error-handling reviewer's "noted, not a finding" item (ImportError-shaped broken extension still falls back silently) is explicitly identified and accepted in design.md ("Considered and rejected: narrowing further to `ModuleNotFoundError`") — correctly not raised as a finding; nothing to disposition.

## Disputed items

None.

## Approved

1 finding (reuse-1/quality-1, deduplicated across two reviewers): 1 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable. The single finding was fixed in a dedicated commit, verified against the diff and by running the test file at HEAD.
