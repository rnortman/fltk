## errhandling-1

**File:** `fltk/fegen/gsm2lib_rs.py` lines 130–134 (generated in `generate()`)

**Broken error path:** The generated `src/lib.rs` for the runtime-only `_native` module contains:

```rust
UNKNOWN_SPAN
    .set(m.py(), unknown_span_obj)
    .expect("UNKNOWN_SPAN already set; module initialized twice");
```

`PyOnceLock::set` returns `Err` when the cell is already filled; `expect` converts that into a hard panic.  This is *intentional* for the double-init case, and correct — a second `import fltk._native` that somehow re-ran the `#[pymodule]` body would be a runtime invariant violation, and panicking is the right response.  **No change needed here.**

However, the line immediately before it:

```rust
let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();
```

`Py::new` can fail with a `PyErr` (e.g., OOM, or if the Python heap is in a broken state).  The `?` propagates it as a `PyResult::Err`, which pyo3 converts to a Python `RuntimeError` on the calling side.  This is fine — it is not swallowed, and the caller (the Python import machinery) receives the error.  But there is no diagnostic log line; all the caller sees is a generic pyo3 `RuntimeError`.  **The existing TODO(native-submodule-error-context) note in `py_module.rs` covers the analogous gap in `register_submodule`; the gap for `Py::new` failure in the generated span-init code is not noted anywhere.**

**Consequence:** If `Py::new(m.py(), Span::unknown())` fails at import time of `fltk._native`, the Python import raises a `RuntimeError` with pyo3's default message and no indication that the failure was in span-object creation vs. class registration.  On-call cannot distinguish "Span class itself failed to construct an unknown-span sentinel" from "something in submodule registration failed."

**What must change:** Either (a) add a brief structured message in the generated code wrapping the `Py::new` failure:

```rust
let unknown_span_obj = Py::new(m.py(), Span::unknown())
    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(
        format!("_native: failed to create UnknownSpan sentinel: {e}")
    ))?
    .into_any();
```

or (b) document in a TODO that this case is intentionally left to pyo3's default message (as has been done for `register_submodule`).  Option (b) is lightweight; option (a) is the right fix.

---

## errhandling-2

**File:** `fltk/fegen/genparser.py` lines 451–466 (`gen_rust_lib`)

**Broken error path:** When `--no-cst` is *not* passed but `--register-span-types` or `--unknown-span-static` *are* passed, the CLI silently rebuilds the `LibSpec` from `standard()` but strips the `register_span_types`/`unknown_span_static` values, then reconstructs:

```python
spec = gsm2lib_rs.LibSpec.standard(module_name, with_parser=not no_parser)
if register_span_types or unknown_span_static:
    spec = gsm2lib_rs.LibSpec(
        module_name=spec.module_name,
        submodules=spec.submodules,
        register_span_types=register_span_types,
        unknown_span_static=unknown_span_static,
    )
```

This combination (`--register-span-types` without `--no-cst`) is semantically odd — it produces a lib.rs that registers both span types *and* grammar submodules, which no current consumer intends.  The CLI has no validation or warning for this combination, so a caller who accidentally passes `--register-span-types` without `--no-cst` gets a silently generated output that is neither a runtime-only lib nor a standard grammar lib.

**Consequence:** The generated file is written without error; only the downstream Rust compilation (or a discerning human reader) would detect the misshapen output.  No diagnostic reaches the CLI caller at the time of generation.  On-call would see a Rust compile error or a runtime module shape mismatch with no indication that the generator was invoked with incompatible flags.

**What must change:** Either (a) add a `ValueError`/`typer.echo` + `raise typer.Exit(1)` guard rejecting `--register-span-types` or `--unknown-span-static` without `--no-cst` (the combination is not a documented use case and has no valid consumer); or (b) if combined span+submodule libs are a legitimate future feature, add a `--warn` or simply document the combination explicitly in the help text.  Option (a) is safer given the current design.

---

## errhandling-3

**File:** `fltk/fegen/gsm2lib_rs.py` line 97 (`RustLibGenerator.__init__`)

**Broken error path:** `spec.validate()` is called in `__init__`, which raises `ValueError` on bad specs.  This is correct.  However, `generate()` is a pure string-building function; if `validate()` did not catch a problem (e.g., a `Submodule` whose `register_fn` field is something that passed `_RUST_IDENT_RE` but is not actually a reachable Rust function), the generated source is emitted silently.

This is not an error-handling gap in the strict sense — the validation is best-effort for identifier syntax — but there is one latent case: **`Submodule` instances constructed directly (not via `LibSpec.standard()`) with a custom `register_fn` are validated for Rust identifier syntax but not for the convention that the fn must be named `register_classes`.**  If a caller passes a `Submodule` with `register_fn="wrong_fn"`, the generated Rust code compiles to `wrong_fn::register_classes` — no, actually it compiles to `mod_name::wrong_fn` — which will fail at Rust compile time with "unresolved function," not at generation time.  The error message from `cargo build` is the only signal.

**Consequence:** A caller using the library API with a non-standard `register_fn` name gets a late Rust compile error rather than a fast Python-level validation error.  This is acceptable for a code generator, and the current design is correct; noting it for completeness.  No change strictly required, but a comment in `Submodule.validate()` acknowledging "Rust identifier validity is the limit of what we can verify here" would reduce reviewer surprise.

---

No other findings. The `register_submodule_impl` error wrapping in `py_module.rs` is thorough — each step (module creation, `register` call, `add_submodule`, `sys.modules` insertion) wraps its `?` with a contextual `PyRuntimeError` that names the qualified module path.  The `src/lib.rs` `expect` for double-init is the correct panic-on-invariant-violation pattern.  The `genparser.py` file-write error path (`Exception` → echo + `Exit(1)`) is complete.  The clockwork diff removes a hand-authored `lib.rs` that contained a comment; no error-handling code changes there.
