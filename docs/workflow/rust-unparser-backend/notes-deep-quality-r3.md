## quality-1

**File:** `fltk/unparse/gsm2unparser_rs.py:139–141`

`RustUnparserGenerator._class_name` reaches into `self._cst._py_gen.class_name_for_rule_node(rule_name)` — the exact same two-level private-attribute drill that `RustParserGenerator._class_name` (`fltk/fegen/gsm2parser_rs.py:229–231`) already does. `RustCstGenerator` has a public wrapper for exactly this purpose — `class_name_for_rule(rule_name: str)` at `fltk/fegen/gsm2tree_rs.py:779`, with a docstring that reads *"Public wrapper around the internal _py_gen delegation; lets callers (e.g. tests) compute derived identifier families without reaching into _py_gen directly."* — yet this diff copies the older bypassing pattern instead of using that API.

**Consequence:** The workaround now lives in two generator classes and will be copied into a third and fourth as further Rust backend generators are added. The public accessor was added to stop exactly this propagation; the diff undoes that intent silently, with no TODO or note acknowledging the pre-existing misuse in `RustParserGenerator`. Future readers have no signal that `self._cst.class_name_for_rule(rule_name)` is the right call and `._py_gen.class_name_for_rule_node` is a private bypass.

**Fix:** In `RustUnparserGenerator._class_name`, replace `self._cst._py_gen.class_name_for_rule_node(rule_name)` with `self._cst.class_name_for_rule(rule_name)`. In the same PR, fix `RustParserGenerator._class_name` (line 231) and its one stray direct use at line 171 of the same file.
