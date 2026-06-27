# Judge verdict — design review

Phase: design. Doc: `docs/workflow/rust-unparser-backend/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings, all dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: PyO3 `unparse_{rule}` returns a rendered `str`, but the Python backend's
`Unparser.unparse_{rule}(node) -> Optional[UnparseResult]` does not render (caller chains
`resolve_spacing_specs` + `Renderer.render`). Consequence: undeclared public-API call-site
divergence (CLAUDE.md "no wholesale call-site churn"), and the design both *decided*
string-return (§2.4) and *re-opened* it (open question 2) — a self-contradiction.

Source grounding confirmed: Python `unparse_{rule}` returns `maybe_unparse_result_type`
(`gsm2unparser.py:198-210`), no render in the generated class; chaining lives in plumbing.

Design now (verified):
- §2.3 (lines 258-264) names the two deliberate Python-surface divergences (constructor +
  per-rule method contract), called out rather than incidental.
- §2.4 (lines 266-292) rewritten: declares the rendered-string return as a deliberate,
  documented divergence with rationale (Doc/UnparseResult are pure-Rust, no PyO3 bindings;
  cross-backend contract is rendered-string parity) plus a bounded migration note.
- Open question 2 (lines 410-415) reframed to the genuinely-open additive part (whether to
  *also* expose the intermediate Doc to Python); no longer re-asks the settled question.

Requirements check (is this design's call to make, or does it need user arbitration?):
requirements.md line 79 sets the cross-backend contract as rendered-string parity ("unparse
with both backends, confirm the formatted output matches"), not per-method return-type
parity; line 11 forbids *skipping* the pipeline (the core still runs Doc→resolve→render and
keeps Doc-producing methods, §2.4:294-299, so the string is the pipeline's product, not a
bypass); line 55 blesses the constructor divergence; lines 11/29 mark internal
representation/decomposition as design decisions. The divergence is therefore consistent
with requirements, not a contradiction. The reviewer's offered fix (a) — "fold open-Q2 into
a stated decision" — is exactly what was done.
Assessment: contradiction removed, divergence declared and grounded; no requirement
contradicted. Fix addresses the consequence. Accept. No escalation needed.

### design-2 — Fixed
Claim: `_doc_to_rust_expr` was specified to handle `Group`/`Nest`/`Join`, but its declared
Python analog `_doc_to_combinator_expr` raises on those — silent cross-backend divergence
(Python errors at gen time, Rust would generate and format) for a `join … by group/nest/join`
separator config.

Source grounding confirmed: `_doc_to_combinator_expr` (`gsm2unparser.py:396-426`) handles
only NIL/NBSP/LINE/SOFTLINE/HARDLINE, `HardLine`, `Text`, `Concat`; everything else raises
`ValueError("Unknown Doc type: …")` at :424-426. Join separator can be group/nest/join via
`_doc_literal_cst_to_doc` (`fmt_config.py:398-419`) through `_process_join_statement`
(:708-722); the JOIN_BEGIN separator is fed to `_doc_to_combinator_expr` at
`gsm2unparser.py:240`, :1512, :1556.

Design now (lines 184-201): `_doc_to_rust_expr` "mirrors `_doc_to_combinator_expr` (:396)
**exactly** … raises the same `ValueError` … on anything else — including `Group`, `Nest`,
and `Join`," with the cross-backend rejection documented and separator-support extension
called out as a future deliberate both-backends change. Matches the reviewer's suggested fix
exactly.
Assessment: fix restores exact-domain parity at the named helper. Accept.

### design-3 — Fixed
Claim: per-construct mapping covered RULE_START/RULE_END anchors but omitted item-level
(before/after-item) GROUP/NEST/JOIN begin/end push/pop. Consequence: an implementer
following the spec literally would drop mid-rule `group/nest/join from … to …`, and the
fixture as specified might not catch it.

Source grounding confirmed: `_gen_anchor_operations_before_item` (`gsm2unparser.py:1472-1515`)
and `_after_item` (:1517-1559) map GROUP/NEST/JOIN begin/end to `push_group/push_nest/
push_join`/`pop_*` (SPACING skipped, :1492-1494/:1536-1538), invoked from
`gen_alternative_unparser` at :1602 and :1656.

Design now adds §2.2 "Item-level anchor operations" bullet (lines 202-216) mapping both
helpers to `acc.push_group()/push_nest(indent)/push_join(sep)` and `pop_*`, noting they are
accumulator state transitions (not Doc results) and that the push_join separator inherits the
design-2 rejection; §2.6 fixture (lines 330-335) now requires at least one item-level
(label-/literal-anchored) range op so the parity test exercises this path. Matches the
reviewer's suggested fix exactly.
Assessment: gap closed in both the spec and the fixture. Accept.

## Approved

3 findings: 3 Fixed verified (design-1 contradiction resolved + divergence requirements-
consistent; design-2 exact-domain parity restored; design-3 item-level mapping + fixture
coverage added).

---

## Verdict: APPROVED

All three dispositions acceptable. Fixes are reviewer-aligned and grounded in source
(`gsm2unparser.py`, `fmt_config.py`) and requirements (rendered-string parity is the stated
cross-backend contract; the declared Python-surface divergences are deliberate and
requirements-consistent, not incidental).
