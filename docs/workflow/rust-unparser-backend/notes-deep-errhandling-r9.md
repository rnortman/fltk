## errhandling-1

**File:** `fltk/fegen/genparser.py:520-521` / `fltk/unparse/gsm2unparser_rs.py:123`

**Broken error path:** `--protocol-module` is an unvalidated string. At line 520-521 of `genparser.py`, `protocol_module` is passed directly to `gen.generate_pyi(protocol_module)` without any format check. Inside `generate_pyi` (line 123 of `gsm2unparser_rs.py`), it is embedded verbatim in an f-string: `f"import {protocol_module} as _proto"`. An empty string produces `import  as _proto`; a value with spaces produces multi-token gibberish; a bare leading dot or trailing dot produces an invalid dotted name. None of these trigger an exception — `generate_pyi` returns normally, `gen.generate()` succeeds, `_write_output_file` writes the `.rs`, and `stub_path.write_text(pyi_text)` writes the `.pyi`. The generator exits 0 with both artifacts on disk.

**Why — where the error goes:** The validation gap is silent. No exception is raised, no log line is emitted, no non-zero exit code is produced. The only observable error surfaces later when pyright (or a downstream build) tries to parse the stub, at which point it reports a syntax error inside the generated `.pyi` file, with no pointer back to the `--protocol-module` argument that caused it.

**Consequence:** An operator (or CI) invoking the generator with a malformed `--protocol-module` value (typo, empty string, spaces) gets a green exit 0 and two committed artifacts, one of which is syntactically invalid Python. The on-call path is: pyright fails → investigate the generated stub → discover the import statement is malformed → trace back to the generator invocation → identify the `--protocol-module` value. That chain is long. The problem is not diagnosable from the pyright error alone. The `.rs` is a valid file; the `.pyi` must be deleted or corrected and the generator re-run.

**What must change:** Add a Python dotted-identifier regex validation (e.g. `^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$`) for `--protocol-module` in `gen_rust_unparser`, called before any generation, parallel to `_validate_cst_mod_path` for `--cst-mod-path`. On mismatch, echo a clear error (`"Error: --protocol-module '...' is not a valid Python module path"`) to stderr and raise `typer.Exit(1)` before any file is written. The same gap exists in `gen_rust_cst` (pre-existing, outside this diff's scope), so a shared `_validate_protocol_module` helper would keep the two consistent.

---

Commit reviewed: `bb96d0e78ae563c4cbad898225c16be02b4baba5`
