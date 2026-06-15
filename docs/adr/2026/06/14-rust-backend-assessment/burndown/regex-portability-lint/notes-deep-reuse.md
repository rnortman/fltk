reuse-1

File: fltk/fegen/regex_portability.py:86-91 (the parse-and-check body of check_regex_portable)

What's duplicated: check_regex_portable constructs a TerminalSource, instantiates _RegexParser, calls apply__parse_regex(0), and tests result is not None and result.pos == len(pattern). This is structurally identical to the logic already in fltk/fegen/regex_corpus.py:classify_pattern (lines 80-83), which does the same three steps and the same predicate. The only differences are: (a) classify_pattern returns bool and compares against len(terminals.terminals), while check_regex_portable compares against len(pattern); (b) check_regex_portable also reads error_tracker.longest_parse_len on the reject path.

Existing function: classify_pattern — fltk/fegen/regex_corpus.py:67-83

Consequence: the accept/reject predicate is now expressed in two places. If the start-rule name, the parser API, or the "consumed entire input" predicate ever changes (e.g. the parser is renamed or the API to query parse length shifts), both sites must be updated in sync. classify_pattern is already imported by the whole-tree completeness test (tests/test_regex_portability.py:30) alongside check_regex_portable, so both abstractions are already live in the same test module. check_regex_portable could call classify_pattern (or a shared lower-level helper) for the boolean predicate, then only add the error_tracker.longest_parse_len read on the reject branch — reducing the duplicated driver boilerplate to a single canonical site.
