# Deep correctness review — Rust CST native span (§2.5/§2.6)

Concise. Precise. Audience: smart LLM/human. Commit reviewed: 1b54878 (base f8fdb53).
Scope: parse-path native source-bearing spans, fltk2gsm migration, native node ctors,
span-source-loss fix, protocol widening, gate fixes. Logic/control/data-flow only.

## correctness-1

`crates/fltk-cst-core/src/span.rs:157` (`text_str`) + `:221` (`text`), consumed via
`fltk/fegen/fltk2gsm.py:30` (`_span_text` → `span.text()`).

What's wrong: the Rust `Span.text()`/`text_str()` slice the source by **byte** offsets
(`text[start..end]` with `is_char_boundary` guards). But the spans are produced by the
**Python** `TerminalSource` parser (`fltk/fegen/pyrt/terminalsrc.py` `consume_literal`/
`consume_regex`), whose `start`/`end` are Python **codepoint** indices. Under the Rust CST
backend the parse path (`gsm2parser._make_span_expr`) feeds those codepoint positions into
`fltk._native.Span.with_source(start, end, source_text)` unchanged, then `text()` reinterprets
them as bytes.

Why: verified empirically —
`fltk._native.Span.with_source(1, 4, SourceText('héllo')).text()` returns `'él'` while the
codepoint slice `'héllo'[1:4]` is `'éll'`. Offsets diverge as soon as any non-ASCII (multi-byte
UTF-8) char precedes/spans the range.

Consequence: this is an **introduced regression** on the §2.6 consumer path. Before this change
`fltk2gsm` read `self.terminals[span.start:span.end]` (codepoint slice — correct on every
backend). After this change `_span_text` calls `span.text()` first, and for a source-bearing
Rust-backend child span `text()` returns non-`None`, so the codepoint fallback is never reached.
For any grammar source containing non-ASCII bytes before/within an identifier/literal/regex
span, `visit_identifier`/`visit_literal`/`visit_regex` now extract the **wrong substring** under
the Rust backend (truncated/shifted by the byte/codepoint delta), producing a malformed GSM —
silently, no error. Pure-ASCII inputs (the test corpus) are unaffected, which is why the gate is
green. The same byte/codepoint mismatch also makes the §4-item-6 `node.span.text()` acceptance
return wrong text for non-ASCII under the Rust backend, though fltk2gsm is the in-tree consumer
that newly depends on it.

Suggested fix: make the parse path's offsets and `Span.text()` agree on one unit across backends.
Either (a) have the Rust-backend parse path convert Python codepoint positions to UTF-8 byte
offsets before calling `Span.with_source` (and keep `text_str` byte-based), or (b) make the Rust
`Span.text_str`/`text` slice by codepoint to match the Python parser's index space. Add a
non-ASCII fixture exercising fltk2gsm under the Rust backend to lock the chosen semantics.

## Notes / non-findings (verified clean)

- `gsm2parser._make_span_expr` (`:252`) + `_span_start` save-before-loop (`:531`, `:725`):
  control flow correct — `_span_start` captures `pos` before the loop mutates it; the `+`
  quantifier no-progress check (`:585`) now compares against `_span_start` instead of
  `result.span.start`, equivalent and Rust-backend-safe (no `.start` read on stored span).
- `_source_text` field init (`gsm2parser.py:93`, generated `fltk_parser.py:16`): set in
  ctor before any parse method runs; every `with_source` call references it. No use-before-init.
- Span getter / `EnumChild::to_pyobject` source-preservation (`gsm2tree_rs.py`): round-trips
  source via `source_full_text_str()` → `fltk._native.SourceText` → `with_source`. Sourceless
  branch falls back to 2-arg `Span(start,end)`. Logic sound; the source-loss TODO is genuinely
  fixed.
- `extend_children` (generated, e.g. `cst.rs:775`): clones each `(label, child)` into the native
  `Vec`; `PartialEq` wildcard `_ => false` emitted only when >1 variant (`gsm2tree_rs.py:377`) —
  correct, single-variant wildcard would be unreachable.
- Native enum `PartialEq` + node eq: structural, compares `(start,end)` spans and recurses into
  `Box<Child>`; native_tests.rs differing-span cases pass because they differ in start/end (span
  eq ignores source by design). Consistent.
- Protocol widening `span: terminalsrc.Span | fltk._native.Span` (`gsm2tree.py:568`) is additive;
  concrete Python CST annotation left unchanged. TYPE_CHECKING-guarded imports. Pyright-clean
  consumer test passes.
- New `#[getter] get_start/get_end` on Rust `Span` (`span.rs:342/350`) deviate from design Option
  B ("no Python getter"), but are additive and not a correctness bug on their own. They do mean a
  Rust-backend span now answers `.start`/`.end` as **byte** offsets; if any consumer slices
  `terminals[span.start:span.end]` they hit the same byte/codepoint issue as correctness-1. The
  in-tree `_span_text` fallback (`fltk2gsm.py:33`) does exactly this slice, but only on the
  sourceless path (not reached for Rust-backend sourced spans).

Verified: `make`-built extension; 203 targeted pytests green (rust_span, rust_cst_poc,
phase4_fixture, test_cst_protocol, clean_protocol_consumer_api).
