# Judge verdict — prepass (round 2)

Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: prepass (code; Phase 2 of design.md — idiomatic native surface). Design at `docs/adr/2026/06/10-rust-idiomatic-cst-api/design.md` as ground truth. Base 7e39dfb..HEAD fb8852f. Round 2 (APPROVED or ESCALATE only). Prior round: REWORK on scope-1 (TODO-deferred benchmark gate failed rubric Q2 → do-now).
Notes: notes-prepass-slop.md (4 findings), notes-prepass-scope.md (3 entries; scope-2 duplicates slop-2, scope-3 is a reviewer-marked non-finding). Dispositions: dispositions-prepass.md (round 2).

## Added TODOs walk

None remaining. The round-1 TODO (`rust-cst-traverse-benchmark`) was promoted to Fixed; grep across `*.rs`, `*.toml`, `*.md`, `*.py` (excluding ADR docs) returns zero references to the slug — both halves (TODO.md entry, `TODO(slug)` comment in `crates/fltk-cst-spike/Cargo.toml`) removed.

## Other findings walk

### scope-1 — Fixed (round 2; was TODO, rejected round 1)
Claim: design §6 item 8 benchmark gate (build + traverse micro-benchmark validating the `Box`→`Shared` uncontended-lock overhead before Phase 2 builds on it) never implemented; consequence is Phase 2 committed atop unvalidated lock-overhead assumptions.
Evidence at HEAD (commit fb8852f):
- `crates/fltk-cst-spike/Cargo.toml`: `[[bench]] name = "traverse"` + criterion 0.5 dev-dependency; the round-1 `TODO(rust-cst-traverse-benchmark)` comment removed.
- `crates/fltk-cst-spike/benches/traverse.rs`: 256-node tree (Items root → 256 Identifier children, each with a labelled Span child); `build` and `traverse` workloads; traverse forces an uncontended `RwLock` read per child via `children_item()` + `read()`. Matches §6 item 8's shape ("build + traverse micro-benchmark") and the round-1 verdict's allowance that absolute numbers judged against the design's order-of-magnitude expectation satisfy the gate (the `Box` "before" no longer exists at HEAD).
- Result recorded in the bench docblock: build/256 ~14.9 µs (~58 ns/child), traverse/256 ~2.0 µs (~7.9 ns/child); gate verdict PASSED; parking_lot contingency (§5) explicitly not triggered.
- Independently reproduced by this judge (release, `--quick`): build/256 14.48–14.73 µs, traverse/256 2.02–2.04 µs — matches the recorded numbers. ~8 ns per uncontended read is within the design's "same order of magnitude as a Box deref" expectation; gate verdict is sound.
- `TODO.md`: `rust-cst-traverse-benchmark` entry deleted; `rust-cst-accessor-clone-efficiency` entry updated to drop the "pending §6 item 8" blocker language and record the gate result — consistent, no dangling cross-reference.
- Benchmark target compiles clean (`cargo check --benches -p fltk-cst-spike`).
Assessment: fix fully addresses the finding and the round-1 demand (add bench, run release build, record result, declare gate outcome, remove TODO). Accept.

### slop-1 through slop-4, scope-2, scope-3 — unchanged from round 1
Verified at a72cb65 in round 1; the round-2 commit fb8852f touches only `Cargo.lock`, `TODO.md`, `crates/fltk-cst-spike/Cargo.toml`, `crates/fltk-cst-spike/benches/traverse.rs`, and the dispositions doc — no regression surface for the prior fixes. Round-1 evidence stands:
- **slop-1 Fixed**: `spike_tests.rs:9` arrow corrected to `` `Identifier_Label` → `IdentifierLabel` ``.
- **slop-2 Fixed**: f-string prefix added at the generator; zero literal `{enum_name}` hits across all five regenerated outputs.
- **slop-3 Fixed**: dead `_child_variants_for_rule` call removed; `total_child_variants` gone from the generator.
- **slop-4 Fixed**: 8-line per-struct boilerplate replaced with the one-line pointer; canonical doc survives only on `Shared<T>` (`crates/fltk-cst-core/src/shared.rs`).
- **scope-2 Fixed**: duplicate of slop-2; same verified fix.
- **scope-3 Won't-Do**: reviewer-marked non-finding (rename design-authorized at §4.3 item 5); correct null disposition.

## Disputed items

None.

## Approved

7 dispositions: 6 Fixed verified (one a duplicate; scope-1 newly verified this round including an independent benchmark re-run), 1 Won't-Do sound (reviewer-marked non-finding). 0 TODOs outstanding.

---

## Verdict: APPROVED

The single round-1 dispute (scope-1) is resolved exactly as demanded: benchmark implemented per design §6 item 8, run and reproduced, gate explicitly declared passed, parking_lot contingency explicitly not triggered, TODO removed from both TODO.md and code. All other dispositions stand from round 1.
