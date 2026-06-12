# Adversarial Validation: TODO(mutator-rs-fast-path-int-index)

Concise. Precise. No fluff. Facts anchored to file:line.

---

## 1. Does the generated code actually call `operator.index` unconditionally?

**The TODO claim is partially wrong.** The code in the _generator_ (`gsm2tree_rs.py`) does emit `operator.index` unconditionally, but the _generated output_ already applies a post-`operator.index` `extract::<i64>()` fast-path for the i64 range. The claim describes what the TODO intends to implement (skip `operator.index` entirely for exact-int inputs), but the current code's structure is:

**`_generic_insert`** (`gsm2tree_rs.py:1256–1268`):
```
let raw_idx = py
    .import(pyo3::intern!(py, "operator"))?
    .getattr(pyo3::intern!(py, "index"))?
    .call1((index,))?;
let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
    (false, Some(i))
} else {
    let neg = raw_idx.lt(0i64)?;
    (neg, None)
};
```
`operator.index` is called unconditionally. Then `extract::<i64>()` is applied to the result to avoid a second Python call for the beyond-i64 sign determination. This is **not** the fast-path the TODO describes — the TODO wants to skip `operator.index` entirely when `index` is already an exact `int`.

**`_generic_remove_at`** (`gsm2tree_rs.py:1331–1336`): same pattern — `operator.index` called unconditionally, then `extract::<i64>().ok()` on the result. Confirmed at `tests/rust_cst_fegen/src/cst.rs:749–754`.

**`_generic_replace_at`** (`gsm2tree_rs.py:1390–1394`): same pattern. Confirmed at `tests/rust_cst_fegen/src/cst.rs:817–821`.

The import is cached via `pyo3::intern!(py, "operator")` and `pyo3::intern!(py, "index")` (interned string keys), so the string-hashing cost is amortized. The actual overhead per call is: `import("operator")` (module dict lookup), `.getattr("index")` (attribute lookup), `.call1((index,))` (call frame + dispatch). Three Python operations per mutator call regardless of input type.

---

## 2. PyO3 0.23 `extract::<i64>()` and `__index__` protocol

**PyO3 version in use**: `pyo3 = 0.23.5` (`Cargo.lock`, `Cargo.toml:pyo3 = { version = "0.23" }`).

**i64 extraction on 64-bit non-Windows (the standard Linux target)**: uses `int_fits_c_long!(i64)` (`conversions/std/num.rs:331`), which calls `extract_int!(obj, -1, ffi::PyLong_AsLong)` with `force_index_call = false`.

The `extract_int!` macro (`conversions/std/num.rs:80–103`):
```rust
if cfg!(Py_3_10) && !force_index_call {
    err_if_invalid_value(obj.py(), error_val, unsafe { pylong_as(obj.as_ptr()) })
} else if let Ok(long) = obj.downcast::<crate::types::PyInt>() {
    // fast path - checking for subclass of `int` just checks a bit
    err_if_invalid_value(...)
} else {
    let num = ffi::PyNumber_Index(obj.as_ptr())...;
    err_if_invalid_value(...)
}
```

Since the project targets `abi3-py310` (`Cargo.toml:pyo3 = { features = ["abi3-py310"] }`), `cfg!(Py_3_10)` is true. The macro takes the first branch: directly calls `PyLong_AsLong(obj.as_ptr())`.

**`PyLong_AsLong` on Python 3.10+**: Per CPython docs and PyO3's own comment at `num.rs:86–88`, in Python 3.10+ `PyLong_AsLong` internally calls `PyNumber_Index` for non-int objects (fixing the float-truncation bug from 3.8–3.9). So `extract::<i64>()` **does** invoke `__index__` on objects with `__index__` but without `__int__`, on Python 3.10+.

**The TODO claim "PyO3 calls `PyLong_AsLongLong` which invokes `__index__`" is factually wrong for 64-bit Linux**: on that platform `i64` maps to `c_long` (64-bit), so PyO3 uses `PyLong_AsLong`, not `PyLong_AsLongLong`. The functional behavior (invoking `__index__` on 3.10+) is the same; the function name claim is wrong.

**`bool` subclass behavior**: `bool` is a subclass of `int` (`PyLong_Check` returns true). `PyLong_AsLong(True)` returns 1. `extract::<i64>()` on `True` returns `Ok(1)`. This is confirmed by the test `test_insert_bool_index` (`test_cst_mutators_parity.py:201–212`), which passes `True` and expects index 1.

**Non-indexable objects**: `PyLong_AsLong("not_an_int")` raises `TypeError`. `extract::<i64>()` on a `str` returns `Err`. If the fast-path were applied directly to the raw `index` argument (skipping `operator.index`), non-indexable inputs would still raise `TypeError` from `PyLong_AsLong`'s internal `PyNumber_Index` call. The error message would differ: `operator.index` says `'str' object cannot be interpreted as an integer`; `PyLong_AsLong` says `int() argument must be a string, a bytes-like object or a real number, not 'str'` (CPython 3.12 wording) or similar. The tests `test_non_index_remove_at_raises_type_error`, `test_non_index_replace_at_raises_type_error`, `test_non_index_insert_raises_type_error` (`test_cst_mutators_parity.py:487–507`) check only that `TypeError` is raised, not the message text. No `TestMessageParity` test covers the non-indexable error message.

---

## 3. `orig_str` capture-ordering concern

The concern is concrete. In `_generic_remove_at` (`gsm2tree_rs.py:1327`) and `_generic_replace_at` (`gsm2tree_rs.py:1387`), `orig_str = index.str()?.to_string_lossy().into_owned()` is captured **before** the `operator.index` call. This means the error message shows the original value (e.g., `True` not `1`, `MyInt(3)` not `3`).

If the fast-path were applied directly to `index` via `extract::<i64>()`, `orig_str` must still be captured before the `extract` call — the ordering is: `orig_str = index.str()...`, then `if let Ok(i) = index.extract::<i64>()`. The `index.str()` call is a Python round-trip, so the fast-path would save the `import+getattr+call1` triple but still pay one `str()` call. For `insert`, there is no `orig_str` capture (`insert` uses Python clamping semantics and never raises `IndexError`), so `orig_str` ordering is not a concern there.

The tests that pin `orig_str` content:
- `test_remove_at_empty_message_parity`: `match=r"Identifier\.remove_at: index 0 out of range \(0 children\)"` (`test_cst_mutators_parity.py:266`)
- `test_remove_at_out_of_range_positive`: `match=r"...index 5 out of range..."` (`test_cst_mutators_parity.py:274`)
- `test_remove_at_out_of_range_negative`: `match=r"...index -2 out of range..."` (`test_cst_mutators_parity.py:282`)
- `test_remove_at_large_positive_out_of_range`: `match=rf"...index {big} out of range..."` where `big = 10**25` (`test_cst_mutators_parity.py:291`)
- `test_remove_at_large_negative_out_of_range`: `match=rf"...index {big} out of range..."` where `big = -(10**25)` (`test_cst_mutators_parity.py:300`)
- `test_replace_at_out_of_range`: `match=r"...index 5 out of range..."` (`test_cst_mutators_parity.py:381`)
- `test_replace_at_large_out_of_range`: `big=10**25` (`test_cst_mutators_parity.py:390`)
- `test_replace_at_large_negative_out_of_range`: `big=-(10**25)` (`test_cst_mutators_parity.py:399`)
- `TestMessageParity.test_remove_at_empty_message_parity`, `test_remove_at_oob_message_parity`, `test_replace_at_oob_message_parity` (`test_cst_mutators_parity.py:546–569`): exact equality between Python and Rust backend error messages.

These tests use plain integers, not `__index__` objects or `bool`. None of them test what `orig_str` looks like for `True` or a custom `__index__` object. The `test_insert_bool_index` test (`test_cst_mutators_parity.py:201`) verifies that `True` is treated as index 1 for `insert` (which uses `operator.index` on the result), but there is no equivalent test for `remove_at(True)` or `replace_at(True, ...)`.

---

## 4. Observable behavior differences under the proposed fast-path

If `extract::<i64>()` were applied directly to `index` (bypassing `operator.index`):

**`bool` inputs**: `True` extracts as `i64(1)`, `False` as `i64(0)`. Current code: `operator.index(True) = 1` (via Python's operator module). Same result, different path. No observable change.

**Custom `__index__` objects**: `class MyIdx: def __index__(self): return 3`. Current path: `operator.index(MyIdx())` calls `__index__` via Python, returns `3`. Fast-path: `extract::<i64>(MyIdx())` calls `PyLong_AsLong(MyIdx())` which calls `PyNumber_Index(MyIdx())` which calls `__index__`. Same result. No observable change on Python 3.10+.

**Non-indexable inputs (e.g., `str`)**: `operator.index("x")` raises `TypeError: 'str' object cannot be interpreted as an integer`. `PyLong_AsLong("x")` also raises `TypeError` but with a different message (CPython-version-dependent). Tests check only `pytest.raises(TypeError)` with no `match` argument (`test_cst_mutators_parity.py:492, 499, 506`), so message differences would not be caught by existing tests.

**Objects with `__int__` but no `__index__`**: `float` has `__float__` and `__int__` but no `__index__`. `operator.index(1.0)` raises `TypeError: 'float' object cannot be interpreted as an integer`. On Python 3.10+, `PyLong_AsLong(1.0)` also raises `TypeError` (the float-truncation bug was fixed). Same behavior.

**`orig_str` for non-int `__index__` objects**: If `index` is a custom `__index__` object `MyIdx()`, current code: `orig_str = "MyIdx()"`, error shows `"MyIdx()"`. Fast-path with direct extraction on `index`: same, `orig_str = "MyIdx()"`. No observable change.

---

## 5. Are mutators hot paths?

Mutators (`insert`, `remove_at`, `replace_at`) are user-facing CST-editing operations. They are not called during parsing (the parser uses the native Rust `push_child` method, `gsm2tree_rs.py:845–847`, which is GIL-free). They are called by downstream application code that builds or transforms CSTs. There is no profiling data in the repo showing these are hot. The typical CST-editing pattern is `append` (not a mutator) for build, and occasional `insert`/`remove_at` for transformations.

---

## 6. Is this a symptom of a deeper problem?

The deeper pattern is that any Python-facing index-taking method must normalize via `PyNumber_Index` semantics (to support the `__index__` protocol) and must raise `TypeError` for non-indexable inputs. The current implementation satisfies this correctly by calling `operator.index`. The fast-path described in the TODO is a micro-optimization that avoids three Python-layer operations (import lookup, attribute lookup, call dispatch) at the cost of relying on CPython 3.10+'s `PyLong_AsLong` behavior for `__index__` dispatch.

The `pyo3::intern!` macro caches the `"operator"` and `"index"` strings, reducing them to interned pointer comparisons, but the module dict lookup (`py.import`) and attribute fetch (`.getattr`) still occur per call.

---

## 7. Summary of TODO accuracy

| Claim | Accurate? | Notes |
|---|---|---|
| `operator.index` called unconditionally | Yes | All three methods |
| "via Python import+getattr+call" | Yes | Three Python ops per call |
| `extract::<i64>()` on original object would suffice | Yes, on Python 3.10+ | PyO3 0.23 `extract::<i64>()` calls `PyLong_AsLong` which invokes `PyNumber_Index` on 3.10+ |
| "PyO3 calls `PyLong_AsLongLong`" | Wrong on 64-bit Linux | Uses `PyLong_AsLong` (`c_long` = 64-bit on Linux x64), not `PyLong_AsLongLong` |
| "avoiding three Python round-trips" | Partially wrong | `orig_str = index.str()` is still one Python call; saves import+getattr+call1 but not str() |
| "`orig_str` capture ordering" concern is real | Yes | `orig_str` must be captured before `extract::<i64>()`, not after `operator.index`'s result |
| Location: `_generic_insert`, `_generic_remove_at`, `_generic_replace_at` | Correct | `gsm2tree_rs.py:1237, 1313, 1365` |

No tests pin the non-indexable TypeError message text, so changing from `operator.index` to direct `PyLong_AsLong`-based extraction would not break any existing test, but would change the error message for non-indexable inputs in a CPython-version-dependent way.
