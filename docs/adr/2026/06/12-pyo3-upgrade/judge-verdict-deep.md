# Judge verdict — deep review

Phase: deep. Base 2919733..HEAD 1ffbbec (dispositions at 63493a8 + TODO commit 1ffbbec). Round 1.
Notes: 7 reviewer files (security, reuse, efficiency: no findings); 14 dispositioned findings.

Style note: concise, precise, complete, unambiguous; audience is smart LLM/human.

## Added TODOs walk

### correctness-1 — TODO(abi-probe-cargo-test) at Makefile:47, TODO.md entry present
Slug join intact: `TODO.md` entry + `TODO(abi-probe-cargo-test)` comment in the `cargo-test` target. Mechanically well-formed.

Q1 (worth doing): yes — verified against `Makefile`: `cargo-test` is `cargo test -q` (root package only; root `Cargo.toml` is a workspace-with-package, so members are not tested), `cargo-test-no-python` compiles the module out, and no clippy lane passes `--all-targets`, so `abi_probe_tests` (including the new correctness-2 equality tests) is neither executed nor type-checked by `make check`. Design §3 step-2 checkpoint ("cargo test -p fltk-cst-core green") is unmet for the feature lane the guard lives in.

Q2 (design/owner input required): split.
- The full fix genuinely needs **owner input**: verified on this box that `/usr/lib64` has only `libpython3.10.so.1.0` — the unversioned `libpython3.10.so` that `-lpython3.10` needs is absent (python3.10 dev package not installed). The TODO's own proposed fix (`-L$(sysconfig LIBDIR)`) does not work here without that package; resolving requires installing OS packages or a CI/environment policy decision the agent cannot make.
- But the reviewer's "at minimum" mitigation — a clippy lane with `--all-targets` so the test module cannot silently stop compiling — needs **no libpython link** (clippy does not link) and is doable now. Not done.

Rubric outcome: per the TODO rubric, "product owner input needed" maps to **ESCALATE**, not TODO. The iteration-created clause also applies: `abi_probe_tests` was added this iteration as the design's named stub-regression guard (§2.A/§5), and it landed gate-dead; a problem this iteration created cannot be silently deferred — it must be fixed or escalated for visibility. The responder buried it in TODO.md instead.

Assessment: disposition wrong — correct outcome is ESCALATE (see escalation section).

## Other findings walk

### errhandling-1 / quality-1 — Fixed (duplicate pair)
Claim: stale `GILOnceCell` in span.rs doc comments at the `_fltk_cst_core_abi` classattr and `kind` getter; misleads on-call readers tracing ABI failure paths.
Diff: span.rs now reads "``PyOnceLock`` init" and "``PyOnceLock`` cache" at both sites; the co-located `downcast_unchecked` → `cast_unchecked` also applied. Accept.

### errhandling-2 — Won't-Do
Reviewer's own verdict: "No finding. Noted for reviewer clarity." Nothing to fix. Accept.

### errhandling-3 — Won't-Do
Reviewer's own verdict: "No finding. Pattern is intentional." Accept.

### errhandling-4 — Fixed
Claim: `registry.rs` race-recovery branch `.expect(...)` panics (PanicException) instead of raising catchable PyErr; reachable under free-threaded Python.
Diff at registry.rs:121-127: `lookup(py, arc_addr)?.ok_or_else(|| PyRuntimeError::new_err(...))` — exactly the reviewer's suggested fix, message preserved. Accept.

### correctness-2 — Fixed
Claim: guard test recomputes `size_of::<Layout>()` independently and never reads the probe sites; a constant-stubbed classattr body passes.
Diff: `span_abi_layout_probe()` / `source_text_abi_layout_probe()` extracted as `pub(crate)` in span.rs; both classattr bodies delegate; lib.rs adds `*_probe_matches_classattr_body` equality tests calling the free fns.
Caveat 1: the disposition's claim "A hardcoded constant in either classattr body now fails the test" is overstated — the tests call the free fns, not the classattrs, so a constant in the one-line delegating classattr body still passes. Residual exposure is a single trivially-reviewable delegation line, and the probe's computation now lives in tested functions; one-sided classattr stubs are also caught end-to-end by the gate-run subprocess ABI tests (`check_abi_pair` success path would mismatch).
Caveat 2: these Rust tests are gate-dead regardless (correctness-1) — folded into the escalation.
Assessment: substantively addresses the finding's intent; accept with caveats noted.

### correctness-3 — Fixed
Claim: `"span: PyObject," not in poc_source` assertions vacuous post-migration.
Diff at test_gsm2tree_rs.py (TestNodeStructure.test_span_field_native, TestNoPyObjectAudit.test_no_pyobject_span_field): `assert "span: Py<PyAny>," not in poc_source` added in both, old spelling retained, docstrings updated. Matches the generator's current `Py<PyAny>` spelling used by the positive assertions. Accept.

### test-1 / quality-2 — Fixed (duplicate pair)
Diff at tests/test_rust_span.py:475-481: all three `GILOnceCell` occurrences in `TestSpanPathAbiGate` docstring now `PyOnceLock`; behavioral claim ("does NOT cache errors") correctly retained per quality-2's verification. Accept.

### test-2 — Fixed (one sub-item declined with rationale)
Diff: span.rs `downcast_unchecked` → `cast_unchecked` (SourceText layout doc + Span abi doc), cross_cdylib.rs:33 `downcast` → `cast`, :247 "PyObject" → "Python object (`Py<PyAny>`)". cross_cdylib.rs:383 "before any unchecked downcast" left as-is: rationale (verb usage, conceptual type-narrowing, standard Rust terminology) is sound — the sentence describes an operation, not the removed pyo3 API name. Note: an unflagged stale `downcast` reference remains at cross_cdylib.rs:73 ("fails the `downcast` above", referring to the `cast` call at :65) and span.rs:97; outside the finding's named sites and both reviewers accepted residual doc-comment mentions as exhaustively surveyed — not a disposition failure. Accept.

### test-3 / quality-3 — Fixed (duplicate pair)
Diff at fltk/fegen/test_genparser.py:75: `GILOnceCell` → `PyOnceLock`. Accept.

### test-4 — Fixed
Claim: Python-side tests assert only `layout > 0`; a probe-disabled variant returning 1 passes pytest.
Diff at tests/test_rust_span.py: `import ctypes` added; `assert layout >= ctypes.sizeof(ctypes.py_object)` in both classattr tests — the reviewer's suggested fix verbatim. Minor inaccuracy carried over from the finding itself: `ctypes.sizeof(ctypes.py_object)` is pointer size (8), not `sizeof(struct PyObject)` (16); the floor still rules out the 0/1 stub constants the finding targets, which is the stated goal. Accept.

## Escalation — correctness-1 / TODO(abi-probe-cargo-test)

Reviewer's claim + consequence: the design's §2.A/§5 stub-regression guard (`abi_probe_tests`, protecting the ABI layout probe that gates `cast_unchecked` across cdylibs) is never compiled or executed by any `make check` lane; design §3 step-2 checkpoint unmet; a future probe stub or bit-rot of the test module passes the full gate. Reviewer verified the tests pass when the link path is forced (symlink), so the code is correct — only the gating is missing.

Responder's disposition + rationale: TODO(abi-probe-cargo-test) — Makefile comment + TODO.md entry stating the libpython link requirement and a proposed PYO3_PYTHON/-L fix.

Why human arbitration is needed:
1. The actual blocker is environment provisioning: this box lacks the unversioned `libpython3.10.so` (dev package not installed; verified). Fixing for real means installing OS packages and/or deciding what `make check` may assume about dev/CI environments — owner decisions an agent cannot make. The rubric maps owner-input-needed to ESCALATE, not TODO; and since this iteration created the gate-dead guard, it cannot be silently deferred to TODO.md.
2. Decision for the owner: (a) install python3.10 dev libs and add `cargo test -q -p fltk-cst-core` (or a dedicated lane) to the gate; (b) accept a sysconfig-derived `-L`/symlink shim in the Makefile (works, but fragile across environments); or (c) accept the gate-run Python-level guards (test-4 floor checks + subprocess ABI-gate tests) as the effective regression defense and downgrade/keep the TODO deliberately.
3. Independent of that choice, the reviewer's minimum mitigation — a clippy lane with `--all-targets` covering `fltk-cst-core` (python feature on) so the test module is at least type-checked by the gate — requires no libpython link and can be done immediately; the responder skipped it.

## Approved

13 of 14 findings: 10 Fixed verified (incl. 3 duplicate pairs resolved with their primaries), 2 Won't-Do sound (reviewer-confirmed no-findings), 1 Fixed with noted caveats (correctness-2).

---

## Verdict: ESCALATE

correctness-1's TODO disposition defers an iteration-created, design-committed gate gap whose resolution requires product-owner/environment decisions. All other dispositions acceptable.
