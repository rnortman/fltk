# Quality review: cst-named-mutators
<!-- Style: concise, precise, complete, unambiguous. No padding, no preamble. -->

Commit reviewed: f904540

## quality-1

**File:line:** `fltk/fegen/gsm2tree_rs.py:1267-1268` (generated into every `insert` pymethod, e.g. `crates/fltk-cst-spike/src/cst.rs:617-618`)

**Issue:** Python work (`raw_idx.lt(0i64)?`) is called while the `self.inner` write lock is held. The write guard is acquired at line 1253 for reading `n`, the `lt` call happens inside that scope on line 1268, and only then is the guard dropped (line 1271). This violates the stated lock discipline (§2.3: "all Python work happens strictly outside the guard").

In CPython the GIL prevents concurrent Python re-entry into this node from another thread, so this does not deadlock in the actual threat model. But:
- The `// Beyond i64 range: use Python __lt__` branch is the one path where a Python call sneaks inside a write lock, exactly where the design says it must not. If the lock ever moves to `parking_lot::RwLock` or is otherwise made re-entrant-safe in a different way, this becomes a live risk.
- It contradicts the documented invariant that readers will use to reason about future changes.

**Consequence:** The documented lock discipline is violated, so future maintainers cannot rely on it when making changes. The inconsistency will propagate: new methods added to the generator will use the existing code as a template and may copy the pattern.

**Fix:** Move the index normalization (including the `__index__` call and the `lt` comparison) entirely outside the lock scope. Read `n` from a read guard, drop it, do the arithmetic, then acquire the write lock to insert. Concretely in `_generic_insert`: call `index.call_method0("__index__")` before acquiring any lock; compute `clamped` (including the `raw_idx.lt(0i64)?` branch) without any lock held; then acquire the write lock only for the `Vec::insert`. The only reason the write lock was grabbed early was to read `n`; read it under a read lock first, then clamp with no lock, then write-lock for the mutation.

---

## quality-2

**File:line:** `fltk/fegen/gsm2tree.py:515-516` (Python `insert`); `fltk/fegen/gsm2tree_rs.py:1245-1247` (Rust `insert`); same asymmetry in `replace_at` at `gsm2tree.py:559-560` vs `gsm2tree_rs.py:1353-1355`.

**Issue:** Validation order diverges between backends.

- Rust `insert`/`replace_at`: child extracted first (line 1245/1353), label extracted second (line 1247/1355).
- Python `insert`/`replace_at`: label checked first (line 515/559), child checked second (line 516/560).

When a caller passes BOTH an invalid label and an invalid child, the backends surface different errors (Rust raises child `TypeError`; Python raises label `TypeError`). Design §3 claims "the Python implementation checks in the same order so the surfaced error matches" — this claim is false.

**Consequence:** A caller that triggers both errors simultaneously sees different exceptions depending on backend, breaking the cross-backend behavioral contract. This is undetectable from the parity tests because `TestErrorBehavior` never passes both a bad label and a bad child to the same call.

**Fix:** Align the Python order to match Rust (child first, label second) in `_emit_py_mutators`'s `insert_fn` and `replace_fn` bodies. Then add a parity test with both a bad child and a bad label to lock in the order.

---

## quality-3

**File:line:** `fltk/fegen/gsm2tree.py:442` and the three analogous branches (lines ~452, ~464); generated into every `_check_child_type_for_mutators` on the Python backend, e.g. `fltk/fegen/fltk_cst.py:107-109`.

**Issue:** The child-type `TypeError` message format differs between backends:
- Python: `"{ClassName}.{method}: unsupported child type {type}"` (includes method name).
- Rust (`extract_from_pyobject`): `"{ClassName}: unsupported child type {type}"` (no method name).

Design §2.2 specifies Rust's existing `extract_from_pyobject` text (`"{ClassName}: unsupported child type {type}"`) as the canonical format. Python deviates by inserting `.{method}`. The parity tests in `TestErrorBehavior` check `with pytest.raises(TypeError)` only — they do not check message text. `TestMessageParity` covers label errors and index errors but has no entry for child-type errors.

**Consequence:** Any caller that catches child-type `TypeError` and inspects the message (e.g. in a test harness, error handler, or debugger message) will see different strings per backend. The gap in `TestMessageParity` means the divergence is invisible to the test suite.

**Fix:** One of:
1. Change the Python generator to emit the shorter format without the method name (conform to the Rust text), or
2. Change `extract_from_pyobject` in the generator to include the method name (but this requires threading `method_name` into `_generic_child_enum_block` and `extract_from_pyobject`).

Option 1 is lower-cost: in `_emit_py_mutators`, change `f"{class_name}.{{method}}: unsupported child type ..."` to `f"{class_name}: unsupported child type ..."`. Then add a `TestMessageParity.test_bad_child_type_insert_message_parity` that asserts `py_msg == emb_msg`.

---

## quality-4

**File:line:** `fltk/fegen/gsm2tree.py:518-521` (Python `insert` body emitted per node); `fltk/fegen/fltk_cst.py:121-126`, etc.

**Issue:** The Python `insert` performs explicit index clamping and then delegates to `self.children.insert(idx, ...)`, which performs CPython's own clamping a second time. The explicit clamping is redundant: `list.insert` already handles negative-index normalization and out-of-range clamping for all Python `int` magnitudes (including beyond-i64 values, since Python's native int is arbitrary precision).

The generator comment acknowledges this design intent ("CPython gives clamping for free" — design §2.4), but the emitted code does not leverage it: it clamps explicitly anyway. The explicit clamping also deviates from the design intent of using CPython's native `list.insert` semantics.

**Consequence:** Each insertion calls `len()` plus arithmetic that CPython's `list.insert` will immediately redo. Minor cost, but the real problem is that the clamping logic is now maintained in two places (explicit code + CPython's list), and any future divergence between the explicit logic and CPython's actual semantics would be silent.

**Fix:** Remove the explicit clamping block from the generated Python `insert` body. Call `operator.index(index)` to enforce `__index__` semantics, then pass the result directly to `self.children.insert(idx, ...)` and let CPython handle normalization. This matches the design §2.4 intent and eliminates the redundant computation.
