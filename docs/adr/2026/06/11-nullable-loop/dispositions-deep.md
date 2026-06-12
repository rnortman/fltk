Concise. Precise. Complete. Unambiguous. No padding.

---

errhandling-1:
- Disposition: Fixed
- Action: (Rework) Implemented `_collect_repeated_nil_errors` recursive helper (gsm.py:356+) that walks `Sequence[Items]` sub-expression terms at any depth. `validate_no_repeated_nil_items` now calls it instead of the flat loop. Added two new tests in `test_nil_validation.py`: `test_repeated_nil_validation_rejects_nested_subexpr` (one level deep) and `test_repeated_nil_validation_rejects_deeply_nested_subexpr` (two levels deep). Removed `TODO(validator-subexpr)` from TODO.md and code. The "guard MUST remain" note stays in the validator docstring (regex-emptiness under-approximation persists).
- Severity assessment: Nested MULTIPLE+nullable items now raise ValueError at validation time, same as top-level cases. Grammar authors get a clear design-time error instead of silent acceptance and surprising empty-match-discard at parse time.

---

correctness-1:
- Disposition: Fixed
- Action: Same as errhandling-1 — same root fix and tests.
- Severity assessment: Nested repeated-nullable is now caught at validation time.

---

correctness-2:
- Disposition: Fixed
- Action: Added docstring to `Rule` (gsm.py:26+) and `Items` (gsm.py:76+) documenting the single-grammar-per-object invariant. The in-tree pipeline is unaffected (classify_trivia_rules uses dataclasses.replace which resets the cache). Out-of-tree API users are now warned. Keying the cache on grammar id was rejected: it would require mutable state in frozen dataclasses and is disproportionate to the impact (standard pipeline is safe; non-standard multi-grammar reuse is an unusual pattern).
- Severity assessment: Stale cached nullability is possible only when the same Rule/Items object is queried under two Grammar instances with differing identifier sets — atypical usage. In-tree behavior is unaffected. Documentation closes the hazard for out-of-tree consumers.

---

security-1:
- Disposition: Fixed
- Action: Changed Rust guard from `== pos` to `<= pos` (gsm2parser_rs.py:708). Changed Python guard from `iir.Equals(...)` to `iir.LogicalNegation(iir.GreaterThan(...))`, compiling to `not one_result.pos > pos` (gsm2parser.py:569+). Regenerated all generated artifacts. Tests updated to assert the new guard strings.
- Severity assessment: Under `==`, a position regression (one_result.pos < pos) would not trigger the guard, leaving the infinite loop unremediated. Today no consume path returns a regressed position, but the guard exists precisely as defense-in-depth for broken invariants. `<=` costs nothing and closes the structural gap.

---

security-2:
- Disposition: Fixed (partial — (a) Fixed; (b) documented)
- Action: (a) Sub-expression recursion gap → Fixed (rework), same as errhandling-1: recursive walk implemented, nested trigger tests added. (b) Context-sensitive regex under-approximation (`\ba*`, `(?=x)`): documented in the validator docstring (gsm.py:356+) — "the guard MUST remain" note explicitly calls out this residual. No code change for (b): conservative False for boundary-anchored patterns means they reach the guard; the guard terminates cleanly; fixing `_test_regex_empty` requires non-trivial regex analysis and is an independent improvement.
- Severity assessment: (a) closed: nested repeated-nullable now raises at validation time. (b) residual: context-sensitive zero-width patterns still pass the validator and reach the guard; documented and bounded (guard handles them correctly).

---

test-1:
- Disposition: Fixed
- Action: Rewrote `test_plus_loop_has_guard` to assert `not one_result.pos > pos` (the actual ast.unparse form of `LogicalNegation(GreaterThan(...))`) and verify `break` appears in the region between the guard condition and the pos update (tests/test_nullable_loop_guard.py:737+).
- Severity assessment: Without the break assertion, a refactor substituting `pass` or any non-terminating statement inside the guard would pass the test. Now both the condition and the terminating effect are verified.

---

test-2:
- Disposition: Fixed
- Action: Added ordering assertion to `test_star_loop_has_guard` (tests/test_nullable_loop_guard.py:753+), verifying the guard index precedes the `pos = one_result.pos` index. Mirrors the existing ordering check in the + test.
- Severity assessment: A regression emitting the guard after the pos update for * loops would produce vacuously true breaks (breaking every iteration), not caught by the former presence-only check.

---

test-3:
- Disposition: Fixed
- Action: Added `test_trivia_rule_not_nil_required_nullable_term` to `fltk/fegen/test_nil_validation.py:105+`. Constructs `_trivia` with REQUIRED quantifier and `Regex(r"\s*")` and asserts `validate_trivia_rule_not_nil` raises ValueError.
- Severity assessment: The newly-tightened REQUIRED+nullable-term path was untested; a regression reverting to quantifier-only checking would not be caught.

---

test-4:
- Disposition: Fixed
- Action: Rewrote `test_one_or_more_empty_literal_is_nil` docstring (tests/test_nullable_loop_guard.py:572+). New docstring states the formula upfront (`is_optional() OR term_can_be_nil` = `False OR True` = `True`) and explains why ONE_OR_MORE+nullable-term is nil. Removed the multi-paragraph argument for False that contradicted the assertion.
- Severity assessment: Documentation trap only; no correctness risk. Future authors can now read the docstring and understand the assertion without being misled into "fixing" it.

---

quality-1:
- Disposition: Fixed
- Action: (Rework) Same fix as errhandling-1/correctness-1 — recursive helper implemented. The quality-1 suggested implementation was the model for `_collect_repeated_nil_errors`.
- Severity assessment: See errhandling-1.

---

quality-2:
- Disposition: Fixed
- Action: Removed `one_result_ref` named local in `gen_item_parser_multiple` (gsm2parser.py:568). Guard condition now uses an inline `loop.block.get_leaf_scope().lookup_as(...)` call, consistent with all other one_result references in the function.
- Severity assessment: Cosmetic consistency; eliminates the maintenance hazard of three different reference patterns for the same object.

---

efficiency-1:
- Disposition: Fixed
- Action: Added `env={**os.environ, "CARGO_TARGET_DIR": str(_repo_root / "target" / "nullable-loop-guard-test")}` to the cargo build subprocess call (tests/test_nullable_loop_guard.py:382+). Updated binary path to point to the shared target dir. Dep crates compile once and are reused across sessions; only the generated parser.rs/cst.rs/main.rs recompile.
- Severity assessment: Without CARGO_TARGET_DIR, every test run cold-compiled regex-automata (the dominant dep, flagged in TODO(regex-automata-features)). With the shared dir, subsequent runs reuse compiled deps — significant wall-clock savings on CI.

---

efficiency-2:
- Disposition: Fixed
- Action: Replaced `test_cross_backend_parity` (which re-ran Python backend in-process and checked the same values as `test_python_backend_guard`) with a lightweight cross-reference check (tests/test_nullable_loop_guard.py:416+). New test asserts that `_RUST_MAIN_RS` encodes the expected pos=2 and None outcomes, making the "parity" claim explicit without re-running generation.
- Severity assessment: The duplicate Python generation added non-trivial overhead on every test run with no additional coverage. The replacement check is near-zero cost and explicitly validates that the Rust binary's expectations match the documented cross-backend values.
