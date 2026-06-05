# Dispositions — Deep Review Round 1

Commit reviewed: 854e1ad..c57f888. Fixes applied at: 9d6f9a0. Rework applied at: 0c4093d.

---

## error-handling

No findings.

---

## correctness

No findings.

---

## security

No findings.

---

## test-1

- Disposition: Fixed
- Action: `tests/test_cross_backend_label_equality.py:223-238` — `TestNodeKindCrossBackend.test_no_raise_on_unrelated` now loops over `[None, 1, "NodeKind.ITEMS", object(), _label(b_key, "Items", "NO_WS")]`, checks both `kind == other` and `other == kind` (symmetric), and asserts both `== False` and `!= True` for all operands.
- Severity assessment: The missing symmetric direction would have failed to detect a bug in the reflected `__eq__` path on `NodeKind` — the path the design §3.2 identifies as critical for correctness when both sides return `NotImplemented`.

---

## test-2

- Disposition: Fixed
- Action: `tests/test_cross_backend_label_equality.py:126-143` — added `_label(b_key, "Disposition", "INCLUDE")` (note `b_key`) to the `unrelated` list, exercising the cross-backend cross-class canonical-name path.
- Severity assessment: A malformed Rust `_fltk_canonical_name` for a non-`Items` label class would not have been detected in the unequal direction.

---

## test-3

- Disposition: Fixed
- Action: `tests/test_cross_backend_label_equality.py:95-110` — added hash checks for `Disposition.Label.INCLUDE` and `Disposition.Label.SUPPRESS` across backends.
- Severity assessment: A `__repr__`/`__hash__` bug on any label class other than `Items` would not have been caught; the set-collapse and membership tests also only used `Items`.

---

## test-4

- Disposition: Fixed
- Action: `tests/test_cross_backend_label_equality.py:211-233` — added assertion that `NodeKind.ITEM` and `Items.Label.ITEM` (same word in both families) have distinct canonical strings and compare unequal, pinning the family-disjointness guarantee for the precise dangerous case.
- Severity assessment: A generator bug emitting `NodeKind.ITEM` with canonical name `"Items.Label.ITEM"` (using the Label format) would have passed the original test because it compared `ITEMS` vs `NO_WS`, where the strings differ regardless of the format.

---

## test-5

- Disposition: Fixed
- Action: `tests/test_cross_backend_label_equality.py:231-281` — new `TestMarkerScope` class with 5 tests: `_fltk_canonical_name` absent from Python, Rust, and embedded-Rust `Items()` nodes; `Items() != Items.Label.ITEM` for same-backend and cross-backend cases.
- Severity assessment: Without this test, a generator change accidentally emitting `_fltk_canonical_name` on node structs would silently break `node == label` — it could return `True` if canonical strings coincided, and no existing test would catch the regression.

---

## test-6

- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:640-658` — replaced global `#[getter]` count assertion with a text-proximity check: walks source lines to find `fn kind(&self) -> NodeKind {`, then walks backward over blank lines and asserts `#[getter]` appears on the immediately preceding non-blank line.
- Severity assessment: The old count test was structurally vacuous for its stated purpose — it passed even if `#[getter]` was removed from the `kind` function specifically, as long as other `#[getter]` annotations existed elsewhere. A regression removing the getter attribute on `kind` would silently break Python-side `node.kind` access.

---

## test-7

- Disposition: Fixed
- Action: `fltk/test_plumbing.py:583` — replaced rule-name-only loop with `assert grammar_default == grammar_baseline` (full structural equality), matching the pattern in `TestAC8RealCst2GsmRustBackend`.
- Severity assessment: A regression in `self.cst` removal that broke disposition or quantifier mapping (e.g. `visit_disposition` returning wrong values) would not have been caught; rule names would still match.

---

## reuse-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:99-125` — extracted `_emit_cross_backend_eq_hash(enum_klass)` static method that emits a bare `_fltk_canonical_name: str` annotation plus `__eq__` and `__hash__` body. Both `_node_kind_enum` and `py_class_for_model` Label emit now call this shared helper. TODO entry and TODO comments removed.
- Severity assessment: A contract fix (e.g. `NotImplemented` path) now needs to be applied in one place only; the two-copy divergence surface is eliminated.

---

## reuse-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:150-184` — extracted `_emit_rust_cross_backend_eq_hash(lines, type_name)` static method appending the 10-line eq/hash pymethod block with `type_name` as the only parameter. Both `_node_kind_block` and `_label_enum_block` now call this helper. TODO entry and TODO comments removed.
- Severity assessment: Same maintenance improvement as reuse-1 on the Rust-emission side.

---

## quality-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:195` — `py_class_for_model` signature gains `rule_name: str = ""` parameter; `kind_member = self.node_kind_member_name(rule_name) if rule_name else class_name.upper()` routes through the defined abstraction. The sole caller (`gen_py_module:145`) now passes `rule` as the third argument. Regenerated `fltk_cst.py`.
- Severity assessment: Without this fix, a change to `node_kind_member_name` (e.g. handling rule names with digits differently) would cause concrete-class `kind` fields to diverge from Protocol `kind` annotations — a pyright error at downstream call sites, not a test failure, and silent until someone runs pyright.

---

## quality-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py:160` — removed `lines.append("#[allow(non_camel_case_types)]")` from `_node_kind_block`. Regenerated `src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs`.
- Severity assessment: The suppression was suppressing a warning that can never fire on `NodeKind` (all variants are CamelCase), and would silently hide future naming regressions on `NodeKind` variants.

---

## quality-3

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:447` — `_protocol_class_for_model(self, class_name, model, rule_name: str)` — default removed; parameter is now required. All callers already passed it. Regenerated `fltk_cst_protocol.py`.
- Severity assessment: The empty-string default created a silent `kind: object` fallback reachable from any future call without the argument — a Protocol member that pyright cannot narrow on, with no error at call time.

---

## quality-4

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:424-436` — `gen_protocol_module` now emits `if typing.TYPE_CHECKING:\n    from {concrete_module} import NodeKind` (an `ast.If` node) instead of a bare import. Regenerated `fltk_cst_protocol.py` — the file now carries the guarded import. With `from __future__ import annotations` present, `Literal[NodeKind.X]` annotations are lazy strings; no runtime `NodeKind` resolution is needed.
- Severity assessment: The bare import coupled every Protocol module consumer to the concrete Python CST module at runtime; in pure-Rust deployments where the generated Python CST is absent, Protocol module import would fail.

---

## efficiency-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree.py:138-165` — `_emit_node_kind_canonical_name_assignments` and `_emit_label_canonical_name_assignments` emit post-class statements that assign `_fltk_canonical_name` as a plain string attribute on each enum member after class construction. The `@property` is removed from the generated class body; `_emit_cross_backend_eq_hash` emits a bare `_fltk_canonical_name: str` annotation instead (for pyright). `gen_py_module` emits NodeKind assignments immediately after the `NodeKind` class; `py_class_for_model` (now returning `list[ast.stmt]`) appends Label assignments after each dataclass. Regenerated `fltk_cst.py`. `__hash__` now reads a pre-computed string with no per-call allocation, restoring cheap same-backend hashing. TODO entry updated to Rust-only.
- Severity assessment: The same-backend `__hash__` regression (per-call f-string rebuild vs. prior identity hash) is fixed; hash cost is now a simple str lookup from a pre-assigned attribute.

---

## efficiency-2

- Disposition: TODO(canonical-name-cache)
- Action: TODO comment retained in `_emit_rust_cross_backend_eq_hash` docstring at `fltk/fegen/gsm2tree_rs.py:151`. `TODO.md` entry updated to Rust-only scope. Python side fixed under efficiency-1.
- Severity assessment: The Rust `__hash__` still allocates a fresh `PyString` per call because CPython's salted hash is load-bearing for cross-backend hash agreement (AC4); the allocation is correctness-constrained and cannot be removed without breaking AC4. Amortizing via `GILOnceCell<isize>` per variant requires no design cycle and is a standard PyO3 pattern, but the cost is only visible at volume for Rust-backend dict/set usage and no profiling-confirmed bottleneck exists yet. Deferred as the remaining correctness-constrained Rust cost.

---

## efficiency-3

- Disposition: TODO(kind-field-dataclass-eq)
- Action: TODO comment at `fltk/fegen/gsm2tree.py:196`. Entry in `TODO.md`.
- Severity assessment: The `kind` field is invariant within a node type so its inclusion in dataclass `__eq__` is pure overhead; cost is minimal (same singleton, `other is self` fast path) and only matters if node-equality is on a hot path.
