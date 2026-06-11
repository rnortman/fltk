# Design: escape control characters in parse-error messages

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir). Both backends in lockstep; byte-identical output (parity comparator, `tests/parser_parity.py:107`).

## Context / root cause

Both `format_error_message` implementations embed the raw failing line verbatim:

- Rust: `crates/fltk-parser-core/src/errors.rs:135-141` — `line_text` interpolated directly; security note + `TODO(error-msg-escape)` at `errors.rs:85-92`.
- Python: `fltk/fegen/pyrt/errors.py:58-63` — raw slice `terminals.terminals[line_span.start:line_span.end]`.

Control characters (ESC/ANSI, `\r`, other C0) pass through → terminal-escape injection and log forging for any consumer surfacing parse errors for untrusted input. The formatter is the designated fix point: no in-tree display layer exists, and generated parsers call the runtime formatter (Rust generated code calls `fltk_parser_core::format_error_message`, e.g. `tests/rust_parser_fixture/src/parser.rs:96`), so the fix lands in one place per backend with **no parser regeneration**.

Both backends use codepoint indices for `line`/`col`/`line_span` (Python `str` indexing; Rust `terminalsrc.rs:14` documents codepoint indices), so the escaping and caret arithmetic below are unit-consistent cross-backend.

## Proposed approach

### Escape function (one spec, two implementations)

`escape_control_chars(text) -> str`: per-character mapping, applied only to the quoted line in `format_error_message`.

**Escape set:**

| Range | Action |
|---|---|
| U+0000–U+001F except U+0009 (`\t`) | escape |
| U+007F (DEL) | escape |
| U+0080–U+009F (C1 controls) | escape |
| everything else (incl. `\t`, all printable Unicode) | pass through unchanged |

**Representation (pinned cross-backend):** `\xHH`, lowercase hex, exactly two digits (e.g. ESC → `\x1b`). All escaped codepoints are ≤ U+009F, so two digits always suffice. Matches the existing `py_repr_str` / Python `repr` convention already used in the `Expected:` block (`errors.rs:191-216`).

**Decisions (deliberate widening beyond the TODO's literal "C0" wording):**

- **DEL + C1 included.** A C0-only filter leaves the exact vector this fix exists to block: U+009B is a single-character CSI in terminals accepting 8-bit controls, and raw DEL is also a control. Escaping them costs nothing and both backends count them identically (one codepoint each).
- **`\n` is in the escape set** even though it is unreachable at the call site (`line_span` excludes the terminating newline both backends). Keeps the helper total and safe for reuse; output is unchanged.
- **`\t` stays literal** per the request: tabs render as-is and the caret pad continues to count them as one column (preexisting imprecision when a terminal expands tabs; unchanged, out of scope).

### Caret alignment

Escaping expands one character into four (`\xHH`), so a caret computed from the raw column misaligns whenever escaped characters precede the error column. Fix: compute the pad from the **escaped prefix**.

Definitions (per backend, identical results):

- `prefix = line_text[..max(col, 0)]` (codepoint slice; `max(col, 0)` preserves the `col == -1` corner — empty prefix, empty pad, matching today's `' ' * -1 == ''` / `col.max(0)` behavior).
- `pad = codepoint-length of escape_control_chars(prefix)` — Python `len(...)`, Rust `.chars().count()` (not byte `len()`: the prefix may contain multibyte characters, which contribute one pad column each, exactly as today).
- Rendered line = `escape_control_chars(prefix) + escape_control_chars(line_text[max(col,0)..])`. Because the mapping is per-character, this equals escaping the whole line; splitting at `col` just makes the pad computation a byproduct.

Resulting semantics: each unescaped character before the error column contributes 1 pad column (unchanged), each escaped character contributes 4. When the error column itself is a control character, the caret points at the `\` of its escape sequence.

Example: raw line `a`, `b`, ESC, `c`, `d` with error at col 3 (`c`). Prefix = `a`, `b`, ESC (3 chars) → escaped `ab\x1b` (6 chars) → pad = 6 spaces. Rendered line = `ab\x1bcd` (8 chars); caret sits under `c`.

### File changes

1. **`fltk/fegen/pyrt/errors.py`**
   - Add module-level `def escape_control_chars(text: str) -> str` (public: importable by tests and downstream consumers who format their own lines).
   - In `format_error_message`: replace the raw-slice interpolation and `' ' * col` with the escaped-prefix/suffix construction above.
2. **`crates/fltk-parser-core/src/errors.rs`**
   - Add `pub fn escape_control_chars(s: &str) -> String`; re-export from `lib.rs` alongside `format_error_message` (mirrors the Python public surface).
   - In `format_error_message`: same construction; pad via `.chars().count()` of the escaped prefix.
   - Replace the security-note + TODO doc comment (`errors.rs:85-92`) with a short note documenting the escaping and the cross-backend byte-identical pin.
3. **`TODO.md`** — remove the `error-msg-escape` entry (`TODO.md:54-62`).
4. **`tests/parser_parity.py`** — **no change.** Both sides apply identical escaping; the byte-equal header comparison at line 107 holds as-is (exploration Claim 5).
5. **Tests** — see Test plan.

### Observable output change (stated plainly)

This deliberately changes generated-error text for downstream consumers: any parse error whose failing line contains characters in the escape set now renders them as `\xHH`, and the caret column shifts accordingly. User-approved (triage item 4). Errors on control-free lines are byte-for-byte unchanged.

## Edge cases / failure modes

- **`col == -1`** (no failure recorded / `longest_parse_len == -1`): `max(col, 0)` → empty prefix → empty pad. Output unchanged from today for control-free lines.
- **Empty line text** (empty input): escape of `""` is `""`; unchanged.
- **Error column at a control char:** caret lands on the `\` of its escape — acceptable and tested.
- **`\t` before the column:** 1 pad space per tab, as today. Misalignment under tab-expanding terminals is preexisting and out of scope.
- **Multibyte chars before the column:** 1 pad column per codepoint, as today (preexisting display-width imprecision for wide glyphs; unchanged).
- **Whitespace regexes consuming controls:** Python `re` and Rust `regex` both class `\r` (and `\x0b`, `\x0c`) as `\s`, so grammars with whitespace separators can successfully consume controls *before* the failure point — this is precisely the escaped-chars-before-caret case the pad fix handles.
- **`Expected:` block:** untouched. `py_repr_str` escapes C0/DEL (`errors.rs:208`) but emits C1 raw — a preexisting, documented Python/Rust divergence (`errors.rs:188-190`). Out of scope: token text is grammar-author-controlled, not untrusted parse input, so it is not the injection vector this fix targets. If the C1 security argument is extended to author-controlled tokens, that is a separate follow-up (would also need cross-backend pinning, since Python `repr` *does* escape C1).
- **Sentinel last-line quirk:** `pos_to_line_col`'s final-line span excludes the last character when input lacks a trailing newline (both backends, preexisting). Escaping does not interact with it; goldens just account for it.
- **Lone surrogates:** Python `str` can hold them; Rust `String` cannot. Inputs crossing the binding boundary are already valid UTF-8; out of scope.

## Test plan

After this change, the following tests exist and pass:

1. **Rust unit tests** (`errors.rs` `#[cfg(test)]`):
   - `escape_control_chars` table test: ESC, `\r`, `\x00`, `\x7f`, `\x9b` → `\xHH`; `\t`, printable ASCII, multibyte (e.g. `→`) pass through.
   - Golden `format_error_message` test: input whose failing line contains `\x1b[31m` and `\r`; assert the full message string (escaped line, correct caret).
   - Caret-alignment golden: escaped characters *before* the error column; assert exact pad width.
   - Assert no raw codepoint < U+0020 (other than `\n`, `\t`), no U+007F, no U+0080–U+009F anywhere in a formatted message containing controls.
   - Existing goldens (`format_error_message_basic` at `errors.rs:302`, `_minus_one_pos`, `_empty_input`, `_multiline`) unchanged — ASCII-clean inputs produce identical output.
2. **Python unit tests** (new `tests/test_pyrt_errors.py`):
   - Mirror the Rust cases with the *same* expected strings (the shared expected strings are themselves the byte-identity check at the unit level).
   - `col == -1` / empty-input behavior unchanged.
3. **Parity corpus** (`tests/test_rust_parser_parity_fixture.py` `_CORPUS`):
   - New FAIL entry with controls in the failing line, e.g. `("num", "\x1b[31mabc", FAIL)` — `num := /[0-9]+/` fails at pos 0; the quoted line carries the ESC sequence; caret at col 0.
   - New FAIL entry with controls *before* the error column: `("stmt", "x\r=\r@", FAIL)`. Trace against the fixture grammar (`stmt := lhs:atom : "=" : rhs:atom`): name matches `x`, the WS_REQUIRED separators consume each `\r` (`\s` classes `\r` as whitespace in both backends), and `rhs:atom` fails at pos 4 (`@` matches neither `/[0-9]+/` nor `/[a-z]+/`), so `longest_parse_len == 4` with two escaped `\r` before the caret (pad = 10). Note the input must *fully* fail, not partially succeed: an input like `"x\r=\r1@"` parses `stmt` through `1` and leaves the farthest *recorded failure* at pos 0, putting no escapes before the caret.
   - The `@` at pos 4 falls on the sentinel last-line quirk (excluded from `line_span`), so the caret points one column past the rendered line — identical on both backends and consistent with existing behavior for ASCII input.
   - These exercise `_assert_messages_equiv`'s byte-equal header check cross-backend with escaped content.
4. **Full gates:** `uv run pytest`, `cargo test`, `make fix` clean.

## Open questions

1. **Escape-set widening: confirm C0 → C0+DEL+C1.** The request pins "C0 controls (except `\t`)" (request.md:25), backed by user-approved triage item 4. This design widens to DEL + C1 for the reasons argued under Decisions (U+009B is a single-character CSI; DEL is a control; cost is zero and both backends count them identically). The widening deviates from the approved spec and will be pinned by parity tests, so it needs explicit user confirmation; if declined, drop DEL/C1 from the escape table and the corresponding test rows — everything else in this design is unchanged.

The caret-pad rule is a design decision argued above, not a user-judgment item.

USER ANSWER A1. Widening is approved.
