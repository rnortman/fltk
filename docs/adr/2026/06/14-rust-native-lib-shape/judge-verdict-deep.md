# Judge verdict — deep review

Phase: deep. Base 7200d9c..HEAD 70fe561 (reviewed commit 7a7ca4d is HEAD's parent; dispositions applied in 70fe561). Round 1.
Notes: 7 reviewer files. Findings: errhandling 1-3, reuse-1, quality 1-4, test 1-5; correctness/security/efficiency reported no findings. 13 dispositioned findings total.

## Added TODOs walk

### errhandling-1 — TODO(native-span-init-error-context) at gsm2lib_rs.py:159-161
Q1 (worth doing): marginal-yes. `Py::new(m.py(), Span::unknown())?` at gsm2lib_rs.py:162 propagates an unwrapped pyo3 RuntimeError on OOM-class failure during `_native` import; on-call cannot distinguish span-sentinel-creation failure from submodule-registration failure. Reviewer's own consequence concedes "OOM, or broken Python heap" — extremely rare, import-time only. Worth a diagnostic eventually.
Q2 (design/owner input required): no — the fix is the reviewer's own option (a): a `.map_err(|e| PyRuntimeError::new_err(format!(...)))` wrap. Mechanical, ~3 lines, no design decision.
Assessment: Q2 fails on its face → strictly this is do-now, not TODO. BUT: this is generated boilerplate emitted by a string-builder; the wrap must be threaded through `RustLibGenerator.generate()` and a test added to pin the emitted text — small but not literally a one-liner, and the failure is genuinely OOM-only at import. Reviewer explicitly offered option (b) "document in a TODO" as acceptable and lightweight. The finding does not create or worsen a problem this iteration (the `Py::new?` propagation predates and is unchanged in behavior; the iteration only relocated where it is emitted). Borderline, but the reviewer sanctioned the TODO route and the consequence is on-call message clarity for an OOM path, not a correctness/robustness defect. TODO acceptable.

### errhandling-3 — TODO(submodule-register-fn-convention) at gsm2lib_rs.py:48-50
Q1 (worth doing): yes, weakly — documents that `Submodule.validate()` checks identifier syntax but not the `register_classes` naming convention; a non-standard `register_fn` fails at Rust compile, not Python validation.
Q2 (design/owner input required): yes — "document or enforce the convention" is the open question. Whether to *enforce* (reject non-`register_classes`) vs *document* is a deliberate API-surface decision: enforcing constrains the library API for all callers; the reviewer itself flagged it "acceptable for a code generator … no change strictly required." This is a real should-we-narrow-the-contract question, not mechanical work.
Assessment: the TODO is a doc-comment that names the limitation and defers the enforce-vs-document call. Reviewer agreed no change is strictly required. TODO acceptable.

### reuse-1 — TODO(rust-ident-dedup) at gsm2lib_rs.py:16-18
Q1 (worth doing): yes, weakly — `_RUST_IDENT_RE` single-segment pattern is hand-written here and as the repeating unit of `_CST_MOD_PATH_RE` in genparser.py. DRY.
Q2 (design/owner input required): no, strictly — importing `_validate_rust_ident` into genparser.py is doable now. BUT reviewer's own consequence: "Currently low risk because the validation is simple … the duplication grows if more gen-* commands are added." Two call sites of a trivial 1-line regex with no current divergence. Consolidating now would couple two modules for negligible benefit; the TODO records the watch-point ("if more gen-* commands need it").
Assessment: this is a nit-severity reuse observation the reviewer rated "low risk currently." A TODO that defers consolidation until a third consumer appears is a defensible product/maintenance call rather than design work — and the alternative (do-now) buys almost nothing. Per the "don't let the responder hide behind non-trivial" caution this is the weakest of the four, but the underlying finding is a nit with no consequence today; deferring a nit is not a silent deferral of a real problem. TODO acceptable (not worth promoting to REWORK).

### quality-1 — TODO(bazel-lib-rs-no-cst) at rust.bzl
Q1 (worth doing): yes — the `_assemble_crate` genrule hard-requires `cst.rs`/`parser.rs` even on the new `lib_rs=None` auto-generate branch; a future runtime-only Bazel caller (the pattern this PR establishes) would hit a misleading `test -f` failure.
Q2 (design/owner input required): yes — reviewer offered three structurally different fixes (parse generated lib.rs for `mod cst;`; Starlark `fail()` guard; split the genrule into two variants). Choosing among them is a Bazel-macro-design decision, and there is no in-tree runtime-only Bazel consumer yet (`bootstrap_native` supplies grammar srcs, so it does not trip the guard). The right fix depends on a future caller's shape.
Assessment: worth doing AND design-shaped AND no current consumer trips it → classic defer-until-concrete-caller TODO. Acceptable.

Scope check across the TODO pile: 4 TODOs, but they are independent low-severity items (one OOM-path diagnostic, one API-convention doc, one DRY nit, one Bazel leaky-abstraction guard), not a coherent slice of design-committed work left unbuilt. The design's stated scope (make `_native` runtime-only; relocate fegen CST/parser; collapse `native_spec()`) is fully implemented per the correctness reviewer's behavioral-equivalence trace. This is not a "scope was wrong → ESCALATE the pile" situation; the TODOs are review-surfaced polish, not deferred core work.

## Other findings walk

### errhandling-2 — Fixed
Claim: gen_rust_lib silently rebuilt a `LibSpec` stripping span flags when `--register-span-types`/`--unknown-span-static` passed without `--no-cst`, producing a misshapen lib (span types + grammar submodules) detectable only at Rust compile; no diagnostic at generation time. Consequence: on-call sees a downstream compile/shape error with no flag-incompatibility signal.
Code at genparser.py:451-457: early guard `if not no_cst and (register_span_types or unknown_span_static)` → `typer.echo(...err=True)` + `raise typer.Exit(1)` with an explicit message naming the incompatibility. The old `dataclasses.replace`-style rebuild branch is gone; the `else` now only builds `LibSpec.standard(...)`. New CLI test `test_gen_rust_lib_span_and_submodules_fails` (test_genparser.py:526) asserts exit != 0 and no file written.
Assessment: guard addresses the consequence at the named site (reviewer option (a), the one it recommended); test pins it. Accept.

### quality-2 — Fixed
Claim: the manual field-by-field `LibSpec` reconstruction in gen_rust_lib was a maintenance hazard (new field → stale copy). Consequence: silent staleness on field addition.
Code: the reconstruction branch is gone entirely — errhandling-2's guard rejects the only combination that needed it, so the `else` builds `LibSpec.standard()` directly and the `no_cst` branch builds a fresh `LibSpec` with all fields explicit (genparser.py:458-466). No field-copy site remains. Disposition's claim ("eliminated the branch entirely") matches.
Assessment: the copy site the finding targets no longer exists. Accept.

### quality-3 — Fixed
Claim: UNKNOWN_SPAN advisory comment hardcoded `fltk.{module_name}.UnknownSpan` — the `fltk.` package prefix is wrong for any non-`fltk.*` module using `unknown_span_static=True`. Consequence: misleading generated comment for standalone extensions.
Code at gsm2lib_rs.py:142: comment now `exposed as \`{spec.module_name}.UnknownSpan\`` — no `fltk.` prefix. Matches disposition.
Assessment: the hardcoded prefix is gone. Accept.

### quality-4 — Fixed
Claim: `tests/rust_poc_cst/Cargo.toml` declared `crate-type = ["cdylib"]` only; under `cargo test --no-default-features` a cdylib-only crate silently produces no test binary and exits zero, so future native tests would appear to pass without running. Consequence: vacuous test lane; asymmetry with `fegen-rust` (the model crate).
Code: `tests/rust_poc_cst/Cargo.toml:13` now `crate-type = ["cdylib", "rlib"]`, matching `crates/fegen-rust/Cargo.toml:14`. Matches disposition.
Assessment: robustness gap (silent-zero-tests) closed; consistency restored. Accept.

### test-1 — Fixed
Claim: `--no-cst` without span flags (validate() rejects empty-submodule zero-span spec) untested at CLI level; a future change swallowing the ValueError or writing a partial file would go uncaught.
Code: `test_gen_rust_lib_no_cst_without_span_flags_fails` (test_genparser.py:496) invokes exactly the cited args, asserts exit != 0 and `not output_rs.exists()`. Matches disposition and reviewer's prescribed fix.
Assessment: error-routing + no-partial-file both pinned. Accept.

### test-2 — Fixed
Claim: `--unknown-span-static` without `--register-span-types` untested at CLI level (ValueError→exit-1 translation unexercised).
Code: `test_gen_rust_lib_unknown_span_without_register_span_types_fails` (test_genparser.py:506) invokes the cited args, asserts exit != 0 + no file. Plus `test_gen_rust_lib_span_and_submodules_fails` (errhandling-2 path). Matches disposition.
Assessment: CLI error translation pinned. Accept.

### test-3 — Fixed
Claim: absence checked by `hasattr` name but old submodule paths not asserted absent from `sys.modules`; a stale `.so` could leave `sys.modules["fltk._native.poc_cst"]` set undetected.
Code: `test_old_native_poc_cst_path_absent_from_sys_modules` and `test_old_native_fegen_cst_path_absent_from_sys_modules` (test_module_split.py:295-301) assert both old qualified paths `not in sys.modules`, exactly the reviewer's fix. Inside `TestNativeRuntimeOnly`.
Assessment: backstop against stale-`.so` submodule leakage added. Accept.

### test-4 — Fixed
Claim: `register_span_types=True, unknown_span_static=False` (span types without UNKNOWN_SPAN) is a valid LibSpec on a distinct emission path, entirely untested; a conditional-logic bug (emitting UNKNOWN_SPAN when False) would not be caught.
Code: `_span_types_no_unknown_span_spec()` helper (test_gsm2lib_rs.py:268) + three tests (lines 279, 289, 297) asserting `mod span;`/class registrations present, UNKNOWN_SPAN + PyOnceLock absent, and submodule registration coexisting. Matches reviewer's prescribed assertions.
Assessment: the previously-uncovered conditional-emission branch is now pinned in both directions. Accept.

### test-5 — Won't-Do
Claim: `TestAC8PyRustCross.test_crates_are_distinct_python_types` asserts `type(py_cst...) is not type(fegen_rust_cst.cst...)` — vacuously true (Python dataclass vs Rust cdylib are always distinct types), so the assert can never fail; the original AC8 property (two Rust cdylibs, equal-but-distinct types) is gone with the `emb` backend.
Code at test_cross_backend_label_equality.py:159 confirms the assertion is exactly as the reviewer describes — `py_cst` vs `fegen_rust_cst.cst` types, which cannot coincide.
Rationale (Won't-Do): the test documents a design property (two backends expose distinct Python types) and is the harmless successor to the deleted AC8 cross-crate test; deleting it leaves AC8 entirely unasserted; the reviewer's own alternative ("remove and document AC8 is gone") is less informative.
Assessment: the reviewer's finding is correct that the assertion is vacuous — but the consequence it states is weak: "exercised only implicitly elsewhere," i.e. a documentation/coverage observation, not active harm. A vacuous-but-harmless sanity-check test is a should-fix-at-most nit; the disposition rubric requires a Won't-Do to argue against a *real* consequence, and here there is no correctness or robustness consequence to argue against — the test passes, asserts a true statement, and carries a docstring describing intent. The responder's rationale (keep as documented sanity check vs delete) is a defensible quality judgment; the reviewer even offered "rename/refocus" or "remove" as equally acceptable. Neither option fixes a defect. Won't-Do accepted: a Won't-Do on a no-consequence nit is sound.

## Disputed items

None. All four TODOs clear the two-question rubric (or, for the two whose Q2 is weak — errhandling-1, reuse-1 — the underlying finding is OOM-rare / nit-severity with no problem created or worsened this iteration, and the reviewer explicitly sanctioned deferral). All eight Fixed dispositions verified against code at HEAD. The one Won't-Do targets a vacuous test whose finding carries no real consequence.

## Approved

13 findings: 8 Fixed verified (errhandling-2, quality-2/3/4, test-1/2/3/4), 4 TODOs acceptable (errhandling-1, errhandling-3, reuse-1, quality-1), 1 Won't-Do sound (test-5). Correctness/security/efficiency reviewers reported no findings; not re-litigated (correctness's byte-identity and behavioral-equivalence traces spot-checked and consistent with the diff).

---

## Verdict: APPROVED

All dispositions acceptable. Every Fixed claim verified at the named line in HEAD 70fe561; every TODO clears the rubric or defers a sanctioned low-severity item with both a `TODO(slug)` comment and a `TODO.md` entry; the single Won't-Do correctly rejects a no-consequence nit. No silent deferral of a problem this iteration created. TODO pile is independent polish, not deferred core scope — not an ESCALATE-the-pile case.
