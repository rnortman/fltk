# Efficiency review — cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: dd52073..f904540 (HEAD f904540). Source of truth: `fltk/fegen/gsm2tree.py`, `fltk/fegen/gsm2tree_rs.py`; spot-checked generated artifacts (`src/cst_fegen.rs`, `fltk/fegen/fltk_cst.py`). Findings are in the generators; every generated module inherits them.

## efficiency-1: Rust `insert` acquires the write lock twice per call; Python comparison runs under the lock

`gsm2tree_rs.py` `_generic_insert` (generated form: `src/cst_fegen.rs:684-734`). The emitted pymethod takes `self.inner.write()` once to read `children.len()` and compute the clamp, drops it, then takes `self.inner.write()` again to do the `Vec::insert`. Two write-lock acquisitions where one suffices; the first is a write lock used only for reading. Worse, the beyond-`i64` fallback executes `raw_idx.lt(0i64)?` — an arbitrary Python `__lt__` call — *inside* the first guard, contradicting the §2.3 lock discipline the code comments cite ("validate BEFORE taking the write lock") and the design text ("Under the lock: ... clamp ... `Vec::insert`" — one lock, pure arithmetic).

**Consequence**: doubled lock acquire/release on every `insert` call on every generated node class — per-mutation cost in tree-rewrite loops, contention multiplier under threaded use. The Python-call-under-lock also reopens the recursive-lock-entry hazard the discipline exists to prevent, and the drop/re-acquire gap is a TOCTOU window (clamp computed against a stale `len`; a concurrent shrink makes `Vec::insert` panic → `PanicException`) — flagging the race for correctness-reviewer, but the efficiency fix removes it for free.

**Fix**: extract `i64`-or-sign from `raw_idx` before any lock (the `lt` call included); then a single `self.inner.write()` scope: read `len`, clamp with pure integer arithmetic, `Vec::insert`.

## efficiency-2: Rust `remove_at`/`replace_at` take two locks per call (read then write)

`gsm2tree_rs.py` `_generic_remove_at` / `_generic_replace_at`. Both resolve the index under `self.inner.read()`, drop the guard, then take `self.inner.write()` to mutate. The design (§2.3) specifies one write lock: "Under the write lock: resolve negative index against `len`, bounds-check, `Vec::remove`". The only operation that must happen outside the guard is the error-path `raw_idx.str()` formatting, and that already works with a single lock: resolve + mutate under one write guard; on out-of-range, drop the guard and format.

**Consequence**: two lock round-trips per call on the two most common rewrite primitives, on every generated class; plus the read→write gap is a TOCTOU window (index validated against a `len` that can change before the write lock lands — `Vec::remove`/index panic → `PanicException`; correctness-reviewer's lane, same free fix).

**Fix**: extract `i64` before the lock; single `write()` scope doing resolve + bounds-check + `Vec::remove`/`mem::replace`; error formatting after guard drop.

## efficiency-3: explicit `__index__` Python method call on every mutator invocation, even for exact ints

`gsm2tree_rs.py`, all three indexed pymethods: `index.call_method0(pyo3::intern!(py, "__index__"))` runs unconditionally. For the overwhelmingly common case — caller passes an exact `int` — this is a full Python attribute lookup + bound-method call + temporary object per operation, when `index.extract::<i64>()` on the original object succeeds directly via C-level conversion.

**Consequence**: fixed per-call Python-dispatch overhead on `insert`/`remove_at`/`replace_at` across all generated classes; pure waste in the hot rewrite path.

**Fix**: fast path `if let Ok(i) = index.extract::<i64>() { ... }` on the original `index` first; fall back to the explicit `__index__` call only when that fails (non-int or beyond-`i64`). Semantics unchanged.

## efficiency-4: Python backend rebuilds allowed-type tuples / union objects on every validation call

`gsm2tree.py` `_emit_py_mutators`, emitted `_check_child_type_for_mutators`:
- Span-typed classes (e.g. `fltk/fegen/fltk_cst.py:470-477`): every call builds `_allowed = (A, B, ...)`, calls `_get_native_span_type()` (a `sys.modules` dict lookup + `m.Span` attribute lookup), and conditionally rebuilds `_allowed = (*_allowed, _ns)`. Two tuple allocations + module/attr lookups per `insert`/`replace_at`.
- Multi-type non-span classes (e.g. `fltk_cst.py:107`): `isinstance(child, Trivia | Rule)` evaluates `type.__or__` at call time, constructing a fresh `types.UnionType` per call. (The single-type variant is fine.)

**Consequence**: per-mutation allocations and lookups on the pure-Python backend — the backend already paying interpreter overhead — multiplied across every insert/replace in a rewrite pass.

**Fix**: hoist the static tuple to a class-level constant (`_MUTATOR_ALLOWED_CHILD_TYPES = (A, B)`); for the union variant use a class-level tuple instead of per-call `|`. For the native span, memoize positively: once `fltk._native` is found it never unloads, so cache the resolved type (e.g. module-level `_native_span_cache`) and only re-probe `sys.modules` while it is still `None`. Laziness/pure-Python importability (§2.2) is preserved.

No other findings: `get_span_type` is `GILOnceCell`-cached (pre-existing); `clear`/`replace_at` drop-outside-lock pattern is correct and bounded; native mutators are zero-overhead delegations; `_registry_snapshot` is feature-gated test-only.
