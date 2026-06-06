# Judge verdict — deep review (clean-protocol-consumer-api)

> Concise. Precise. Complete. Unambiguous. No padding.

Phase: deep. Base 1e78b73..HEAD 87c8342 (response commit 052e98e; reviewers saw bc42280, fixes land at 052e98e). Round 1.
Notes: 7 reviewer files. Findings dispositioned: 11 (errhandling-1/2/3, test-1/2/3/4, reuse-1/2, quality-1/2/3). Correctness, security, efficiency reviewers filed no actionable findings.

## Added TODOs walk

Two TODOs added, both backing the same two reuse/quality findings. Verified `TODO.md` entries (`TODO.md:71-77`) and `TODO(slug)` comments (`gsm2tree.py:443-449`) both present; slugs join correctly.

### reuse-1 / quality-1 — TODO(protocol-label-member-bridge-unify) at gsm2tree.py:447
Q1 (worth doing): yes — two independent emitters of the cross-backend `__eq__`/`__hash__` bridge (`_emit_cross_backend_eq_hash` pygen at `gsm2tree.py:99-132` vs. `_emit_protocol_label_member_class` `ast.parse` string at `:451-468`) can drift; any future bridge edit must be applied twice.
Q2 (design/owner input required): yes — not mechanical. The two shapes deliberately differ in the same-type fast path: the enum helper emits `self.name == other.name` (`:121`), which `_ProtocolLabelMember` cannot use (it is a plain class, no `.name`; it compares `_fltk_canonical_name`, `:459`). `_emit_cross_backend_eq_hash` also takes an `enum_klass` ClassDef and mutates it in place. Unifying requires choosing how to parameterize the same-type discriminant and reshaping the helper's contract — a real design decision, not a rename.
Furthermore (iteration-created check): this iteration introduced `_ProtocolLabelMember` and thus the second emitter. But the duplication is not a *failure deferred silently* — correctness of both bridges is directly guarded by the AC-7 cross-backend equality/hash tests (`test_clean_protocol_consumer_api.py` Label suite, both operand orders, matching + non-matching, hash). The drift risk is a future-maintenance hazard, not a present defect; it does not fail Q2's "problem this iteration created cannot be silently deferred" bar because it is test-guarded and surfaced, not silent.
Assessment: YES/YES → TODO acceptable.

### quality-3 — TODO(protocol-label-member-private) at gsm2tree.py:443
Q1 (worth doing): yes — `_ProtocolLabelMember` is emitted as a module-level class in the generated public protocol module (`fltk_cst_protocol.py`, public API per CLAUDE.md), visible to `import *` and IDE autocomplete; downstream could couple to it. Leading underscore is informal-only.
Q2 (design/owner input required): yes — both fixes touch public-API surface. (a) emitting `__all__` changes `import *` semantics for *every* existing public symbol in the generated module (a behavior change on public API consumed out-of-tree), and requires curating the exported set; (b) moving the class to a new `pyrt.bridge` module is a structural/layout decision. Per CLAUDE.md the generated protocol module is public API with breaking-change rules; deciding the boundary mechanism is exactly the kind of deliberate, called-out public-API decision the TODO defers correctly.
Furthermore (iteration-created check): the leak was created this iteration. Not silently deferred: the symbol is named, the TODO is filed, and it is inert (underscore-prefixed, no behavior). It is a surfaced API-hygiene item awaiting a deliberate public-API call, not a masked failure.
Assessment: YES/YES → TODO acceptable. Single TODO covers both quality-3 and the shared root cause; not a pile.

## Other findings walk

### errhandling-1 — Fixed
Claim: five bare asserts in `fltk2gsm.visit_items` carry no diagnostic payload; `AssertionError` on malformed CST gives no signal (which label/index/rule). Consequence: silent-ish failure mode in a grammar-compilation pipeline requiring repro to debug.
Diff (`fltk2gsm.py:55-86`): loop now `enumerate`d; all five asserts carry f-string messages with actual value (`{item_label!r}`, `kind={item.kind!r}`, `{sep_label!r}`) and the computed interleaved-child index (`start_idx + 2*i`, trailing index, count mismatch). Matches reviewer's prescription.
Assessment: fix addresses the consequence at every named site. Accept.

### errhandling-2 — Fixed
Claim: Rust `Span.kind` getter propagated raw `ModuleNotFoundError`/`AttributeError` via `?` with no root-cause context; a broken deployment makes the whole CST traversal surface unusable with an opaque error from inside a `#[getter]`.
Diff (`src/span.rs:260-276`): `?` chain replaced with `.and_then(...).and_then(...).map(...).map_err(|e| PyValueError::new_err(format!("Span.kind: failed to load SpanKind.SPAN from fltk.fegen.pyrt.terminalsrc: {e}")))`. Wrapped message names the import path and the bridge as the reviewer specified. `GILOnceCell` retry-on-failure behavior is acceptable (idempotent import, reviewer concurred).
Assessment: fix addresses the consequence at the named line. Accept.

### errhandling-3 — Won't-Do
Claim: duck-typed `__eq__` returns `True` for any foreign object that happens to carry the right `_fltk_canonical_name`. Reviewer's own verdict: "Not a new finding; design-intentional. No change required."
Rationale: intentional cross-backend equality contract, present pre-diff, mandated by requirements ("equality is defined via the existing canonical-name bridge"; "Changing the equality contract itself ... is out of scope") and design §1.
Assessment: the finding states no actionable consequence — the reviewer explicitly closed it as informational. Requirements lock the canonical-name bridge as out-of-scope-to-change. Responder right that it is bogus-as-actionable. Accept Won't-Do.

### test-1 — Fixed
Claim: `test_shapes_fixture_no_forbidden_patterns` did not scan for `TYPE_CHECKING`; a fixture regression reintroducing the shadow import would pass all tests, violating the gating criterion undetected.
Diff (`test_clean_protocol_consumer_api.py:254`): `assert "TYPE_CHECKING" not in code_text` added alongside the existing cast/runtime_checkable/S101 scans.
Assessment: closes the named gap. Accept.

### test-2 — Fixed
Claim: `test_nodekind_nonmatching_neq` exercised only Python (`py_cst`) in the `!=` direction; missed external Rust `NodeKind` for the non-matching case (AC 7 `False` semantics, design §2.3c `NotImplemented` load-bearing).
Diff (`:436-450`): base test now also covers `embedded_rust_cst.NodeKind.GRAMMAR` both orders (`:442-443`); new gated `test_nodekind_nonmatching_neq_rust_external` (`:446-450`) covers `fegen_rust_cst.NodeKind.GRAMMAR` both orders. Reviewer asked for embedded+external; both present.
Assessment: closes the gap, exceeds the ask. Accept.

### test-3 — Fixed
Claim: `PROTOCOL_MODULE_PATH` declared but unused; no test guards design §3 "no new file-level suppressions" in the generated protocol module.
Diff (`:310-325`): `test_protocol_module_no_new_file_level_suppressions` reads `PROTOCOL_MODULE_PATH`, asserts exactly one `# ruff: noqa` line and that it is `N802` (pre-existing/permitted), asserts no inline `# type: ignore`. Correctly scopes to the generated module; the `terminalsrc.py` `# type: ignore[attr-defined]` is hand-written and out of this module's scope (reviewer concurred).
Assessment: constant now used; guard matches the design constraint. Accept.

### test-4 — Fixed
Claim: AC 12 "`case cst.Span.kind:` matches a Rust `fltk._native.Span` separator" was not exercised end-to-end through `match`/`case` dispatch — only `==` on a standalone instance. A bug satisfying `==` but not match/case evaluation order would be missed.
Diff (`:681-701`): `test_rust_native_span_dispatches_via_match_case` runs a real `match rust_span.kind` with `case proto_cst.Item.kind / Trivia.kind / Span.kind / _`, asserts the `Span` arm is taken and no fall-through. `RustSpan` is `fltk._native.Span`. Matches the reviewer's prescription exactly.
Assessment: closes the dispatch-mechanism gap. Accept.

### reuse-2 — Fixed
Claim: `SpanKind.__eq__` same-type branch used `isinstance(other, SpanKind): return self is other` — `isinstance` matches subclasses while every generated bridge uses exact-type `type(other) is type(self)`; latent asymmetry, and no AC-7 reflected-order test covers `SpanKind`.
Diff (`terminalsrc.py:18-19`): same-type branch now `if type(other) is type(self): return self.name == other.name`, structurally matching the generated `_emit_cross_backend_eq_hash` pattern (`gsm2tree.py:121`). Full `NotImplemented` fallback and canonical-name `__hash__` present (`:23,26`).
Assessment: divergence eliminated; matches generated shape. (Reviewer's secondary note — no SpanKind reflected-order test — is a coverage observation, not part of this finding's required change; test reviewer did not file it as blocking.) Accept.

### quality-2 — Fixed
Claim: module-scope `pytest.importorskip("fegen_rust_cst")` silently skipped all ~47 tests when the optional `fegen_rust_cst` build is absent, including ~40 with no dependency on it — core correctness (fltk2gsm cleanliness, Span equality, protocol runtime values) unexercised in default CI.
Diff (`:45-56`): `try/except ImportError` sets `fegen_rust_cst = None`, `_FEGEN_RUST_CST_AVAILABLE = False`; `_FEGEN_RUST_CST_SKIP = pytest.mark.skipif(...)` applied per-test only to the ~7 tests that reference `fegen_rust_cst` (grep confirms the mark on `:333,428,445,461,485,512,730`). Unconditional tests now run without the optional build.
Assessment: matches the reviewer's prescribed fix (per-test/per-class gating, not module-scope skip). Accept.

## Disputed items

None. All Fixed dispositions verified against the diff at the named lines; both Won't-Do/TODO dispositions sound; both TODOs pass the YES/YES rubric and are individually justified (not a scope-failure pile — two distinct, design-requiring items sharing one root cause).

## Approved

11 findings: 7 Fixed verified (errhandling-1, errhandling-2, test-1, test-2, test-3, test-4, reuse-2, quality-2 — 8 Fixed), 1 Won't-Do sound (errhandling-3), 2 TODOs acceptable (protocol-label-member-bridge-unify covering reuse-1/quality-1; protocol-label-member-private covering quality-3).

Recount: 8 Fixed + 1 Won't-Do + 2 TODO-backed (reuse-1/quality-1/quality-3) = all 11 disposition entries accounted for.

---

## Verdict: APPROVED

All dispositions acceptable. Fixes land at the named lines and address the stated consequences; the single Won't-Do is the reviewer's own informational close confirmed against the locked equality contract; both TODOs answer YES to both rubric questions (worth doing; require a deliberate public-API / bridge-unification design decision) and are surfaced, not silently deferred.
