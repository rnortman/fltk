# Judge verdict — prepass

Phase: prepass (code). Base 663b273..HEAD ae90f84. Round 1.
Notes: 2 reviewer files (slop, scope); 3 findings (slop), 0 findings (scope).

## Added TODOs walk

No TODO-dispositioned findings, and the diff adds no `TODO(...)` comments
(`git grep` over the diff: none). Nothing to score against the rubric.

## Other findings walk

### slop-1 — Fixed
Claim: `_item_anchor_lines` op loop has no `else`; an unhandled `OperationType`
silently drops a push/pop and emits an unbalanced accumulator stack — a silent
codegen-corruption bug.
Diff at `gsm2unparser_rs.py:537-543`: added
`else: raise ValueError(f"Unsupported OperationType in item anchor: {op.operation_type!r}")`
after the `JOIN_END` branch — exactly the fix the finding requested.
Responder's factual pushback verified: the finding cites `RULE_START`/`RULE_END`
as the unhandled trigger, but those are `ItemSelector` members
(`fmt_config.py:67-68`), not `OperationType`. `OperationType`
(`fmt_config.py:101-107`) has exactly seven members — `SPACING` + six begin/end
ops — and all seven are handled (`gsm2unparser_rs.py:510-536`), so no current
config can reach the `else`. Severity is therefore nit (path genuinely
impossible today), but the guard is harmless, never fires for valid config (no
generated-output change, parity preserved), and converts a future enum
extension from silent corruption into a loud generation-time error.
Assessment: fix addresses the comment; responder's severity correction is
accurate. Accept.

### slop-2 — Fixed
Claim: `_gen_item_body` inlines `item.quantifier.is_multiple()` instead of
calling `_item_routes_to_quantified_loop`, so the predicate's docstring claim of
single-source routing is not enforced; a maintainer editing only the predicate
produces mismatched `__inner` sibling emission vs. body routing.
Diff at `gsm2unparser_rs.py:633`: `_gen_item_body` now guards on
`self._item_routes_to_quantified_loop(item)`. Equivalence verified: the
predicate (`:599`) returns `item.disposition != SUPPRESS and
item.quantifier.is_multiple()`; the `SUPPRESS` early-return at `:631-632`
guarantees the first conjunct is already true at that point, so the new call is
behaviorally identical to the prior inline check. Both call sites
(`_gen_item_method:576`, `_gen_item_body:633`) now route through the one
predicate, making the docstring's single-source claim true.
Assessment: zero behavioral change; the maintainability defect the finding
named is resolved. Accept.

### slop-3 — Fixed
Claim: the `# position == "after"` comment is tautological — the
`Literal["before", "after"]` type already guarantees the fallthrough value; an
LLM tell.
Diff at `gsm2unparser_rs.py:474-475`: replaced with a comment stating the
load-bearing distinction — the "after" path resolves a labeled item by `LABEL`
only, no literal fallback, unlike "before". Accuracy verified against the
function body: "before" tries `LABEL` then falls back to `LITERAL` for literal
terms (`:465-472`); "after" resolves labeled items by `LABEL` only (`:476-477`).
The replacement matches the method docstring's own bullets (`:457-461`).
Assessment: cosmetic finding, correct fix carrying real semantic content.
Accept.

## Approved

3 findings: 3 Fixed verified (slop). Scope reviewer: 0 findings.

---

## Verdict: APPROVED

All three dispositions acceptable: each fix lands at the named line and
addresses the comment, the responder's slop-1 factual correction checks out, and
slop-2 is verifiably behavior-preserving. No TODOs, no disputed items.
