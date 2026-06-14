# Bazel Run Verification — Clockwork ↔ FLTK Rust Packaging POC

**Verdict: BLOCKED-ENVIRONMENT**

The Bazel build fails before it ever reaches the new Rust surface. The blocker is
a repository-fetch failure: Clockwork's `@fltk` Bazel module is pinned to a git
commit that does not exist on the GitHub remote it fetches from. No `rules_rust`
code, Rust toolchain, crate fetch, codegen action, or generated parser was
exercised — the build dies at "Computing main repo mapping". This is a
setup/packaging-state problem, **not** evidence the Bazel rules are correct or
incorrect; they were never reached.

Date: 2026-06-13. Run by automated verification.

---

## Environment

- **Bazel:** none installed system-wide (`bazel`/`bazelisk` not on PATH). To run a
  real build I downloaded `bazelisk v1.27.0` (linux-amd64, official GitHub release)
  to `~/.local/bin/bazel`. Bazelisk then honored Clockwork's `.bazelversion` and
  downloaded/launched **Bazel 8.4.2** successfully (`bazel version` → Build label
  8.4.2). So the Bazel version under test is the pinned 8.4.2.
- **Rust toolchain:** host has `rustc`/`cargo` 1.96.0 + `rustup` (`~/.cargo/bin`).
  Not relevant to the failure — the design uses `rules_rust` download-prebuilt
  1.87.0, and the build never got far enough to register or invoke any Rust
  toolchain.
- **Network:** available. GitHub releases (302), Bazel Central Registry (200),
  `github.com/rnortman/fltk.git` (`git ls-remote` succeeded) are all reachable.
  Network is **not** the blocker.

---

## Per-target results

| Target | Result |
|---|---|
| `//clockwork/dsl:clockwork_rust_roundtrip_test` (roundtrip py_test) | **BLOCKED** — repo fetch of `@fltk` fails; build aborts at main-repo-mapping computation. |
| `@fltk//:bootstrap_rust_srcs` (FLTK-side smoke target) | **NOT RUN** — exists in `@fltk//BUILD.bazel:101` but cannot be invoked: there is no Bazel/MODULE setup to build FLTK standalone via Bazel from this checkout, and the only Bazel consumer (Clockwork) cannot fetch FLTK. Note: `fltk_pyo3_cdylib` is *not* exercised even by Clockwork's smoke target — only `generate_rust_parser` is (`BUILD.bazel:111-112`, `TODO(fltk-pyo3-cdylib-smoke)`). |

---

## Failure detail (verbatim, roundtrip target)

```
ERROR: ... An error occurred during the fetch of repository 'fltk+':
   ...
Error in fail: error running 'git reset --hard f32b2c9e02f06ba6edb26fc1392d73c8a15ba290' while working with @fltk+:
fatal: Could not parse object 'f32b2c9e02f06ba6edb26fc1392d73c8a15ba290'.
ERROR: Error computing the main repository mapping: error during computation of main repo mapping:
error running 'git reset --hard f32b2c9e02f06ba6edb26fc1392d73c8a15ba290' while working with @fltk+:
fatal: Could not parse object 'f32b2c9e02f06ba6edb26fc1392d73c8a15ba290'.
```

## Root cause (environment / packaging state, not a rules defect)

Clockwork pins FLTK by **commit on the GitHub remote**:

```
# clockwork/MODULE.bazel:34
("fltk", "https://github.com/rnortman/fltk.git", "f32b2c9e02f06ba6edb26fc1392d73c8a15ba290", NO_PATCH),  # main
```

This commit is **not present on the remote**. `git ls-remote
https://github.com/rnortman/fltk.git` shows `main` at `fafa6d7` and contains no
`f32b2c9` / `fac3da5`. The entire `rust-bazel-packaging` line of FLTK work
(commits `334cc8a` → `fac3da5`, including `f32b2c9`) exists **only in the local
FLTK checkout at `/home/rnortman/src/fltk` and is unpushed**. Bazel's
`git_override` clones from the `.git` remote, so it cannot resolve the pin.

Two compounding issues:

1. **Unpushed pin (the hard blocker).** `f32b2c9` is reachable locally
   (`git cat-file -t f32b2c9` → `commit`, and it is an ancestor of local `main`
   `fac3da5`) but not on GitHub. Until the FLTK Rust-Bazel branch is pushed to
   the remote `main` (or wherever the override fetches), no Bazel build can fetch
   it. Alternatively the integration would need a `local_path_override` pointing
   at the local FLTK checkout (the mechanism exists in Clockwork's MODULE.bazel
   via the `LOCAL_PATH_OVERRIDE` list, but FLTK is wired through the `.git`
   override list, not the local one).

2. **Stale pin (latent, would matter after #1 is fixed).** Even if `f32b2c9`
   were fetchable, it is **5 commits behind** local FLTK HEAD `fac3da5`. The
   intervening commits are review fixes — notably `e1ea36f` "rust-bazel-review:
   fix label resolution, python feature, test wiring, and docstring" — which the
   log/design treat as required corrections. The Clockwork pin should be bumped
   to the reviewed HEAD before a meaningful green run is expected. Per task
   instructions nothing was changed.

## What this run did and did NOT prove

- Did NOT compile any Rust, register the `rules_rust` toolchain, fetch the
  `pyo3`/`regex-automata` crate graph, run `generate_rust_parser` codegen, build
  the `fltk._native` or `clockwork_native` cdylibs, or import anything in Python.
  All of that is downstream of the failed `@fltk` fetch.
- DID confirm: Bazel 8.4.2 launches; network/registry reachable; the documented
  target labels exist as written (`clockwork_rs_srcs`, `clockwork_native`,
  `clockwork_rust_roundtrip_test` in `clockwork/dsl/BUILD.bazel`;
  `bootstrap_rust_srcs` in `@fltk//BUILD.bazel`); the consumer source files
  (`clockwork_native_lib.rs`, `clockwork_rust_roundtrip_test.py`) are present.

## To get an actual GREEN/RED signal, an implementer must

1. Push the FLTK Rust-Bazel commits to the GitHub remote (`rnortman/fltk.git`),
   **or** switch Clockwork's FLTK override to a `local_path_override` against the
   local checkout.
2. Bump `clockwork/MODULE.bazel:34` from `f32b2c9` to the reviewed FLTK HEAD
   (`fac3da5d68521ba3893f833a1045672ca9e99504`).
3. Re-run `bazel test //clockwork/dsl:clockwork_rust_roundtrip_test`.

Only then will the run exercise the Rust toolchain + crate fetch + codegen +
cdylib link + Python import path that this POC is meant to validate.
