//! `fltkfmt` — a standalone, pure-Rust formatter for `.fltkg` grammar files.
//!
//! This binary parses `.fltkg` input with the pure-Rust parser generated from
//! `fegen.fltkg`, hands the resulting CST to the pure-Rust unparser generated from
//! `fegen.fltkg` + `fegen.fltkfmt` (the format spec is baked in at generation time), and
//! renders the result. No Python, PyO3, or GIL is involved at any stage.
//!
//! The entire binary is a single `fltk_formatter_main!` invocation (from the reusable
//! `fltk-fmt-cli` scaffolding crate) naming the fegen grammar's concrete `Parser` /
//! `Unparser` types and its start-rule (`grammar`) parse/unparse methods. Producing a
//! formatter for any other FLTK grammar is the same one invocation with different names.

// TODO(fltkfmt-integration-tests): add the design §4 end-to-end tests under
// `crates/fltkfmt/tests/` (idempotency, golden, trailing-newline, parse-error) — they also
// cover the `fltk_formatter_main!` partial-parse and unparse-None error branches, which need
// a real consumer like this binary. Landing with the §2.3 `make check` gating increment.
fltk_fmt_cli::fltk_formatter_main! {
    parser: fegen_rust_cst::parser::Parser,
    unparser: fegen_rust_cst::unparser::Unparser,
    parse: apply__parse_grammar,
    unparse: unparse_grammar,
}
