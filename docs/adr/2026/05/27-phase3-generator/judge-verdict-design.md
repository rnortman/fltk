# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/05/27-phase3-generator/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 5 findings.

**Note**: No `dispositions-design.md` file exists. The design document itself addresses all five reviewer findings inline — the design was written (or revised) to incorporate the reviewer's feedback. Judging the design text as the de facto response.

## Other findings walk

### design-1 — Fixed (implicit; addressed in design text)
Claim: `add_submodule` does not register in `sys.modules`; `from fltk._native.fegen_cst import X` raises `ModuleNotFoundError`. Consequence: AC-7/AC-8 tests fail at import.
Design lines 294-303: The `lib.rs` code block includes explicit `sys.modules` insertion (`sys.getattr("modules")?.set_item("fltk._native.fegen_cst", &fegen_sub)?`). Lines 310-311 explain the rationale. This is the reviewer's suggested fix (b).
Assessment: Fix addresses the consequence directly. Accept.

### design-2 — Fixed (implicit; addressed in design text)
Claim: `capture_trivia` value inconsistent between design body (omitted/`False`) and exploration (`True`). Consequence: Low — no functional breakage; risk of implementer confusion.
Design line 78: Explicitly states the divergence and explains why `capture_trivia` is irrelevant, citing `gsm.py:380`, `classify_trivia_rules`, and `CstGenerator.__init__`. This matches the reviewer's suggested fix (one sentence noting supersession).
Assessment: Fix addresses the consequence. Accept.

### design-3 — Fixed (implicit; addressed in design text)
Claim: Minimal-grammar fixture path imprecise (implied `tests/` but file is under `fltk/fegen/`); test file placement splits generator tests. Consequence: Low — minor implementer confusion.
Design line 380: Correctly cites `fltk/fegen/test_regression_empty_nary.py`. Design line 370: Explicit placement rationale for `tests/` (groups all Phase 3 test files together; Rust-extension tests convention). This matches the reviewer's suggested fix (correct citation + deliberate placement decision).
Assessment: Fix addresses the consequence. Accept.

### design-4 — Fixed (implicit; addressed in design text)
Claim: `#[classattr] Label` / `type_object(py)` unverified for submodule-registered classes. Consequence: Low-to-medium; bounded by AC-8 smoke test.
Design lines 353-354: Explicitly marked as an **Assumption** (not assertion), with the AC-8 smoke test (`test_label_access`) named as the validation mechanism. This matches the reviewer's suggested fix (downgrade from assertion to expectation).
Assessment: Fix addresses the consequence. Accept.

### design-5 — Fixed (implicit; addressed in design text)
Claim: "Open Questions: None" hides unresolved integration detail (design-1's sys.modules gap). Consequence: Low (subsumes design-1).
Design lines 406-408: Open Questions section is no longer "None." It contains a genuine open question (OQ-empty-label-enum vs requirements). The design-1 sys.modules issue is resolved outright in the design (lines 298-303), so it does not need to remain open. The remaining OQ is a legitimate requirements-design conflict: requirements line 122-123 say "still emits a node struct with an empty label enum (zero variants)," but Rust cannot have zero-variant enums; the design omits the enum (lines 244-249) and notes the requirements should be updated.
Assessment: Fix addresses the consequence. The OQ section now surfaces the one genuine unresolved item. Accept.

## Approved

5 findings: 5 addressed in design text, all verified.

---

## Verdict: APPROVED
