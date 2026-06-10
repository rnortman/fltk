# Overnight TODO Burndown — 2026-06-10 — Decision Log

Style: concise, precise, no padding. Audience: product owner reviewing in the morning.

Autonomous run per your instruction: all human gates filled by the orchestrator, work on `main`, one squashed commit per iteration, **nothing pushed**. Everything is reversible from the base commit.

**Base commit at start: `5d5bf072c938d9375c4a9c7ce47f71ddd85eb417`**

To discard everything: `git reset --hard 5d5bf07` (then force-of-will, not force-push — nothing was pushed).

## Where to look

- `triage.md` (this dir) — full per-TODO analysis, recommendations, and decisions.
- `exploration-*.md` (this dir) — adversarial validation for the kept/deleted items. Several TODOs were factually wrong; details in triage.
- `docs/adr/2026/06/10-<slug>/` — per-item ADR dirs for the accepted items, each with `request.md`, `exploration.md`, design (where applicable), review notes, dispositions, judge verdicts.

## Decisions at a glance

| Slug | Decision | Status |
|---|---|---|
| `example-placeholder` | Keep (by design) | n/a |
| `bazel-rules-rust` | Keep deferred (your instruction) | n/a |
| `rust-cst-child-node-identity` | Keep deferred — verified the deferral is sound; cache fix has unstated invalidation complexity; needs a real consumer demand to justify | n/a |
| `child-span-params-dedup` | **Delete** — refactor saves ~0 lines, drift is loud, makes a clean test table worse | pending iteration 1 |
| `pyi-label-quintet-reuse` | **Delete** — pyright conformance tests already catch the drift this guards against; a 3rd copy (Rust) makes "single source" unachievable anyway | pending iteration 1 |
| `dependabot-branch-pin-gap` | **Do** — re-pin `dtolnay/rust-toolchain` to the `v1` tag SHA so Dependabot tracks it; `with: toolchain: stable` already guards the branch difference | queued |
| `gencode-poc-fltkg` | **Do** — `.fltkg` source file verified to produce byte-identical output; adds drift-guard test | queued |
| `preamble-helpers-into-cst-core` | **Do** — move 5 duplicated unsafe-adjacent helpers into `fltk-cst-core`; verified sound, no behavior change | queued |
| `span-source-as-py-crosscdylib` | **Do (reframed)** — real O(source-length)-per-read perf bug for downstream consumers; fix needs a new `fltk._native`-side entry point, not just the preamble helper the TODO proposed; design stage included | queued after preamble |
| `pyright-batch-tests` | **Do (reframed)** — TODO was factually wrong twice; real fix is per-file pyright batching (14 subprocesses → ~4), skipping the cross-module consolidation the TODO asked for | queued last |

## Items set aside for you

None required your input outright. The closest call was `rust-cst-child-node-identity`: kept deferred (status quo), but if you weigh Python-vs-Rust `is`-identity parity for downstream consumers heavily, say so and it gets a design pass.

## Iteration log

All complete. One squashed commit each; every commit passed the full precommit gate (lint, format-check, typecheck, pytest, cargo check/clippy/test).

- Iteration 1 — `3256793` — triage docs + delete `child-span-params-dedup`, `pyi-label-quintet-reuse`
- Iteration 2 — `6d42885` — `dependabot-branch-pin-gap`: re-pinned to `v1` tag SHA
- Iteration 3 — `87bf19e` — `gencode-poc-fltkg`: `fltk/fegen/test_data/poc_grammar.fltkg` + standard regen path + drift-guard test; `src/cst_generated.rs` byte-identical
- Iteration 4 — `9db20de` — `preamble-helpers-into-cst-core`: helpers now in `crates/fltk-cst-core/src/cross_cdylib.rs`; deep review deferred one finding as new tracked `TODO(crosscdylib-abi-sentinel)`
- Iteration 5 — `8bee6b0` — `span-source-as-py-crosscdylib`: full design + review chain. Accessor span reads now O(1) and Arc-sharing. **Bonus finding**: the copying also broke `merge`/`intersect` of accessor-derived spans on the Rust backend (Python backend succeeded) — a cross-backend divergence, now fixed and pinned by tests. Design corrected my request's sketch: an isinstance gate is directionally impossible canonical-side; replaced with an ABI-marker gate (version skew → clean TypeError; forged-marker UB documented as out-of-contract on the private entry point, hardening owned by `crosscdylib-abi-sentinel`).
- Iteration 6 — `3217a14` — `pyright-batch-tests`: 14 → 4 pyright subprocesses (~4s saved per run measured); assertions/attribution preserved; shared helper in `tests/pyright_test_utils.py`

## Post-run TODO.md state

`example-placeholder` (by design), `bazel-rules-rust` (kept, your call), `rust-cst-child-node-identity` (kept deferred, verified sound), `crosscdylib-abi-sentinel` (new — ABI-gate unification/strengthening for the unsafe cross-cdylib casts; emerged from iterations 4–5 reviews).

## Notes for review

- Nothing pushed. Six commits on `main` after base `5d5bf07`.
- The span-source change is the one with real design risk (new Python-reachable `unsafe` path behind a private classmethod + ABI marker). It got the full chain: design review, 7-reviewer deep review, judge. Read `docs/adr/2026/06/10-span-source-as-py-crosscdylib/design.md` §2.2–§3 if you read only one thing.
- The dependabot re-pin changes which upstream branch the action code comes from (`stable` → `v1`/master tree); `with: toolchain: stable` keeps the installed toolchain identical. CI will exercise it on your first push.
