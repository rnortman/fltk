# Efficiency Review — Phase 2 Nested Enum PoC

Commit reviewed: 5ee6eb4 (base 0f9b786)
Scope: `src/cst_poc.rs`, `src/lib.rs`, `tests/test_rust_cst_poc.py`.

Context note: the design scopes this as a standalone PoC not wired into any
production path, so none of these costs bite *today*. They matter because
`TODO(rust-cst-macro)` (cst_poc.rs:1) states this code is the template Phase 3
code generation will target. Every per-construction / per-access cost below
gets multiplied across every generated node type and every parse. Findings are
framed as "fix before the pattern is generalized," not "fix now."

---

## efficiency-1

- File: `src/cst_poc.rs:80-82`, `:249-251` (`Identifier::new`, `Items::new`).
- Problem: `new()` calls `py.import("fltk._native")?` then `.getattr("UnknownSpan")?`
  on every no-arg construction. `py.import` is a dict lookup in `sys.modules`
  (cached, so not a re-import) plus a `getattr` — two Python-level attribute
  operations per node built without an explicit span.
- Consequence: Per-node construction cost. In a real parser every node is
  constructed at least once, and the parser pattern in the design
  (`Identifier(span=Span(...))`) usually passes a span — but inline/intermediate
  nodes and any default-span construction pay this. At parse scale (one node per
  grammar match) this is a per-allocation tax on the hot path the generated code
  will inherit.
- Fix/direction: Cache the `UnknownSpan` object once. Options: store a
  `GILOnceCell<PyObject>` module-level and clone_ref the cached handle; or
  construct the default span as a native value directly (the design rejected
  this for the equality guarantee, but `UnknownSpan` is a singleton `Span` —
  holding one cached `Py<Span>` and cloning the reference preserves both
  equality and identity without the import+getattr each call).

## efficiency-2

- File: `src/cst_poc.rs:139-148`, `:309-318`, `:381-390`, `:453-462`, `:525-534`
  (`extend_<label>`), and generic `extend` at `:104-119`, `:274-289`.
- Problem: The label object is rebuilt inside the per-element loop. `extend_name`
  calls `Identifier_Label::Name.into_pyobject(py)?` once per iteration
  (line 143); the generic `extend` calls `label_val.clone_ref(py)` per iteration
  (line 115). For the per-label variants the label is loop-invariant — a fresh
  Python enum object is materialized for every child.
- Consequence: Per-child allocation cost during `extend`. Extending with N
  children does N label materializations instead of 1. In a parser, repetition
  rules (`+`/`*`) funnel through extend, so this scales with input size and
  carries into generated code.
- Fix/direction: Hoist the `into_pyobject` call above the loop and `clone_ref`
  the bound handle per iteration (same as the generic path already does for its
  label), or reuse the single bound object directly since `PyTuple::new` only
  borrows it.

## efficiency-3

- File: `src/cst_poc.rs:150-202` (`children_name`/`child_name`/`maybe_name`) and
  the 4×3 `Items` equivalents (`:320-372`, `:392-444`, `:464-516`, `:536-588`).
- Problem: Each accessor iterates the full `children` list and compares every
  tuple's label via `tup.get_item(0)?.eq(&label_obj)?` — a full Python
  `PyObject_RichCompare` against a `#[pyclass(eq)]` enum per element. PyO3's
  generated enum `__eq__` does a `downcast` + discriminant compare; invoked
  through the Python richcompare protocol per child it is materially heavier
  than a Rust-side discriminant match. `child_name`/`maybe_name` also keep
  scanning to the end after finding/exceeding the target count to compute the
  full count for the error message.
- Consequence: Per-query cost, O(children) Python-level comparisons each call.
  CST consumers (unparser, fltk2gsm at the call sites cited in the design)
  call these accessors repeatedly while walking the tree — every label-filtered
  access re-pays a full Python-compare scan. Multiplied across node types and
  tree size in generated code.
- Fix/direction: Two levers. (a) Avoid the Python richcompare: extract the
  stored label back to the Rust enum (or compare discriminants) instead of
  `PyAny::eq`. (b) `child_*` can stop scanning once `count == 2` (it already
  knows it will raise); `maybe_*` can stop at `count == 2`. The "have N" in the
  error message would then become "have at least 2" — acceptable, or compute the
  exact count only on the cold error path.

## efficiency-4

- File: `src/cst_poc.rs:204-215`, `:590-601` (`__eq__`).
- Problem: Not a defect — note only. `__eq__` delegates span and children
  comparison to Python `==` (`PyAny::eq`), which is the right call for
  correctness and avoids reimplementing recursive comparison. No change needed;
  flagged so a reader doesn't "optimize" it into a manual element loop that would
  be slower and buggier.

---

No other findings. The duplication between `Identifier` and `Items` is a
maintenance concern already captured by `TODO(rust-cst-macro)`, not an
efficiency one.
