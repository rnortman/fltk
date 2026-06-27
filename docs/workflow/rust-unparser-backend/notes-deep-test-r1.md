## Test review: `fltk-unparser-core` batch 1

Commit reviewed: 285064a9a37c76f56f6fa1b44d4c553c34f49bcc

Sources ported: `accumulator.py` → `accumulator.rs`, `combinators.py` → `doc.rs`,
`resolve_specs.py` → `resolve.rs`. Tests live inline in each source file under
`#[cfg(test)]`.

---

### test-1

**File:line:** `crates/fltk-unparser-core/src/resolve.rs` — `mutate_text_newline` (line 452)

**What's wrong:** `mutate_text_newline` — the pattern `Text("\n"), SeparatorSpec(spacing=Some(_)) → HardLine` — has no test, direct or indirect. No test in the Rust suite passes a `Text("\n")` node adjacent to a `SeparatorSpec` with `spacing=Some(_)` and verifies the output is `HardLine { blank_lines: 0 }`.

**Consequence:** If the implementation checked the wrong field, compared against the wrong string, or had an off-by-one on the pattern index, no existing test would fail. This code path is completely unexercised.

**Fix:** Add a test such as:
```rust
#[test]
fn text_newline_plus_separator_becomes_hardline() {
    let doc = cat(vec![
        text("\n"),
        sep(Some(line()), None, false),
        text("x"),
    ]);
    let resolved = resolve_spacing_specs(&doc);
    assert_eq!(resolved, cat(vec![hardline(0), text("x")]));
}
```

---

### test-2

**File:line:** `crates/fltk-unparser-core/src/resolve.rs` — `extract_boundary_specs` (line 197)

**What's wrong:** Python's `test_resolve_specs.py` has four edge-case tests for `_extract_boundary_specs`: `only_leading`, `only_trailing`, `all_specs`, and `empty_list`. The Rust suite ports only `basic` and `no_specs`. Missing cases:
- Only leading specs, empty remaining, empty trailing.
- Only trailing specs, empty leading, non-empty remaining.
- All items are specs (leading BeforeSpecs then a trailing AfterSpec, with empty remaining).
- Empty input list.

**Consequence:** A bug specific to the only-leading path (e.g., the while-loop over trailing incorrectly consuming content when there is no remaining) or the all-specs path (remaining becomes empty after both extraction loops) would not be caught.

**Fix:** Port the missing four Python tests directly.

---

### test-3

**File:line:** `crates/fltk-unparser-core/src/resolve.rs` — `resolve_spacing` (line 631)

**What's wrong:** The `assert!` in `resolve_spacing` that fires when `sep_spacing.is_none()` (the `"Separator has neither preserved trivia nor spacing"` message) is never triggered by any test. This assert is the faithful port of the Python `raise RuntimeError`. No test verifies it fires.

**Consequence:** A caller that incorrectly constructs a `SeparatorSpec { spacing: None, preserved_trivia: None, required: false }` inside an `AfterSpec / Sep / BeforeSpec` triple would silently corrupt output rather than panic. The assert is the only guard.

**Fix:** Add a `#[should_panic(expected = "Separator has neither preserved trivia nor spacing")]` test that builds `cat(vec![after(line()), sep(None, None, false), before(line())])` and calls `resolve_spacing_specs`.

---

### test-4

**File:line:** `crates/fltk-unparser-core/src/accumulator.rs` — `pop_nest` (line 173)

**What's wrong:** `pop_group_rejects_wrong_nesting` and `pop_join_rejects_wrong_nesting` both have `#[should_panic]` tests. The symmetric case — calling `pop_nest()` on an accumulator whose `nesting_doc` is `Group` or `Join` — has no test. The panic message would be "Expected Nest but have ...".

**Consequence:** A copy-paste error that caused `pop_nest` to match the wrong variant (e.g., accepting a `Group` instead of panicking) would not be detected.

**Fix:**
```rust
#[test]
#[should_panic(expected = "Expected Nest")]
fn pop_nest_rejects_wrong_nesting() {
    let _ = DocAccumulator::new().push_group().pop_nest();
}
```

---

### test-5

**File:line:** `crates/fltk-unparser-core/src/resolve.rs` — `resolve_spacing_specs` tests

**What's wrong:** Eight Python tests are not ported to Rust:
- `test_nested_group_nest_extraction` — Group → Nest multi-level extraction with consecutive Before/AfterSpecs merging.
- `test_multiple_nested_groups` — outer Group containing inner Group with specs.
- `test_complex_multilevel_extraction` — three-deep nesting (Group → Nest → Group), specs at every level.
- `test_empty_group_with_specs` — Group whose only content is Before+AfterSpec (remaining content becomes NIL).
- `test_consecutive_groups_with_specs` — two consecutive Groups each with boundary specs, separator between.
- `test_deeply_nested_empty_structures` — Group → Nest → Group that empties completely after extraction.
- `test_consecutive_specs_inside_group` — consecutive BeforeSpecs inside a Group that must be merged then extracted.
- `test_consecutive_leading_specs_in_group` — the compound scenario that motivated the consecutive-spec merging fix (two Groups, the first trailing AfterSpec + SeparatorSpec, the second leading consecutive BeforeSpecs).

These were added to the Python suite specifically to cover bugs in boundary-spec extraction and consecutive-spec merging. The last two are the most important because they exercise the interaction between `mutate_consecutive_specs` and `extract_all_boundary_specs` that was a regression target.

**Consequence:** Regressions in multi-level boundary-spec extraction, consecutive-spec merging inside groups, and the empty-group-after-extraction case would not be caught. These are the scenarios most likely to re-regress because they involve subtle ordering of passes.

**Fix:** Port all eight tests. The `test_consecutive_leading_specs_in_group` case should be highest priority.

---

### test-6

**File:line:** `crates/fltk-unparser-core/src/resolve.rs` — `pick_spacing_with_blank_lines` (line 430)

**What's wrong:** `pick_spacing_with_blank_lines` has a branch where the separator's `HardLine { blank_lines > 0 }` wins over the primary spacing (after/before spec). This fires when the separator carries a HardLine with more blank lines than the primary. No test exercises this path — all separator specs in existing tests use `nil()` spacing or spacing where the primary clearly wins.

**Consequence:** If the condition `*sep_bl > 0` or the comparison `*blank_lines < *sep_bl` were wrong, the resolver would silently emit fewer blank lines than the separator requested.

**Fix:** Add a test where a `sep(Some(hardline(2)), None, true)` flanked by `after(line())` resolves to `hardline(2)`.

---

### test-7

**File:line:** `crates/fltk-unparser-core/src/accumulator.rs:272–275` — `add_trivia_sets_flag`

**What's wrong:** This test directly accesses the private field `last_was_trivia` to assert its value after `add_non_trivia` and `add_trivia`. It tests internal state rather than observable behavior. The observable consequence of `last_was_trivia` — that it propagates through `pop()` to the parent — is already covered by `pop_propagates_trivia_state_to_parent`.

**Consequence:** A safe refactor that tracks trivia state differently (e.g., an enum instead of bool) would break this test even if behavior is identical. Brittle coupling to implementation detail.

**Fix:** Remove or rewrite to test behavior: assert that a pop after `add_trivia` propagates the trivia flag, rather than asserting the private field directly. Since `pop_propagates_trivia_state_to_parent` already covers this, the test could simply be deleted.

---

### test-8

**File:line:** `crates/fltk-unparser-core/src/doc.rs` — stack-overflow tests (line 316)

**What's wrong:** Stack-overflow regression tests exist for `Group`, `Concat`, and `Join` but not for `Nest`, `AfterSpec`, or `BeforeSpec`. All four single-child variants go through the same `take_children` worklist arm, but only `Group` is verified not to overflow a 200 000-deep chain.

**Consequence:** If the iterative Drop incorrectly handled `Nest` (e.g., a future refactor that accidentally bypassed `take_children` for `Nest`), no test would catch the stack overflow.

**Fix:**
```rust
#[test]
fn deep_nest_chain_drops_without_stack_overflow() {
    let mut doc = text("leaf");
    for _ in 0..200_000 {
        doc = nest(4, doc);
    }
    drop(doc);
}
```
