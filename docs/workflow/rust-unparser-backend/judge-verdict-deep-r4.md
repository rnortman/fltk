# Judge verdict — deep review

Phase: deep. Base 014bbda..HEAD f237b16. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 11 findings + a no-findings security note.

## Added TODOs walk

No `TODO(slug)` comments were added in this diff and no disposition is a TODO. Section empty.

## Other findings walk

### correctness-1 — Fixed
Claim: `_gen_term_body` routes every `gsm.Identifier` to `_gen_identifier_term_body`, which assumes INCLUDE semantics and never checks `item.disposition`; a single+required INLINE identifier (`!other`) falls through to INCLUDE-shaped extraction. Consequence: emitted `.rs` references `cst::{CN}Child`/`{CN}Label` variants the CST never defines (or consumes a position the inlined content doesn't occupy) — broken compile / wrong output, and a cross-backend parity break (Python raises at generation, design §2.2). Blocker.
Code at `gsm2unparser_rs.py:370-383`: after the Identifier type check, `if item.disposition != gsm.Disposition.INCLUDE:` raises a `RuntimeError` naming the rule and term, paralleling the Python backend's generation-time rejection. SUPPRESS identifiers are filtered earlier into `_gen_suppressed_item_body`, so INLINE is the only non-INCLUDE disposition reaching the guard. Test `test_inline_identifier_rejected_at_generation` (`r := keep:"k" . !other; other := "x";`) asserts `generate()` raises matching "only INCLUDE identifier references" — passes.
Assessment: fix addresses the consequence at the named site; behavior now matches Python (fail-fast at generation). Accept.

### errhandling-1 — Fixed
Claim: `assert isinstance(item.term, gsm.Identifier)` is an internal routing guard with no rule context; stripped under `python -O`, after which a misrouted term's `.value` silently feeds wrong text into emitted Rust. Should-fix (generator-internal invariant, latent under -O).
Code at `gsm2unparser_rs.py:360-369`: `if not isinstance(item.term, gsm.Identifier): raise RuntimeError(f"... reached with {type(item.term).__name__} term in rule {rule_name!r}")`. Test `test_identifier_term_body_rejects_non_identifier_term` asserts raise matching "_gen_identifier_term_body reached with Literal" — passes.
Assessment: exactly the requested change; survives -O and names the rule. Accept.

### errhandling-2 — Fixed
Claim: same class for `assert isinstance(item.term, gsm.Literal)` in `_gen_literal_term_body`; a misrouted Regex/Identifier (both carry `.value`) embeds a pattern/rule name as literal text. Should-fix.
Code at `gsm2unparser_rs.py:410-418`: explicit `RuntimeError` naming the rule. Test `test_literal_term_body_rejects_non_literal_term` (Regex term) asserts raise matching "_gen_literal_term_body reached with Regex" — passes.
Assessment: parallels errhandling-1; correct. Accept.

### errhandling-3 — Fixed
Claim: when `need_tuple=False` and `item.label` is truthy, `_gen_child_prelude` skips the `child_tuple` binding yet emits the label check referencing `child_tuple.0`; generated `.rs` has an unbound variable, caught only at Rust compile (E0425). Medium/latent — no current caller triggers it, but a future labeled caller with `need_tuple=False` would.
Code at `gsm2unparser_rs.py:451`: `if need_tuple or item.label:` binds the tuple, so the label check at `:456` always has its operand. The undefined-variable path can no longer be generated. Responder applied quality-1's bind-the-tuple self-enforcement rather than the finding's proposed raise.
Assessment: binding is the stronger fix — the labeled case is legitimate and now works rather than erroring, and the broken emission is eliminated at the source rather than converted to a Python error. The bound `child_tuple` is consumed by the label check in every branch that binds it, so no dead binding. Accept.

### quality-1 — Fixed
Claim: `_gen_child_prelude` binds `child_tuple` only when `need_tuple=True` but references it in the unconditional label check — a hidden caller contract; `_gen_validate_span_child` carries `bool(item.label)` solely to prevent the broken path, splitting the invariant across two methods. Fix: `if need_tuple or item.label`, then simplify span-child `need_tuple` to `num_variants > 1`. Medium/latent (maintainability + future-caller correctness).
Code: `:451` `if need_tuple or item.label`; `:478` `need_tuple = num_variants > 1` (the `bool(item.label)` term dropped). Method now self-enforces "labeled ⇒ tuple bound".
Assessment: exactly the proposed change; same change resolves errhandling-3. Accept.

### reuse-1 — Fixed
Claim: `gsm2tree_rs.py` inlines `(1 if has_span else 0) + len(child_classes)` at two in-class sites that should call the new `num_child_variants`, so the method's promised consolidation isn't delivered; future arithmetic changes need three edits. Low (maintainability).
Code: `_child_enum_block` `:850` and `_label_type_info` `:1774` now call `self.num_child_variants(rule_name)`; `:1774` also dropped the now-unused `child_class_names, has_span` unpack. Variant arithmetic lives only in `num_child_variants`.
Assessment: both sites consolidated. Accept.

### efficiency-1 — Fixed
Claim: `_child_variants_for_rule` re-walks `model.types` + `sorted()` on every call; called once per identifier item and per INCLUDE-literal item, plus existing CST-generator callers, all uncached. Generator-time CPU only. Low.
Code: `_child_variants_cache` init at `gsm2tree_rs.py:187`; lookup/populate at `:302-318`. Cache returns `(sorted(child_class_names), has_span)`.
Read-only safety check (a memoization returning a shared mutable list is the classic regression here): grepped all four `_child_variants_for_rule` callers (`:453, :816, :828, :1008`) — each only `len()`s, iterates, or `set.update()`s the list; no `.append/.sort/.extend/.remove/.insert/.pop/.clear/.reverse` on any `child_classes` anywhere in the file. The cache is safe — no correctness regression introduced by the fix. Accept.

### test-1 — Fixed
Claim: INLINE branch of `_gen_literal_term_body` (emit text, no `pos+1`) is untested; a refactor unifying INCLUDE/INLINE advance would go undetected.
Disposition implemented as a unit test (`test_inline_literal_body_emits_text_without_advance`) on `_gen_literal_term_body` rather than the finding's end-to-end `r := !"x";`. Justification: an inline literal is unconstructable end-to-end (CST builder asserts inline⇒identifier). The unit test drives the INLINE `gsm.Item` directly and asserts the body emits `add_non_trivia(text("x"))` with no `pos + 1` and no `node.children()` — exactly the branch the finding targets. Passes.
Assessment: the deviation is sound and the test pins the precise branch. Accept.

### test-2 — Fixed
Claim: the final fallthrough raise in `_gen_suppressed_item_body` (suppressed required sub-expression) is untested; could silently become a pass-through.
`test_suppressed_required_subexpression_raises` constructs a sub-expression term (`[gsm.Items(...)]` — not Literal/Regex/Identifier) under SUPPRESS/REQUIRED and asserts the catch-all raise matching "cannot be recreated from CST". Passes.
Assessment: reaches the intended fallthrough; guards it. Accept.

### test-3 — Fixed
Claim: the pass-through for a non-suppressed single-quantifier Regex term is untested; a future regex increment could misroute it to the literal body (fixed string instead of matched span).
`test_single_regex_term_stays_scaffold` (`r := foo:/[0-9]+/;`) asserts `add_non_trivia` and `node.children()` are both absent — if regex were misrouted to the literal body, `add_non_trivia` would appear and the test would fail. Passes.
Assessment: assertion is slightly weaker than the finding's suggested exact-body match but still catches the misrouting the finding cares about. Accept.

### reuse-2 — Won't-Do
Claim: three required-suppressed `RuntimeError` messages are character-identical across `gsm2unparser_rs.py:474-490` and `gsm2unparser.py:516-530`; the "lable"→"label" typo this diff fixes is the symptom; a shared helper would make message changes atomic across backends. Consequence: future re-divergence. Low (maintainability).
Rationale: the duplication is *cross-backend* (the three messages differ from each other within the Rust file, so a Rust-only helper — the finding's literal suggestion — deduplicates nothing). The only fix addressing the stated concern is a shared helper coupling the two generators, and design §2 (lines 82-86, verified in `design.md`) deliberately keeps them as independent string emitters: "this keeps the Python backend (and its public API) at zero risk and keeps the two generators side-by-side auditable, exactly as `gsm2parser.py` and `gsm2parser_rs.py` sit today."
Assessment: the rejection is grounded in source — the finding's own literal fix doesn't address its concern, and the real fix introduces a dependency edge the design explicitly forbids (including into the stable Python backend). This is a "contradicts a documented, deliberate design decision" rejection, not a "not now / out of scope" dodge. The messages are now synced; the marginal future-divergence risk does not outweigh the design's independence guarantee. Accept Won't-Do.

### security — no findings
Reviewer reported nothing: all interpolated grammar text routes through `rust_str_lit`, identifiers are constrained to `/[_a-z][_a-z0-9]*/`, and grammar/format inputs are build-time developer artifacts, not runtime untrusted input. Nothing to disposition.

## Approved

11 findings: 10 Fixed verified (correctness-1, errhandling-1/2/3, quality-1, reuse-1, efficiency-1, test-1/2/3), 1 Won't-Do sound (reuse-2). Security: no findings. All 49 generator tests pass; new tests present and passing.

---

## Verdict: APPROVED

All dispositions acceptable. Every Fixed claim verified against the code at its named line; the two same-root fixes (errhandling-3 / quality-1) verified once; the efficiency-1 memoization checked for the shared-mutable-list regression and found safe; the reuse-2 Won't-Do grounded in design §2's deliberate generator independence.
