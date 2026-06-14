# Error-Handling Review — Rust-Bazel Packaging

Commits reviewed: fltk fafa6d7..9657025, Clockwork ece332a..6717614

---

errhandling-1  
**File**: `fltk/fegen/gsm2tree_rs.py` (module load, ~line 120)  
**Path**: `_bad_reserved` invariant check covers only `_RESERVED_CLASS_NAMES`, not `_RESERVED_CLASS_NAMES_SEEDED`.  
**Why**: The new `_RESERVED_CLASS_NAMES_SEEDED` dict contains names that ARE in `Py{CN}` form (e.g. `PyAnyMethods`, `PyListMethods`). The module-load guard that fires on the bad-shape invariant iterates only over `_RESERVED_CLASS_NAMES`. A future maintainer who incorrectly adds a `Child`- or `Label`-suffixed entry to `_RESERVED_CLASS_NAMES_SEEDED` will not be caught at module load — the guard is silent, and the seeded entry would block every grammar rule that happens to derive that identifier with no clear diagnostic.  
**Consequence**: On-call would see mysterious `ValueError: Generated Rust identifier 'XChild' collides` against the seeded sentinel `("(pyo3 import)", ...)` with no explanation that the seeded entry itself is mis-shaped. The guard exists to catch exactly this class of mistake but does not cover the new dict.  
**What must change**: Extend the `_bad_reserved` list comprehension (or add a parallel one) to also iterate `_RESERVED_CLASS_NAMES_SEEDED` with the same `endswith("Child")` / `endswith("Label")` predicate.

---

errhandling-2  
**File**: `rust.bzl`, `fltk_pyo3_cdylib` macro, Step 1 genrule shell command (~line 217)  
**Path**: The `for f in $(locations {rs_srcs}); do cp $$f $$OUTDIR/$$(basename $$f); done` loop copies every file delivered by `rs_srcs`. If `rs_srcs` emits a file whose `basename` is neither `cst.rs` nor `parser.rs` (e.g. if `generate_rust_parser` is later extended to emit a third file), the extra file is silently accepted — but the three declared `outs` (`lib.rs`, `cst.rs`, `parser.rs`) are fixed. Conversely, if a future `rs_srcs` emits fewer than the expected two files (regression in `generate_rust_parser`), the shell loop writes nothing to `cst.rs` or `parser.rs` and Bazel fails with an uninformative "declared output not created" error rather than a diagnostic naming the missing file.  
**Why**: The loop is unguarded; no verification that exactly `{cst.rs, parser.rs}` were written.  
**Consequence**: A maintainer extending `generate_rust_parser` (e.g. to emit a third `types.rs`) gets a cryptic Bazel action failure. The shell command itself has no way to report which file was missing or spurious. Debug time on CI is significant.  
**What must change**: After the loop, assert the two expected basenames are present: `test -f $$OUTDIR/cst.rs || { echo "ERROR: cst.rs not produced by rs_srcs"; exit 1; }` and the same for `parser.rs`. This converts the silent error into a diagnostic message.

---

errhandling-3  
**File**: `rust.bzl`, `fltk_pyo3_cdylib`, Step 3 ABI3 rename genrule (~line 264)  
**Path**: `cmd = "cp $< $@"` — `$<` expands to the first prerequisite of `srcs = [":" + name + "_cdylib"]`. `rules_rust` emits `lib<crate_name>.so`; the genrule assumes exactly one file. If `rules_rust` ever emits additional files (e.g. a `.pdb` or `.d`), `$<` still works (first file only), but if the `.so` is not the first file the rename silently copies the wrong file. There is no assertion that the source file ends in `.so`.  
**Why**: The `cmd` is not verified against the actual filename — the rename is based on positional assumption.  
**Consequence**: The `.abi3.so` exists but is the wrong file; `import clockwork_native` at runtime raises `ImportError: dynamic module does not define init function`. This is a silent build success followed by a runtime crash with no message pointing at the rename step.  
**What must change**: Use an explicit path rather than `$<`: `cmd = "cp $(location :" + name + "_cdylib) $@"` with the actual `lib<name>.so` path, or add a `test $$(basename $<) = lib{name}.so || { echo ...}` guard.

---

errhandling-4  
**File**: `clockwork/dsl/clockwork_native_lib.rs`, line 17–19  
**Path**: `register_submodule(m, "cst", cst::register_classes)?` and `register_submodule(m, "parser", parser::register_classes)?`.  
**Why**: Both calls propagate via `?` to PyO3's module initializer. This is correct for `PyResult` propagation — any error from `register_classes` (e.g. `add_class` failure, OOM in CPython's type registry) surfaces as a Python `ImportError` at `import clockwork_native`. No context is added before the `?` escape. The error message that reaches Python will be whatever pyo3/CPython emits for the failed `add_class`, with no indication of which submodule (`cst` or `parser`) failed.  
**Consequence**: If `cst::register_classes` fails, the resulting `ImportError` says nothing about "cst" — the submodule name passed to `register_submodule` is not threaded into the error. On-call sees a bare pyo3 error with no indication of which of the two submodules is the culprit.  
**What must change**: Either `register_submodule` in `fltk-cst-core` should annotate the returned error with the submodule name, or the call sites in `clockwork_native_lib.rs` should `.map_err(|e| PyErr::new::<pyo3::exceptions::PyImportError, _>(format!("registering 'cst': {e}")))` before `?`. This is low-severity but makes the consumer-authored lib.rs a diagnostic dead-end.

---

No findings in the generated `cst.rs` / `parser.rs` regeneration (the `?` propagation throughout PyO3 generated code is correct for the domain — PyResult is the right error channel for runtime Python-extension errors, and all PyO3 call-site `?` operators propagate to CPython's exception machinery as designed). The collision-detection `ValueError` raises at codegen time with sufficient context. The Bazel Starlark rule actions use no error-suppression idioms.
