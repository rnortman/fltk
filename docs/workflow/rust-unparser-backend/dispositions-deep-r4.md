# Dispositions — deep review round 4 (rust-unparser-backend)

Base: 014bbda. Reviewed HEAD: 66657a3. Fixes committed at: f237b16.

All fixes verified with `uv run pytest` (2227 passed, 1 skipped), `ruff`, `pyright`,
and the pre-commit `make check` (full cargo lanes pass — the generated Rust fixture
still compiles, confirming no generated-code drift from the `gsm2tree_rs.py` refactor).

---

## correctness-1
- Disposition: Fixed
- Action: Added a disposition guard in `_gen_identifier_term_body`
  (`fltk/unparse/gsm2unparser_rs.py:370-383`): a non-INCLUDE (inlined) identifier term
  now raises `RuntimeError` at generation time instead of emitting INCLUDE-shaped
  extraction. New test `test_inline_identifier_rejected_at_generation` plus the
  surrounding routing is covered end-to-end.
- Severity assessment: High. Confirmed empirically: for `r := keep:"k" . !other; ...`
  the Python backend raises in `_extract_and_validate_nonsequence_child` while the
  pre-fix Rust backend silently generated `.rs` referencing `cst::RChild::Other` /
  `cst::RLabel::Other` for a rule whose CST has no such variant (or, in the rarer
  variant-exists case, consumed a child position the inlined content does not occupy) —
  a broken-compile / wrong-output cross-backend parity break (design §2.2).

## errhandling-1
- Disposition: Fixed
- Action: Replaced `assert isinstance(item.term, gsm.Identifier)` with an explicit
  `RuntimeError` naming the rule (`fltk/unparse/gsm2unparser_rs.py:360-369`). Test
  `test_identifier_term_body_rejects_non_identifier_term`.
- Severity assessment: Low-medium. A generator-internal invariant; the prior assert is
  stripped under `python -O`, after which a misrouted term's `.value` would silently feed
  wrong text into emitted Rust. The raise makes a misroute fail fast with rule context.

## errhandling-2
- Disposition: Fixed
- Action: Replaced `assert isinstance(item.term, gsm.Literal)` with an explicit
  `RuntimeError` naming the rule (`fltk/unparse/gsm2unparser_rs.py:409-418`). Test
  `test_literal_term_body_rejects_non_literal_term`.
- Severity assessment: Low-medium. Same `-O`-strip class as errhandling-1; a misrouted
  Regex/Identifier (both carry `.value`) would otherwise embed a pattern/rule name as
  literal text — quietly wrong output rather than a crash.

## errhandling-3
- Disposition: Fixed
- Action: Fixed via the same change as quality-1 (the two findings target the same
  latent `_gen_child_prelude` bug). `_gen_child_prelude` now binds `child_tuple` whenever
  `need_tuple or item.label` (`fltk/unparse/gsm2unparser_rs.py:451`), so the undefined-
  variable path the finding describes can no longer be generated.
- Severity assessment: Medium (latent). No current caller triggers it, but a future
  labeled-item caller that passed `need_tuple=False` would have emitted Rust referencing
  an unbound `child_tuple`, caught only at Rust compile time.
- Note: I applied quality-1's self-enforcement (bind the tuple) rather than this finding's
  proposed raise-on-violation. Binding is strictly better: the labeled case is legitimate
  and should work, not error. The "broken error path" is eliminated rather than reported.

## quality-1
- Disposition: Fixed
- Action: `_gen_child_prelude` binding guard changed to `if need_tuple or item.label`
  (`fltk/unparse/gsm2unparser_rs.py:451`); `_gen_validate_span_child` `need_tuple`
  simplified to `num_variants > 1`, dropping the now-redundant `bool(item.label)` term
  (`:478`). The method self-enforces the labeled⇒tuple-bound invariant.
- Severity assessment: Medium (latent). Removes a hidden caller contract that every future
  `_gen_child_prelude` caller (quantified loops, regex, nested-alt terms) would otherwise
  have to reproduce.

## reuse-1
- Disposition: Fixed
- Action: Both inline `(1 if has_span else 0) + len(child_classes)` sites now call
  `self.num_child_variants(rule_name)` — `_child_enum_block`
  (`fltk/fegen/gsm2tree_rs.py:850`) and `_label_type_info` (`:1774`, which also dropped its
  now-unused `child_class_names, has_span` unpack). The variant arithmetic lives only in
  `num_child_variants`.
- Severity assessment: Low. Maintainability; the three sites could otherwise drift on a
  future child-variant-category change.

## efficiency-1
- Disposition: Fixed
- Action: Memoized `_child_variants_for_rule` on `RustCstGenerator` via a `rule_name`-keyed
  cache (`fltk/fegen/gsm2tree_rs.py:187` cache init; `:302-318` lookup/populate). Result is
  a pure function of the immutable rule model; all callers treat the returned list as
  read-only (verified).
- Severity assessment: Low. Generator-time CPU only (one-shot per build, scales with
  grammar size); trivially eliminable and also helps the existing CST-generator callers,
  including the new `num_child_variants` double-call introduced by reuse-1.

## test-1
- Disposition: Fixed
- Action: Added `test_inline_literal_body_emits_text_without_advance`
  (`tests/test_rust_unparser_generator.py`). Implemented as a unit test on
  `_gen_literal_term_body` (not the finding's end-to-end `r := !"x";`): inline literals
  cannot be modeled — the CST builder asserts inline⇒identifier — so an end-to-end grammar
  is unconstructable. The unit test pins the INLINE branch: emits text, no `pos + 1`, no
  child extraction.
- Severity assessment: Low. Coverage of an existing untested branch; a refactor unifying
  the INCLUDE/INLINE advance would otherwise go undetected.

## test-2
- Disposition: Fixed
- Action: Added `test_suppressed_required_subexpression_raises`
  (`tests/test_rust_unparser_generator.py`). Sub-expression terms are `Sequence[Items]`
  (a list of alternatives), not a bare `gsm.Items`; the test constructs that and asserts the
  catch-all raise in `_gen_suppressed_item_body`.
- Severity assessment: Low. Coverage of the final fallthrough raise; guards against it
  silently becoming a pass-through.

## test-3
- Disposition: Fixed
- Action: Added `test_single_regex_term_stays_scaffold`
  (`tests/test_rust_unparser_generator.py`) — `r := foo:/[0-9]+/;` emits the pass-through
  (no `add_non_trivia`, no `node.children()`), mirroring the existing
  `test_multiple_quantifier_literal_stays_scaffold` scaffold-pinning pattern.
- Severity assessment: Low. Pins current scaffold so a future regex-term increment that
  misroutes regex to the literal body (emitting a fixed string instead of the matched span
  text) is caught.

## reuse-2
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Low. Three short generation-time error-message strings are duplicated
  across the two backends; the typo divergence the diff corrected was a symptom. Messages
  are now in sync.
- Rationale: The only fix that addresses the finding's actual concern (cross-backend message
  sync) is a *shared* helper coupling `gsm2unparser.py` and `gsm2unparser_rs.py`; a
  Rust-only helper leaves the cross-backend duplication intact. Design §2 (lines 82-86)
  deliberately keeps the two generators independent string emitters — "side-by-side
  auditable, exactly as gsm2parser.py and gsm2parser_rs.py sit today" — and states the
  separate-generator approach "keeps the Python backend (and its public API) at zero risk."
  Introducing a shared dependency edge (especially into the stable Python backend) for three
  short, stable, now-synced strings undermines that explicit decision for marginal benefit.
  A TODO would be inappropriate because the design argues this sharing should *not* happen.

---

## security (notes-deep-security-r4)
- No findings reported; nothing to disposition. The reviewer confirmed all interpolated
  grammar text routes through `rust_str_lit` and that grammar/format inputs are
  build-time developer artifacts, not runtime untrusted input.
