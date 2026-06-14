# Judge verdict — deep review

Phase: deep. fltk base 7200d9c..HEAD 674f392 (fix commits 25bbfef, 8fd4059, 674f392). clockwork base 6ede250..HEAD ea34388 (no code changes in fix round). Round 1.
Notes: 7 reviewer files; 15 findings (errhandling 5, correctness 0, security 3, test 4, reuse 1, quality 3, efficiency 0). Dispositions reference HEAD 8fd4059; verified against actual HEAD 674f392, which is a strict superset (adds dispositions doc, TODO.md entry, deferred Bazel comment).

## Added TODOs walk

### errhandling-4 — TODO(bazel-lib-rs-location) at rust.bzl:218
Q1 (worth doing): marginal-yes — guards a latent ambiguous-`$(location)` expansion that triggers only if `name + "_gen_lib"` ever grows a second `outs` entry. Verified at `rust.bzl:208-219`: the genrule declares exactly one out (`gen_lib_rs_out`), so `$(location :name_gen_lib)` is unambiguous today. The TODO documents the load-bearing invariant ("works because exactly one out").
Q2 (design/owner input required): no — the suggested change (use `$(location gen_lib_rs_out)` instead of the target label) is mechanical, single-line, single-file.
Furthermore check: this iteration did NOT create or worsen a defect here — the current code is correct; the TODO is a forward-looking invariant note, not a deferred bug. So the "cannot silently defer" clause does not bite.
Assessment: Fails Q2 in the strict sense, which would normally push to do-now. But the change is purely defensive against a non-existent future state (no second out), the consequence is latent and trivial (opaque-but-non-silent Bazel error, not a wrong result), and the comment correctly pins the invariant that keeps the current form correct. Both halves of the TODO convention are satisfied (TODO.md:31 + comment at rust.bzl:218). Acceptable as a TODO; not worth a rework cycle. The responder's framing (quoting fix applied, latent concern deferred) matches the code.

## Other findings walk

### errhandling-1 — Fixed
Claim: two independent copies of `_RUST_IDENT_RE` (genparser.py:400 and gsm2lib_rs.py:16) can silently diverge, producing inconsistent CLI vs library validation.
Verification: `grep _RUST_IDENT_RE fltk/fegen/genparser.py` returns nothing — the CLI copy and its pre-validation block are gone. genparser.py:431-437 now builds the spec and delegates entirely to `RustLibGenerator(spec)`, whose `__init__` calls `spec.validate()`; the `ValueError` is caught at the existing `except ValueError` → `typer.Exit(1)`. Single authoritative copy remains at gsm2lib_rs.py:16.
Assessment: fix removes the duplication that was the finding's whole consequence. Accept.

### errhandling-2 — Fixed
Claim: `try/except ValueError` covered only `generate()`, not the `RustLibGenerator(...)` constructor, so a constructor-side `ValueError` from `spec.validate()` would escape as an unformatted traceback.
Verification: genparser.py:432-437 (`gen_rust_lib`) and 462-467 (`gen_rust_native_lib`) both now read `gen = RustLibGenerator(spec); src = gen.generate()` with both statements inside the `try`. Constructor validation is now guarded.
Assessment: fix addresses the named consequence at the named lines. Accept.

### errhandling-3 — Fixed
Claim: `LibSpec(submodules=())` with no span/UNKNOWN_SPAN flags silently generates an empty `#[pymodule]` that registers nothing.
Verification: gsm2lib_rs.py:81-83 adds the guard in `validate()` raising `ValueError("LibSpec.submodules must not be empty when no span types or UNKNOWN_SPAN are registered")`. Test `test_empty_submodules_raises_value_error` (test_gsm2lib_rs.py:122-125) asserts `pytest.raises(ValueError, match="submodules")`.
Assessment: silent-acceptance path is now a hard error with a test pinning it. Accept.

### errhandling-5 — Won't-Do
Claim: `register_submodule` `?`-propagation in the consumer lib.rs lacks added context. Reviewer's own text: "already acknowledged as TODO(native-submodule-error-context) ... tracked in TODO.md. No change needed; noting here for completeness."
Verification: the slug is tracked at TODO.md:27 and the `TODO(native-submodule-error-context)` comment was relocated to its true home at `crates/fltk-cst-core/src/py_module.rs:86` (the design §3/§4 bookkeeping requirement — comment + TODO.md entry both present, satisfying CLAUDE.md's two-part convention). The finding states no consequence requiring action and recommends no change.
Assessment: reviewer explicitly requests no fix; no actionable consequence stated. Responder wins by default. Accept. (Bookkeeping the design promised is also verified done.)

### test-1 — Fixed
Claim: `test_gen_rust_lib_invalid_module_name_empty` and `..._has_space` checked only `exit_code != 0` / file-absence, not that the message names the offending value.
Verification: test_genparser.py:403 adds `assert "''" in result.output` to the empty test; the has-space test (test_genparser.py:422-424) adds `assert not output_rs.exists()` and `assert "has space" in result.output`. Now matches the digit/hyphen test pattern.
Assessment: silent-exit regression now caught. Accept.

### test-2 — Fixed
Claim: no test for `--module-name` omitted entirely (distinct typer parse-layer path from empty string).
Verification: `test_gen_rust_lib_missing_module_name` (test_genparser.py:437-444) invokes `gen-rust-lib` with no `--module-name` and asserts `exit_code != 0`.
Assessment: the omission path is now covered. Accept.

### test-3 / quality-2 — Fixed (same fix)
Claim: `cfg_python_gate` is dead config on a public frozen dataclass — `generate()` never reads it; a caller setting it gets standard output silently.
Verification: `grep -rn cfg_python_gate fltk/ src/` returns nothing — the field is fully removed from `LibSpec`. Responder chose removal over a `NotImplementedError` guard, which is the cleaner choice per the reviewer's own option (b) and avoids a public-API footgun (CLAUDE.md: generated/public surface). Field can return with a real implementation when needed.
Assessment: dead-field trap eliminated. Accept both.

### test-4 — Fixed
Claim: native_spec tests check presence only, not relative order of mod declarations / registrations; a transposition would pass all tests.
Verification: `test_native_spec_declaration_and_registration_order` (test_gsm2lib_rs.py:198-209) asserts `src.index("mod cst_generated;") < src.index("mod cst_fegen;")` and `src.index('"poc_cst"') < src.index('"fegen_cst"')`.
Assessment: ordering is now pinned. Accept.

### reuse-1 / quality-1 — Fixed (same fix as errhandling-1)
Claim: duplicate `_RUST_IDENT_RE` constant; CLI pre-check duplicates generator validation.
Verification: same as errhandling-1 — CLI copy and pre-check removed; single site at gsm2lib_rs.py:16.
Assessment: Accept both.

### quality-3 — Won't-Do
Claim: if typer lets the call proceed with `module_name = None`, the old guard `if not module_name` passes but `_RUST_IDENT_RE.match(None)` raises `TypeError` instead of a clean usage error.
Verification: the premise is now structurally void — the CLI pre-guard (and its `_RUST_IDENT_RE.match`) was deleted in the errhandling-1 fix, so there is no `match(None)` site to raise `TypeError`. Independently, typer rejects a missing required option at its parse layer with exit 2 before the function body runs (responder verified by running the CLI; test-2's `test_gen_rust_lib_missing_module_name` pins the non-zero exit).
Assessment: the finding's failure mechanism cannot occur — it described code that no longer exists, and typer guards the missing-option case at parse time regardless. Won't-Do rationale argues the premise is false and is correct against the source. Accept.

### security-1 — Fixed
Claim: target `name` interpolated unquoted into the genrule shell `cmd`; the `_RUST_IDENT_RE` validation runs inside the Python command, i.e. after the shell boundary, so it does not protect the shell.
Verification: rust.bzl:213 now emits `--module-name '{module_name}'` (single-quoted). The interpolated value sits inside shell quotes before the Python validator sees it; the guard is now on the correct side of the boundary.
Assessment: fix puts the quoting where the finding said it belonged. Defense-in-depth, low real exposure (build-author actor, Bazel name grammar), but correctly addressed. Accept.

### security-2 — Won't-Do
Claim: `module_name`/submodule names interpolated into generated Rust; safe only because `validate()` is the mandatory gate. Finding explicitly: "Currently safe ... Suggested fix: none required."
Verification: `RustLibGenerator.__init__` calls `spec.validate()` (gsm2lib_rs.py:90) — the single mandatory gate, unchanged and confirmed present. No unvalidated construction path exists.
Assessment: reviewer recommends no fix; the invariant it relies on holds. Accept.

### security-3 — Won't-Do
Claim: no path validation/confinement on `output_file`. Finding explicitly: "Acceptable for a developer codegen CLI ... Suggested fix: none required."
Verification: build-time tool; caller is the build author / genrule controlling `$@`. No trust boundary crossed. Matches the security reviewer's own trust-model section.
Assessment: no actionable consequence; reviewer agrees no fix. Accept.

### correctness / efficiency — no findings
Both reviewers reported zero findings. Correctness reviewer independently traced generator output byte-for-byte against committed `src/lib.rs`, the blank-line separator logic, `--no-parser` control flow, recursion_limit non-injection, and Bazel genrule wiring — all confirmed correct. Nothing to adjudicate.

## Disputed items

None. Every Fixed disposition is verified at the named line; every Won't-Do has a reviewer-stated no-fix recommendation or a source-confirmed false premise; the one TODO satisfies the rubric and the two-part TODO convention.

## Approved

15 findings: 9 Fixed verified (errhandling-1/-2/-3, test-1/-2/-3/-4, reuse-1, quality-1, security-1 — counting the shared fixes once each: errhandling-1≡reuse-1≡quality-1 one fix, test-3≡quality-2 one fix), 5 Won't-Do sound (errhandling-5, quality-3, security-2, security-3), 1 TODO acceptable (errhandling-4 / bazel-lib-rs-location). Correctness and efficiency: 0 findings.

---

## Verdict: APPROVED

All dispositions acceptable. Every Fixed verified against HEAD 674f392 at the named lines; every Won't-Do is either reviewer-recommended-no-fix or rests on a premise the source contradicts; the single TODO passes the two-question rubric (latent, trivial, invariant-documenting) and satisfies the two-part TODO convention. No item disputed.

Commit: fltk 674f392, clockwork ea34388.
