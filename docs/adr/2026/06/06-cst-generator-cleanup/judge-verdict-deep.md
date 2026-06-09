# Judge verdict — deep review

Concise. Precise. No padding. Audience: smart LLM/human.

Phase: deep. Base 2dd27f0..HEAD 9d23e52. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, efficiency: no findings); 8 findings total.
Verified at HEAD: `tests/test_gsm2tree_py.py` 21/21 pass; ruff clean on changed files; repo-wide pyright 0 errors.

## Added TODOs walk

### reuse-1 — TODO(test-grammar-helpers-conftest) at tests/test_gsm2tree_py.py:23, tests/test_gsm2tree_rs.py:127
Q1 (worth doing): yes — duplicate zero-label boundary grammars in two files can drift and mask Python/Rust generator asymmetries; TODO.md entry is concrete.
Q2 (design/owner input required): no — the extraction is mechanical: move `_make_zero_label_grammar` / `_make_labeled_grammar` / `_make_generator` to a shared `tests/` helper module (the TODO.md entry itself names the two obvious homes) and update imports in both files. The only judgment call — which of two trivially-different grammar shapes to keep — is not a design cycle.
Furthermore: `tests/test_gsm2tree_py.py` is a **new file in this diff** (does not exist at 2dd27f0); the duplication was created by this iteration. Per rubric, a problem this iteration created cannot be silently deferred when it fails Q2.
Responder rationale ("cross-file refactor better handled as a standalone increment") is a sequencing/scope argument — the "not now" category, not "design work required" or "owner input needed."
Assessment: Q2 fails + iteration-created → do-now. Disposition wrong.

### reuse-2 — TODO(test-grammar-helpers-conftest) at tests/test_gsm2tree_rs.py:477
Q1: yes — inline `CstGenerator(grammar=..., py_module=..., context=...)` duplicates `_make_generator`; a constructor-signature change requires two edits.
Q2: no — folded into the same shared-helper move as reuse-1; once the helper module exists, this is a one-line replacement.
Assessment: same slug, same failure: do-now alongside reuse-1. Disposition wrong.

## Other findings walk

### test-1 — Fixed
Claim: `extend_children` uncovered on label-free nodes; a regression omitting or mis-annotating it would go undetected.
Evidence: `test_extend_children_present` at `tests/test_gsm2tree_py.py:178-188` asserts presence, `other: 'Foo'` forward-ref param, return annotation `None`. Passes at HEAD.
Assessment: matches the finding's prescribed fix exactly. Accept.

### test-2 — Fixed
Claim: magic-constant "first 10 stmts" check does not verify the structural invariant (`__all__` immediately after last import / TYPE_CHECKING block).
Evidence: rewritten `test_all_appears_near_top` at `tests/test_gsm2tree_py.py:361-398` locates `__all__` by index and asserts the preceding statement is `ast.Import`/`ast.ImportFrom` or a `typing.TYPE_CHECKING` `ast.If` (attribute-shape check matches `pygen.if_(pygen.expr("typing.TYPE_CHECKING"))` per the correctness reviewer's verification). Magic constant gone.
Assessment: encodes the contract the finding demanded. Accept.

### test-3 — Fixed
Claim: per-label quintet tests are presence-only; wrong return type for `child_<l>`/`maybe_<l>` from `_emit_label_quintet` would go uncaught.
Evidence: `test_child_name_return_annotation` (`:232-240`, asserts non-empty, not `typing.Optional[`-wrapped) and `test_maybe_name_return_annotation` (`:242-247`, asserts `typing.Optional[` prefix) using `_annotation_source` as suggested.
Assessment: slightly weaker than the finding's letter ("should equal the per-label child annotation" — exact equality not asserted), but the named regression class (Optional/bare swap in the extracted helper, the primary sub-task-C hazard) is pinned, and both quintet methods named in the consequence are covered. Accept.

### test-4 — Fixed
Claim: `concrete_body_for`'s `ValueError` guard (slop-1 fix) untested; typo in the string comparison or removed guard would go uncaught.
Evidence: `test_emit_label_quintet_unknown_method_raises` at `tests/test_gsm2tree_py.py:406-434` monkeypatches `_emit_label_quintet` to invoke the real production closure with `"nonexistent_method"` during `py_class_for_model`; asserts `ValueError` with "Unknown method". Exercises the production closure, not a reimplementation. Passes.
Assessment: guard verified by test as the finding required. Accept.

### quality-1 — Fixed
Claim: `body_for: Callable[[str, str], ...]` loses static checking of the closed five-method set; misspellings surface only as runtime `ValueError`.
Evidence: `fltk/fegen/gsm2tree.py:7` adds `Literal` import; `_emit_label_quintet` signature now `Callable[[Literal["append", "extend", "children", "child", "maybe"], str], list[ast.stmt]]` (`:558`). Annotation-only; repo pyright 0 errors. test-4's deliberate bad call carries `# type: ignore[arg-type]`, confirming pyright now flags unknown names.
Assessment: implements the finding's exact fix. Accept.

### quality-2 — Fixed
Claim: `pygen.stmt(f"__all__ = {public_names!r}")` is the sole repr-roundtrip site in the generator; fragile under non-identifier names, inconsistent with structural AST construction.
Evidence: `fltk/fegen/gsm2tree.py:523-531` now builds `ast.Assign(targets=[ast.Name("__all__")], value=ast.List(elts=[ast.Constant(name) ...]))`. Regenerated artifacts unchanged in this commit; all `__all__` tests pass.
Assessment: structural construction as prescribed. Accept.

## Disputed items

- **reuse-1 + reuse-2 / TODO(test-grammar-helpers-conftest)**: fails rubric Q2 (mechanical shared-helper extraction, no design cycle or owner input) and the duplication was created by this iteration (new file `tests/test_gsm2tree_py.py`). Need: perform the extraction now (shared `tests/` helper module + update both files, remove the TODO comments and TODO.md entry), OR escalate with a specific reason it requires design or owner input.

## Approved

6 findings: 6 Fixed verified, 0 Won't-Do, 0 TODOs acceptable.

---

## Verdict: REWORK

Two dispositions wrong (reuse-1, reuse-2 — single shared TODO that should be done now). Round 1.
