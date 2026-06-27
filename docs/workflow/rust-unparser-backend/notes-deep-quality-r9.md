## quality-1

**File:** `Makefile:225-226` (and `Makefile:285-288`)

The `gen-rust-unparser` Makefile target passes only `$(GRAMMAR)` and `$(RS_OUT)` and has no `$(EXTRA_ARGS)` escape hatch:

```makefile
gen-rust-unparser:
	uv run python -m fltk.fegen.genparser gen-rust-unparser $(GRAMMAR) $(RS_OUT)
```

`gen-rust-cst` already carries `$(EXTRA_ARGS)` for exactly this situation. Because `gen-rust-unparser` does not, the `gencode` rule cannot call `$(MAKE) gen-rust-unparser EXTRA_ARGS=--format-config ...` when it needs to pass `--format-config` for the fixture grammar. Instead it bypasses the target entirely and inlines a raw `uv run python -m fltk.fegen.genparser gen-rust-unparser ...` invocation. The `gen-rust-unparser` target is now a dead letter for callers who need `--format-config` (or `--protocol-module`, or `--pyi-output`).

**Consequence:** The target and the `gencode` invocation can diverge silently — if the invocation style changes (e.g., the module path moves), only the target is updated and the inline call rots. The pattern will propagate: any new Makefile rule that needs `--format-config` on the unparser will face the same workaround rather than a supported parameter. `gen-rust-parser` has the same gap, but that pre-dates this batch; this batch extends the gap to `gen-rust-unparser` without closing it.

**Fix:** Add `$(EXTRA_ARGS)` to `gen-rust-unparser`, matching `gen-rust-cst`:

```makefile
gen-rust-unparser:
	uv run python -m fltk.fegen.genparser gen-rust-unparser $(GRAMMAR) $(RS_OUT) $(EXTRA_ARGS)
```

Then `gencode` can use:

```makefile
$(MAKE) gen-rust-unparser GRAMMAR=... RS_OUT=... EXTRA_ARGS=--format-config fltk/fegen/test_data/rust_parser_fixture.fltkfmt
```

---

## quality-2

**File:** `fltk/fegen/genparser.py:529-535` (and the parallel block at `:373-379` in `gen_rust_cst`)

Both `gen_rust_cst` and `gen_rust_unparser` write the `.pyi` stub with an inline try/except that duplicates `_write_output_file()`:

```python
try:
    stub_path.write_text(pyi_text)
except Exception as e:
    typer.echo(f"Error: Failed to write .pyi stub '{stub_path}': {e}", err=True)
    raise typer.Exit(1) from e
```

`_write_output_file()` exists precisely to centralise this pattern. Its implementation is path-agnostic (`output_file.write_text(src)` on an arbitrary `Path`); only the docstring says "generated `.rs` artifact". The inline blocks differ only in the error-message noun ("`.pyi` stub" vs "output file"), which is marginal justification for duplication.

**Consequence:** A third command that emits both `.rs` and `.pyi` will copy the pattern a third time. A change to the error contract (exit code, message format, structured logging) requires three edits instead of one.

**Fix:** Extend `_write_output_file()` to accept an optional `artifact_label` parameter (defaulting to `"output file"`) and call it for the stub:

```python
def _write_output_file(output_file: Path, src: str, artifact_label: str = "output file") -> None:
    try:
        output_file.write_text(src)
    except Exception as e:
        typer.echo(f"Error: Failed to write {artifact_label} '{output_file}': {e}", err=True)
        raise typer.Exit(1) from e
```

Then both stub writes become `_write_output_file(stub_path, pyi_text, ".pyi stub")`.
