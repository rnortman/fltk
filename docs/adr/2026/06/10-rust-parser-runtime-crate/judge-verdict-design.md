# Judge verdict — design review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: design. Doc: `docs/adr/2026/06/10-rust-parser-runtime-crate/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings. Doc phase — no TODO walk.

## Findings walk

### design-1 — Fixed
Claim: `PackratState` has a private `recursions` field and no specified constructor, so §4 item 1's external integration test (`tests/memo_toy.rs`) and Phase 2's generated `Parser::new` cannot construct it; `ErrorTracker`'s `-1` initial-value invariant (errors.py:26 — verified: `longest_parse_len: int = -1`) has no single encoding point. Consequence: test plan doesn't compile as written; Phase 2 blocked or invents unspecified surface.
Severity: blocker — the design's own §4 test plan is unimplementable against the specified API.
Evidence in doc: §2.5 now specifies `impl Default for PackratState` (empty stack/map), explicitly noting it is the only external construction path because `recursions` is private and the toy test is an integration test outside the crate, and that "`Default` ships in the §2.1 public surface alongside the type" — satisfying the reviewer's API-inventory ask, since `Default` is an inherent impl that travels with the re-exported type. §2.4 now specifies `impl Default for ErrorTracker` (`longest_parse_len: -1`, empty context) with the invariant encoded once.
Assessment: fix addresses both halves of the finding at the named sections. Accept.

### design-2 — Fixed
Claim: §4 item 3 specified Python-captured byte-golden strings for `format_error_message` including multi-token-per-rule cases, contradicting §2.4's own analysis that Python's within-rule line order is `PYTHONHASHSEED`-dependent (`defaultdict(set)` iteration, errors.py:64-70) while Rust uses deterministic first-occurrence order. Consequence: goldens unstable at capture or falsely failing against correct Rust output.
Severity: should-fix — test plan internally inconsistent; would produce flaky/false-failing tests.
Evidence in doc: §4 item 3 now carries the ordering constraint verbatim per the suggested fix: byte-equality goldens restricted to at most one distinct token per rule group; ≥2-token cases assert header + rule-group order byte-exactly and within-rule lines as an unordered set, explicitly tied to §2.4's Phase 3 comparator rule.
Assessment: constraint stated where the reviewer asked, consistent with §2.4. Accept.

### design-3 — Fixed
Claim: §2.3 claimed `consume_literal` "matches Python exactly" and the empty-literal sentence (`pos <= len → Some`) literally included negative `pos`, contradicting the validity contract three lines earlier; Python actually wraps negative indices (verified: terminalsrc.py `pos + literal_len > terminals_len` does not reject negative `pos`; `self.terminals[pos + i]` wraps). Consequence: implementer ambiguity and spurious cross-backend differential-test mismatches.
Severity: should-fix — internal contradiction plus false parity claim; the behavior choice itself was already correct.
Evidence in doc: §2.3 now scopes the exact-match claim to `pos >= 0`, restates the empty-literal case as `0 <= pos <= len`, and calls out `pos < 0 → None` as a deliberate divergence from Python's negative-index wrapping with the concrete Python examples (`Span(-1, 0)`, `Span(-5, -5)`), plus the differential-testing restriction to `pos >= 0`. Cross-referenced from the §3 negative-`pos` bullet; counted in §5's judgment-call list ("rejecting negative `pos` instead of Python's index wrapping (§2.3)").
Assessment: both ambiguity and false claim resolved; divergence is now a recorded deliberate decision. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All three dispositions verified against the revised design and the Python source. No TODOs, no Won't-Dos, nothing disputed.
