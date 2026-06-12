# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 1963894..HEAD 7841378. Round 1.
Notes: 7 reviewer files (correctness and quality: no findings); 12 findings total.
Dispositions cite ad58891; HEAD 7841378 adds the reuse-1 TODO comment + TODO.md entry on top. Judged at HEAD.

## Added TODOs walk

### reuse-1 — TODO(crosscdylib-helper-consolidation) at cross_cdylib.rs:116
Q1 (worth doing): weak yes — `py_type_name` (cross_cdylib.rs:144) and `py_attr_type_name` (cross_cdylib.rs:170) have byte-identical bodies modulo fallback string (`"<unknown type>"` vs `"<unknown>"`); `py_type_obj_name` differs only in input type and name method. Some consolidation value exists, though the reviewer's own note says "No action required if the module stays this size."
Q2 (design/owner input required): no — three module-private helpers, two call-site categories, mechanical refactor. No API surface, no design tradeoff, no owner input.
Furthermore: this iteration added the third helper (`py_type_obj_name`), worsening the duplication it defers — per rubric, a problem this iteration worsened cannot be silently deferred.
Also: the TODO body ("Consolidate if a fourth variant is needed") is a conditional tripwire, not concrete work with an obvious "done" — violates the project TODO convention (CLAUDE.md: "every TODO should describe a concrete thing that needs to happen, in a place where 'done' is obvious").
Assessment: Q2 fails → TODO is the wrong disposition. Acceptable resolutions: (a) do it now — fold the two identical-body helpers (and optionally the third), or (b) delete the TODO comment + TODO.md entry and disposition reuse-1 as Won't-Do per the reviewer's own "no action required" close. Either is fine; deferring via TODO is not.

## Other findings walk

### errhandling-1 — Fixed
Claim: `map_err(|_|` at steps 1 and 5 of `check_abi_pair` swallows non-AttributeError exceptions from raising `__getattr__`; consequence is misdiagnosis ("no marker" reported when the real cause was an unrelated exception).
Code at HEAD: both getattrs use `map_err(|e| ...)` appending `"; getattr raised: {e}"` (cross_cdylib.rs:203–213, 235–244). This is the reviewer's stated minimal fix, verbatim.
Assessment: addresses the finding. Accept. (Escaping interaction with security-1 adjudicated under security-1.)

### errhandling-2 — Fixed
Claim: `map_err(|_|` on both `extract` calls drops the original extraction error.
Code at HEAD: `map_err(|e| ...)` appending `"; extract raised: {e}"` at steps 2 and 6 (cross_cdylib.rs:215–222, 246–253).
Assessment: matches the reviewer's minimal fix. Accept.

### errhandling-3 — Won't-Do
Reviewer self-retracted in the notes ("Retracted — not a finding. `get_or_init` is infallible"). Verified: `get_or_init` returns `&T`, not `Result`; `let _ =` at cross_cdylib.rs:97 is correct.
Assessment: accept.

### errhandling-4 — Won't-Do
Reviewer marked no finding ("This is correct — the original error is included"). Verified at cross_cdylib.rs:380–388: `format!("... {e}")` preserves the import error.
Assessment: accept.

### errhandling-5 — Fixed
Claim: `get_source_text_type` returns an unvalidated type with no documented safety-contract gap.
Code at HEAD: "# Safety contract gap" doc section at cross_cdylib.rs:407–410, stating the returned type is NOT ABI-validated and forbidding `downcast_unchecked` without a separate `check_abi_pair`. Matches the reviewer's requested wording in substance.
Assessment: accept.

### errhandling-6 — Fixed
Claim: bare AttributeError from the `_with_source_unchecked` getattr lacks context.
Code at HEAD: `map_err` wrapping in `PyRuntimeError` naming `fltk._native.Span._with_source_unchecked` (cross_cdylib.rs:308–312). Exactly the suggested fix.
Assessment: accept.

### security-1 — Fixed (disputed)
Claim: attacker-influenced type identity (`__module__`/`__qualname__` via `fully_qualified_name()`, plus the same exposure in `py_type_name`/`py_attr_type_name`) flows unescaped into six error templates; consequence is log injection / terminal escape-sequence injection.
Code at HEAD: `escape_control_chars_for_msg` (cross_cdylib.rs:126–141) applied inside all three name helpers (lines 150, 164, 176). The suggested fix is implemented as specified.
However, the same commit (ad58891, the errhandling-1/2 fix) added four new unescaped attacker-influenced interpolations into the same templates: `"; getattr raised: {e}"` (steps 1, 5) and `"; extract raised: {e}"` (steps 2, 6). `PyErr` Display embeds the Python exception message verbatim:
- A raising metaclass `__getattr__` puts a fully attacker-chosen message into `{e}` — the exact entry point security-1 names ("raising metaclass `__getattr__`" appears in the security notes' gate-equivalence section).
- The ordinary missing-attr AttributeError message embeds the type's `__name__` ("type object 'NAME' has no attribute ..."), and `type("x\x1b[2J...", (), {})` permits control characters in `NAME`.
- Extract-failure TypeErrors embed the attr value's type name similarly.
So the finding's stated consequence — control characters reaching the error templates from attacker-influenced strings — persists at HEAD through a channel this iteration's own rework created. The disposition's claim ("Attacker-influenced ... strings are sanitized before appearing in any error template") is contradicted by code. (Template 3's `{s:?}` is fine: Rust `Debug` for `str` escapes control characters.)
Assessment: incomplete. Need: escape the `{e}` rendering at the four sites, e.g. `escape_control_chars_for_msg(&e.to_string())`, or escape the assembled message once per template.

### test-1 — Fixed
Claim: `test_with_source_unchecked_non_str_marker_raises_type_error` pinned only the attribute name, not the unified template.
Code at HEAD: test_rust_span.py:328–342 — `match="SourceText ABI mismatch"` plus assertions on `"_fltk_cst_core_abi"` and `"not str"`.
Assessment: pins template 2 as requested. Accept.

### test-2 — Fixed
Claim: Span-path templates 2 and 5 had no subprocess coverage.
Code at HEAD: `test_non_str_abi_marker_raises_type_error` (test_rust_span.py:648–686, patches marker to `42`, asserts `"Span ABI mismatch"` + `"not str"`) and `test_non_int_abi_layout_raises_type_error` (test_rust_span.py:688–726, patches layout to `"oops"`, asserts `"Span ABI mismatch"` + `"not int"`). Both follow the existing subprocess pattern.
Assessment: exactly the two requested tests. Accept.

### test-3 — Won't-Do
Reviewer's own note: "No fix needed" — substring assertion is intentionally loose and sufficient per design §2.
Assessment: not a finding. Accept.

### efficiency-1 — Fixed
Claim: `subject` computed eagerly (`fully_qualified_name()` Python call + String alloc) on every slow-path validation including success.
Code at HEAD: `check_abi_pair` takes `subject_fn: impl Fn() -> String` (cross_cdylib.rs:193–197); `subject_fn()` is invoked only inside the seven error arms (lines 206, 216, 225, 238, 247, 256). SourceText call site passes `|| py_type_obj_name(&obj_type)` (line 93); Span site passes `|| "fltk._native.Span".to_string()` (line 389).
Assessment: work moved to error-path-only as requested; success path allocates nothing. Accept.

## Disputed items

- **security-1**: escape the four `{e}` interpolations (`"; getattr raised: {e}"` at cross_cdylib.rs:211, 242; `"; extract raised: {e}"` at lines 219, 249) — e.g. `escape_control_chars_for_msg(&e.to_string())` — so the finding's consequence is closed at HEAD, not just at the three name helpers.
- **reuse-1 / TODO(crosscdylib-helper-consolidation)**: fails rubric Q2 (mechanical, module-private, no design or owner input needed) and the duplication was worsened by this iteration. Either consolidate now (the two identical-body helpers at minimum) or delete the TODO comment + TODO.md entry and close reuse-1 as Won't-Do per the reviewer's "no action required."

## Approved

10 findings: 7 Fixed verified (errhandling-1, errhandling-2, errhandling-5, errhandling-6, test-1, test-2, efficiency-1), 3 Won't-Do sound (errhandling-3, errhandling-4, test-3).

---

## Verdict: REWORK

Two dispositions wrong (security-1 incomplete; reuse-1 TODO fails rubric Q2). Round 1.
