# Reuse review: regex-grammar-spike

Commit reviewed: 88282829

## reuse-1

**File:** `fltk/fegen/regex_corpus.py:67-83` (`classify_pattern`)

**What's duplicated:** `classify_pattern` manually instantiates `TerminalSource`, constructs the parser, calls `apply__parse_regex(0)`, and checks `result.pos == len(terminals.terminals)`. This is exactly the logic in `fltk.plumbing.parse_text` (`fltk/plumbing.py:300-331`), which does the same three steps (construct `TerminalSource`, instantiate the parser class, call the start-rule method by name, compare `result.pos != len(terminals.terminals)`).

**Existing function:** `parse_text(parser_result, text, rule_name)` at `fltk/plumbing.py:300`.

**Consequence:** If `parse_text`'s acceptance logic changes (e.g. the position comparison semantics or the `TerminalSource` contract shifts), `classify_pattern` will silently diverge. The module docstring acknowledges `parse_text` but gives "avoid importing the full plumbing stack" as the justification. That rationale is reasonable for a module imported at test-collection time, but it is a documented divergence point that must be kept in sync by hand. If the plumbing stack's import weight becomes acceptable in future (e.g. because the test suite restructures collection), the manual duplicate should be replaced.

## reuse-2

**File:** `fltk/fegen/genparser.py:66-71` vs `fltk/plumbing.py:186-209`

**What's duplicated:** Two public `parse_grammar_file` functions with overlapping contracts. `genparser.parse_grammar_file` (`fltk/fegen/genparser.py:66`) applies `add_trivia_rule_to_grammar` + `classify_trivia_rules`. `plumbing.parse_grammar_file` (`fltk/plumbing.py:186`) delegates to `parse_grammar` which also applies trivia rules (via `_read_and_parse_grammar` → `parse_grammar`). `regex_corpus.py:106` imports from `fltk.plumbing`; `tests/test_regex_grammar_corpus.py:24` also imports from `fltk.plumbing`. The duplication predates this diff, but `regex_corpus.py` choosing `plumbing.parse_grammar_file` over `genparser.parse_grammar_file` adds another call site to the plumbing copy without consolidating the two. If the trivia-handling steps in the two implementations diverge, the corpus tool and the genparser tool will disagree on what the grammar looks like.

**Existing function:** `fltk.fegen.genparser.parse_grammar_file` at `fltk/fegen/genparser.py:66`.

**Consequence:** Two implementations of the same operation with slightly different signatures; new code in this diff selects one without consolidating. Maintenance cost: any change to trivia rule wiring must be applied in both places.
