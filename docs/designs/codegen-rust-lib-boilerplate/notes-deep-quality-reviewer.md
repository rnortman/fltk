# Quality Review Notes — codegen-rust-lib-boilerplate

Commit reviewed: 25bbfef (fltk), ea34388 (clockwork)

---

## quality-1

**File:line** `fltk/fegen/gsm2lib_rs.py:16` and `fltk/fegen/genparser.py:400`

**Issue** `_RUST_IDENT_RE` is defined identically in two modules:

```python
# gsm2lib_rs.py:16
_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# genparser.py:400
_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
```

`genparser.py` already imports `gsm2lib_rs`; the CLI guard at line 434 (`if not module_name or not _RUST_IDENT_RE.match(module_name)`) duplicates the validation that `LibSpec.validate()` / `RustLibGenerator.__init__` already perform via the copy in `gsm2lib_rs.py`. So there are two independent copies of the same pattern and two independent validation paths for the same constraint.

**Consequence** If the identifier rule ever needs to change (e.g. to accept raw identifiers or unicode), both copies must be updated in sync. The pre-validation in `genparser.py` will silently diverge from the generator's own validation. The pattern will also propagate to any future CLI commands that call other generators requiring Rust identifier validation.

**Fix** Delete `_RUST_IDENT_RE` from `genparser.py` and the pre-validation block in `gen_rust_lib` (lines 400 and 434-436). The `ValueError` already raised by `RustLibGenerator(spec)` (which calls `spec.validate()` in `__init__`) is caught at line 442 and converted to `typer.Exit(1)`. The pre-flight check in the CLI adds nothing beyond what the generator already does; removing it keeps a single validation site in `gsm2lib_rs.py`.

---

## quality-2

**File:line** `fltk/fegen/gsm2lib_rs.py:62-63`

**Issue** `cfg_python_gate: bool = False` is defined in `LibSpec` with a docstring, but the `generate()` method never reads it — the field has no effect whatsoever. Nothing in the test suite tests it or exercises it.

**Consequence** The field is dead API on a public dataclass. Future callers who set `cfg_python_gate=True` expecting `#[cfg(feature = "python")]` gates will silently get standard output with no gating. Because `LibSpec` is a frozen dataclass that is part of the public API surface, removing or renaming the field later is a breaking change for any downstream code that has already set it.

**Fix** Either implement the feature now (emit `#[cfg(feature = "python")]` around the `#[pymodule]` fn when the flag is set, and add a test), or remove the field entirely before this ships. Since the design explicitly scopes `cfg_python_gate` out (the in-scope targets — clockwork and `fltk._native` — do not use it), removing it is the cleaner choice. If it is genuinely wanted for `tests/rust_cst_fegen/src/lib.rs` in a future milestone, it can be added then with a real implementation.

---

## quality-3

**File:line** `fltk/fegen/genparser.py:406-412` (the `module_name` parameter to `gen_rust_lib`)

**Issue** `module_name` is declared as a `typer.Option` with no default value, which typer treats as a required option. In typer, a required option with no default is silently turned into a `None` default internally if the user omits it — the behaviour depends on the typer version. The existing test `test_gen_rust_lib_invalid_module_name_empty` passes `--module-name ""`, which reaches the CLI's explicit empty-string guard (`if not module_name`). But there is no test for the case where `--module-name` is omitted entirely. If typer allows the call to proceed with `module_name = None`, the guard `if not module_name` passes (since `not None` is `True`) but `_RUST_IDENT_RE.match(None)` raises `TypeError` rather than exiting cleanly.

**Consequence** A user who forgets `--module-name` gets an unhandled `TypeError` traceback instead of a clear usage error — poor UX and a gap between the CLI's contract and its behavior.

**Fix** Add a `required=True` annotation explicitly to the `typer.Option` call (e.g. `typer.Option("--module-name", ..., required=True)`) so typer rejects the missing option before control reaches the function body. Alternatively, restructure `module_name` as a `typer.Argument` (positional), which is consistent with how `output_file` is handled and makes omission a parse error. Add a CLI test that invokes `gen-rust-lib out.rs` with no `--module-name` and asserts a non-zero exit.
