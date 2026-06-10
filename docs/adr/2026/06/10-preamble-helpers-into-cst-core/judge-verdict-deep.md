# Judge verdict — deep review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: deep. Base 87bf19e..HEAD e7f8f88 (implementation 5e29293, respond round e7f8f88). Round 1.
Notes: 7 reviewer files; 6 findings (reuse, quality, efficiency, correctness: no findings).

## Added TODOs walk

### security-1 — TODO(crosscdylib-abi-sentinel) at crates/fltk-cst-core/src/cross_cdylib.rs:34-36
Q1 (worth doing): yes — version skew between a consumer's pinned `fltk-cst-core` and the installed `fltk._native` wheel lets `isinstance` pass while `Span` layout differs, so `downcast_unchecked` (cross_cdylib.rs:37) converts a packaging error into in-process memory corruption. Reviewer's consequence verified against the code; the `pub` promotion (lib.rs re-export) genuinely widens reach to arbitrary downstream Rust crates.
Q2 (design/owner input required): yes — the sentinel mechanism needs design decisions: what the sentinel derives from (`CARGO_PKG_VERSION` vs layout hash — version equality is stricter than ABI compatibility), where it is exported (`fltk._native` module registration lives in a different crate), and mismatch semantics. Also behavior-preservation was an explicit constraint of this change (design.md §2.1), so a runtime check could not land in this iteration; the reviewer themself marked it "a follow-up, not a blocker."
Iteration-created check: the unsafe path is pre-existing, moved verbatim per design constraint; the exposure widening (pub) was a deliberate design-stage decision, not incidental. Deferral is not silent: TODO comment inside the INVARIANT VIOLATION block + `TODO.md:19-21` entry — both join points verified present, slugs match.
Assessment: TODO acceptable.

## Other findings walk

### errhandling-1 — Fixed
Claim: `get_span_type` propagates a bare `ModuleNotFoundError` on failed `fltk._native` import, with no cross-cdylib context; asymmetric with `get_source_text_type`.
Diff at `cross_cdylib.rs:58-62`: `.map_err` wrapping added inside the `get_or_try_init` closure, emitting `PyRuntimeError("cross-cdylib Span type lookup failed (fltk._native.Span): {e}")` — exactly the pattern the reviewer cited from `get_source_text_type` (cross_cdylib.rs:81-83).
Assessment: fix addresses the consequence at the named location. Accept.

### errhandling-2 — Fixed
Claim: `obj.get_type().name()?` in the error branch can itself fail, replacing the intended `PyTypeError` with a context-free secondary error.
Diff at `cross_cdylib.rs:40-44`: replaced with `.map(|n| n.to_string()).unwrap_or_else(|_| "<unknown type>".to_string())` — the error branch now always emits `PyTypeError`; the secondary failure path is eliminated. Matches the reviewer's suggested shape.
Assessment: accept.

### test-1 — Fixed (partial — slow positive path deferred)
Claim: only the fast path of `extract_span` is exercised; the cross-cdylib slow path (isinstance + `downcast_unchecked`) is uncovered. Reviewer's fix explicitly offered a fallback: "If a two-crate test fixture is impractical, at minimum document the gap and add a negative-path test."
Action verified: `TestExtractSpanErrorPaths` added at `tests/test_phase4_rust_fixture.py:375-416` (four tests); suite passes (44 passed). This satisfies the reviewer's stated minimum.
Additionally, code inspection shows the reviewer's premise is incorrect: the slow **positive** path is already exercised in CI. `tests/test_phase4_rust_fixture.py:34` imports `Span` from `fltk._native`; `_span` (line 61) constructs that type; `test_ac2_span_write` (line 169-175) and `test_construction_and_span` (line 429-436) assign it to nodes from the fixture cdylib `phase4_roundtrip_cst`, which registers its **own** `Span` type object (`tests/rust_cst_fixture/src/lib.rs:16`). pyo3 `extract::<Span>()` matches only the locally-registered type object (documented at cross_cdylib.rs:8-10), so these assignments fail the fast path, traverse isinstance + `downcast_unchecked`, and round-trip-assert the result. The "deferred" portion is therefore already covered; no TODO needed for it.
Assessment: accept.

### test-2 — Fixed
Claim: `import_count == 0` assertion over-broad as written; needs intent-scoping comment. Reviewer: "No code change required if acceptable as-is — this is a documentation/intent clarity issue."
Diff at `tests/test_gsm2tree_rs.py:191-194`: comment added scoping the assertion to preamble-helper absence, with explicit instruction to update on future legitimate `py.import("fltk._native")` emission. Matches the requested fix.
Assessment: accept.

### test-3 — Fixed
Claim: no test for the `extract_span` wrong-type error path (`PyTypeError` + "expected fltk._native.Span" message).
Action verified: `TestExtractSpanErrorPaths` covers integer/string/None rejections plus `test_set_span_wrong_type_message_mentions_span` with `pytest.raises(TypeError, match="fltk._native.Span")` — exception type and message both pinned. Ran: 44 passed.
Assessment: accept.

## Approved

6 findings: 5 Fixed verified, 1 TODO acceptable.

---

## Verdict: APPROVED

All dispositions acceptable. Both errhandling fixes verified at the named lines; the security TODO passes both rubric questions and is dual-registered; all three test findings resolved with passing tests (and the one deferred gap is shown to be already covered in-tree).
