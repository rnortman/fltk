# Design: stop cloning the full children Vec in Python-facing CST accessors

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` in this dir. Facts: `exploration.md`, `exploration-accessor-clone-archaeology.md`.

## Root cause / context

Four `#[pymethods]` accessor emitters in `fltk/fegen/gsm2tree_rs.py` generate the pattern: clone the ENTIRE children `Vec` under the read guard, drop the guard, then filter/index the snapshot. Cost is O(total-children) clones per call (Arc refcount bump per node child, `Span` copy per terminal child, label enum copy per entry) regardless of how many children match:

- `_generic_child` — `child()` pymethod (`gsm2tree_rs.py:1011-1036`).
- `_per_label_methods` — `children_<label>` (1387-1404), `child_<label>` (1410-1435), `maybe_<label>` (1440-1465).

The snapshot itself is architecturally required: the project invariant is **no Python work while holding a node lock** (documented at `_span_getter_setter` 836-851, `_children_getter` 887-909, `_generic_extend_children` 988-1009; mandated by design ADR `2026/06/10-rust-idiomatic-cst-api` design.md:218). The inefficiency is solely that the snapshot includes non-matching entries. Native (GIL-free) accessors in `_native_per_label_methods` were already made zero-alloc (deep-review disposition `efficiency-1`); they are out of scope.

## Proposed approach

Edit the four emitters so label filtering / length checking happens **under** the read guard (cheap pure-Rust comparisons), cloning only what the post-guard Python conversion needs. All `to_pyobject` / `into_pyobject` / exception-raising work stays outside the guard, preserving the lock-discipline invariant. Each emitted site keeps a lock-scope comment in the existing style (cf. `_span_getter_setter`).

### `_generic_child` → `child()` pymethod

Under the guard: read `children.len()`; if exactly 1, clone only `children[0]` (one `(Option<Label>, Child)` tuple clone). Drop guard. If len != 1, raise `PyValueError` with the existing message `"Expected one child but have {n}"` (n captured under the guard as `usize`); otherwise convert label + child to Python objects and build the tuple. Emitted shape:

```rust
// Lock scope: read len and clone at most the single entry under the guard;
// drop the guard before any Python work (object conversion, exception raise).
let (n, entry) = {
    let guard = self.inner.read();
    let n = guard.children.len();
    let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
    (n, entry)
};
let Some((label, child)) = entry else {
    return Err(PyValueError::new_err(format!("Expected one child but have {n}")));
};
// label/child conversion as today, operating on owned values (no .clone() needed)
```

Error paths (n == 0 or n > 1) now clone nothing.

### `children_<label>`

Under the guard: iterate `children`, compare labels, clone only the matching `Child` values into a `Vec<{Class}Child>` (labels are not cloned — the return shape is a list of children only, unchanged). Drop guard. Build the `PyList` by calling `to_pyobject` per element, in order, as today. Emitted shape:

```rust
// Lock scope: filter by label under the read guard, cloning only matching
// children (Arc bump or Span copy each); drop the guard before to_pyobject,
// which performs Python work that must not happen while a node lock is held.
let matching: Vec<_> = {
    let guard = self.inner.read();
    guard.children.iter()
        .filter(|(lbl, _)| *lbl == Some({LabelEnum}::{Variant}))
        .map(|(_, child)| child.clone())
        .collect()
};
let result = PyList::empty(py);
for child in &matching {
    result.append(child.to_pyobject(py)?)?;
}
Ok(result.unbind())
```

O(matching) clones; zero clones and an unallocated empty `Vec` when nothing matches.

### `child_<label>` and `maybe_<label>`

Under the guard: single scan counting label matches and cloning only the **first** match (one `Child` clone, no `Vec`). Drop guard. Then:

- `child_<label>`: if count != 1, raise `PyValueError` with the existing message `"Expected one {label} child but have {count}"` (exact count preserved — pinned by `tests/test_rust_cst_poc.py:109`); else convert the cloned child.
- `maybe_<label>`: if count > 1, raise the existing fixed-text `"Expected at most one {label} child but have at least 2"`; if count == 0, `Ok(None)`; else convert.

Emitted scan shape (shared by both, mirroring the existing count/found loop, moved inside the guard with `clone` replacing `to_pyobject`):

```rust
// Lock scope: count label matches and clone only the first under the guard;
// drop the guard before to_pyobject / exception raise (Python work).
let (count, first) = {
    let guard = self.inner.read();
    let mut count = 0usize;
    let mut first = None;
    for (lbl, child) in &guard.children {
        if *lbl == Some({LabelEnum}::{Variant}) {
            count += 1;
            if count == 1 {
                first = Some(child.clone());
            }
        }
    }
    (count, first)
};
```

The full scan is kept (no early exit at count == 2) for uniformity with `child_<label>`'s exact-count message and minimal generator divergence; remaining iterations are label compares only.

### TODO removal and bookkeeping

- Delete all four `TODO(rust-cst-accessor-clone-efficiency)` comments from `gsm2tree_rs.py` (1014-1016, 1388-1390, 1411, 1441).
- Delete the `rust-cst-accessor-clone-efficiency` entry from `TODO.md` (line 27).

### Files changed

- `fltk/fegen/gsm2tree_rs.py` — `_generic_child`, `_per_label_methods` (the three read emitters; `append_<label>`/`extend_<label>` untouched).
- `TODO.md` — remove entry.
- Regenerated outputs via `make gencode` (covers `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, and `crates/fltk-cst-spike/src/cst.rs` via the `cp` step) then `make fix`. All six generated `.rs` files currently carry the TODO comments; regeneration removes them.
- One new regression test (see Test plan).

No public API change: method names, signatures, return shapes, and error messages are identical. No native-accessor change. No `fltk-cst-core` change.

## Edge cases / failure modes

- **Lock discipline preserved.** Everything under the guard is pure Rust: label enum `PartialEq`, `usize` arithmetic, `Child::clone` (Arc bump / `Span` copy). `format!`, `PyValueError::new_err`, `to_pyobject`, `into_pyobject` all execute after the guard drops. Reviewers should reject any Python call inside the guard block.
- **Snapshot atomicity unchanged.** Each call still takes exactly one read guard and observes one consistent children state; concurrent-writer visibility semantics are identical to today.
- **Error-path conversion side effect removed (deliberate, unobservable).** Today, `child_<label>`/`maybe_<label>` with count > 1 call `to_pyobject` on the first match *before* raising, which (a) mints/registers a canonical Python handle as a side effect and (b) could in principle surface a `to_pyobject` error instead of the `ValueError`. The new shape raises without converting. (a) has no lasting effect: the registry is weak-valued, so an error-path handle held by nothing is evicted immediately, and the next successful read mints the canonical handle identically. (b) is unreachable in practice — `to_pyobject` fails only on allocation/registry failure — and validate-before-convert is the strictly more correct ordering. No documented result or error changes.
- **`children_<label>` partial-failure behavior unchanged.** Conversion still happens element-by-element in child order after the guard; a failing `to_pyobject` mid-list propagates at the same point and discards the partial list, as today.
- **Clippy gate.** Generated code must pass `cargo clippy -- -D warnings`. The Makefile clippy targets (`cargo-clippy`, `cargo-clippy-no-python`) gate the workspace (root, fltk-cst-core, fltk-cst-spike, fltk-parser-core) plus the `tests/rust_cst_fegen` and `tests/rust_parser_fixture` crates; `tests/rust_cst_fixture` is compile-checked only via maturin/pytest (`Makefile:106`), but the changed pymethod templates are label-agnostic and identical across grammars, so any lint would surface in the clippy-gated outputs. The shapes above avoid known lint traps: `filter`+`map`+`collect` is idiomatic; the `let (count, first) = { ... }` block has no redundant-clone or needless-collect pattern. Any lint that does fire is fixed in the generator template, never hand-patched in generated files (`make gencode` drift check enforces this).
- **Rules with no labels / span-only children.** `_generic_child` is emitted for every rule; the per-label emitters only for labeled rules. The new shapes are label-agnostic templates (same as the current ones), so no per-shape branching changes are needed in the generator.

## Test plan

After the change:

- Existing pinned behavior tests pass unchanged: `tests/test_rust_cst_poc.py` (exact error messages incl. counts, lines 109-181), `tests/test_fegen_rust_cst.py:280`, `tests/test_phase4_rust_fixture.py`, `tests/test_phase4_fegen_rust_backend.py`, plus `cargo test` in the fixture crates (`make test-native-parser`, `make test-rust-parser-fixture`).
- New regression pin (invited by request §Verification): one test in `tests/test_rust_cst_poc.py` building a node with many children under one label and zero-or-few under another, asserting `children_<label>` returns exactly the matching subset in order, `child_<label>`/`maybe_<label>` return/raise correctly, and `child()` raises with the correct count — guarding the filter-under-guard logic against off-by-label regressions. Identity assertion (same child read twice `is` the same handle) included to pin the registry path.
- Full gates: `uv run pytest`, `make check` (clippy + drift + format) clean.

## Open questions

None. The only judgment call — dropping the error-path `to_pyobject` side effect — is resolved in Edge cases: unobservable through the documented API; all raised error types and messages unchanged.
