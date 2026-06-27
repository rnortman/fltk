## reuse findings — batch 8

Commit reviewed: 69fa04efa8bdb0524c0b3f9c4a4026da66d0c941

---

### reuse-1

**File:line:** `fltk/fegen/genparser.py:471–474` (new in diff); also at 357–361, 400–404, 559–562 (pre-existing)

**What's duplicated:** Identical 4-line try/except block that writes `src` to `output_file` with a CLI-friendly error message on failure:

```python
try:
    output_file.write_text(src)
except Exception as e:
    typer.echo(f"Error: Failed to write output file '{output_file}': {e}", err=True)
    raise typer.Exit(1) from e
```

This block appears byte-for-byte in `gen_rust_cst` (line 357), `gen_rust_parser` (line 400), `gen_rust_unparser` (line 471, introduced in this diff), and `gen_rust_lib` (line 559). The diff adds the third instance.

**Existing function/utility:** No shared helper exists; each command inlines the block directly.

**Consequence:** Each new Rust backend subcommand is expected to copy this block. If the error message format changes, or a decision is made to emit the error on stdout rather than stderr, all four sites diverge independently. A `_write_output_file(path: Path, text: str) -> None` helper (4 lines including the signature) would make this a single maintenance point.

---

### reuse-2

**File:line:** `fltk/fegen/genparser.py:444–446` (new in diff); also at 388–390 (pre-existing in `gen_rust_parser`)

**What's duplicated:** Identical 3-line `--cst-mod-path` validation block:

```python
if not _CST_MOD_PATH_RE.match(cst_mod_path):
    typer.echo(f"Error: --cst-mod-path {cst_mod_path!r} is not a valid Rust module path", err=True)
    raise typer.Exit(1)
```

The diff introduces this a second time in `gen_rust_unparser` (line 444), copying it verbatim from `gen_rust_parser` (line 388).

**Existing function/utility:** `_CST_MOD_PATH_RE` (line 372) is the shared regex, but no helper wraps the validation + error + exit logic.

**Consequence:** Any future command that also accepts `--cst-mod-path` must copy the block again. If the error message wording or the exit code changes it must be updated in both places. A `_validate_cst_mod_path(value: str) -> None` helper (raising `typer.Exit(1)` on mismatch) would centralise this.
