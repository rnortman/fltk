# Design review notes: span-source-as-py-crosscdylib

Concise. Precise. Adversarially fact-checked against HEAD (9db20de). Audience: smart LLM/human.

## Verification summary (load-bearing claims, all confirmed unless noted)

- §1 double-copy mechanism, line cites (`span.rs:168-170,39-45,151-161,203-207,178-185`): verified against `crates/fltk-cst-core/src/span.rs`.
- §1 "verified live" merge claim: **reproduced** — `fc.Grammar(span=Span.with_source(0,5,SourceText(t)))`; `g.span.merge(g.span)` raises `ValueError: cannot merge spans from different sources` today; same merge succeeds on the Python backend (`terminalsrc._coerce_source` string equality, `terminalsrc.py:102-107` verified). The TDD observable is real and red.
- §2.1 directionality correction: **verified sound, and the request's isinstance sketch is indeed wrong.** `extract_span` (`cross_cdylib.rs:15-48`) anchors on the one canonical type importable by any consumer. In the new entry point, executing in `fltk._native`, the incoming `source_as_py` result is registered with the *consumer's* lazily-created `PyTypeObject` (distinct object, no subclass relation — `SourceText` is `#[pyclass(frozen)]`, not subclassable, `span.rs:29`), so `isinstance` against cached `fltk._native.SourceText` rejects exactly the target case. No type anchor exists in the canonical→consumer direction. The ABI-marker substitution is justified; the request explicitly delegated this ("designer to confirm/refine", "the design must state the soundness argument explicitly").
- §2.2 mechanics: `SourceText.inner` is `pub` (`span.rs:31`), frozen+Sync so `Bound::get()` is valid; pyo3 0.23 + abi3-py310 (all three Cargo.tomls) supports `extract::<&str>()`, `#[classattr]`, `downcast_unchecked`, `intern!`, `PyTypeInfo::type_object`. SAFETY-comment mirror cites (`cross_cdylib.rs:25-36`, `40-47`) accurate.
- §2.4 fast path: in `fltk._native`, local registration is canonical; `Py::new` is sound. Slow path dispatches the canonical type's method copy (compiled into `fltk._native`), matching §2.1's per-cdylib-statics claim.
- §2.5 generator cites all accurate at HEAD: `_preamble` 244-252, `_span_getter_setter` 626-654, `_child_enum_block` 406-506; the only two `source_full_text_str` emission sites are covered (lines 457, 635); `span_type` is fetched solely for `to_pyobject` in `_children_getter`/`_generic_child`/`children_/child_/maybe_` and kept where `extract_from_pyobject` needs it — item-4 caller list is complete and correct.
- §2.7 bookkeeping: slug grep confirms the only code occurrence is `span.rs:148`; `gsm2tree_rs.py` has none; both `TODO.md` entries exist; `make gencode` covers `cst_generated.rs`, `cst_fegen.rs` + `fltk/_native/fegen_cst.pyi`, fixture `cst.rs`; `tests/rust_cst_fegen/src/cst.rs` is an `include!` (no regen needed). Stub-filter cites (`test_fltk_native_stub.py:142,157`) check out.
- §4 test vehicles exist: `tests/test_fegen_rust_cst.py`, `tests/test_phase4_rust_fixture.py` (`phase4_roundtrip_cst` = fixture crate lib name), `TestChildSpanAccessorContract` (`test_phase4_fegen_rust_backend.py:126`) runs against `fegen_rust_cst` (foreign cdylib) as claimed. Scoped slug-grep gate matches the verified `preamble-helpers-into-cst-core` precedent (`docs/adr/2026/06/10-preamble-helpers-into-cst-core/design.md:103`).
- Requirements coverage: every request constraint and verification expectation maps to a design section (goal §2.2-2.5; additive private entry point §2.3; `with_source` untouched §2.3; canonical-type constraint §2.3/§2.4; copying-contract confirmation §3; sourceless unchanged §3; regen §2.7; TODO removal §2.7; tests/gates §4). No gaps found.

## Findings

### design-1 — §3/§4: `test_merge_different_sources_raises` misdescribed; it pins the §3 "residual divergence"

Quote (§3): "No existing test asserts it (`tests/test_rust_span.py:173-179` `test_merge_different_sources_raises` uses genuinely different texts — unchanged)."

What's wrong: the test uses the **same** text twice — `src1 = SourceText("hello"); src2 = SourceText("hello")` (`tests/test_rust_span.py:174-175`). It does not use "genuinely different texts" (that's `test_intersect_different_sources_raises`, lines 209-215, "hello"/"world"). Consequently the design's own §3 "Residual divergence" case (two user-constructed same-text `SourceText`s raise on Rust merge while the Python backend succeeds) is not merely "noted for the record" — it is actively pinned as desired Rust behavior by this exact existing test.

Why: source-backed above; design contradicts the test file it cites. The conclusion ("unchanged"/green) still holds — user-constructed `SourceText`s remain distinct `Arc`s, so `coerce_source` (`span.rs:178-185`) still raises.

Consequence: an implementer auditing §3 against the suite finds the design's record of existing coverage false; the residual cross-backend divergence is recorded as untested when it is test-pinned, which would mislead a future cross-backend-equivalence pass that trusts this ADR (CLAUDE.md treats cross-backend equivalence as a hard out-of-tree-consumer requirement).

Suggested fix: correct the parenthetical — the test uses same-text, distinct `SourceText` objects; note in §3 that the residual divergence is pinned by `test_merge_different_sources_raises`.

### design-2 — §3 understates the marker's skew blind spot: pyo3-resolution skew, not just "local dev edits"

Quote (§3): "Limitation: `CARGO_PKG_VERSION` does not distinguish two builds of the same version with different layouts (e.g. local dev edits without a bump)".

What's wrong: a likelier same-marker/different-layout cause is unnamed: pyo3 version skew. The consumer crates are standalone workspaces with independent dependency resolution (`tests/rust_cst_fixture/Cargo.toml`: `[workspace]` empty, `pyo3 = { version = "0.23", ... }` caret range; real out-of-tree crates likewise). Two cdylibs can both compile `fltk-cst-core 0.1.0` (identical marker `fltk-cst-core/0.1.0`) against different pyo3 releases; `PyClassObject<SourceText>` layout is a pyo3 internal with no cross-version stability guarantee. Marker matches → `downcast_unchecked` proceeds → UB. The §2.2 soundness argument correctly states the invariant ("same pyo3 version, same struct layout") but §3's edge-case entry implies the clean-`TypeError`-on-skew improvement covers version skew generally; it only covers `fltk-cst-core` version skew. Also note `fltk-cst-core` is version `0.1.0` and effectively never bumped, so even that coverage is weak in practice.

Consequence: implementer/operator gains false confidence that skew now fails cleanly on the `SourceText` path; the most plausible real-world skew class (independent pyo3 resolution in out-of-tree consumer builds) still reaches UB with a matching marker.

Suggested fix: name pyo3-resolution skew explicitly in §3 and in the emitted `TODO(crosscdylib-abi-sentinel)` comment text (the §2.2 "layout hash" idea already points the right direction); optionally fold pyo3's version into the ABI string.

### design-3 — §2.2 contract delta: pure-Python-reachable UB accepted without considering a non-forgeable marker carrier

Quote (§2.2): "the marker is forgeable from Python (a hand-written class could set `_fltk_cst_core_abi`), whereas isinstance is not. Forged input ⇒ UB. Acceptable because (a) … (b) …".

What's wrong (gap, not error): the substitution is verified necessary (design-review brief; see verification summary — the isinstance gate cannot accept the target case), and the mitigation (private entry point, documented out-of-contract) is consistent with the `extract_span` precedent. But the design introduces the first UB path reachable from pure Python without ctypes (`extract_span`'s isinstance gate is not pure-Python forgeable: `PyObject_IsInstance` consults the canonical type's metaclass, which is pyo3's default), and the alternatives section (§2.3 "Considered and rejected") only weighs broadening `with_source`. A string classattr is the weakest marker carrier; a `PyCapsule` classattr (capsule name = ABI string) is constructible only from C/ctypes — pure Python cannot forge it — at essentially the same implementation cost and the same version-skew semantics.

Consequence: any in-process Python code (plugin, test helper, user mistake — `class Fake: _fltk_cst_core_abi = "fltk-cst-core/0.1.0"`) can trigger memory corruption through a method present on a public type, where today the worst pure-Python outcome on this surface is a `TypeError`. If the project later judges that unacceptable, the gate mechanism gets reworked post-ship.

Suggested fix (optional): carry the marker in a `PyCapsule` classattr and compare capsule name; or explicitly record in §2.2 why the string form was chosen over a capsule (e.g. abi3/pyo3 ergonomics), so the decision is deliberate rather than unexamined.

### design-4 — Stale citation: canonical-type comment is not at `src/cst_fegen.rs:317-319` at the stated base

Quote (§2.3): "satisfying the hard constraint at `src/cst_fegen.rs:317-319`."

What's wrong: at base 9db20de, lines 310-335 of `src/cst_fegen.rs` are `append`/`extend` label-handling code; the "Return a `fltk._native.Span` so consumers always get the canonical type" comment occurs at lines 247, 633, 1078, 1481, 2094 (grep-verified). The 317-319 cite is inherited verbatim from `request.md`/pre-9db20de exploration, while the design header claims its cites are against base 9db20de (and its other line numbers are HEAD-accurate).

Consequence: trivial — the constraint itself is real and verified; an implementer following the cite lands in unrelated code and must re-grep.

Suggested fix: cite `src/cst_fegen.rs:633-634` (span getter instance) or just the comment text.
