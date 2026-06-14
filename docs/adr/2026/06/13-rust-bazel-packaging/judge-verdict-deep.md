# Judge verdict — deep review

Phase: deep. fltk base fafa6d7..HEAD fac3da5; clockwork base ece332a..HEAD 932320e. Round 1.
Notes: 7 reviewer files (security, reuse = "No findings"). 18 findings dispositioned.

Note on phase shape: the deliverable under review is a design ADR plus its accompanying first-cut implementation diff (rust.bzl, BUILD.bazel, MODULE.bazel, clockwork cdylib target + roundtrip test). The build is not yet runnable from a clean checkout (toolchain wiring / crate_universe resolution is the implementation spike, by the design's own framing). Several findings are spike-time verifications that cannot be settled from the source tree — relevant to the TODO walk below.

## Added TODOs walk

### correctness-3 / efficiency-3 — TODO(verify-pyo3-ext-module) at MODULE.bazel:42
Q1 (worth doing): yes — if `extension-module` is not active on `@fltk_crates//:pyo3`, both `:native` and every `fltk_pyo3_cdylib` consumer link libpython and fail at link/import (the failure mode design §4 names). High-value verification.
Q2 (design/spike input required): yes — this is a crate_universe `from_cargo` feature-resolution question. The correctness reviewer themselves "could not confirm from the tree"; it is only answerable by actually running `bazel build //:native` with the toolchain wired, which is the implementation spike. Not doable now from source.
Furthermore check (this-iteration risk cannot be *silently* deferred): not silent — TODO present, TODO.md entry present (line 17), documented `crate.annotation` fallback, and §4 flags the failure as loud (link/import error, never wrong answer). Surfaced, not buried.
Assessment: both Q1/Q2 yes → TODO acceptable.

### test-3 — TODO(fltk-pyo3-cdylib-smoke) at BUILD.bazel:107
Q1 (worth doing): yes — `fltk_pyo3_cdylib`'s crate-assembly / abi3-rename / py_library-wrapper logic has no FLTK-side coverage; it is new public Bazel surface (CLAUDE.md: generated/Bazel surface is consumed out-of-tree). Design §5.4 lists it as a test-plan item.
Q2 (design/spike input required): borderline-yes. The reviewer supplies a concrete recipe (fixture grammar + minimal lib.rs), so the *authoring* is mechanical. But the smoke target links the same pyo3 and exercises the same macro path that is blocked on `verify-pyo3-ext-module`; it cannot be validated until the toolchain is wired and that spike resolves. Writing an unrunnable smoke target now buys nothing over deferring it to when the macro path is first actually built.
Assessment: gated on the same spike as verify-pyo3-ext-module; tracked in TODO.md (line 13) with a concrete recipe and location. Acceptable as a deferral to the implementation spike, not a silent scope drop. TODO acceptable.

Aggregate-scope check: the deferred set is two spike-time verifications + one smoke target, all genuinely blocked on the single "not runnable until implementation spike" gate intrinsic to an ADR-design phase. This is not a respond-mode narrowing of substantive design work (no `scope-N` reviewer finding; design §5 still commits to all five test-plan items). Not an ESCALATE-grade scope pile.

## Other findings walk

### correctness-1 — Fixed
Claim: test reads `result.value`; `PyApplyResult` has no `value` getter → `AttributeError`, AC #4 span asserts are dead code.
Evidence: `gsm2parser_rs.py:850-861` confirmed — `PyApplyResult` exposes only `pos` and `result` getters, `frozen`, no `__getattr__`. Test now reads `module_node = result.result` (`clockwork_rust_roundtrip_test.py:62`) with a comment noting there is no `.value`.
Assessment: fix addresses the consequence at the named line. Accept.

### correctness-2 — Fixed
Claim: `register_classes` is `#[cfg(feature = "python")]`-gated; cdylib set only `extension-module`; Bazel crate_features do not forward → unresolved symbol at compile, cdylib does not build (AC #2).
Evidence: feature gate confirmed at `gsm2parser_rs.py:843,957` and `gsm2tree_rs.py:382-392`; `clockwork_native_lib.rs:15-16` calls `cst::register_classes`/`parser::register_classes` unconditionally. Fix at `rust.bzl:233` now sets `crate_features = ["extension-module", "python"] + crate_features` with an explanatory comment; linked `fltk-cst-core` BUILD sets `["python"]` (`crates/fltk-cst-core/BUILD.bazel:6`), so they agree.
Assessment: build-blocking defect correctly resolved at the named line. Accept.

### correctness-4 — Fixed
Claim (minor): trailing `\n` + `result.pos == len(src)` is a fail-loud risk if final-separator trivia does not consume the newline.
Evidence: `clockwork_rust_roundtrip_test.py:50` now `src = "cpu_domain main;"` (no newline), with a comment explaining the removal.
Assessment: fail-loud risk removed at the named line. Accept.

### errhandling-1 — Won't-Do
Claim: `cp $< $@` in the abi3-rename genrule expands `$<` to all `DefaultInfo` files; a *future* `rules_rust` sidecar could make it copy the wrong file → opaque ImportError. Consequence is conditioned on "if a future rules_rust version adds a sidecar."
Disposition rationale: correctness reviewer independently verified `$<` is the sole `.so` today ("Checked and OK", correctness notes:147-149); future risk is speculative; failure if it ever occurs is a loud `ImportError`, not a silent wrong answer.
Assessment: the finding's consequence is explicitly future-conditional and does not apply to the code as shipped; current behavior verified correct by a second reviewer. Won't-Do rationale argues the failure stays loud (no silent wrong answer). Bar met. Accept.

### errhandling-2 — Won't-Do
Claim: crate-assembly `for` loop over `$(locations rs_srcs)` would copy a *future* third output of `generate_rust_parser` into the crate dir → name collision / cryptic compile error. Future-conditional.
Disposition rationale: rule's `DefaultInfo` emits exactly two files today (verified — `rust.bzl:72` returns `depset([cst_out, parser_out])`); the genrule has explicit declared `outs` (`cst.rs`, `parser.rs`, `lib.rs`), so any unexpected extra copy collides and fails loudly at compile, not silently; a future third output is a deliberate change to `generate_rust_parser` with an obvious update site.
Assessment: confirmed `DefaultInfo` is exactly two files; explicit `outs` make the speculated failure loud. Future-conditional finding, no current defect. Accept.

### errhandling-3 — Fixed (subsumed by quality-1)
Claim: `@fltk//:native_py` as a bare string in the py_library dep could self-reference / cycle when the macro is called inside FLTK.
Evidence: `rust.bzl:267` now `deps = [Label("@fltk//:native_py")]`; `Label()` binds to FLTK's module context at load time.
Assessment: the Label() fix removes the call-site ambiguity the finding raises. Accept.

### errhandling-4 / test-2 — Fixed
Claim: `warnings.catch_warnings` around `import fltk._native` is vacuous — span.py's fallback warning is never triggered by importing `_native` directly; the AC #3 guard is effectively absent, and import caching makes it order-dependent.
Evidence: test rewritten (`clockwork_rust_roundtrip_test.py:13-35`) — `catch_warnings` block removed; now imports `fltk._native` directly (loud ImportError if `.so` absent) and asserts `fltk_native.Span.__module__ == "fltk._native"` to distinguish the Rust type from the pure-Python fallback. This is the substantive check the reviewers asked for.
Assessment: the vacuous guard is replaced with a real AC #3 assertion at the named lines. Accept.

### errhandling-5 / quality-1 — Fixed
Claim: bare string cross-repo labels (`//crates/fltk-cst-core`, `//crates/fltk-parser-core`, `@fltk_crates//:pyo3`) resolve relative to the *caller's* repo under Bzlmod → "no such target" for every out-of-tree consumer; the macro is broken for its primary use case (CLAUDE.md: out-of-tree consumers are load-bearing).
Evidence: `rust.bzl:240-242` now wraps all three in `Label(...)`, plus `Label("@fltk//:native_py")` at :267, with an explanatory comment (:235-239) stating exactly the Bzlmod resolution rule.
Assessment: real correctness defect for the advertised use case, fixed at the named lines. Accept.

### test-1 — Fixed
Claim: Clockwork's `py_test` wrapper calls `fail()` at analysis time without `py_pytest_main` boilerplate → target never runs, AC #4 unexercised.
Evidence: `clockwork/dsl/BUILD.bazel:82-98` adds `py_pytest_main(name = "__rust_test__", deps = ["@clockwork_pip//pytest"])`, includes `:__rust_test__` in `srcs` and `deps`, and sets `main = ":__rust_test__.py"` — matching the repo pattern.
Assessment: analysis-time failure resolved; AC #4 can now execute. Accept.

### quality-2 — Fixed
Claim: docstring says `@fltk//:native_so`; code depends on `@fltk//:native_py` (cosmetic, misleading).
Evidence: `rust.bzl:150` now reads `carries @fltk//:native_py as a data dep`.
Assessment: corrected at the named line. Accept.

### quality-3 — Fixed
Claim: MODULE.bazel comment "spike excluded" is inaccurate — `fltk-cst-spike` is a workspace member and is included in the hub.
Evidence: `MODULE.bazel:27-32` now states `fltk-cst-spike IS included as a workspace member and its transitive deps appear in this hub`, correctly distinguishes the `tests/*` crates as excluded, and adds `TODO(bazel-cst-spike-hub)` (TODO.md:21).
Assessment: comment now matches actual `from_cargo` behavior. Accept.

### efficiency-1 — Won't-Do
Claim: the crate-assembly copy is a third action per cdylib; could be collapsed by having `generate_rust_parser` accept `lib_rs`.
Disposition rationale: design §3.4 considered and rejected `#[path=...]`; the copy is the accepted cost of same-directory `mod` resolution; one genrule copy per cdylib, negligible at Clockwork's one-cdylib scale; collapsing it changes the rule interface (out of scope).
Assessment: finding's own framing concedes "negligible / not blocking." Won't-Do argues a real design trade-off already documented. No correctness consequence. Accept.

### efficiency-2 — Won't-Do
Claim: `cp $< $@` byte-copies a multi-MB `.so` on every relink instead of symlinking; incremental-rebuild I/O and remote-cache bandwidth.
Disposition rationale: symlinks need platform-specific sandbox handling; `cp` is the portable default; cost acknowledged and acceptable for one cdylib + one `:native`; `copy_file` from skylib is a noted future cleanup path.
Assessment: should-fix-at-most efficiency nit on a build action (not a runtime hot path); reviewer's own "if cp must stay for sandbox-portability, this is acceptable" concedes the trade-off. Won't-Do reasoning sound. Accept.

## Disputed items

None.

## Approved

18 findings: 9 Fixed verified, 4 Won't-Do sound, 2 TODOs acceptable (3 finding IDs across the 2 TODO slugs: correctness-3 + efficiency-3 share verify-pyo3-ext-module; test-3 is fltk-pyo3-cdylib-smoke), errhandling-3 Fixed-subsumed verified. Security and reuse reviewers returned "No findings."

---

## Verdict: APPROVED

All dispositions acceptable. Fixed claims verified against the diff at the named lines (rust.bzl, BUILD.bazel, MODULE.bazel, clockwork BUILD.bazel + test). Both Won't-Dos rest on future-conditional or negligible-cost reasoning that holds against the code as shipped, with failures shown to stay loud. Both deferred TODOs pass the two-question rubric — worth doing and genuinely blocked on the implementation spike (crate_universe feature resolution can only be settled by running the build) — are tracked in TODO.md with concrete recipes, and are not a respond-mode narrowing of committed design scope.
fltk HEAD: fac3da5. clockwork HEAD: 932320e.
