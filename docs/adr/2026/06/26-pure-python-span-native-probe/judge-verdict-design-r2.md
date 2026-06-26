# Judge verdict — design review (r2)

Phase: design. Doc: `./design.md`. Base commit `49e9701`. Round 1.
Notes: 1 reviewer file; 2 findings (design-1, design-2), both dispositioned Fixed.

## Other findings walk

### design-1 — Fixed
Claim: §4.1's literal instruction for `tests/test_clean_protocol_consumer_api.py` would delete
`TestCrossBackendDualShapeDispatch` by dependency — `_rust_cst_grammar` (`:160-168`) is the data
source for the `rust_items` fixture (`:580-583`) feeding that class (`:566`). Consequence: loss of
the only coverage of consumer-side cross-backend dispatch agnosticism (Shape 1 / Shape 2 producing
identical output on a Python vs Rust CST) — a property CLAUDE.md and `requirements.md` name a hard
constraint. Reviewer's remedy: RETARGET `_rust_cst_grammar` to the genuine config-2 parser, don't
delete.

Disposition: Fixed — §4.1 rewrote the file's bullet into two sub-bullets; `_rust_cst_grammar`
RETARGETed to `fegen_rust_cst.parser.Parser(grammar_text, capture_trivia=False)` →
`apply__parse_grammar(0)` → `result.result`; `test_fltk2gsm_behavioral_equivalence` (`:360`)
removed; new §4 test-plan bullet added; §4.1 intro broadened.

Evidence (design.md §4.1 lines 336-359 + §4 lines 301-308):
- Data-source chain verified: `_rust_cst_grammar` (`:160-168`) is called by the `rust_items`
  fixture (`:582`), which feeds the five `TestCrossBackendDualShapeDispatch` tests consuming
  `rust_items` (`:639,650,664,670,676`). The finding's dependency claim is accurate.
- Retarget API verified against ground truth: `TestRustParserSelfHosting`
  (test_phase4_fegen_rust_backend.py:252-263) drives exactly
  `fegen_rust_cst.parser.Parser(text, capture_trivia=False)` → `apply__parse_grammar(0)`, with
  `result.result` asserted `isinstance fegen_rust_cst.cst.Grammar`. The cited API exists and
  produces genuine Rust CST nodes; `_get_first_items_node`'s accessors (`children_rule`,
  `child_alternatives().children_items()`) operate on the same `fegen_rust_cst.cst.*` classes the
  hybrid produced.
- Span-kind survival verified: design notes genuine-Rust separator spans become `fltk._native.Span`
  (vs hybrid's `terminalsrc.Span`) and that `test_span_kind_narrows_rust_backend_span_children`
  (`:676`) still holds because `.kind` is shared. Confirmed: `RustSpan(1,5).kind is SpanKind.SPAN`
  (`:773-778`) and `_fltk_canonical_name == "SpanKind.SPAN"` (`:763-771`); the test asserts exactly
  those (`:686,692`), and `case proto_cst.Span.kind` dispatch matches native spans
  (`:696-701,703-723`). Docstring-update instruction is the correct and sufficient follow-up.
- Removed `test_fltk2gsm_behavioral_equivalence` (`:354-361`, Python-vs-Rust GSM equality) — its
  property is genuinely covered by the kept `TestRustParserSelfHosting.test_fegen_grammar_self_hosted`
  (`:273-281`), which self-hosts `fegen.fltkg` through the Rust parser → Rust CST → real Cst2Gsm and
  asserts `gsm_rust == gsm_python` (`:261-263`). No agnosticism coverage lost.

Assessment: finding is legitimate (real consequence on a central requirement); fix is present in the
design and technically sound against source. The retarget is feasible (`fegen_rust_cst` already
imported tentatively `:45-51`; class already `@_FEGEN_RUST_CST_SKIP`-gated `:565`), preserves every
dispatch assertion, and the removed test loses nothing. Accept.

### design-2 — Fixed
Claim: §2.3 enumerated the dead symbols to delete but omitted `_fegen_grammar_cache`
(plumbing.py:38). Consequence: after `_load_fegen_grammar` is deleted, it is orphaned module-level
state; ruff's unused-binding rules (F841) do not cover module-level globals, so `make check` would
not catch it — silent cruft contradicting §2.3's own "delete the now-dead support code" intent.

Disposition: Fixed — added `_fegen_grammar_cache` (`:38`) to the §2.3 deletion list with the
ruff-doesn't-flag-globals note.

Evidence: design.md §2.3 (lines 204-211) now lists `_fegen_grammar_cache` (`:38`) alongside
`_load_rust_cst_classes`, `RustBackendUnavailableError`, `_fegen_rust_parser_cache`, and
`_load_fegen_grammar`, and states it is "referenced only inside `_load_fegen_grammar` (`:53,66,67`)"
with the F841-doesn't-cover-globals rationale. Ground truth (plumbing.py): `_fegen_grammar_cache` is
defined at `:38`; its only references are `:53` (`if not _fegen_grammar_cache`), `:66` (`.append`),
`:67` (`return ...[0]`) — all inside `_load_fegen_grammar` (`:47-67`). The cited line numbers and
the orphaning claim are exact.

Assessment: finding is legitimate (low blast radius but real, ruff-invisible); fix is present and the
deletion-list line references match source precisely. Accept.

## Approved

2 findings: 2 Fixed verified (design-1, design-2). No disputed items.

---

## Verdict: APPROVED

Both findings are legitimate and both Fixed dispositions are present in the design and verified
sound against source. No disposition is wrong; nothing disputed.
