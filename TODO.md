# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `pin-ci-actions`

SHA-pin all GitHub Actions references in `.github/workflows/ci.yml` to immutable commit SHAs rather than mutable branch/tag refs. Currently `dtolnay/rust-toolchain@stable`, `actions/checkout@v4`, and `astral-sh/setup-uv@v6` use mutable refs. A compromised action repo could execute arbitrary code in CI and tamper with build artifacts. Use Dependabot to manage SHA-pinned action updates. Location: `.github/workflows/ci.yml:12,15,21`.
