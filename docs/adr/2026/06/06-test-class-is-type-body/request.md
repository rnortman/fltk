# Request: test-class-is-type-body

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** test cleanup (remove dead-weight assertion); trivial.

**Background.** `tests/test_fegen_rust_cst.py` — `TestAllClassesImportable.test_class_is_type` (assertion at line 71, `TODO(test-class-is-type-body)` comment at 67-70) asserts `isinstance(cls, type)` over 14 generated classes. That predicate passes for *any* class object, including a wrong/misimported alias, so it adds zero signal beyond "the import statement ran." AC-7 (importability) is already enforced by the module-level imports at lines 12-27 (a failed import fails the whole module). Construction (`cls()`) is already covered for all 14 classes by AC-8a `TestConstructionDefaultSpan.test_default_span_is_unknown` (lines 80-84) and many other AC-8 tests.

**Fix shape (chosen).** Remove the redundant `test_class_is_type` method (and its `ALL_CLASSES`/`ALL_CLASS_IDS` usage only if it becomes unused — it does not; AC-8 tests reuse them, so leave those intact). Net: delete the method and its `TODO` comment. Do NOT replace it with a `cls()` check — that is already covered by AC-8a; adding it back would just re-duplicate.

**Load-bearing constraints.**
- AC-7's real guarantee (import success) must remain enforced — it already is, by the top-of-file imports. Confirm those imports stay.
- `ALL_CLASSES` / `ALL_CLASS_IDS` are shared with AC-8 tests; do not remove them.
- No other test depends on `test_class_is_type`.

**Non-goals.** No broadening of coverage; no new tests. This is pure removal of a no-signal test.

**Verification.** `uv run pytest tests/test_fegen_rust_cst.py` passes with the method gone; the file still imports all 14 classes at module scope; `TODO.md` entry and the `TODO(test-class-is-type-body)` comment removed.

**Exploration:** `exploration.md` in this dir.
