Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 5ee6eb4. Revision commit: 6a0553c.

---

## errhandling-1

- Disposition: TODO(cst-unwrap-diagnostic)
- Action: Added `// TODO(cst-unwrap-diagnostic)` comment at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`. The `found.unwrap()` calls in all `child_*` methods are logically safe today (guarded by `count != 1` check immediately before). Deferring to avoid churn before Phase 3 macro extraction supersedes all of this code.
- Severity assessment: Latent only; if the `count`/`found` invariant breaks in a future edit the panic message is non-diagnostic. No production impact now since this is a standalone PoC.

---

## errhandling-2

- Disposition: TODO(cst-constructor-import-context)
- Action: Added `// TODO(cst-constructor-import-context)` comment at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`. The per-call `py.import("fltk._native")` in `new()` also overlaps with efficiency-1; both are addressed by `TODO(cst-unknown-span-cache)` which eliminates the import entirely.
- Severity assessment: If `fltk._native` is unavailable, `Identifier()` raises a bare `ImportError` with no constructor context. Confusing but rare; not a production path in Phase 2.

---

## errhandling-3

- Disposition: TODO(cst-downcast-context)
- Action: Added `// TODO(cst-downcast-context)` comment at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`.
- Severity assessment: A corrupted `children` list (non-tuple elements) surfaces a terse PyO3 downcast error with no node type, method name, or index. Diagnosable by traceback but slow to root-cause in production.

---

## correctness (no findings)

No action required. All correctness trace notes confirmed by code reading.

---

## security (no findings)

No action required.

---

## test-1

- Disposition: Fixed
- Action: `tests/test_rust_cst_poc.py:83` — added `assert not isinstance(result, tuple)` to `test_append_name_and_child_name`. If `child_name()` were changed to return the full `(label, child)` tuple, this assertion catches it.
- Severity assessment: Without the fix, a refactor changing `child_name()` to return the tuple would silently pass since `Span != tuple` anyway, but the intent of the test would not be enforced.

---

## test-2

- Disposition: Fixed
- Action: `tests/test_rust_cst_poc.py` — added `TestItemsMethods::test_cross_label_filtering`. Appends ITEM, NO_WS, ITEM, WS_ALLOWED children to an Items node and asserts each `children_*` returns only its own label's children and `children_ws_required()` returns empty.
- Severity assessment: Without this test, a bug where `children_item()` returned all children regardless of label would pass the entire `TestItemsMethods` suite.

---

## test-3

- Disposition: Won't-Do
- Action: No change. Reviewer self-corrected: `tup == (Identifier.Label.NAME, s)` via Python tuple equality already verifies index 0 is the label and index 1 is the value. No additional assertion needed.
- Rationale: The reviewer found no defect and withdrew the finding. The existing assertion is adequate.

---

## test-4

- Disposition: Fixed
- Action: `tests/test_rust_cst_poc.py` — added `TestLabelSemantics::test_label_not_equal_none`. Directly asserts `Identifier.Label.NAME != None` and `(Identifier.Label.NAME == None) is False`, explicitly documenting the PyO3 cross-type `__richcmp__` contract that the None-label filtering relies on.
- Severity assessment: Without this test, a PyO3 version that changed `NotImplemented` → exception for cross-type comparison would break `children_name` filtering; the change might not be caught until AC-27 test data happened to mix None-labeled and non-None-labeled children in a revealing way.

---

## test-5

- Disposition: Fixed
- Action: `tests/test_rust_cst_poc.py` — added `TestEquality::test_not_equal_cross_type`. Asserts `Identifier() != Items()`, `Identifier() != "string"`, `Identifier() != None`, `Identifier() != 42`.
- Severity assessment: Without this, a bug in `__eq__` (e.g., `is_instance_of::<Items>()` returning `True`) causing `Identifier() == Items()` would go undetected.

---

## test-6

- Disposition: Fixed
- Action: `tests/test_rust_cst_poc.py` — added `TestSpanField::test_span_keyword_construction_stores_provided_span`. Constructs `Identifier(span=s)` and asserts `node.span == s` and `node.span is not UnknownSpan`.
- Severity assessment: The parser uses `Identifier(span=Span(start=pos, end=-1))` as its primary construction pattern. A bug where the keyword argument was silently ignored would not be caught by the pre-existing setter test (AC-21) or default test (AC-22).

---

## reuse-1

- Disposition: TODO(rust-cst-macro)
- Action: Existing `TODO(rust-cst-macro)` at `src/cst_poc.rs:1` and `TODO.md` already covers extraction of per-label boilerplate including the filter loop. No new TODO added.
- Severity assessment: 10 loop copies across this file; all phase 3 generated nodes inherit. Acceptable for a PoC explicitly scoped as template material pending macro extraction.

---

## reuse-2

- Disposition: TODO(rust-cst-macro)
- Action: Covered by existing `TODO(rust-cst-macro)`. The constructor body duplication (`make_node_span` free function) would be addressed as part of macro extraction.
- Severity assessment: Two copies now; N copies in Phase 3. No production impact today.

---

## reuse-3

- Disposition: TODO(rust-cst-macro)
- Action: Covered by existing `TODO(rust-cst-macro)`. `__eq__`/`__hash__`/`__repr__` per-node duplication is explicitly part of the boilerplate the macro will replace.
- Severity assessment: Same as reuse-2. The hardcoded class name in `__hash__` error message is a rename hazard, noted in TODO.

---

## reuse-4

- Disposition: TODO(cst-generator-vs-list)
- Action: Added `// TODO(cst-generator-vs-list)` at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`. The divergence from `gsm2tree.py`'s `Iterator` return is intentional per design ("deliberate simplification") but must be resolved before Phase 3.
- Severity assessment: Call sites using `isinstance(result, list)` or generator exhaustion will break silently when switching from Python to Rust nodes. Deferred correctly — this is a Phase 3 design decision.

---

## quality-1 / efficiency-2

- Disposition: Fixed
- Action: Hoisted `into_pyobject(py)?.into_any().unbind()` before the loop in all five `extend_<label>` methods (`extend_name`, `extend_item`, `extend_no_ws`, `extend_ws_allowed`, `extend_ws_required`). Per-iteration now uses `label.bind(py).clone()` matching the generic `extend` pattern. `src/cst_poc.rs:139-148`, `309-318`, `381-390`, `453-462`, `525-534`.
- Severity assessment: N label object allocations per extend call instead of 1. In a real parser, `extend_*` on repetition rules scales with input size. This was a template bug; the fix propagates to all Phase 3 generated `extend_<label>` methods.

---

## quality-2

- Disposition: TODO(rust-cst-macro)
- Action: The `filter_by_label` helper extraction falls within the scope of the existing `TODO(rust-cst-macro)`. A proc-macro or generic helper would generate `child_*` and `maybe_*` from the same template, eliminating the loop duplication without a separate free function that stays outside the `#[pymethod]` surface.
- Severity assessment: 10 loop copies; any loop body change (e.g., early exit at count==2) must be applied to all. Acceptable for Phase 2 PoC; must be resolved before Phase 3 generation.

---

## efficiency-1

- Disposition: TODO(cst-unknown-span-cache)
- Action: Added `// TODO(cst-unknown-span-cache)` at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`. Also addresses errhandling-2 by eliminating the import entirely.
- Severity assessment: Per-node Python attribute lookup on the construction hot path. Phase 3 generated code with N node types each constructed per grammar match pays this tax at parse scale.

---

## efficiency-3

- Disposition: TODO(cst-accessor-early-exit)
- Action: Added `// TODO(cst-accessor-early-exit)` at `src/cst_poc.rs` top-of-file block and entry in `TODO.md`.
- Severity assessment: Full O(children) scan per `child_*`/`maybe_*` call even when the error is known at count==2. CST consumers call these accessors while walking the full tree; cost multiplies across nodes and parse size. Phase 3 inherits.

---

## efficiency-4

- Disposition: Won't-Do
- Action: No change. Reviewer noted this as "not a defect" and explicitly requested no action.
- Rationale: `__eq__` delegation to Python `==` is correct and avoids reimplementing recursive comparison. Any manual element loop would be slower and buggier per the reviewer's own note.
