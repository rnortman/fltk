# Judge verdict — deep review: span-source-as-py-crosscdylib

Phase: deep. Base 9db20de..HEAD 28355db (review commit 588d55f + respond commit 28355db). Round 1.
Notes: 7 reviewer files; 13 findings (4 errhandling, 1 correctness, 2 security, 5 test, 1 reuse, 1 efficiency; quality: none).
Verified empirically at HEAD: `tests/test_rust_span.py` 59 passed (foreign-cdylib tests ran, not skipped); `tests/test_phase4_rust_fixture.py -k "sourceless or merge"` 3 passed; slug grep over `*.py`/`*.rs`/`*.pyi` empty; slug absent from `TODO.md`.

Note repeated per style rule: Concise. Precise. Complete. Unambiguous.

## Added TODOs walk

### efficiency-1 — TODO(crosscdylib-abi-sentinel) at cross_cdylib.rs:114-117
Q1 (worth doing): yes — per-span-read constant overhead (`get_span_type` + `type_object().is()` + classmethod getattr) on the consumer slow path, which is the accessor hot path for out-of-tree consumers walking large CSTs. Reviewer rates it small-magnitude/optional, but real.
Q2 (design/owner input required): yes — the cache's natural home is the `GILOnceCell` init that `crosscdylib-abi-sentinel` will redesign (TODO.md:17: sentinel "checked once in get_span_type's GILOnceCell init"); bolting caches onto the gate mechanism now would be churned by that redesign, and the efficiency reviewer explicitly recommended "extend that TODO rather than churn this change." Not a problem this iteration created — the change is a strict improvement over the O(N) copies it replaces.
TODO system: `TODO(crosscdylib-abi-sentinel)` comment present at the named site; slug entry exists at `TODO.md:15-17`. Join key intact. Minor: the TODO.md body was not extended to name the caching sub-task (it lives only in the code comment); greppable via the slug, so acceptable.
Assessment: TODO acceptable.

## Other findings walk

### errhandling-1 — Fixed
Claim: non-str `_fltk_cst_core_abi` marker fell through to a misleading "expected SourceText, got X" TypeError, hiding the real cause; consequence is mis-diagnosis cost.
Inspection: `cross_cdylib.rs:78-87` adds a distinct TypeError naming the attribute and its actual type ("_fltk_cst_core_abi attribute is {attr_type}, not str") before the final fallthrough. Pinned by new `test_with_source_unchecked_non_str_marker_raises_type_error` (`test_rust_span.py:309-316`, `match="_fltk_cst_core_abi"`). Passes.
Assessment: fix addresses the consequence at the named branch. Accept. (Residual nit: the new branch re-inlines the type-name retrieval with a `"<unknown>"` fallback instead of calling `py_type_name(&marker)` — see reuse-1 note; outside this finding's scope, non-blocking.)

### errhandling-2 — Won't-Do
Reviewer's own note: "No finding here... Documented to avoid re-raising." `?` propagation of `get_span_type` errors confirmed correct by the reviewer.
Assessment: non-finding; Won't-Do trivially correct. Accept.

### errhandling-3 — Won't-Do
Reviewer's own note: "Documented to avoid re-raising: the allocation error is correctly propagated."
Assessment: non-finding. Accept.

### errhandling-4 — Won't-Do
Claim: the fast-path comment in `extract_source_text` ("succeeds when caller is the same cdylib") is slightly misleading for the `span_to_pyobject` slow-path invocation, where the consumer-registered `SourceText` fails the canonical-cdylib downcast and takes the marker path. Reviewer: "Not an error-handling finding — noting for accuracy." No consequence stated.
Inspection: the observation is technically correct, but `span_to_pyobject`'s slow-path doc (`cross_cdylib.rs:110-112`) already states the marker check is what fires on that path. No-consequence finding → responder wins by default; rationale (explaining the re-entrancy would obscure more than clarify) is reasonable besides.
Assessment: accept.

### correctness-1 — Fixed
Claim: retired slug `span-source-as-py-crosscdylib` remained in `TODO.md` sentinel-entry prose, falsely failing the design §4 item 5 completion gate.
Diff at `TODO.md:17`: "(added in the `span-source-as-py-crosscdylib` fix)" → "(introduced alongside `extract_source_text`)" — exactly the reviewer's suggested rewording. Gate re-run by me: `grep -rn` over `*.py`/`*.rs`/`*.pyi` returns nothing; slug count in `TODO.md` is 0.
Assessment: accept.

### security-1 — Won't-Do
Claim: forgeable ABI-marker gate makes `downcast_unchecked` a pure-Python-reachable memory-corruption primitive; suggested `__basicsize__` defense-in-depth check.
Ground truth: design §2.2 explicitly weighs this exact threat (marker "forgeable from Python... Forged input ⇒ UB"), rejects the capsule alternative as equally replayable, and states "Fail-safe hardening that narrows forgery to `TypeError` (e.g. sanity-checking the foreign type's `__basicsize__`...) is delegated to `crosscdylib-abi-sentinel`, which owns the gate mechanism." That design passed design review. The reviewer's own note concedes the design accepts the risk and frames the suggestion as defense-in-depth. The reviewer's residual complaint (risk "lives in an ADR, not at the call site") is factually addressed: UB-on-forgery is documented at the `unsafe` site (`cross_cdylib.rs:62-67`), in the function safety contract (`:31-39`), and in the `_with_source_unchecked` docstring. Deferral is tracked under the existing `crosscdylib-abi-sentinel` TODO.md entry.
Push-back on the rationale's weakest plank: a basicsize check is ~6 lines, not a "partial redesign" — but the controlling fact is the design's explicit, reviewed delegation of that hardening to the sentinel follow-up, so the Won't-Do stands on design grounds regardless.
Assessment: accept.

### security-2 — Won't-Do
Claim: `CARGO_PKG_VERSION`-only marker misses pyo3-resolution skew → silent UB. Reviewer: "Already tracked; recorded here so the memory-safety consequence is explicit."
Ground truth: design §3 names pyo3-resolution skew as the likeliest skew class and assigns the strengthened derivation to `crosscdylib-abi-sentinel`; the TODO comment at `cross_cdylib.rs:14-21` and the `TODO.md:17` entry both name it explicitly.
Assessment: documented known limitation, already tracked; no new finding. Accept.

### test-1 — Fixed
Claim: no test names the `span_to_pyobject` same-cdylib fast path as its target; a refactor removing the branch would pass silently.
Inspection: `test_span_to_pyobject_fast_path_arc_sharing` (`test_rust_span.py:263-277`) constructs a `fltk._native.fegen_cst.Grammar` (same cdylib), names the `Span::type_object(py).is(&span_type)` branch in the docstring, asserts double-read merge + text. Matches the reviewer's suggested fix verbatim. Passes.
Assessment: accept.

### test-2 — Fixed
Claim: `pytest.raises(TypeError)` without `match` would pass on any TypeError; skipped-fixture lane unverified.
Inspection: `match="SourceText"` added at `test_rust_span.py:338`; docstring now states "A CI lane where this test is always skipped is a gap, not a pass" (`:330-331`). Test ran (not skipped) in my verification.
Assessment: both halves of the suggested fix applied. Accept.

### test-3 — Fixed
Claim: marker test verified class-direct access, not the `type(instance)` path `extract_source_text` actually takes.
Inspection: `test_source_text_abi_classattr_exists` (`test_rust_span.py:241-250`) now asserts `hasattr(type(src), ...)` and `type(src)._fltk_cst_core_abi == SourceText._fltk_cst_core_abi`, with a docstring naming the production access path.
Assessment: accept.

### test-4 — Fixed
Claim: sourceless arm of `span_to_pyobject`'s slow path (cross-cdylib) unexercised.
Inspection: `TestAC7BothBackends.test_cross_cdylib_sourceless_span_accessor` (`test_phase4_rust_fixture.py:583-594`) constructs `Entry(span=Span(3, 7))` through the foreign `phase4_roundtrip_cst` cdylib, asserts `not s.has_source()` and `s == Span(3, 7)`. Pins the `None` arm exactly as the reviewer specified. Passes.
Assessment: accept.

### test-5 — Fixed
Claim: final no-marker branch's error message unasserted; no explicit no-marker-attribute test.
Inspection: (a) `match="fltk._native.SourceText"` on the str case (`test_rust_span.py:295-298`); (b) `test_with_source_unchecked_no_marker_attr_raises_type_error` with a bare class (`:300-307`); (c) `test_with_source_unchecked_non_str_marker_raises_type_error` (`:309-316`) — exceeds the asked-for fix by also pinning the errhandling-1 branch. All pass.
Assessment: accept.

### reuse-1 — Fixed
Claim: identical four-line type-name/TypeError blocks duplicated between `extract_source_text` and `extract_span`.
Inspection: `fn py_type_name` at `cross_cdylib.rs:96-101`; both named call sites now use it (`:91`, `:174`). The duplication the finding named is gone.
Assessment: accept. Observation (non-blocking nit, new code outside the finding's scope): the errhandling-1 fix's non-str-marker branch (`:79-83`) re-inlines the same pattern on `marker` with a divergent `"<unknown>"` fallback where `py_type_name(&marker)` would serve; candidate for a future cleanup pass, does not invalidate this disposition.

## Approved

13 findings: 8 Fixed verified (errhandling-1, correctness-1, test-1..5, reuse-1), 4 Won't-Do sound (errhandling-2/3/4, security-1/2 — errhandling-2/3 were reviewer-declared non-findings), 1 TODO acceptable (efficiency-1).

## Disputed items

None.

---

## Verdict: APPROVED

All 13 dispositions acceptable. Fixes verified at the named lines and empirically green at HEAD; Won't-Dos grounded in the approved design or in reviewer-declared non-findings; the single TODO passes both rubric questions and is properly joined to `TODO.md`.
