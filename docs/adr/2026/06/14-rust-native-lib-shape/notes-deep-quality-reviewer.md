# Quality Review — rust-native-lib-shape

Commit reviewed: 7a7ca4d

---

## quality-1

**File:line:** `rust.bzl:239-251` / `fltk_pyo3_cdylib` assemble-crate genrule

**Issue:** The `_assemble_crate` genrule unconditionally declares `crate_cst_rs` and `crate_parser_rs` as outputs and hard-fails if they are absent — even when `lib_rs` is omitted (the new auto-generate branch). The `bootstrap_native` smoke target (`BUILD.bazel:121-125`) invokes `fltk_pyo3_cdylib` with `lib_rs` omitted. The auto-generated lib.rs contains no `mod cst;`/`mod parser;` (that is the whole point of the refactor), so `rs_srcs` supplies only a grammar-derived `cst.rs` and `parser.rs` — and those are indeed present for `bootstrap_native` because it uses `bootstrap_rust_srcs`. But the macro itself has no guard: a future caller that passes `lib_rs=None` and `rs_srcs` that do not emit `cst.rs`/`parser.rs` (e.g. a runtime-only extension analogous to `_native`) will hit the hard `test -f $$OUTDIR/parser.rs || exit 1` error with a misleading message. The macro's `lib_rs = None` branch promises "generate lib.rs from the target name" but silently requires callers to still supply grammar-derived sources — a leaky abstraction.

**Consequence:** Every future invocation of `fltk_pyo3_cdylib` without a hand-authored `lib_rs` must supply `rs_srcs` that produce both `cst.rs` and `parser.rs` or it fails with a build-time error rather than a clear contract violation. The `lib_rs = None` abstraction looks like a "grammar-free lib.rs" convenience but secretly is not; this will bite the next person who tries to use the macro for a runtime-only extension (exactly the pattern this PR establishes).

**Fix:** Either (a) make `cst.rs`/`parser.rs` assembly conditional on whether the auto-generated lib.rs references them (check output of `gen-rust-lib` for `mod cst;`), or (b) document the macro parameter as "only for the standard cst+parser layout" and add a Starlark `fail()` when `lib_rs == None` and the generated lib would be CST-free, or (c) simplest — split the assembly genrule into two variants (with-grammar and span-only) selected on `lib_rs == None`. The immediate safeguard is a comment or guard that makes the "requires cst.rs + parser.rs in rs_srcs" constraint explicit in the `lib_rs == None` branch.

---

## quality-2

**File:line:** `fltk/fegen/genparser.py:458-466` — `gen_rust_lib` CLI, the `else` branch

**Issue:** When `--no-cst` is NOT passed, the code path is:

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

`LibSpec` is a frozen dataclass — the second construction is a workaround for the absence of a `replace`/`evolve` helper, copying every field manually. Any future addition of a field to `LibSpec` will silently leave this copy stale (the new field gets its default, not the value from `spec`). This is also the only place in the codebase that manually reconstructs a `LibSpec` by field copy; if `standard()` ever gains additional fields, this branch diverges silently.

**Consequence:** Maintenance hazard: adding a new `LibSpec` field requires remembering this hidden copy site. The standard Python pattern is `dataclasses.replace(spec, register_span_types=..., unknown_span_static=...)`, which is immune to field additions.

**Fix:** Replace the manual reconstruction with `dataclasses.replace(spec, register_span_types=register_span_types, unknown_span_static=unknown_span_static)`. Add `import dataclasses` at the top of `genparser.py` (or pass it through as a kwarg to the existing `LibSpec` constructor by restructuring to build the spec in a single pass).

---

## quality-3

**File:line:** `fltk/fegen/gsm2lib_rs.py:131-134` — UNKNOWN_SPAN comment in generated output

**Issue:** `RustLibGenerator.generate()` emits the comment:

```
// UNKNOWN_SPAN is set at module init (below) and exposed as `fltk._native.UnknownSpan`.
```

The comment hard-codes the module path `fltk._native.UnknownSpan` regardless of `spec.module_name`. For the `_native` module this is correct. For any other module that passes `unknown_span_static=True` (e.g. a hypothetical second runtime-hosting module), the generated comment will cite the wrong path.

**Consequence:** The comment will mislead readers of any non-`_native` lib.rs that uses `unknown_span_static`. The template already uses `spec.module_name` in one place (the `f"// UNKNOWN_SPAN is set..." ` f-string on line 132 does use `spec.module_name`) — but the Python attribute reference in the string says `fltk.{spec.module_name}.UnknownSpan`, which hardcodes the `fltk.` package prefix. A standalone extension not under `fltk.*` would get an incorrect comment.

**Fix:** The comment text on line 132 already uses an f-string: `f"// UNKNOWN_SPAN is set at module init (below) and exposed as \`fltk.{spec.module_name}.UnknownSpan\`."` — the `fltk.` prefix is the concrete bug. Either strip the package prefix (just `{spec.module_name}.UnknownSpan`) or omit the fully-qualified path from the comment entirely since it is only advisory. This is a one-character fix in the template string.

---

## quality-4

**File:line:** `tests/rust_poc_cst/Cargo.toml:12` — `crate-type = ["cdylib"]` only

**Issue:** `tests/rust_poc_cst/Cargo.toml` declares `crate-type = ["cdylib"]` only, unlike `crates/fegen-rust/Cargo.toml` which has `crate-type = ["cdylib", "rlib"]`. The Makefile adds `tests/rust_poc_cst` to `cargo-test-no-python` with `--no-default-features`, which runs native Rust unit tests. A cdylib-only crate cannot be used as a library dependency (no rlib), but more relevantly `cargo test --no-default-features` on a cdylib-only crate silently produces no test binary and exits zero — the `native_parser_tests`-style test coverage pattern (used in `fegen-rust`) would be impossible to add to `poc_cst` later.

**Consequence:** The `cargo-test-no-python` lane for `tests/rust_poc_cst` runs successfully but exercises nothing — it compiles the cdylib and exits zero with zero tests. Any native Rust tests added to `poc_cst` in the future would appear to pass without being run. The asymmetry with `fegen-rust` (which has rlib) is also confusing: the PoC fixture is the model for what downstream grammars should look like, so inconsistency here sets a bad example.

**Fix:** Add `"rlib"` to `crate-type` in `tests/rust_poc_cst/Cargo.toml`: `crate-type = ["cdylib", "rlib"]`. This matches the `fegen-rust` crate and every other pattern in the repo.
