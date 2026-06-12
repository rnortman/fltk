# Dispositions — deep review, round 1

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: f904540. Fixes applied at: c51eab1. Rework (round 2) applied at: HEAD.

---

## errhandling-1

- Disposition: Fixed
- Action: Removed `.{method}` from Python `_check_child_type_for_mutators` error message to match Rust's `"{ClassName}: unsupported child type {type}"`. Also removed unused `method` parameter from that helper's signature. Added `TestMessageParity.test_bad_child_type_insert_message_parity` asserting `py_msg == emb_msg`. `gsm2tree.py:442-468`, `tests/test_cst_mutators_parity.py` (new test).
- Severity assessment: Callers matching or logging child-type TypeError messages for cross-backend diagnostics would see different strings, silently undermining the parity contract.

---

## errhandling-2

- Disposition: Fixed
- Action: Replaced `index.call_method0(intern!(py, "__index__"))` with `py.import("operator")?.getattr("index")?.call1((index,))` in all three indexed Rust methods. This follows Python's `operator.index` contract: raises `TypeError` (not `AttributeError`) for non-indexable inputs. Tightened parity tests from `pytest.raises((TypeError, AttributeError))` to `pytest.raises(TypeError)`. `gsm2tree_rs.py:_generic_insert/remove_at/replace_at`, `tests/test_cst_mutators_parity.py`.
- Severity assessment: Code catching `TypeError` for bad-index inputs on the Python backend silently misses `AttributeError` on Rust — a backend-specific divergence that violates the "type pinned" contract.

---

## errhandling-3

- Disposition: Fixed
- Action: Reordered Python emitter's `insert` and `replace_at` to child → label → index, matching Rust's extraction order. Added `test_bad_child_wins_over_bad_label_insert` and `test_bad_child_wins_over_bad_label_replace_at` parity tests (both backends, asserting `"unsupported child type"` message wins). `gsm2tree.py:511-525,549-570`, `tests/test_cst_mutators_parity.py`.
- Severity assessment: Multi-bad-argument calls surface different exception types and messages per backend, breaking the cross-backend behavioral contract.

---

## errhandling-4

- Disposition: TODO(mutator-remove-at-oob-atomicity)
- Action: `TODO(mutator-remove-at-oob-atomicity)` comment added at `gsm2tree_rs.py:_generic_remove_at`, documenting that `to_pyobject` failures after removal leave the tree mutated. `TODO.md` entry added.
- Severity assessment: On OOM during `to_pyobject`, `remove_at` returns an error but the child is permanently lost from the tree. Extremely rare (OOM in Arc/PyO3 allocation); fixing requires clone-before-remove or re-insert-on-failure, adding non-trivial complexity for a near-impossible path. Deferred.

---

## correctness-1

- Disposition: Fixed
- Action: Refactored `_generic_insert` to compute `is_negative_big`/`raw_i64` outside the lock, then acquire a single write lock for `len` + clamp + `Vec::insert`. `gsm2tree_rs.py:_generic_insert`.
- Severity assessment: Without the fix, a concurrent shrink between the two write-lock acquisitions could make `Vec::insert` panic → `PanicException` with no diagnostic; under concurrent grow, the child lands at a stale position (silent data corruption). Single-threaded use is unaffected.

---

## correctness-2

- Disposition: Fixed
- Action: Refactored `_generic_remove_at` and `_generic_replace_at` to use a single write lock for resolve + bounds-check + mutation. Used a `Result<_, usize>` inner result to carry `n` out for error formatting after guard release. `gsm2tree_rs.py:_generic_remove_at/replace_at`.
- Severity assessment: Concurrent shrink between read-guard release and write-guard acquisition causes `Vec::remove`/slice-index panic or wrong-element mutation with no error — silent data corruption.

---

## correctness-3

- Disposition: Fixed (same fix as errhandling-2)
- Action: See errhandling-2. Additionally: the non-`int` `__index__` return case (where `call_method0` returned a non-int value, causing insert to silently clamp instead of raising `TypeError`) is also fixed by routing through `operator.index`.
- Severity assessment: Non-int `__index__` return could cause silent wrong-index insert/IndexError-where-TypeError-expected. These are maliciously-crafted or highly-unusual inputs; in practice, the effect is surprising behavior rather than security risk.

---

## correctness-4

- Disposition: Fixed
- Action: Changed `raw_idx.str()` to `index.str()` (captured before `operator.index` call) in Rust `remove_at` and `replace_at` error message formatting. `gsm2tree_rs.py:_generic_remove_at,_generic_replace_at`.
- Severity assessment: For `True`, `bool` subclasses, or numpy scalars with custom `__repr__`, the pinned cross-backend error message text diverges (e.g. "index 1 out of range" vs "index True out of range").

---

## correctness-5

- Disposition: Fixed (same fix as errhandling-3)
- Action: See errhandling-3.
- Severity assessment: Same as errhandling-3.

---

## correctness-6

- Disposition: Fixed
- Action: Changed Python `_check_label_type_for_mutators` to use `_cn = "{class_name}"` (static, generator-controlled string) instead of `type(self).__name__` (dynamic). `gsm2tree.py:472-488`. Message now matches Rust's static `class_name`-based text.
- Severity assessment: For downstream subclasses (public API per CLAUDE.md), the Python message names a nonexistent `{Subclass}_Label` and diverges from Rust's pinned text — breaking cross-backend diagnostic parity.

---

## correctness-7

- Disposition: Fixed (subsumed by correctness-1/2/3 fixes)
- Action: All Python work (including `raw_idx.lt(0i64)?` and `raw_idx.extract::<i64>()` under read lock) now happens outside any guard. The `operator.index` call and `orig_str` capture are both done before any lock acquisition. `gsm2tree_rs.py:_generic_insert/remove_at/replace_at`.
- Severity assessment: Python re-entry into the same node while a non-reentrant `RwLock` is held deadlocks the thread. Reachable via an evil `__index__` result or GC-triggered `__del__` touching `node.children` on the same thread.

---

## test-1

- Disposition: Fixed
- Action: Added `TestMessageParity.test_bad_child_type_insert_message_parity` asserting `py_msg == emb_msg` for `TypeError` raised by `insert(0, "not_a_span")` on both backends. `tests/test_cst_mutators_parity.py`.
- Severity assessment: Child-type message drift between backends is invisible to the test suite; any downstream diagnostic code matching the message would behave differently per backend.

---

## test-2

- Disposition: Fixed
- Action: Added `TestLabelFreeNodeErrors` class with two tests: `test_insert_non_none_label_on_label_free_node_raises_type_error` and `test_replace_at_non_none_label_on_label_free_node_raises_type_error`. Uses a dynamically-compiled label-free `Foo` class from `make_zero_label_grammar`. `tests/test_cst_mutators_parity.py`.
- Severity assessment: The "no labels defined" TypeError path in both Python backends is entirely untested; a bug in the message format or condition would be invisible.

---

## test-3

- Disposition: Fixed (same fix as errhandling-2)
- Action: Tightened `test_non_index_*` from `pytest.raises((TypeError, AttributeError))` to `pytest.raises(TypeError)`. See errhandling-2. `tests/test_cst_mutators_parity.py`.
- Severity assessment: Exception type for non-indexable index is not actually pinned despite the design's "type pinned" claim; a future regression to `ValueError` or other exception would not be caught.

---

## test-4

- Disposition: Fixed
- Action: Added `TestMixedOpsNodeChildren` with four tests exercising `insert`/`remove_at`/`replace_at`/`clear` on `Alternatives` nodes (node-typed `Items` children). `tests/test_cst_mutators_parity.py`.
- Severity assessment: A mutation-after-mutation regression with node-typed children would not be caught by the existing mixed-ops test (which uses only span-typed children).

---

## test-5

- Disposition: Fixed
- Action: Added `TestClearRegistryEviction.test_remove_at_then_drop_evicts_registry_entry` mirroring the `clear` eviction test. `tests/test_cst_mutators_identity.py`.
- Severity assessment: `remove_at`'s "no retained strong handle" guarantee is unpinned; an accidental strong-Arc retain in a local variable would not be caught.

---

## test-6

- Disposition: Fixed
- Action: Added `TestReplaceAt.test_replace_at_large_negative_out_of_range` with `big = -(10**25)`. `tests/test_cst_mutators_parity.py`.
- Severity assessment: Negative-overflow code path for `replace_at` is untested; a backend treating `-(10**25)` as index 0 instead of raising `IndexError` would go undetected.

---

## reuse-1

- Disposition: Fixed
- Action: Extracted `_emit_resolve_index_stmts()` static method on `RustCstGenerator` (`gsm2tree_rs.py`). Both `_generic_remove_at` and `_generic_replace_at` now call it via `*self._emit_resolve_index_stmts()` instead of copy-pasting the `match maybe_i64 { Some(i) if i < 0 => ... }` block. TODO entry and TODO comment removed. All generated artifacts regenerated; `make check` clean.
- Severity assessment: Same as before: future normalization changes now only require one edit.

---

## reuse-2

- Disposition: Fixed
- Action: Extracted `_emit_bounds_check_stmts(method_name)` inner function inside `_emit_py_mutators` (`gsm2tree.py`). Both `remove_fn` and `replace_fn` bodies now call it for the `operator.index` + `len` + normalise + `IndexError` block, followed by their diverging final statement. TODO entry and TODO comment removed. All generated artifacts regenerated; `make check` clean.
- Severity assessment: Same as before: future message or normalization changes now only require one edit.

---

## quality-1

- Disposition: Fixed (subsumed by correctness-1/7 fixes)
- Action: `raw_idx.lt(0i64)?` (Python work under write lock) is eliminated: the `is_negative_big` determination now happens outside any lock. See correctness-1/7.
- Severity assessment: Lock discipline violation; future maintainers using existing code as template propagate the anti-pattern.

---

## quality-2

- Disposition: Fixed (same fix as errhandling-3/correctness-5)
- Action: See errhandling-3.
- Severity assessment: Same.

---

## quality-3

- Disposition: Fixed (same fix as errhandling-1)
- Action: See errhandling-1.
- Severity assessment: Same.

---

## quality-4

- Disposition: Won't-Do (comment corrected)
- Action: Deleted the false comment at `gsm2tree.py` (was at line ~508-511) that read "CPython's list.insert handles all index clamping natively (negative, out-of-range, beyond-i64), so no explicit clamping is needed after operator.index normalization". Replaced with a correct comment explaining that CPython's list.insert raises `OverflowError` for beyond-`ssize_t` ints, so explicit clamping is required. Won't-Do itself stands: the clamp is load-bearing for large ints; removing it is a bug.
- Severity assessment: False comment directly above the load-bearing clamp invited a future maintainer to delete it; corrected comment prevents that misread.

---

## efficiency-1

- Disposition: Fixed (subsumed by correctness-1 fix)
- Action: `insert` now acquires one write lock (not two). See correctness-1.
- Severity assessment: Doubled lock acquire/release on every `insert` call; free fix as part of the correctness fix.

---

## efficiency-2

- Disposition: Fixed (subsumed by correctness-2 fix)
- Action: `remove_at`/`replace_at` now acquire one write lock (not two). See correctness-2.
- Severity assessment: Doubled lock round-trips on every call; free fix as part of the correctness fix.

---

## efficiency-3

- Disposition: TODO(mutator-rs-fast-path-int-index)
- Action: `TODO(mutator-rs-fast-path-int-index)` comment added at `gsm2tree_rs.py:_generic_insert`. The `operator.index` call is currently unconditional; for the common exact-`int` case, `extract::<i64>()` directly on the original `index` object would skip the Python import+getattr+call overhead. Deferred because the operator.index fix was the primary correctness goal and this optimization requires careful thought about `orig_str` capture ordering. `TODO.md` entry added.
- Severity assessment: Fixed per-call Python-dispatch overhead on hot rewrite paths; practically bounded by Python interpreter overhead anyway.

---

## efficiency-4

- Disposition: Fixed
- Action: `_emit_py_mutators` now emits `_MUTATOR_ALLOWED_CHILD_TYPES = None` as a plain class-body assignment (not an annotated field; dataclasses ignores it). `_check_child_type_for_mutators` lazily initialises it to the static-type tuple on first call, then memoises; native Span is appended once when `fltk._native` is first seen and cached (it never unloads). After the first call, `_check_child_type_for_mutators` reads one class attribute and calls `_get_native_span_type()` only when the cached tuple does not yet include native Span. TODO entry removed. Generated artifacts regenerated; `make check` clean.
- Severity assessment: Per-mutation tuple construction + sys.modules probe eliminated after first call; strictly better on the hot rewrite path.
