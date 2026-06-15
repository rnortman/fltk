# Judge verdict — pre-pass

Phase: pre-pass. Base 034252d..HEAD ba953c8. Round 1.
Design: `regex-portability-lint/design.md`.
Notes: 2 reviewer files (notes-prepass-slop.md = "No findings."; notes-prepass-scope.md = 1 finding). 1 disposition.

## Other findings walk

### scope-1 — Fixed
Reviewer claim: design §7 generator-integration bullet 3 — "`genparser gen-rust-parser` on such a grammar exits non-zero with the message on stderr (exercises `genparser.py:386-391`)" — was unimplemented. The three existing integration tests (`test_non_portable_grammar_raises_from_rust_generator`, `test_non_portable_error_message_has_offset`, `test_posix_class_motivating_bug_is_rejected`) call `RustParserGenerator.generate()` directly and assert `ValueError`; none exercise the CLI `ValueError → typer.Exit(1)` handler.

Consequence stated: yes — a regression in the `genparser.py` handler (wrong exit code, swallowed error, differently-formatted message) would go undetected; the CLI is the integration surface real downstream users hit, and only the library API was covered.

Finding legitimacy (bogus-reviewer check): consequence is real and the design lists this test as a *distinct* §7 bullet (design.md:565-566), separate from the library-API tests on 564 and 568. Confirmed the three prior tests at `test_regex_portability.py:316-365` call `.generate()`/`generate_parser()` directly — none spawn a subprocess. The CLI handler path was genuinely uncovered. Finding is legitimate, not bogus.

Disposition: Fixed. Action claims `test_genparser_cli_exits_nonzero_on_non_portable_grammar` added at `test_regex_portability.py:370-416`.

Evidence (diff `6bede5f..ba953c8`):
- Test added at `test_regex_portability.py:366-403` (disposition's "370-416" is approximate; the test is present). It writes `word := value:/[[:alpha:]]+/ ;` to a temp grammar, spawns `uv run --group dev python -m fltk.fegen.genparser gen-rust-parser <grammar> <out>`, asserts `returncode != 0`, and asserts `"[[:alpha:]]"` in `result.stderr`.
- CLI command name matches: `@app.command(name="gen-rust-parser")` at `genparser.py:368`.
- Handler exercised: `genparser.py:386-391` is `except (ValueError, RuntimeError, NotImplementedError) as e: typer.echo(f"Error: {e}", err=True); raise typer.Exit(1)`. Non-zero exit + message-on-stderr both covered.
- stderr assertion holds: the Rust generator raises `f"Regex pattern {term.value!r} is outside the portable subset ..."` (`gsm2parser_rs.py` wiring diff). `term.value` = `[[:alpha:]]+`, so `{term.value!r}` = `'[[:alpha:]]+'`, which contains substring `[[:alpha:]]`; it reaches stderr via the handler's `typer.echo(..., err=True)`.
- Wiring is at the correct site: `elif isinstance(term, gsm.Regex)` branch of `_gen_consume_term` (block at `gsm2parser_rs.py:783`), `check_regex_portable(term.value)` called *before* `self._regex_idx(term.value)` — per design §5.3 (not inside `_regex_idx`).
- Ran the test: PASSED (0.33s).

Assessment: fix addresses the named consequence at the named surface; verified passing. The asymmetry assertion (Rust rejects / Python accepts) is independently covered by `test_non_portable_grammar_python_generates_without_error`. Accept.

## Approved

1 finding: 1 Fixed verified. (slop notes: no findings.)

---

## Verdict: APPROVED

The single finding (scope-1) is legitimate, dispositioned Fixed, and the fix is verified end-to-end: the CLI subprocess test exists, exercises the `genparser.py:386-391` handler, asserts non-zero exit and the pattern on stderr, and passes. Commit ba953c8.
