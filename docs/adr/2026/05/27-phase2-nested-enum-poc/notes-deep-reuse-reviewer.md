Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## reuse-1: `child_name`/`maybe_name` inline the filter loop that `children_name` already contains

**File:line**: `src/cst_poc.rs:168-208` (`child_name`, `maybe_name`); existing: `children_name` at line 156.

**What's duplicated**: Both `child_name` and `maybe_name` replicate the full label-filter loop — `into_pyobject`, iterate, `downcast::<PyTuple>`, `tup.get_item(0)?.eq(...)`, accumulate — that `children_name` already performs. The design doc explicitly acknowledges this: "Inline the filter logic rather than calling `children_name`, avoiding an unnecessary list allocation." The rationale is valid for the PoC, but the loop body (5–9 lines) is copied verbatim four more times for the other three labels in `Items`.

**Existing utility**: `children_name` at `src/cst_poc.rs:156`; same pattern repeated across `children_item`, `children_no_ws`, `children_ws_allowed`, `children_ws_required`.

**Consequence**: The filter loop is now duplicated 10 times across the two node types (5 labels × 2 `child_`/`maybe_` variants each). When Phase 3 generates N node types, this becomes N×labels×2 copies. If the iteration idiom changes (e.g., switching from `downcast::<PyTuple>` to a typed iterator, or adding a short-circuit on first mismatch), every copy must change independently. The TODO(rust-cst-macro) at line 1 calls this out for eventual macro extraction, but in the meantime the PoC already shows the divergence cost: `children_name` collects into `PyList`; `child_name`/`maybe_name` accumulate into `Option<PyObject>` with a separate count — these are semantically compatible but structurally distinct, so a future reader cannot easily confirm they stay in sync.

---

## reuse-2: `new` constructor body duplicated verbatim between `Identifier` and `Items`

**File:line**: `src/cst_poc.rs:82-94` (`Identifier::new`) and `src/cst_poc.rs:252-264` (`Items::new`).

**What's duplicated**: Both constructors are identical except for the struct literal name (`Identifier { … }` vs `Items { … }`). The `UnknownSpan` import path, the `match span { … }` block, and `PyList::empty(py).unbind()` are copied byte-for-byte.

**Existing utility**: `Identifier::new` at `src/cst_poc.rs:82`. No shared helper exists.

**Consequence**: If the `UnknownSpan` default acquisition changes (e.g., caching the import, or the module path changes), both constructors must be updated. In Phase 3, N generated node types means N copies. A free function `fn make_node_span(py: Python<'_>, span: Option<PyObject>) -> PyResult<PyObject>` would eliminate the duplication with no API impact.

---

## reuse-3: `__eq__` / `__hash__` / `__repr__` duplicated between `Identifier` and `Items`

**File:line**: `src/cst_poc.rs:210-233` (`Identifier`) and `src/cst_poc.rs:596-619` (`Items`).

**What's duplicated**: `__eq__` structure is identical — type guard via `is_instance_of`, `PyRef` extraction, delegate `span` then `children` equality. `__hash__` differs only in the error-message string `'Identifier'` vs `'Items'`. `__repr__` differs only in the format string prefix.

**Existing utility**: `Identifier`'s implementations at the lines above. No shared helper exists.

**Consequence**: Same as reuse-2: N-node Phase 3 blows this up to N copies. The `__hash__` error message embeds the class name as a string literal rather than using `type_name::<Self>()` or `py.get_type::<Self>().name()`, so a rename requires grep-level surgery. A macro or generic helper (already called for by TODO(rust-cst-macro)) would close all three of these findings simultaneously.

---

## reuse-4: Python `children_*` returns generator; Rust `children_*` returns list — semantic divergence from generated Python counterpart

**File:line**: `src/cst_poc.rs:156-166` (`children_name` returns `Py<PyList>`); counterpart: `fltk/fegen/gsm2tree.py:189-204` generates `children_rule` returning `typing.Iterator[…]` (a generator expression). Also `fltk/fegen/fltk_cst.py:34` (generated output showing `children_rule() -> Iterator`).

**What's duplicated / diverged**: The Rust PoC intentionally returns a list rather than a generator ("deliberate simplification," design doc §Per-Label Methods). The Python-generated accessor returns a lazy generator. These are the same logical operation — filter children by label — on the same data structure, now implemented with different return types in two languages.

**Consequence**: Call sites that are currently written to consume the generator (e.g., `list(node.children_rule())`, `for x in node.children_rule()`) will silently work with both, but call sites that test `isinstance(result, list)` or depend on generator exhaustion will break when switching from Python to Rust nodes. The divergence is intentional for Phase 2 but must be resolved before Phase 3 generates production Rust nodes that are used alongside existing Python call sites. If it isn't explicitly addressed in the Phase 3 design, the mismatch will be discovered at integration time rather than design time.
