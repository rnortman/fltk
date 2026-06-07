# Design: Rust CST — Native Node State (No Python-Object References)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Requirements: `docs/adr/2026/06/06-rust-cst-native-span/requirements.md` (approved).
Exploration: `docs/adr/2026/06/06-rust-cst-native-span/exploration.md`.
This doc does not restate requirements; it refers to them by section.

## 1. Root cause / context

Every generated Rust CST node struct stores its node state as Python-object handles, so the
"Rust" CST cannot exist without a live interpreter and the GIL.

- `gsm2tree_rs.py:289-294` emits every node struct as:
  ```rust
  #[pyclass]
  pub struct <Name> {
      #[pyo3(get, set)] span: PyObject,
      #[pyo3(get)] children: Py<PyList>,
  }
  ```
  Both fields are Python handles. `span` accepts any Python object (no type check); `children`
  is a `Py<PyList>` of `(label, child)` `PyTuple`s where each `child` is itself a `PyObject`.
- `_new_method` (`gsm2tree_rs.py:323-342`) defaults `span` by importing `fltk._native.UnknownSpan`
  at runtime through a per-file `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject>`
  (`_preamble`, lines 118-129).
- `_eq_method` (lines 535-550) compares spans and children with **Python** `.eq()` calls
  (`self.span.bind(py).eq(...)`, `self.children.bind(py).eq(...)`).
- All child accessors (`_per_label_methods`, lines 414-533) iterate the `Py<PyList>`, downcast
  each element to `PyTuple`, and compare labels via Python `.eq()`.
- `_repr_method` (lines 560-570) calls Python `.repr()` on both fields.

A pure-Rust `Span` already exists (`src/span.rs:63-69`): `#[pyclass(frozen, eq, hash)]`, GIL-free
construction/field-access/equality/clone, value equality on `(start, end)` only
(`src/span.rs:71-84`). The blocker is that node structs hold the *Python wrapper* for spans and
children rather than native Rust values. Requirements §"In scope" makes the full migration of
*every* Python-object node field the target; `span` is one instance.

Two structural facts shape the design:

1. **`children` is the dominant, API-shaping part** (requirements scope-magnitude note). Today a
   child slot holds heterogeneous values: a Rust CST node pyobject, or a `terminalsrc.Span`
   (Python dataclass) for token/terminal children. Going native requires a Rust enum over the
   concrete child node types plus a span/token variant, and a native container of
   `(label, child)` pairs.

2. **The root crate is `crate-type = ["cdylib"]` only** (`Cargo.toml`). A cdylib cannot be a
   normal Rust library dependency of the downstream fixture crates (`tests/rust_cst_fixture/`,
   `tests/rust_cst_fegen/`), which today depend on `fltk._native` at runtime only
   (`tests/rust_cst_fixture/src/lib.rs:1-4`). For a downstream crate to name the runtime types
   (`Span`, `SourceText`) at *compile* time (requirements §"Build-system changes"), those types must
   live in a linkable rlib that does **not** carry pyo3's `extension-module` feature. §2.1 resolves
   this with a split `fltk-cst-core` crate that holds only the runtime types — **not** the generated
   node structs, which are emitted to the consumer-chosen `RS_OUT` path and merely `use` the core
   crate.

## 2. Proposed approach

### 2.1 Make the native types linkable as a Rust library (build system)

A downstream cdylib must link the runtime types (`Span`, `SourceText`) at compile time, but it
*also* declares its own pyo3 `extension-module`. Linking an rlib that itself carries
`pyo3/extension-module` into such a crate double-activates the feature → pyo3-runtime symbol/init
conflict. `Cargo.toml` today: `crate-type = ["cdylib"]`, `default = ["extension-module"]`,
`extension-module = ["pyo3/extension-module"]`. So the naive `["cdylib","rlib"]` + a default-features
dependency is itself the failure mode.

**Adopt the split-crate structure** (the safe form; recommended over validate-then-decide):

- New `fltk-cst-core` rlib crate holding **only the runtime types** that generated code depends on,
  with **no** `extension-module` feature and no pyo3-runtime activation: `Span` and `SourceText`
  (moved out of `src/span.rs`). These are the types every generated node struct references via
  `use fltk_cst_core::Span;`. They are pyo3-runtime-free so that the `Box`-based native node state
  built on top of them (§2.3) and native equality/traversal (§2.4) need no `Python::with_gil`.
- **Generated node structs do NOT live in `fltk-cst-core`.** They are emitted to the consumer-chosen
  `RS_OUT` path: FLTK's own grammars emit to `src/cst_*.rs` (compiled into the `fltk._native`
  extension); out-of-tree consumers emit into *their own* crate. Either way the generated file `use`s
  `fltk-cst-core` for `Span`/`SourceText` and defines its own per-rule child-node enums (`Box`-based,
  §2.3) and `#[pyclass]`/`#[pymethods]` bindings locally. Forcing generated structs into
  `fltk-cst-core` would force out-of-tree consumers to generate inside FLTK's crate — a CLAUDE.md
  violation and explicitly **not** this design.
- pyo3 itself (without the `extension-module` feature) is usable wherever the generated structs land,
  so the `#[pyclass]`/`#[pymethods]` bindings (getters returning `Py<…>`, setters, accessors) sit
  alongside each generated node struct in its own `RS_OUT` file — no cross-crate `#[pymethods]`.
- The existing extension crate (`fltk._native`) keeps `crate-type = ["cdylib"]`, keeps
  `extension-module`, depends on `fltk-cst-core`, compiles FLTK's own generated `src/cst_*.rs`, and
  registers their pyclasses into the Python module.
- Downstream fixture/out-of-tree crates depend on `fltk-cst-core` for the runtime types:
  ```toml
  [dependencies]
  fltk-cst-core = { path = "<...>", default-features = false }
  ```
  `default-features = false` is mandatory: it guarantees the downstream crate never transitively
  activates `pyo3/extension-module`. The `tests/rust_cst_fixture/` crate is the existence proof —
  generated CST in its own crate, depending on `fltk-cst-core` as a library.

`Span`/`SourceText` live in `fltk-cst-core` precisely because §2.3/§2.4 build pyo3-runtime-free
native node state on them (pure-Rust construction and equality). The runtime Python import of
`fltk._native` for the *module* is unaffected; the new Cargo dependency is a compile-time link for
the *runtime types* only.

(A simpler `["cdylib","rlib"]` on the existing crate with `extension-module` moved out of `default`
is a fallback if the split proves unnecessary, but the split is preferred because §2.3/§2.4 already
force a pyo3-free runtime-type core.)

### 2.2 Native `Span` field + public constructor/accessors

- Emit `span: Span` (native) instead of `span: PyObject`. Default to the sentinel value
  `Span { start: -1, end: -1, source: None }` constructed directly in Rust — **no**
  `UNKNOWN_SPAN_CACHE`, no `fltk._native.UnknownSpan` import. Remove the `_preamble`
  `GILOnceCell<PyObject>` emission.
- Resolve the `pub(crate)` visibility blocker (`src/span.rs:66-68`, exploration §"Cross-crate
  access"). `Span`/`SourceText` move into `fltk-cst-core` (§2.1); add **public Rust
  constructors/accessors** there rather than making fields `pub` (keeps invariants, keeps byte-offset
  semantics encapsulated):
  - `pub fn Span::unknown() -> Span` (sentinel).
  - `pub fn Span::new_sourceless(start: i64, end: i64) -> Span` and a `with_source` Rust-level
    constructor (the existing `#[new]`/`with_source` are `#[pymethods]`, not callable cross-crate;
    add plain `impl Span` public fns).
  - `pub fn Span::start(&self) -> i64`, `pub fn Span::end(&self) -> i64` for **Rust** readers
    (downstream pure-Rust traversal). These are Rust methods, **not** `#[getter]`s — the Python
    `.start`/`.end` decision is Option B (requirements `native-span-start-end`): no Python getter.
- Python binding surface (requirements §"Python binding surface"):
  - getter `fn span(&self, py) -> Py<Span>` returns a clone wrapped as the `Span` pyclass.
  - setter: emit an explicit `#[setter]` taking `value: &Span` (or `PyRef<Span>`) and storing
    `value.clone()`. pyo3 extraction of a non-`Span` argument fails with `TypeError` before the
    body runs, satisfying the setter acceptance criterion. (A `#[setter]` is used rather than
    relying on `#[pyo3(set)]` because the stored field type is native `Span` while the
    Python-visible value is the `Span` pyclass — the explicit setter makes the clone-on-store and
    the type bound unambiguous.)

### 2.3 Native `children` container + child enum (children-container-shape resolution)

Resolves requirements open question `children-container-shape`. Idiomatic-Rust choice, translate
at the Python boundary (per the requirement's recommendation).

**Per-node child enum (native, `Box`-based).** For each rule's node, the generator emits a child-value
enum over the concrete child node types that can appear under that rule, plus a terminal/span variant.
The set of possible child node types per rule is already computed by the Python generator
(`CstGenerator.rule_models[...]`, used today to type protocol `children` unions, e.g.
`Alternatives | Identifier | Trivia` in `fltk_cst_protocol.py:115`). Reuse that model to emit:

```rust
pub enum <Name>Child {
    Alternatives(Box<Alternatives>),
    Identifier(Box<Identifier>),
    Trivia(Box<Trivia>),
    Span(Span),            // terminal/token children (was terminalsrc.Span)
}
```

**Native storage is required, not `Py<ChildNode>`.** The requirement (§"Native node state", 2nd
bullet) is an *acceptance criterion*: a node tree with child nodes must be constructed, walked, and
compared in pure Rust with no `Python::with_gil` and no Python init. `Py<T>` cannot satisfy this — its
construction needs a `Python` token. Therefore stored child nodes are owned natively (`Box<ChildNode>`);
the node structs themselves are pyo3-runtime-free (`fltk-cst-core`, §2.1). `Py<…>` appears *only* at
the Python binding boundary, when an accessor wraps a native child for return to Python — never in
stored state. The terminal variant holds a **native** `Span`. Pure-Rust traversal
(construct/walk/compare/clone) works directly on the enum; equality is structural (§2.4).

> Cost (the real, in-scope cost of the requirement): every accessor that returns a child to Python must
> translate the native variant → a `Py<ConcreteNode>` (the matched node's pyclass) or a `Py<Span>` at
> call time. This is the larger change both the exploration and requirements flagged for children; it
> is accepted, not deferred.
>
> Consequence — Python child identity: native ownership means a child returned twice through the Python
> getter need not be the same `PyObject` (the old `Py<PyList>` preserved identity). Tracked as
> `TODO(rust-cst-child-node-identity)`: if a consumer relies on Python child-object identity, layer a
> per-node `Py` cache at the binding boundary. Does not block the native-state acceptance.

**Container.** `children: Vec<(Option<<Name>Label>, <Name>Child)>`. `Vec` preserves order exactly
as the current `Py<PyList>` (ordering is load-bearing — `fltk2gsm.visit_items` depends on
interleaved order, `fltk2gsm.py:54-87`). Label is the existing native label enum
(`<Name>_Label`), already emitted (`_label_enum_block`); `None` for unlabeled children (matches
current `py.None()` label, `gsm2tree_rs.py:368`).

**Accessors keep identical signatures** (no-symbol-rename constraint, requirements §Constraints).
`append`/`extend`/`child`/`append_<label>`/`extend_<label>`/`children_<label>`/`child_<label>`/
`maybe_<label>` retain names and Python-visible behavior, but source from the `Vec` and translate
at the boundary:
- `append(child, label=None)`: extract `child` into the node's child enum (dispatch on Python
  type / `Span` extract), push `(label, variant)` onto the native `Vec`. When appending a node, take
  its native value into a `Box`.
- `extend(other_children)`: append each element of `other_children` onto the native `Vec`. **The
  parser generator must call this method (and `append`), not `.extend()` on the `children` getter
  result** (see parser-generator note below).
- `children_<label>` / `child_<label>` / `maybe_<label>`: filter the `Vec` by native label enum
  equality (Rust `==`, not Python `.eq()`), map each matched child variant back to its Python object
  (node variant → `Py<ConcreteNode>` (the node's pyclass); `Span` variant → `Py<Span>`).
- `children` Python getter: build a `PyList` of `(label_pyobj, child_pyobj)` tuples on demand from
  the `Vec`, preserving the current Python-visible shape `list[tuple[Label|None, Child]]` that
  `fltk2gsm.py:36` and the protocol (`children: list[tuple[...]]`) rely on. This list is read-oriented
  and rebuilt per call; it is **not** a mutation handle (see below).

**Parser-generator change (in scope).** Generated parsers today mutate children via the getter:
`result.children.extend(item.result.children)` (`fltk_parser.py:114,224,…`,
`bootstrap_parser.py:94,198,…`), emitted by `gsm2parser.py:497,715`
(`...fld.children.method.extend.call(...children.move())`). With a rebuild-on-each-call getter, that
mutates a throwaway list and silently drops children. `gsm2parser.py` must instead emit a call to the
node's own `extend`/`append` method (which mutates the native `Vec`):
`result.extend_children(item.result)` / `result.extend(item.result.children_iter())` — the exact
generated form keeps the no-rename constraint by using the existing node methods. This is required for
the Rust backend; under the Python backend the node's `extend`/`append` produce identical results, so
the change is backend-neutral. Without it, Rust-backend parsing yields empty/incomplete children and
the parse-path + fltk2gsm acceptances fail.

### 2.4 Native equality, hash, repr

- `_eq_method`: compare `self.span == other.span` (native `Span` `PartialEq`) and recursively
  compare `children` via the native enum's derived/structural `PartialEq` (`Vec` equality; element
  equality compares label enums natively, the `Span` variant per `span.rs`, and `Box<ChildNode>`
  variants by recursing into the child node's native field equality). No comparison borrows a `Py<T>`
  and none enters Python `.eq()` on stored state. The native `PartialEq` on the node enum lives in
  `fltk-cst-core` and is callable with no GIL. Replaces the current `self.children.bind(py).eq(...)` /
  `self.span.bind(py).eq(...)` Python-equality path (`gsm2tree_rs.py:535-550`). Satisfies requirements
  §"Node and span equality" acceptance (equality without entering Python equality code for stored
  state) *and* the pure-Rust equality requirement.
- `_hash_method`: unchanged (nodes remain unhashable, `gsm2tree_rs.py:552-558`).
- `_repr_method`: build from native fields. repr is explicitly **not** a cross-backend equivalence
  surface (requirements §"Behavioral equivalence"); emit a Rust-native form
  (`<Name>(span=Span(start=.., end=..), children=[..])`). No Python `.repr()` on stored state.

### 2.5 Parse path (native span production)

Generated parsers currently assign `fltk.fegen.pyrt.terminalsrc.Span` to `node.span`
(exploration §"What currently sets span"). Under the Rust backend the setter now requires a
`fltk._native.Span`. The parser generator (`fltk/fegen/genparser.py`) and regenerated parsers
(`fltk_parser.py`, `bootstrap_parser.py`) must, **when the Rust CST backend is selected**:
1. Wrap the input once in `fltk._native.SourceText`.
2. Construct **source-bearing** spans via `fltk._native.Span.with_source(start, end, source_text)` —
   for both node spans **and child/terminal spans**. (Child spans must carry source so the fltk2gsm
   `text()` reads resolve, §2.6.)
3. Assign that native span; append native children through the node's `append`/`extend` **methods**
   (which extract into the native child enum, §2.3 — not `.children.extend(...)` on the getter).

Under the Python backend, the parser must likewise attach the existing `SourceText`/terminals to child
`terminalsrc.Span`s so their `text()` resolves (changing what source is attached, not the type — §2.6).

**Prerequisite (lands first): backend-with-source-signature.** The portable, both-backend
`Span.with_source(start, end, SourceText(...))` constructor that this parse-path work calls does not
yet exist as a portable surface — today the Python-backend selector binds `SourceText = None`
(`fltk/fegen/pyrt/span.py:14`) and Python `with_source` takes a raw `str`, while the Rust backend
takes `&SourceText`. The `backend-with-source-signature` change
(`docs/adr/2026/06/06-backend-with-source-signature/design.md`) unifies this: it adds a Python
`SourceText` wrapper to `terminalsrc.py`, makes Python `with_source` accept `str | SourceText`, and
exports a real `SourceText` from the selector on both paths. **That change is pulled into this work
as a prerequisite and must land before §2.5**, because §2.5 (and the §2.6 both-backend `text()`
reads) call `Span.with_source(start, end, source_text)` portably across backends. Until it lands,
the generated parser cannot construct source-bearing spans on both backends from one code path.
Implement it per its design (three Python-side edits; no Rust/parser/generator/protocol changes),
then remove `TODO(backend-with-source-signature)` (`span.py:7`) and its `TODO.md` entry.

This is the parse-path work formerly gated by `TODO(backend-with-source-signature)` (exploration
§"parse path"). The backend selector, after the prerequisite, surfaces a portable `Span`/`SourceText`
source signature so the same generated parser code targets either backend.
**Staging:** the prerequisite lands first; then the parse-path stage, which is itself a
**prerequisite** for §2.6 (fltk2gsm both-backend reads), per the dependency chain in §5.

### 2.6 In-tree consumer migration (`fltk2gsm.py`) — a CHILDREN-surface concern

The reads in `fltk2gsm.py:26,147,151` are **child-span** reads, not `node.span`:
`visit_identifier` uses `identifier.child_name()`; `visit_literal`/`visit_regex` use `child_value()`.
The protocol types these as `terminalsrc.Span` (`fltk_cst_protocol.py:532,562,592`). So this migration
belongs to the **children** surface (§2.3), and the value read is a *child* span.

Two facts constrain the fix:
1. **Option B** (`native-span-start-end`): the Rust-backend child Span exposes no `.start`/`.end`, so
   `self.terminals[span.start:span.end]` is unavailable under the Rust backend. The sanctioned read is
   `span.text()` / `span.text_or_raise()`.
2. **Current Python-backend child spans are sourceless**: `terminalsrc.Span._source` defaults `None`
   (`terminalsrc.py:38`); generated parsers build child `Span(start=…, end=…)` with no source
   (`fltk_parser.py:108,117,124,…`). `text_or_raise()` on a sourceless span raises `ValueError`
   (`terminalsrc.py:55-56`, `span.rs:153-159`) — which is exactly why fltk2gsm uses
   `self.terminals[start:end]` today.

Therefore the `text()`-based read works under *neither* backend until child spans carry source.
**This migration depends on the parse-path stage (§2.5) as a prerequisite** — it is *not* independent,
contrary to a naive staging read. The parse-path stage must attach source to child spans under **both**
backends:
- Rust backend: parser builds child spans via `Span.with_source(start, end, source_text)` (§2.5).
- Python backend: parser passes the existing `SourceText`/terminals to the child `terminalsrc.Span`
  constructor so `text()` resolves. This changes *what the parser attaches*, not the `terminalsrc.Span`
  *type* (Out of scope forbids changing the type, not its source field, which already exists).

Then `fltk2gsm.py:26,147,151` become `span.text_or_raise()` (or `.text()`), working under both backends.
- Verify no other in-tree reader touches `.start`/`.end` on a span (grep gate in test plan).

### 2.7 Protocol annotation widening (additive)

`fltk_cst_protocol.py:85,114,…` annotate `span: fltk.fegen.pyrt.terminalsrc.Span`. This annotation
is generated by `gsm2tree.py` (protocol `span` at `gsm2tree.py:543`; concrete-CST `span` at
`:227`). Widen **additively** to a union admitting both backends:
`span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span`. Requirements §"Protocol annotations"
requires a strict superset: existing Python-backend consumers' type-checks must pass unedited
(union widening is additive — assignment of the old type still satisfies the union). Edit the
emission in `gsm2tree.py:543` and regenerate the protocol module. The concrete Python-CST
annotation (`gsm2tree.py:227`) is **not** widened — the Python backend's stored span type is
unchanged (requirements §"Out of scope": no change to the Python backend's CST).

`children` element types do not need widening: §2.3 preserves the Python-visible `children` shape
exactly (`list[tuple[Label|None, Child]]`), so the existing per-rule union of node classes already
covers Rust-backend child nodes (the Rust node classes are the same Python-visible classes). Only
`span` widens. Acceptance: requirements §"Protocol annotations" acceptance (a Python-backend
consumer type-checks unedited).

### 2.8 Generator changes (the single source of fix)

All node structs are generated (requirements §"In scope"). Edit `gsm2tree_rs.py`:
- `_preamble`: drop `UNKNOWN_SPAN_CACHE` / `GILOnceCell`.
- `_node_block`: emit `span: Span`, `children: Vec<(Option<Label>, Child)>`, and the per-node
  `Child` enum.
- `_new_method`: native sentinel span default; empty `Vec`.
- `_eq_method`, `_repr_method`: native (§2.4).
- `append`/`extend`/`child`/per-label accessors: source from `Vec`, translate at boundary (§2.3).
- Span getter/setter: §2.2.

Also edit `gsm2parser.py` (parser-generator child-mutation, §2.3) and `gsm2tree.py:543` (additive
protocol widening, §2.7).

**All four `*.rs` CST files are generated**, not hand-written: `src/cst_generated.rs` and
`src/cst_fegen.rs` carry the generator's exact preamble and are produced by `RustCstGenerator` (the
`make gen-rust-cst GRAMMAR=… RS_OUT=…` target, `Makefile:53-55`, drives
`fltk.fegen.genparser gen-rust-cst` → `RustCstGenerator`); `tests/test_gsm2tree_rs.py` confirms the
PoC and fegen grammars are the sources. Regenerate via:
- PoC grammar → `RS_OUT=src/cst_generated.rs`
- `fltk/fegen/fegen.fltkg` → `RS_OUT=src/cst_fegen.rs`
- the fixture grammars → `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`

then `make fix`/`cargo fmt`, then commit (CLAUDE.md §"Generated Code and Formatting"). Note: the
currently committed `src/cst_*.rs` have drifted from HEAD's generator (cosmetic: e.g. `other_label`
vs the generator's `other_kind`); the post-regen audit (§4 item-2 grep gate over the no-`PyObject`
property), **not** byte-equality to the prior committed files, is the correctness check. No file is
hand-edited.

## 3. Edge cases / failure modes

- **Non-`Span` set to `node.span`** → setter extraction fails → `TypeError` (acceptance,
  requirements §"Python binding surface"). Previously silently stored; behavior tightened
  intentionally.
- **Heterogeneous child set in `append`** (Python passes a `terminalsrc.Span` vs a node) →
  dispatch: try `Span` extract first, else match against the rule's known child node types, else
  `TypeError` naming the rule and accepted types. A child type not in the rule's model is a bug
  (parser/consumer contract violation) and must fail loudly, not store untyped.
- **Cross-backend child mixing** — a consumer appends a *Python-backend* node to a *Rust-backend*
  node. The child enum has no variant for the Python class → `TypeError`. This is correct: mixing
  backends within one tree is unsupported (requirements: a tree is one backend).
- **`children` Python getter rebuilds a list each call** → identity of the returned list is not stable
  across calls (today it returns the same `Py<PyList>`), and the rebuilt list is **not** a mutation
  handle. The in-tree consumers that mutate via the getter are the **generated parsers**
  (`result.children.extend(...)`, `fltk_parser.py:114,…`); §2.3 fixes this by changing
  `gsm2parser.py` to emit calls to the node's own `extend`/`append` methods (mutating the native
  `Vec`). After that change, no in-tree consumer mutates via the getter. Any *out-of-tree* consumer
  that mutated `node.children` in place was already relying on undocumented behavior; it must use
  `append`/`extend`. (grep gate in test plan confirms no remaining in-tree getter-mutation.)
- **Child node Python identity not stable** — `Box<ChildNode>` ownership means the getter/accessor
  wraps a fresh `Py<ConcreteNode>` per call; the same child read twice need not be the same `PyObject`.
  Tracked `TODO(rust-cst-child-node-identity)`; mitigated by a boundary `Py` cache if a consumer needs
  it. Value equality and `.kind`/`.text()` are unaffected.
- **Sentinel span equality** — native `Span` equality ignores source (`src/span.rs:71-75`), so a
  sourceless sentinel equals a source-bearing span at the same offsets. Preserved (requirements
  §Constraints "value semantics preserved").
- **Span out-of-source-bounds / non-char-boundary** in `fltk2gsm` via `text_or_raise()` → raises
  `ValueError` (existing `src/span.rs:153-191`) instead of producing a silently-wrong slice as
  `terminals[start:end]` might. Behavior change is a strict improvement; note in migration.
- **rlib + cdylib pyo3 linking** — a downstream cdylib linking a native rlib that carries
  `pyo3/extension-module` double-activates the feature → pyo3-runtime symbol/init conflict. Resolved
  by §2.1: native types live in the pyo3-runtime-free `fltk-cst-core` crate, depended on with
  `default-features = false`.

## 4. Test plan

After this change the following tests exist (TDD: write failing first):

1. **Pure-Rust node state (Rust `#[cfg(test)]` in the standalone fixture crate
   `tests/rust_cst_fixture/`, or an equivalent standalone pure-Rust crate):** construct a node
   subtree with native spans and `Box`-owned child nodes, walk it, read `span.start()/end()` (Rust
   accessors), compare two equal subtrees and two differing subtrees — **without** `Python::with_gil`
   / interpreter init. The test must run against the fixture crate's *generated* CST (which depends
   on `fltk-cst-core` as a library), **not** FLTK's extension-compiled `src/cst_*.rs` — the latter is
   linked into the `fltk._native` cdylib and cannot be exercised GIL-free in isolation. This is the
   acceptance test the native-state requirement owes; the `Box<ChildNode>` representation (§2.3) makes
   it writable. (requirements §"Native node state" acceptance.)
2. **No-Python-object audit (test/grep gate):** assert no generated CST struct field is
   `PyObject`/`Py<PyList>`/`Py<...>` for node state, and no generated file emits
   `UNKNOWN_SPAN_CACHE` / `import("fltk._native")` for state. Mechanical grep over the four
   generated files. (requirements §"Native node state" audit acceptance.)
3. **Span setter type check (Python):** `node.span = object()` raises `TypeError`; `node.span =
   fltk._native.Span(0,3)` succeeds and `node.span` returns a `fltk._native.Span` value-equal to
   the set span.
4. **Native equality (Python):** two Rust-backend nodes with equal spans+children compare equal;
   differing span or any differing child compares unequal — verified not to route through Python
   `.eq()` on stored objects (covered structurally by §2.4; behavioral test asserts results).
5. **Cross-crate construction (downstream fixture, Rust):** a fixture crate constructs `Span`
   (sourceless and with-source) and a node holding child nodes via the **public** Rust API, reads
   back start/end and children, compiles and runs without touching `pub(crate)` fields.
   (requirements §"Public Rust construction/access" acceptance.)
6. **Parse path (Python, Rust backend):** parsing input yields a tree whose spans are
   `fltk._native.Span`, stored children are native CST nodes (not `terminalsrc.Span`), and
   `node.span.text()` returns the spanned source. (requirements §"Parse path" acceptance.)
7. **fltk2gsm under both backends (Python):** the existing fltk2gsm conversion path passes its tests
   under **both** the Python and Rust CST backends after the `text()`/`text_or_raise()` migration.
   **Depends on the parse-path stage** (§2.5/§2.6): child spans must carry source under both backends,
   else the `text()` read raises `ValueError`. Test asserts both-backend success. (requirements
   §"In-tree consumer migration" acceptance.)
8. **Protocol additive-widening (pyright):** a Python-backend-only consumer that type-checks
   against the protocol with the current `terminalsrc.Span` usage still type-checks unedited after
   widening. (requirements §"Protocol annotations" acceptance.)
9. **Cross-backend behavioral equivalence (Python):** `.text()`, `.kind`, `len`/`is_empty`, child
   accessor results, node equality match across backends; repr explicitly excluded
   (requirements §"Behavioral equivalence").

## 5. Open questions

Genuine user-judgment items only. Three items raised in earlier drafts (child representation, build-crate
structure, getter-identity) are now **decided** in §2 (native `Box<ChildNode>`; split `fltk-cst-core`
crate; parser-generator routes mutation through node methods) because each was an acceptance-criterion
gap or a fact-determined choice, not a judgment call.

- **Delivery staging order.** Scope is fixed; ordering is the requester's call. The dependency chain is
  now firm: **`backend-with-source-signature` (§2.5 prerequisite) lands first**; the **parse-path stage
  (§2.5) is a prerequisite** for the fltk2gsm migration (§2.6) and for the both-backend `text()` reads,
  because child spans must carry source under both backends. A valid staging: (0) prerequisite
  `backend-with-source-signature` (portable `SourceText` constructor); (1) span-field native + native
  equality + `fltk-cst-core` split; (2) native children (`Box` enum) + parser-generator child-mutation
  change; (3) parse-path source-bearing child spans + fltk2gsm migration. Stages 1–2 can land without
  stage 3 only if fltk2gsm's reads are left on a backend that still has sourced/extent access — i.e.
  fltk2gsm stays Python-backend-only until stage 3.

USER DECISION: Implementation will be incremental and the implementers can sequence this in whatever way works.

A follow-on, not blocking:
- `TODO(rust-cst-child-node-identity)` — native child ownership drops Python child-object identity
  stability through the getter (§2.3, §3). Add a boundary `Py` cache only if a real consumer needs it.
