# Judge verdict — requirements phase

Phase: requirements. Doc: `docs/workflow/rust-unparser-backend/requirements.md`. Round 1.
Notes: 1 reviewer file (`notes-requirements-requirements-reviewer.md`); 3 findings.
User directive (`notes-requirements-user.md`, per reviewer): full formatting pipeline must be reproduced — treated as binding.

## Other findings walk

### requirements-1 — Fixed
Claim: refined doc stated *new* unparser artifacts as settled requirements — crate `fltk-unparser-core` under `crates/` with prescribed decomposition, CLI subcommand `gen-rust-unparser`, `LibSpec` `with_unparser` param, workspace member, fixture. Exploration Open Questions #4/#5 list subcommand shape and LibSpec extension as undetermined; the request only constrains "the pattern is the same." Consequence: designer treats crate name/boundary/subcommand/param as fixed and skips evaluating alternatives. Reviewer's own mitigating factor: existence of analogous artifacts is fair enrichment; only naming/structure stated *as settled* intrudes on design.
Evidence in current doc:
- Runtime-library bullet (line 29): name dropped; now "analogous to how `fltk-parser-core` (under `crates/fltk-parser-core/`)..." (the parser's real crate, legit context) and closes with an explicit deferral — "The exact crate name, boundaries, and internal decomposition are design decisions."
- Build-system section: `gen-rust-unparser` gone → "analogous CLI and Makefile integration" (line 71); `with_unparser` gone → "wired into this mechanism" (line 73); workspace → "will need to fit into this workspace structure" (line 75).
- Residual: line 40 still reads "The analogous `fltk-unparser-core` crate would live under `crates/` and provide the grammar-independent `Doc` combinator types, the accumulator/builder, the spacing-resolution logic, and the renderer." So the disposition's literal claim ("removed `fltk-unparser-core`") is overstated — one hedged mention remains, naming the crate, its location, and a one-crate decomposition.
Assessment: Accept. The finding's consequence is the designer treating name/boundary/decomposition as fixed; line 29 *explicitly* states these are design decisions, and the two most settled-sounding items (subcommand, lib param) are fully removed. The lone residual (line 40) is hedged with "would" — the same conditional framing the reviewer itself quoted approvingly from the exploration ("a `fltk-unparser-core` crate **would be** a parallel new crate under `crates/`") and treated as the acceptable baseline. The component list it names (Doc combinators, spacing resolution, renderer) is the user-mandated formatting pipeline, so naming the *functionality* is enrichment, not design dictation. A designer reading the whole doc cannot reasonably believe the name/boundary is pre-decided given line 29's explicit deferral. Consequence neutralized; the disposition's prose slightly overclaims but the outcome is sound.

### requirements-2 — Fixed
Claim: "produce equivalent `Doc` trees" resolved the *representation* half of exploration Open Question #1 (output type undetermined), pinning the internal IR — a design call. Reviewer rated this minor (reproducing the pipeline naturally wants a Doc-like IR anyway). Consequence: designer assumes a literal `Doc` enum is mandated.
Evidence in current doc: line 11 now reads "The Rust unparser must reproduce all of this formatting behavior -- producing strings directly without the formatting pipeline is not acceptable. The Python implementation's `Doc` combinator tree, spacing resolution, and Wadler-Lindig renderer are the reference for what the Rust side must achieve; the exact internal representation is a design decision." Line 27 changed "produces a Doc tree from it" → "produces formatting output from it."
Assessment: Accept. Behavior (full pipeline, per binding user directive) is preserved; representation is explicitly deferred to design at the named locations. Matches the reviewer's suggested fix exactly.

### requirements-3 — Fixed
Claim: overall/big-picture — positive assessment; no defect. The one weakness flagged (artifact naming crossing into design) is the requirements-1 concern.
Evidence: validation finding, not a defect; its only substantive concern is subsumed by requirements-1, which is addressed.
Assessment: Accept. Nothing to fix beyond requirements-1; "no additional changes" is the correct disposition.

## Approved

3 findings: 3 Fixed verified (requirements-1 substantially, residual line-40 mention hedged and non-binding given line 29's explicit deferral; requirements-2 fully; requirements-3 validation only).

---

## Verdict: APPROVED

All three dispositions acceptable. requirements-2 and requirements-3 fully resolved. requirements-1's fix neutralizes the finding's consequence — crate name, boundaries, and decomposition are explicitly declared design decisions (line 29), and the prescriptive subcommand/lib-param items are removed; the single residual mention of `fltk-unparser-core` (line 40) is hedged "would"-language consistent with the exploration's own accepted framing and does not lock the designer in. The disposition's "removed the name" phrasing overstates slightly, but the requirements doc no longer dictates design — which is the bar.
