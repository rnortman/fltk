Style: concise, precise, complete, unambiguous. No padding, no preamble.

quality-1:
- Disposition: Fixed
- Action: Moved `child_enum_name` from inside the "Label enum" section (was gsm2tree_rs.py:419) to just before `_child_enum_block` in the "Child enum" section (now gsm2tree_rs.py:509). No behavior change. 195 tests pass.
- Severity assessment: Low — organizational only; correctness and output are unaffected. Maintenance risk if the wrong precedent propagated to future naming helpers.
