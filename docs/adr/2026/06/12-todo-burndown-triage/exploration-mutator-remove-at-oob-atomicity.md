# Adversarial validation: `mutator-remove-at-oob-atomicity` TODO

Style: concise, precise, token-dense. No padding, no preamble. All claims anchored to file:line.

---

## 1. Does the generated `remove_at` actually have the described ordering?

**Yes — confirmed in both the emitter and the generated artifact.**

Emitter template: `fltk/fegen/gsm2tree_rs.py:1313-1363` (`_generic_remove_at`).
Generated artifact (Grammar node): `src/cst_fegen.rs:742-787`.

Exact sequence (Grammar node, lines reference `src/cst_fegen.rs`):

1. `orig_str` capture (l.745) and `operator.index` call (l.749-752) — before any lock.
2. `maybe_i64` extraction (l.754).
3. Write lock acquired (l.758): resolve negative index against `len`, bounds-check, `Vec::remove` (l.770) — child extracted from Vec under lock.
4. Write lock released at end of the block (l.773).
5. **After lock release**: label `into_pyobject` (l.783`?`) and child `to_pyobject` (l.785`?`) — both fallible.
6. `PyTuple::new` (l.786`?`) — fallible.

The `Rule` node instance is at `src/cst_fegen.rs:1690-1735`; `Alternatives` at `src/cst_fegen.rs:2647-...`; all generated nodes follow the identical template via `_generic_remove_at`.

---

## 2. Is `Py::new` inside `registry::get_or_insert_with` the only fallible step after removal?

**No. There are at least four fallible steps after `Vec::remove`, in order:**

### 2a. Label `into_pyobject` (l.783, `src/cst_fegen.rs`)

```rust
Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
```

`GrammarLabel` is a `#[pyclass(frozen)]` (l.135). PyO3's `IntoPyObject` for a `#[pyclass]` type calls `Py::new` internally on a registry-miss, or returns a reference-bumped existing object on a hit. Either path can fail. Also: `.into_any()` itself calls PyO3 type coercion and is `?`-propagated (`?` is on `.into_any().unbind()` chain in context). The `?` on line 783 means a label wrap-out failure drops the child before returning the error.

### 2b. `child.to_pyobject(py)?` (l.785)

`GrammarChild::to_pyobject` (`src/cst_fegen.rs:212-228`) calls `registry::get_or_insert_with` (l.216 or l.223), which:
- calls `lookup` → `get_registry` → potentially `py.import("weakref")` (first call only; `GILOnceCell`), then `WeakValueDictionary.get` — all fallible.
- On miss: calls `make_handle = || Py::new(py, handle)` (l.218 or l.225) — `Py::new` allocates the Python heap object; can return `PyErr` on `MemoryError`.
- Then `register_if_absent` → `get_registry` again + `setdefault` call (l.72) — fallible.

### 2c. `PyTuple::new(py, [label_obj, child_obj])?` (l.786)

`PyTuple::new` allocates a Python tuple; can fail on `MemoryError`.

### 2d. Registry internals (within `get_or_insert_with`, `crates/fltk-cst-core/src/registry.rs`)

`lookup` calls `get_registry` (`registry.rs:50-58`) which can fail on first init (imports `weakref`, creates `WeakValueDictionary` — `registry.rs:37-44`). After init, calls `WeakValueDictionary.get` (`registry.rs:53`) — fallible (Python method call). `arc_addr.into_pyobject(py)?` (`registry.rs:52`) converts `usize` to Python int — can fail on `MemoryError`. All `?`-propagated back to the caller.

**Summary of failure modes after Vec::remove:**

| Step | File:line | Can fail on |
|------|-----------|-------------|
| `lbl.into_pyobject(py)?` | `cst_fegen.rs:783` | `MemoryError`; pyclass allocation failure |
| `lookup` in `get_or_insert_with` | `registry.rs:111` | `MemoryError` (int key alloc); `WeakValueDictionary.get` failure |
| `Py::new(py, handle)` in `make_handle` | `cst_fegen.rs:218,225` | `MemoryError` |
| `register_if_absent` → `setdefault` | `registry.rs:72` | `MemoryError`; dict mutation failure |
| `PyTuple::new` | `cst_fegen.rs:786` | `MemoryError` |

OOM is not the only failure mode in principle. `weakref` module import can theoretically fail (interpreter shutdown, corrupted `sys.modules`). During interpreter finalization, any Python object protocol call can fail. `WeakValueDictionary` methods can raise if the dict is concurrently finalized (pathological state). In practice these are indistinguishable from "unreachable" for normal operation.

---

## 3. Is the "atomic: either returns (label, child) or does nothing" contract stated or documented anywhere?

**The exact quoted text does not appear verbatim in any code or docstring.** Occurrences:

- `TODO.md:34` — states the contract verbatim, but this is the TODO entry itself (the claim being evaluated), written by the TODO author.
- `docs/adr/2026/06/11-cst-named-mutators/notes-deep-error-handling.md:28` — the reviewer's finding states: "the semantic contract of 'atomic: either returns (label, child) or does nothing' is violated."

The contract is **not** in any docstring, generated doc comment, `.pyi` stub, or inline comment on `remove_at` itself. The design doc (`docs/adr/2026/06/11-cst-named-mutators/design.md`) does not state an atomicity guarantee for `remove_at` under wrap-out failure. Section §3 "Edge cases / failure modes" (`design.md:110-120`) does not mention wrap-out failure. Section §2.5 (`design.md:91-99`) addresses registry identity semantics but not wrap-out failure atomicity.

The `_generic_remove_at` docstring (`gsm2tree_rs.py:1314-1321`) mentions the issue only via the `TODO(mutator-remove-at-oob-atomicity)` comment (l.1318-1319), which describes the hazard. No docstring states "this is atomic."

**Conclusion: the "atomic" contract is claimed in the TODO and the deep-review finding, but is not formally documented anywhere in code, docstrings, or the design doc as a stated invariant.**

---

## 4. Does the proposed "wrap-before-remove" fix have a TOCTOU hazard?

The TODO proposes: "clone the Arc (read-lock snapshot) and attempt `to_pyobject` before acquiring the write lock for removal; only remove if wrap-out succeeds."

**Yes, this introduces a TOCTOU hazard.** Between releasing the read lock used for the Arc clone and acquiring the write lock for removal:

- A concurrent writer could `remove_at(idx)` the same element, changing the Vec length and shifting indices.
- The same index `idx` now points to a different element; the write-lock removal removes the wrong element.
- Or the concurrent `remove_at` removes the target element first, and then this removal either panics (OOB) or removes a different element.

The "clone Arc first" approach requires validating the index, cloning the Arc, then verifying the index still refers to the same Arc before removal — but `Arc::ptr_eq` under a second lock is still a separate lock acquisition and the index could shift between the read-lock clone and the write-lock check.

The alternative the TODO lists — "remove, attempt wrap-out, re-insert on failure" — does not have a TOCTOU problem (the removal is atomic under the write lock), but requires a second write-lock acquisition for re-insert and must preserve the original index precisely.

**The "clone + wrap-before-remove" strategy as described is not TOCTOU-safe without holding the write lock across both clone and removal** (which would violate §2.3 lock discipline by calling `to_pyobject` under the write lock).

The `notes-deep-error-handling.md` fix proposal (`docs/adr/2026/06/11-cst-named-mutators/notes-deep-error-handling.md:29`) notes the re-insert alternative "requires a re-insert under a second write lock" but does not analyze TOCTOU for the clone-first approach.

---

## 5. Do `replace_at` and `insert` have the same hazard?

**`replace_at`: No.**

`replace_at` (`src/cst_fegen.rs:790-850`) validates child and label before the lock (l.797-812), then under a single write lock: resolve index, bounds-check, `std::mem::replace` (l.844). After guard release: `drop(old)` (l.848). `replace_at` returns `()` — there is no `to_pyobject` call on the removed (old) entry after removal. The old entry is just dropped. No Python wrap-out failure can occur on the removed value.

**`insert`: No.**

`insert` (`src/cst_fegen.rs:684-738`) only adds to the Vec; it does not remove anything, so there is no "removal then failed wrap-out" scenario.

**`clear`: No.**

`clear` (`src/cst_fegen.rs:852-860`) does `std::mem::take` under the write lock, then `drop(old)` outside. No wrap-out.

**The hazard is unique to `remove_at`** because it is the only mutator that (a) removes from the Vec and (b) must wrap the removed value into a Python object to return it.

---

## 6. Is this fixing a symptom of a deeper problem?

The deep problem is a structural tension: §2.3 lock discipline forbids Python work under the Rust lock (correct — prevents deadlock), but the only way to guarantee atomicity for `remove_at` is to either (a) do the Python wrap-out before removal (requiring a different lock strategy), or (b) undo the removal on failure (re-insert under a second lock). Both strategies conflict with either the lock discipline or simplicity.

The deeper design question is whether `remove_at` should even need to guarantee atomicity under `MemoryError`. As `dispositions-deep.md:37` notes: "Extremely rare (OOM in Arc/PyO3 allocation); fixing requires clone-before-remove or re-insert-on-failure, adding non-trivial complexity for a near-impossible path." The judge verdict (`judge-verdict-deep.md:11-15`) accepted the TODO deferral because the fix strategy is a design call.

No other generated Rust mutator has this tension; the hazard is structurally specific to `remove_at`'s return-the-removed-value semantics.

---

## 7. Current code state at HEAD (5d94733)

The TODO is present and unresolved. The actual generated code matches the template exactly:

- `fltk/fegen/gsm2tree_rs.py:1313-1363` — emitter template, `TODO(mutator-remove-at-oob-atomicity)` at l.1318-1319.
- `src/cst_fegen.rs:742-787` — generated Grammar node `remove_at`; identical `Rule` node at l.1690-1735.
- `TODO.md:32-34` — entry present.
- No atomicity docstring on any `remove_at` method in any generated file.
