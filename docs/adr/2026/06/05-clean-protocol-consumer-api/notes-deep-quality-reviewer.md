# Quality Review: clean-protocol-consumer-api

Commit range: 1e78b73..bc42280

---

## quality-1

**File:line:** `fltk/fegen/gsm2tree.py:434–461` vs `fltk/fegen/pyrt/terminalsrc.py:8–26`

**Issue: Three copy-paste implementations of the cross-backend bridge pattern with no shared source.**

The bridge (`_fltk_canonical_name`, `__eq__` with `NotImplemented` fallback, `__hash__`) is implemented three times: (1) `_emit_cross_backend_eq_hash` in `gsm2tree.py`, which emits it via the `pygen` AST builder for `NodeKind`/`Label` enums; (2) `_emit_protocol_label_member_class` in `gsm2tree.py`, which emits the identical logic as a raw `ast.parse()` string for `_ProtocolLabelMember`; (3) `SpanKind` hand-written directly in `terminalsrc.py`. None of these call or reference the others' implementation. The docstring on `_emit_protocol_label_member_class` says it matches "the shape in `_emit_cross_backend_eq_hash`" but does not enforce it.

Additionally, `SpanKind.__eq__` uses `isinstance(other, SpanKind): return self is other` for the same-type branch, while the generated pattern uses `type(other) is type(self): return self.name == other.name`. These are semantically different (subclass vs exact-type; identity vs name comparison) and will silently diverge if either path is updated.

**Consequence:** Any future change to the bridge contract (e.g. adding a new short-circuit, changing the fallback) must be applied in all three places independently. The docstring coupling note is invisible to someone editing `terminalsrc.py`. The `isinstance`/identity divergence in `SpanKind` will silently produce different behavior if a future `SpanKind` gets multiple members or if the pattern is copy-pasted to another hand-written class.

**Fix:** Unify. Option A: make `_emit_protocol_label_member_class` call `_emit_cross_backend_eq_hash` by building a throwaway `ast.ClassDef` and extracting the body, or (simpler) replace the raw `ast.parse()` string with `pygen` builder calls matching `_emit_cross_backend_eq_hash` exactly. Option B: factor the bridge `__eq__`/`__hash__` bodies into a shared helper function in `terminalsrc.py` (or a new `fltk.fegen.pyrt.bridge` module) that all three sites import, so editing the bridge in one place propagates everywhere. Also: align `SpanKind.__eq__` same-type branch to use `type(other) is type(self): return self is other` to match the generated pattern structurally.

---

## quality-2

**File:line:** `tests/test_clean_protocol_consumer_api.py:43–46`

**Issue: `pytest.importorskip("fegen_rust_cst")` at module scope silently skips all 47 tests when `fegen_rust_cst` is absent, including ~40 tests that have no dependency on it.**

Only ~7 tests actually reference `fegen_rust_cst` directly (e.g. `test_nodekind_proto_eq_rust_external`, `test_fltk2gsm_behavioral_equivalence`, `test_nodekind_hash_consistent`). The remaining tests cover pyright/ruff cleanliness of the shapes fixture, `fltk2gsm.py` static checks, protocol `Label`/`NodeKind` runtime values, `Span` equality/hash invariants, and `SpanKind` canonical strings — none of which require `fegen_rust_cst`. These tests all become silently absent from CI runs on the base configuration (where `make build-fegen-rust-cst` has not been run), providing no coverage for the core correctness properties that the design depends on.

**Consequence:** The tests most likely to run (no special build step needed) are the ones most likely to be skipped. The basic `fltk2gsm.py` cleanliness tests, `Span` equality regression tests, and protocol runtime-value tests will go unexercised in CI until `fegen_rust_cst` is built, which is an optional step. Any regression in these areas is silent.

**Fix:** Move the `fegen_rust_cst` importorskip to a module-level fixture or marker applied only to the test functions/classes that actually use `fegen_rust_cst`. Use `pytest.importorskip` inside a `@pytest.fixture` or at the top of the specific class bodies, or add a `@pytest.mark.skipif` on the individual tests/classes that reference `fegen_rust_cst`. Tests that only use `embedded_rust_cst` (always available as `fltk._native.fegen_cst`) or pure-Python infrastructure should never be gated on `fegen_rust_cst`.

---

## quality-3

**File:line:** `fltk/fegen/fltk_cst_protocol.py:57–77` (generated); `fltk/fegen/gsm2tree.py:443–461`

**Issue: `_ProtocolLabelMember` is a module-level class in the generated public protocol module with no `__all__` exclusion or naming convention beyond the leading underscore.**

The class appears in the module body and is visible to `from fltk_cst_protocol import *` and to IDE auto-complete. The test `test_protocol_module_has_one_class_per_rule` explicitly adds `"_ProtocolLabelMember"` to the expected class set (line 113), treating it as a permanent expected inhabitant of the generated module. Since `fltk_cst_protocol.py` is public API for out-of-tree consumers (CLAUDE.md), downstream code could accidentally depend on `_ProtocolLabelMember` — for example by introspecting label member types or using it in `isinstance` checks. Once any downstream code takes a dependency on it, it becomes a de-facto public symbol subject to the breaking-change rules.

**Consequence:** An implementation detail meant for internal use (backing runtime values for `Label` members) leaks into a public-API module with no enforcement mechanism to prevent downstream coupling. If the sentinel class ever needs to change (e.g. to merge with `_emit_cross_backend_eq_hash`), removing it from the generated output or changing its behavior will be a breaking change for any consumer that touched it.

**Fix:** Either (a) emit a module-level `__all__` in the generated protocol module listing only the intended public names (`NodeKind`, `SpanKind`, the Protocol classes), which suppresses `_ProtocolLabelMember` from `import *` and makes the boundary explicit; or (b) move the implementation to a non-generated shared module (e.g. `fltk.fegen.pyrt.bridge`) imported by the generated protocol module, keeping the implementation out of the public API file entirely. The `test_protocol_module_has_one_class_per_rule` whitelist update (adding `_ProtocolLabelMember`) should also be reconsidered: if it's an internal detail, the test should not assert its presence by name.
