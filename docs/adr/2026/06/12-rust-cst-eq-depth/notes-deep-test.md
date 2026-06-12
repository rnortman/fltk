Commit reviewed: 44458c5

test-1
File: tests/rust_parser_fixture/src/native_tests.rs (EQ-1 through EQ-6)
What: The `la != lb` (label mismatch) branch of the iterative PartialEq is not exercised by any test. In EQ-6 both nodes have `label=Some(ValLabel::Item)` (appended via `append_item`), so the comparison reaches `eq_shallow_enqueue` rather than the `la != lb` early-exit. None of the other EQ tests produce nodes with differing labels. The old one-liner (`self.children == other.children`) caught label mismatches via `Vec`/tuple `PartialEq`; the new explicit `if la != lb` check is a new code path with no test.
Consequence: A bug that inverted or removed the `la != lb` condition would cause nodes whose children have different labels to compare equal — undetected.
Fix: Add a test that constructs two nodes with one child each under different labels and asserts `!=`. Using the parser fixture: build one `Expr` with `push_child(Some(ExprLabel::Lhs), ExprChild::Atom(..))` and another with `push_child(Some(ExprLabel::Rhs), ExprChild::Atom(..))` — same span, same child variant, differing label — and assert they are unequal.

test-2
File: tests/rust_parser_fixture/src/native_tests.rs (EQ-1 through EQ-6), tests/rust_cst_fixture/src/native_tests.rs
What: The `children.len() != other.children.len()` early-exit path in the iterative `PartialEq` impl is not exercised. All EQ tests build trees with matching child counts. The Python-side `test_assert_cst_equal_fails_child_count_mismatch` uses the `assert_cst_equal` helper (structural walk), not `==`, so it does not reach the Rust `PartialEq` path.
Consequence: A bug in the length check (e.g. wrong operator, off-by-one) would cause nodes with different child counts to be compared element-wise via the zip loop (which terminates at `min(len_a, len_b)`), potentially returning true for nodes that differ only in trailing children.
Fix: Add a test building two nodes with the same span but different child counts and assert `!=`. Example: one `Expr` with zero children, another with one `append_atom` child.

test-3
File: tests/test_phase4_rust_fixture.py (line 456: `test_node_eq_self_no_deadlock`); no other Python eq test
What: No Python test exercises deep-tree `__eq__` through the iterative Rust path. `test_node_eq_self_no_deadlock` only covers the `ptr_eq` short-circuit (self-comparison on an empty node). The `_eq_method` pymethod delegates `self.inner == other_handle.inner` → `Shared<T>::PartialEq` → the iterative `T::eq`. A regression in that delegation chain (e.g. wrong method called, Python-side wrapping bug) would not be caught by any Python test.
Consequence: A breakage in the Python `__eq__` path for distinct-allocation deep trees would go undetected by the Python test suite; only the Rust tests cover the underlying logic.
Fix: Add a Python test that parses the same non-trivial input twice through the Rust parser and asserts `result1 == result2` via Python `==` (not `assert_cst_equal`). A small grammar with a few levels of nesting is sufficient — depth correctness is covered by the Rust tests; this test pins the pymethod delegation.
