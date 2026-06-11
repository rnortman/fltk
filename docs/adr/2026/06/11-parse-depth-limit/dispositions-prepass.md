## Dispositions: prepass round 1

### slop-1

- Disposition: Fixed
- Action: `memo.rs:72-77` — rewrote `PackratState` doc comment to accurately say `invocation_stack` and `max_depth` are `pub` and that private-field immutability is the safety property (not "all mutable access via accessors"). Removed the inaccurate "per-field public accessors are the only external construction/mutation path" claim.
- Severity assessment: Doc mismatch with actual visibility; no functional bug. Would have caused reviewer confusion on auditing the encapsulation claim against the `pub` field.

---

### slop-2

- Disposition: Fixed
- Action: `tests/memo_toy.rs:548-556` — replaced the vague "~4 more entries" comment with explicit depth accounting for the growth iteration (5 entries, showing why depth=4 fires at the 4th `apply__nest` call). Added `assert!(pos < 9, ...)` to distinguish "growth stalled at seed" from "nest_sum fully parsed."
- Severity assessment: T4 is the only test pinning the §2 truncated-Some premise. An imprecise comment risked the test silently becoming vacuous on future refactors; the explicit accounting and partial-consume assertion make the invariant self-evident.

---

### slop-3

- Disposition: Fixed
- Action: `tests/memo_toy.rs:522-524` — replaced the single-line cache-clear comment with an explanation that stickiness is proven by `depth_exceeded()` remaining set, not by `result.is_none()` (which a cached-Failure hit would also produce).
- Severity assessment: Readability only; test logic was correct. Without the clarification a careful reader would wonder if the test actually exercised stickiness or just cache behavior.
