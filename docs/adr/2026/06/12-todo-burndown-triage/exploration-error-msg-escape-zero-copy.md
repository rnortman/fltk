# Adversarial validation: TODO(error-msg-escape-zero-copy)

Concise. Precise. No fluff. Audience: smart LLM/human reviewing the TODO for burndown triage.

---

## Fast path: does it exist as described?

**Yes, exactly as described.**

`crates/fltk-parser-core/src/errors.rs:94-112`:

```rust
pub fn escape_control_chars(s: &str) -> String {
    #[inline(always)]
    fn needs_escape(cp: u32) -> bool {
        (cp <= 0x1F && cp != 0x09) || cp == 0x7F || (0x80..=0x9F).contains(&cp)
    }
    // Fast path: control-free input — return a copy without rebuilding char-by-char.
    if !s.chars().any(|c| needs_escape(c as u32)) {
        return s.to_owned();
    }
    ...
}
```

Single `chars().any(...)` scan; on control-free input returns `s.to_owned()` — one heap allocation, no per-char rebuilding. The Python counterpart at `fltk/fegen/pyrt/errors.py:70-71` returns `text` unchanged (zero allocation in Python).

---

## Callers of `escape_control_chars` (Rust)

**Sole call sites: `errors.rs:167-168`**, both inside `format_error_message`:

```rust
let escaped_prefix = escape_control_chars(&line_text[..split_bytes]);
let escaped_suffix = escape_control_chars(&line_text[split_bytes..]);
```

Both results feed directly into `format!(...)` at line 171-178:

```rust
let mut result = format!(
    "Syntax error at line {} col {}:\n{}{}\n{}^\nExpected:\n",
    line + 1, col + 1,
    escaped_prefix,   // String consumed by format!
    escaped_suffix,   // String consumed by format!
    spaces
);
```

`escaped_prefix` is also used at line 169 to compute `.chars().count()` (codepoint-count for padding), before being moved into `format!`. `escaped_suffix` is used only in `format!`.

**Conclusion: both returned `String` values are immediately consumed by `format!` into a new `String`.** A `Cow<'_, str>` returning the original `&str` slice on the fast path would not eliminate any final String allocation — the `format!` macro always allocates a new `String` for `result`. The saving from `Cow` here is: skip one `s.to_owned()` call per `escape_control_chars` invocation (two calls per `format_error_message` call), i.e., avoid two transient `String` heap allocations that are created only to be consumed by `format!` and dropped.

---

## Is `escape_control_chars` `pub` and exposed to downstream crates?

**Yes, `pub` and re-exported at the crate root.**

- `errors.rs:94`: `pub fn escape_control_chars(s: &str) -> String`
- `lib.rs:25`: `pub use errors::{escape_control_chars, format_error_message, ErrorTracker, ParseContext, TokenType};`

Downstream crates (generated parsers, test fixtures) depend on `fltk-parser-core` via path dep (`tests/rust_parser_fixture/Cargo.toml:19`, `tests/rust_cst_fegen/Cargo.toml:23`). Changing the signature from `-> String` to `-> Cow<'_, str>` is a semver-visible API change.

The function is described in `CLAUDE.md` as part of the public API surface: downstream consumers of FLTK generate parsers that link against this crate.

---

## Is `escape_control_chars_for_msg` in `fltk-cst-core` the same function?

**No.** `crates/fltk-cst-core/src/cross_cdylib.rs:123-138` is a **private duplicate** (`fn`, not `pub fn`), used only within `cross_cdylib.rs` for ABI error messages. It lacks the fast path (no pre-scan), and has a different C0 encoding path (loops over `c.to_string().bytes()` for C1 chars, emitting multiple `\xHH` per multi-byte codepoint). It does not import or call `fltk_parser_core::escape_control_chars`.

---

## How hot is the path?

`format_error_message` is called only on parse failure. Generated parser structs expose it as `fn error_message(&self) -> String` (e.g., `tests/rust_parser_fixture/src/parser.rs:112`, `collision_parser.rs:82`). Call sites in test fixtures use it in failure-path assertions (`native_tests.rs:164,194,214,...`). This is an error-reporting path, not a hot loop. One `format_error_message` call allocates two transient `String`s via `escape_control_chars`, both consumed by `format!`.

---

## Summary of TODO claim accuracy

| Claim | Verdict |
|---|---|
| Fast path exists: pre-scan with `chars().any`, returns `s.to_owned()` on clean input | **Correct** (`errors.rs:100-101`) |
| Python counterpart returns `text` unchanged (zero-copy) | **Correct** (`errors.py:70-71`) |
| `Cow` would eliminate remaining allocation | **Technically correct but marginal**: both callers immediately pass the result into `format!`, so `Cow` avoids 2 transient `String` allocs per error render, not a meaningful saving on an error path |
| Requires changing public function signature | **Correct**: `pub fn`, re-exported from crate root (`lib.rs:25`) |
| Location: `crates/fltk-parser-core/src/errors.rs` | **Correct** |

---

## Open factual questions

None. All facts resolved from source.
