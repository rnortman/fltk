## Dispositions: prepass review (slop + scope)

### slop-1

- Disposition: Fixed
- Action: `tests/test_pyrt_errors.py` line 121 — replaced raw UTF-8 bytes `\xc2\x80` (C1 U+0080) with explicit Python escape `\x80`; input is now `"\x80‎\tabc"` and fully readable in diffs. Commit 40fbd00.
- Severity assessment: The test was functionally correct (raw bytes matched the C1 codepoint), but the invisible character made the diff unverifiable for reviewers maintaining the cross-backend pin. Readability fix only; no behavioral change.

### slop-2

- Disposition: Won't-Do
- Action: no change to `crates/fltk-cst-core/src/lib.rs`
- Severity assessment: `pub mod escape` is intentional per design §Part (a), which states the canonical implementation lives in `fltk_cst_core::escape::escape_control_chars` as a reachable public path. `fltk-parser-core` re-exports via `pub use fltk_cst_core::escape::escape_control_chars`; making the mod `pub(crate)` would break that re-export path for downstream consumers. The broader surface is the deliberate design choice.
- Rationale (Won't-Do): Design §Part (a) explicitly says "New module `crates/fltk-cst-core/src/escape.rs`… `pub mod escape;` in `fltk-cst-core/src/lib.rs`." Narrowing to `pub(crate)` would silently break `fltk-parser-core`'s `pub use fltk_cst_core::escape::escape_control_chars` for any external crate that imports the re-exported symbol, contradicting the "public paths preserved" requirement. The scope note observes test duplication but explicitly marks it as not a violation.
