# Design: named children mutators on both backends (insert / remove_at / replace_at / clear)

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md`, this dir. Exploration: `exploration.md`, this dir.

## 1. Root cause / context

The cross-backend mutation API is append-only: `append`, `extend`, `append_<lbl>`, `extend_<lbl>`, `extend_children` (`gsm2tree.py:268-290`, `gsm2tree_rs.py:911-1009`). Tree rewriting (remove / replace / insert / clear) has no supported path on the Rust backend — `node.children` is a per-call snapshot (`_children_getter`, `gsm2tree_rs.py:875`), so in-place mutation is a silent no-op — and only the accidental live-list path on Python (`children` is a bare dataclass field, `gsm2tree.py:258-260`; the pattern is test-banned in generated parser code, `fltk/fegen/test_genparser.py:135-163`).

The live-proxy alternative was rejected in triage (user-ratified; request.md "Background"). This design adds named, index-addressed mutators with identical names, semantics, and error behavior on both backends.

## 2. Proposed approach

### 2.1 Python-visible API (identical on both backends)

Four methods on every generated node class. `{child}` is the node's existing child-annotation union; `{label}` is `Optional[ClassName.Label]` (or `None` for label-free nodes) — same annotations `append`/`child()` already use.

| Method | Signature | Returns | Semantics |
|---|---|---|---|
| `insert` | `insert(index: int, child: {child}, label: {label} = None)` | `None` | Insert `(label, child)` at `index`. CPython `list.insert` index semantics: negative indices count from the end; out-of-range clamps (never raises for valid args; identical behavior for arbitrarily large ints, §3). |
| `remove_at` | `remove_at(index: int)` | `tuple[{label}, {child}]` | Remove and return the entry at `index`. Negative indices supported; out of range after normalization → `IndexError`. |
| `replace_at` | `replace_at(index: int, child: {child}, label: {label} = None)` | `None` | Replace the entire entry at `index` with `(label, child)`. Same index rules as `remove_at`. `label=None` means *unlabeled* — it does **not** preserve the old label (consistent with `append`/`insert`, where `None` = unlabeled). |
| `clear` | `clear()` | `None` | Remove all children. |

**Naming rationale** (deliberate, hard-to-reverse — CLAUDE.md public-API rule):
- `insert` / `clear` reuse `MutableSequence` vocabulary — semantics are instantly familiar, and argument order extends `append(child, label=None)` by prepending `index`.
- `remove_at` / `replace_at` deliberately avoid bare `remove` (list-land `remove(value)` is by-value; ours is by-index) and avoid `__setitem__`/`__delitem__` (the rejected proxy direction). The `_at` suffix signals index addressing.
- `remove_at` returns the removed entry (pop-style): move/reorder idioms (`lbl, ch = node.remove_at(i); node.insert(j, ch, lbl)`) need no separate read; costs nothing on either backend. The tuple shape matches `child()`'s return.
- `replace_at` returns `None` (assignment-like, matching `__setitem__` convention); callers wanting the old entry read `children[index]` first.

**Collision check**: per-label generated names are all prefixed (`append_`, `extend_`, `children_`, `child_`, `maybe_` + label), so a label can never produce a bare `insert`/`remove_at`/`replace_at`/`clear`. No `insert_<lbl>`/`remove_<lbl>`/`replace_<lbl>`/`clear_<lbl>` per-label family is added, so no label can collide with the new fixed names either. `_RESERVED_LABELS` (`gsm2tree_rs.py:24-26`) needs no new entries; a test pins this reasoning (§4.1).

### 2.2 Error behavior (pinned cross-backend)

| Case | Exception | Message (identical text both backends) |
|---|---|---|
| `remove_at`/`replace_at` index out of range | `IndexError` | `"{ClassName}.{method}: index {index} out of range ({n} children)"` — `{index}` is the caller's original (possibly negative) value |
| label not `None` and not this node's Label enum | `TypeError` | Rust's existing `_label_from_pyobject_match` text: `"{ClassName}.{method}: label argument is not a {ClassName}_Label; got {type}"` (label-free nodes: `"{ClassName}.{method}: no labels defined for this node; got {type} label"`) |
| child not an allowed child type | `TypeError` | Rust's existing `extract_from_pyobject` text: `"{ClassName}: unsupported child type {type}"` |
| non-index-able index | `TypeError` | index conversion follows `__index__` semantics on both backends (Python: `operator.index`; Rust: `PyNumber_Index`-equivalent normalization, §2.3); message backend-specific, type pinned, text not |

The Python backend bounds-checks and type-checks explicitly (it does not lean on CPython's `list` error text) so messages match Rust exactly. If PyO3's `get_type().name()` and Python's `type(x).__name__` render a type differently in practice, the Python side conforms to the Rust rendering (parity tests assert exact message equality, so any drift fails loudly).

**Validation parity decision**: the new mutators type-check `label` and `child` on BOTH backends. This makes the Python backend's new methods stricter than its grandfathered permissive `append`/`extend` (which stay unchanged — tightening them is a back-compat break, out of scope per request non-goals). Deliberate asymmetry: new API is strict from day one; old API keeps its contract.

Python-side child validation: `isinstance` against the node's allowed concrete classes (same module) plus span types. Span types are resolved lazily — `terminalsrc.Span` always; `fltk._native.Span` only via `sys.modules.get("fltk._native")` — so the generated module still never imports the native extension at runtime (preserves pure-Python importability, matching the existing TYPE_CHECKING-guard pattern, `gsm2tree.py:179-200`). If `fltk._native` is not loaded, no native Span instance can exist, so the lazy check is complete.

**Node classes are symmetric; span acceptance is deliberately asymmetric.** Node classes mirror: each backend accepts its own node classes and rejects the other backend's (Rust's `extract_from_pyobject` already rejects Python dataclass nodes). Spans do not mirror: the **Python backend accepts both** `terminalsrc.Span` and `fltk._native.Span` — the `pyrt.span` backend selector can put native spans into Python-backend trees, so rejecting them would break legitimate trees. The **Rust backend accepts only native spans** (local pyclass or cross-cdylib `fltk._native.Span` via `extract_span`, `crates/fltk-cst-core/src/cross_cdylib.rs:256-281`); a pure-Python `terminalsrc.Span` falls through to the `"{ClassName}: unsupported child type {type}"` TypeError. The asymmetry is forced by representation — Rust nodes store a native `Span` struct and cannot hold a pure-Python span. Consequence for tests: cross-backend span hand-in is **excluded from the exact-parity matrix** (§4.2); per-backend tests pin each side's span acceptance separately.

### 2.3 Rust backend (`gsm2tree_rs.py`)

New emitter methods on `RustCstGenerator`, wired into `_node_block` after `_generic_child` (around `gsm2tree_rs.py:790`):

**Index handling (shared helper, all three indexed methods):** pymethods take `index: &Bound<PyAny>` (not `i64`) so index semantics match the Python backend for arbitrary int magnitude. Before the lock: normalize via `PyNumber_Index`-equivalent (`__index__` semantics, matching Python's `operator.index`; failure → backend-specific `TypeError`, §2.2), then attempt `i64` extraction. On overflow (value beyond `i64`): the sign alone determines the outcome — `insert` clamps (negative → 0, non-negative → `len`); `remove_at`/`replace_at` raise the §2.2 `IndexError`, formatting the caller's original value via `str()`. No `OverflowError` ever escapes.

- `_generic_insert(class_name, enum_name, labels)` — pymethod `fn insert(&self, py, index: &Bound<PyAny>, child: &Bound<PyAny>, label: Option<PyObject>)`. Normalize index (above), extract child via `{Enum}::extract_from_pyobject` and label via the `_label_from_pyobject_match` arms (reused with `method_name="insert"`) — all **before** taking the write lock. Under the lock: `n = guard.children.len()`, clamp (`if index < 0 { max(n + index, 0) } else { min(index, n) }` in `usize`-safe arithmetic), `Vec::insert`.
- `_generic_remove_at(...)` — pymethod `fn remove_at(&self, py, index: &Bound<PyAny>) -> PyResult<PyObject>`. Index conversion (above) before the lock. Under the write lock: resolve negative index against `len`, bounds-check, `Vec::remove`, capture the entry; **drop the guard**, then convert `(label, child)` to a Python tuple (label via `into_pyobject`, child via `to_pyobject` → registry wrap-out). `IndexError` constructed/returned outside the guard scope.
- `_generic_replace_at(...)` — normalize index and extract child+label outside the lock (as `insert`); under the lock: bounds-check, `let old = std::mem::replace(&mut guard.children[idx], entry);`; drop guard; `drop(old)` after release.
- `_generic_clear(...)` — under the write lock: `let old = std::mem::take(&mut guard.children);`; drop guard; `drop(old)` after release.

Lock discipline (the hard invariant, `_span_getter_setter` comments `gsm2tree_rs.py:836-851`): all Python work (extraction, registry calls, wrap-out) happens strictly outside the guard. Old entries from `replace_at`/`clear` are dropped after guard release so a deep recursive `Arc` drop chain never runs while the parent lock is held (pure-Rust-safe either way, but keeps lock hold times bounded).

**Native (GIL-free) mutators: emitted.** Symmetry with the existing native write surface (`push_child`, `extend_children`, `append_<lbl>`, `extend_<lbl>`) — generated Rust parsers and native consumers get the same editing capability. Added to the plain `impl {ClassName}` block:

- `pub fn insert_child(&mut self, index: usize, label: {label_type}, child: {Enum})` — delegates to `Vec::insert`; panics on `index > len` (Vec convention; native callers bounds-check, Python-facing clamping lives in the pymethods).
- `pub fn remove_child(&mut self, index: usize) -> ({label_type}, {Enum})` — `Vec::remove`; panics on out-of-range.
- `pub fn replace_child(&mut self, index: usize, label: {label_type}, child: {Enum}) -> ({label_type}, {Enum})` — `mem::replace`; returns old entry; panics on out-of-range.
- `pub fn clear_children(&mut self)`.

Naming follows the `push_child` precedent; none of these can collide with per-label native names (all prefixed; no `insert_`/`remove_`/`replace_`/`clear_` per-label prefixes exist). Panic-vs-`Result` divergence from Python clamping/IndexError semantics is documented in each method's doc comment.

`generate_pyi` (`gsm2tree_rs.py:127`) gains the four method stubs per class, using the same `_pyi_annotation_for_model_types` machinery as `append`/`child` (`remove_at` returns the `child()` tuple type).

**Registry snapshot binding (test support):** `registry::snapshot` (`crates/fltk-cst-core/src/registry.rs:137`) is `pub` Rust-side but currently has no Python binding anywhere (`src/lib.rs` exports only `Span`/`SourceText`/`UnknownSpan` + node classes). The generator emits a module-level `#[pyfunction] fn _registry_snapshot(py) -> PyResult<Bound<PyDict>>` wrapping it, registered in `register_classes` — underscore-prefixed, documented as test/debug-only, deliberately omitted from the `.pyi` stub. Emitted per generated module because the registry static is per-cdylib; the snapshot must come from the cdylib whose nodes are under test. Required by the §4.3 registry-eviction test.

### 2.4 Python backend (`gsm2tree.py`)

In `py_class_for_model`, after `child_fn` (`gsm2tree.py:306`), emit four methods:

- All three indexed methods first convert via `operator.index(index)` (matches Rust's `__index__` normalization, §2.3; CPython's `TypeError` text is the backend-specific message).
- `insert`: validate label + child (raise per §2.2), then `self.children.insert(idx, (label, child))` — CPython gives clamping for free, including arbitrarily large ints.
- `remove_at`: explicit normalize/bounds-check (for message parity; the `IndexError` formats the caller's original value), then `return self.children.pop(idx)` using the normalized index.
- `replace_at`: validate label + child, normalize/bounds-check, `self.children[idx] = (label, child)`.
- `clear`: `self.children.clear()` — no validation needed.

Validation helpers are emitted per class (they reference the class's `Label` enum and allowed child classes); the lazy native-Span lookup (§2.2) is a small module-level helper emitted once per generated module.

In `_protocol_class_for_model` (`gsm2tree.py:623`), add the four method stubs with the same annotations, between `child` and the per-label quintet — mirroring the concrete order.

### 2.5 Registry / identity (Rust)

No registry mutation is needed; existing semantics compose:

- **Removal/replace/clear** drop `Arc` clones from the parent's `Vec`. The registry (weak-valued, keyed by `arc_ptr`) is unaffected: a live Python handle owns its own `Arc` (`inner: Shared<T>`), so the removed child node survives as long as its handle does — same observable behavior as the Python backend, where a removed child object survives while referenced.
- **`remove_at`'s return value** wraps the child via `to_pyobject` → `registry::get_or_insert_with`: returns the existing canonical handle if one is alive, else mints and registers one (the returned handle then keeps the node alive). Identity is `is`-stable with any previously obtained handle for the same child.
- **Re-insertion** of a removed child's handle goes through `extract_from_pyobject` → `register_if_absent` — the same hand-in path `append` uses; subsequent reads return the same handle.
- **Full drop**: if no Python handle survives removal, the `Arc` count reaches zero, the node frees, and the weak registry entry self-evicts; `arc_ptr` reuse is already handled by weakref semantics (dead entry replaced on next insert).

No new corruption pathway exists; §4.3 pins these properties.

### 2.6 Files changed / regenerated

Generators: `fltk/fegen/gsm2tree.py` (dataclass methods, protocol stubs), `fltk/fegen/gsm2tree_rs.py` (pymethods, native methods, `.pyi` stubs).

Regenerated committed artifacts: `gsm2tree.py`/`gsm2tree_rs.py` changes touch **every** generated CST module — run `make gencode` (Makefile:147-186), then `make fix`, commit, per CLAUDE.md. The full set it covers: Python CST + protocol for fegen (`fltk/fegen/fltk_cst.py`, `fltk_cst_protocol.py`), bootstrap (`fltk/fegen/bootstrap_cst.py`, `bootstrap_cst_protocol.py`), toy (`fltk/unparse/toy_cst.py`, `toy_cst_protocol.py`), unparsefmt (`fltk/unparse/unparsefmt_cst.py`, `unparsefmt_cst_protocol.py`); Rust CST for `src/cst_fegen.rs` (+ `fltk/_native/fegen_cst.pyi`), `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, and `crates/fltk-cst-spike/src/cst.rs` (cp of `cst_generated.rs`). Do not regenerate a subset: `make check`'s regen-then-diff cheat-detection and the `rust_cst_fegen` staleness check fail on partial regeneration.

TODO bookkeeping: delete the `rust-cst-children-list-view` entry (`TODO.md:23`) and the `TODO(rust-cst-children-list-view)` comment in `_children_getter`'s docstring (`gsm2tree_rs.py:881`); replace the docstring note with a pointer to the named mutators and this ADR. (Also fixes the stale 682–700 line citation flagged in exploration §1.)

## 3. Edge cases / failure modes

- **`insert` clamping**: `insert(10**6, c)` on a 2-child node appends; `insert(-10**6, c)` prepends. Pinned by parity tests. Chosen over strict bounds because it is exactly `list.insert` (least surprise) and the Python backend gets it by direct delegation.
- **`replace_at` label footgun**: omitting `label` clears the old label rather than preserving it. Documented in generated doc comments/stubs; pinned by a parity test. Consistency with `append`/`insert` (where `None` = unlabeled) wins over convenience; "preserve" semantics would make `None` ambiguous.
- **Indices beyond `i64`**: identical cross-backend behavior — `insert` clamps by sign; `remove_at`/`replace_at` raise the pinned `IndexError` (no tree has 2^63 children, so any beyond-`i64` index is out of range by definition). Achieved by taking `index` as `&Bound<PyAny>` on Rust with sign-based overflow handling (§2.3); cost is one normalization step per call. Pinned by parity tests (§4.2). Satisfies the request's "index semantics must match between backends" verbatim — no `OverflowError` divergence.
- **`bool` index**: `int` subclass, accepted as 0/1 on both backends (`__index__` normalization agrees). No special handling.
- **Empty node**: `remove_at(0)` → `IndexError` with `(0 children)`; `clear()` is a no-op; `insert(k, c)` for any `k` inserts at 0.
- **Self-insertion / cycles**: `node.insert(0, node)` creates a cycle, exactly as the existing `append` already permits (extraction happens before the write lock; no same-thread lock re-entry). Pre-existing exposure; not widened, not fixed here.
- **Concurrent mutation**: all writes go through the node's `RwLock`, same as `append`. A Python-side reader iterating a `children` snapshot sees a stale-but-consistent view (Rust) or the live list (Python) — pre-existing divergence, unchanged (request non-goal).
- **Span children through `remove_at`**: spans are wrapped fresh per call (`span_to_pyobject`); spans have no identity guarantee — consistent with the `children` getter.
- **Validation order**: both backends validate child/label *before* touching the children list (Rust: extraction precedes the lock; Python: explicit checks precede mutation), so a failed call never partially mutates. For `insert`/`replace_at` with both a bad index and a bad child, the child/label `TypeError` wins on Rust (extraction first); the Python implementation checks in the same order so the surfaced error matches.

## 4. Test plan

### 4.1 Generator emission tests
- `tests/test_gsm2tree_py.py` / `tests/test_gsm2tree_rs.py` (existing patterns): generated source for the fixture grammar contains the four pymethods, the four native methods, the protocol stubs, and the `.pyi` stubs with expected signatures.
- Reserved-name regression: a unit test asserting no per-label name pattern can equal any fixed mutator name (guards the §2.1 collision reasoning against future per-label families).

### 4.2 Cross-backend behavior parity (new module, e.g. `tests/test_cst_mutators_parity.py`)
Parametrized over both backends' fegen CST modules, asserting identical resulting trees (kind/label/span sequences) and — for errors — identical exception type and message text:
- `insert` at head/middle/tail; negative indices; clamping both directions; labeled and unlabeled.
- `remove_at` positive/negative; returned `(label, child)` equals the prior `children[index]` entry; out-of-range and empty-node `IndexError`.
- `replace_at` preserves order/length; `label=None` clears the label; out-of-range `IndexError`.
- `clear` on populated and empty nodes.
- Bad label type (`TypeError`, exact message); non-`None` label on a label-free node; bad child type (`TypeError`, exact message); non-index-able index (`TypeError`, type only).
- Beyond-`i64` indices (e.g. `±10**25`): `insert` clamps both directions; `remove_at`/`replace_at` raise `IndexError` with exact message (§3).
- Mixed operation sequences (interleaved insert/remove/replace/append) produce identical trees.
- Span hand-in is per-backend, not parity (§2.2 asymmetry): Python accepts `terminalsrc.Span` and (when loaded) `fltk._native.Span`; Rust accepts native spans and rejects `terminalsrc.Span` with the unsupported-child-type `TypeError`.

### 4.3 Rust identity tests (extend `tests/test_rust_cst_poc.py` or sibling)
- Handle obtained before `remove_at` remains valid and usable after removal.
- `remove_at` return value `is` the previously obtained handle for that child (node children only; spans carry no identity guarantee, §3).
- Removed child re-inserted via `insert`/`append` → subsequent `children` reads return the same handle (`is`-stable).
- `replace_at`: evicted child's externally held handle unaffected; new child read back `is`-stable.
- Registry eviction: take a handle to a child, confirm its entry appears in `_registry_snapshot()` (the test-support binding, §2.3); `clear()`, drop the handle, force GC; assert the entry is **absent** from the snapshot and a weakref to the handle is dead. Pins two things a naive weakref-only test would not: `clear()` leaks no strong handle references, and the registry self-evicts after removal (the §2.5 claim).

### 4.4 Rust native tests
`cargo test` in `tests/rust_cst_fixture`: `insert_child`/`remove_child`/`replace_child`/`clear_children` happy paths; `#[should_panic]` for out-of-bounds `insert_child`/`remove_child`/`replace_child`.

### 4.5 Suites / gates
Existing conformance and stub checks pass after regeneration (`typecheck_fegen_cst_conformance.py`, `test_fltk_native_stub.py`, `test_clean_protocol_consumer_api.py`); `uv run pytest`, `cargo test`, `make check` clean.

## 5. Open questions

None. Judgment calls resolved inline: signatures/index semantics including beyond-`i64` parity (§2.1-2.3, §3), span-acceptance asymmetry (§2.2), strict validation on new Python-backend methods (§2.2), native mutators emitted with Vec panic conventions (§2.3), `remove_at` returns the removed entry / `replace_at` returns `None` (§2.1).
