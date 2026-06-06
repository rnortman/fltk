# Dispositions: Deep Review — Clean Protocol-Only Consumer API

Reviewed: 1e78b73..bc42280. Fixes committed at HEAD (see response commit).

---

## errhandling-1

- Disposition: Fixed
- Action: Added diagnostic context messages to all five narrowing/invariant asserts in `fltk2gsm.visit_items`. Each assert now includes the actual value received and the child index. `fltk/fegen/fltk2gsm.py:56-86`.
- Severity assessment: Without messages, `AssertionError` on malformed CST input provides no signal about which child, which label, or which index was wrong. The fix makes invariant-violation diagnosis immediate.

---

## errhandling-2

- Disposition: Fixed
- Action: Replaced chained `?` propagation in `Span.kind` getter with `.map_err` that wraps the Python exception in a `PyValueError` with a context string identifying the import path and the bridge. `src/span.rs:261-278`.
- Severity assessment: Without wrapping, a broken deployment surfaces as an opaque `ModuleNotFoundError` from inside a `#[getter]` with no indication that the Rust→Python `SpanKind` bridge is the root cause. The context message names the cause directly.

---

## errhandling-3

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Duck-typed `__eq__` matching any object with the right `_fltk_canonical_name` attribute is the intentional cross-backend equality contract, present since the initial implementation. No new behavior introduced by this diff; the finding is informational.
- Rationale: The design doc (§1) explicitly states `_fltk_canonical_name` is duck-typed and the bridge `__eq__` is designed to compare on canonical strings regardless of object type. Changing this would break the cross-backend equality mechanism the entire feature depends on.

---

## test-1

- Disposition: Fixed
- Action: Added `assert "TYPE_CHECKING" not in code_text` to `test_shapes_fixture_no_forbidden_patterns`. `tests/test_clean_protocol_consumer_api.py:248`.
- Severity assessment: A regression reintroducing a `TYPE_CHECKING` shadow import in the shapes fixture would have passed all tests previously. This gating criterion violation would be undetected.

---

## test-2

- Disposition: Fixed
- Action: Split `test_nodekind_nonmatching_neq` — the embedded-only case stays in the base test; a new `@_FEGEN_RUST_CST_SKIP`-gated `test_nodekind_nonmatching_neq_rust_external` asserts `proto_kind != fegen_rust_cst.NodeKind.GRAMMAR` in both operand orders. `tests/test_clean_protocol_consumer_api.py:449-461`.
- Severity assessment: A broken `__eq__` returning `True` for cross-backend non-matching NodeKind members would pass the old test. The fix closes the gap for the external Rust backend.

---

## test-3

- Disposition: Fixed
- Action: Added `test_protocol_module_no_new_file_level_suppressions` that reads `PROTOCOL_MODULE_PATH`, asserts exactly one `# ruff: noqa` line (the pre-existing `N802`), and asserts no inline `# type: ignore` lines in the generated module. `tests/test_clean_protocol_consumer_api.py:312-331`. `PROTOCOL_MODULE_PATH` is now used.
- Severity assessment: A generator regression introducing a new file-level suppression into `fltk_cst_protocol.py` was previously undetected. The `terminalsrc.py` `# type: ignore[attr-defined]` is in a hand-written file and is correct; the test correctly scopes to the generated module only.

---

## test-4

- Disposition: Fixed
- Action: Added `test_rust_native_span_dispatches_via_match_case` that runs a full `match`/`case` dispatch against a standalone `RustSpan(1, 5)` instance, asserts the `cst.Span.kind` arm is taken, and asserts it does not fall through to `case _:`. `tests/test_clean_protocol_consumer_api.py:667-690`.
- Severity assessment: The AC 12 claim that `case cst.Span.kind:` matches a `fltk._native.Span` via match/case value-pattern dispatch was not previously exercised end-to-end through the dispatch mechanism. A bug in match/case evaluation order would have been missed.

---

## reuse-1

- Disposition: TODO(protocol-label-member-bridge-unify)
- Action: Added entry to `TODO.md` and `TODO(protocol-label-member-bridge-unify)` comment in `gsm2tree.py` docstring for `_emit_protocol_label_member_class`. `fltk/fegen/gsm2tree.py:443-460`. `TODO.md`.
- Severity assessment: Two independent implementations of the cross-backend bridge (`ast.parse` string vs. `pygen` builder) can drift. The divergence today is intentional (non-enum same-type fast path uses `_fltk_canonical_name` comparison, enum uses `.name`), but informal. Refactoring is non-trivial and correctness is currently guarded by the AC 7 cross-backend tests; deferred.

---

## reuse-2

- Disposition: Fixed
- Action: Changed `SpanKind.__eq__` same-type branch from `isinstance(other, SpanKind): return self is other` to `type(other) is type(self): return self.name == other.name` to match the generated bridge pattern exactly. `fltk/fegen/pyrt/terminalsrc.py:15-19`.
- Severity assessment: `isinstance` matches subclasses; the generated pattern uses exact-type comparison. The asymmetry was latent — `SpanKind` has no subclasses — but would cause divergent behavior if ever subclassed, and made code review harder by presenting a structural mismatch with no documented justification.

---

## quality-1

- Disposition: TODO(protocol-label-member-bridge-unify) (subsumes this finding — same root cause as reuse-1)
- Action: See reuse-1 disposition. The `SpanKind` alignment (reuse-2) is Fixed.
- Severity assessment: Same as reuse-1 for the duplication concern; the `isinstance` vs `type()` divergence is now fixed.

---

## quality-2

- Disposition: Fixed
- Action: Replaced module-scope `pytest.importorskip` with a try/except that sets `fegen_rust_cst = None` and `_FEGEN_RUST_CST_AVAILABLE = False` when absent, plus a `_FEGEN_RUST_CST_SKIP` mark applied per-test/per-method to the ~7 tests that actually reference `fegen_rust_cst` directly. The ~40 tests covering pyright/ruff cleanliness, `Span` equality, protocol runtime values, and embedded-Rust backend equality now run unconditionally. `tests/test_clean_protocol_consumer_api.py:42-56`.
- Severity assessment: Previously all 53 tests were silently absent in CI runs without the optional `make build-fegen-rust-cst` step, leaving core correctness properties (fltk2gsm cleanliness, Span equality, protocol import isolation) unexercised.

---

## quality-3

- Disposition: TODO(protocol-label-member-private)
- Action: Added entry to `TODO.md` and `TODO(protocol-label-member-private)` comment in `gsm2tree.py` docstring. `fltk/fegen/gsm2tree.py:435-460`. `TODO.md`.
- Severity assessment: `_ProtocolLabelMember` appears in the public protocol module and is visible to `import *` and IDE autocompletion. Downstream consumers could accidentally depend on it. The leading underscore provides informal-only protection. Moving it or suppressing it via `__all__` is the correct fix but requires generator changes; deferred.
