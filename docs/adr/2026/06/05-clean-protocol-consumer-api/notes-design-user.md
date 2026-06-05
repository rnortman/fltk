# USER DIRECTIVE — REJECTED APPROACH (durable; applies to all future authors/reviewers this cycle)

## Verbatim (user, livid — this proposal has now been rejected TWICE across sessions)

> HOW DOES children_accessors_with_separators SOLVE THE GENERAL FUCKING PROBLEM. We have plastered
> this all over CLAUDE.md: WE ARE BUILDING THIS FOR OUT-OF-TREE CONSUMERS. fltk2gsm.py is a *model*
> user but not the *target* user. That proposal is SPECIFIC TO OUR OWN IN-TREE USE CASE. I literally
> swatted that proposal down already once in the last session. Kill it with fire.

## HARD PROHIBITION

Any **traversal-shaped / use-case-specific accessor** is REJECTED. Concretely banned:
`children_items_with_separators()` and any generated method whose shape is cut to one consumer's
traversal pattern (item+separator pairing, etc.). A point solution for `fltk2gsm.py`'s Items walk is
NOT acceptable. Do not re-propose it under a new name. If a design re-introduces a per-traversal
accessor, it has failed.

## THE ACTUAL REQUIREMENT (general narrowing primitive)

A **protocol-only consumer** (imports only the generated protocol module) must be able to narrow a
child-union element to its concrete node type **in an arbitrary traversal pattern they write
themselves** — cast-free, suppression-free, no concrete-backend import. The primitive is
traversal-agnostic: it narrows a single element on demand, so the consumer composes it into whatever
walk THEY need (match-statement, index walk, sibling walk, interleaved pairing, recursion — their
choice, not ours).

`fltk2gsm.py` must then CONSUME this general primitive exactly as an out-of-tree consumer would. It is
the *model* user, not the *spec*. Its Items walk is just one call site.

## COMMITTED MECHANISM — `TypeIs`/`TypeGuard` is the RECOVERED PLAN OF RECORD (not a new idea)

Per the user: a generated **`TypeIs`/`TypeGuard` narrowing predicate** was ALREADY the decided
mechanism in a prior session. It is **committed**, not a candidate to re-weigh. The design must adopt
it and frame it as the established decision.

Shape: a generated per-node-type narrowing predicate whose body duck-checks the `kind` discriminant
(`getattr(child, "kind", None) == NodeKind.X`, which is `Span`-safe) and whose **`TypeIs[Node]` return
type** performs the static narrowing — so it works even though the raw union containing
`terminalsrc.Span` is not `kind`-discriminable. This unifies the user's "`kind` is the primitive"
instinct with real, general narrowing, usable in ANY consumer-authored traversal.

`runtime_checkable` Protocol + `isinstance` was already evaluated and REJECTED in a prior cycle
(data-member protocols are not usefully runtime-checkable; see
`docs/adr/2026/06/05-cst-type-annotations-regression/notes-design-design-reviewer.md:42`). Do not
re-propose it as the primary mechanism.

### PROVENANCE / WHY THIS WAS LOST (persist so it is never lost again)

The `TypeIs` decision was never written into any artifact — it lived only in a prior session's
conversation. The cross-backend handoff and its design §2.5 recorded the OPPOSITE (`typing.cast`) as
settled. So each new session inherited "cast" from the handoff, re-derived from scratch, and `TypeIs`
kept resurfacing as if new. This decision is now persisted HERE and must be carried into design.md
(a "Decision / plan of record" section) and into any handoff. A decision that is not in an artifact
does not exist across sessions.

## WHY THIS KEEPS RECURRING (so the next author does not regenerate it)

1. `fltk2gsm.py` is the only consumer visible in the repo; agents optimize against visible evidence and
   cut the accessor to its shape. The general problem is invisible (out-of-tree consumers aren't here).
2. "Make fltk2gsm clean" is concrete+testable; "general primitive" is abstract+design-risky; the review
   chain rewards the minimal testable thing.
3. **Generality was tested as "another grammar of the same items+separator shape" — which a point
   solution passes.** That is the bug. Generality-by-same-shape is not generality.

## ENFORCEMENT (make the wrong answer FAIL the gate)

- The generality acceptance criterion MUST require the primitive to be exercised across **at least two
  STRUCTURALLY DIFFERENT traversal patterns** (e.g. a match/case dispatch AND an interleaved walk), NOT
  two grammars of the same shape. A traversal-shaped accessor must be UNABLE to satisfy this.
- Add an explicit "Rejected approaches" section naming the bespoke accessor and this rationale, so it
  is not re-proposed.
- The narrowing primitive must be defined per node TYPE (or as a general predicate), never per
  traversal pattern.
