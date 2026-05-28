# Reuse Review — Phase 4 Runtime Integration

Commit reviewed: cdffac4

---

## reuse-1

**File:line**: `fltk/fegen/genparser.py:219–251` (`_parse_grammar_raw`) vs. `fltk/fegen/genparser.py:26–55` (`parse_grammar_file`, unchanged pre-existing function)

**What's duplicated**: `_parse_grammar_raw` is a near-copy of the module-level `parse_grammar_file` function that already lives in the same file. Both open the grammar file, build a `TerminalSource`, run `fltk_parser.Parser`, call `apply__parse_grammar(0)`, call `errors.format_error_message` on failure, construct `fltk2gsm.Cst2Gsm(terminals.terminals)`, and call `visit_grammar`. The only difference is that `_parse_grammar_raw` omits the `add_trivia_rule_to_grammar`/`classify_trivia_rules` tail, while `parse_grammar_file` applies both.

**Existing function**: `genparser.parse_grammar_file` at `fltk/fegen/genparser.py:26`. The parse-and-convert body (lines 32–53) is identical. The trivia call (line 54) is the sole divergence.

**Consequence**: Two places in the same file maintain the same file-read + TerminalSource + fltk_parser + Cst2Gsm sequence. If fltk_parser is replaced, the error-message format changes, or TerminalSource semantics shift, both must be updated independently. The split is also confusing: a reader of `_parse_grammar_raw` cannot tell it is intentionally trivia-free without reading the docstring, while `parse_grammar_file` above it applies trivia — the relationship between them is implicit. The right fix is to factor the shared body into a helper (`_parse_grammar_text_to_raw_gsm(text) -> gsm.Grammar`) and have both call it, with `parse_grammar_file` appending the trivia pass and `_parse_grammar_raw` returning the result directly.

---

## reuse-2

**File:line**: `fltk/fegen/genparser.py:26–55` (`genparser.parse_grammar_file`) vs. `fltk/plumbing.py:151–174` (`plumbing.parse_grammar_file`) vs. `fltk/unparse/genunparser.py:19–48` (`genunparser.parse_grammar_file`)

**What's duplicated**: Three separate `parse_grammar_file` functions across three modules perform the same sequence — open the file, build `TerminalSource`, run `fltk_parser.Parser`, check the result, call `format_error_message`, construct `Cst2Gsm`, and call `visit_grammar`. `plumbing.parse_grammar_file` delegates to `plumbing.parse_grammar` (which is the canonical version, with the Rust-backend seam added in this diff). `genparser.parse_grammar_file` and `genunparser.parse_grammar_file` are inline implementations of the same logic, pre-dating `plumbing`.

**Existing function**: `plumbing.parse_grammar` / `plumbing.parse_grammar_file` at `fltk/plumbing.py:94–174`. These are the post-diff canonical implementations that also support the new Rust backend.

**Consequence**: `genparser.parse_grammar_file` and `genunparser.parse_grammar_file` are frozen copies of the Python-only parse path. The diff extended only `plumbing.parse_grammar`/`parse_grammar_file` with the `rust_fegen_cst_module` backend selector. Any future change to error formatting, terminal source construction, or parse failure handling must be made in all three places. More immediately: `genparser._parse_grammar_raw` (reuse-1) would not exist if `genparser.parse_grammar_file` were delegating to `plumbing.parse_grammar_file` — the raw-grammar variant could simply call `plumbing.parse_grammar(text)` (no trivia) while the existing function adds the trivia pass, collapsing both issues.
