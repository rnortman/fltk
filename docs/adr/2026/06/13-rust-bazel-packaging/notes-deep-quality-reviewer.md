# Quality Review Notes — rust-bazel-packaging

Commit reviewed: 36eda0d (fltk), 45bc7fe (Clockwork).

---

## quality-1 — `fltk_pyo3_cdylib` macro uses unresolved string labels for cross-repo deps

**File:line:** `rust.bzl:229-231, 256`

**Issue:**

The `fltk_pyo3_cdylib` macro passes bare string labels to `rust_shared_library` (and implicitly to `native.genrule`):

```python
deps = [
    "//crates/fltk-cst-core",      # line 229
    "//crates/fltk-parser-core",    # line 230
    "@fltk_crates//:pyo3",          # line 231
] + deps
```

and at line 256:

```python
deps = ["@fltk//:native_py"],
```

In Bazel Bzlmod (Bazel 8, which is what Clockwork targets at 8.4.2), string label attributes passed to a rule instantiated inside a macro are resolved using the **calling BUILD file's repository mapping**, not the `.bzl` file's module context. When Clockwork calls `fltk_pyo3_cdylib` from `//clockwork/dsl/BUILD.bazel`:

- `"//crates/fltk-cst-core"` resolves to `@clockwork//crates/fltk-cst-core` — does not exist.
- `"//crates/fltk-parser-core"` resolves to `@clockwork//crates/fltk-parser-core` — does not exist.
- `"@fltk_crates//:pyo3"` — `fltk_crates` is an apparent repo name in FLTK's repo mapping, declared via `use_repo(crate, "fltk_crates")`. It is NOT in Clockwork's repo mapping. This label is unresolvable from Clockwork's BUILD context.
- `"@fltk//:native_py"` — `fltk` IS in Clockwork's repo mapping (it has `bazel_dep(name = "fltk")`). This one is correct.

The rule attr `_gen_tool`'s `default = Label("//:genparser")` (line 93) is correctly handled: `Label()` evaluated at `.bzl` load time binds to FLTK's module context. But the deps strings in the macro body are not `Label()` objects — they are plain strings that Bazel resolves at rule-instantiation time in the calling module's context.

**Consequence:**

The `fltk_pyo3_cdylib` macro silently compiles in FLTK's own smoke-test (where `//crates/fltk-cst-core` IS in FLTK's own repo), but fails with "no such target" or "no such repository" when called from any out-of-tree consumer — including Clockwork. This is the core advertised use case. The build would break for every external consumer, which is exactly the scenario CLAUDE.md calls out as load-bearing. If not caught before other teams adopt this surface, every consumer hits the same break.

**Fix:**

Use `Label()` to create repo-anchored label objects inside the macro, which are resolved at `.bzl` load time in FLTK's module context:

```python
deps = [
    Label("//crates/fltk-cst-core"),
    Label("//crates/fltk-parser-core"),
    Label("@fltk_crates//:pyo3"),
] + deps
```

and at the `py_library` call:

```python
deps = [Label("@fltk//:native_py")],
```

This is the canonical Bzlmod pattern for macros that instantiate rules with cross-repo deps. The same `Label()` fix applies to any future macros added to `rust.bzl`.

---

## quality-2 — Docstring says `@fltk//:native_so`; code depends on `@fltk//:native_py`

**File:line:** `rust.bzl:150`

**Issue:**

The `fltk_pyo3_cdylib` docstring under "Step 4" reads:

> carries @fltk//:native_so as a data dep so `import fltk._native` resolves

The actual code (line 256) depends on `@fltk//:native_py` (the `py_library` wrapper), which is correct: `native_py` carries `native_so` as `data` and puts it on the Python path. `native_so` alone is a `genrule` output, not a `py_library`, and would not place the `.so` on the import path. The docstring names the wrong target.

**Consequence:**

A reader of the docstring who tries to understand the invariant chain (`fltk._native` importable because of `native_py`'s `data` dep) gets the wrong target name, making the chain harder to audit. It also undermines the reliability of the docstring as a source of truth for future maintainers updating the dependency structure.

**Fix:**

Change line 150 from `@fltk//:native_so` to `@fltk//:native_py`.

---

## quality-3 — MODULE.bazel comment "spike and tests/* excluded" is inaccurate

**File:line:** `MODULE.bazel` (FLTK), crate extension block (~line 24 comment area); design §3.1

**Issue:**

The design (§3.1) and the `MODULE.bazel` comment state that `fltk-cst-spike` and `tests/*` crates are excluded from the `fltk_crates` hub. However, the `crate.from_cargo` call seeds from `//:Cargo.toml`, which is the workspace root. The workspace `[workspace]` members include `"crates/fltk-cst-spike"`. When `rules_rust` `crate_universe` processes a workspace-root `Cargo.toml`, it includes all workspace members by default. `fltk-cst-spike` and its transitive deps (including `criterion` as a dev-dep, though dev-deps are typically excluded from crate hub builds) will be part of the hub resolution. The `tests/*` fixture crates have separate `[workspace]` declarations, so those genuinely are excluded — that part of the claim is accurate.

**Consequence:**

Future maintainers adding crates to `fltk-cst-spike` may not realize those deps appear in the `fltk_crates` hub, potentially pulling in unintended crates. The discrepancy between documented scope and actual scope makes the hub harder to reason about over time. If fltk-cst-spike ever acquires large or conflicting deps, diagnosing hub resolution failures will be harder because the membership was not expected.

**Fix:**

Either: (a) update the comment to accurately state that `fltk-cst-spike` IS included as a workspace member, and note that `tests/*` fixture crates (which have their own `[workspace]` blocks) are excluded; or (b) explicitly exclude `fltk-cst-spike` from the hub by removing it from the workspace root `Cargo.toml` members list or using `crate.annotation` to exclude it. Option (a) is lower-risk for this increment.
