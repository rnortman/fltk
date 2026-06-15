# Scope prepass — regex-portability-lint

Commit reviewed: 6bede5f (base: 034252d)

## scope-1

**File:line:** missing — design §7 generator integration tests, bullet 3

**Expected:** A test that invokes `genparser gen-rust-parser` on a non-portable grammar as a CLI subprocess and asserts the process exits non-zero with the rejection message on stderr. Design §7 lists this as a distinct bullet: "`genparser gen-rust-parser` on such a grammar exits non-zero with the message on stderr (exercises `genparser.py:386-391`)."

**Actual:** The integration tests (`test_non_portable_grammar_raises_from_rust_generator`, `test_non_portable_error_message_has_offset`, `test_posix_class_motivating_bug_is_rejected`) call `RustParserGenerator.generate()` directly and assert `ValueError` is raised. They exercise the generator's `ValueError` path but do not exercise the `genparser.py:386-391` handler that converts `ValueError` → `typer.Exit(1)` with the message on stderr. The `genparser.py` CLI wiring is untested by this diff.

**Consequence:** If the `genparser.py` handler silently swallowed the error, printed the wrong exit code, or formatted the message differently from what a downstream consumer would see, no test in this diff would catch it. The CLI is the integration surface a real user hits; only the library API is covered.

**Suggested fix:** Add one test that spawns `uv run python -m fltk.fegen.genparser gen-rust-parser` with a temp grammar file whose regex is `[[:alpha:]]+`, asserts `returncode != 0`, and checks that stderr contains the pattern string. A single `subprocess.run` call suffices; it does not need to be elaborate.

---

## No other findings.

The design's core deliverables are all present and correctly wired:
- `regex.fltkg` (reconciled name for `regex_subset.fltkg`) serves as the executable portable-subset definition.
- `regex_portability.py` implements `RegexPortabilityIssue` + `check_regex_portable` per §5.2 spec (uses `error_tracker.longest_parse_len` as the reported offset).
- Wiring is at the `gsm.Regex` branch of `_gen_consume_term` in `gsm2parser_rs.py`, not inside `_regex_idx`, per §5.3.
- Module docstring rewritten to describe the two-engine semantic boundary per §5.4.
- No escape hatch introduced per §5.5.
- Parity corpus extended per §5.6.
- `TODO(regex-unicode-class-divergence)` and `TODO(regex-portability-target-list-drift)` present in both `TODO.md` and at their code locations per CLAUDE.md convention.
- `genparser.py` not modified per design intent.
- `docs/adr/2026/06/10-rust-parser-codegen/README.md` not modified per design intent.

scope-1 is a single missing subprocess test — respond-mode scope, no escalation warranted.
