quality-1

File: `fltk/unparse/gsm2unparser_rs.py`, `_gen_rule_entry` (~lines 202–228 of
current HEAD) vs. `_item_anchor_lines` (~lines 509–543).

The new `_item_anchor_lines` method (added in this diff) adds an
`else: raise ValueError(...)` for unrecognized `OperationType` members, with
an explicit in-code rationale: "A new enum member reaching here would silently
drop a push/pop and emit an unbalanced accumulator stack, so fail loudly at
generation time instead."  The identical class of bug can occur in the
pre-existing `_gen_rule_entry` anchor loops, which iterate RULE_START and
RULE_END operations without an `else`/raise:

- RULE_START loop handles `GROUP_BEGIN`, `NEST_BEGIN`, `JOIN_BEGIN`; any other
  member (`SPACING`, `GROUP_END`, `NEST_END`, `JOIN_END`, or a hypothetical new
  member) is silently discarded.
- RULE_END loop handles `NEST_END`, `GROUP_END`, `JOIN_END`; same silent drop
  for anything else.

**Consequence:** The guard in the new code creates a false expectation that the
generator will always fail loudly for unrecognized operations.  When a new
`OperationType` member is added, `_item_anchor_lines` will catch it and surface
a generation-time error; the rule-level loops will silently produce an
unbalanced accumulator stack (a GROUP_BEGIN with no GROUP_END, or vice versa),
which corrupts Doc structure in a way that survives the generator without error
and produces wrong formatted output at runtime.  The inconsistency will also
mislead the person adding the new member — they'll see the guard fire for
item-level anchors but won't know to look for the missing rule-level case.

Fix: add `else: raise ValueError(f"Unsupported OperationType in RULE_START
anchor for rule {rule_name!r}: {op.operation_type!r}")` (and analogously for
RULE_END) to both loops in `_gen_rule_entry`, mirroring the rationale already
documented in `_item_anchor_lines`.
