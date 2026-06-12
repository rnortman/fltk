# Efficiency review — error-msg-escape

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Reviewed: ef8288c..8da7924 (HEAD 8da7924). Scope: `crates/fltk-parser-core/src/errors.rs`, `fltk/fegen/pyrt/errors.py`, `crates/fltk-parser-core/src/lib.rs`, tests.

Context: all changed code is on the error-formatting path — runs once per failed parse, input bounded by one source line. Nothing here is hot. Findings below are real waste but low-stakes; fix or disposition cheaply.

## efficiency-1 — Rust: line traversed ~4x with 3 intermediate allocations

`crates/fltk-parser-core/src/errors.rs:150-159` (`format_error_message`).

Sequence: `line_text.chars().collect::<Vec<char>>()` (alloc 1), `prefix: String` collect (alloc 2), `suffix: String` collect (alloc 3), then `escape_control_chars` on each (allocs 4–5, unavoidable), then `escaped_prefix.chars().count()` re-walks the escaped prefix. The `Vec<char>` exists only to convert a codepoint index to a split point.

Consequence: per-error CPU/alloc cost proportional to line length × ~4. Bites when a service formats many errors on long single-line inputs (minified/generated sources) — bounded, never pathological, but pure overhead.

Fix: find the byte offset of codepoint `split` via `line_text.char_indices().nth(split).map_or(line_text.len(), |(i, _)| i)`, then slice `&line_text[..byte_split]` / `&line_text[byte_split..]` — no `Vec<char>`, no intermediate prefix/suffix Strings. Optionally have the escape loop over the prefix return its output char count to drop the `chars().count()` re-walk.

## efficiency-2 — Rust: `format!` allocates a temp String per escaped char

`crates/fltk-parser-core/src/errors.rs:91` — `out.push_str(&format!("\\x{:02x}", cp))` inside the per-char loop of `escape_control_chars`.

Consequence: one heap allocation per control character. Adversarial input (a line of N controls — exactly the input this fix targets) costs N temp allocations. Bounded by line length; cold path.

Fix: `use std::fmt::Write; write!(out, "\\x{cp:02x}").unwrap();` — formats directly into `out`, zero temp allocations. Same output bytes.

## efficiency-3 — both backends: no fast path for control-free lines (the common case)

Rust `errors.rs:87-96`; Python `fltk/fegen/pyrt/errors.py:58-72`.

The overwhelmingly common error line contains no escapable characters, yet both implementations rebuild it char-by-char unconditionally. Python regressed from a direct slice interpolation (old code) to a per-char loop + list append + join on every formatted error. Rust copies every char into a fresh String even when output == input.

Consequence: every formatted parse error — including the 99% control-free case — now pays O(line) per-char Python bytecode / Rust copy where the old code paid a slice. Per-error cost only; matters for tooling that formats errors in bulk (test harnesses, LSP-style loops over many bad inputs).

Fix: pre-scan and return input unchanged when clean — Python: `if not any(...escapable...): return text` (or `re.sub` with a compiled class, which also handles the dirty case faster than the per-char loop); Rust: `Cow<'_, str>` return or `if !s.chars().any(needs_escape) { return s.to_owned() }`. Note: `escape_control_chars` is documented as public cross-backend API, so keep the signature decision deliberate (`Cow` changes the Rust signature; the early-return form does not).

No other findings. Test additions (2 parity corpus entries, unit tables) are appropriately sized; no redundant work, no concurrency opportunities missed, no memory growth, no recurring no-op updates in scope.
