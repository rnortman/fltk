# Dispositions — design review round 1, Phase 1 `fltk-parser-core` runtime crate

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Findings from `notes-design-design-reviewer.md`. Each fact-checked against design.md, errors.py, terminalsrc.py, and the controlling design before disposition.

design-1:
- Disposition: Fixed
- Action: Verified — design §2.5 declared `recursions` private with no constructor anywhere, and §4 item 1's `tests/memo_toy.rs` is an integration test outside the crate, so the spec as written could not compile its own test plan; `ErrorTracker`'s `-1` invariant (errors.py:26) had no encoding point. Added `impl Default for PackratState` (empty stack/map, noted as the only external construction path, used by the toy test and Phase 2 `Parser::new`) in §2.5, and `impl Default for ErrorTracker` (`longest_parse_len: -1`, empty context; invariant encoded once) in §2.4.
- Severity assessment: Real blocker if unfixed — Phase 1's own integration test cannot construct `PackratState`, and Phase 2's generated constructor would force ad-hoc unspecified API invention; the `ErrorTracker` half is a latent correctness trap (`-1` invariant re-stated at every construction site).

design-2:
- Disposition: Fixed
- Action: Verified — errors.py:64-70 iterates a `defaultdict(set)`; `ParseContext` hashes via str/enum hashing, so within-rule line order is `PYTHONHASHSEED`-dependent, exactly as design §2.4 itself analyzes. §4 item 3 indeed specified Python-captured byte-golden strings for multi-token-per-rule cases without acknowledging this. Added the ordering constraint to §4 item 3: byte-equality goldens restricted to ≤1 distinct token per rule group; ≥2-token cases assert header + rule-group order byte-exactly and within-rule lines as an unordered set (same comparator rule §2.4 prescribes for Phase 3).
- Severity assessment: Without the constraint, golden expectations are unstable at capture time and/or fail against correct Rust output — a flaky or falsely-failing test suite contradicting the design's own analysis.

design-3:
- Disposition: Fixed
- Action: Verified against terminalsrc.py:168-175 — `pos + literal_len > terminals_len` does not reject negative `pos`, and `self.terminals[pos + i]` wraps, so Python's `consume_literal(-1, <last char>)` succeeds with `Span(-1, 0)` and an empty literal at `pos = -5` yields `Span(-5, -5)`. Rewrote the §2.3 parity sentence: exact-match claim now scoped to `pos >= 0`, empty-literal case stated as `0 <= pos <= len`, and the `pos < 0 → None` behavior called out as a deliberate divergence from Python's negative-index wrapping (unreachable from generated code; cross-backend differential tests must restrict to `pos >= 0`). Cross-referenced from the §3 negative-`pos` bullet and counted in §5's judgment-call list.
- Severity assessment: Spec ambiguity (two contradictory sentences three lines apart) plus a false parity claim that would produce spurious mismatches for anyone differential-testing `consume_*` at negative positions; behavior choice itself was already correct.

All three findings Fixed; no TODOs, no Won't-Dos. Edits were localized (constructor specs, one sentence rewrite, one test-plan constraint) — cleanup-editor not re-invoked.
