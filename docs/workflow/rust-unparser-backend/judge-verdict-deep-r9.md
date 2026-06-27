# Judge verdict — deep review (rust-unparser-backend, r9)

Phase: deep. Base 90ffae8c..HEAD d07c9824. Round 1.
Notes: 7 reviewer files (correctness / security / efficiency = "No findings"); 5 findings.
Dispositions authored against bb96d0e; fixes landed in HEAD d07c9824 ("respond(deep-r9)").

## Added TODOs walk

No TODO-dispositioned findings this round. Grep of added lines in base..HEAD finds no
new `TODO(...)` comments. Nothing to score.

## Other findings walk

### errhandling-1 — Fixed
Claim: `--protocol-module` is unvalidated and interpolated verbatim into the stub's
`import {protocol_module} as _proto` line; empty / spaces / leading-or-trailing dot
produces a syntactically invalid `.pyi` with exit 0 and both artifacts on disk, only
failing later in a downstream type checker with no pointer back to the flag.
Premise verified: `gsm2unparser_rs.py:123` is `f"import {protocol_module} as _proto"` —
verbatim, no escaping. Real diagnosability gap.
Fix: added `_PROTOCOL_MODULE_RE = ^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$`
and `_validate_protocol_module` (`genparser.py:397-414`), which echoes
`Error: --protocol-module '...' is not a valid Python module path` and raises
`typer.Exit(1)` on mismatch. Called in both `gen_rust_cst` (`:354-355`) and
`gen_rust_unparser` (`:514-515`) at the point recommended — after the `--pyi-output
requires --protocol-module` check, before `_parse_grammar_raw` (`:517`) and well before
either `_write_output_file` (`:547`, `:551`). Empty/space/leading-dot/trailing-dot all
fail the regex. Tests `test_gen_rust_unparser_invalid_protocol_module` /
`test_gen_rust_cst_invalid_protocol_module` assert exit≠0, the message, and that
neither `.rs` nor `.pyi` is written.
Assessment: fix addresses the consequence (no artifacts, immediate diagnosable error)
at the named line; the sibling `gen_rust_cst` was also fixed via the shared helper the
finding itself recommended. Accept.

### test-1 — Fixed
Claim: the `except` guarding the `.pyi` stub write has no test; three behaviors
unverified — error message/exit code, the partial-artifact state (`.rs` written first
remains while `.pyi` does not), and that no raw traceback leaks.
Fix: `test_gen_rust_unparser_pyi_write_failure_exits_cleanly` points `--pyi-output` at
an existing directory (write_text raises IsADirectoryError → caught by
`_write_output_file`). Asserts exit≠0, `isinstance(result.exception, SystemExit)`,
`"Error:"` and `".pyi stub"` in output, and `output_rs.exists()` (documents the
partial-artifact state).
Assessment: covers all three named behaviors; pins the exit contract and the documented
partial state. Accept.

### reuse-1 — Fixed
Claim: the `.pyi` write try/except in `gen_rust_unparser` is byte-identical to the one
in `gen_rust_cst`; `_write_output_file` exists precisely to centralize the
write-with-error-contract pattern; duplication risks divergence.
Fix: `_write_output_file` gained `artifact_label="output file"` (`:272`); both inline
`.pyi` blocks replaced with `_write_output_file(stub_path, pyi_text, ".pyi stub")`
(`gen_rust_cst:379`, `gen_rust_unparser:551`). Error contract now single-sourced.
Assessment: duplication removed at both sites; reuses the named existing helper. Accept.

### quality-1 — Fixed
Claim: `gen-rust-unparser` Makefile target lacked `$(EXTRA_ARGS)`, so `gencode` bypassed
it with an inline raw invocation that can silently diverge from the target.
Fix: added `$(EXTRA_ARGS)` to the target (`Makefile:226`) and rerouted `gencode` through
`$(MAKE) gen-rust-unparser ... EXTRA_ARGS="--format-config ..."` (`Makefile:285-286`),
matching `gen-rust-cst`. Correctness reviewer independently confirmed no generation
drift in the regenerated fixture `unparser.rs`.
Assessment: closes the dead-letter target; the inline divergence is gone. Accept.

### quality-2 — Fixed
Same duplication as reuse-1, resolved by the same `_write_output_file` extension.
Assessment: Accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified (errhandling-1, test-1, reuse-1, quality-1, quality-2).
3 reviewers reported no findings (correctness, security, efficiency). No TODOs,
no Won't-Do.

---

## Verdict: APPROVED

All five dispositions are Fixed and verified against the HEAD diff: the
`--protocol-module` validation is sound (premise confirmed at `gsm2unparser_rs.py:123`)
and ordered before any write, the new tests exercise the previously-untested `.pyi`
write-failure and invalid-flag paths, and the duplication / Makefile-escape-hatch
cleanups landed as described. No disputed items.
HEAD: d07c98248ce36c6dc994a18c5c8e08ed4496aea2
