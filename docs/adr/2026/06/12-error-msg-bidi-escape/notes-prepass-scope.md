No findings.

One unjustified bonus: design §test plan #1 said "existing `errors.rs` escape tests *move* here verbatim" to `escape.rs`. The diff duplicates them — `escape_control_chars_table` and `escape_control_chars_empty` remain in `crates/fltk-parser-core/src/errors.rs` (lines 315–340) in addition to the new copies in `escape.rs`. Net effect is more test coverage, not less; correctness unaffected. Not a scope violation; noted for awareness.
