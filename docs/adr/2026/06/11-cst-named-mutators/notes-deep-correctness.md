# Deep correctness review — cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Reviewed: `dd52073..f904540`. Design: `design.md`, this dir. Generator sources reviewed in depth (`fltk/fegen/gsm2tree.py`, `fltk/fegen/gsm2tree_rs.py`); generated artifacts spot-checked against emitters (`src/cst_fegen.rs`, `fltk/fegen/fltk_cst.py`) and match. Tests read (`tests/test_cst_mutators_parity.py`, `tests/test_cst_mutators_identity.py`).

All Rust findings cite the emitter (`gsm2tree_rs.py`); each is replicated into every regenerated `cst.rs` (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture`, `tests/rust_cst_fegen`, `tests/rust_parser_fixture` ×2, `crates/fltk-cst-spike`).

## correctness-1: TOCTOU race in Rust `insert` — clamp and mutation under separate locks

- `fltk/fegen/gsm2tree_rs.py:1252-1278` (`_generic_insert`; e.g. generated `src/cst_fegen.rs` `Grammar::insert`).
- The clamped index is computed under one write guard, the guard is explicitly dropped (`drop(guard)`), and `Vec::insert` runs under a **second** `self.inner.write()`. Design §2.3 pins clamp + `Vec::insert` under a single lock acquisition ("Under the lock: `n = guard.children.len()`, clamp …, `Vec::insert`").
- Why: between the two acquisitions another thread can shrink `children` (e.g. `clear`, `remove_at`), making `clamped > len`.
- Consequence: `Vec::insert` panics → caller gets `pyo3_runtime.PanicException` instead of the pinned clamping semantics ("never raises for valid args"), and the panic poisons the lock mid-operation (poison is swallowed by `Shared`, but the insert is lost). Under a concurrent *grow* at the head, the precomputed clamp also lands the child at a stale position. Violates the §2.1 invariant for any concurrent writer; single-threaded use is unaffected.
- Fix: hold one write guard across len-read, clamp, and insert. The only Python work in that window is `raw_idx.lt(0)` / `extract` — hoist those above the lock (see correctness-3/7), leaving the guarded region pure Rust.

## correctness-2: TOCTOU race in Rust `remove_at` / `replace_at` — bounds check under read lock, mutation under later write lock

- `fltk/fegen/gsm2tree_rs.py:1290-1325` (`_generic_remove_at`), `1358-1392` (`_generic_replace_at`).
- `resolved`/`n` are computed under `self.inner.read()`; the guard drops; mutation (`guard.children.remove(idx)` / `mem::replace(&mut guard.children[idx], …)`) happens under a separately acquired write guard. Design §2.3 pins resolve + bounds-check + mutate "Under the write lock".
- Why: between read-guard release and write-guard acquisition another thread can mutate `children`.
- Consequence: (a) concurrent shrink → `Vec::remove` / slice index panics → `PanicException` instead of the pinned `IndexError`; (b) concurrent insert/remove at a lower index → the **wrong element** is silently removed/replaced — data corruption with no error. Single write-lock acquisition (resolve inside it; format the `IndexError` after dropping the guard, `n` already captured) eliminates both; the existing code already defers error formatting, so the fix is purely moving resolution into the write-guard scope.

## correctness-3: Rust index normalization is not `__index__`-semantics-equivalent (`call_method0("__index__")` vs `PyNumber_Index`)

- `fltk/fegen/gsm2tree_rs.py:1251,1288,1357`.
- Design §2.2/§2.3 pin "PyNumber_Index-equivalent normalization" with exception **type pinned as `TypeError`**. `index.call_method0(intern!(py, "__index__"))` differs from `PyNumber_Index` in two ways:
  1. **Missing `__index__`** → `AttributeError`, not `TypeError`. Python backend (`operator.index`, `gsm2tree.py:514,537,558`) raises `TypeError`. Cross-backend exception-type divergence on the same input (`node.remove_at("x")`). The parity tests were loosened to `pytest.raises((TypeError, AttributeError))` with the comment "(or AttributeError on Rust)" (`tests/test_cst_mutators_parity.py`, `TestErrorBehavior.test_non_index_*`) — the test codifies the divergence instead of catching it. The design's pinned contract ("type pinned") is violated.
  2. **Non-`int` `__index__` return is accepted.** `PyNumber_Index`/`operator.index` raise `TypeError` when `__index__` returns a non-int; `call_method0` returns whatever the method returns. Downstream, `raw_idx.extract::<i64>()` fails and the code treats the value as "beyond i64": `insert` **silently clamps and inserts** (e.g. an object whose `__index__` returns `2.5` → child appended at `len`); `remove_at`/`replace_at` raise `IndexError` ("index 2.5 out of range") where Python raises `TypeError`. Wrong behavior class, not just wrong message.
- Fix: normalize via `pyo3::ffi::PyNumber_Index` (stable ABI) or `py.import("operator")?.getattr("index")?.call1((index,))` before any lock; both give CPython semantics exactly and fix the AttributeError and non-int cases at once. Then tighten the parity tests back to `TypeError` only.

## correctness-4: Rust `IndexError` message formats the normalized value, not the caller's original

- `fltk/fegen/gsm2tree_rs.py:1315,1382` (`raw_idx.str()` — `raw_idx` is the `__index__()` result), vs Python backend `gsm2tree.py:541,564` (formats the original `index` parameter object).
- Design §2.2: "`{index}` is the caller's original (possibly negative) value", with exact cross-backend text parity.
- Consequence: for any index whose `str` differs from its `__index__` result — `True` (`"True"` vs `"1"`), enum-int subclasses, numpy scalars with custom repr — the pinned-identical message diverges between backends (e.g. `Identifier.remove_at: index True out of range (1 children)` vs `… index 1 …`). Untested: the parity matrix only uses plain ints.
- Fix: format `index.str()` (the original `Bound<PyAny>`), not `raw_idx.str()`. (Note: §3's beyond-`i64` case still works — `str()` of the original big int equals `str()` of its `__index__` result for real ints.)

## correctness-5: Cross-backend argument-validation order diverges, contradicting design §3

- Python (`gsm2tree.py:512-516,556-560`; generated e.g. `fltk_cst.py` `Items.insert`): `operator.index(index)` → label check → child check.
- Rust (`gsm2tree_rs.py:1238-1251,1344-1357`): child extraction → label extraction → index normalization.
- Design §3 pins: "the child/label TypeError wins on Rust (extraction first); the Python implementation checks in the same order so the surfaced error matches." The Python implementation checks in the **reverse** order on both axes.
- Consequence (multi-bad-argument calls; all pinned-message `TypeError`s, so exact-text parity is broken, not just ordering trivia):
  - bad child + bad label: Python raises the label message, Rust the child message;
  - non-indexable index + bad child/label: Python raises the index `TypeError`, Rust the child/label message.
- Fix: reorder the Python emitter to child → label… no — reorder to match Rust: validate child, then label, then `operator.index` (or reorder Rust; either way make them identical and pin one combined-bad-args parity test).

## correctness-6: Python label-error message uses dynamic `type(self).__name__`; child-error and Rust use the static class name

- `gsm2tree.py:464-476` (`_check_label_type_for_mutators` emits `_cn = type(self).__name__` → `f"{_cn}.{method}: label argument is not a {_cn}_Label…"`); the sibling child check (`gsm2tree.py:~430-460`) and Rust's `_label_from_pyobject_match` (`gsm2tree_rs.py:1078-1106`) hard-code the generated class name.
- Consequence: for an instance of a downstream subclass (generated dataclasses are subclassable public API per CLAUDE.md), the message names a nonexistent `{Subclass}_Label` enum and diverges from the Rust backend's pinned text. Internally inconsistent within the Python backend too (label error dynamic, child error static).
- Fix: use the static class name literal, matching the child check and Rust.

## correctness-7: Python-level calls executed while holding the node lock (§2.3 lock-discipline violation; same-thread deadlock path)

- `gsm2tree_rs.py:1268` — `raw_idx.lt(0i64)?` (PyObject_RichCompare) runs while the `insert` **write** guard is held.
- `gsm2tree_rs.py:1294,1362` — `raw_idx.extract::<i64>()` runs under the `remove_at`/`replace_at` **read** guard; for a non-int `raw_idx` (possible per correctness-3.2), pyo3 i64 extraction goes through `PyLong_AsLongLong`, which calls `__index__` — arbitrary Python under the lock.
- Design §2.3 pins: "all Python work (extraction, registry calls, wrap-out) happens strictly outside the guard."
- Consequence: any Python re-entry into the same node while the guard is held deadlocks (`std::sync::RwLock`, `Shared`, `crates/fltk-cst-core/src/shared.rs` — non-reentrant). Reachable via an evil `__index__` result whose `__lt__`/`__index__` touches the node, and — for the `lt` call even with genuine big ints — via allocation-triggered GC running a `__del__` that reads `node.children` on the same thread. Exotic inputs, but it is the exact invariant the design calls "the hard invariant".
- Fix: subsumed by correctness-1/2/3 — normalize via `PyNumber_Index` and complete all extraction/sign work before acquiring any guard; guarded regions become pure Rust.

## Notes (no finding)

- Rust clamp arithmetic (`n as i64 + i`) cannot overflow for `i ≥ i64::MIN`, `n ≥ 0` — checked, sound.
- Python backend clamp/bounds/pop/replace logic verified correct, including negative and empty-node cases.
- Lazy native-Span acceptance (`_get_native_span_type` via `sys.modules.get`) is complete: no native Span instance can exist if `fltk._native` is unloaded.
- `_registry_snapshot` feature gating (`test-introspection` → `fltk-cst-core/test-introspection`) is wired consistently across all six Cargo.tomls; `registry::snapshot` is gated identically in core (`registry.rs:139-140`).
- Identity tests' use of `phase4_roundtrip_cst` (test-introspection on by default for that fixture) is consistent with the gating; `pytest.importorskip` handles absence.
- `drop(old)`-outside-guard discipline in `replace_at`/`clear` matches §2.3.
