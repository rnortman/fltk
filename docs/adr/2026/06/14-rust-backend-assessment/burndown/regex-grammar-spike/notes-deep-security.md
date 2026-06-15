# Deep security review — regex-grammar-spike

Commit reviewed: 88282829 (range 61df5ff..88282829)

Scope of diff: a new grammar file (`fltk/fegen/regex.fltkg`), four generated
parser/CST artifacts, a Makefile codegen line, a general extract/classify tool
(`fltk/fegen/regex_corpus.py`) with a CLI that reads a developer-supplied
`.fltkg` path, and two test modules. No network, auth, serialization, crypto, or
credential surface is introduced. No `eval`/`exec`/`subprocess`/`pickle`/
`yaml.load`/`os.system` appears in the changed files (the `exec()` calls live in
pre-existing `fltk/plumbing.py`, outside this diff). The diff contains no secrets.

## Findings

security-1. Local DoS via stack exhaustion on adversarial regex input (LOW / informational)

- File: `fltk/fegen/regex_corpus.py:80-83` (`classify_pattern`) and the generated
  recursive-descent parser `fltk/fegen/regex_parser.py` (the `apply__parse_*`
  methods, e.g. `apply__parse_group`/`apply__parse_alternation`).
- Issue: `classify_pattern` drives `RegexParser.apply__parse_regex(0)` on an
  arbitrary input string. The generated parser recurses through native Python
  call frames for nested constructs (group → alternation → concatenation → atom →
  group …). A deeply-nested adversarial pattern such as `((((((...))))))` of
  sufficient depth will reach Python's recursion limit and raise `RecursionError`
  (or, in a CPython build with a raised limit, exhaust the C stack and crash the
  interpreter). The CLI (`_run_cli`) does not catch `RecursionError` — only
  `ValueError`/`FileNotFoundError` from `parse_grammar_file` are caught — so a
  hostile grammar file would abort the tool with an uncaught traceback.
- Trust boundary / data flow: untrusted input enters two ways — (a) the regex
  bodies extracted from a developer-supplied `.fltkg` path passed on the CLI
  (`_run_cli` → `parse_grammar_file` → `collect_regexes` → `classify_pattern`),
  and (b) the adversarial pattern strings in the test suite. Both reach the
  recursive parser without a depth bound.
- Consequence: an attacker who can get a victim to run
  `python -m fltk.fegen.regex_corpus <evil.fltkg>` (or feed a crafted pattern to
  any consumer of `classify_pattern`) can crash the process / exhaust the stack.
  Impact is bounded: this is a local developer/CI validation tool, not a network
  service; the asset at risk is only the availability of that one invocation, and
  the worst case is a crash, not code execution or data disclosure. The recursion
  behavior is inherent to every FLTK-generated parser via the shared
  `fltk/fegen/pyrt/memo.py` runtime and is therefore pre-existing, not introduced
  by this diff — this spike merely adds one more entry point that exercises it.
- Suggested fix: none required for a spike-scoped local tool. If hardening is ever
  wanted for consumers that feed genuinely untrusted patterns, bound input depth/
  length before parsing, or catch `RecursionError` in `_run_cli` and report it as
  a normal rejection rather than an uncaught traceback. Flagged for awareness only.

No other findings. The CLI's path handling is read-only (`Path.exists()` +
`parse_grammar_file`), performs no filesystem writes, no traversal-sensitive
operations, and no shelling out; printing extracted patterns with `!r` (repr)
avoids terminal-control-sequence injection from hostile grammar contents.
