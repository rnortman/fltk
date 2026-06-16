# Judge verdict — prepass

Phase: prepass (code + design reconciliation). Base 8cd6232..HEAD b6c0aac. Branch `span-line-col-api`. Round 1.
Notes: slop (no findings) + scope (3 findings). Dispositions: 3 Fixed.

## Added TODOs walk

This phase added two `TODO(slug)` items. scope-1 dispositions the *missing `TODO.md` entries*, not the TODOs themselves, but the rubric is applied here to confirm the TODOs are acceptable deferrals (not lazy-responder cover).

### TODO(linecol-cache-consolidate) — TODO.md:62, comments at terminalsrc.rs:167,178 and span.rs:53
Q1 (worth doing): yes — this change created the duplicated state. `TerminalSource.line_ends` and the new `SourceInner.line_ends` are two line-ends tables over the same immutable text; consolidation removes one. Adjacent and real.
Q2 (design/owner input required): yes — pointing `TerminalSource::pos_to_line_col` at `&self.source.inner.line_ends` touches the parser-core/cst-core crate boundary and the public `pos_to_line_col` caching contract; it is a cross-crate refactor, not a one-liner. Defer is legitimate.
Furthermore-clause check: this iteration *created* the duplicate state, so it cannot be *silently* deferred — but it is not silent: it is documented in design §7 item 2 as a consciously-accepted compromise and carries the full two-piece TODO record (entry + three comments). Surfaced, not hidden. Acceptable.

### TODO(py-span-linecol-cache) — TODO.md:66, comment at terminalsrc.py:133
Q1 (worth doing): yes — Python `Span.line_col()` recomputes the O(N) scan per call (the frozen-slots span can't reach a cache). Concrete, "done is obvious."
Q2 (design/owner input required): yes — caching requires threading a `_line_ends` cache on `SourceText` through `with_source`; the design (§7 item 1) judged the plumbing non-trivial for a cold (error-reporting) path. Genuine design work, not a do-it-now.
Furthermore-clause check: the per-call recompute is a *new* cost introduced by adding `Span.line_col()` to the Python backend, so the iteration created it — but again it is surfaced in design §7 with a paired TODO record, not silently deferred. Cold path; performance-only (correctness identical per exploration-codepoint-efficiency §4). Acceptable.

Neither TODO is a one-line/single-file mechanical change the responder could have done now; both are genuinely design-cycle-gated and both are surfaced in the design. No pile signal (two TODOs, both intrinsic to the accepted-compromise list).

## Other findings walk

### scope-1 — Fixed
Claim: `TODO.md` has no entries for `linecol-cache-consolidate` / `py-span-linecol-cache`; design §7 + CLAUDE.md "TODO System" mandate paired entries, else the code comments are orphaned and the burndown audit has nothing to join against. Consequence stated (orphaned comments, audit-join failure) — process-real.
Disposition: Fixed. Added both entries to `TODO.md` after `extend-children-owned`.
Evidence: `git diff` on `TODO.md` shows both `## \`linecol-cache-consolidate\`` (line 62) and `## \`py-span-linecol-cache\`` (line 66) added, each naming concrete follow-up, deferral rationale, and code location. Code-side join targets confirmed present: `TODO(linecol-cache-consolidate)` at `terminalsrc.rs:167,178` and `span.rs:53`; `TODO(py-span-linecol-cache)` at `terminalsrc.py:133`. Both halves of the two-piece convention now exist.
Assessment: fix addresses the consequence; slugs join. Accept.

### scope-2 — Fixed
Claim: `pos_to_line_col` sentinel changed from `len-1` to `len` (Python + Rust), but design §2.5 / §2.4 / §2.12 said the legacy path is "unchanged"/"left untouched", and `test_span.py:392-393` carried a stale "legacy uses `len-1`" comment. Consequence: undocumented behavioral change (last char of a trailing-newline-less line now included in `line_span`) and a stale record. The note itself judged the *fix* correct and asked for the *record* to be reconciled.
Disposition: Fixed (record reconciliation; sentinel value accepted as the correct bug fix).
Evidence (three sites, all verified):
1. `test_span.py` — the added `test_line_col_parity_*` block reads "Both implementations now use sentinel = len (exclusive past-end) for the final line"; the flagged stale "legacy uses `len-1`" wording is not in the committed file. Diff confirms the corrected block is new, not pre-existing.
2. design §2.5 note 3 (lines 251-256) — now states "Its observable behavior is unchanged **except for one intentional bug fix**: the sentinel for the final line changes from `len - 1` to `len`", calling it a latent-bug correction required for parity.
3. design §2.4 (lines 209-211) and §2.12 (§5 lines 821-824) — "unchanged"/"left untouched" now carry the sentinel-correction exception.
Cross-check: the actual code matches — `span.rs:232-236` pushes `len` for non-empty text (not `len-1`), and `test_span.py` asserts `line_span.end == 11` for `"hello\nworld"`. Record now matches behavior on all three sites.
Assessment: the bug fix is correct (old sentinel truncated the last char); reconciliation is complete and accurate at every named site. Accept.

### scope-3 — Fixed
Claim: `span.rs:209` docstring said the bisect "stores codepoint indices of `\n` plus a final sentinel of `len - 1`", but the code at lines 233-235 pushes `len`. Consequence: a reader of the public `resolve_line_col` doc expects `line_span.end == len-1` but gets `len` — documentation hazard.
Disposition: Fixed. Updated the docstring.
Evidence: `span.rs:209-211` now reads "final sentinel equal to `len` (exclusive end of the last line) for non-empty text without a trailing `\n`, or `-1` for empty input", which matches the code at lines 232-236 (`push(if len > 0 { len } else { -1 })`). The accurate inline comment at lines 224-231 is unchanged, as the disposition stated.
Assessment: docstring now describes the sentinel the function actually pushes. Accept.

## Approved

3 findings: 3 Fixed verified. 2 added TODOs acceptable (both design-cycle-gated, both surfaced in design §7 with paired TODO.md entries + code comments).

---

## Verdict: APPROVED

All three scope dispositions are Fixed and verified at their named sites (TODO.md entries added with joinable slugs; sentinel record reconciled across test/design; `resolve_line_col` docstring corrected). The two TODOs this phase introduced both pass the two-question rubric (worth doing + require a design cycle) and are surfaced — not silently deferred — in design §7 with the full two-piece TODO record. No slop findings. No disputed items.
