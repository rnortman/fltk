# Request: escape control characters in parse-error messages

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Bug fix (security: terminal-escape injection / log forging), BOTH backends in lockstep.

**Origin:** TODO.md slug `error-msg-escape`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 4, USER DECISION: Do).

## Background

Both `format_error_message` implementations embed the offending source line (the line containing `ErrorTracker.longest_parse_len`, the furthest-failure high-water mark) verbatim in the error string:
- Rust: `crates/fltk-parser-core/src/errors.rs:121-141`, raw `line_text` at line 136. Security note + TODO at `errors.rs:86-92`.
- Python: `fltk/fegen/pyrt/errors.py:52-71`, raw slice `terminals.terminals[line_span.start:line_span.end]` at line 60.

Control characters (ESC/ANSI, `\r`, other C0) pass through, enabling terminal-escape injection and log forging against any consumer that surfaces parse errors for untrusted input.

Validation findings (see `exploration.md` in this dir):
- The two implementations match byte-for-byte in the header section (where `line_text` lives), including the `col = -1` corner (`' ' * -1` == `''` in Python; `col.max(0)` in Rust).
- Parity comparator: `tests/parser_parity.py:107` compares header lines byte-equal. If both sides apply IDENTICAL escaping, the comparator needs **no structural change** — but fixing one side alone breaks it, hence lockstep.
- `line_span` excludes the terminating newline, so the practical escape targets within the line are ESC, `\r`, and other C0 controls; `\n`/`\t` exemption per original TODO (note `\n` can't appear in a line slice anyway; keep `\t` literal for column alignment — design should confirm the caret-alignment interaction with escaped multi-char sequences).
- Golden test `errors.rs:311` uses ASCII-clean input — unaffected. No existing test uses control characters.

## Fix shape

Identical escaping of C0 controls (except `\t`; `\n` unreachable) in the quoted line, implemented in both `format_error_message`s with byte-identical output (e.g. `\x1b`-style hex escapes — design picks one representation and pins it cross-backend). Remove the TODO comment at `errors.rs:86-92` and the TODO.md entry.

Known design wrinkle to address: escaping expands one byte into several characters, which can misalign the `^` caret when escaped characters precede the error column. Design must decide (and test) the caret behavior — adjusting the caret offset for expansion is preferred over a misaligned caret.

## Constraints / non-goals

- Both backends MUST produce byte-identical messages (parity comparator enforces).
- This is a deliberate, user-approved change to generated-error text — an observable output change for downstream consumers; the design should state it plainly.
- No change to which line/position is reported, only how its text is rendered.

## Verification expectations

- New tests both backends: input whose failing line contains ESC + ANSI sequence and `\r`; assert escaped output, assert no raw C0 bytes (other than `\n`/`\t`) anywhere in the message.
- New parity-corpus FAIL entry with control characters (exercises the comparator cross-backend).
- Caret-alignment test with escapes before the error column.
- Full suite + parity tests; `make fix`; `uv run pytest` + `cargo test` clean.
