## Test review — batch 3 (generator backbone)

Commit reviewed: e6a682cb883db43d6df2cc7215cb982121934254

---

### test-1 — JOIN_BEGIN / JOIN_END rule-level anchor path is untested, including the explicit error branch

**File:** `tests/test_rust_unparser_generator.py` — no test exercises this path.

`_gen_rule_entry` handles three operation types for RULE_START: GROUP_BEGIN, NEST_BEGIN, and JOIN_BEGIN. `test_rule_start_and_end_anchors_emit_push_pop` covers GROUP_BEGIN and NEST_BEGIN. JOIN_BEGIN and its paired JOIN_END (in the pop chain) are never exercised.

More importantly, the JOIN_BEGIN branch contains an explicit `RuntimeError` guard:

```python
elif op.operation_type == OperationType.JOIN_BEGIN:
    if op.separator is None:
        msg = "JOIN_BEGIN operation missing required separator"
        raise RuntimeError(msg)
    separator_expr = self._doc_to_rust_expr(op.separator)
    lines.append(f"        let acc = acc.push_join({separator_expr});")
```

Neither the happy path (`push_join(...)` emission) nor the error path (separator is None) is tested. A regression removing the None check or corrupting the emitted call would go undetected.

**Consequence:** The only explicit error raise in the new code for this increment is invisible to tests. JOIN_END in the pop chain (`.pop_join()`) is similarly untested.

**Fix:** Add two tests. First, a test analogous to `test_rule_start_and_end_anchors_emit_push_pop` that sets a JOIN_BEGIN anchor with a Text separator and a paired JOIN_END anchor, then verifies `acc.push_join(Doc::text(...))` and `.pop_join()` appear in the output. Second, a test constructing a `FormatOperation(OperationType.JOIN_BEGIN)` with `separator=None` and verifying `RuntimeError` is raised during `generate()`.

---

### test-2 — Empty-alternative branch in `_gen_alternative_body` is untested

**File:** `tests/test_rust_unparser_generator.py` — no grammar in the test suite has a zero-item alternative.

`_gen_alternative_body` has a special early-return branch:

```python
if not alt.items:
    lines.append("        Some(UnparseResult::new(acc, pos))")
    lines.append("    }")
    return "\n".join(lines)
```

The code comment labels this "Degenerate empty alternative." No test hits this branch because every grammar used in the suite (`'greeting := "hello";'`, `'opt := "a"? . "b";'`, `'choice := "a" | "b";'`, `'pair := a:"x" : b:"y";'`) has at least one item in every alternative.

**Consequence:** If the empty-alternative body is accidentally modified to emit the threading preamble (`let mut pos = pos; let mut acc = acc;`) before the early return — producing a dead variable warning / different structure — no test catches it. The degenerate path is the one that diverges most from the normal path, so it is the most likely to be broken by incremental edits to `_gen_alternative_body`.

**Fix:** Construct a `gsm.Items(items=[], sep_after=[])` directly and wrap it in a one-alternative `gsm.Rule`, or find a grammar syntax that yields an empty alternative, then assert the emitted alt body is exactly `Some(UnparseResult::new(acc, pos))` with no `let mut` preamble.

---

### test-3 — NEST_BEGIN with `op.indent is None` (falling back to 1) is not tested

**File:** `tests/test_rust_unparser_generator.py`, line 239 area.

`_gen_rule_entry` emits `push_nest({op.indent or 1})`. When `op.indent` is `None` (a `FormatOperation` constructed without an `indent` argument), this falls back to `1`. The only test that exercises `NEST_BEGIN` passes `indent=2` explicitly, so the fallback path is never reached.

In normal usage, `_process_nest_statement` always supplies `indent_value = 1` (or from config), so `None` does not arise through `.fltkfmt` parsing. However, the fallback is there, and the semantics differ subtly: `indent=0` would also evaluate to `1` via `or`, which could surprise a caller who explicitly requests zero indentation. The expressed intent of the fallback is undocumented.

**Consequence:** Minor — the fallback is unlikely to be reached in practice, but if future callers construct `FormatOperation(OperationType.NEST_BEGIN)` directly (as `test_rule_start_and_end_anchors_emit_push_pop` does for GROUP_BEGIN and NEST_END), they get the silent default with no test coverage.

**Fix:** Add a sub-assertion in `test_rule_start_and_end_anchors_emit_push_pop` (or a new test) that constructs `FormatOperation(OperationType.NEST_BEGIN)` without `indent` and asserts `push_nest(1)` appears in the output.
