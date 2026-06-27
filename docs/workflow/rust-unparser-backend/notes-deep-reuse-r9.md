## reuse-1

File:line: `fltk/fegen/genparser.py:529–535` (new) vs `fltk/fegen/genparser.py:373–379` (pre-existing)

What's duplicated: The `.pyi` write block in `gen_rust_unparser` is byte-for-byte identical to the one in `gen_rust_cst`:

```python
if pyi_text is not None:
    stub_path = pyi_output if pyi_output is not None else output_file.with_suffix(".pyi")
    try:
        stub_path.write_text(pyi_text)
    except Exception as e:
        typer.echo(f"Error: Failed to write .pyi stub '{stub_path}': {e}", err=True)
        raise typer.Exit(1) from e
```

Existing function/utility: `_write_output_file` at `fltk/fegen/genparser.py:272` — the helper extracted specifically to share the `.rs` write-with-error-handling pattern across all subcommands. Its docstring already names `gen-rust-cst / gen-rust-parser / gen-rust-unparser / gen-rust-lib` as the sharing site.

Consequence: The error message text and exit-code contract for `.pyi` writes now lives in two places instead of one. A future third subcommand that adds `.pyi` output (e.g. a hypothetical `gen-rust-unparser` variant) would copy the block a third time. If the error message is ever revised (e.g. to include the grammar name for diagnosability), both blocks must be updated in sync; the `_write_output_file` pattern was introduced to prevent exactly this class of divergence.
