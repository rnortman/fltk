# Deep correctness review — cst-python-feature-gate

Reviewed: e6a9117..431ab53 (HEAD 431ab53), against design.md in this directory.

## Verification performed (all green)

- All four committed generated files byte-match fresh generator output (`gen-rust-cst` rerun + diff): `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`.
- `cargo test -p fltk-cst-core --no-default-features` (23 tests), `cargo test -p fltk-cst-spike` (19 tests): pass.
- `cargo clippy -D warnings`: python-off core, spike python-off, spike `--features python`, and default workspace: all clean.
- `make check-no-pyo3`: passes; positive-control logic in the recipe verified sound (`set -e` + command-substitution assignment propagates `cargo tree` failure; `!`-negated pipeline safe under `set -e`).
- Standalone fixture cdylibs (`tests/rust_cst_fixture`, `tests/rust_cst_fegen`) `cargo check` with the new feature plumbing: clean; their `Cargo.lock` files unchanged as the design predicted.
- `uv run pytest tests/test_gsm2tree_rs.py fltk/fegen/test_genparser.py`: 129 passed.

## Logic traced, no defects found

- `span.rs` method moves (`text`, `has_source`, `len`, `is_empty`, `merge`, `intersect`, `coerce_source`): bodies are verbatim relocations into the plain `impl Span`; `py_*` rename wrappers preserve Python names, signatures, and the exact `"cannot merge spans from different sources"` ValueError message for both `merge` and `intersect` (matching the old shared `coerce_source` message). `text_or_raise` untouched.
- Dual-cfg enum emission (`NodeKind`, label enums): python-on and python-off variant lists are emitted from the same `rule_info`/`labels` iteration in `gsm2tree_rs.py`, so they cannot drift; deviation from design §2.3 (`cfg_attr` on variant helper attrs) is documented in implementation-log.md and the committed output confirms it.
- `append`→`extend` error-message change (`{Class}.extend: label argument is not a ...`) is a deliberate, documented fix of a copy-paste diagnostic bug (dispositions-prepass.md slop-1); no in-tree test pinned the old string.
- Feature plumbing: positive-polarity `python` feature, `dep:pyo3`, forwarding features in fltk-native and both fixture crates match the design; `-p` isolation in the no-python lanes correctly sidesteps workspace feature unification.
- Spike tests' match arms are exhaustive against the generated child enums; assertions against source substrings ("hello world foo" offsets) check out.

## Findings

### correctness-1

- File: docs/rust-cst-extension-guide.md:58
- What: The corrected consumer Cargo.toml template declares `fltk-cst-core = { version = "0.1", ... }` — a crates.io-style version dependency. Nothing in the repo indicates fltk-cst-core is published to crates.io (Python package distributed via maturin; no Rust publish workflow; design §2.7 said "path/version").
- Why: An out-of-tree consumer copying this template verbatim gets `error: no matching package named fltk-cst-core` at resolution time, before any of the loud-but-actionable failure modes the design enumerates. The in-tree fixtures all use `path = ...` deps.
- Consequence: The documented Step-2 workflow is unbuildable as written for any consumer outside this repo, unless/until the crate is published. Impact is currently low (user confirmed no Rust out-of-tree consumers exist yet), but this guide is the artifact such a consumer would follow first.
- Suggested fix: Show a `path`/`git` dependency form (or both forms with a note), or publish the crate before the guide advertises a version dep. Minor adjacent nit in the new migration section (line ~140): the lint is named `unexpected_cfgs`, not `unexpected_cfg`.

No other findings: code logic, control flow, and data flow are clean.
