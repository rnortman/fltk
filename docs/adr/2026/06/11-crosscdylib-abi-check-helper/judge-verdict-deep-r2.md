# Judge verdict — deep review, round 2

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 1963894..HEAD 5cbead2 (rework commit 466df05; 5cbead2 is the dispositions update). Round 2 — APPROVED or ESCALATE only.
Scope: the two items disputed in round 1 (`judge-verdict-deep.md`): security-1 (incomplete) and reuse-1 (TODO failed rubric Q2). The 10 findings approved in round 1 are not re-walked; the rework diff (7841378..5cbead2) touches only `cross_cdylib.rs`, `TODO.md`, and the dispositions doc — no round-1-approved fix was disturbed.

## Added TODOs walk

### reuse-1 — TODO(crosscdylib-helper-consolidation), formerly at cross_cdylib.rs:116
Round 1 ruled the TODO failed rubric Q2 (mechanical, module-private, no design input) and offered: (a) consolidate now, or (b) delete TODO + Won't-Do. Responder chose (a).
Code at HEAD: `py_type_name` and `py_attr_type_name` (byte-identical bodies modulo fallback string) merged into `py_any_type_name` (cross_cdylib.rs:141–148). Call sites updated: `extract_span` at line 353; `check_abi_pair` steps 2 and 6 at lines 206, 239. `py_type_obj_name` retained (line 156) — different input type (`&Bound<PyType>`) and name method (`fully_qualified_name()`); the design §2 documents why the two name forms must coexist, so retaining it is correct, not evasion. TODO comment deleted (diff confirms); `TODO.md` carries only the unrelated `crosscdylib-abi-size-probe` slug; `git grep crosscdylib-helper-consolidation` outside the ADR dir: no hits. Fallback string unified to `"<unknown type>"` — failure-path-only message delta, acceptable.
Assessment: resolution (a) executed in full. TODO no longer exists. Accept.

## Other findings walk

### security-1 — Fixed
Round 1 dispute: the errhandling-1/2 rework added four unescaped attacker-influenced `{e}` interpolations (`"; getattr raised: {e}"` steps 1/5, `"; extract raised: {e}"` steps 2/6), leaving the finding's consequence (control chars reaching error templates) open at HEAD.
Code at HEAD: all four sites now render via `escape_control_chars_for_msg(&e.to_string())` — step 1 at cross_cdylib.rs:197, step 2 at 207, step 5 at 230, step 6 at 240. The diff 7841378..5cbead2 shows exactly these four substitutions. This is the remediation the round-1 verdict specified verbatim. Remaining template interpolations: `{subject}` via the escaping name helpers (round 1 verified), `{s:?}` at step 3 (Rust `Debug` for `str` escapes control chars), numeric `{reported_layout}`/`{expected_layout}` (not strings). The unescaped `{e}` at span_to_pyobject:299 and the import-failure paths (lines 375, 408) render errors from the canonical `fltk._native` lookup, not from an attacker-supplied class — outside security-1's stated trust boundary (crafted class reaching the validation entry point) and pre-existing pattern, not part of the finding.
Compile check: `cargo check -p fltk-cst-core` clean at HEAD. Test assertions from test-1/test-2 pin substrings (`"not str"`, `"not int"`, the prefix) that survive the appended escaped suffix.
Assessment: finding's consequence closed at HEAD. Accept.

## Disputed items

None. Both round-1 disputes resolved as specified.

## Approved

12 findings: 8 Fixed verified (errhandling-1, errhandling-2, errhandling-5, errhandling-6, security-1, test-1, test-2, efficiency-1), 3 Won't-Do sound (errhandling-3, errhandling-4, test-3), 1 reuse consolidation done (reuse-1, TODO withdrawn and work performed).

---

## Verdict: APPROVED

Both round-1 reworks verified against code at HEAD 5cbead2. No dispositions remain in dispute.
