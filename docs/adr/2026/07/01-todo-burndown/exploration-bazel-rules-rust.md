# Exploration: `TODO(bazel-rules-rust)` Adversarial Verification

Base commit: `8fd5ecf` (HEAD of `main` at task start). All checks below were run live against this checkout.

## TODO.md claim (verbatim, `TODO.md:7-11`)

> Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.
>
> Implementation in progress — see ADR at `docs/adr/2026/06/13-rust-bazel-packaging/`.

## Is `rules_rust` in `MODULE.bazel`?

Yes. `MODULE.bazel:6`: `bazel_dep(name = "rules_rust", version = "0.70.0")`. `MODULE.bazel:22-35` also declares a `crate.from_cargo(name = "fltk_crates", ...)` extension seeded from the root `Cargo.toml`/`Cargo.lock` plus `crates/fltk-cst-core/Cargo.toml` and `crates/fltk-parser-core/Cargo.toml`, with `use_repo(crate, "fltk_crates")`.

No `# TODO(bazel-rules-rust)` comment remains anywhere in `MODULE.bazel` (the comment cited in the TODO's own history, e.g. `docs/adr/2026/06/13-rust-bazel-packaging/exploration-fltk.md:203`, has been replaced by the real dependency).

## Is the native extension buildable via Bazel, right now?

Yes, verified with a live `bazel build` invocation (bazel 9.1.1, binary at `/home/rnortman/.local/bin/bazel`) against this exact checkout — not just reading docs:

- `bazel build //:native` → `Target //:native up-to-date: bazel-bin/libfltk_native.so`, "Build completed successfully, 1 total action."
- `bazel build //:native_so //:native_py //:bootstrap_rust_srcs //:bootstrap_native` → all four green, "Build completed successfully, 10 total actions."
- `bazel build //...` (full tree, 26 targets) → "Build completed successfully, 34 total actions," no failures.

Relevant `BUILD.bazel` targets backing this (all present at HEAD):
- `BUILD.bazel:3` — `load("@rules_rust//rust:defs.bzl", "rust_shared_library")`
- `BUILD.bazel:31-44` (approx.) — `rust_shared_library(name = "native", crate_features = ["extension-module", "python"], deps = ["//crates/fltk-cst-core", "@fltk_crates//:pyo3"])`
- `BUILD.bazel` — `genrule(name = "native_so", ...)` renaming `libfltk_native.so` → `fltk/_native.abi3.so`
- `BUILD.bazel` — `py_library(name = "native_py", data = [":native_so"], ...)`
- `crates/fltk-cst-core/BUILD.bazel`, `crates/fltk-parser-core/BUILD.bazel` — `rust_library` targets consumed by `:native`
- `rust.bzl` — `generate_rust_parser` rule and `fltk_pyo3_cdylib` macro used by the `bootstrap_rust_srcs` / `bootstrap_native` smoke targets in `BUILD.bazel`

One incidental observation from the live build: `bazel build //...` regenerated `MODULE.bazel.lock` (new `FILE:` hash entries for `crates/fltk-unparser-core/Cargo.toml` and `crates/fltk-fmt-cli/Cargo.toml`, which post-date when the lockfile was last committed). This is normal Bazel lockfile self-repair from new workspace members added since; reverted after the check (`git checkout -- MODULE.bazel.lock`) since no fix was requested. It does not affect the verdict — the build succeeded regardless, both before and after the lock regenerated.

## Is this TODO already complete?

The underlying work (rules_rust dependency, cdylib target, full-tree buildability) is done and verified working, but `TODO.md`'s own text has not been updated to reflect this — it still reads "Implementation in progress." Per-commit history shows the work landed in a single squashed commit:

- `git log --oneline -- MODULE.bazel` shows `7200d9c rust-bazel-packaging: expose FLTK Rust backend to downstream Bazel consumers` — confirmed an ancestor of HEAD (`git merge-base --is-ancestor 7200d9c HEAD` → true). This commit's diffstat includes `MODULE.bazel`, `BUILD.bazel`, `crates/fltk-cst-core/BUILD.bazel`, `crates/fltk-parser-core/BUILD.bazel`, and the full ADR docs under `docs/adr/2026/06/13-rust-bazel-packaging/`.
- The ADR's own `docs/adr/2026/06/13-rust-bazel-packaging/verify-final.md` records a prior "GREEN" verification (fltk `make check`, Clockwork roundtrip test, FLTK-side Bazel smoke target), dated in the ADR's own history, using a temporary `local_path_override` in Clockwork to point at FLTK's local tree — i.e. the verification predates FLTK's Rust-Bazel work being consumed by Clockwork through a normal git pin.

## Deferred/follow-up items named in the ADR that are NOT reflected as live TODOs

`docs/adr/2026/06/13-rust-bazel-packaging/README.md`'s "Status / deferred work" section names several follow-ups with TODO-style slugs:
- `TODO(fltk-pin-finalize)` — revert Clockwork's temporary `local_path_override` back to a real `git_override` pin once FLTK's Rust-Bazel commits are pushed.
- `TODO(rust-pyany-qualify)` — de-glob the `pyo3::prelude::*` import further.
- `TODO(rust-recursion-limit-macro)` — make `recursion_limit` an optional macro attribute.

None of these three slugs appear anywhere in the current `TODO.md`, nor as `TODO(<slug>)` code comments anywhere in the tree (checked `.py`, `.rs`, `.bzl`, `BUILD.bazel`, `MODULE.bazel`). The only TODO-system slug from that ADR era still live in `TODO.md` and in code is `bazel-neg-test-harness` (`TODO.md:109`, comment at `BUILD.bazel:138`), which covers a different, later-scoped gap (no automated negative-test harness for the macro's `fail()` guards). Whether `fltk-pin-finalize`/`rust-pyany-qualify`/`rust-recursion-limit-macro` were separately resolved and their TODO entries removed, or were never promoted into the tracked TODO system, was not determined from this exploration alone — noted here as a fact (absence), not a conclusion about disposition.

## Summary of ground truth

| Question | Answer | Evidence |
|---|---|---|
| `rules_rust` in `MODULE.bazel`? | Yes | `MODULE.bazel:6` |
| `fltk._native` buildable via Bazel? | Yes, confirmed live | `bazel build //:native` → success, this session |
| Full `bazel build //...` green? | Yes, confirmed live | 26 targets, 34 actions, success, this session |
| `TODO.md` text updated to reflect completion? | No — still says "Implementation in progress" | `TODO.md:11` |
| Commit landing the work is on `main` ancestor of HEAD? | Yes | `7200d9c`, confirmed ancestor of `8fd5ecf` |
