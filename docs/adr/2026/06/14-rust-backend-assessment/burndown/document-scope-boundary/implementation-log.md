## Increment 1 — version bump to 0.2.0 + consumer-guide pin fix (commit 0adf385)

- pyproject.toml:9 — `fltk` version 0.1.1 → 0.2.0
- Cargo.toml:7 — `fltk-native` version 0.1.0 → 0.2.0
- Cargo.lock, uv.lock — updated by `maturin develop` rebuild; all 1897 tests pass
- docs/rust-cst-extension-guide.md:57-67 — replaced the non-resolving `fltk-cst-core = { version = "0.2", ... }` example with commented-out path and git pin alternatives; no preferred method expressed; Bazel option noted. The `pyo3` line remains as the only uncommented dependency entry.
