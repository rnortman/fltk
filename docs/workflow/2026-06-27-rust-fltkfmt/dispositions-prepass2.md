# Dispositions — prepass 2 (increments 4-6)

Commit reviewed: c52d998a09e4ce433289872be91a3ce7c249dca0
Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a

## slop-1
- Disposition: Fixed
- Action: Deleted the `/// Is this path the stdin sentinel (`-`)?` docstring on
  `is_stdin` (`crates/fltk-fmt-cli/src/lib.rs:81`). The one-line body
  (`path.as_os_str() == "-"`) is self-evident; there is no non-obvious invariant to
  document.
- Severity assessment: Cosmetic. A redundant docstring that restates the identifier adds
  noise but no behavioral risk.

## slop-2
- Disposition: Fixed
- Action: Removed the "the design's 'CLI behavior summary'" citation from the `validate`
  rustdoc, keeping the enumerated list of rejected combinations
  (`crates/fltk-fmt-cli/src/lib.rs:86`).
- Severity assessment: Low. A design-doc cross-reference is dead noise for out-of-tree
  readers, but it does not affect behavior.

## slop-3
- Disposition: Fixed
- Action: Dropped the "See design §3 …" sentence from `write_atomic`'s rustdoc; the
  preceding atomic-write rationale stands alone
  (`crates/fltk-fmt-cli/src/lib.rs:119`).
- Severity assessment: Low. Opaque cross-reference; no behavioral impact.

## slop-4
- Disposition: Fixed
- Action: Replaced the "This is the 'easy reuse' surface from the design:" opener in the
  `#[macro_export] fltk_formatter_main!` rustdoc with a direct description of what the
  macro does (`crates/fltk-fmt-cli/src/lib.rs:178-183`).
- Severity assessment: Low-moderate. This is public (`#[macro_export]`) API documentation
  visible to out-of-tree consumers in generated docs, so process narrative there is more
  visible than internal comments, but still no behavioral effect.

## slop-5
- Disposition: Fixed
- Action: Removed the "first consumer" / "Almost all of the work lives in …" process
  framing from the `fltkfmt` binary module doc; now leads with the durable fact that the
  binary is a single `fltk_formatter_main!` invocation
  (`crates/fltkfmt/src/main.rs:8-11`).
- Severity assessment: Low. The "first consumer" framing would read as wrong once a second
  consumer exists; cosmetic, no behavioral effect.

## scope-1
- Disposition: Fixed
- Action: Corrected the increment-4 log entry from "15 new `run_inner` integration tests"
  to "13 new" (`docs/workflow/2026-06-27-rust-fltkfmt/implementation-log.md:86`). Base had
  12 tests, HEAD has 25, so the diff adds 13. The "25 tests pass" total was already
  correct, and the reviewer confirmed no behavior or coverage is missing — purely a log
  count error.
- Severity assessment: Negligible. A miscount in the implementation log only; the code,
  test coverage, and all design §4 `fltk-fmt-cli` behaviors are present and passing.
