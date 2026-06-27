# Deep correctness review — batch 5 (generator term-handling)

Commit reviewed: 5f7b5cb1d33150b1125daf6e0f19c4051ab28c30 (base f9ed936)
Scope: `fltk/unparse/gsm2unparser_rs.py` regex / sub-expression / before-after item
spacing handling; `crates/fltk-unparser-core/src/doc.rs` (`before_spec`/`after_spec`);
`lib.rs` re-exports. Cross-backend parity vs `fltk/unparse/gsm2unparser.py`.

Verification performed: line-by-line comparison against the Python `UnparserGenerator`,
plus generating the fixture unparser (`fltk/fegen/test_data/rust_parser_fixture.fltkg`)
both with the default config and with a custom `.fltkfmt` exercising before/after
label+literal spacing and rule-level group/nest, and `cargo check` of the generated
`.rs` against `fltk-cst-core` + `fltk-unparser-core`: 0 errors, 137 unique methods, no
duplicate method names.

## correctness-1 — Regex INLINE (non-INCLUDE) disposition diverges: Rust emits code, Python rejects

File: `fltk/unparse/gsm2unparser_rs.py:635-638` (`_gen_regex_term_body`, the
`else` branch of the disposition check).

What's wrong: For a regex term whose disposition is not `INCLUDE`, the Rust generator
emits a working body (binds the `Span`, reads `span.text()`, adds it as non-trivia,
returns without advancing `pos`). The Python backend does the opposite: its `Regex`
branch (`gsm2unparser.py:1750`) calls `_extract_and_validate_nonsequence_child`
*unconditionally*, and that method's first statement is an explicit
`raise RuntimeError(...)` whenever `item.disposition != gsm.Disposition.INCLUDE`
(`gsm2unparser.py:267-272`). So Python *rejects* a non-INCLUDE regex; Rust *accepts* it.
The only non-INCLUDE, non-SUPPRESS disposition is `INLINE`, and the author has pinned the
Rust behavior as intended in `test_regex_inline_body_reads_span_without_advance`, so the
two backends contradict each other on the same input.

Why / trace: In normal (non-`-O`) runs this divergence is masked: `RustUnparserGenerator.__init__`
builds a `RustCstGenerator` → `CstGenerator`, whose `model_for_items`
(`gsm2tree.py:629-630`) executes `assert isinstance(item.term, gsm.Identifier)` for any
`INLINE` item at construction time, so an `INLINE` regex raises `AssertionError` before
`generate()` runs (confirmed by repro). But that guard is a bare `assert`, stripped under
`python -O` / `PYTHONOPTIMIZE`. Python's rejection is an explicit `raise` that survives
`-O`. The same file deliberately uses explicit `raise` over `assert` for exactly this
reason (`_gen_regex_term_body:613-622` routing guard says "surviving `python -O`").

Consequence: Under `python -O`, a grammar containing an `INLINE`-dispositioned regex
term (e.g. `r := !/[a-z]+/;`) makes the Python unparser generator raise `RuntimeError`
at generation but the Rust generator silently emit a regex body — opposite outcomes for
the same grammar, violating the cross-backend generation-equivalence goal. Off `-O` both
reject (one `AssertionError`, one `RuntimeError`), so impact is limited to optimized runs;
hence low confidence / narrow trigger, but it is a genuine latent parity break and the
else-branch is dead code in every other configuration.

Suggested fix: Make `_gen_regex_term_body` reject non-INCLUDE dispositions with an explicit
`raise` (mirroring the literal/identifier routing-guard style already in this file and the
Python backend's `_extract_and_validate_nonsequence_child` message), rather than emitting a
no-advance body. If non-INCLUDE regex is intended to be supportable later, that must be a
deliberate both-backends change, not a Rust-only superset.

## Non-findings examined (parity confirmed correct)

- Before/after item spacing (`_gen_alternative_body` + `_item_spacing_lines`): placement
  matches Python `gen_alternative_unparser` exactly — `BeforeSpec` added unconditionally
  ahead of the item call (persists when an optional item is absent), `AfterSpec` added only
  on the success path (inside the `if let Some` block for optional items). Verified in
  generated `unparse_stmt__alt0` / `unparse_expr__alt0`. `_item_spacing_lines`'
  `if spacing is None` matches Python's `if before_spacing:`: `Doc` defines no
  `__bool__`/`__len__`, so every non-None `Doc` (incl. `Nil`) is truthy — no divergence.
- Regex INCLUDE: bounds→label→type order, single-vs-multi-variant catch-all gating, and
  `pos + 1` advance all match Python; `span.text()?` → enclosing `None` is the documented
  sourceless-span behavior (design §3).
- Sub-expression handling (`_gen_subexpr_term_body` / `_gen_subexpr_methods` /
  `_gen_alts_dispatch`): delegates to `{item_prefix}__alts` from the *passed* `pos` with no
  rule anchors; prefix-driven names match the Python path-join scheme; recursion into
  nested sub-expressions verified (`unparse_r__alt0__item0__alts__alt1__item0__alts`), acc
  clone-all-but-last is correct for Rust ownership. Compiles.
- `isinstance(item.term, list | tuple)` is a harmless superset of Python's `isinstance(term, list)`:
  sub-expression terms are always built as lists (`fltk2gsm.visit_alternatives`).
- `before_spec`/`after_spec` in `doc.rs` correctly wrap into `BeforeSpec`/`AfterSpec`.

## Minor note (tied to deferred work — not a current-batch bug)

Python gates before-spacing on disposition: `if not isinstance(item_disposition, Omit | RenderAs)`
(`gsm2unparser.py:1604-1605`). The Rust `_gen_alternative_body` adds before/after spacing
unconditionally. With any default/normal config this is identical (no `Omit`/`RenderAs`
anchors → all items `Normal`). It only diverges once a config uses `omit`/`render`, and
`Omit`/`RenderAs` item-body handling is itself deferred — so no incremental observable
divergence today. Flagging so the disposition gate is restored when Omit/RenderAs lands.
