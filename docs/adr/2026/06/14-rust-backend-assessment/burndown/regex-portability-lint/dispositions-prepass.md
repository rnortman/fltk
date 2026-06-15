# Pre-pass dispositions — regex-portability-lint

Reviewer notes reviewed: notes-prepass-slop.md, notes-prepass-scope.md
Commit reviewed: 6bede5f (base: 034252d)

---

## slop findings

No findings — notes-prepass-slop.md contains "No findings."

---

## scope-1

**Finding:** Missing subprocess test for `genparser gen-rust-parser` CLI path. Design §7 lists as a distinct bullet: invoking `genparser gen-rust-parser` on a non-portable grammar exits non-zero with the message on stderr (exercises `genparser.py:386-391`). The three existing integration tests call `RustParserGenerator.generate()` directly; none exercised the `ValueError → typer.Exit(1)` handler.

**Disposition:** Fixed

**Action:** Added `test_genparser_cli_exits_nonzero_on_non_portable_grammar` to `tests/test_regex_portability.py:370-416`. The test writes a grammar with `[[:alpha:]]+` to a temp file, spawns `uv run python -m fltk.fegen.genparser gen-rust-parser` as a subprocess, asserts `returncode != 0`, and asserts `"[[:alpha:]]"` appears in stderr. Test passes (127/127).

**Severity assessment:** Without this test, a regression in `genparser.py`'s `ValueError` handler (wrong exit code, swallowed error, wrong message format) would go undetected. The CLI is the integration surface real downstream users hit; this was the only uncovered path in the design's §7 test plan.
