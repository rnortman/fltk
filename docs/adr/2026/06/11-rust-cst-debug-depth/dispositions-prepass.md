slop-1:
- Disposition: Fixed
- Action: Removed the two added sentences ("child_union: the sorted list..." and "into_drop_item is emitted when...") from `_child_enum_block` docstring (gsm2tree_rs.py:545-548). The parameter name and existing docstring text are sufficient; the deleted sentences restated what the code does rather than stating contract or invariant.
- Severity assessment: Docstring inflation; no correctness impact. The deleted sentences did add one piece of non-obvious information (the dual condition for `needs_drop_item`), but a single inline comment at the condition itself (which already exists at lines 588-596) is the right place for that.

slop-2:
- Disposition: Fixed
- Action: Removed `# Pre-compute the child-class union once for _drop_block.` comment from `generate()` (gsm2tree_rs.py:281). The variable assignment and single downstream call site are self-evident.
- Severity assessment: Noise only; no correctness impact.

slop-3:
- Disposition: Fixed
- Action: Replaced "impl Drop is emitted when the rule has node-typed children (child_classes non-empty)." in `_node_block` docstring with the invariant that matters: why span-only nodes skip Drop (trivially non-recursive drop glue + avoids E0509). The `if child_classes:` guard remains unchanged; the docstring now explains the *reason*, not the condition itself.
- Severity assessment: Docstring quality only; no correctness impact.

slop-4:
- Disposition: Fixed
- Action: Made the "Teardown is iterative: bounded stack at any depth." docstring line conditional on `child_classes` being non-empty (gsm2tree_rs.py:~720). Regenerated all six CST outputs; span-only structs (Identifier, Trivia, Disposition, Quantifier, RawString, etc.) no longer carry the false claim. Structs with node-typed children (Items, Expr, etc.) retain the accurate statement.
- Severity assessment: False public API documentation on generated types visible to downstream consumers. The statement was technically defensible (span-only drop glue is bounded) but misleading because it implied an iterative `impl Drop` exists. Fixing it is correct.

slop-5:
- Disposition: Fixed
- Action: Hoisted the two-line "drops here: count==1 → childless node, trivial drop; count>1 → refcount decrement only. Either way, no recursion." comment out of the per-variant loop body in `_drop_block` and emitted it once before the `match self {` block (gsm2tree_rs.py:~1673). The per-arm inline comment about "Sole owner: steal the children..." is retained in each arm (it describes the conditional, not the drop). Regenerated outputs: cst.rs files now have the hoisted comment once, not repeated per variant.
- Severity assessment: Generated-file noise; no correctness impact. With many variants (21 in cst_fegen.rs) the repetition was particularly egregious.
