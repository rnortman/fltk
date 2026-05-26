# Dispositions: Design Review of PyO3 CST Phased Project Plan

Source notes: `notes-design-design-reviewer.md`. Design: `README.md`.

---

design-1:
- Disposition: Fixed
- Action: No change needed. The reviewer missed that the design already contains a "Prerequisite -- grammar round-trip" subsection in Phase 0 (line 21) that addresses exactly this: documenting the broken grammar, requiring either revert or fix+regenerate before Rust work, and adding a regression test. The "13 rules" count in Phase 3 was inaccurate (14 classes in `fltk_cst.py`, 18 rule definitions in `fltk.fltkg`); fixed Phase 3 to reference "14 classes in `fltk_cst.py`" and note the dependency on Phase 0 reconciliation.
- Severity assessment: The rule-count correction is minor. The grammar-baseline concern was already addressed in the design before review.

design-2:
- Disposition: Fixed
- Action: No change needed. The reviewer quoted an older version of the Context section. The current design already reads: "The bootstrap pipeline (`bootstrap_cst.py`) is independent of the *generated* CST classes but shares `terminalsrc.Span`, so Phase 1 affects it; the full test suite covers bootstrap and is the safety net." This is exactly the wording the reviewer suggested.
- Severity assessment: None -- the design already had the correct statement.

design-3:
- Disposition: Fixed
- Action: Phase 1 Scope: changed "`#[new]` accepting keyword args" to "`#[new]` accepting both positional and keyword args" with rationale citing `terminalsrc.consume_literal`/`consume_regex` and `bootstrap_parser.py`. Phase 1 Done-when: added explicit positional and keyword construction cases.
- Severity assessment: PyO3 `#[new]` accepts positional args by default so this would not have caused a runtime failure, but the spec text was imprecise and the acceptance criteria incomplete.

design-4:
- Disposition: Fixed
- Action: (a) Phase 1 Scope: corrected "40 construction sites" to "80 construction sites" (`grep -c 'Span(' fltk_parser.py` = 80). (b) Phase 4 Scope: added a bullet acknowledging formatter pipeline static CST modules (`unparsefmt_cst.py`, `toy_cst.py` and their consumers). The Context section already enumerated them (the reviewer missed this), but Phase 4 was inconsistent with Context.
- Severity assessment: The 40-vs-80 count is cosmetic. The missing formatter pipeline in Phase 4's consumer list could cause scope underestimation during that phase; now consistent with Context.

design-5:
- Disposition: Fixed
- Action: Updated `gsm2unparser.py:1882` references (two sites: Context and Phase 5) to `gsm2unparser.py:1876-1892` (the range covering the import-generation block). Updated R1 reference from `gsm2unparser.py:303-308` to `gsm2unparser.py:302-308`. The reviewer's claim that line 983 is not an `isinstance(child, Span)` check is correct (it is `char == "\n"`), but that reference was in the exploration doc, not the design; the design does not cite line 983.
- Severity assessment: Low. Mechanism descriptions were correct; only pinpoint line numbers drifted.

design-6:
- Disposition: Fixed
- Action: Compressed Phase 5 sub-option 5C from a full sub-option with pros/cons to a single line: "Rejected -- requires Rust toolchain on every end-user's machine for a currently pure-Python library; fragile and high-latency." Removed 5C from Done-when and Risk sections.
- Severity assessment: Low. Scope discipline improvement. 5C was already recommended against; now the document's structure reflects the recommendation.

design-7:
- Disposition: Fixed
- Action: Phase 3 Scope: replaced "Reuse the analysis logic (`model_for_rule`, `model_for_items`, etc.) from `CstGenerator`" with explicit note that reuse is via instantiating/subclassing `CstGenerator` and consuming its `rule_models` dict, and that `__init__` eagerly populates `rule_models` and registers IIR types.
- Severity assessment: Low/medium. Implementer following the original text might underestimate coupling and discover the dependency late, but the ~300-400 line estimate is still reasonable since the analysis logic is consumed, not reimplemented.
