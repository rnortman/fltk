slop-1:
- Disposition: Fixed
- Action: Removed 4-line derivation comment block (sentinel quirk derivation) from `format_error_message_with_controls_in_line` in `crates/fltk-parser-core/src/errors.rs:362-366` (pre-fix); kept only the functional assertions.
- Severity assessment: Cosmetic; the workbench notes reduced reviewer confidence and would be stale after any refactor of the sentinel logic.

slop-2:
- Disposition: Fixed
- Action: Removed the 2-line sentinel-quirk explanation comment from the `("stmt", "x\r=\r@", FAIL)` corpus entry in `tests/test_rust_parser_parity_fixture.py:118-120` (pre-fix); retained the functional description of why parsing fails where it does.
- Severity assessment: Cosmetic; the comment hedged on correctness of an existing behavior and would need a separate update if the sentinel quirk were ever fixed, creating a sync hazard.

slop-3:
- Disposition: Fixed
- Action: Replaced literal C1 codepoints (U+009B, U+0080, U+009F) in `tests/test_pyrt_errors.py:25-27` with explicit ``, ``, `` unicode escape sequences. The codepoints were present and correct (confirmed via raw byte inspection), but invisible in editor/diff views, making the tests unverifiable by inspection.
- Severity assessment: Low-severity correctness risk; the tests passed as-written, but the literal codepoints are silently stripped by many editors (including some CI formatters), which would convert the tests into vacuous empty-string checks that would then fail with an assertion error rather than pass — an insidious failure mode.
