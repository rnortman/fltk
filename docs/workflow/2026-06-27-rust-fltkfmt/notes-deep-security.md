# Deep security review — rust-fltkfmt increments 1-3

Commit reviewed: 1b48755794ecca64a81f799fc91550904ea0970c (base 61fc5e89...)

Scope: generated fegen Rust unparser (`crates/fegen-rust/src/unparser.rs`), its
generator (`fltk/unparse/gsm2unparser_rs.py`), crate wiring
(`crates/fegen-rust/src/lib.rs`, Cargo/Makefile/pyproject), and the new CLI
scaffolding crate (`crates/fltk-fmt-cli`).

## Findings

No findings.

## What was checked (and why it's clean)

- **No injection into generated Rust.** Grammar literals/regex/source-name are the
  only data interpolated into emitted Rust source. They flow through `rust_str_lit`
  (`gsm2parser_rs.py:59`), which escapes `\`, `"`, control chars (<0x20) and DEL into
  `\u{..}` form — correct for a Rust string-literal context. Inputs (grammar +
  fltkfmt config) are developer-authored build-time artifacts, not a runtime trust
  boundary.
- **Generated `unparser.rs` is a pure CST→Doc transform.** No `unsafe`, no
  `std::fs`/`std::net`/`std::process`/`Command`/`env`, no `include_str`, no
  `panic!`/`expect`/`unwrap`. It reads already-parsed source via `span.text()` and
  builds Doc combinators. No new sink.
- **`fltk-fmt-cli/src/lib.rs` has no I/O yet.** Only the `FmtArgs` clap struct and
  `fully_consumed`. `fully_consumed` guards `pos < 0` and treats `pos` as a char
  index; an out-of-range positive `pos` yields an empty suffix (→ "consumed"), but
  `pos` originates from the parser bounded by input length, so not attacker-driven.
- **New dependency `clap` 4.6.1** + standard tree (anstyle/strsim/windows-sys/etc.).
  Well-known, MIT/Apache-2.0, no known advisories. Design notes the `cargo deny`
  gate.
- **No secrets** in the diff (Cargo.lock additions are dependency metadata only).

## Forward-looking (later increments — not in this diff, do not regress)

- The security-sensitive surface (`run_main` file/stdin I/O, `--in-place` temp+rename
  writes, `--output`, path handling) is **not yet present**. When implemented, watch:
  - `--in-place` atomic write must create the temp file in the same directory and
    `rename` over the target; do not follow symlinks in a way that lets a formatted
    file escape its directory, and preserve sane permissions on the rewritten file
    (avoid world-readable temp files / mode changes).
  - Error/usage messages and the path-prefixing in `run_main` should not echo
    unsanitized content in a way that matters for terminal escapes (low concern, but
    worth a glance).
- **Recursion on untrusted input (inherent, not introduced here).** A formatter may
  run on untrusted `.fltkg` files (e.g. CI). Both the recursive-descent parser
  (landed earlier) and this unparser recurse with input nesting depth; a
  pathologically nested file can exhaust the stack (process abort = DoS, not memory
  corruption in Rust). The unparser adds no reach the parser doesn't already gate, so
  no new finding — noted only so a future depth limit, if added, covers both.
