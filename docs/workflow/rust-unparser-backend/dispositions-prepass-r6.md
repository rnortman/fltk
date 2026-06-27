# Dispositions — prepass r6

Commit: ae90f84671cf03d4b6e2aeed244bab3df1b1d633

## slop-1

- Disposition: Fixed
- Action: Added an `else: raise ValueError(...)` to the `_item_anchor_lines`
  operation loop in `fltk/unparse/gsm2unparser_rs.py:534` (after the `JOIN_END`
  branch), turning a silently-dropped op into a loud generation-time error.
- Severity assessment: Low. The finding's cited trigger is factually wrong:
  `RULE_START`/`RULE_END` are `ItemSelector` members
  (`fmt_config.py:67-68`), not `OperationType` members. `OperationType`
  (`fmt_config.py:98-107`) has exactly seven members — `SPACING` plus six
  begin/end ops — and all seven are already handled in the loop, so no current
  config can reach an unhandled branch and there is no live silent-corruption
  bug. The guard is purely defensive against a future eighth enum member. The
  Python helpers (`gsm2unparser.py:1490-1559`) likewise have no `else`, but this
  guard never fires for any valid config, so it changes no generated output and
  cross-backend parity is preserved; it only makes the Rust generator fail loudly
  rather than emit an unbalanced push/pop stack if the enum is later extended.

## slop-2

- Disposition: Fixed
- Action: `_gen_item_body` (`fltk/unparse/gsm2unparser_rs.py:625`) now routes via
  `self._item_routes_to_quantified_loop(item)` instead of re-inlining
  `item.quantifier.is_multiple()`.
- Severity assessment: Low; no behavioral change. The two expressions are
  equivalent at that point (the `SUPPRESS` early-return above guarantees
  `disposition != SUPPRESS`, the predicate's other conjunct). The fix makes the
  predicate's docstring claim — that it is the single source of truth keeping
  body-routing and sibling-emission from drifting — actually true, so a future
  change to the routing condition stays in one place.

## slop-3

- Disposition: Fixed
- Action: Replaced the tautological `# position == "after"` comment in
  `_item_anchor_config` (`fltk/unparse/gsm2unparser_rs.py:474`) with a comment
  that states the load-bearing difference: the "after" path resolves a labeled
  item by `LABEL` only, with no literal fallback (unlike the "before" path).
- Severity assessment: Cosmetic. The old comment restated what the
  `Literal["before", "after"]` type already guarantees; the replacement carries
  the actual semantic distinction documented in the method docstring.
