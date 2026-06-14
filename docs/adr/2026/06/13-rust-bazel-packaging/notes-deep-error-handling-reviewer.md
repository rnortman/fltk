# Error-Handling Review — Rust/Bazel Packaging

Commit reviewed: 36eda0d (fltk), 45bc7fe (clockwork)

---

## errhandling-1

**File:** `rust.bzl` (fltk), `fltk_pyo3_cdylib` macro, Step 3 (ABI3 rename genrule), line 239–244

**Broken error path:**

```python
native.genrule(
    name = name + "_so",
    srcs = [":" + name + "_cdylib"],
    outs = [abi3_so],
    cmd = "cp $< $@",
)
```

The `$<` expansion in a genrule with a `rust_shared_library` source expands to _all_ files in the provider's `DefaultInfo.files` depset. For `rules_rust` targets that is not guaranteed to be a single `.so`; it may include a `.d` depfile, `.pdb` (on Windows — out of scope but harmless), or debug-info sidecar files. If `rules_rust` emits more than one file into `DefaultInfo`, `$<` silently copies only the first file in shell expansion order, which is not necessarily the `.so`. The rule would then produce a syntactically valid but non-functional `.abi3.so`, failing only at `import` time with an opaque `ImportError` or `OSError: invalid ELF`, with no build-time error and no message pointing at the packaging step.

**Why:** `$<` in Bazel genrules expands to the full `$(SRCS)` list when the source dep provides multiple files; there is no "single-file guard" built in. The `cp $< $@` pattern is correct only when the source provides exactly one file.

**Consequence:** If a future `rules_rust` version or platform adds a sidecar to the `rust_shared_library` outputs, the renamed `.abi3.so` will silently contain wrong content. On-call sees `ImportError: dynamic module does not define init function` or a corrupt-ELF error at test time, with no pointer to the rename step.

**What must change:** Replace `$<` with an explicit `$(location :<name>_cdylib)` (which selects the single declared output file) or add a shell guard:

```
cmd = """
    SO=$$(echo $(locations :{name}_cdylib) | tr ' ' '\\n' | grep '\\.so$$' | head -1)
    test -n "$$SO" || (echo "No .so found in cdylib outputs" >&2; exit 1)
    cp "$$SO" $@
""".format(name = name),
```

The same pattern applies to the `:native_so` genrule in `BUILD.bazel` (line 50–55).

---

## errhandling-2

**File:** `rust.bzl`, `fltk_pyo3_cdylib` macro, Step 1 (crate-source assembly genrule), lines 201–216

**Broken error path:**

```python
cmd = """
    OUTDIR=$$(dirname $(location {crate_lib_rs}))
    cp $(location {lib_rs}) $$OUTDIR/lib.rs
    for f in $(locations {rs_srcs}); do
        cp $$f $$OUTDIR/$$(basename $$f)
    done
""".format(...)
```

The `for` loop iterates over `$(locations {rs_srcs})` — all files emitted by the `generate_rust_parser` target — and copies each one using `$(basename $$f)`. If `generate_rust_parser` ever emits a third file (e.g. a future `.pyi` stub, a `.d` depfile, or any additional output added to its `DefaultInfo`), the loop silently copies it into the crate directory alongside `cst.rs` and `parser.rs`. This will not fail the genrule, but it will pollute the crate source tree with an unexpected file. Rustc may then encounter a name collision or unexpected module, producing a cryptic compile error with no pointer to the assembly step.

The converse failure is also unguarded: if `generate_rust_parser` emits fewer than two files (e.g. due to a future refactor), the declared `outs` (`cst.rs`, `parser.rs`) will not be produced, causing a Bazel "declared output was not created" error. That error is loud, but it names the genrule's declared outputs, not the root cause (missing upstream files), so diagnosis is indirect.

**Consequence:** Future additions to `generate_rust_parser` outputs corrupt the assembled crate silently or cause confusing compile errors; the on-call has no structured signal pointing at the assembly genrule.

**What must change:** Replace the open-ended loop with explicit `cp $(location {rs_srcs_name}/cst.rs)` / `cp $(location {rs_srcs_name}/parser.rs)` using the known fixed basenames, and add existence assertions before each copy. This pins the assembly to exactly the files it expects and makes unexpected additions a non-issue.

---

## errhandling-3

**File:** `rust.bzl`, `fltk_pyo3_cdylib` macro, Step 4 (py_library wrapper), lines 253–259

**Broken error path:**

```python
py_library(
    name = name,
    data = [":" + name + "_so"],
    deps = ["@fltk//:native_py"],
    imports = ["."],
    visibility = visibility,
)
```

The `deps = ["@fltk//:native_py"]` label is resolved relative to the _consumer's_ package (Clockwork's `clockwork/dsl/`). In a Bzlmod context, `@fltk//:native_py` is the correct absolute label and will resolve correctly for Clockwork. However, when `fltk_pyo3_cdylib` is called _within_ the FLTK repo itself (e.g. for an in-FLTK smoke test), `@fltk//:native_py` may resolve to the module itself, creating a self-reference cycle or at minimum an ambiguous label depending on how the Bazel module resolution handles `@fltk` in the root context. There is no guard against this, and the failure mode — a circular dep error or a silent no-op — is not surfaced at load time.

**Consequence:** Any in-FLTK use of `fltk_pyo3_cdylib` (e.g. a future smoke test that exercises the full cdylib path in FLTK's own CI) may silently produce a circular dependency or an unresolvable label without a clear error message.

**What must change:** The macro should use `Label("@fltk//:native_py")` (a `Label` literal rather than a string) so Bzlmod resolves it relative to the FLTK module at macro-definition time rather than at call-site time. This is the standard `rules_rust` / Starlark pattern for macros that reference their own module's targets across repo boundaries.

---

## errhandling-4

**File:** `clockwork/dsl/clockwork_rust_roundtrip_test.py`, `test_fltk_native_span_is_rust_path`, lines 17–28

**Broken error path:**

```python
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    import fltk._native as fltk_native  # noqa: PLC0415
```

Python's import system caches modules in `sys.modules`. If `fltk._native` was already imported before this `with` block (e.g. because `clockwork_native` was imported at module level, or because test collection imported something that triggered `fltk._native`), the `import` statement inside the `with` block is a no-op — the module is returned from cache, and no warnings are emitted. The test would then pass vacuously: `span_fallback_warnings` would be empty not because the Rust path is live but because `fltk._native` was already imported on a prior call (whether Rust or pure-Python) and the `warnings.catch_warnings` block captured nothing.

The test as written detects the fallback only on the _first_ import of `fltk._native` in the process. In Bazel py_test isolation each test binary is a fresh process, so this is currently safe; but it is a fragile guarantee that depends on import ordering. If `test_clockwork_native_parses_module` runs first (it imports `clockwork_native`, which triggers `fltk._native` via the cdylib), `test_fltk_native_span_is_rust_path` will see a cached module and miss any fallback.

**Consequence:** The test that is supposed to assert the Rust path is live can silently pass even when `fltk._native` is on the pure-Python fallback path, if test ordering causes prior import caching. The guard that the design depends on (AC #3) becomes a no-op.

**What must change:** Check `sys.modules.get("fltk._native")` before the `with` block. If already present, assert `hasattr(fltk._native, "Span")` and check for the absence of the pure-Python `SourceText` sentinel (e.g. `type(fltk_native.Span).__module__ == "fltk._native"` for the Rust type). Alternatively, assert directly on `fltk._native.Span` type identity (`fltk._native.Span` from the Rust path is a `PyType` registered by the cdylib, distinguishable from the pure-Python class by its module attribute) rather than relying on warning capture.

---

## errhandling-5

**File:** `rust.bzl`, `fltk_pyo3_cdylib` macro, Step 2 (`rust_shared_library`), lines 219–234

**Broken error path:**

```python
deps = [
    "//crates/fltk-cst-core",
    "//crates/fltk-parser-core",
    "@fltk_crates//:pyo3",
] + deps,
```

When `fltk_pyo3_cdylib` is called from a consumer module (Clockwork), the labels `//crates/fltk-cst-core` and `//crates/fltk-parser-core` resolve relative to the _call site_ (Clockwork's repo), not relative to FLTK's repo. In Bzlmod, bare `//...` labels in a macro defined in `@fltk` but called from `@clockwork` resolve relative to `@clockwork`, not `@fltk`. The design intends these to be `@fltk//crates/fltk-cst-core`, etc. Without `Label("@fltk//crates/...")`, these deps silently resolve to nonexistent Clockwork targets, producing "no such package" build errors rather than a clear "wrong repo" message.

(Note: This may already be handled by Bazel's relative-label semantics within `.bzl` files — Bazel resolves string labels in `.bzl` files relative to the repository where the `.bzl` file lives, not the call site. However, this behavior is documented as a Starlark nuance and may not hold for all contexts, especially with Bzlmod's module remapping. The correct defensive form is `Label("@fltk//crates/fltk-cst-core")` to make the resolution unambiguous.)

**Consequence:** If Bazel label resolution does not apply `.bzl`-origin semantics here, the consumer build silently links against nonexistent or wrong targets, producing either a "no such package" error (loud but not well-attributed) or, worse, picks up a Clockwork-local target with the same path. On-call cannot distinguish "wrong crate linked" from "Clockwork has no such target" without reading the full dep graph.

**What must change:** All cross-repo labels in the macro body should be `Label("@fltk//...")` literals. This is the pattern `rules_rust` macros use for their own internal deps and is the only guaranteed-correct form under Bzlmod.
