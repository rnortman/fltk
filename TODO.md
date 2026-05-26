# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `backend-with-source-signature`

Unify the `Span.with_source` construction API across backends. Currently the Python backend takes a raw `str` while the Rust backend takes a `SourceText` handle. Code using `from fltk.fegen.pyrt.span import Span` that calls `Span.with_source(start, end, src_str)` breaks silently when the Rust backend is active. Options: expose a `SourceText`-like wrapper in the Python backend, or accept both types in the Rust backend. Deferring until the parse path is wired to produce source-bearing spans (Phase 2+). Location: `fltk/fegen/pyrt/span.py`.

## `pin-ci-actions`

SHA-pin all GitHub Actions references in `.github/workflows/ci.yml` to immutable commit SHAs rather than mutable branch/tag refs. Currently `dtolnay/rust-toolchain@stable`, `actions/checkout@v4`, and `astral-sh/setup-uv@v6` use mutable refs. A compromised action repo could execute arbitrary code in CI and tamper with build artifacts. Use Dependabot to manage SHA-pinned action updates. Location: `.github/workflows/ci.yml:12,15,21`.
