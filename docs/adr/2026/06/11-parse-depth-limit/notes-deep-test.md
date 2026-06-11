## Test-reviewer findings — parse-depth-limit (ef315be..d442f56)

Style: concise, precise, complete. No padding.

---

### test-1

**File**: `fltk/fegen/test_gsm2parser_rs.py` — Python bindings code-generation section (tests named `test_python_bindings_*`)

**What's wrong**: No generator test covers the three new depth-limit code-generation paths in `_gen_python_bindings`:
1. `PyRecursionError` import emitted in the bindings block.
2. The `depth_exceeded` guard (`if self.inner.depth_exceeded() { return Err(PyRecursionError…) }`) emitted after each `let result = self.inner.apply__parse_X(pos)` call.
3. The new `max_depth` and `depth_exceeded` `#[getter]` methods emitted in `PyParser`.

The new constructor signature (`max_depth = None`) is also not tested at the generator level (only at runtime in `test_rust_parser_fixture_bindings.py`). `_EXPECTED_NON_APPLY_PUB_FNS` includes `set_max_depth`, `max_depth`, `depth_exceeded` but that set is only exercised by `test_private_rule_bodies_not_pub`, which tests that generated Rust functions are not unexpectedly public — it doesn't assert the functions are *present* in the output.

**Consequence**: A regression in the generator (e.g. accidentally dropping the `PyRecursionError` import, omitting the guard, or not emitting the getters) would not be caught by any fast `uv run pytest fltk/fegen/test_gsm2parser_rs.py` run. The fault would surface only when the full fixture is rebuilt, which is a slower and less reliable signal.

**Fix**: Add generator-level tests in `test_gsm2parser_rs.py` that call `gen.generate()` on a minimal grammar and assert:
- `"use pyo3::exceptions::{PyRecursionError, PyValueError};"` (or the equivalent import) appears in the bindings block.
- `"if self.inner.depth_exceeded()"` appears in the bindings block (one occurrence per rule, or at minimum one).
- `"fn max_depth(&self) -> u32"` and `"fn depth_exceeded(&self) -> bool"` appear in the bindings block.
- `"max_depth = None"` (or `"max_depth: Option<u32>"`) appears in the `#[pyo3(signature = …)]` for `new`.

---

### test-2

**File**: `crates/fltk-parser-core/tests/memo_toy.rs:460-476` (T1) and `tests/test_rust_parser_fixture_bindings.py` (T5/T6)

**What's wrong**: `max_depth = 0` (the explicitly called-out degenerate case from design §2: "first apply fails with flag set") is not tested anywhere — neither in the toy-parser cargo tests nor in the fixture bindings tests. The design declares this "well-defined" and explicitly notes the guard uses `>=`, making `max_depth=0` reject the very first call.

**Consequence**: If the guard condition is ever changed (e.g. `>` instead of `>=`), or if the `Default` impl somehow initialises `depth` to 1 rather than 0, the degenerate case silently breaks. No test catches it.

**Fix**: Add one cargo test in `memo_toy.rs`:
```rust
#[test]
fn test_depth_limit_zero_rejects_immediately() {
    let input = vec!["1".to_owned()];
    let mut p = DepthParser::new(input, 0);
    let result = p.apply__nest(0);
    assert!(result.is_none());
    assert!(p.packrat.depth_exceeded());
}
```
Optionally mirror this in `test_rust_parser_fixture_bindings.py` with `Parser("42", max_depth=0)` → `RecursionError`.

---

### test-3

**File**: `tests/test_rust_parser_parity_fixture.py:98-105`

**What's wrong**: The parity corpus for `nest` and `nest_sum` contains only `SUCCESS` cases. No `FAIL` entries are added for the new rules (e.g. `("nest", "(42", FAIL)` — unclosed paren — or `("nest_sum", "+42", FAIL)` — leading operator). Every other rule group in the parity corpus has at least one failure case. The new rules exercise a code path (`parse_nest__alt0`, `parse_nest__alt1`) that is absent from all other rules (right-recursive with suppressed delimiters), so the failure path of that code is not parity-covered.

**Consequence**: A generator bug that makes `parse_nest` accept malformed input would not be caught by the parity corpus. The failure cases of the generated alt functions for `nest`/`nest_sum` are untested.

**Fix**: Add to the corpus:
```python
("nest", "(42", FAIL),      # unclosed paren
("nest_sum", "+42", FAIL),  # no leading operand
```

---

### test-4

**File**: `tests/test_rust_parser_fixture_bindings.py:78-85` (`test_t5_spent_instance_raises_on_subsequent_call`)

**What's wrong**: The test calls `p.apply__parse_nest(0)` as the second call on the spent instance, parsing from position 0 on the *same deeply-nested text* that caused the original overflow. This means the second call might raise `RecursionError` due to a cached-`Failure` hit being short-circuited by the sticky flag — which is correct — but it doesn't distinguish "sticky flag returns `None` → guard raises" from "cached `Failure` → `None` → guard raises". The intent is to prove the sticky flag, but the cache for pos 0 may contain a `Failure` entry from the first call, so both mechanisms produce the same outcome. This doesn't make the test wrong, but it's a weaker proof of stickiness than the T3 cargo test (which clears caches). The comment in the test doesn't acknowledge this subtlety.

**Consequence**: Low. The sticky property is also proven by T3 (cargo, with cache-clearing). The binding-level test still demonstrates that repeated calls raise `RecursionError`, which is the observable behaviour contract. However, if the sticky flag were removed and only cache-based `None` remained, this test would still pass, masking the regression.

**Fix**: Either (a) add a comment noting that both mechanisms produce the same observable outcome and T3 is the definitive stickiness proof, or (b) use a *different* (trivially parseable) text for the second call:
```python
p2 = rust_parser_fixture.Parser("42")  # fresh but same instance after overflow — not possible
```
Better: after the overflow, call a *different* rule that was not invoked at all, so its cache is cold:
```python
with pytest.raises(RecursionError):
    p.apply__parse_nest_sum(0)  # different rule, cold cache — proves flag not cache
```
This verifies the sticky flag independently of the cache state.
