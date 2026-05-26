# Judge verdict — design review

Phase: design. Doc: `README.md` (PyO3 CST Phased Project Plan). Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 7 findings + coverage check.

## Other findings walk

### design-1 — Fixed
Claim: Committed `fltk.fltkg` is broken (undefined `rule_options`, extra rules); "13 rules" count wrong; Phases 3/4 impossible without a grammar-baseline fix. Consequence: plan assumes a clean regenerate-and-compare baseline that does not exist.
Disposition: "No change needed" + rule-count correction.
Evidence: Design line 21 contains a "Prerequisite — grammar round-trip" subsection in Phase 0, describing the broken grammar, requiring revert-or-fix, and adding a regression test. Phase 3 (line 105) now reads "currently 14 classes in `fltk_cst.py`" and notes dependency on Phase 0 reconciliation. The responder's "no change needed" framing is misleading (they did change the count), but the substance is correct: Phase 0 already addressed the prerequisite concern, and the count is now fixed.
Assessment: Fix addresses the consequence. Accept.

### design-2 — Fixed
Claim: "Bootstrap pipeline is independent and unaffected" is false — `bootstrap_cst.py` shares `terminalsrc.Span`, so Phase 1 affects it. Consequence: plan understates Phase 1 blast radius.
Disposition: "No change needed" — design already has the correct wording.
Evidence: Design line 11 reads: "The bootstrap pipeline (`bootstrap_cst.py`) is independent of the *generated* CST classes but shares `terminalsrc.Span`, so Phase 1 affects it; the full test suite covers bootstrap and is the safety net." This matches the reviewer's suggested fix verbatim.
Assessment: Design already had the correct statement. Accept.

### design-3 — Fixed
Claim: Phase 1 says "`#[new]` accepting keyword args" only, but `terminalsrc.py` and tests use positional construction. Consequence: if Rust `#[new]` is keyword-only, every parse fails.
Disposition: Changed to "both positional and keyword args"; added acceptance criteria.
Evidence: Design line 43: "accepting both positional and keyword args (positional construction is used on the hot path in `terminalsrc.consume_literal`/`consume_regex` and throughout `bootstrap_parser.py`)". Done-when (line 52): "Positional (`Span(1, 2)`) and keyword (`Span(start=1, end=2)`) construction both work."
Assessment: Fix addresses the consequence at both the spec and acceptance-criteria level. Accept.

### design-4 — Fixed
Claim: (a) 40 construction sites should be 80. (b) Formatter pipeline CST modules (`unparsefmt_cst.py`, `toy_cst.py`) omitted from Phase 4.
Disposition: (a) Corrected to 80. (b) Added formatter pipeline to Phase 4.
Evidence: Design line 46: "80 construction sites in `fltk_parser.py`". Phase 4 line 135: "The formatter pipeline's static CST modules (`unparsefmt_cst.py`, `toy_cst.py` and their consumers — see Context) follow the same generated-CST pattern and share `terminalsrc.Span`; validated by the full test suite."
Assessment: Both corrections verified in the design text. Accept.

### design-5 — Fixed
Claim: Line references for `gsm2unparser.py` are off (1882 → range, 303-308, and exploration's line 983 claim is wrong).
Disposition: Updated to ranges. Correctly notes line 983 was in exploration doc, not the design.
Evidence: Design line 13: "gsm2unparser.py:1876-1892". Risk R1 (line 216): "gsm2unparser.py:302-308". No line 983 reference in the design.
Assessment: References corrected. The 983 issue is out of scope (exploration doc, not design). Accept.

### design-6 — Fixed
Claim: Phase 5 sub-option 5C presented at equal depth despite being recommended against. Consequence: invites premature design of an unlikely path.
Disposition: Compressed to one line.
Evidence: Design line 171: "**5C: Runtime Rust compilation.** Rejected — requires Rust toolchain on every end-user's machine for a currently pure-Python library; fragile and high-latency." Single line, no longer co-equal with 5A/5B.
Assessment: Fix matches the reviewer's suggestion and the plan's own recommendation. Accept.

### design-7 — Fixed
Claim: Phase 3 "reuse `CstGenerator.model_for_rule`" understates coupling — reuse requires instantiating `CstGenerator` and consuming `rule_models`; `__init__` eagerly populates state.
Disposition: Replaced with explicit instantiation/subclassing note.
Evidence: Design line 99: "Reuse the analysis logic by instantiating (or subclassing) `CstGenerator` and consuming its `rule_models` dict (note: `CstGenerator.__init__` eagerly populates `rule_models` and registers IIR types via `self.context.python_type_registry`; `py_module` drives annotation paths)."
Assessment: Fix makes the coupling explicit. Accept.

### Coverage check gaps (no finding ID)
The reviewer noted two gaps: (1) dynamic module registration lacks a dedicated PoC, and (2) no phase validates the formatter pipeline. The design addresses (1) at line 9 by scoping dynamic module registration to Phase 5B only ("under the recommended 5A path... no new registration is needed"), making a dedicated PoC unnecessary under the recommended path. Gap (2) is addressed by design-4's fix (line 135). Neither gap remains actionable.

## Approved

7 findings: 7 Fixed verified.

---

## Verdict: APPROVED
