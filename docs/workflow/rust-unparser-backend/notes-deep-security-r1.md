# Security review — rust-unparser-backend batch 1 (deep, r1)

Commit reviewed: 285064a9a37c76f56f6fa1b44d4c553c34f49bcc (base 8a29f254bd76b414d229a87b2c2367d7dc7a1e5c)

Scope: `crates/fltk-unparser-core/` — `doc.rs`, `accumulator.rs`, `resolve.rs`,
`lib.rs`, `Cargo.toml`. Pure in-memory data-transformation library (Doc combinator
tree, immutable accumulator, spacing-spec resolution). No I/O, no network, no
filesystem, no deserialization, no crypto, no auth surface, no secrets, no `unsafe`,
no FFI in this diff. The classic injection / SSRF / path-traversal / secrets / authz
classes have no attack surface here.

## No findings.

The only security-relevant trust boundary in scope is denial-of-service via stack
exhaustion on attacker-controlled tree depth (Doc/CST depth is attacker-controlled
for unparsers over untrusted input; a Rust stack overflow is an *uncatchable* abort).
I evaluated it and am explicitly NOT raising it, for the reasons below:

- The happy-path teardown hazard is handled: `Doc::drop` (doc.rs:73) and
  `DocNode::drop` (accumulator.rs:35) are iterative worklist/loop drains, and
  `concat`/`concat_rc`/`pop_join` splice children via `&mut`/`mem::{take,replace}`
  rather than recursing.
- The remaining recursive surfaces — the `resolve.rs` passes (`expand_joins`,
  `extract_all_boundary_specs`, `resolve_patterns`, `collapse_hardline_sequences`,
  `resolve_rc`), the recursive `parent`-chain drop in `DocAccumulator`, and the
  derived recursive `Debug`/`PartialEq` — recurse on attacker-controllable depth.
  This is a real DoS vector, but it is an **explicitly deferred, user-approved**
  design item, not present-but-overlooked code: design §3(b) + open question 1
  ("Leaving resolve_spacing_specs recursive is fine for now"), tracked as
  `TODO(unparser-deep-tree)`. Per the review scope ("Absence of not-yet-implemented
  design components is expected"), it is out of scope for this batch. Recorded here
  so the deferral is visible, not as an actionable finding.

Other things checked and cleared:

- No integer arithmetic that can overflow on attacker input; `blank_lines`/`indent`
  (u32) are only compared, never combined (merge_spacing, pick_spacing_with_blank_lines).
- Index/deque operations (`extract_boundary_specs` remove/pop, `resolve_concat_patterns`
  pop_front loops) are all length-guarded before access — no panic-on-untrusted-index.
- `assert!`/`panic!` sites (`resolve_spacing` neither-trivia-nor-spacing; accumulator
  pop/merge invariants) fire on generator-built malformed Doc trees, not directly on
  untrusted source text, and faithfully mirror the Python backend's `RuntimeError`
  (no new Rust-only crash vector; see dispositions-prepass-r1.md slop-2).
- `Rc`-based types are single-threaded by construction (not Send/Sync); no data-race
  surface, no `unsafe`.
