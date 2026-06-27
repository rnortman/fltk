# Correctness review — increments 7-8 (rust-fltkfmt final chunk)

Commit reviewed: 25cd5dcab7489fc1cb05c6c3e29009a170130d0f (base 78eacab318a0d30e43a469dee2269b29cef0875d)
Diff scope: `Makefile` (check gating), `tests/test_fltkfmt_parity.py` (new), implementation-log.md.

No findings.

## What was checked (logic / control flow / data flow)

- **Parity test genuineness.** `_py_format` faithfully reproduces the `unparse_cli.py`
  pipeline (`parse_text` rule_name=None → `generate_unparser(..., formatter_config)` →
  `unparse_cst` → `render_doc(RendererConfig(max_width, indent_width))`). `resolve_spacing_specs`
  is applied exactly once on each side — Python inside `unparse_cst` (plumbing.py:333), Rust in
  the `fltk_formatter_main!` macro before `Renderer::render`. So `assert py_out == rust_out` is a
  real cross-backend check, not a vacuous pass; drift would fail it.
- **Arg/ID mapping.** `_CONFIGS = [(80,2),(40,4)]` unpacked as `max_width,indent_width`; CLI
  invocation `-w max_width -i indent_width` matches `FmtArgs` (`-w`=width, `-i`=indent) and the
  Python `RendererConfig(max_width=, indent_width=)`. `_CONFIG_IDS`/`_CORPUS_IDS` are positionally
  aligned (same length/order). 8 corpus files × 2 configs = 16, matching the log.
- **Paths.** `_REPO_ROOT` derives from `__file__` (absolute); all corpus, manifest, and binary
  paths absolute and confirmed to exist. Subprocess uses absolute paths so cwd is irrelevant.
- **Binary location.** `crates/fltkfmt/target/debug/fltkfmt` is correct: fltkfmt is its own
  `[workspace]`, no `.cargo/config.toml` and no `CARGO_TARGET_DIR` redirect target-dir; fixture
  rebuilds debug each session so the path is fresh, not stale.
- **UTF-8 / newline data flow.** Binary writes `formatted.as_bytes()`; test decodes
  `proc.stdout.decode("utf-8")` and compares to the Python `str`. `.fltkg` corpus is `\n`-only, so
  `Path.read_text()` universal-newline behavior introduces no divergence on this platform.
- **Makefile `check-no-pyo3` fltkfmt block.** Positive control (`grep -q fltk-parser-core`,
  arrives transitively via `fegen-rust-cst { default-features = false }`) precedes the negative
  `! grep -q pyo3`; `set -e` + command-substitution failure guards against silent `cargo tree`
  failure. No `--no-default-features` flag is needed because fltkfmt pins
  `default-features = false` on its `fegen-rust-cst` dep in its own manifest, and the standalone
  workspace avoids feature unification with `fltk-native`.
- **Other Makefile lines.** `cargo-test-no-python` (compiles + 0 tests — gates build breakage),
  `cargo-clippy-no-python --all-targets -D warnings`, and `cargo-deny` additions are mechanically
  consistent with the existing per-standalone-crate pattern.

Deferred `crates/fltkfmt/tests/` end-to-end suite is under the accepted
TODO(fltkfmt-integration-tests) — not flagged.
