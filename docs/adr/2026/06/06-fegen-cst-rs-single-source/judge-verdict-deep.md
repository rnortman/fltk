# Judge verdict — deep review

Style note: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base ce8b8f2..HEAD 431f7a7. Round 1.
Notes: 7 reviewer files; 1 finding total (reuse-1). Six reviewers (correctness, errhandling, security, test, quality, efficiency) report no findings; correctness, test, and efficiency document substantive null-result verification (byte-identical include target, 123 tests pass not skip, no new runtime paths), consistent with the diff I inspected (6,858-line copy → one-line `include!`, duplicate `gencode` step removed).

## Added TODOs walk

### reuse-1 — TODO(preamble-helpers-into-cst-core) at fltk/fegen/gsm2tree_rs.py:131
Bookkeeping verified in diff: `TODO.md` entry `## preamble-helpers-into-cst-core` added with concrete description and locations; `TODO(preamble-helpers-into-cst-core)` comment added at `gsm2tree_rs.py:131` (`_preamble()`). Slug matches in both places.

Q1 (worth doing): yes — the helper block (`FLTK_NATIVE_SPAN_TYPE`, `extract_span`, `get_span_type`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`, `get_source_text_type`) is emitted byte-identically into three committed files (`src/cst_fegen.rs:8-75`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`), and the surface grows per grammar; a preamble fix propagates only on explicit regeneration. The reviewer's consequence is real.

Q2 (design/owner input required): yes —
- The block contains `unsafe { obj.downcast_unchecked::<Span>() }` whose SAFETY comment (`src/cst_fegen.rs:26-35`) documents a memory-corruption failure mode under rlib version skew. Relocating it into `fltk-cst-core` changes where that invariant is stated and enforced relative to the cdylibs that rely on it (rlib statics are duplicated per linking cdylib — the "single definition at link time" claim in the TODO entry itself needs design-stage scrutiny).
- It interacts with the open `span-source-as-py-crosscdylib` TODO, which proposes adding an `extract_source_text` helper to this same preamble; whether new helpers land in the preamble or in core is one coordinated decision, not two independent edits.
- It changes `fltk-cst-core`'s public Rust surface and the content of all committed generated files — generated output is public API for out-of-tree consumers per CLAUDE.md, so this is a deliberate, called-out decision, not a do-now.
- It is squarely outside this iteration's request-fixed scope (build-wiring only, generator explicitly out of scope per `design.md` "Edge cases": "The generator (`gsm2tree_rs.py`) is not in scope to change").

Created/worsened this iteration? No — pre-existing (preamble emission predates ce8b8f2; this diff touched no preamble logic and *removed* one duplicated copy). The cannot-silently-defer rule does not apply.

Phase signal: one TODO, not a pile.

Assessment: both rubric answers yes; TODO acceptable.

## Other findings walk

None — reuse-1 is the only finding across all seven notes files; no Fixed or Won't-Do dispositions exist.

## Approved

1 finding: 1 TODO acceptable.

---

## Verdict: APPROVED

Sole disposition is a rubric-passing TODO with correct bookkeeping; all other reviewers report no findings, and their null results are consistent with the diff.
