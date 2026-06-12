slop-1. `crates/fltk-parser-core/src/errors.rs` test `format_error_message_with_controls_in_line`, comment block starting `// line_text for a single-line input...`
Quote: `// line_text for a single-line input with no trailing newline:\n// line_ends sentinel excludes last char, so text = "\x1b[31mab" (len=8, sentinel at pos 7)\n// prefix = "" (col=0, max(0,0)=0), escaped_prefix="", pad=0\n// escaped_suffix = escape("\x1b[31mab") = "\\x1b[31mab"`
What's wrong: Narrative implementation-note comment explaining how the test was derived, not what the test verifies. Documents internal sentinel quirk and manual calculation inline; this is LLM-narrating-its-reasoning, not useful future-reader context.
Consequence: Reads as unfinished cleanup; a reviewer sees the author left workbench notes in the committed artifact.
Fix: Remove the derivation block; keep only the assertion that ESC is escaped and the caret is at col 0.

slop-2. `tests/test_rust_parser_parity_fixture.py`, corpus entry comment for `("stmt", "x\r=\r@", FAIL)`.
Quote: `# Note: '@' is at pos 4 which triggers the sentinel last-line quirk (excluded from\n# line_span), so the caret points one column past the rendered line — both backends.`
What's wrong: Implementation detail of the sentinel quirk belongs in a doc/ADR, not as a corpus comment. It explains why the test looks odd without providing actionable insight to a future reader maintaining the corpus.
Consequence: Signals "this is weird and we're not sure it's right" — the kind of hedge a reviewer flags for follow-up. Also, a future refactor that fixes the sentinel quirk will need to update the comment and the corpus expectation, two places to keep in sync.
Fix: Either remove the note (the test value speaks for itself) or move the sentinel explanation to a module-level comment near the sentinel logic, not inline with a data entry.

slop-3. `tests/test_pyrt_errors.py`, `test_escape_control_chars_c1` — the three test strings render as empty in the diff.
Quote: `assert escape_control_chars("") == "\\x9b"\nassert escape_control_chars("") == "\\x80"\nassert escape_control_chars("") == "\\x9f"`
What's wrong: The C1 codepoints U+009B, U+0080, U+009F are invisible in the source as stored — the diff shows them as empty strings. Whether this is a diff-rendering artifact or the actual source cannot be determined from the diff alone, but if it is the source, the test strings are missing their inputs, making the assertions vacuously pass or test empty-string behavior rather than C1 escaping.
Consequence: If inputs are genuinely empty strings, all three assertions are equivalent to `escape_control_chars("") == "\\x9b"` which would fail — meaning the tests would never pass as written. If the codepoints are present but non-rendering in this view, the tests are fine but fragile to editor normalization. Either way a reviewer cannot verify correctness from the diff.
Fix: Use explicit unicode escapes: `escape_control_chars("")`, `escape_control_chars("")`, `escape_control_chars("")` so the source is unambiguous and editor-safe.
