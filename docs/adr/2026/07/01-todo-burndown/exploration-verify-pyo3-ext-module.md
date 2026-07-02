# Exploration: `verify-pyo3-ext-module`

## TODO text (verbatim, `TODO.md:13-15`)

> At implementation spike time, confirm that `extension-module` is active on the `@fltk_crates//:pyo3` target after `crate_universe` resolution. Run `bazel build //:native` on a clean checkout; if pyo3 links libpython the feature is not activated and a `crate.annotation(crate = "pyo3", crate_features = ["extension-module"])` is needed in `MODULE.bazel`'s `crate.from_cargo` block. Also confirm that dev-dep crates from the root workspace do not leak into the hub. Location: `MODULE.bazel` (`crate.from_cargo` block).

## All `TODO(verify-pyo3-ext-module)` occurrences

Code comment (the only in-code marker):

- `MODULE.bazel:38-44`, inside the `crate.from_cargo(name = "fltk_crates", ...)` block:

```
    # TODO(verify-pyo3-ext-module): confirm that the `extension-module` feature is
    # active on the @fltk_crates//:pyo3 target after crate_universe resolution.
    # In crate_universe `from_cargo`, pyo3's extension-module feature should be
    # activated via fltk-native's `default = ["extension-module"]` in root Cargo.toml.
    # Verify empirically at spike time with `bazel build //:native`; if pyo3 links
    # libpython the feature is missing and a `crate.annotation(crate = "pyo3",
    # crate_features = ["extension-module"])` annotation is needed here.
```

Ledger entry: `TODO.md:13-15`.

Prose references (no `TODO(...)` marker, discussion only, not part of the join-key system): `docs/adr/2026/06/13-rust-bazel-packaging/dispositions-deep.md:17-18,92-93`; `docs/adr/2026/06/13-rust-bazel-packaging/judge-verdict-deep.md:10,18-19,96`; `docs/adr/2026/06/14-rust-native-lib-shape/judge-verdict-prepass.md:13`; `docs/adr/2026/06/14-rust-backend-assessment/u5-build-ci.md:83,240,276,300`; `docs/adr/2026/06/14-rust-backend-assessment/recommended-actions.md:208,216`; `docs/adr/2026/06/14-rust-backend-assessment/ASSESSMENT.md:152`; `docs/adr/2026/06/14-rust-backend-assessment/u7-completeness-cruft.md:106`; `docs/adr/2026/06/14-rust-backend-assessment/a8-build-release.md:189,198,212`; `docs/adr/2026/06/30-codegen-protocol-pyi-outputs/exploration.md:394`.

The June 14 `rust-backend-assessment` ADR set (`a8-build-release.md`, `u5-build-ci.md`, `recommended-actions.md`, `ASSESSMENT.md`) treats the TODO as **UNRESOLVED** as of its writing (June 14), explicitly calling for a CI smoke job (`bazel build //:native` + `ldd`-no-libpython check) to close it. That assessment predates the current HEAD (`8fd5ecf`, main branch history through 2026-06-30/07-01 shown above) and does not reflect anything landed since.

## MODULE.bazel current state (ground truth)

Full `crate.from_cargo` block, `MODULE.bazel:29-46`:

```python
crate = use_extension("@rules_rust//crate_universe:extensions.bzl", "crate")
crate.from_cargo(
    name = "fltk_crates",
    cargo_lockfile = "//:Cargo.lock",
    manifests = [
        "//:Cargo.toml",
        "//crates/fltk-cst-core:Cargo.toml",
        "//crates/fltk-parser-core:Cargo.toml",
    ],
    # TODO(verify-pyo3-ext-module): ...
)
use_repo(crate, "fltk_crates")
```

**No `crate.annotation(...)` call exists anywhere in `MODULE.bazel`** (confirmed by full-file read — the file is 47 lines total and contains exactly the block above; no other `crate.` calls). The fallback the TODO describes as conditionally needed has not been added.

## Where `extension-module` actually gets set today

Two Bazel sites set `crate_features = ["extension-module", "python", ...]`, but both apply the features to the **consumer/top crate being compiled** (a `rust_shared_library` target), not to `@fltk_crates//:pyo3` via `crate.annotation`:

1. `BUILD.bazel:34-53` — the `:native` target itself:
```python
rust_shared_library(
    name = "native",
    srcs = glob(["src/**/*.rs"]),
    crate_name = "fltk_native",
    crate_features = [
        "extension-module",
        "python",
    ],
    ...
    deps = [
        "//crates/fltk-cst-core",
        "@fltk_crates//:pyo3",
    ],
)
```

2. `rust.bzl:479-505` — inside the `_build_pyo3_cdylib` macro (used by `generate_rust_parser` consumers like `bootstrap_native`), the generated `<name>_cdylib` `rust_shared_library` sets `crate_features = ["extension-module", "python"] + crate_features` (line 493) and depends on `Label("@fltk_crates//:pyo3")` (line 502).

Neither site touches `@fltk_crates//:pyo3` directly; the TODO's proposed fix location (`crate.annotation` inside `crate.from_cargo`) remains unused. Whether `@fltk_crates//:pyo3` itself resolved with `extension-module` active is a `crate_universe` feature-resolution question, independent of these `crate_features` lists on the *dependent* targets.

## Empirical verification performed this session

Ran `bazel build //:native` in this working tree (not a clean checkout — pre-existing Bazel cache present at `~/.cache/bazel/_bazel_rnortman/...`):

```
INFO: Analyzed target //:native (1 packages loaded, 3 targets configured).
Target //:native up-to-date:
  bazel-bin/libfltk_native.so
INFO: Elapsed time: 7.186s, Critical Path: 0.00s
INFO: 1 process: 1 action cache hit, 1 internal.
INFO: Build completed successfully, 1 total action
```

(Action cache hit — the .so was already built from a prior invocation in this environment, not built fresh in this session.)

`ldd bazel-bin/libfltk_native.so` output:

```
	linux-vdso.so.1 (0x00007fdfe6f87000)
	libgcc_s.so.1 => /lib64/libgcc_s.so.1 (0x00007fdfe6c6c000)
	libc.so.6 => /lib64/libc.so.6 (0x00007fdfe6c6c000)
	/lib64/ld-linux-x86-64.so.2 (0x00007fdfe6f89000)
```

No `libpython*.so` dependency present. This is the exact empirical signal the TODO specifies ("if pyo3 links libpython the feature is not activated") — and it does not link libpython, meaning the `extension-module` feature is active on the built artifact as produced by the current `crate.from_cargo` resolution plus the explicit `crate_features` on the `rust_shared_library` targets described above.

## Dev-dep leak concern — source ground truth

The TODO also asks to "confirm that dev-dep crates from the root workspace do not leak into the hub." Full contents of every `Cargo.toml` in the workspace were read:

- `Cargo.toml` (root/`fltk-native`, one of the three `manifests` fed to `crate.from_cargo`): no `[dev-dependencies]` section.
- `crates/fltk-cst-core/Cargo.toml` (one of the three `manifests`): no `[dev-dependencies]` section.
- `crates/fltk-parser-core/Cargo.toml` (one of the three `manifests`): no `[dev-dependencies]` section.
- `crates/fltk-unparser-core/Cargo.toml` and `crates/fltk-fmt-cli/Cargo.toml` (workspace members per `[workspace] members` in root `Cargo.toml:2`, but **not** listed in `crate.from_cargo`'s `manifests` at `MODULE.bazel:33-37`): no `[dev-dependencies]` section either.

`grep -n "dev-dependencies" -A 20` across all five `Cargo.toml` files in the workspace returned no matches. There are currently no dev-dependencies declared anywhere in the workspace, in any member manifest — so there is nothing dev-dep-shaped that could leak into the `fltk_crates` hub today, regardless of manifest-list membership.

`bazel query 'kind(rule, @fltk_crates//...)'` filtered for `criterion|proptest|dev` returned no output (no such crates in the resolved hub).

## Summary of facts (no prescription)

- The TODO's proposed fallback (`crate.annotation(crate = "pyo3", crate_features = ["extension-module"])` in `MODULE.bazel`'s `crate.from_cargo` block) has not been added; `MODULE.bazel` contains zero `crate.annotation` calls.
- `bazel build //:native` succeeds and the resulting `libfltk_native.so` links no libpython shared object, which is the empirical pass condition the TODO itself defines.
- The `extension-module` (and `python`) features are supplied explicitly via `crate_features` on the two `rust_shared_library` targets that depend on `@fltk_crates//:pyo3` (`BUILD.bazel:43-46` for `:native`, `rust.bzl:493` for the `_build_pyo3_cdylib` macro's generated cdylib target) — this is a different mechanism than the `crate.annotation`-on-pyo3 fallback the TODO names, and does not by itself prove what feature set `@fltk_crates//:pyo3` itself resolved with under `crate_universe`.
- No dev-dependencies exist in any workspace-member `Cargo.toml` (the three manifests fed to `crate.from_cargo`, plus the two workspace members excluded from that list), so the "dev-dep leak into the hub" half of the TODO has no current dev-dep source to leak from.
- The build run in this session was not on a "clean checkout" (the TODO's stated verification condition) — it hit Bazel's action cache (1 action cache hit, 0 fresh actions), reusing a `.so` built earlier in this environment.
