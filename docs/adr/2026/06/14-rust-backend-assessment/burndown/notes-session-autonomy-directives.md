# Session autonomy directives (verbatim user grant, 2026-06-14)

The user granted full autonomous execution of the serialized burndown impl lane and went to sleep.
Recorded verbatim so the criteria are applied exactly and survive a context loss.

## User's words (verbatim)

> OK, the regex-portability-lint design is approved in principle pending positive spike outcome. If the
> regex spike proves we can parse regexes and distinguish in-scope vs out-of-scope regex features, then we
> can proceed with the regex-portability-lint implementation; my approval not needed. If the spike result
> is more complicated then that's something I'll weigh in on.
>
> Yes roll the queue autonomously -- incremental mode for everything, squash each burndown item when it's
> done, include ADR artifacts in each commit. No check-ins. I'm going to be asleep in a moment here.

## Operational interpretation (how the orchestrator will apply this)

**Serialized impl lane — roll autonomously, no check-ins.** Order:
1. `regex-grammar-spike` (in progress) — finish increments (Inc 4 = adversarial, **opus**) → pre-pass + deep
   review chain → squash to ONE commit including its ADR artifacts.
2. `fix-forged-abi-segfault` — incremental impl → review chain → squash (incl. ADR artifacts). OQ1 already
   resolved in its design.
3. `document-scope-boundary` — fast-track (versions→0.2.0, neutral pin) → review → squash (incl. ADR artifacts).
4. `demote-cst-spike` — fast-track (delete traverse.rs bench) → review → squash (incl. ADR artifacts).
5. `regex-portability-lint` — **conditional** (see below).

**Each item:** incremental implementation → full review chain (pre-pass slop+scope → responder → judge;
deep 7-reviewer → responder → judge) → on deep APPROVED, squash to one commit **including that item's ADR
working-dir artifacts**. Only an **ESCALATE** stops the lane and surfaces to the user.

**`regex-portability-lint` gate (conditional approval):** After the spike squashes, assess the spike outcome
against TWO criteria: (a) regexes can be parsed, AND (b) in-scope vs out-of-scope regex features can be
distinguished.
- **Both proven cleanly → PROCEED** autonomously: regenerate the stale ELI5, then implement → review → squash.
  User approval NOT needed.
- **Outcome is "more complicated" → ESCALATE** to the user; do not implement until they weigh in.
(Use a fresh judging agent to make this CLEAN-POSITIVE vs COMPLICATED call against the spike's actual results.)

**Deferred side-task:** delete the two confirmed-cruft TODOs (`rust-ident-dedup`, `cst-header-escape-dedup`)
— TODO.md entries + `TODO(slug)` comments — as a STANDALONE trivial commit at a lane boundary (committing it
mid-chain would corrupt an item's squash). Not an ADR artifact; its own commit.

**Push:** none, ever, without separate explicit per-repo/branch authorization. User reviews all commits on wake.

## EXECUTION RESULT (session complete — autonomous run finished)

All queued items shipped as squashed commits on `main` over base `205c36b`. Nothing pushed.

| # | Commit | Item |
|---|---|---|
| 1 | `9f96d43` | cst-generated-header (prior session) |
| 2 | `a4b35b8` | remove-dead-duplicate-crate (prior session) |
| 3 | `6158488` | burndown: land WIP ADR working docs |
| 4 | `b5695c4` | fltk-grammar-reference doc |
| 5 | `a8e2e28` | recommended-actions: mark shipped items done |
| 6 | `61df5ff` | document-scope-boundary: record user decision |
| 7 | `862b412` | **regex-grammar-spike** (gate CLEAN-POSITIVE) |
| 8 | `d82e82f` | remove two cruft TODOs |
| 9 | `440b4ed` | **fix-forged-abi-segfault** (security bypass caught + closed in review) |
| 10 | `e813764` | **document-scope-boundary** (versions→0.2.0) |
| 11 | `034252d` | **demote-cst-spike** (criterion leak removed) |
| 12 | `dba6a4b` | **regex-portability-lint** (\0 false-negative caught + closed in review) |

Each designed/spec'd item passed: pre-pass (slop+scope) + 7-reviewer deep review + judge. Two items
needed one rework round (forged-abi security, regex-lint reuse-1); both then APPROVED.

Deferred follow-up TODOs planted during the run (legitimate, in TODO.md + code):
`TODO(forged-abi-extract-span-uniformity)`, `TODO(regex-unicode-class-divergence)`,
`TODO(regex-portability-target-list-drift)`.

Remaining for the user: review all commits `205c36b..HEAD`; authorize any push (none done).
