# User decisions on the 3 open questions — requirements (authoritative)

Apply these to requirements.md so the open questions are settled or explicitly marked designer-to-answer.

## C — identity / equality semantics: SETTLED
Equality/inequality only (`==` / `!=`). **Object identity (`is`) is NOT part of the contract** and is not guaranteed — distinct modules/backends may produce distinct objects, so `node.kind is NodeKind.ITEM` can be `False` even when `==` is `True`. `match`/`case` value patterns (which use `==`) keep working. Document this as the public API contract for out-of-tree consumers.

## A — protocol `Label` real-enum vs type-erased: DESIGNER TO ANSWER
Not a user fork. The gating criterion + existing `_fltk_canonical_name` bridge constrain the answer; the designer validates feasibility of the clean form and escalates to the user ONLY if it proves infeasible.

## B — NodeKind runtime-dependency (pure-Rust deployments): SETTLED
Option A: no eager concrete-backend import. Consistent with the requirements' own no-eager-import constraint; `fltk2gsm.py` does not use `NodeKind`.
