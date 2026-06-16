# Deep security review — span-line-col-api

Base: `8cd6232`  HEAD: `b6c0aac`  Branch: `span-line-col-api`
Scope: hand-written Rust/pyo3 boundary (`span.rs`, `terminalsrc.rs`, `errors.rs`, `src/lib.rs`)
and Python runtime (`terminalsrc.py`, `error_formatter.py`, `span_protocol.py`).
Focus per brief: unsafe indexing/slicing in codepoint↔byte conversion, panics across the
pyo3 boundary, integer over/underflow in position math, untrusted filename strings flowing
into `format_source_line` output, OOB on malformed/empty source. Generated grammar files skipped.

## Summary

No high-confidence exploitable vulnerability found. The new line/col, filename, and
error-formatter surface is defensive: every position-math path is bounds-checked before
indexing, the pyo3 `unwrap`/`expect` calls are all guarded by a preceding `is_none()`/range
check, control-char escaping is applied to source line text on the parse-error path, and the
filename is treated as an opaque stored-and-retrieved string. The findings below are
low-severity / defense-in-depth observations, not confirmed exploits.

---

### security-1 — `format_source_line` does not escape control characters in the source line or message

File: `fltk/fegen/pyrt/error_formatter.py:54,61-66`

Issue: `format_source_line` renders `lc.line_span.text()` (the offending source line) and the
caller-supplied `message` / `filename` directly into the returned string with no escaping of
control/bidi/zero-width characters. Contrast the *parser*-error path
(`crates/fltk-parser-core/src/errors.rs:144-145`, `format_error_message`), which deliberately
runs `escape_control_chars` over the line text precisely to keep raw ESC/CR/bidi-override
characters out of the output, and has a battery of tests asserting "no raw control chars in
message" (`errors.rs:365-437`). The new shared Python formatter omits that protection.

Trust boundary / data flow: the source text is fully attacker-controlled (it is the parsed
input — arbitrary user file or network payload). It enters via the parser, is carried on the
span's `_source`, and reaches the returned string through `lc.line_span.text()`. The
`filename` likewise originates from the caller (potentially attacker-influenced path strings).

Consequence: a crafted source line containing ANSI escape sequences (`\x1b[2J`, `\x1b]0;...\x07`),
a U+202E RLO bidi override, or a CR can corrupt or spoof the terminal/log when the formatted
string is printed to a TTY or written to a log viewer — terminal-injection / log-spoofing. The
caret-alignment math (`' ' * lc.col`, codepoint-based) also misaligns visually when the line
contains zero-width or wide characters, but that is cosmetic. This is the same class of issue
the Rust `format_error_message` path explicitly defends against; the new public helper is a
regression of that hardening for any consumer (including the documented clockwork migration)
that prints its output to a terminal. Severity is bounded by "only matters when rendered to a
control-interpreting sink," but the asymmetry with the sibling formatter is the concrete signal.

Suggested fix: route `line_text` (and ideally `message`) through the existing
`escape_control_chars` helper (exposed in `fltk-cst-core`'s escape module / its Python
equivalent) before interpolation, matching `format_error_message`, and recompute the caret pad
from the escaped prefix length as `errors.rs:144-147` does. If escaping the message body is
undesirable, at minimum escape the source-derived `line_text`.

---

### security-2 — `filename` interpolated unescaped into header line (newline / control injection)

File: `fltk/fegen/pyrt/error_formatter.py:61`; storage `crates/fltk-cst-core/src/span.rs:50,80`,
`fltk/fegen/pyrt/terminalsrc.py:24,249`

Issue: `resolved_filename` is interpolated raw into `f"In {resolved_filename}:..."`. The
filename is an opaque string stored once on the source (Rust `SourceInner.filename`, Python
`SourceText._filename` / `TerminalSource.filename`) and never validated. A filename containing
a newline or control sequence is reflected verbatim into the formatted header.

Trust boundary / data flow: filename enters at source/parser construction
(`SourceText(text, filename=...)`, `TerminalSource(text, filename=...)`,
`Parser(source, filename=...)`). In typical use it is a trusted local path, but a consumer that
threads an externally-derived name (e.g. an uploaded file's original name, an import-path
fragment from the parsed document) hands attacker-influenced bytes straight into the error
string.

Consequence: a filename like `"a\n  rm -rf ~  #"` or one bearing ANSI/bidi sequences lets an
attacker inject extra lines or terminal control into rendered error output (log-spoofing /
terminal-injection), and a newline in the filename breaks the single-line `In <file>:L:C:`
header contract that downstream tooling may parse. Lower likelihood than security-1 because the
filename is usually developer-supplied, but it is unvalidated end-to-end and shares the same
sink.

Suggested fix: same remediation as security-1 — escape the filename (or reject embedded
newlines/control chars at the formatter) before interpolation. Stripping/escaping at the
formatter is preferable to validating at construction since the design intentionally keeps
filename uninterpreted at storage time.

---

## Verified safe (no finding)

- **`resolve_line_col` bisect (`span.rs:215-263`)** — `partition_point` can return
  `ends.len()`; the `idx >= ends.len() → None` guard (`span.rs:243-245`) prevents OOB on
  `ends[idx]`. `ends` is never empty (sentinel push at `span.rs:233-237` guarantees ≥1 element
  when no `\n` is present), so `ends[0]` / `ends[idx-1]` cannot panic. No integer overflow:
  positions are `i64` codepoint counts bounded by source length. Preconditions (`pos >= 0`,
  EOF-clamped) are enforced by every caller before delegating.
- **`Span::line_col_inner` (`span.rs:516-535`)** and Python `Span.line_col`
  (`terminalsrc.py:113-158`) — guard order is correct: sourceless → `None`, `start < 0` →
  `None`, `start > len` → `None`, then EOF clamp, then delegate. No slicing on unchecked indices.
- **pyo3 panic surface** — `line_col_or_raise`'s `self.source.as_ref().unwrap()`
  (`span.rs:795`) is guarded by the `is_none()` check at `span.rs:783`; `py_line_col` /
  `py_filename` return `PyResult`/`Option` and never panic. `text_or_raise`'s `.expect(...)`
  (`span.rs:664`) is likewise guarded. No new `panic!`/`unwrap` reachable across the boundary
  with attacker-controlled state.
- **`format_error_message` byte-slicing (`errors.rs:141-145`)** — `split` is `col.max(0)`,
  converted to a byte offset via `char_indices().nth(split)` with `map_or(len, ...)` fallback,
  so the `line_text[..split_bytes]` / `[split_bytes..]` slices are always on char boundaries and
  in range; the `None` arm at `errors.rs:133-138` avoids a panic on the (documented unreachable)
  out-of-domain position. Control chars in the line are escaped (the defense security-1 notes is
  *missing* from the new Python formatter).
- **`consume_regex` end-byte → codepoint (`terminalsrc.rs:147-153`)** — `partition_point` +
  `debug_assert` on a regex boundary that is always a char boundary; no release-mode OOB
  (returns a valid `end_cp` even if the assert's premise were violated).
- **Filename storage** — never branched on, never used in a filesystem/network operation; it is
  inert until it reaches the formatter sinks flagged in security-1/-2. No path-traversal or SSRF
  surface introduced (the filename is display-only).
- **`_source_filename` Python field** — `compare=False, hash=False` preserves `Span`
  equality/hash; no security-relevant change to identity.
