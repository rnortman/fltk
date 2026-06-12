Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 2f9b05e. Dispositions commit: 7267eb4.

---

error-handling-1 (no findings):
- Disposition: Won't-Do
- Action: no change — reviewer reported no findings
- Severity assessment: N/A

correctness-1 (no findings):
- Disposition: Won't-Do
- Action: no change — reviewer reported no findings
- Severity assessment: N/A

security-1 (no findings):
- Disposition: Won't-Do
- Action: no change — reviewer reported no findings
- Severity assessment: N/A

test-1 (stale derive(Debug) assertion + missing generator-level Debug/Drop tests):
- Disposition: Fixed
- Action: tests/test_gsm2tree_rs.py — replaced the stale `assert "#[derive(Clone, Debug)]" in poc_source` (TestCfgFeatureGate.test_node_struct_pyclass_gated) with correct assertions: `#[derive(Clone)]\npub struct Identifier {` present, `#[derive(Clone, Debug)]\npub struct Identifier {` absent, `impl fmt::Debug for Identifier {` present, `f.debug_struct("Identifier")` present, `"<{} child(ren)>"` present. Added TestNodeDebugDrop class with five tests covering: node-struct derive(Clone)-only, manual Debug impl, DropWorklistItem emission for non-flat grammar, impl Drop for node-with-node-children, no impl Drop for span-only node.
- Severity assessment: The stale assertion was passing only because child enums still carry derive(Clone, Debug); a generator regression silently reverting node structs to derived Debug would pass all Python tests undetected.

test-2 (flat grammar missing DropWorklistItem absence check):
- Disposition: Fixed
- Action: tests/test_gsm2tree_rs.py TestMinimalGrammar — added test_flat_grammar_no_drop_worklist asserting neither "DropWorklistItem" nor "impl Drop" appear in the minimal single-rule output.
- Severity assessment: A regression that emits an empty-union DropWorklistItem would produce dead_code warnings under -D warnings (hard failure at cargo-clippy gate); the absence check provides an earlier Python-level signal.

test-3 (same stale assertion as test-1, different framing):
- Disposition: Fixed
- Action: same fix as test-1 — addressed together.
- Severity assessment: Same as test-1.

test-4 (multi-child worklist path not exercised by deep-tree tests):
- Disposition: Fixed
- Action: tests/rust_parser_fixture/src/native_tests.rs — added test_multi_child_drop_worklist: builds a 100-level chain where each Expr has both lhs:Expr (Shared<Expr>) and rhs:Atom (Shared<Atom>) children, so the worklist holds >1 item at each level. Verifies drop completes without overflow.
- Severity assessment: Tests 1 and 2 exercised the worklist with at most 1 item; a bug that dropped the second child push or misidentified the Atom variant's drain arm would be undetected by those tests alone.

test-5 (duplicate Shared::strong_count unit test):
- Disposition: Fixed
- Action: tests/rust_parser_fixture/src/native_tests.rs — added comment to test_shared_strong_count clarifying it tests downstream-crate public reachability of the method; the canonical contract test lives in fltk-cst-core/src/shared.rs. Kept both tests with distinct documented purposes.
- Severity assessment: Low — tests cover the same behavior. Resolved by scoping them as testing different things (contract vs. accessibility), not by deletion.

test-6 (IdentifierChild::Span Debug format discarded without assertion):
- Disposition: Fixed
- Action: crates/fltk-cst-spike/src/spike_tests.rs — replaced `let _ = format!(...)` with an assertion that the Debug output contains "Span".
- Severity assessment: Minor coverage gap; if IdentifierChild::Span's Debug were accidentally broken the test would still pass.

test-7 (implicit drop ordering in test 5):
- Disposition: Fixed
- Action: tests/rust_parser_fixture/src/native_tests.rs — added explicit `drop(r); drop(parser);` with a comment explaining the LIFO declaration order and what each drop exercises.
- Severity assessment: Documentation/clarity gap only; functional behavior was already correct. Explicit ordering makes the intent unambiguous.

reuse-1 (duplicate strong_count test):
- Disposition: Fixed
- Action: same fix as test-5 — resolved by scoping the two tests as contract (core crate) vs. reachability (fixture crate).
- Severity assessment: Low maintenance concern; addressed without deletion to preserve coverage scope clarity.

reuse-2 (DEEP_TREE_DEPTH not used in test 5):
- Disposition: Fixed
- Action: tests/rust_parser_fixture/src/native_tests.rs line 115 — replaced `let n = 100_000usize;` with `let n = DEEP_TREE_DEPTH;`.
- Severity assessment: If the depth constant were adjusted, test 5 would silently diverge from the other deep-tree tests.

quality-1 (stale assertion in test_node_struct_pyclass_gated):
- Disposition: Fixed
- Action: same fix as test-1.
- Severity assessment: Same as test-1.

quality-2 (rust-cst-eq-depth not tracked in TODO.md):
- Disposition: Fixed
- Action: TODO.md — added rust-cst-eq-depth entry describing the pre-existing PartialEq recursive-depth exposure and pointing to the fix location. crates/fltk-cst-core/src/shared.rs:93 — added TODO(rust-cst-eq-depth) comment above PartialEq impl. fltk/fegen/gsm2tree_rs.py _node_block — added TODO(rust-cst-eq-depth) comment above the emitted PartialEq impl.
- Severity assessment: Without a TODO entry the PartialEq stack-exhaustion DoS (same class as the fixed Debug/Drop paths) would be invisible to future maintainers. The comment at the code sites directly precedes the vulnerable code so the deferral is discoverable.

quality-3 (drain_into arms copy-pasted N times in generator loop):
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py — extracted _emit_drain_arm static method called in the per-class loop in _drop_block. Generated output is byte-identical; the change reduces future change surface for drain logic to one site.
- Severity assessment: Pure maintainability issue; a mis-edit to one arm that diverged from others would be hard to detect in a flat list of lines.append calls.

efficiency-1 (worklist collect() allocates even for shared/memoized children):
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py _node_block — replaced the `collect()` form with `Vec::new()` + per-item `drain_into` loop so the worklist is not allocated until the first steal. Regenerated all six CST outputs. No behavior change; deep owned chains still allocate once (first push from drain_into); shared/memoized children (the backtracking hot path) allocate nothing.
- Severity assessment: The collect() form allocated one Vec per discarded partial node during parsing, which fires at every failed alternative with a node-typed child already appended. For left-recursive grammars over long inputs this is a per-parse cost proportional to input length × failed-alternative density.

efficiency-2 (generator recomputes _child_variants_for_rule per rule, O(U) list membership):
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Generator-time only; current grammar sizes (tens of rules) make this negligible. Adding lru_cache and converting child_union to a set would complicate the generator for no observable benefit at current scale. The design's pre-pass already computes the union once before the per-rule loop; the remaining redundancy is at codegen time, not parse time.
