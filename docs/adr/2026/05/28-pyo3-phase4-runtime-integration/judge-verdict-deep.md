# Judge verdict — deep review

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base f8a2fe1..HEAD 52d3c04. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 18 findings.
Note: reviewers reviewed `cdffac4`; the dispositions/fixes land in HEAD `52d3c04` (descendant of `cdffac4`). Verified fixes against the `cdffac4..52d3c04` diff and current file state.

## Added TODOs walk

Four findings dispositioned TODO. Each scored against the two-question rubric before judging.

### security-1 — TODO(rust-cst-dyn-import-doc) — claimed at plumbing.py:78
Q1 (worth doing): marginal-yes — a docstring note that `rust_cst_module` must be a trusted/static value, never derived from untrusted input. The reviewer's own remedy is "document in the function docstring."
Q2 (design/owner input required): **NO** — adding ~2 lines to the `_load_rust_cst_classes` / `generate_parser` docstring is mechanical, needs no design cycle and no owner input. Fails Q2 → do-now, not TODO.
Furthermore — broken TODO: the disposition claims `TODO(rust-cst-dyn-import-doc)` at `plumbing.py:78` but `grep` finds **no** such comment in the code and **no** `TODO.md` entry (the only hit is the dispositions doc itself). The disposition text explicitly states "No TODO.md entry added." Per CLAUDE.md "TODO System", a TODO requires BOTH halves joined on the slug; neither exists. So the disposition is a no-op: the documentation was neither written nor tracked.
Assessment: **REWORK**. Fails Q2 (doable now) and the "TODO" is non-existent — neither the doc note nor a valid TODO(slug)+TODO.md pair. Either write the one-paragraph docstring note now (preferred), or create a real, joined TODO.

### test-5 — TODO(rust-cst-child-span-test) at tests/test_phase4_fegen_rust_backend.py:114
Q1 (worth doing): yes — pins that Rust-backed `child_name()`/`child_value()` results expose `.start`/`.end`, the exact attributes `Cst2Gsm.visit_identifier/literal/regex` read (`fltk2gsm.py:26,136,140`).
Q2 (design/owner input required): borderline — the test is gated on the `fegen_rust_cst` Tier-2 artifact, which is build-and-CI infrastructure already wired (`make build-fegen-rust-cst`, CI lane). Writing the focused assertion is mechanical (the reviewer specifies it), but it sits in the skip-when-absent tier and AC8 already exercises the path indirectly via `parse_grammar` equality. Not a problem this iteration created (the accessor contract is Phase 3).
Assessment: TODO **acceptable, marginally**. Coverage exists indirectly (AC8); the deferred item is a diagnostic-aid focused test in a build-gated tier. TODO(slug) + TODO.md both present and joined. Not the strongest TODO, but defensible — does not drive the verdict.

### reuse-1 / quality-1 — TODO(genparser-parse-dedup) at genparser.py:226
Q1 (worth doing): yes — `_parse_grammar_raw` (genparser.py:219-251) is a verbatim copy of `parse_grammar_file` (genparser.py:26-55) minus the trivia tail; two copies of file-read + TerminalSource + fltk_parser + Cst2Gsm must move together.
Q2 (design/owner input required): **NO** — extracting a private helper that both call, both in the same file, is a pure mechanical refactor. No API surface, no design cycle, no owner input. The disposition's rationale ("doing it in a respond round risks introducing bugs in parser invocation and error formatting") is exactly the "non-trivial" dodge the rubric forbids — that is a code-review concern, not "design work required."
Furthermore — `_parse_grammar_raw` is **new code this iteration** (added by the `gen-rust-cst` subcommand, increment 3). The duplication was *introduced* by this diff, not inherited. Per rubric, a problem this iteration created cannot be silently deferred.
Assessment: **REWORK**. Fails Q2 (mechanical, single-file) and the duplication is iteration-introduced. Extract the shared helper now (reviewer even notes `_parse_grammar_raw` could delegate to `plumbing.parse_grammar`), or escalate with a concrete reason it cannot be done in this round.

### quality-3 — TODO(fegen-cst-rs-single-source) at tests/rust_cst_fegen/src/cst.rs:1
Q1 (worth doing): yes — `src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` are byte-identical committed copies (reviewer verified `diff` = empty); a regen of one silently diverges the other, and the fegen Rust CST fixture would then test stale code.
Q2 (design/owner input required): yes — the fix is a build-mechanism choice (symlink vs. Makefile copy step vs. Rust `include!`), each with cross-platform / build-graph tradeoffs that belong in a deliberate build-system decision, not a respond round. The stringly-typed `"fltk._native"`/`"UnknownSpan"` half is already tracked under the pre-existing `TODO(rust-cst-abi-pinning)`.
Furthermore — the duplicate committed file is **iteration-introduced** (the `tests/rust_cst_fegen/` crate is new this phase, 4608 lines). A problem this iteration created cannot be *silently* deferred — but it is **not** silent: TODO(slug) at `cst.rs:1` + TODO.md entry both present and joined, surfacing the hazard for the build-system decision.
Assessment: TODO **acceptable**. YES to both rubric questions (worth doing AND needs a build-mechanism design choice); the iteration-created hazard is surfaced, not hidden. Properly joined.

## Other findings walk

### errhandling-1 — Fixed
Claim: `_load_fegen_grammar` `fegen_fltkg.open()` had no try/except; a corrupted/mis-packaged install surfaces a bare `FileNotFoundError` with an internal path and no diagnosis. Consequence stated (on-call cannot distinguish broken-package from user error).
Diff at `plumbing.py:53-62`: wrapped `open()` in `try/except FileNotFoundError`, re-raised as `RuntimeError` naming the path and directing to reinstall. Verified present at HEAD.
Assessment: fix addresses the consequence at the named site. Accept.

### errhandling-2 — Fixed
Claim: `genparser.py:174` shared-CST write block caught `except RuntimeError`, but `open()`/`write()` raise `OSError`; the catch never fires, so I/O failures crash with a raw traceback instead of the intended CLI message. Real bug in diff-touched code (the `generate` command was extended this phase).
Diff at `genparser.py:174`: `except RuntimeError` → `except OSError`. Verified at HEAD (line 174). The `typer.echo(...err=True)` + `raise typer.Exit(1)` now reachable on permission/missing-dir failures.
Assessment: correct fix; matches stated consequence. Accept.

### correctness-1 — Fixed
Claim: `lib.rs:10` `pub(crate) static UNKNOWN_SPAN` is now write-only — no generated code reads `crate::UNKNOWN_SPAN` after the sentinel-cache change; latent dead-code/coupling-confusion trap. Reviewer explicitly scoped this as a note, not a behavior bug.
Diff at `lib.rs:7-16`: added a comment block explaining the static is set at init, exposed as `fltk._native.UnknownSpan`, no longer read by generated code (which uses per-extension `UNKNOWN_SPAN_CACHE`), retained for back-compat; references `TODO(rust-cst-shared-rlib)` (comment + TODO.md both present). No behavioral change.
Assessment: the finding asked for a drop-or-comment; responder chose comment + TODO cross-ref. Addresses the consequence (future reader won't mistake it for live coupling). Accept.

### security-2 — Won't-Do
Claim: `exec()` of generated parser/unparser from grammar text; a malicious grammar could induce RCE at parser-generation time. Consequence stated.
Rationale: pre-existing architectural assumption (grammars are trusted developer artifacts), predates the diff; the Rust branch *reduces* exec surface (no CST exec); a fix requires redesigning the generator — out of scope.
Verification: reviewer's own note (security-2) concurs — "predates the diff… the diff does not widen it… Out of scope as a *new* finding… Suggested: none for this diff." The `# noqa: S102` markers are not new. The diff's Rust path adds no exec; it removes one.
Assessment: Won't-Do argues against an iteration-introduced regression that does not exist here, and the reviewer agrees no action is warranted for this diff. Accept.

### test-1 — Fixed
Claim: `test_rust_backend_no_python_exec_fallback` is byte-identical to `test_rust_backend_missing_module_hard_errors`; zero additional coverage.
Diff: deleted `test_rust_backend_no_python_exec_fallback` (test_plumbing.py). Verified removed; the surviving test asserts `RustBackendUnavailableError` + `module_name not in sys.modules`.
Assessment: duplicate removed, coverage preserved. Accept.

### test-2 — Fixed
Claim: `test_parse_grammar_rust_missing_module_no_fallback` used a try/except sentinel; a wrong exception type would silently pass with `result is None`.
Diff at test_plumbing.py:532-537: replaced with `with pytest.raises(RustBackendUnavailableError): parse_grammar(...)`. Verified.
Assessment: now fails on wrong exception type. Accept.

### test-3 — Fixed
Claim: `test_parse_grammar_file_rust_backend` body identical to `test_fegen_grammar_itself_rust_equals_python`; zero added coverage.
Diff: deleted `test_parse_grammar_file_rust_backend` (test_phase4_fegen_rust_backend.py:85-92). Verified removed; the equality test via `parse_grammar_file(..., rust_fegen_cst_module=...)` remains.
Assessment: duplicate removed. Accept.

### test-4 — Fixed
Claim: `test_rust_backend_uses_provided_classes` did not assert `pr.parser_class is not None`; a `None` parser class would pass the `in sys.modules`/`hasattr` checks.
Diff at test_plumbing.py:512: added `assert pr.parser_class is not None`. Verified.
Assessment: defect now caught. Accept.

### test-6 — Fixed
Claim: `assert "UNKNOWN_SPAN\n" not in poc_source` (test_gsm2tree_rs.py:207) is a fragile newline-suffix check that passes vacuously if coupling re-appears without a trailing newline.
Diff at test_gsm2tree_rs.py:207: replaced with `assert "\nuse crate::UNKNOWN_SPAN" not in poc_source` — the exact import form that re-introduces linkage. Line 208 (`UNKNOWN_SPAN.get(py)`) retained as the behavioral check.
Assessment: structural import check now targets the real re-coupling form. Accept.

### test-7 / quality-2 — Fixed (same fix)
Claim: `generate_parser` set `sys.modules[module_name] = cst_module` before the parser `exec`/class-validation; a codegen failure leaves a poisoned entry under `fltk_grammar_{id(grammar)}`, observable by a later call reusing the same `id`.
Diff: removed the early `sys.modules[...]=cst_module` (was after the setattr loop) and moved it to `plumbing.py:272-273`, after the "Generated parser class not found" raise. Verified: registration now follows successful class resolution.
Assessment: a codegen failure now leaves `sys.modules` clean. Both test-7 and quality-2 (same defect) addressed. Accept.

### reuse-2 — Won't-Do
Claim: three independent `parse_grammar_file` implementations (`genparser`, `plumbing`, `genunparser`) duplicate the parse sequence. Consequence: a parse/error-format change must touch three places.
Rationale: `genparser.parse_grammar_file` and `genunparser.parse_grammar_file` predate this diff and were untouched; consolidating pre-existing untouched code in a respond round widens scope without a design mandate. Tracked at the right level by `TODO(genparser-parse-dedup)` for the in-file pair.
Verification: the diff touched only `plumbing.parse_grammar`/`parse_grammar_file` (Rust seam). The three-module spread is pre-existing tech debt, not iteration-introduced.
Assessment: Won't-Do on the pre-existing cross-module triplication is sound (not a regression, no design mandate). NOTE: this is distinct from reuse-1/quality-1 (`genparser-parse-dedup`), which concerns the *new* in-file `_parse_grammar_raw` duplicate — adjudicated separately above as REWORK. Accept reuse-2 as scoped.

### efficiency-1 — Fixed
Claim: the Rust branch of `parse_grammar` called `generate_parser(fegen_grammar, ...)` on every invocation, paying full codegen+exec each time though the fegen grammar is fixed.
Diff at `plumbing.py:38-42,149-154`: added module-scope `_fegen_rust_parser_cache: dict[str, ParserResult]` keyed by module name; cache-checks before `generate_parser`; on hit only `TerminalSource`+parse+`Cst2Gsm` are per-call. Verified.
Assessment: removes the per-call codegen multiplier; matches the stated consequence and the reviewer's suggested fix. Accept.

### efficiency-2 — Won't-Do
Claim: `visit_items` builds a filtered `labeled_children` copy per `Items` node, a full-copy no-op on the Python backend (no None-labeled children) — O(total children) extra allocation taxing the default path for a Rust-only concern.
Rationale: cost is small (grammar conversion is one-shot, not a tight inner loop); the uniform code path has clarity value; the efficiency reviewer flagged it low-priority and "if kept for simplicity, no action needed."
Verification: reviewer's own text concedes "Modest in absolute terms… Low priority… If kept for simplicity, no action needed." Severity is nit (cosmetic allocation on a non-hot path).
Assessment: nit; reviewer pre-conceded no action. Won't-Do acceptable. Accept.

## Disputed items

- **security-1 / TODO(rust-cst-dyn-import-doc)**: fails Q2 (the remedy is a mechanical docstring note, doable now) AND the dispositioned TODO does not exist — no `TODO(slug)` comment in `plumbing.py`, no `TODO.md` entry (disposition states so outright). Need: write the docstring trust note now (preferred), OR create a real joined TODO(slug)+TODO.md pair and justify the deferral against Q2.
- **reuse-1 / quality-1 / TODO(genparser-parse-dedup)**: fails Q2 (single-file mechanical helper extraction) and the `_parse_grammar_raw` duplicate is iteration-introduced. Need: extract the shared helper now (or delegate `_parse_grammar_raw` to `plumbing.parse_grammar`), OR escalate with a concrete blocker. The TODO is properly joined, but a properly-tracked TODO does not rescue a do-now item from the rubric.

## Approved

16 findings: 9 Fixed verified (errhandling-1, errhandling-2, correctness-1, test-1, test-2, test-3, test-4, test-6, test-7/quality-2, efficiency-1), 3 Won't-Do sound (security-2, reuse-2, efficiency-2), 2 TODOs acceptable (test-5 marginally, quality-3/fegen-cst-rs-single-source).

---

## Verdict: REWORK

Two dispositions wrong, round 1:
- **security-1** — TODO that fails Q2 (mechanical docstring note) and was never actually created (no comment, no TODO.md entry).
- **reuse-1/quality-1** — TODO that fails Q2 (single-file mechanical refactor) for an iteration-introduced duplicate.

Both are do-now items hidden behind deferral; security-1 additionally violates the TODO-system join requirement. Remaining 16 findings accept.
