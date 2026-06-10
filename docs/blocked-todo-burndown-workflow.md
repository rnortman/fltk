# TODO Burndown — Orchestrator Workflow

Captures the delta from the standard orchestrator workflow (explore → requirements → design → implement → ship). Assumes the orchestrator already knows CLAUDE.md and the standard chain; this doc covers only the burndown-specific shape on top.

Start by creating a directory under docs/adr for all workflow artifacts.

## Phase 1 — Find candidates

`grep -n '^##' TODO.md` will concisely provide slugs of all currently-tracked TODO items. The slugs tell you enough to take a guess at low-hanging, high-value fruit. Choose 10-20 slugs, preferring those where:
- The exploration suggests any required decision-making is **straightforward** (a stated fix shape, not a question), AND
- The value is **real** (correctness bug, data loss, drift foot-gun, "robust as fuck" misalignment, security primitive consolidation, structural cleanup that reduces code).

OR: The TODO seems likely to end up as a "won't do". These are the easiest ones to handle (see below) and so can be prioritized to reduce noise.

## Phase 2 — Validate candidates against code (parallel Explore agents)

**TODOs as written are frequently wrong in subtle ways**, and the triage doc you write next will be poisoned if you don't sanity-check. In particular a TODO may prescibe a fix, but it's only fixing a symptom, not an underlying problem. This is where your judgement will come in.

Spawn one review-chain:explorer agent per candidate, **all in parallel** (one assistant message, N `Agent` invokes). Each prompt:
- States the TODO's claim verbatim
- Asks the agent to verify adversarially against the code: do the cited lines actually look like that? Are the proposed constraints real? Is the proposed fix shape feasible? Are there blockers the TODO didn't mention? Is this only papering over a symptom of a deeper problem?
- Asks for facts and source-code-ground-truth (file and line numbers) only — no prescriptions
- Tells the agent to write its result to a file in the ADR (just like normal explorer workflows)

**Read the full output of the explorations yourself**, not only summaries. This is an exception to the usually prohibition against reading workflow artifacts.

**Second-guess the agents.** They often propagate the TODO's framing instead of questioning it. Be ready to push back when an agent's answer doesn't add up. You can read code yourself or use another agent to investigate alternate perspectives.

## Phase 3 — Write the triage doc

Audience: **someone who has not read the code and doesn't want to**.

Per investigated candidate:
- **What the problem is** — plain English. No code-reading required.
- **Why it matters** — concretely. Data loss? Silent shadowing? Drift between sites? "Robust as fuck" misalignment? Quantify if you can.
- **What the work actually looks like** — the *real* fix, including any constraint shape the validation phase surfaced.
- **The case for skipping** — when not to do this. Helps the user pick.
- **Recommendation** — Do, Delete, or Blocked:
  - Do: This is worth doing and nothing stops us from doing it now.
  - Delete: This is not worth doing ever. Delete it.
  - Blocked: This is worth doing but is blocked on something else. Be specific about what's blocking it. ("Needs design" is not blocking in this context.)

Note that many of the entries in TODO.md may in fact be best not done, because they have hardly any value or are actively harmful. Consider for example a ticket to create a test helper to eliminate duplication between 2-3 unit tests. What do the call sites look like after that refactoring? Are we saving many lines of code? Sometimes a refactoring like that actually results in complex call signatures and awkward call sites, and a multi-mode "helper". That's a good candidate to recommend as "don't do it, delete it".

Many TODOs may be incorrectly framed as-is. If your recommendation is to reframe it, then a "do" recommendation means to do your reframed version, not the original framing.

The recommendation should be *clear* as to what it is recommending, so that if the user simply says "I accept all recommendations* it is unambiguous what that means. If there are options, provide options, but pick *one* as the recommendation.

## Phase 4 — User gate (the most load-bearing one)

Stop. The user reads the triage and arbitrates.

## Phase 5 — Set up parallel ADR workflows

For each accepted item:

1. Create ADR dir at `docs/adr/YYYY/MM/DD-<slug>/`.
2. Write `request.md` in that dir. Do this work *yourself*; do not delegate; it requires context that only you have. **request.md must be self-contained** — workflow agents do not see the triage conversation. Include:
   - Type of work (pure refactor / new feature / spike).
   - Background: what the problem is and where it lives. Cite files and line numbers from the validation phase.
   - Load-bearing constraints surfaced during validation (dep directions, target-compat, upstream-enforced invariants, etc.).
   - User-supplied direction verbatim where applicable. Flag user direction explicitly so downstream agents don't second-guess it.
   - The fix shape (the *user's* chosen approach, not the original TODO).
   - Constraints / non-goals.
   - Verification expectations.
   - Style note up top: concise, precise, no padding, no preamble.
3. If the existing exploration is adequate given the final direction chosen by the user, just move that file into the new dir to serve as the exploration. You can then skip to requirements.

Once all `request.md` files exist, fan out: spawn one explorer or requirements refiner (as appropriate) per workflow, **all in parallel** (one assistant message, N invokes). Each workflow then runs the standard chain independently. Cross-workflow parallelism applies at every stage where the inputs are ready.

### Status tracking inline

Use TaskCreate or track per-workflow status in your reply text after each notification. A compact table works:

```
Status:
- workflow-A: ▶ designer in flight
- workflow-B: ⏸ design gate
- workflow-C: requirements judge in flight
- workflow-D: queued
```

If any workflow is waiting on user review, provide the path to the file they need to review.

## Phase 6 — User gates (one at a time, as they arrive)

Each workflow surfaces its requirements doc when judge-APPROVED; same for design. **Do not batch user gates.** Surface each as it arrives. The user reviews while slower workflows are still finishing.

Common user reply forms:
- "X approved" → advance that workflow.
- "X approved with this direction…" → relay verbatim to the next-phase agent.
- In-place edits in the artifact → revise pointing at the edited doc.

A workflow that the user approves at the design stage either:
- Joins the implementation queue (the default), or
- Receives a special policy (e.g. spike with results-on-branch — see below).

## Phase 7 — Implementation (serialized)

**Serialization is load-bearing.** Exploration, requirements, and design can proceed in parallel across projects, but multiple implementations would step on each other's source-code edits. Implementation runs strictly one workflow at a time.

Queue order: as user-approved designs arrive, append. Drain in order.

Per item, run the standard workflow, typically in incremental mode for implementation or as otherwise instructed. Include all review/respond/judge stages as usual.

On deep APPROVED: **squash to a single commit on `main`**, including the ADR docs in the same commit. Mechanical git. Clean commit message.

`git reset --soft` is not adequate to stage everything; things the implementation agent left untracked will not be included. Notably, ADR docs are often not committed by the implementation agent. It's your job to ensure these make it into the commit.

At this point you are unblocked to proceed to the next queued project.

### Burndown-specific implementation policy

- **Skip the ship-gate**. The burndown convention is: user reviews all commits at the end of the batch, not between items.
- **No pushes**. Ever. The user pushes (or not) on their own time.
- **Squash includes ADR docs.** The exploration, requirements, design, dispositions, judge verdicts, notes, etc. all land alongside the source change as a single historical record.

After squash, advance the queue and start the next item.
