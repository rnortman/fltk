# Efficiency review — parse depth limit (ef315be..d442f56)

No findings.

Hot-path additions examined and accepted: the `apply` guard adds two `state(parser)`
projections, one compare, and an inc/dec per rule application — noise next to the
HashMap hash/lookup already in `apply_inner` (memo.rs); counting cache hits and the
non-`#[inline]` `apply`/`apply_inner` split are deliberate design choices (§1, frame
budget in §6) with negligible cost. Per-rule Python bindings add one bool read per
Python-level call; the `format!` allocation is error-path only. Test inputs are built
linearly; no quadratic construction, no redundant I/O, no new unbounded state (depth
counter is a `u32`; memo caches were already unbounded pre-change).
