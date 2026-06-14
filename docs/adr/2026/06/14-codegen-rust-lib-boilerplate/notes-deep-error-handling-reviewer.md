# Error-Handling Review — codegen-rust-lib-boilerplate

Commits reviewed: fltk 7200d9c..25bbfef, clockwork 6ede250..ea34388

---

## errhandling-1

**File:** `fltk/fegen/genparser.py:438–443`

**Broken path:** `gen_rust_lib` pre-validates `module_name` before constructing `LibSpec`, but `LibSpec.standard` passes the already-validated name straight through to `LibSpec.__init__`, which then calls `LibSpec.validate()` again inside `RustLibGenerator.__init__`. If `validate()` were to raise `ValueError` here it would be caught and printed as `"Error: <msg>"`. However, the pre-validation in `gen_rust_lib` uses a locally-defined `_RUST_IDENT_RE` (line 400), while `gsm2lib_rs._validate_rust_ident` uses its own copy (line 16). These two regexes are identical right now, so the double-check is redundant rather than wrong. **The real issue is that the two regexes are separate copies with no shared constant or test asserting they are the same.** If one is updated without the other, CLI validation will diverge from library validation silently — a user-facing rejection at the CLI could differ from the library's acceptance (or vice versa), producing inconsistent behaviour with no diagnostic.

**Consequence:** If the regexes drift, invalid identifiers may pass CLI pre-check but be rejected inside the library with a generic `"Error: <msg>"` (losing which check failed), or valid identifiers may be rejected at the CLI with the wrong message before the library gets to validate them. An on-call engineer sees inconsistent errors with no indication which code path applied.

**Change needed:** Extract the pattern into a single shared constant (`gsm2lib_rs._RUST_IDENT_RE`) and import it into `genparser.py` instead of redeclaring it. The CLI-level `_RUST_IDENT_RE` at line 400 of `genparser.py` is redundant and should be removed in favour of the one from `gsm2lib_rs`.

---

## errhandling-2

**File:** `fltk/fegen/genparser.py:438–443` (`gen_rust_lib`) and `genparser.py:467–478` (`gen_rust_native_lib`)

**Broken path:** Both commands catch `ValueError` from `RustLibGenerator(spec).generate()` and surface it as `"Error: <msg>"` with exit code 1. However, `RustLibGenerator.__init__` calls `spec.validate()`, which raises `ValueError` on invalid identifiers. A `ValueError` from `__init__` is not the same kind of error as one from `generate()`: the former is a programming error (caller built a bad spec), while the latter would signal an unexpected generator internal invariant violation. Both are caught by the same `except ValueError` block covering only the `generate()` call (lines 439–443 and 468–472), not the constructor. If `RustLibGenerator.__init__` raises (because `spec.validate()` was bypassed or the spec is wrong), the exception propagates uncaught to typer, which will produce an unformatted traceback instead of a clean `"Error: ..."` message.

In practice, in `gen_rust_lib` the spec is built from an already-validated module name via `LibSpec.standard`, so `validate()` inside `__init__` won't fire. In `gen_rust_native_lib` the spec is hardcoded via `native_spec()` and will never be invalid. So the consequence is latent rather than immediately reachable — but it means that future callers who construct a `LibSpec` manually and then call `RustLibGenerator(spec).generate()` in a try/except covering only `generate()` will be surprised when `__init__` raises outside the guarded region.

**Consequence:** Unexpected traceback instead of a clean error message if a `LibSpec` with invalid identifiers is passed to `RustLibGenerator`. Not currently reachable via the CLI paths but is a trap for any future caller or test that constructs a spec with a bad identifier and wraps only `generate()`.

**Change needed:** Either move the `try/except ValueError` to cover both construction and generation (`try: gen = RustLibGenerator(spec); src = gen.generate()`) or document explicitly that `__init__` validates eagerly and that construction should be included in the guard. The former is simpler.

---

## errhandling-3

**File:** `fltk/fegen/gsm2lib_rs.py:283–284` (`RustLibGenerator.__init__`)

**Broken path:** `RustLibGenerator.__init__` calls `spec.validate()` which raises `ValueError` for invalid identifiers. This is the right design for a library API. However, `LibSpec.validate()` validates `module_name` and each `Submodule`'s three fields, but does NOT validate the `cfg_python_gate` boolean field or the boolean flags `register_span_types` / `unknown_span_static`. Those are booleans and cannot be invalid. The gap is a different one: `LibSpec` is a `frozen=True` dataclass and all string fields are validated. But there is no validation that `submodules` is non-empty when both `register_span_types` and `unknown_span_static` are False — a `LibSpec(module_name="x", submodules=())` produces a lib.rs with a `#[pymodule]` body that only contains `Ok(())`, which is syntactically valid Rust but will register nothing. This is silently accepted — no warning or error is raised — and the resulting crate compiles but is unusable.

**Consequence:** A caller who accidentally passes `submodules=()` gets a silently generated lib.rs with an empty `#[pymodule]`. No import at Python side will find any classes. No diagnostic at generation time. An on-call engineer debugging "why are there no CST classes" gets no clue from the generation step.

**Change needed:** `LibSpec.validate()` should warn or raise if `submodules` is empty and neither `register_span_types` nor `unknown_span_static` is True. Alternatively, document this explicitly. An empty-submodule `LibSpec` is not a use case the design describes, so a `ValueError` is appropriate.

---

## errhandling-4

**File:** `fltk/fegen/rust.bzl:246–247` (the `_assemble_crate` genrule `test -f` guards)

**Broken path:** The assembly genrule checks that `cst.rs` and `parser.rs` both exist after copying from `rs_srcs`:

```
test -f $$OUTDIR/cst.rs || { echo "ERROR: ..."; exit 1; }
test -f $$OUTDIR/parser.rs || { echo "ERROR: ..."; exit 1; }
```

However, when `lib_rs` is omitted and `gen_lib_rs_out = name + "_gen_lib/lib.rs"` is generated by the preceding `genrule`, the `_assemble_crate` genrule lists `lib_rs = ":" + name + "_gen_lib"` as a `srcs` entry. If the `_gen_lib` genrule fails (e.g. `gen-rust-lib` exits non-zero due to an invalid module name derived from `name`), Bazel will refuse to run `_assemble_crate`. That is correct Bazel behaviour, and the `_gen_lib` action itself will surface the error. No silent failure here.

However: the assembly genrule uses `$(location {lib_rs})` where `lib_rs` is now `:name_gen_lib` (a target label, not a file label). When `lib_rs` is a genrule that emits exactly one file (`gen_lib_rs_out`), `$(location :name_gen_lib)` expands to that file. If the genrule ever emits more than one file, `$(location ...)` would be ambiguous and the build fails with an opaque Bazel error rather than a diagnostic naming the root cause. This is fragile but not a current failure mode since the `_gen_lib` genrule is defined with exactly one `outs` entry.

**Consequence:** If `_gen_lib` is ever extended to emit more than one file, the `_assemble_crate` shell command will fail with a non-obvious Bazel expansion error. Low-severity latent issue; worth noting but not urgent.

**Change needed:** Use `$(location {gen_lib_rs_out})` (the specific file path) rather than `$(location :{name}_gen_lib)` (the target) in the assembly command when constructing the auto-generated case. Currently the format string uses `lib_rs` which resolves to the label, not the file.

---

## errhandling-5 (acknowledged/deferred in diff, recorded for completeness)

**File:** `crates/fltk-cst-core/src/py_module.rs:86–89` (TODO comment) and generated `src/lib.rs:25–26`

**Broken path:** `register_submodule` propagates `register_classes` errors (and `add_submodule` errors) by wrapping them in a `PyRuntimeError` with context naming the `qualified_name`. The TODO in the diff notes that when called from a consumer lib.rs (the generated or hand-authored one), the caller site does `register_submodule(m, "cst", cst::register_classes)?;` — using `?` with no added context. If `register_submodule` itself returns an error, the error message already contains the submodule name (via `register_submodule_impl`'s `map_err` wrappers at lines 159–163 and 164–167). So the TODO is about the *caller side* not annotating, which is not a concern because the callee already wraps.

However, the existing `?` propagation in the generated `src/lib.rs` from `register_submodule` results in a `PyResult::Err` that bubbles up to PyO3's module-init machinery, which converts it to a Python `ImportError`. The diagnostic message does include the submodule name because of the wrapping in `register_submodule_impl`. The TODO is therefore already partially addressed by the existing wrapping inside `register_submodule_impl`.

This finding is **already acknowledged as TODO(native-submodule-error-context)** in the diff and tracked in `TODO.md`. No change needed; noting here for completeness.
