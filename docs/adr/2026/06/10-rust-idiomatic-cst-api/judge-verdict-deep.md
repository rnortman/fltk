# Judge verdict — deep review (Phase 2), round 2

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: deep (Phase 2 — idiomatic native Rust CST surface). Base 7e39dfb..HEAD 18ae558. Round 2 (APPROVED or ESCALATE only).
Round 1 verdict: REWORK on a single item — quality-2 (TODO(union-label-native-accessor-tests) failed rubric Q2: mechanical fix, design-committed coverage per §6 item 1, iteration-created gap). All 35 other dispositions were verified and accepted in round 1; that walk is carried forward below unchanged. Round-2 fix commits: 482880d (fix), 18ae558 (disposition update to Fixed).

Round-2 verification run at HEAD 18ae558:
- `cargo test --features python` in `tests/rust_cst_fixture`: 48 pass (39 at round 1 + 9 new union tests).
- `uv run pytest tests/test_gsm2tree_rs.py`: 132 pass (125 + 7 new `TestUnionLabelNativeAccessors`).
- `uv run pytest tests/test_phase4_rust_fixture.py`: 59 pass (Python-side integration over the regenerated fixture cdylib — grammar change did not break the Tier-2 path).

## Added TODOs walk

### security-1 — TODO(rust-cst-debug-depth) at gsm2tree_rs.py:~638 (derive emit), TODO.md
Q1 (worth doing): yes — derived `Debug` recurses through `Shared<T>` with no depth bound; tree depth is attacker-controlled via input nesting (R4 targets parsers over untrusted input); stack exhaustion → uncatchable abort on debug-logging.
Q2 (design/owner input required): yes — design §4.3 item 1 commits to `Debug` on all generated types and §5 documents the recursion hazard for cycles only; a depth-capped manual impl changes the public Debug surface (CLAUDE.md: generated output is downstream public API) — a design revision. Slug comment + TODO.md entry verified (round 1; entry still present at HEAD).
Assessment: TODO acceptable (unchanged from round 1).

### quality-2 — formerly TODO(union-label-native-accessor-tests), now Fixed (round-2 rework target)
Round 1 ruled this TODO fails Q2 (do-now). Round-2 fix verified at commit 482880d:
- Grammar: `value_node := operand:identifier | operand:literal` added to `fltk/fegen/test_data/phase4_roundtrip.fltkg` — label `operand` maps to {Identifier, Literal}, exercising the union branch of `_native_per_label_methods` for the first time in-tree.
- Regeneration: `tests/rust_cst_fixture/src/cst.rs` +589 lines (ValueNode, ValueNodeLabel, ValueNodeChild, union accessors). Makefile:129–130 confirms this is the sole generated output of that grammar; `git grep ValueNode` shows no other artifact stale. The `phase4_roundtrip_cst` Python cdylib is built from the same crate; its 59 integration tests pass.
- Compiled Rust tests: 9 added in `tests/rust_cst_fixture/src/native_tests.rs` — `child_operand` Ok for both Identifier and Literal variants; zero/two-child `ChildCount` errors for `child_operand`; `maybe_operand` None / Some(Literal) / two-child `ChildCount` pinning `expected: "0 or 1"`; `children_operand` yielding both variants in order; `extend_operand` bulk append. Read and write paths both covered, matching the reviewer's requested shape and design §6 item 1 ("union label → child enum").
- Generator string tests: 7 added in `tests/test_gsm2tree_rs.py::TestUnionLabelNativeAccessors` — union signatures for all five accessors, absence of `UnexpectedChildType` arm in `child_operand` body, `.map()` (not `filter_map`) in `children_operand`, child-enum write-side forms.
- Slug hygiene: `TODO(union-label-native-accessor-tests)` removed from both `gsm2tree_rs.py` union branches and from `TODO.md`; `git grep` finds the slug only in the dispositions doc (historical record — acceptable).
Assessment: fix complete; disposition Fixed is correct. Dispute resolved.

### test-10 — TODO(registry-unit-tests) at registry.rs:128 (pre-existing; Phase 1 finding)
Q1: yes — registry logic verified only through Python integration tests.
Q2: yes — direct Rust unit tests blocked by pyo3/libpython linkage in rlib test binaries; TODO.md enumerates three infra options — a build-architecture decision. Slug comment + entry verified (round 1).
Assessment: TODO acceptable (unchanged from round 1).

### reuse-1 / reuse-2 — TODO(crosscdylib-abi-check-helper) (pre-existing; Phase 0 findings)
Q1: yes — duplicated type-name idiom and ABI-pair-check blocks with already-diverging wording in `cross_cdylib.rs`.
Q2: yes — the generics extraction restructures two functions on the UB-guarding cross-cdylib boundary; Phase 0 code unchanged by Phase 2. Slug comments + TODO.md entry verified (round 1).
Assessment: TODO acceptable (unchanged from round 1).

## Other findings walk

All items below were verified and accepted in round 1 (evidence re-stated; none changed by the round-2 fix commits, which touch only the grammar file, regenerated fixture cst.rs, two test files, gsm2tree_rs.py TODO-comment deletions, and TODO.md).

### errhandling-1 / errhandling-2 (Phase 2) — Won't-Do
Phase 0 re-listings (the error-handling reviewer's Phase 2 section states "No findings"). At HEAD both `get_span_type` getattrs carry `.map_err(...PyTypeError...)` — fixed in Phase 0 round 2. Outcome correct. Accept.

### errhandling-3 (Phase 2) — Won't-Do
Same scope; `extract_source_text` layout getattr has `.map_err` at HEAD. Accept.

### errhandling-4 (Phase 2) — Fixed
Generator emits `registry::register_if_absent(py, addr, obj)?;`; generated outputs match. (`?` form present since Phase 1 merge; addressed at HEAD.) Accept.

### correctness-1 (Phase 2) — Fixed
`rule_name: str` parameter added to `_native_per_label_methods`; `rule_name_map` and dead union-shaped fallback deleted; unconditional `_label_type_info(rule_name, label)`. All five outputs regenerated. Accept.

### correctness-2 (Phase 2) — Fixed
f-prefix added to both TODO comment strings; generated output reads `see children_name above`. Accept.

### test-1 through test-5 (Phase 2 section) — Won't-Do
Phase 0 re-listings, out of scope; addressed in Phase 0 round-2 dispositions with fixes verified there. Accept.

### test-6 / test-7 / test-8 — Fixed (already present at HEAD)
`test_handle_struct_emitted`, `test_to_py_canonical_uses_registry`, `test_py_new_uses_force_register` in tests/test_gsm2tree_rs.py; pass in the 132-test run. Accept.

### test-9 — Fixed (already present at HEAD)
`test_children_label_accessor_identity` at tests/test_phase4_rust_fixture.py. Accept.

### test-11 — Fixed (already present at HEAD)
`assert first is ident` in `test_extend_children_duplicates_entries`. Accept.

### test-12 — Fixed (already present at HEAD)
`test_shared_child_mutation_visible_through_two_parents`. Accept.

### test-13 — Fixed
Spike `child_item_unexpected_child_type` + `child_item_count_error_beats_type_error`; fixture `child_lbl_unexpected_child_type_returned_by_accessor` + `child_lbl_count_error_beats_type_error_with_wrong_types`. Matches the reviewer's requested fix. Accept.

### test-14 — Fixed
Spike `children_item_skips_off_type_variant`, fixture `children_key_skips_off_type_variant` — typed count == 1, lossless `children().len() == 2`. Accept.

### test-15 — Fixed
Spike `child_item_exactly_one_ok`, `child_item_zero_returns_child_count_error` (node-typed label path). Accept.

### test-16 — Fixed
Spike `maybe_item_two_returns_child_count_error` pins `expected: "0 or 1"`. Accept.

### reuse-3 — Fixed (already present at HEAD)
Generated `__eq__` emits `let eq = self.inner == other_handle.inner;` — delegates to `Shared::PartialEq`. Accept.

### reuse-4 — Won't-Do
Core-crate test infra blocked by the same pyo3 linkage issue as `registry-unit-tests`; two-grammar duplication yields coverage from two perspectives. Nit severity. Accept.

### reuse-5 / reuse-6 / reuse-7 — Won't-Do
Post-efficiency-1, both branches emit the identical zero-alloc `(next, next)` match shape; remaining duplication is generator-internal emit organization, and divergence would surface in committed regenerated outputs at review. Nit severity. Accept.

### reuse-8 — Fixed (superseded by efficiency-1)
Zero `let matching: Vec<_>` sites across all five generated outputs. Accept.

### quality-1 — Fixed
Same fix as correctness-1. Accept.

### efficiency-1 — Fixed
Alloc-free `(it.next(), it.next())` match in `child_<lbl>`/`maybe_<lbl>` for single-node and span branches; recount only on the error path. Accept.

### efficiency-2 — Fixed
All three `extend_<lbl>` branches emit `self.children.extend(...map(...))`. Accept.

### efficiency-3 — Fixed
Same fix as correctness-1 (per-call O(rules) dict rebuild eliminated). Accept.

## Disputed items

None. The round-1 dispute (quality-2) is resolved: the TODO was promoted to Fixed with grammar, regeneration, compiled Rust tests, and generator string tests, exactly as the rework required.

## Approved

36 findings: 20 Fixed verified, 12 Won't-Do sound, 4 TODOs acceptable.

---

## Verdict: APPROVED

All dispositions acceptable. The single round-1 REWORK item (quality-2) is fixed and verified at HEAD 18ae558; all other dispositions stand as verified in round 1.
