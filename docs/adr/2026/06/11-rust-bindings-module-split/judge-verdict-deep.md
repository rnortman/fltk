# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 3157b59..HEAD d8233c6 (review commit 4fe645d, respond commit d8233c6). Round 1.
Notes: 7 reviewer files (security, reuse, efficiency: no findings); 14 dispositioned items.
Verification: respond diff inspected file-by-file; `uv run pytest tests/test_module_split.py tests/test_gsm2tree_rs.py::TestReservedClassNameRejection fltk/fegen/test_gsm2parser_rs.py` — 101 passed; `cargo test -p fltk-cst-core --no-default-features --lib` — 28 passed.

## Added TODOs walk

### correctness-1 — TODO(register-submodule-non-maturin) at crates/fltk-cst-core/src/py_module.rs:19
TODO mechanics: slug comment present (py_module.rs:19-24), TODO.md entry present (TODO.md:64-67). Both-halves requirement met.

Q1 (worth doing): yes — `user_facing_name("a.b.b")` unconditionally strips to `"a.b"` (py_module.rs:39-41, enshrined by `triple_nested_double_match`), producing wrong `sys.modules` keys for genuine `a.b.b` layouts. CLAUDE.md: out-of-tree consumers are the primary audience and the absence of an in-tree consumer is not evidence of safety; the repo itself documents Bazel as an alternative build path. Consequence is `RustBackendUnavailableError` despite a loaded extension, plus possible shadowing of a real `a.b.cst`.

Q2 (design/owner input required): no. The fix is already fully specified — twice. The reviewer named it (`register_submodule_with_parent_name` variant or `Option<&str>` override), and the responder's own TODO.md entry repeats it verbatim as "Fix: add a `register_submodule_with_parent_name` variant (or `Option<&str>` override) that bypasses the heuristic." A TODO entry that contains its own implementation plan cannot simultaneously claim a design cycle is needed. Moreover the design (§2.2) already specified the explicit `parent_qualified_name` API; the heuristic was an implementation-time deviation, so the explicit-name escape hatch is the *designed* surface, not new design territory. Implementation is additive (~20 lines + unit test): keep the heuristic default, add the override; no behavior change for existing callers.

Furthermore: this iteration created the problem. `register_submodule` and `user_facing_name` did not exist before this branch (introduced b62f721, redesigned 56f8b00); the false-positive is a property of the new heuristic, not pre-existing. Per rubric, an iteration-created problem cannot be silently deferred — fix now (Q2 is no) or escalate. Neither was done.

Assessment: fails Q2 and falls under iteration-created-cannot-defer. Disposition wrong → do-now.

## Other findings walk

### errhandling-1 — Fixed
Claim: `parent.name()?` at py_module.rs propagated a raw pyo3 error with no context; consequence: on-call cannot tell which registration step failed.
Code: py_module.rs:86-93 — `map_err` wraps with `PyRuntimeError` naming the submodule (`register_submodule({name:?}): failed to get parent module name`).
Assessment: addresses the claim at the named site. Accept.

### errhandling-2 — Fixed
Claim: `register(&sub)?` / `parent.add_submodule(&sub)?` propagated raw errors without submodule identity; reviewer noted `qualified_name` had to move earlier.
Code: py_module.rs:94-107 — `qualified_name` constructed before both calls; both wrapped with `PyRuntimeError` naming the qualified path.
Assessment: complete, including the reordering note. Accept.

### errhandling-3 — Won't-Do
Reviewer's own assessment: "Not a finding — correctly handled invariant violation" (double-init `expect`). Won't-Do is the only coherent disposition for a non-finding. Accept.

### errhandling-4 — Won't-Do
Reviewer's own assessment: "No finding" — `"Trivia"` is not in `_RESERVED_CLASS_NAMES`; the fragility requires a hypothetical future edit. Accept.

### errhandling-5 — Won't-Do
Reviewer's own assessment: "Not a finding; the propagation is correct" — `from exc` preserves `__cause__`. Accept.

### errhandling-6 — Won't-Do
Reviewer's own assessment: "Correctly handled. Not a finding." Accept.

### correctness-2 — Fixed
Claim: submodule `__name__` stayed leaf-only (`"cst"`), breaking the `sys.modules[k].__name__ == k` invariant; `importlib.reload` and `import_module(mod.__name__)` round-trips misresolve. Reviewer specified the fix must come after `add_submodule` (pyo3 derives the attribute name from the current module name).
Code: py_module.rs:108 — `sub.setattr("__name__", &qualified_name)?` placed after `add_submodule` (line 103-107) and before the `sys.modules` insert (line 114), exactly per the constraint.
Assessment: correct fix, correct ordering. Accept.

### test-1 — Fixed
Claim: `test_parser_apply_result_rules_accepted` only asserted construction; design §4 item 2 requires source-content checks in both cst and parser output.
Code: tests/test_gsm2tree_rs.py — test now calls `gen.generate()` and asserts `name = "Parser"` / `name = "ApplyResult"` in cst source; new `test_source_text_rule_cst_class_name_in_source` asserts `name = "SourceText"`. fltk/fegen/test_gsm2parser_rs.py — new `test_parser_apply_result_grammar_rules_coexist_with_fixed_pyclass_names` asserts the fixed machinery names survive in parser source. All pass.
Assessment: covers every element of the finding (cst handle, parser coexistence, source_text positive case). Accept.

### test-2 — Fixed
Claim: no `sys.modules` assertions for `fltk._native.poc_cst` / `fegen_cst`; attribute traversal masks a missing key.
Code: tests/test_module_split.py — `test_sys_modules_poc_cst` and `test_sys_modules_fegen_cst` assert key presence and identity (`is`). `sys` imported at line 13. Pass.
Assessment: accept.

### test-3 — Fixed
Claim: no three-distinct-segment unit case for `user_facing_name`.
Code: py_module.rs:149-150 — `"fltk._native.sub"` and `"a.b.c"` added to `different_segments_unchanged`. cargo test: 28 passed.
Assessment: accept.

### test-4 — Fixed
Claim: `if parser_child is not None:` guard made the isinstance check vacuous-pass capable.
Code: tests/test_module_split.py:121-123 — unconditional `assert parser_child is not None, "expected maybe_p() to return a Parser node for input 'foo'"` plus rationale comment. Pass.
Assessment: accept.

### test-5 — Fixed
Claim: `NodeKind` presence in `poc_cst` untested.
Code: tests/test_module_split.py — `test_poc_cst_has_node_kind`. Pass.
Assessment: accept.

### quality-1 — Fixed
Claim: gen-rust-cst help text lacked the lib.rs wiring snippet design §2.3 required.
Code: fltk/fegen/genparser.py:309-318 — snippet added after the submodule-placement sentence. Note: the snippet uses the implemented two-arg-plus-closure `register_submodule(m, "cst", ...)` signature, not the design's four-arg form — correct, since the snippet must match the shipped API.
Assessment: accept.

## Disputed items

- **correctness-1 / TODO(register-submodule-non-maturin)**: fails rubric Q2 — the fix is specified in the TODO entry itself and matches the design's original §2.2 API — and the false-positive is iteration-created (heuristic introduced on this branch), which bars silent deferral. Need: implement the explicit-parent-name override (`register_submodule_with_parent_name` or `Option<&str>` per the responder's own TODO text) with a unit test, remove the TODO comment and TODO.md entry — OR escalate with a concrete reason this requires owner/design input that the TODO entry's own fix-spec does not already resolve.

## Approved

13 findings: 8 Fixed verified, 4 Won't-Do sound (all reviewer-self-classified non-findings), 1 N/A.
(Count detail: errhandling-1/2, correctness-2, test-1/2/3/4/5 Fixed; errhandling-3/4/5/6 Won't-Do.)

---

## Verdict: REWORK

One disposition wrong (correctness-1 TODO; do-now under the rubric). Round 1.
