No findings.

Checked: `crates/fltkfmt/tests/cli.rs` (new), `crates/fltkfmt/src/main.rs`, `TODO.md`,
`crates/fltkfmt/tests/golden/fegen.fltkg.golden` (diff base 9233540d..HEAD 2728a782).

Considered and ruled out as reuse issues (no existing utility available to replace them):
- `CORPUS`/`CONFIGS` lists in `cli.rs` duplicate `_CORPUS`/`_CONFIGS` in
  `tests/test_fltkfmt_parity.py` — cross-language (Rust vs Python), no shared-list
  mechanism exists; design doc explicitly calls this out with cross-reference comments.
- `temp_file` helper in `cli.rs` is structurally similar to `temp_dir` in
  `crates/fltk-fmt-cli/src/lib.rs:669` — that helper is a private `#[cfg(test)]` item in
  a different crate (unit tests, stub `format_fn`s), not exported, and no shared
  test-support crate exists in the workspace to host a common version.
- Hand-rolled `Command`/`Stdio` subprocess runner in `cli.rs` — no `assert_cmd` or
  similar dependency is used anywhere else in the repo, and the design explicitly opts
  out of adding one to keep `fltkfmt`'s dependency footprint minimal (its Cargo.toml
  header comment: "minimal template for a new formatter binary"). No existing in-repo
  Rust subprocess-driving helper exists (`grep -rl 'Command::new' crates/` returns only
  this new file).

No hand-rolled logic in the new file duplicates functionality already available via an
existing project utility.
