# Exploration: Rust CST Native Span

Concise. Precise. Token-dense — no fluff, full information. No preamble. No padding.

## The problem, precisely

Every Rust CST node struct in the codebase holds its span as `PyObject` — a raw Python object
reference requiring the GIL. This is the full list of affected node structs:

**`src/cst_generated.rs`** (PoC grammar — hand-written):
- `Identifier` (line 110): `span: PyObject`
- `Items` (line 357): `span: PyObject`
- `Trivia` (line 857): `span: PyObject`

**`src/cst_fegen.rs`** (fegen grammar — hand-written, 5081 lines):
- `Grammar` (line 142): `span: PyObject`
- `Rule` (line 382): `span: PyObject`
- `Alternatives` (line 707): `span: PyObject`
- `Items` (line 953): `span: PyObject`
- `Item` (line 1462): `span: PyObject`
- … all 14 grammar node types follow the same pattern

**`tests/rust_cst_fixture/src/cst.rs`** (Phase 4 fixture — generated):
- `Config` (line 121): `span: PyObject`
- `Entry` (line 364): `span: PyObject`
- `Operator` (line 783): `span: PyObject`
- `Identifier` (line 1196): `span: PyObject`
- `Literal` (line ~1500+): `span: PyObject`
- `Trivia` (line ~1700+): `span: PyObject`

**`tests/rust_cst_fegen/src/cst.rs`** (fegen fixture — generated):
- All 14 node types: `span: PyObject`

**Generator** (`fltk/fegen/gsm2tree_rs.py`):
- `_node_block` method (line 290-295) emits `span: PyObject` for every generated node.
- `_new_method` (lines 323-342) resolves `UnknownSpan` by importing `fltk._native.UnknownSpan`
  at runtime and storing it as a `PyObject`.
- `_preamble` (lines 118-129) emits `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject>` in
  every generated file.

The `span` getter and setter are exposed to Python via `#[pyo3(get, set)]`. The setter accepts
any Python object (no type check). The `__eq__` method (`_eq_method`, lines 535-550) compares
spans via `self.span.bind(py).eq(other_node.span.bind(py))` — a Python equality call requiring
the GIL.

## Rust Span is already a first-class Rust type

`src/span.rs` defines a pure Rust `Span` struct:

```rust
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceInner>>,
}
```

It is `#[pyclass(frozen, eq, hash)]` and is fully usable in pure Rust without the GIL. It has:
- No GIL requirement for construction or field access
- `Clone` derive
- Equality/hash implemented entirely in Rust (lines 71-84)
- Python bindings layered on top via `#[pymethods]`

`UnknownSpan` is a sentinel `Span { start: -1, end: -1, source: None }` created at module init
(`src/lib.rs:22-31`) and stored in `static UNKNOWN_SPAN: GILOnceCell<PyObject>`. This static
exists but is noted as "no generated code reads it directly" (lib.rs:14-15).

## What `span: PyObject` prevents

1. **Pure Rust usability.** A `struct Identifier { span: PyObject, ... }` cannot be constructed
   or used without a live Python interpreter and the GIL. The `Py<PyList>` children field has
   the same problem, but span is the focus here.

2. **Type safety.** `span: PyObject` accepts any Python object. The only enforcement is in the
   `#[new]` method which defaults to `UnknownSpan`; a caller can set an arbitrary object via
   the exposed setter.

3. **No-GIL Rust traversal.** Comparing, copying, or inspecting spans in a Rust-side tree walk
   requires acquiring the GIL on every node.

## What the protocol layer says about span type

`fltk/fegen/fltk_cst_protocol.py:85` annotates `span: fltk.fegen.pyrt.terminalsrc.Span` on
every Protocol node class. This is the **Python-backend** `terminalsrc.Span` (a frozen
dataclass). The protocol annotation is not backend-agnostic — it names the concrete Python type.

The Python generated CST (`fltk/fegen/fltk_cst.py`) matches: `span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan`.

## What currently sets span on Rust CST nodes

**Generated parsers** (`fltk_parser.py`, `bootstrap_parser.py`) assign span like:
```python
result.span = fltk.fegen.pyrt.terminalsrc.Span(start=result.span.start, end=pos)
```
They import `fltk.fegen.pyrt.terminalsrc.Span` directly (not the backend selector). These
parsers are permanently Python-backend-only for span objects. The Rust CST node's `span`
attribute receives a `terminalsrc.Span` (Python dataclass), not a `fltk._native.Span` (Rust).

This is confirmed by `docs/adr/2026/06/06-rust-cst-child-span-test/exploration.md`:
> "When the Rust fegen CST backend is used, the CST *nodes* are Rust objects, but the *children
> stored inside them* are still `terminalsrc.Span` instances — Python objects stored in the Rust
> `Py<PyList>` children list."

**`fltk/fegen/fltk2gsm.py`** (lines 24-26, 145-151) calls `span.start` and `span.end` on the
result of `child_name()`, `child_value()` — these work today because those are `terminalsrc.Span`
Python dataclass instances, not `fltk._native.Span`.

## What `children: Py<PyList>` means

Every child stored in a Rust CST node is also a Python object (`PyObject` inside a `Py<PyList>`).
The request identifies `span` as the target. The `children` field has the same Python-dependency
for the same reason: it is typed as `Py<PyList>` whose elements are `PyObject` (whatever was
appended). Changing span to native Rust does not resolve the children dependency.

## What a native Rust span field would look like

Instead of `span: PyObject`, each generated struct would hold `span: crate::Span` (or
`fltk::Span` in downstream extension crates). Construction:
```rust
pub struct Identifier {
    pub span: Span,
    children: Py<PyList>,
}
```

The `#[new]` method would accept `Option<Py<Span>>` (a Rust-wrapped Python Span), extract the
inner `Span` via `span.extract::<Span>(py)`, and default to `Span { start: -1, end: -1,
source: None }`. The getter would return `Py<Span>` (wrapping a clone). The setter would accept
`Py<Span>` (or `&Span`) and store a clone.

## Cross-crate access: the `pub(crate)` problem

`Span`'s fields `start`, `end`, `source` are `pub(crate)` in `src/span.rs:66-68`. Generated CST
in downstream crates (`tests/rust_cst_fixture/`, `tests/rust_cst_fegen/`, and any out-of-tree
user) cannot access `fltk._native.Span` field internals even if they hold a `Span` value. The
`Span` type itself is `pub struct Span` but its fields are not. This must be resolved (either
making fields `pub` or providing `pub` constructor/accessor fns) for downstream crates to
construct `Span` values in pure Rust.

## Downstream crate dependency on `fltk._native`

Generated node crates (`tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`)
depend on `fltk._native` only at **runtime** (Python import), not at **link time**. Their
`Cargo.toml` does not have a Rust dependency on the `fltk` crate. If `span: Span` (native) is
used, the generated crate needs a Rust crate dependency to get the `Span` type at compile time.
This is a build system change.

The `tests/rust_cst_fixture/src/lib.rs:3` comment confirms:
> "Independent of fltk's crate at link time; depends on fltk._native only at runtime."

## API surface change for Python consumers

Currently `node.span` returns whatever Python object was stored — typically a `terminalsrc.Span`.
After the change, `node.span` would return a `fltk._native.Span` object. These are different
types with different attribute surfaces:

- `terminalsrc.Span`: dataclass with public `.start: int`, `.end: int`, `.kind`, `.text()`, etc.
- `fltk._native.Span`: `.start`/`.end` intentionally NOT exposed (test_rust_span.py:61-69),
  only `.text()`, `.text_or_raise()`, `.has_source()`, `.len()`, `.is_empty()`, `.kind`,
  `.merge()`, `.intersect()`.

`fltk/fegen/fltk2gsm.py` lines 26, 147, 151 call `span.start` and `span.end` directly on
child-accessor results. After migrating to native Rust span, these calls would fail at runtime
with `AttributeError` unless the parser also migrates to produce `fltk._native.Span` objects,
or the `fltk._native.Span` exposes `.start`/`.end` getters.

## Generated parser migration scope

`fltk/fegen/genparser.py` (the parser generator) and all generated parsers would need to:
1. Import `fltk._native.SourceText` and `fltk._native.Span` (or their backend-selector
   equivalents) instead of `fltk.fegen.pyrt.terminalsrc.Span`.
2. Construct source-bearing spans via `Span.with_source(start, end, source_text)` where
   `source_text` is a `SourceText` object (wrapping the input string once).
3. Assign `result.span = <fltk._native.Span value>` on each rule result.

This is the "parse path" migration blocked by `TODO(backend-with-source-signature)` and noted
in `docs/adr/2026/06/06-backend-with-source-signature/exploration.md`.

## Files and identifiers to change

| File | Change needed |
|------|---------------|
| `src/span.rs:66-68` | Make `start`, `end`, `source` fields `pub` (or add pub constructors/accessors) |
| `src/cst_generated.rs` | Change `span: PyObject` to `span: Span`; update `#[new]`, getter, setter, `__eq__`, `__repr__` |
| `src/cst_fegen.rs` | Same, all 14 node structs |
| `fltk/fegen/gsm2tree_rs.py:290-342` | Update generator: emit `span: Span`, change `_new_method`, `_eq_method`, `_repr_method` |
| `tests/rust_cst_fixture/src/cst.rs` | Regenerated from updated generator; Cargo.toml needs fltk dependency |
| `tests/rust_cst_fegen/src/cst.rs` | Same |
| `fltk/fegen/fltk_cst_protocol.py:85,114,...` | Change `span: fltk.fegen.pyrt.terminalsrc.Span` to a backend-agnostic type (or union) |
| `fltk/fegen/genparser.py` | Change emitted parser code to assign `fltk._native.Span` to `node.span` |
| `fltk/fegen/fltk_parser.py`, `bootstrap_parser.py` | Regenerated from updated genparser |
| `fltk/fegen/fltk2gsm.py:26,147,151` | Replace `span.start`/`span.end` with `SpanProtocol`-compatible access |

## Open factual questions

1. **Are there out-of-tree consumers of `node.span` that call `.start`/`.end` on the result?**
   Unknown. The request says out-of-tree consumers exist but are not visible.

2. **Should `fltk._native.Span` expose `.start`/`.end` as Python getters?** This would ease
   migration of `fltk2gsm.py` and downstream code, but conflicts with the existing design
   decision documented in `src/span.rs:54-56` (intentionally omitted) and enforced by
   `tests/test_rust_span.py:61-69`.

3. **What is the exact Rust API for downstream crates to construct a `Span`?** Currently
   impossible in pure Rust because fields are `pub(crate)`. The fix needs a public Rust
   constructor function or public fields.

4. **Does the children list also need to migrate?** The request says "no Rust CST node may hold
   a reference to any Python object." `children: Py<PyList>` is also a Python object reference.
   The request explicitly names span, but `Py<PyList>` may also need to change to satisfy the
   stated requirement fully. This is a potentially much larger change.
