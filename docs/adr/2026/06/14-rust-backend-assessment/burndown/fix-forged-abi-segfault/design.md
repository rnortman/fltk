# Design: fix-forged-abi-segfault

## Status

Draft.

## Requirements

This design implements the `fix-forged-abi-segfault` action as specified in
`docs/adr/2026/06/14-rust-backend-assessment/recommended-actions.md` and its plain-English
companion `recommended-actions-eli5.md` (same slug). Those documents are the spec; this design
does not restate them. The two binding obligations they impose:

1. Add a check before the dangerous cast that rejects pure-Python forged objects while still
   accepting a genuine `SourceText` from a *different* compiled copy of the library (the
   cross-cdylib case is real and must keep working).
2. Add the segfault repro as a **subprocess-isolated** regression test.

---

## 1. Root cause / context

### 1.1 The crash, reproduced

`Span._with_source_unchecked` is a public `#[classmethod]` on the native `Span` pyclass
(`crates/fltk-cst-core/src/span.rs:444-453`). It accepts `source: &Bound<'_, PyAny>` — *any*
Python object — and forwards it to `extract_source_text`
(`crates/fltk-cst-core/src/cross_cdylib.rs:63-116`).

`extract_source_text` has two paths:

- **Fast path** (`cross_cdylib.rs:65`): `obj.cast::<SourceText>()` — a *checked* downcast that
  succeeds only when `obj`'s type object IS this cdylib's registered `SourceText`. Memory-safe.
- **Slow path** (`cross_cdylib.rs:78-115`): reached when the fast cast fails (a `SourceText`
  registered by a *different* cdylib). It validates two attributes on the object's type
  (`_fltk_cst_core_abi`, `_fltk_cst_core_abi_layout`) via `check_abi_pair`
  (`cross_cdylib.rs:158-233`), then performs `obj.cast_unchecked::<SourceText>()`
  (`cross_cdylib.rs:112`) and reads `st.get().inner.clone()`.

Both gating attributes are plain Python class attributes, readable from user code. A pure-Python
class that copies both values off a genuine `SourceText` passes all of `check_abi_pair`, reaches
`cast_unchecked`, and has its `PyObject*` memory reinterpreted as
`PyStaticClassObject<SourceText>` — a type-confusion read. The subsequent
`st.get().inner.clone()` treats arbitrary bytes as an `Arc<SourceInner>` pointer.

Reproduced live during this design (subprocess, Python 3.10.20):

```python
import fltk._native as native
ST = native.SourceText
class Forge:
    _fltk_cst_core_abi = ST._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = ST._fltk_cst_core_abi_layout
native.Span._with_source_unchecked(0, 5, Forge())   # process exits with signal 11
```

Subprocess exit code `139` (= `128 + SIGSEGV(11)`), crash before any output — confirming the
assessment's "verified live 4/4" and `cross_cdylib.rs:109-111`, which already names this exact
forgery as an accepted residual under the SAFETY comment.

### 1.2 Why it is a hard blocker

The Python backend's equivalent (`fltk/fegen/pyrt/terminalsrc.py:130`, `with_source`) does a
plain `isinstance` check and raises `TypeError` for bad input — always memory-safe. Per
`CLAUDE.md`, the Rust backend is a near-drop-in replacement; a public method that segfaults the
interpreter on pure-Python input where the Python backend raises is unacceptable, and the
type-confusion primitive is a latent security concern. `recommended-actions.md` records this as
the sole correctness blocker (§5).

### 1.3 The genuine cross-cdylib path that must keep working

The slow path is **not** dead — it is the normal path for source-bearing span reads from
out-of-tree consumer crates. `span_to_pyobject` (`cross_cdylib.rs:257-297`) is the legitimate
driver:

- When this cdylib is NOT `fltk._native` (`IS_CANONICAL_CDYLIB == false`), a source-bearing span
  is converted by calling `span.source_as_py(py)` (`span.rs:241-251`), which produces a genuine
  `Py<SourceText>` registered in the *consumer* cdylib, then invoking the cached
  `fltk._native.Span._with_source_unchecked` with that object (`cross_cdylib.rs:270-285`).
- That `SourceText` fails the fast `cast` (different cdylib type object) and reaches the slow
  path legitimately. `cast_unchecked` is sound there because both cdylibs link the same
  `fltk-cst-core` rlib + same pyo3, so the CPython memory block was genuinely allocated as
  `PyStaticClassObject<SourceText>`.

Empirically confirmed: a `SourceText`/`Span` from the `phase4_roundtrip_cst` consumer fixture
reports the identical `__basicsize__` (40 for `Span`, 24 for `SourceText`) as the native types,
because basicsize is determined by the shared rlib + pyo3 build. Any fix must preserve this path.

### 1.4 Why no Python-readable attribute can be a sufficient gate

The structural problem: **anything readable from Python is replayable from Python.** Both ABI
markers are class attributes; a forger copies them. This generalizes — `__basicsize__`,
`__flags__`, `__name__`, even a `PyCapsule` *exposed on the class*, can all be re-presented by a
hand-crafted class:

- A naive `__basicsize__` check rejects the trivial `Forge` above (its basicsize is 32, not 24).
- But a forger can pad: `class Forge: __slots__ = ('x',)` produces `__basicsize__ == 24`,
  matching `SourceText` exactly (verified live). The padded forge still has a `PyObject*` in the
  slot where the Rust `Arc<SourceInner>` is expected → still UB if cast.

So a basicsize check *narrows* the window (it kills the easy forgery and every accidental
mismatch) but, like the existing ABI-layout probe, does not *close* it. The only properties that
cannot be forged from pure Python are ones that require genuine Rust code to install on the
**individual instance's allocation** — see §2.

---

## 2. Proposed approach

`_with_source_unchecked` must stay a public classmethod accepting `PyAny`: `span_to_pyobject`
calls it cross-cdylib by name (`cross_cdylib.rs:270-285`), so neither the name, the signature,
nor its public reachability can be removed without breaking the legitimate consumer path. The fix
is therefore a single mechanism: **add a layout-genuineness gate inside `extract_source_text`
before `cast_unchecked`**, strong enough that a pure-Python forge with copied class attributes
fails it, while a genuine foreign-cdylib `SourceText` passes. The forgeable attribute pair
(`check_abi_pair`) is demoted from safety gate to version-skew diagnostic.

The decisive enabling fact (caller survey: the only non-test caller of `_with_source_unchecked`
is `span_to_pyobject`) is that **the only legitimate argument ever passed is the output of
`source_as_py` — a genuine pyo3-allocated `SourceText`.** A plain-Python object is never a
legitimate argument, so the method does not need to "validate and accept arbitrary `PyAny`"; it
needs to refuse anything whose CPython allocation is not a genuine `PyStaticClassObject<SourceText>`.

### 2.A The layout-genuineness gate: `tp_basicsize` of the object's actual type

There is no pyo3 0.29 API for "is this object's memory a `PyStaticClassObject<T>` allocated by a
*different* cdylib." pyo3's own safe `cast` resolves genuineness purely via type-object identity
(`PyType_IsSubtype` against `T::type_object`), which is by construction unavailable cross-cdylib —
that is exactly why the slow path exists. The gate must therefore be built from a CPython
primitive that a forger cannot satisfy by copying a class attribute.

The gate: read the object's actual type object's `tp_basicsize` and require it to equal
`size_of::<<SourceText as PyClassImpl>::Layout>()` — the same compile-time value already exposed
as `_fltk_cst_core_abi_layout`. pyo3 sets `tp_basicsize` from the layout basicsize at type
creation (`create_type_object.rs:519-545`), so every cdylib linking the same rlib + pyo3 reports
the identical value (verified live: native and `phase4_roundtrip_cst` consumer types both report
24 for `SourceText`, 40 for `Span`).

**Access path (use `__basicsize__`, not raw `PyType_GetSlot`).** Read it via
`obj.get_type().getattr("__basicsize__")` and `extract::<usize>()` — a stable-ABI type attribute
available under `abi3-py310`, returning a Python `int`, safe, and the same shape the existing
tests already use to read `_fltk_cst_core_abi_layout` off `type(src)` (`test_rust_span.py:471-473`).
Do **not** reach for `PyType_GetSlot(ty, Py_tp_basicsize)` as a co-equal alternative: while it is
abi3-valid, it returns `*mut c_void` whose value is the `Py_ssize_t` basicsize *reinterpreted as a
pointer* (a documented CPython quirk), so it must be cast `ptr as usize` — never dereferenced or
null-checked — and the call requires `unsafe`. An implementer who treats the return as a real
pointer reads garbage, which would silently mis-size the gate (spuriously rejecting genuine foreign
`SourceText`, breaking Requirements item 1, or spuriously accepting, defeating the gate). The
`getattr("__basicsize__")` path avoids that footgun entirely and is the mandated one. Surface any
read/extract failure as a diagnostic `TypeError` (see Edge cases, exotic-type bullet).

Why this gate and not the existing attribute check: `tp_basicsize` is read off the **type object
itself**, not a copyable class attribute. A forger cannot present it by writing
`_fltk_cst_core_abi_layout = 24` on a class; the forger must make the *real* CPython type carry a
matching `tp_basicsize`, which forces real `__slots__` padding and changes the instance's actual
allocation shape. This kills the trivial copy-the-attribute forgery (the verified 4/4 crash) and
every accidental layout mismatch.

**Honest residual.** A determined forger can still pad `__slots__` to make `tp_basicsize` match
exactly (verified: `class Forge: __slots__ = ('x',)` → `tp_basicsize == 24`). The padded forge
still has a `PyObject*` in the slot where the Rust `Arc<SourceInner>` is expected, so casting it
is still UB. The basicsize gate therefore *narrows* the window to the same residual class the
existing `_fltk_cst_core_abi_layout` probe already documents (`span.rs:117-126`,
`cross_cdylib.rs:104-111`): an object with the right size but the wrong field interpretation. This
residual is identical in kind to one the codebase already accepts and documents; this design does
not close it and must not pretend to. Whether to close it fully is Open Question 1.

**Why not a PyCapsule on instances (which would close the residual).** A `PyCapsule` holding a
real Rust pointer, set on each genuine `SourceText` *instance*, cannot be forged: Python cannot
manufacture a capsule wrapping a valid Rust pointer it does not already hold. It is not adopted
here because (a) it adds per-instance construction cost and API surface to the hot cross-cdylib
path that `span.rs:101-102` deliberately declined ("deliberately not a PyCapsule"); and (b) it
closes the same residual the project already accepts elsewhere via the layout probe, so the
cost/benefit does not clearly favor it for a blocker fix. Recorded as the deferred option in
Open Question 1.

### 2.B Close the cache-seeding bypass

The slow path caches the first validated foreign `SourceText` type in
`FLTK_FOREIGN_SOURCE_TEXT_TYPE` (`cross_cdylib.rs:35`, populated at `cross_cdylib.rs:97`), after
which same-type objects are accepted by pointer identity alone (`cross_cdylib.rs:82-91`). Today a
type becomes cache-eligible by passing only the forgeable `check_abi_pair`, so a forged type
could seed the cache and let later instances of it bypass even the attribute check (the residual
in `exploration.md:211-214`). The fix: a type is offered to `get_or_init` only after passing the
`tp_basicsize` gate (§2.A) *in addition to* `check_abi_pair`.

**Ordering invariant (load-bearing — state it in the SAFETY comment).** The basicsize gate must
be evaluated *before* the `get_or_init` call (`cross_cdylib.rs:97`) **and** must be the gating
condition for seeding, so the cache cell can only ever hold a basicsize-validated type. Concretely:
on a cache *miss*, run `check_abi_pair` then the basicsize gate, and only on both passing call
`get_or_init` and then `cast_unchecked`. The cache-*hit* branch (`cross_cdylib.rs:82-91`) is then
left **unchanged** — pointer identity to a cell that, by this invariant, can only hold a
basicsize-validated type is genuine provenance. If an implementer instead places the basicsize
check *after* `get_or_init`, or only inside the miss arm without making it the seeding precondition,
the broader pre-fix residual returns (any `check_abi_pair`-passing forge seeds the cell). This
ordering is the whole point of §2.B and must not be left implicit.

**Residual parity with §2.A.** §2.B narrows the cache-seeding residual to *exactly* the same
padded-forge residual as the direct path, not more: a `__slots__`-padded forge whose basicsize is
24 passes both `check_abi_pair` and the basicsize gate, so it can still seed the cell, after which
its instances hit the cache-hit `cast_unchecked` (UB). §2.B does **not** close this residual — it
makes the cache path's residual identical in kind to §2.A's, consistent with this design's
honesty about the padded forge. It is not a full closure of the cache residual.

### 2.C `extract_span` symmetry — deferred (no hazard to remove)

`extract_span` (`cross_cdylib.rs:310-338`) has the same `cast_unchecked` shape (`cross_cdylib.rs:331`)
but is gated by `is_instance` against the canonical `fltk._native.Span` type
(`cross_cdylib.rs:321`), where that type is fetched via `get_span_type`, which already runs
`check_abi_pair::<Span>` on first use (`cross_cdylib.rs:362`). `Span` is not subclassable
(`span.rs:155`, no `subclass`), so anything that passes `is_instance` **is** the canonical `Span`
type, whose `__basicsize__` is by construction equal to the local `size_of::<Span::Layout>()` in
the same process. A pure-Python forge cannot pass `is_instance` against the canonical type, and
genuine cross-cdylib layout skew is already caught once by `check_abi_pair::<Span>` in
`get_span_type`.

Consequently the basicsize gate adds **no rejection power** on the `extract_span` path: there is
no forged object that reaches its `cast_unchecked`, and the only thing the gate could catch
(canonical-type layout skew) is already caught. Adding it here would be code on the hot span-read
path that changes no observable behavior — speculative generality the blocker does not need. This
design therefore **does not** apply the gate to `extract_span`; it is recorded as
`TODO(forged-abi-extract-span-uniformity)`, a pure consistency/uniform-helper measure (not a
hazard removal) to be picked up only if a future change makes `extract_span` reachable by
non-canonical types. The segfault blocker is fully addressed by the `SourceText` path alone.

### 2.D Files / interfaces touched

- `crates/fltk-cst-core/src/cross_cdylib.rs`
  - `extract_source_text`: apply the `tp_basicsize` gate (§2.A) in the slow path. Required
    ordering (§2.B, §4.3a): on a cache miss run `check_abi_pair` **first**, then the basicsize
    gate, and only on both passing call `get_or_init` (seeding the cache) and then
    `cast_unchecked`. `check_abi_pair` stays as the version-skew diagnostic and runs before the
    basicsize gate so the existing pinned ABI/layout messages keep firing. The cache-hit branch
    (`cross_cdylib.rs:82-91`) is left unchanged.
  - Add a small helper, e.g. `fn check_instance_layout<T: PyClass>(ty: &Bound<PyType>) ->
    PyResult<()>`, that reads the type's `__basicsize__` via
    `ty.getattr("__basicsize__")?.extract::<usize>()` (not raw `PyType_GetSlot`; see §2.A),
    compares against `size_of::<<T as PyClassImpl>::Layout>()`, and returns a diagnostic
    `TypeError` on mismatch or read failure. The helper is generic so it could later be reused
    for `extract_span`, but this design does not call it there (§2.C is deferred).
  - SAFETY-comment updates at `cross_cdylib.rs:98-111` to reflect the new gate, the required
    `check_abi_pair`→basicsize→`get_or_init` ordering, and the *narrowed* (not closed) residual,
    which extends identically to the cache-seeding path (§2.B).
- `crates/fltk-cst-core/src/span.rs`
  - `_with_source_unchecked` docstring (`span.rs:433-443`): update to state the method now
    rejects non-native objects with `TypeError` rather than documenting forged input as silent
    UB. No signature change (it still delegates to `extract_source_text`); the behavior change
    lives in `extract_source_text`.
- `tests/test_rust_span.py`
  - New subprocess-isolated regression test class (see Test Plan).

No generated-code change, no public-API rename, no Python-side change. `_with_source_unchecked`
keeps its name and signature, so generated consumer `cst.rs` and `span_to_pyobject` are
unaffected. This respects the `CLAUDE.md` public-API/no-churn constraint.

---

## 3. Edge cases / failure modes

- **Genuine same-cdylib `SourceText`** — fast path (`cast`), never reaches the probe. Unchanged.
- **Genuine foreign-cdylib `SourceText`** (the real consumer path) — fails fast `cast`, passes
  ABI pair + basicsize gate (basicsize is identical across cdylibs linking the same rlib;
  verified live at 24/40), gets cached, `cast_unchecked` is sound. Must stay green via the
  existing `phase4_roundtrip_cst` round-trip tests and the new control test.
- **Trivial forge (copied attrs, default object layout)** — basicsize 32 ≠ 24 → `TypeError`.
  This is the verified 4/4 crash; now it cannot segfault.
- **Padded forge (`__slots__` tuned to match basicsize)** — passes the basicsize gate; this is the
  documented residual (§2.A). Same residual class as the existing layout probe. Not closed by
  this change; called out, not hidden.
- **Wrong ABI string / wrong layout int / missing markers / non-str / non-int** — already covered
  by `check_abi_pair`; those diagnostic `TypeError`s and their pinned messages are preserved,
  contingent on `check_abi_pair` running *before* the basicsize gate (the direct-call suite at
  `test_rust_span.py:308-868` and the Span-path subprocess suite at `test_rust_span.py:523-753`;
  see §4.3 for the ordering requirement).
- **`__getattr__`-raising or `__basicsize__`-missing exotic type** — a non-type object has no
  `__basicsize__`; the probe must surface that as a `TypeError`, not an unwrap panic. The helper
  returns `PyResult` and maps any read failure to a diagnostic `TypeError`, mirroring
  `check_abi_pair`'s `map_err` discipline (`cross_cdylib.rs:168-179`).
- **abi3 portability** — `__basicsize__` is a stable type attribute under the limited API on
  Python ≥ 3.10 (the project floor), read via `getattr("__basicsize__").extract::<usize>()` (the
  mandated path; see §2.A for why the raw `PyType_GetSlot` alternative is rejected). `tp_basicsize`
  is set by pyo3 from the layout basicsize at type creation (`create_type_object.rs:519-545`), so
  the attribute reports the genuine compile-time value for any cdylib linking the same rlib.
- **Cache races** — `get_or_init` semantics unchanged; the only change is that a type must pass
  the basicsize gate *before* it is offered to `get_or_init`. Two threads racing a genuine type
  both pass and cache the same pointer (harmless, as already noted at `cross_cdylib.rs:95-96`).
- **Subprocess test flakiness** — the regression test must assert on a crash signal (negative
  return code) in the unfixed state and a clean `TypeError` in the fixed state; see Test Plan for
  how this is made deterministic.

---

## 4. Test plan

All tests live in `tests/test_rust_span.py`, reusing the established subprocess harness
`_run_script` (`test_rust_span.py:488-497`) and the `pytest.importorskip` skip-guard pattern
where a fixture is needed.

### 4.1 Crash-regression test (the required subprocess-isolated repro)

New test class, e.g. `TestForgedSourceTextRejected`. Does **not** require `phase4_roundtrip_cst`
— the forgery is reproducible with `fltk._native` alone (`exploration.md:267-271`).

- **`test_forged_source_text_raises_type_error`**: subprocess runs the §1.1 `Forge` script and
  calls `Span._with_source_unchecked(0, 5, Forge())` inside a `try/except TypeError`. Asserts
  `result.returncode == 0` and `"OK" in result.stdout`. This is the test that *fails by
  segfault* (returncode `-11`/`139`) before the fix and *passes* after. Subprocess isolation is
  mandatory: a recurrence must not take down the suite.
- **`test_forged_source_text_message_is_diagnostic`**: same forge, asserts the `TypeError`
  message names the layout/ABI mismatch (so a future regression that swaps the gate for a silent
  pass is caught). Message-substring assertions follow the existing pinned-message convention
  (`test_rust_span.py:549-551`).
- **`test_padded_forge_passes_basicsize_gate_boundary`** (documents the residual *without pinning
  a UB outcome*): the `__slots__`-padded forge whose basicsize is tuned to 24. The padded forge
  reaches `cast_unchecked` on memory that is not a `PyStaticClassObject<SourceText>` — this is
  Undefined Behavior (§2.A, "still UB if cast"), so its *runtime outcome* (silent pass / crash /
  corruption) is not a contract and must not be asserted: UB has no stable value to pin, and a
  debug/release flip, pyo3 bump, or allocator change can flip it with no code change here. This
  test therefore pins only the **gate boundary**, never the post-cast behavior — it asserts that
  the padded forge's `type(forge).__basicsize__` equals the native
  `SourceText._fltk_cst_core_abi_layout` (i.e. it confirms the residual exists: basicsize alone
  cannot distinguish it), and the test does **not** call `_with_source_unchecked` on the padded
  forge. A comment in the test states explicitly that crossing the gate with this object is UB and
  out-of-contract, and that closing it requires a per-instance unforgeable token (Open Question 1).
  This documents the known residual as an explicit, tested fact while keeping the suite free of a
  UB-dependent (flaky or actively-misleading) assertion. If a stronger primitive is later adopted
  (Open Q1), this test is upgraded to assert rejection at `_with_source_unchecked`.

### 4.2 Cross-cdylib non-regression (the legitimate path stays sound)

Requires `phase4_roundtrip_cst` (skip-guarded).

The genuine-foreign **end-to-end accept path** is *already* covered and must stay green — do not
duplicate it: `test_with_source_unchecked_foreign_cdylib_works` (`test_rust_span.py:399`) passes a
real foreign `SourceText` directly to `_with_source_unchecked`, and
`test_source_bearing_span_reads_from_consumer_cdylib` (`test_rust_span.py:777`) exercises the same
accept path through `span_to_pyobject`. These pin the Requirements-item-1 obligation that a genuine
foreign object survives the slow path. The fix must keep them green; that is the primary non-regression
guard.

What those tests do **not** pin is that the genuine object passed *the new basicsize gate
specifically* (rather than the gate being bypassed, mis-ordered, or added on the wrong branch).
Add one focused assertion to close that gap:

- **`test_foreign_source_text_basicsize_matches_native_layout`**: build a foreign `SourceText`
  from the fixture and assert `type(foreign_st).__basicsize__ == SourceText._fltk_cst_core_abi_layout`
  (the native compile-time layout value). This pins the gate's *accept-branch precondition* directly:
  if a future change to either side breaks the cross-cdylib basicsize equality, it is caught at the
  gate's own input, not only end-to-end — so a mis-placed or accidentally-bypassed gate that still
  happens to pass the end-to-end tests cannot mask a broken precondition. This is a cheap, direct
  pin of the value the basicsize gate compares, complementing (not replacing) the existing
  end-to-end accept tests.

### 4.3 Existing tests preserved — and the check-ordering they pin

Two distinct existing suites touch this area and **both** must stay green.

**(a) The `extract_source_text` direct-call suite — the suite most exposed to this change.**
These call `Span._with_source_unchecked(...)` directly with forged objects and pin exact
diagnostic messages produced by `check_abi_pair`:

- `test_rust_span.py:308` `test_with_source_unchecked_str_raises_type_error` — `"SourceText ABI mismatch"`, `"pre-sentinel build"`
- `test_rust_span.py:314` `test_with_source_unchecked_no_marker_attr_raises_type_error` — `"_fltk_cst_core_abi marker"`, `"pre-sentinel build"`
- `test_rust_span.py:331` `test_with_source_unchecked_non_str_marker_raises_type_error` — `"not str"`
- `test_rust_span.py:347` `test_with_source_unchecked_bogus_abi_marker_raises_type_error` — `"ABI mismatch"`, `"FakeSource"`
- `test_rust_span.py:363` `test_with_source_unchecked_escape_in_type_name` — control-char escaping in the type name
- `test_rust_span.py:789` `test_source_text_abi_layout_mismatch_raises` — `"layout mismatch"`, `"999999"`
- `test_rust_span.py:803` `test_source_text_abi_layout_missing_raises` — `"partial-upgrade"`
- `test_rust_span.py:815` `test_source_text_abi_layout_non_int_raises` — `"not int"`
- `test_rust_span.py:827` `test_source_text_abi_string_missing_raises` — `"SourceText ABI mismatch"`, `"pre-sentinel build"`
- `test_rust_span.py:399` `test_with_source_unchecked_foreign_cdylib_works` — genuine foreign; must stay **accepting**

Every forged `FakeSource*` above is a plain class body with **no `__slots__`**, so its basicsize
is 32 ≠ 24 — the new basicsize gate would *also* reject each of them, but with the *basicsize*
message, not the pinned `check_abi_pair` message. **Therefore `check_abi_pair` must run before the
basicsize gate** (the ordering already mandated in §2.B and §2.D): the pinned ABI/layout messages
(`"layout mismatch"`, `"999999"`, `"partial-upgrade"`, `"not int"`, `"pre-sentinel build"`, the
escaped type name) continue to fire for these inputs. If an implementer runs the basicsize gate
first, all of these flip to the basicsize message and the suite goes red (or gets silently
weakened by loosening the assertions). This ordering is load-bearing for the regression surface
the design claims to protect; it is not optional.

**(b) The `TestSpanPathAbiGate` subprocess suite** (`test_rust_span.py:476-753`) exercises the
*Span*-path gate (`get_span_type` → `check_abi_pair::<Span>`), which this design does not modify
(see §2.C). Its seven scenarios remain green; the Span-path ABI messages are untouched.

`make test` (which builds fixtures first, `Makefile:94-97`) and `cargo-test-python-features`
(`Makefile:117-123`) are the lanes that exercise both suites.

### 4.4 After this change, the test surface guarantees

1. The exact forged-ABI segfault can never recur silently (it fails CI as a crashing subprocess).
2. The genuine cross-cdylib source-preservation path is exercised and asserted intact, and the
   new gate's accept-branch precondition (foreign basicsize == native layout) is pinned directly.
3. The known residual (basicsize-padded forge) is documented as a tested *fact* — the gate
   boundary is pinned (basicsize cannot distinguish it) without asserting any UB-dependent runtime
   outcome.

---

## 5. Open questions

1. **Should this change close the residual (PyCapsule on instances) or only narrow it
   (basicsize gate)?** The `tp_basicsize` gate (§2.A) narrows to the same residual the project
   already accepts and documents (`span.rs:117-126`). Closing it fully requires a per-instance
   unforgeable token (a PyCapsule wrapping a real Rust pointer), which adds hot-path cost and API
   surface the codebase deliberately declined (`span.rs:101-102`). Recommendation: narrow now
   (basicsize gate + cache-seeding fix), and record the capsule option as a
   `TODO(forged-abi-capsule-hardening)` if the user wants the residual fully closed. This is a
   genuine risk-vs-cost judgment, not resolvable from the spec alone: the spec says "reject
   fakes," but the padded forge shows that perfect rejection of *all* fakes is not achievable with
   any attribute- or size-based probe — only a per-instance unforgeable token can.

   USER ANSWER: The narrow fix is fine and DO NOT record the capsule option as a TODO; TODOs are not supposed to be vague "maybe we'll do this someday" things; they are supposed to be concrete things that we will almost certainly do in the relatively near future.

2. ~~**Should `extract_span` (§2.C) adopt the basicsize gate in this change, or defer?**~~
   *Resolved: deferred.* The `extract_span` path is not reachable by any forged object (its
   `is_instance`-against-canonical gate blocks pure-Python forges, and canonical-type layout skew
   is already caught by `check_abi_pair::<Span>` in `get_span_type`), so the basicsize gate adds no
   rejection power there — it would be code with no observable effect on the hot span-read path.
   §2.C records this as `TODO(forged-abi-extract-span-uniformity)`, a pure uniform-helper measure
   to revisit only if a future change makes `extract_span` reachable by non-canonical types. Not an
   open user-judgment question; carried as a TODO, not a blocker decision.
