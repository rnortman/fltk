# Adversarial validation: `error-msg-bidi-escape` TODO

Style: concise, precise, no padding, claims anchored to file:line.

---

## Claim 1: Escape set stops at U+009F in both backends

**TRUE for `errors.rs` and `errors.py`. PARTIALLY TRUE for `cross_cdylib.rs` (third implementation).**

### `crates/fltk-parser-core/src/errors.rs:94-113` — canonical Rust

```rust
fn needs_escape(cp: u32) -> bool {
    (cp <= 0x1F && cp != 0x09) || cp == 0x7F || (0x80..=0x9F).contains(&cp)
}
```

Upper boundary: `0x9F`. TAB (0x09) passes through. All codepoints > 0x9F pass through unchanged.

### `fltk/fegen/pyrt/errors.py:52-79` — Python

```python
_C0_END = 0x1F
_TAB = 0x09
_DEL = 0x7F
_C1_START = 0x80
_C1_END = 0x9F

if (cp <= _C0_END and cp != _TAB) or cp == _DEL or _C1_START <= cp <= _C1_END:
    result.append(f"\\x{cp:02x}")
```

Upper boundary: `_C1_END = 0x9F`. Identical logic to `errors.rs`. TAB passes through.

### `crates/fltk-cst-core/src/cross_cdylib.rs:123-138` — third implementation (private, undocumented as such)

```rust
fn escape_control_chars_for_msg(s: &str) -> String {
    for c in s.chars() {
        let cp = c as u32;
        if (cp <= 0x1F) || cp == 0x7F || (0x80..=0x9F).contains(&cp) {
            for byte in c.to_string().bytes() {
                out.push_str(&format!("\\x{byte:02x}"));
            }
        } else {
            out.push(c);
        }
    }
}
```

Upper boundary also 0x9F. **Three divergences from `errors.rs`:**

1. **TAB not excluded**: `cp <= 0x1F` without `&& cp != 0x09`, so TAB (U+0009) gets escaped here but passes through in `errors.rs` and Python.
2. **C1 encoded as UTF-8 bytes, not codepoint**: `for byte in c.to_string().bytes()` iterates the UTF-8 byte sequence. U+0080 is encoded as `[0xC2, 0x80]` in UTF-8 → emits `\xc2\x80` (two escapes). `errors.rs` uses `write!(out, "\\x{:02x}", cp)` with the codepoint scalar (0x80) → emits `\x80` (one escape). The comment at `cross_cdylib.rs:128-129` claims "this writes a single \xHH using the Unicode scalar value" — **the comment is wrong**.
3. **No cross-backend pin doc**: `cross_cdylib.rs:escape_control_chars_for_msg` is not mentioned in the TODO, not covered by any parity test, and has no `#[cfg(test)]` block in that file.

---

## Claim 2: Two-digit `\xHH` is insufficient for bidi/zero-width chars

**TRUE.**

All named codepoints require 4 hex digits:

| Codepoint | Value | Hex digits needed |
|---|---|---|
| U+202A (LRE) | 0x202A | 4 |
| U+202E (RLO) | 0x202E | 4 |
| U+2066 (LRI) | 0x2066 | 4 |
| U+2069 (PDI) | 0x2069 | 4 |
| U+2028 (LS) | 0x2028 | 4 |
| U+2029 (PS) | 0x2029 | 4 |
| U+200B (ZWSP) | 0x200B | 4 |
| U+FEFF (BOM/ZWNBSP) | 0xFEFF | 4 |

The current representation `\xHH` (always two hex digits) is insufficient. A new format such as `\u{XXXX}` would be needed — or variable-length `\xHHHH` (Python uses `\uXXXX` for BMP above 0x7F in some contexts). Either choice requires updating both backends and cross-backend parity pins.

---

## Claim 3: Cross-backend equivalence pinning — where and what

**The parity pin is at the test/assertion level, not a spec document.**

`tests/parser_parity.py:99-116` — `_assert_messages_equiv`:
- Line 107: `assert py_header == rust_header` — byte-equal list comparison of header lines (everything before `From rule "..."` sections).
- Header lines include: `"Syntax error at line N col M:"`, the escaped line text, the caret line, `"Expected:"`.

`tests/test_pyrt_errors.py:1-4` states: "Expected strings are cross-pinned with the Rust unit tests in `crates/fltk-parser-core/src/errors.rs` to verify byte-identical output." The mirroring is by convention (same literal strings in both test files), not by a shared fixture or spec document.

**No escaping spec document exists.** The design rationale lives in `docs/adr/2026/06/11-error-msg-escape/design.md:20-33` (escape table + representation choice), but it is a design doc, not a machine-checked spec. `cross_cdylib.rs:escape_control_chars_for_msg` is not mentioned there.

---

## Claim 4: Are the two canonical backends byte-identical today?

**YES for the tested domain.** The cross-pinned tests exercise C0 (0x00–0x1F except TAB), DEL (0x7F), and C1 (0x80–0x9F). The TODO's passthrough claim is factually correct: bidi codepoints (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width chars (U+200B etc.) are not in the escape set and are not tested.

**`errors.rs` and `errors.py` are byte-identical on C0+DEL+C1.** The Python tests (`tests/test_pyrt_errors.py:13-47`) and Rust tests (`errors.rs:338-362`) use identical expected strings. The parity corpus (`tests/test_rust_parser_parity_fixture.py:113-118`) exercises ESC and `\r` via two FAIL entries: `("num", "\x1b[31mabc", FAIL)` and `("stmt", "x\r=\r@", FAIL)`.

---

## Claim 5: U+2028/U+2029 and the parity comparator's `splitlines`

**Substantiated, with a specific interaction the TODO does not mention.**

`tests/parser_parity.py:56`: `lines = msg.splitlines()`. Python's `str.splitlines()` treats U+2028 (Line Separator) and U+2029 (Paragraph Separator) as line terminators. If U+2028 appears in the quoted line of an error message, `splitlines()` would split that message line into two entries in `header_lines`. Both Python and Rust messages would be split the same way (the comparator applies Python `splitlines()` to both). So `py_header == rust_header` would still pass — but the `header_lines` list would have an extra entry from the split, making the caret line misalign with respect to line index assumptions. No test currently exercises this path.

The `terminalsrc.py` line-splitting (line 190: `c == "\n"`) and `terminalsrc.rs` (line 198: `*c == '\n'`) both use only `\n` — U+2028/U+2029 do not create new lines in the source, so they appear as inline text in the error-message line. This confirms they can reach `escape_control_chars` unmodified.

---

## Claim 6: "Extending escape set requires new representation spec"

**TRUE and precise.**

The design doc (`docs/adr/2026/06/11-error-msg-escape/design.md:33`) states: "All escaped codepoints are ≤ U+009F, so two digits always suffice." Bidi/zero-width chars are > U+009F, so `\xHH` (fixed 2 digits) cannot represent them. A new representation would be required (`\u{XXXX}` or `\uXXXX`), and every parity test using literal expected strings would need updating.

---

## Claim 7: "Cross-backend repinning required"

**TRUE.** The parity pin is by identical literal strings in two test files (`errors.rs` tests and `test_pyrt_errors.py`). Changing the escape representation requires updating both. There is no single source of truth for the expected strings — they are duplicated by convention.

---

## Open factual questions

1. **`cross_cdylib.rs:escape_control_chars_for_msg` is a third, untested, divergent implementation.** It applies to `type_name` and `attribute_name` strings in CST bridge error messages, not parse-error line text. The TODO does not mention it. No test covers C1 or TAB behavior for that function. The comment at line 128-129 claims single-`\xHH`-per-codepoint behavior but the code iterates UTF-8 bytes, producing two escapes for any C1 codepoint. Whether this matters depends on whether Python type/attribute names can contain C1 codepoints (unlikely in practice, but not impossible with adversarial `__class__.__name__` manipulation).

2. **No escaping spec document.** The design doc at `docs/adr/2026/06/11-error-msg-escape/design.md` covers the original escape decision but does not describe a representation extension path. Extending to bidi/zero-width would require authoring such a spec as the first step.
