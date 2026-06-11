# Judge verdict — pre-pass

Phase: pre-pass. Base ef315be..HEAD d442f56. Round 1.
Notes: 2 reviewer files (slop: 3 findings; scope: no findings).

Style: concise, precise, complete, unambiguous. No padding, no preamble.

## Added TODOs walk

None — no TODO dispositions.

## Other findings walk

### slop-1 — Fixed
Claim: `PackratState` doc comment claimed "per-field public accessors are the only external construction/mutation path" while `max_depth` is `pub`; consequence is an encapsulation claim the code does not deliver.
Diff at `memo.rs:70-77` (HEAD): comment rewritten to "`invocation_stack` and `max_depth` are `pub` for direct access; all other fields are private. `Default` (manual ...) is the only construction path — struct-literal construction is impossible, so adding private fields never breaks existing callers." The inaccurate accessor-only claim is gone; the remaining claims (private fields, no struct-literal construction, additive-field safety) match the declaration. Keeping `max_depth` `pub` is design-conformant (design §1 specifies `pub max_depth`); the finding itself offered the comment fix as the simpler valid option.
Assessment: fix addresses the consequence at the named location. Accept.

### slop-2 — Fixed
Claim: T4's "~4 more entries" comment was unverified approximation; consequence: T4 is the only test pinning the §2 truncated-Some premise and could silently go vacuous on refactor.
Diff at `tests/memo_toy.rs` T4 (`test_depth_limit_t4_some_with_flag`): explicit depth accounting added (seed needs depth ≤2; growth chain `apply__nest_sum` → cache-hit re-entry → `apply__nest` at pos 2/3/4 → guard fires at the 4th `apply__nest` entry; `(((9)))` needs depth ≥5 from pos 2) plus `assert!(pos < 9, ...)` distinguishing "growth stalled at seed" from "fully parsed."
Independent verification: traced the guard (`depth >= max_depth` checked before increment). Entries: nest_sum→1; growth nest chain enters at depths 2,3,4; the 4th `apply__nest` (pos=5) sees depth=4 ≥ 4 and is rejected. The comment's "guard fires at the 4th apply__nest entry" is correct; full parse would need 5 concurrent slots, so "needs depth≥5" is correct. The arrow-chain labels depth-after-increment, mildly compressed at the final arrow, but the accounting is substantively right and the `pos < 9` assertion — the anti-vacuousness mechanism the finding asked for — is present (growth success would land pos=9 and fail it).
Assessment: both halves of the suggested fix implemented; accounting checks out. Accept.

### slop-3 — Fixed
Claim: T3's cache-clear comment didn't explain that stickiness is proven by the `depth_exceeded()` assertion, not by `result.is_none()`; consequence: test looks weaker than it is.
Diff at `tests/memo_toy.rs` T3 (`test_depth_limit_t3_sticky`): comment now reads "Stickiness is proven by `depth_exceeded()` remaining set on the last assert — not by `result` alone (a cached-Failure hit would also return `None`, so `result` alone is insufficient)." Matches the finding's requested clarification.
Assessment: readability fix delivered as specified. Accept.

### Scope reviewer
`notes-prepass-scope.md`: "No findings." Nothing to adjudicate.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED
