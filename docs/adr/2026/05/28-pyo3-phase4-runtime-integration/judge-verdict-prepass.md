# Judge verdict — prepass

Phase: prepass. Base f8a2fe1..HEAD 4320e5d. Round 1.
Notes: 2 reviewer files (slop, scope); 6 findings (slop-1..4, scope-1, scope-2).
Note carried into this doc: concise, precise, source-backed. No padding.

Dispositions header references commit 11dce0a; HEAD is 4320e5d. All claims re-verified against HEAD.

No added-TODO findings in this prepass (the two `TODO(slug)` items are design-anticipated deferrals, not findings dispositioned this round). Other-findings walk only.

## Other findings walk

### slop-1 — Fixed
Claim: stray meta-instruction `Concise. Precise. Audience: FLTK user...` shipped in `docs/rust-cst-extension-guide.md` body. Consequence: meta-instruction shipped to users as prose.
Evidence: `grep "Concise. Precise"` on the guide returns nothing; head of file shows clean Overview prose, no stray line.
Assessment: line removed. Fix addresses the consequence. Accept.

### slop-2 — Fixed
Claim: `cst_label` walrus at `fltk2gsm.py` bypasses the `self.cst` DI pattern; latent isinstance-dispatch inconsistency. Consequence (responder-corrected): the "references nothing in scope" premise is false (walrus binds a local); real concern is future-reader confusion.
Evidence: `fltk2gsm.py:81-83` now carries a two-line comment ("`cst_label` is a raw CST node; `visit_identifier` reads only span offsets off it, so no `self.cst` isinstance dispatch is needed here"). `visit_identifier` (line 24) reads `.child_name()` / span only — no isinstance, confirming no dispatch is required.
Assessment: finding was low-severity (responder correctly downgraded the false-crash premise); comment resolves the reader-confusion concern. Accept.

### slop-3 — Fixed
Claim: task-tracker prose ("Increment 3", "deferred from Increment 2", "AC6 Python half") in `test_genparser.py` module docstring. Consequence: development-history narration, not reader-facing description.
Evidence: `test_genparser.py:1` now a single line: "Tests for the gen-rust-cst CLI subcommand: source emission, sentinel decoupling, and no-double-trivia contract." No increment/AC references remain.
Assessment: replaced with a reader-facing description. Accept.

### slop-4 — Fixed
Claim: "behavior identical to before" narrative docstring at `test_python_backend_default_unchanged`. Consequence: cosmetic LLM-narration tell in a public docstring.
Evidence: `test_plumbing.py:454` now "No rust_cst_module argument → Python backend is used; parser and cst_module are populated as usual." (A separate "behavior identical to before" remains at `:533` on a different test, `test_*` for `parse_grammar`, not the finding's target at the old 1048-1050 range.)
Assessment: targeted docstring rewritten. Accept. (The :533 sibling was not in scope of this finding; not re-flagged.)

### scope-1 — Fixed
Claim: `test_cst2gsm_default_namespace_unchanged` (design Test Plan §Tier 1) absent — DI refactor's `Cst2Gsm` default-path backward-compat not independently unit-guarded. Consequence: a regression in the default-`cst` path surfaces only through integration paths.
Evidence: `test_plumbing.py:565` `TestCst2GsmDefaultNamespace` with two tests — `test_default_cst_is_fltk_cst` (`cst2gsm.cst is _fltk_cst`) and `test_default_namespace_produces_correct_grammar` (constructs `Cst2Gsm(terminals.terminals)` with no `cst=`, calls `visit_grammar`, compares to `parse_grammar` baseline).
Assessment: focused unit guard for the default path now exists; catches a namespace-binding regression, which is the DI refactor's risk. Grammar comparison is shallow (rule count + names only, not full structural identity) — weaker than the design's "identical gsm.Grammar output" but the finding's core consequence (no independent default-path guard) is discharged. Accept.

### scope-2 — Won't-Do — REJECTED
Claim: `test_makefile_builds_rust_cst` (AC6, design Test Plan §Tier 2 lines 581-584) absent — no automated assertion that `make build-*` targets produce importable artifacts.
Consequence (finding): drift between Makefile targets and crate layouts caught only manually. The finding itself hedges: "acceptable to record as a CI gap... IF CI already runs these before pytest... If CI does not yet run those targets, the gap is real."
Disposition rationale: "The design treats this as a CI-level concern ('CI runs make build-* before pytest'). A pytest test shelling to make would invert build/test separation. CI pipeline configuration is out of scope for respond mode."

Source check — the rationale's load-bearing premise is FALSE against repo state:
- `.github/workflows/ci.yml:27` runs only `make check`.
- `Makefile:6`: `check: lint typecheck test cargo-check cargo-clippy cargo-test` — does NOT invoke `build-native`, `build-test-user-ext`, or `build-fegen-rust-cst`.
- Therefore CI never builds `phase4_roundtrip_cst` or `fegen_rust_cst`. Both Tier-2 suites are gated `skipif(... not importable)` (`tests/test_phase4_rust_fixture.py:30`, `tests/test_phase4_fegen_rust_backend.py:31`), so EVERY Tier-2 test — including the *binding* AC5 (`test_rust_cst_contract_non_fltk`), AC8 (`test_real_cst2gsm_on_rust_fegen_backend`), AC3 roundtrip — silently skips in CI.
- Design line 442 / 559: "A CI lane that skips every Tier-2 test is a failure signal" / "a CI skip is a failure signal." The current repo IS that failure signal.

The responder invoked the design's "CI builds before pytest" framing to justify deferral, but CI is not wired that way. The finding's own conditional ("If CI does not yet run those targets, the gap is real") is satisfied — the gap is real, and it is not cosmetic: the entire artifact-dependent verification suite (the binding ACs) is inert in CI.

Rubric: the fix is doable now without a design cycle or owner input — add the three `make build-*` invocations to `ci.yml` before the test step (and/or fold them into `check`). Not "design work required," not "owner input needed." Furthermore, this iteration introduced both the skip-when-absent Tier-2 policy and the CI-builds-first contract the rationale leans on; per the rubric a problem this iteration created cannot be silently deferred.

The "no cargo/maturin from any Python parse path" half of AC6 IS covered (`TestNoRuntimeCompilation` / `test_plumbing_imports_no_subprocess_or_build_tools`, `test_plumbing.py:607`), and the "module importable + classes exposed" half has partial Tier-2 coverage (`TestAC6FegenRustCstModule`). The uncovered piece is precisely the build-wiring guarantee — which the false CI premise leaves unprotected.

Assessment: Won't-Do does not meet the active-harm bar; rationale rests on a false premise about CI state. Real consequence, mechanical fix, this-iteration regression. REWORK.

## Disputed items

- **scope-2 / Won't-Do**: rejected. Needed — wire `make build-native`, `make build-test-user-ext`, `make build-fegen-rust-cst` into CI (`ci.yml`, before/within the pytest step) so Tier-2 suites run rather than skip, satisfying the design's "a CI skip is a failure signal" contract and discharging the AC6 build-wiring guarantee. The promised CI sequence does not currently exist. (A pytest-shells-to-make test is NOT required and the responder is correct to reject that form; the fix is the CI wiring the rationale falsely assumed already present.)

## Approved

5 findings: 5 Fixed verified (slop-1, slop-2, slop-3, slop-4, scope-1).

Out-of-scope note (no verdict impact): the scope reviewer asserted both deferred TODOs have code-comment placements; `TODO(rust-cst-abi-pinning)` has a `TODO.md` entry but its marker appears only in `docs/rust-cst-extension-guide.md`, not at a source-code work site (cf. `rust-cst-shared-rlib` correctly placed at `gsm2tree_rs.py:121`). Not a dispositioned finding this round; flagged for the next author, not adjudicated here.

---

## Verdict: REWORK

One disposition wrong (scope-2 Won't-Do rests on a false premise about CI state; real consequence — binding ACs skip in CI; mechanical fix available). Round 1.
