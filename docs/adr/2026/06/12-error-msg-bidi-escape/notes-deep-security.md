# Security review — error-msg-bidi-escape (108ee61..65279b7)

Style: concise, precise, complete, unambiguous. No padding.

Scope: full diff (escape.rs new module, cross_cdylib.rs dedup, errors.rs/errors.py extension, tests, TODO.md). Change is security-positive overall: closes the bidi-reorder and LS/PS line-split vectors in parse-error messages and kills the divergent untested third copy. Verified the Rust `needs_escape` and Python `_needs_escape` predicates define identical sets, the `\xHH`/`\uXXXX` split point (≤U+009F) matches, both fast paths use the shared predicate, and the `splitlines()` line-terminator set (\x1c–\x1e, U+0085, U+2028/29) is fully covered by the escape set. Step-3/step-7 `check_abi_pair` interpolations of the forged marker use Rust `{:?}` (`escape_debug` escapes Cc/Cf), so the unescaped-`s` path is safe.

## security-1

- **File:line:** `tests/test_pyrt_errors.py:25-27` and `:192` (HEAD 65279b7).
- **Issue:** The diff replaced visible `"\u009b"` / `"\u0080"` / `"\u009f"` escape literals (present at base 108ee61) with **raw C1 control characters embedded in the source file**: raw U+009B, U+0080, U+009F in `test_escape_control_chars_c1`, and a raw U+009B inside the input string of `test_format_error_message_no_raw_extended_set_in_output` (line 192, between the `\x7f` and `\u061c` escape sequences). Verified by hexdump (`c2 9b`, `c2 80`, `c2 9f` bytes) and a full-codepoint scan of all changed files; these four are the only raw escape-set chars introduced.
- **Trust boundary / data flow:** The file itself is the artifact — it flows to terminals and review tools whenever displayed (`cat`, `git diff`, `grep`, CI logs).
- **Consequence:** (a) U+009B is CSI — the single-byte Control Sequence Introducer. Displaying the file in a VT-compatible terminal emits a live CSI, the exact terminal escape-sequence-injection asset class the parent error-msg-escape ADR closed; an unlucky following byte sequence becomes an interpreted ANSI control sequence. (b) The characters are invisible in most editors/review UIs, so the assertions silently depend on bytes a reviewer cannot see, and any tool that normalizes/strips control chars (editors, linters, copy-paste) changes test meaning without visible diff. (c) Breaks the cross-language pin convention asymmetrically: the Rust twin tests in `escape.rs` use visible `\u{009b}`-style literals; the "duplicated literal strings" pin is no longer literally comparable by eye. Ironic in a change whose subject is invisible-character injection.
- **Fix:** Restore `"\u009b"`, `"\u0080"`, `"\u009f"` escape-sequence literals (as at base) and use `"\u009b"` in the line-192 input string. Optionally add a repo lint (ruff `PLE2502`-family / custom check) rejecting raw C0/C1/bidi chars in source.

## security-2

- **File:line:** `crates/fltk-cst-core/src/cross_cdylib.rs:278` and `:356` (adjacent to changed code; not modified by the diff).
- **Issue:** The diff routed the four `check_abi_pair` `e.to_string()` interpolations through `escape_control_chars`, but two other error strings in the same file still interpolate PyErr display text raw: `"fltk._native.Span._with_source_unchecked lookup failed: {e}"` and `"cross-cdylib Span type lookup failed (fltk._native.Span): {e}"`.
- **Trust boundary / data flow:** PyErr text originates from Python-level failures during `import fltk._native` / attribute lookup. Reaching it with attacker content requires controlling the Python environment (sys.path shadowing, import hooks) — an attacker with that capability already executes code, so the marginal injection value is low.
- **Consequence:** Control/bidi chars in the exception text pass unescaped into `RuntimeError` messages → same log/terminal-injection class the rest of the file now defends against, but only under an already-compromised-environment precondition. Inconsistency more than exposure.
- **Fix:** Wrap both `{e}` sites in `escape_control_chars(&e.to_string())` for uniformity, or document why these paths are exempt (error text not derived from untrusted parse input).

## security-3

- **File:line:** `crates/fltk-cst-core/src/cross_cdylib.rs` (deletion of `escape_control_chars_for_msg`); behavioral change called out in design §Part (a).
- **Issue:** TAB in Python type/attribute names embedded in CST-bridge `TypeError` text was previously escaped (`\x09`) and now passes through literally, because the canonical function deliberately excludes TAB.
- **Trust boundary / data flow:** Type names are attacker-influenceable via dynamically created classes passed to the underscore-private bridge entry points; TypeError text typically lands in logs/tracebacks.
- **Consequence:** Literal TABs in error text permit whitespace-based field spoofing in TSV/column-aligned log pipelines. No line injection, no escape sequences, no reordering. Design explicitly calls this out as a deliberate alignment decision and the new test pins it; recorded here so the disposition is on the record, not as a defect demanding change.
- **Fix:** None required if the design disposition stands; otherwise re-add TAB to the escape set in both backends (cross-pin churn).

No other findings. Commit reviewed: 65279b7.
