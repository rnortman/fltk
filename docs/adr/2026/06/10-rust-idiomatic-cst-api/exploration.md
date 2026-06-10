# Exploration: Rust-Idiomatic CST API

Token-dense fact survey for the designer. No recommendations. All claims anchored to code.

---

## Code Surface

### Generator

`fltk/fegen/gsm2tree_rs.py` — `RustCstGenerator` class, the sole source of generated Rust CST code.

Key methods and what they emit:

- `generate() -> str` (line 222): top-level orchestrator; calls `_preamble`, `_node_kind_block`, then per-rule `_label_enum_block` / `_child_enum_block` / `_node_block`, then `_register_classes_fn`.
- `_node_block` (line 530): emits the `pub struct NodeName` definition, `PartialEq`, `Clone`, a **plain `impl` block** (the Rust-only accessors), and a `#[cfg(feature = "python")] #[pymethods] impl` block.
- The **plain `impl` block** (lines 571–595) emits exactly three methods: `new_native`, `span_native`, `children_native`, `push_child_native`.
- The **pymethods block** (lines 600–625) emits: `new`, `span` getter/setter, `kind` getter, optionally `Label` classattr, `children` getter, `append`, `extend`, `extend_children`, `child`, then per-label quintet (`append_<lbl>`, `extend_<lbl>`, `children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`), then `__eq__`, `__hash__`, `__repr__`.

### Generated Output (representative sample)

`tests/rust_cst_fixture/src/cst.rs` and `tests/rust_cst_fegen/src/cst.rs` — hand-committed generated outputs. Both files are 2636 lines and identical in structure; the fixture grammar is a 6-rule config grammar, the fegen file is for fltk's own grammar.

`src/cst_generated.rs` and `src/cst_fegen.rs` — the in-tree committed Rust CST for the PoC grammar and the fegen grammar, registered into `fltk._native` (see `src/lib.rs:19-48`).

`crates/fltk-cst-spike/src/cst.rs` — hand-written spike CST for a 3-rule grammar (Identifier, Items, Trivia). Structurally identical to generated output; used as a proving ground.

### Core Library

`crates/fltk-cst-core/src/span.rs` — `Span` (24 bytes: two `i64` + one `Option<Arc<SourceInner>>`), `SourceText` (Arc wrapper), `SpanError`. Rust-native API: `Span::new_sourceless`, `Span::new_with_source`, `Span::unknown`, `.start()`, `.end()`, `.text()`, `.merge()`, `.intersect()`, `.has_source()`, `.len()`, `.is_empty()`. No `_native` suffix on any of these.

`crates/fltk-cst-core/src/cross_cdylib.rs` — cross-cdylib helpers, all `#[cfg(feature = "python")]`-gated: `extract_span`, `extract_source_text`, `span_to_pyobject`, `get_span_type`, `get_source_text_type`. These are implementation helpers, not user-facing API.

`crates/fltk-cst-core/src/lib.rs` — public re-exports. Under `python` feature: `extract_source_text`, `extract_span`, `get_source_text_type`, `get_span_type`, `span_to_pyobject`. Always: `SourceText`, `Span`, `SpanError`.

---

## The `_native` Suffix Problem: Exact Origin

The `_native` suffix appears on exactly **four** method names in each generated node struct, emitted by `gsm2tree_rs.py`'s `_node_block` method (lines 571–595):

```rust
pub fn new_native(span: Span) -> Self { ... }      // constructor
pub fn span_native(&self) -> &Span { ... }          // span accessor
pub fn children_native(&self) -> &[...] { ... }    // children slice
pub fn push_child_native(&mut self, ...) { ... }   // child appender
```

These are in the **unconditional** `impl NodeName` block (no `#[cfg]` gate). They exist because the same method names (`new`, `span`, `children`) are taken by the `#[pymethods]` block. The pymethods block's `fn new` is the pyo3 `#[new]` constructor; `fn span` is the `#[getter]` returning `PyObject`; `fn children` is the `#[getter]` returning `Py<PyList>`. Since pyo3 `#[pymethods]` and plain `impl` blocks coexist on the same struct, a name collision means the suffixed names were chosen to avoid the conflict.

The suffix is not in the preamble, child enums (`IdentifierChild`, etc.), label enums (`Identifier_Label`, etc.), or `NodeKind`. Only these four constructors/accessors carry it.

Evidence from tests: `tests/rust_cst_fixture/src/native_tests.rs:31,37,50,57,66,68` — all pure-Rust test code uses only the `_native`-suffixed methods. The tests call `new_native`, `span_native`, `children_native`, `push_child_native` exclusively for GIL-free construction and traversal.

---

## Dual-Layer Structure Per Node

Every generated node has two overlapping `impl` blocks on the same struct:

**Layer 1 — plain `impl`** (Rust-only, always compiled):
- `new_native(span: Span) -> Self`
- `span_native(&self) -> &Span`
- `children_native(&self) -> &[(Option<NodeName_Label>, NodeNameChild)]`
- `push_child_native(&mut self, label: Option<NodeName_Label>, child: NodeNameChild)`

**Layer 2 — `#[cfg(feature = "python")] #[pymethods]`** (Python-gated):
- `new(py, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self>` — takes Python span or None
- `span(&self, py) -> PyResult<PyObject>` — returns canonical `fltk._native.Span` via `span_to_pyobject`
- `set_span(&mut self, py, value: &Bound<'_, PyAny>) -> PyResult<()>` — accepts cross-cdylib spans via `extract_span`
- `kind(&self) -> NodeKind` — returns enum variant
- `Label(py) -> PyResult<PyObject>` — classattr returning label enum type
- `children(&self, py) -> PyResult<Py<PyList>>` — rebuilds list from native Vec on each call
- `append`, `extend`, `extend_children`, `child` — generic mutation/access
- `append_<lbl>`, `extend_<lbl>`, `children_<lbl>`, `child_<lbl>`, `maybe_<lbl>` — per-label quintet

The label enum `NodeName_Label` and child enum `NodeNameChild` are **unconditionally** compiled (no `#[cfg]` gate on the enum or `PartialEq`/`Clone` impls). Only the `#[pymethods]` impl block on `NodeNameChild` (containing `to_pyobject`/`extract_from_pyobject`) is gated: `#[cfg(feature = "python")] impl NodeNameChild { ... }`.

The `NodeKind` enum and `NodeName_Label` enums use a **dual-block pattern** (not `cfg_attr` on variants):
```rust
#[cfg(feature = "python")]
#[pyclass(frozen, name = "NodeKind")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum NodeKind { ... variants with #[pyo3(name = "...")] ... }

#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum NodeKind { ... same variants without pyo3 attrs ... }
```
This is required because pyo3 0.23 validates helper attributes before proc-macro expansion, making `cfg_attr` on enum variants with `#[pyo3(name=...)]` fail. `gsm2tree_rs.py:319-343`.

---

## Cargo Feature Architecture

`crates/fltk-cst-core/Cargo.toml:17-19`: `python` feature is **default-on** in the core crate. Depends on `pyo3 = { version = "0.23", ... optional = true }`.

`crates/fltk-cst-spike/Cargo.toml:13-15`: `python` feature is **default-off**. Enables `dep:pyo3` + `fltk-cst-core/python`. Consumer crates are expected to follow this pattern: depend on `fltk-cst-core` with `default-features = false`, and enable `python` only when building the Python extension.

Root `Cargo.toml:14-17`: the `fltk-native` cdylib has `default = ["extension-module"]`; `extension-module` implies `python` which implies `fltk-cst-core/python`. The root crate is always Python-on.

`crates/fltk-cst-spike/src/lib.rs:1`: `#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]` — the spike enforces that the python-off path is safe.

---

## pyo3 Boundary: How CST Nodes Cross Python/Rust

### Span crossing

`crates/fltk-cst-core/src/cross_cdylib.rs` contains the full machinery. The canonical Python `Span` type lives in `fltk._native`; consumer crates (out-of-tree cdylibs) register their own copy of `Span` via pyo3, which is a **different type object** from `fltk._native.Span` in Python's eyes.

`get_span_type(py)` (cross_cdylib.rs:179): imports `fltk._native.Span` and caches it in a `GILOnceCell`. All generated code calls this when receiving a span from Python.

`extract_span(py, obj)` (cross_cdylib.rs:147): tries `obj.extract::<Span>()` first (fast path: same cdylib), then falls back to `instanceof fltk._native.Span` + `downcast_unchecked` (slow path: cross-cdylib). The slow path is gated by an ABI marker check for `SourceText`; the `Span` path lacks that marker and is noted as a TODO (`crosscdylib-abi-sentinel`).

`span_to_pyobject(py, span)` (cross_cdylib.rs:113): fast path when `Span::type_object(py).is(&span_type)` (this IS `fltk._native`); slow path calls `_with_source_unchecked` on the canonical type.

### Node crossing

Generated node structs are `#[cfg_attr(feature = "python", pyclass)]`. They do **not** implement any marker protocol for cross-cdylib identity — unlike `Span`, which has the ABI-marker `_fltk_cst_core_abi` classattr. Each consumer cdylib registers its own copies of node types; there is no shared canonical type for nodes analogous to `fltk._native.Span`.

When a node is returned through a Python accessor (e.g. `children_name`), the node is **cloned**: `Py::new(py, (**n).clone())` (child enum `to_pyobject` in spike/cst.rs:526, fixture/cst.rs:530). This means:
- Each Python read of a child allocates a new pyo3 `PyCell` wrapping a clone of the native node.
- Python object identity (`is`) is not preserved across reads. This is tracked as `TODO(rust-cst-child-node-identity)` in TODO.md.

### extend_children across modules

`extend_children` takes `PyRef<'_, NodeName>` — this means it only accepts the **same cdylib's** registered `NodeName` type; a `NodeName` from another cdylib would fail the pyo3 downcast. There is no cross-cdylib `extend_children` equivalent.

---

## Current Rust Client-Facing API Shape

A pure Rust consumer (feature `python` off) using a generated crate currently sees **only**:

```rust
// Enums (unconditional)
NodeKind { Identifier, Items, Trivia }
Identifier_Label { Name }
Items_Label { Item, NoWs, WsAllowed, WsRequired }
IdentifierChild { Span(Span) }
ItemsChild { Span(Span), Identifier(Box<Identifier>), Trivia(Box<Trivia>) }

// Node structs with only the _native-suffixed API
impl Identifier {
    pub fn new_native(span: Span) -> Self
    pub fn span_native(&self) -> &Span
    pub fn children_native(&self) -> &[(Option<Identifier_Label>, IdentifierChild)]
    pub fn push_child_native(&mut self, label: Option<Identifier_Label>, child: IdentifierChild)
}
```

No accessors for individual labeled children exist in the Rust-only layer. The per-label quintet (`children_name`, `child_name`, `maybe_name`, etc.) exists **only** in `#[pymethods]`. A Rust-only consumer must manually iterate `children_native()` and match on labels.

The Python consumer sees: `new(span=...)`, `span` property, `children` property, `append`, `extend`, `extend_children`, `child`, per-label methods, `kind`, `Label`, `__eq__`, `__hash__`, `__repr__`. All Python-accessible methods are suffixless.

---

## Schemas / Contracts

### Node struct layout (invariant across all generated nodes)

```rust
pub struct NodeName {
    span: Span,                                          // private field
    children: Vec<(Option<NodeName_Label>, NodeNameChild)>,  // private field
}
```

### Child enum pattern

Leaf nodes (regex/literal terminals): `NodeNameChild { Span(Span) }`.
Non-leaf nodes: `NodeNameChild { Span(Span), ChildClass1(Box<ChildClass1>), ChildClass2(Box<ChildClass2>) }`.

### Label enum naming

Rust enum type: `NodeName_Label` (snake_case node name + `_Label`; `#[allow(non_camel_case_types)]`).
Rust variants: CamelCase of label (e.g. `no_ws` → `NoWs`). `gsm2tree_rs.py:21-23`.
Python-visible names: ALL_CAPS of label (e.g. `no_ws` → `NO_WS`). `gsm2tree_rs.py:26-28`.
`NodeKind` variants: same as class name (CamelCase), e.g. `NodeKind::Identifier`; Python-visible `"IDENTIFIER"`.

### NodeKind canonical string

`"NodeKind.CLASSNAME_UPPERCASED"` e.g. `"NodeKind.IDENTIFIER"`. Used for cross-backend equality via `_fltk_canonical_name` getter. `gsm2tree_rs.py:276-279`.

---

## Invariants and Constraints

**pyo3 `#[pymethods]` name collision with plain `impl`:** In pyo3, a `#[pymethods]` impl block and a plain `impl` block coexist on the same struct. Method names in `#[pymethods]` are Python-side names; Rust method names in the pymethods block also exist as Rust methods. If both blocks define `fn span`, there is a Rust name collision. The current design avoids this by using `_native` suffixes in the plain impl. (`span_native` vs `fn span` in pymethods at cst.rs:202, 234.)

**The `_native` suffix is not cosmetic — it is forced by name collision.** The pymethods block at span.rs:334–513 uses `py_new`, `py_text`, `py_has_source`, `py_len`, `py_is_empty`, `py_merge`, `py_intersect` as Rust-side names (with `#[pyo3(name = "...")]` to set Python names), avoiding the same collision. The generated node structs do not use this `#[pyo3(name = "...")]` technique on the pymethods; they use the natural name for the Python API (`fn span`, `fn children`, `fn new`) and suffix the native API.

**`Span` itself (cst-core) does NOT have `_native` suffixes.** Its Rust API (`start()`, `end()`, `text()`, `merge()`, `intersect()`, `has_source()`, `len()`, `is_empty()`, `new_sourceless()`, `new_with_source()`, `unknown()`) has no suffix. The Python-visible wrappers use `#[pyo3(name = "...")]` with a `py_` prefix on Rust method names where collision exists (e.g. `fn py_text` → Python `text`). `span.rs:380-462`. This is the pattern that exists in `cst-core` but was not applied when generating node structs.

**Clone on every Python boundary crossing:** Node children are stored as `Box<ChildNode>` in the native Vec. Every Python accessor call clones the boxed node to wrap it in a new `Py<ChildNode>`. `to_pyobject` in child enums: `Py::new(py, (**n).clone())`. This is structural and pervasive.

**No `Debug` derive on generated types.** Noted in spike_tests.rs:5-7: tests use `assert!` instead of `assert_eq!` because `Debug` is absent. The spike comment describes this as "a gap surfaced by the spike."

**`extend_children` is `PyRef`-bound:** The method signature `fn extend_children(&mut self, other: PyRef<'_, NodeName>)` means it only works within the same cdylib registration.

**`children` getter rebuilds on every call:** The `#[getter] fn children` always constructs a new `PyList` by iterating the native Vec. No caching. (gsm2tree_rs.py:682-700.)

---

## Forward Path: Toward Generated Rust Parsers

The existing generated CST is the foundation for a future generated Rust parser. Current scaffolding relevant to this:

`extend_children` (gsm2tree_rs.py:770-785): the docstring states it was added "for inline_to_parent items: instead of mutating the throwaway list returned by the `children` getter, the parser calls this method to transfer children from a sub-parser result into the parent node's native Vec." This is explicit parser-oriented API.

`push_child_native` (gsm2tree_rs.py:591-594): the unconditional mutation method a Rust parser would use to build the tree.

`new_native` (gsm2tree_rs.py:573-579): the GIL-free constructor a Rust parser would use.

The parser would need to construct nodes (`new_native`), push children (`push_child_native`), then either: (a) hold them as Rust values and return them to Python by wrapping in `Py::new`, or (b) in a pure-Rust scenario, pass them directly. The current API already supports (b) for the Rust-only path.

There is no Rust parser generator yet (`gsm2parser.py` at `fltk/fegen/gsm2parser.py` generates Python parsers only; there is no `gsm2parser_rs.py` analog).

---

## Open Factual Questions

1. **Do any out-of-tree consumers currently depend on the `_native`-suffixed API names?** If yes, renaming is breaking. If no in-tree usage and no known external consumers yet, the window to rename is open.

2. **Is `Identifier_Label` (the `NodeName_Label` naming) intentional for both Python and Rust?** Python sees `"Identifier_Label"` as the class name (set via `#[pyclass(frozen, name = "Identifier_Label")]`). Rust has `#[allow(non_camel_case_types)]` to suppress the lint. The Python-side attribute access path is `node.Label` (classattr) which returns the enum type, so Python consumers do not use `Identifier_Label` directly as a name. Rust consumers would pattern-match `Identifier_Label::Name`. Whether `Identifier::Label` as a nested type (Rust `mod` or associated type) is preferred over `Identifier_Label` as a top-level name is unresolved by existing code.

3. **Does the `children` getter rebuild-on-every-call and clone-on-child-access matter at the scale of a generated Rust parser?** A Rust parser would never go through `children` (getter) or per-label Python methods; it would use `children_native` and direct enum match. The Python boundary cost is only paid when a Python caller reads children back.

4. **Can a mixed Rust/Python application today pass a CST node from Python into Rust?** Only if both sides are in the same cdylib. `PyRef<'_, Identifier>` in `extend_children` requires same-cdylib registration. There is no cross-cdylib node extraction equivalent to `extract_span`.
