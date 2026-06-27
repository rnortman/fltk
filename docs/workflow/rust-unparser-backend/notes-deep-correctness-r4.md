# Deep correctness review — rust-unparser-backend batch 4

Commit reviewed: 66657a3e192b152178fb179099987c9942de2285 (base 014bbda).
Scope: generator term-handling in `fltk/unparse/gsm2unparser_rs.py` (suppressed /
INCLUDE-INLINE literal / identifier bodies), `num_child_variants` helper in
`gsm2tree_rs.py`. Implemented paths checked against the Python backend
(`gsm2unparser.py`) for behavioral parity. Crate API signatures
(`text`, `concat`, `add_non_trivia`, `add_accumulator`, `push_join`, `push_nest`,
`Doc` variants) verified to match the generated references.

---

## correctness-1 — INLINE identifier term emits broken/diverging code instead of erroring

File: `fltk/unparse/gsm2unparser_rs.py:330-377` (`_gen_term_body` ->
`_gen_identifier_term_body`); routing at `_gen_item_body:313-328`.

What's wrong: `_gen_term_body` routes *every* `gsm.Identifier` term to
`_gen_identifier_term_body`, which unconditionally assumes INCLUDE semantics —
it extracts a child node at `pos`, matches a `cst::{CN}Child::{RefClass}` variant,
read-locks the handle, recurses, and advances `pos + 1`. It never checks
`item.disposition`. SUPPRESS is filtered earlier in `_gen_item_body`, but INLINE
is not, so a single (non-multiple) INLINE identifier (`r := !other;`) falls
through to this INCLUDE path.

Why — contradicting source: the Python backend guards this. `gen_term_unparser`
for an identifier calls `_extract_and_validate_nonsequence_child`
(`gsm2unparser.py:1687`), whose first action (`:267-272`) raises
`RuntimeError("_extract_and_validate_child called on non-included item with
disposition Disposition.INLINE …")` for any non-INCLUDE disposition. An INLINE
identifier is not a CST child node at all: `gsm2tree.py:629-634` *incorporates*
the inlined rule's model into the parent rather than adding the rule's class as a
child variant, so the parent's child enum/label enum do not contain the inlined
rule's class.

Verified by running both backends on `r := !other; other := "x";`:
- Python `generate_unparser` raises `RuntimeError` ("… disposition
  Disposition.INLINE … internal error …") at generation time.
- Rust `generate()` succeeds but emits, in `unparse_r__alt0__item0`:
  `if child_tuple.0 != Some(cst::RLabel::Other)` and
  `match &child_tuple.1 { cst::RChild::Other(shared) => shared, }` while
  `num_child_variants("r") == 0` — i.e. neither `cst::RLabel` nor `cst::RChild`
  is emitted by the CST generator for `R`. The generated `.rs` references
  nonexistent enum types and cannot compile.

Consequence: any grammar with an explicitly inlined rule reference (`!ident`)
that is single and required produces, on the Rust backend, a `.rs` file that
fails to compile (references `cst::{CN}Label::X` / `cst::{CN}Child::X` that the
CST never defines). In the rarer case where the parent independently references
the same rule elsewhere (so the variant happens to exist), it instead emits code
that consumes a child position the inlined content does not occupy, giving wrong
runtime unparse output / spurious `None`. Either way it diverges from the Python
backend, which fails fast at generation time. Cross-backend behavioral parity
(stated design goal; INLINE called out explicitly in the review brief and design
§2.2) is broken. No test covers INLINE identifiers, so this is silent.

Suggested fix: in `_gen_term_body` (or `_gen_identifier_term_body`), guard on
`item.disposition`. For an identifier whose disposition is not INCLUDE, raise at
generation time with a message paralleling the Python backend's, rather than
emitting INCLUDE-shaped extraction. (If INLINE identifiers are intended to be
genuinely supported later, that is a deliberate both-backends change; for parity
now the Rust generator must reject them as the Python one does.)

---

## Paths checked and found correct (parity holds)

- Suppressed items (`_gen_suppressed_item_body`): optional -> pass-through;
  required literal -> single `add_non_trivia(text(...))` with no pos advance;
  required regex/identifier/other -> generation-time raise. Matches
  `_gen_suppressed_quantified_item_body` (`gsm2unparser.py:485-531`), including
  the SUPPRESS-before-multiple routing order (a suppressed `+` literal emits the
  text exactly once).
- INCLUDE/INLINE literal (`_gen_literal_term_body`): INCLUDE validates the Span
  child and advances `pos + 1`; INLINE emits text with no advance. Matches
  `gsm2unparser.py:1719-1748`.
- INCLUDE identifier (`_gen_identifier_term_body`): bounds + optional label
  prelude, variant match (catch-all only when `num_variants > 1`), read-lock,
  recurse, `add_accumulator(&...)`, `pos + 1`. Matches `gsm2unparser.py:1680-1717`
  and the union-label mismatch -> `None` control flow.
- `num_child_variants` (`gsm2tree_rs.py:796-806`) computes
  `len(child_classes) + (1 if has_span else 0)`, identical to the CST
  `_child_enum_block`'s `num_variants` (`gsm2tree_rs.py:839`); the
  `num_variants > 1` catch-all guards align, so no unreachable-arm / non-exhaustive
  mismatch. Span-only vs node-ref single-variant reasoning verified safe (an
  INCLUDE literal forces `has_span`, an INCLUDE identifier forces a node variant).
- Bounds check `pos >= children.len()` then `&children[pos]`: no off-by-one.
- Label variant naming `naming.snake_to_upper_camel` matches the CST label-enum
  variant naming (`_rust_variant_name`, `gsm2tree_rs.py:157-159`).
- Rule entry RULE_START push / RULE_END pop-chain ordering and per-alternative
  acc clone-then-move match `gen_alternatives_unparser` semantics; optional-item
  `acc.clone()` preserves the prior accumulator on absence.
- Crate API signatures (`crates/fltk-unparser-core`) match all generated calls.
