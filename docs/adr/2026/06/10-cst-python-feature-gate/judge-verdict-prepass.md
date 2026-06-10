# Judge verdict — prepass

Style: concise, precise, no padding. Audience: smart LLM/human.

Phase: prepass (code). Base e6a9117..HEAD 431ab53. Round 1.
Notes: notes-prepass-slop.md (3 findings), notes-prepass-scope.md (0 findings). Dispositions: dispositions-prepass.md.

## Added TODOs walk

No TODO dispositions; no `TODO(` lines added in the diff range (grep-verified).

## Other findings walk

### slop-1 — Fixed
Claim: generated `extend` methods emit error strings naming `.append:`; consequence is misleading diagnostics for downstream consumers debugging label-type errors.
Diff at 431ab53, `fltk/fegen/gsm2tree_rs.py`: `_label_from_pyobject_match` gains `method_name: str = "append"` parameter, used in both error-string arms (labeled and no-labels); the extend emitter passes `method_name="extend"`. Regeneration verified at HEAD: every node type in all four generated files (`crates/fltk-cst-spike/src/cst.rs`, `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`) now has paired `NodeName.append:` (in append) and `NodeName.extend:` (in extend) strings — e.g. spike cst.rs:281 vs 306. No residual `.append:` inside extend bodies. Generator tests do not pin the old strings (grep of `tests/test_gsm2tree_rs.py` shows no exact-string assertion on these messages), so no stale test.
Assessment: fix at root cause (generator) plus regeneration. Accept.

### slop-2 — Fixed
Claim: identical boilerplate comment blocks (`// Return a fltk._native.Span...`, `// span_to_pyobject: O(1) Arc clone...`) repeated at every span getter / to_pyobject Span arm across all generated files; consequence is review/diff noise.
Diff at 431ab53, `gsm2tree_rs.py`: both comment templates removed from the span-getter and `to_pyobject` Span-arm emitters. Grep at HEAD for `Return a fltk._native.Span` and `O(1) Arc clone` hits only docs/ADR prose, zero source files. All four generated files regenerated in the same commit.
Assessment: complete. Accept.

### slop-3 — Fixed
Claim: `crates/fltk-cst-core/src/lib.rs` comment references design-doc section numbering (`§4 item 2 from design`); consequence is comment rot and scaffolding residue.
Inspection of `lib.rs` at HEAD: line 57 reads `// Tests for the native (non-Python) Span API`; line 13 reads `// Pure-Rust GIL-free Span construction and equality tests.` Grep for `§` in lib.rs at HEAD: no hits. Disposition also covered the second §-reference (line 13) not explicitly demanded by the finding — exceeds the ask.
Assessment: complete. Accept.

### Scope reviewer
No findings; the notes affirmatively walk design §2.1–§2.8 and §4 against the diff and record one deviation (dual-cfg blocks instead of `cfg_attr` on enum variants, pyo3 0.23 attribute-validation constraint) as called out in the implementation log. Nothing to adjudicate.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable.
