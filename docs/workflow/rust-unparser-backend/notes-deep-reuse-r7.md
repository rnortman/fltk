# Reuse review — batch 7

Commit reviewed: 1fcae0bbe0063b83b1883eb439ababc9da6916d4

## reuse-1

**File:** `fltk/unparse/gsm2unparser_rs.py`

**Duplicated blocks:**
- `_gen_trivia_rule_processing`, lines 1127–1167 (inner-indent pair `i2`/`i3`)
- `_gen_non_trivia_rule_processing`, lines 1263–1303 (inner-indent pair `i5`/`i6`)

Both blocks implement the same generation-time `preserve_blanks` branching:

```python
if preserve_blanks > 0:
    # emit `if newline_count >= 2 { … HardLine{blank_lines=preserve_blanks} … }`
    # emit `} else if newline_count >= 1 { … HardLine{blank_lines=0} … }`
    # emit `} else { … default separator … }`
else:
    # emit `if newline_count >= 1 { … HardLine{blank_lines=0} … }`
    # emit `} else { … default separator … }`
```

The only structural difference is the indent-level variables passed into `_add_separator_spec_lines` / `_add_default_separator_spec_lines`. The calls are byte-for-byte identical apart from the indent argument.

**Existing function:** `_gen_trivia_rule_processing` already contains the first copy; `_gen_non_trivia_rule_processing` contains the second.

A private helper — e.g. `_gen_newline_separator_lines(self, rule_name, separator, is_required, preserve_blanks, outer_indent, inner_indent) -> list[str]` — would eliminate the duplication. Both callers already know their indent depth, so the signature is clean.

The `preserve_blanks` extraction (`preserve_blanks = 0; if self._formatter_config.trivia_config: preserve_blanks = …`) also appears identically in both methods (lines 1111–1113 and 1226–1228); a property or one-liner in the class would reduce this further, but the branching block is the higher-maintenance duplicate.

**Consequence:** Any future change to the newline-branching logic (e.g. adding a `>= 3` tier, adjusting HardLine construction, modifying context strings) must be made in both places and kept in sync. The two sites are already ~150 lines apart in the same file, so the risk of one being updated without the other is real.
