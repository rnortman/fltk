# Judge verdict — prepass

Phase: prepass. Base 90ffae8..HEAD bb96d0e. Round 1.
Notes: 2 reviewer files (slop, scope); 4 findings (all slop), scope reports none.

## Added TODOs walk

No TODOs added in this increment (`git diff` for `^\+.*TODO` is empty). Nothing to score.

## Other findings walk

All four findings are slop (LLM-tell) cosmetic items: design-document cross-references (`design §N`, `OQ-N`, `user answer "…"`) embedded in docstrings/comments that mean nothing to an out-of-repo reader. All dispositioned Fixed.

### slop-1 — Fixed
Claim: `generate_pyi` docstring (`gsm2unparser_rs.py`) is 25+ lines of design-rationale with `OQ-3` / `§2.4` / `§2.3` / `user answer "Yes, emit .pyi"` breadcrumbs burying the method contract; consequence is a docstring that reads like an implementation diary and points to inaccessible refs.
Evidence: `generate_pyi` is added in this increment (diff lines 119-171, all `+`). The committed docstring describes the contract only — what `protocol_module` is (import path of the CST protocol module, aliased `_proto`), what the returned `.pyi` describes (the `Unparser`/`Doc` Python surface), and that it is pure-Python and extension-independent. No `design §`, `OQ-`, or `user answer` phrase present (grep of HEAD file: NONE).
Assessment: fix addresses the consequence; contract retained, breadcrumbs gone. Accept.

### slop-2 — Fixed
Claim: `_gen_python_bindings` docstring contains `user answer "Please expose the intermediate Doc"` and `design OQ-2` — conversation transcript where a spec belongs; consequence is the same diary-prose noise.
Evidence: diff lines 287-313 show the `(design §2.3)` and `(design §2.3/§2.4 …)` parentheticals stripped from the existing prose, and the newly added additive-`_doc` paragraph reads "Additively, each rule also gets `unparse_{rule}_doc` …" with no `OQ-2` / `user answer` attribution. Behavioral rationale (full-pipeline string method, additive `_doc`, `unsendable` because core `Doc` uses `Rc`) preserved. Grep of HEAD file: NONE.
Assessment: fix matches the comment; technical content kept. Accept.

### slop-3 — Fixed
Claim: `gen_rust_unparser` docstring (`genparser.py`) carries `(design OQ-3)` in the Typer `--help` text, surfacing a meaningless parenthetical in CLI `--help`.
Evidence: diff lines 44-46 — the added `.pyi`-stub sentence reads "also emits a .pyi stub describing the Unparser/Doc Python surface so downstream code is type-checked; use --pyi-output to control the exact path." No `(design OQ-3)`. Grep of HEAD file: NONE.
Assessment: parenthetical removed, sentence reads correctly. Accept.

### slop-4 — Fixed
Claim: four test-body comments in `test_rust_unparser_generator.py` reference `§2.1` / `§2.4` / `OQ-2`, explaining decision history rather than what the assertion checks.
Evidence: diff confirms each cited comment rewritten to the inline testable reason — `unsendable … single-threaded` (no `§2.1`, lines 474-477); fully-qualified-path comment tightened (lines 480-481); `purely additive` (no `§2.4`, line 533); `An inspection affordance for callers` (no `OQ-2`, line 507). Grep of HEAD file: NONE.
Assessment: design refs replaced with the assertion's own reason; signal restored. Accept.

### Consistency-sweep claim — verified
The dispositions claim every `design §N` / `OQ-N` / `user answer X` occurrence across all three files (beyond the four cited spots) was stripped in the same commit, while durable source-location refs (`gsm2unparser.py:267`, `gsm2tree.py:630`, etc.) and `deep-r1` notes were left intact.
Evidence: grep of all three files at HEAD for `design §|OQ-[0-9]|user answer|§2.|§3|§4` returns NONE in each. Diff confirms durable refs preserved (e.g. `gsm2tree.py:630` at line 237, `gsm2unparser.py:267` at lines 232/428, `:846`/`:971` retained). The responder correctly distinguished transient design-doc refs from durable code refs — no over-stripping.

## Approved

4 findings: 4 Fixed verified (all cosmetic slop). Scope reviewer: no findings.

---

## Verdict: APPROVED

All four slop dispositions are sound — breadcrumbs removed, technical/contract content preserved, durable source refs untouched, and the broader sweep claim holds against the HEAD files. No added TODOs. Scope clean.
