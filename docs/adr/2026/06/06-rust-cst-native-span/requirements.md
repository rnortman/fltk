# Requirements: Rust CST — No Python-Object References

Concise. Precise. Unambiguous. No padding. Audience: smart LLM/human.

## Goals

No Rust CST node may hold a reference to any Python object. The Rust CST must be usable
standalone in pure Rust — no GIL, no live Python interpreter — for construction, traversal,
field access, equality, and cloning. Python bindings/wrappers layered on top must not force the
underlying Rust CST to depend on Python types. `span` (currently `PyObject`) is the known
instance of the violation, not the boundary of the requirement: every Python-object-typed field
on every Rust CST node is in scope.

> Scope note: the ADR slug (`rust-cst-native-span`) is historical. The scope is **all**
> node-state fields, not span. `span` is one instance of a general rule.

> Scope-magnitude note: the `children` migration (`Py<PyList>` → native container) is the
> dominant, API-shaping portion of this work — it reshapes the public Rust traversal surface and
> introduces per-node child representation, and per the exploration is "potentially the largest
> change," larger than the span fix. It is firmly in scope (the user requires "no Python-object
> reference"). The requester may choose to **stage** delivery (span/scalar fields first, children
> second) or do it atomically; staging is an implementation-ordering choice and does not narrow
> scope.

## In scope

- **Every** field of **every** Rust CST node struct that currently holds a Python object is
  migrated to a native Rust representation. All such structs are **generated** artifacts — emitted
  by `RustCstGenerator` (`fltk/fegen/gsm2tree_rs.py`) and checked into the repo. There are zero
  hand-written CST node structs with Python-object fields anywhere (including tests). The affected
  generated-into-repo files are `src/cst_generated.rs`, `src/cst_fegen.rs`,
  `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`. The fix belongs in the
  generator and is delivered by regenerating these files. Known field instances:
  - `span: PyObject` → native Rust `Span`.
  - `children: Py<PyList>` → a native Rust container whose elements are native Rust CST node /
    span / token values (not `PyObject`).
  - Any other `PyObject`, `Py<...>`, or Python-handle-typed field discovered on a CST node
    struct (the migration target is "no Python-object reference," not an enumerated list).
- The Rust CST node generator (`gsm2tree_rs.py`) emits native Rust types for all node fields and
  the corresponding constructor / getter / setter / equality / repr / accessor code, with no
  `PyObject`/`Py<PyList>` node-state fields and no runtime `fltk._native.*` imports to
  materialize node state (e.g. the `UNKNOWN_SPAN_CACHE` / `GILOnceCell<PyObject>` pattern).
- A public Rust API for constructing and reading the native field types (`Span`, the children
  container, child accessors) from downstream crates — resolving the `pub(crate)`
  field-visibility blocker on `Span` and any equivalent blocker on node/children types.
- Build-system changes so generated downstream crates can name the native Rust types
  (`Span`, node types) at compile time (Cargo dependency on the `fltk` crate).
- The parse path (parser generator + generated parsers) producing native Rust values where
  required so Rust CST nodes receive native spans and native children rather than Python
  `terminalsrc.Span` / Python objects, when the Rust CST backend is selected.
- In-tree callers that read CST node state (notably `fltk2gsm.py`, and any reader of
  `node.span` or child accessors) updated to the native access surface so they work under both
  backends without `AttributeError`.
- Protocol annotations for affected fields made backend-agnostic so they admit both the
  Python-backend types (`terminalsrc.Span`, Python child nodes) and the Rust-backend native
  types. The widening must be **additive** — a strict superset of the current annotation — so
  that existing Python-backend-only consumers' type-checks continue to pass with no required
  annotation edits. (The protocol annotation is public type-surface; per CLAUDE.md, forcing
  Python-backend consumers to update annotations would be a breaking change and is out of scope.)
  - Acceptance: a Python-backend-only consumer that type-checks against the protocol with the
    current `terminalsrc.Span` annotation still type-checks without edits after the widening.
- The in-repo generated CST modules are manually re-generated, re-formatted with cargo fmt, and committed in the new form.

## Out of scope

- Forcing out-of-tree consumers to migrate. They continue on the Python backend unchanged; they
  update only when they choose the Rust CST backend.
- Performance optimization of the parse path beyond what the native-representation change
  requires.
- Any change to the Python backend's CST node representation or its `terminalsrc.Span`.
- Renaming any generated public symbol (class names, accessor method names, label enums).

## System behavior

### Native node state (Rust)

- No generated Rust CST node struct (`src/cst_generated.rs`, `src/cst_fegen.rs`,
  `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, and any future generator
  output) holds any field of type `PyObject`, `Py<PyList>`, or any other Python-object handle for
  its node state (span, children, or otherwise). Each such field is a native Rust type. (All these
  structs are generated by `gsm2tree_rs.py`; there are no hand-written CST node structs.)
  - Acceptance: an audit of every generated CST node struct confirms no Python-object-typed state
    field. (Python bindings — `#[pymethods]`, getters returning
    `Py<...>` for the Python API — are permitted; the prohibition is on **stored state**.)
- A Rust CST node can be constructed, traversed (parent → child), and have its span and children
  read / compared / cloned in pure Rust without acquiring the GIL and without a live Python
  interpreter.
  - Acceptance: a pure-Rust test (no `Python::with_gil`, no Python init) constructs a generated
    node tree (a node with child nodes and spans), walks it, reads spans and children, and
    compares two subtrees for equality.
- The default span for a node constructed without an explicit span is the sentinel "unknown
  span" (`start = -1`, `end = -1`, no source), equal in value to the existing `UnknownSpan`
  sentinel.
- Generated files no longer emit `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject>` or import
  `fltk._native.UnknownSpan` (or any other `fltk._native.*` runtime import) to materialize node
  state.

### Node and span equality

- Node `__eq__` compares all state — span and children — using native Rust equality (value
  semantics per `src/span.rs` for spans; recursive native equality for children), not Python
  `.eq()` calls on stored Python objects.
  - Acceptance: two nodes (with children) that are value-equal compare equal, and two that
    differ in any span or child compare unequal — both verifiable without the comparison path
    entering Python equality code for stored node state.

### Python binding surface

- From Python, `node.span` returns a `fltk._native.Span` (Rust-backed Span pyclass) wrapping a
  clone of the stored native span. Child accessors return the Python-wrapped native child nodes.
- The span setter accepts a `fltk._native.Span` and stores its inner native value (a clone); it
  no longer accepts arbitrary Python objects.
  - Acceptance: setting `node.span` to a non-`Span` Python object raises (TypeError) rather than
    silently storing it.

### Public Rust construction/access (cross-crate)

- Downstream crates can construct native node and span values and read their state (span
  extents, children) in pure Rust via a stable public Rust API (public constructors and
  accessors), without touching `pub(crate)` fields.
  - Acceptance: a downstream crate constructs a `Span` (with and without source) and a node
    holding child nodes, then reads back span start/end and children via the public Rust API,
    compiling and running without touching crate-private fields.

### Parse path

- When using the Rust CST backend, the parser generator and generated parsers assign native Rust values (source-bearing `Span`
  where a source is available; native child values into the native children container) to Rust
  CST nodes, so nodes produced by parsing hold no Python objects as state when the Rust CST
  backend is selected.
  - Acceptance: parsing input with the Rust CST backend yields a node tree whose spans are
    `fltk._native.Span` and whose stored children are native CST nodes (not Python
    `terminalsrc.Span` / Python objects); `.text()` on a node's span returns the spanned source
    text.

### In-tree consumer migration

- `fltk2gsm.py` (and any other in-tree reader of `node.span` or child accessors) reads node
  state through an access surface valid for the native types returned by the Rust backend, so it
  works under both backends without `AttributeError`.
  - Acceptance: the existing fltk2gsm conversion path passes its tests under the Rust CST
    backend.

### Behavioral equivalence

- Cross-backend (Python vs Rust) observable behavior remains equivalent from a consumer's
  perspective: span `.text()`, `.kind`, length/empty predicates, child accessor results, and
  node equality. Span-extent access (`.start`/`.end`) availability is governed by Open question
  `native-span-start-end`.
- Node/span `repr()` string output is **not** a tracked equivalence surface. The Rust backend's
  `node.span` repr (and any node repr that interpolates the span) may differ from the Python
  backend's `terminalsrc.Span(...)` repr. Consumers must not depend on cross-backend repr
  equality; the generator need not reproduce the Python repr form.

## User-visible surface

- Generated Rust CST node structs: all node-state field types change from Python objects
  (`PyObject`, `Py<PyList>`) to native Rust types (`Span`, native children container, native
  child node types) — public Rust API surface for out-of-tree Rust consumers.
- Python `node.span`: type returned changes (under the Rust backend) from a Python
  `terminalsrc.Span` to `fltk._native.Span`. Attribute surface differs (exploration:
  `terminalsrc.Span` exposes `.start`/`.end`; `fltk._native.Span` currently does not). Deliberate,
  called-out change affecting out-of-tree consumers **only when they select the Rust backend**.
- Generated downstream crates gain a Rust compile-time dependency providing the native types
  (build-system / Cargo manifest change).
- Protocol class annotations for affected fields change to backend-agnostic types/unions.
- No generated public **symbol names** (class names, accessor method names, label enums) change.

## Constraints

- Backward compatibility: out-of-tree consumers on the Python backend see no change. The Rust
  backend remains a near-drop-in replacement — no forced wholesale edits to downstream type
  annotations or call sites beyond the field-type surface changes inherent to this work and the
  import-statement updates already expected when adopting the Rust backend.
- No generated public symbol renames; no annotation churn beyond the affected field types.
- Pure-Rust usability invariant: no CST node field imposes a GIL/interpreter requirement.
- `Span` value semantics (start/end/source equality and hashing) per `src/span.rs` are
  preserved.

## Open questions

### native-span-start-end

`fltk._native.Span` intentionally does NOT expose `.start`/`.end` Python getters (design decision
in `src/span.rs`, enforced by `tests/test_rust_span.py`). After this change `node.span` returns
`fltk._native.Span`, so any consumer (in-tree `fltk2gsm.py`, and unknown out-of-tree code) that
reads `node.span.start`/`.end` breaks with `AttributeError`.

Options:
- (A) Expose `.start`/`.end` getters on `fltk._native.Span`, reversing the prior design decision
  (update/remove the enforcing test). Eases migration; widens the native Span API.
- (B) Keep `.start`/`.end` off the native Span; migrate in-tree callers to use only the
  sanctioned surface (`.text()`, `.len()`, `.is_empty()`, etc.) and accept that out-of-tree code
  reading `.start`/`.end` must migrate when adopting the Rust backend.

USER DECISION: Option (B); users must migrate, Rust does not expose .start/.end. (Indexing works differently in Rust because of UTF-8, so option A is a massive footgun.)

### children-container-shape

`children` migrates from `Py<PyList>` to a native Rust container (now in scope). The container's
concrete shape and element type are not pinned by the request. Dimensions to decide:
- Element type: a native enum over child node types / span / token, vs. a trait-object /
  boxed-dyn representation. Affects the public Rust traversal API and downstream ergonomics.
- Container type: `Vec<...>` vs. another structure; whether ordering/label-grouping is preserved
  exactly as today.
- Whether the existing label-based child accessor methods keep identical signatures (required by
  the no-symbol-rename constraint) while sourcing from the native container.

Designer chooses a resolution. It is recommended to stick with idiomatic and efficient Rust mechanisms, and translate to Python at the boundary.

### out-of-tree-state-readers

Unknown whether out-of-tree consumers read `node.span.start`/`.end` or otherwise depend on the
current Python-object identity of stored children (e.g. `isinstance` against `terminalsrc.Span`
or Python child classes). Affects how aggressively the native surface must preserve the prior
attribute/identity surface (interacts with `native-span-start-end` and `children-container-shape`).
No in-repo evidence available; surfaced rather than assumed.

USER ANSWER: Out of tree consumers that directly access start/end must update in order to switch to Rust backend. Python consumers not affected, and all other aspects of the Rust backend should be compatible with Python.
