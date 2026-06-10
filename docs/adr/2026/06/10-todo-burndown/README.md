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

(Updated as iterations complete. One squashed commit each.)

- Iteration 1 — triage docs + two TODO deletions: pending
- Iteration 2 — `dependabot-branch-pin-gap`: pending
- Iteration 3 — `gencode-poc-fltkg`: pending
- Iteration 4 — `preamble-helpers-into-cst-core`: pending
- Iteration 5 — `span-source-as-py-crosscdylib`: pending
- Iteration 6 — `pyright-batch-tests`: pending
