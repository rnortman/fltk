# Judge verdict — deep review

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: deep. Base d2abc80..HEAD 9e621d9. Round 1.
Notes: 7 reviewer files (security, efficiency: no findings); 13 dispositions (2 duplicate pairs: errhandling-1≡correctness-1, reuse-1≡quality-1).
Verification basis: `git diff 4f66083..9e621d9` (fix commits 0196f06, 9e621d9), code inspection at HEAD, targeted test run (22 passed: ReservedClassName + CrossRule + prediction tests).

## Added TODOs walk

### correctness-3 — TODO(empty-cn-underscore-rule) at gsm2tree_rs.py:18-21
Q1 (worth doing): yes — underscore-only rule names (`_`, `__`) pass `_IDENTIFIER_RE` but `snake_to_upper_camel` collapses them to CN `""` (documented contract, `fltk/fegen/naming.py:13-15`), emitting `pub struct  {` — uncompilable Rust with no generation-time diagnostic; same silent-bad-output class this change targets.
Q2 (design/owner input required): yes — `_IDENTIFIER_RE` deliberately mirrors the language grammar's identifier rule (`fegen.fltkg:16`: `/[_a-z][_a-z0-9]*/`), which admits `_`; tightening the regex desyncs generator validation from the grammar spec, and the empty-CN problem also afflicts the Python backend (same `snake_to_upper_camel`), so where to enforce (grammar spec, gsm-level validation, per-backend CN check) and cross-backend consistency is a design decision, not a mechanical edit.
Not created/worsened by this iteration: the uncompilable output pre-exists d2abc80; reviewer itself marked it "pre-existing; adjacent" and endorsed a TODO.
Both halves present: `TODO(empty-cn-underscore-rule)` comment at the relevant site + `TODO.md` entry with slug, description, location (verified in 9e621d9 diff).
Assessment: TODO acceptable.

## Other findings walk

### errhandling-1 / correctness-1 — Fixed (duplicate findings, one fix)
Claim: `EqWorklistItem` emitted by `_eq_block` under the same conditions as `DropWorklistItem` but absent from `_RESERVED_CLASS_NAMES`; rule `eq_worklist_item` → silent Rust E0428.
Diff (0196f06): `"EqWorklistItem": "the generated EqWorklistItem eq-worklist enum"` added to the dict; `("eq_worklist_item", "EqWorklistItem", "EqWorklistItem")` added to `TestReservedClassNameRejection` parametrize. Test passes. The name satisfies the Py/Child/Label invariant (no `Py` prefix, no `Child`/`Label` suffix), so no claims-dict seeding needed — consistent with the design's recorded constraint.
Assessment: fix complete. Accept.

### errhandling-2 — Fixed
Claim: `.get()` + `is not None` guard in the claims loop is dead defensiveness today and a silent false-negative under a future sparse-`rule_models` refactor.
Diff (0196f06): `model = self._py_gen.rule_models[rule.name]` with invariant comment; guard reduced to `if model.labels:`. KeyError now surfaces invariant violations instead of silently skipping the `{CN}Label` claim — exactly the reviewer's prescribed fix.
Assessment: accept.

### correctness-2 — Fixed
Claim: module-level Py/Child/Label invariant guard was a bare `assert`, compiled out under `python -O`, while the design's no-seeding decision depends on it.
Diff (9e621d9): replaced with `_bad_reserved = [...]` / `if _bad_reserved: raise RuntimeError(...)` naming the offending entries and the remediation. Survives `-O`.
Assessment: accept. (Disposition cites lines 56-65; actual location ~50-58 at HEAD — immaterial.)

### reuse-1 / quality-1 — Fixed (duplicate findings, one fix)
Claim: three inline `f"Py{...}"` emission sites (727, 757, 2186) left after `py_handle_name` was declared single source of truth.
Diff (0196f06): all three converted to `self.py_handle_name(child_cls)` / `self.py_handle_name(class_name)` in `_child_enum_block` (to_pyobject, extract_from_pyobject) and the module-init registration block. `git grep` of the post-fix diff shows no remaining inline `f"Py{` emission interpolations in those paths.
Attribution note: dispositions credit reuse-1 to 9e621d9 and quality-1 to 0196f06 for the same edit; the edit is in 0196f06. Bookkeeping slip only; fix verified at HEAD.
Assessment: accept.

### reuse-2 — Fixed
Claim: `_make_two_rule_grammar`'s inner `_make_rule` duplicated `_make_single_rule_grammar`'s body; silent drift risk.
Diff (0196f06): `_make_single_rule_grammar` gained `labeled: bool = True` keyword; `_make_two_rule_grammar` now composes two single-rule grammars and merges rules/identifiers; inner helper deleted.
Assessment: accept.

### quality-2 — Fixed
Claim: drift test reached into `gen._py_gen.*` and `_label_enum_rust_name` (private internals); delegation refactor would silently break the primary drift guard.
Diff (0196f06): `label_enum_name` exposed as public static (with `_label_enum_rust_name` kept as thin deprecated alias for internal call sites); `class_name_for_rule` and `rule_has_labels` added as public instance wrappers; `test_prediction_vs_output_consistency` rewritten using only public surface (`gen.class_name_for_rule`, `gen.rule_has_labels`, `RustCstGenerator.child_enum_name/py_handle_name/label_enum_name`).
Assessment: accept. (Residual: internal sites still call the deprecated alias — alias delegates to the public name, so no drift surface; not a blocker.)

### test-1 — Fixed
Claim: drift test predicted the handle name via inline `f"Py{cn}"`, hollowing the formula-drift guard for the handle family.
Diff (0196f06): `py_handle = RustCstGenerator.py_handle_name(cn)` at the assertion site, with comment stating the rename-propagation intent.
Assessment: accept.

### test-2 — Fixed
Claim: collision tests never asserted family-description strings or the "rename" action hint.
Diff (0196f06): foo/foo_child test asserts `"child value enum"`, `"node struct"`, `"rename"`; foo/foo_label asserts `"label enum"`; foo/py_foo asserts `"Python handle struct"` — one assertion per family, as the finding prescribed.
Assessment: accept.

### test-3 — Fixed
Claim: no test for ≥3 claimants on one identifier; truncation regression undetectable.
Diff (0196f06): `test_three_way_collision_all_claimants_reported` — `foo_bar`/`foo__bar`/`foo___bar` all CN `FooBar`; asserts all three rule names in the error. Passes.
Assessment: accept.

### test-4 — Fixed
Claim: auto-generated trivia annotation only tested for the CN family, not derived-identifier collisions.
Diff (0196f06): `test_trivia_child_rule_collides_with_auto_trivia_child_enum` — single rule `trivia_child`, asserts `TriviaChild`, `trivia_child`, and the auto-generated annotation (`"auto"` case-insensitive). Exercises the annotation path for the child-enum family.
Assessment: accept. (Asserting `"auto"` is looser than the full annotation string, but combined with the existing CN-family trivia tests that assert exact annotation text, coverage of the finding's stated bug — annotating only CN claims — is real.)

## Disputed items

None.

## Approved

13 dispositions (11 distinct findings after dedup): 12 Fixed verified, 1 TODO acceptable.

---

## Verdict: APPROVED

All Fixed dispositions verified against the 4f66083..9e621d9 diff and passing tests; the single TODO passes both rubric questions (pre-existing, cross-backend/grammar-spec design decision) with comment + TODO.md entry in place. Round 1.
