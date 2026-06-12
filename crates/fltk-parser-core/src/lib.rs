//! `fltk-parser-core`: pure-Rust runtime for FLTK-generated parsers.
//!
//! This crate is the Rust port of `fltk/fegen/pyrt/` (`memo.py`, `terminalsrc.py`,
//! `errors.py`). It contains no pyo3 code — pyo3-freedom is structural absence, not a
//! disabled feature. The generated parser's Python surface lives in the generated file
//! and uses `fltk-cst-core`'s python-gated machinery.
//!
//! # Re-exports
//!
//! `pub use regex_automata` is intentional: generated parser code references
//! `fltk_parser_core::regex_automata::meta::Regex` exclusively, so consumer crates need
//! no direct `regex-automata` dependency. This structural re-export guarantees version
//! coherence between runtime and generated code — if both referenced `regex-automata`
//! independently, a consumer running `cargo update` could end up with mismatched versions.

pub mod errors;
pub mod memo;
pub mod terminalsrc;

// Re-export regex_automata so generated code can use
// `fltk_parser_core::regex_automata::meta::Regex` without consumers declaring a separate
// `regex-automata` dependency (version coherence guarantee).
pub use regex_automata;

pub use errors::{escape_control_chars, format_error_message, ErrorTracker, ParseContext, TokenType};
pub use memo::{apply, ApplyResult, Cache, DEFAULT_MAX_DEPTH, MemoEntry, MemoResult, PackratState, RecursionInfo};
pub use terminalsrc::{LineColPos, TerminalSource};
