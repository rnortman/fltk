# Deep security review: fix-forged-abi-segfault

Commit reviewed: 79460b6 (base d82e82f).
Scope: `crates/fltk-cst-core/src/cross_cdylib.rs`, `crates/fltk-cst-core/src/span.rs`, `tests/test_rust_span.py`.

The change is a memory-safety hardening fix: it adds a `tp_basicsize` "layout-genuineness"
gate (`check_instance_layout`) before a `cast_unchecked` type-confusion site, to reject
pure-Python forged-marker objects passed to the public classmethod
`fltk._native.Span._with_source_unchecked`. Trust boundary: arbitrary Python objects
(`PyAny`) reach `extract_source_text` → `cast_unchecked` → a raw reinterpret of the object's
memory as `Arc<SourceInner>`. Asset: process integrity (segfault / type-confusion read; the
design itself calls this "a latent security concern").

---

## security-1 — basicsize gate is bypassable via a metaclass `__basicsize__` property; the segfault the fix claims to close remains reachable

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:276-292` (`check_instance_layout`), reached
from `extract_source_text` slow path (`:118-136`); entry point `Span::_with_source_unchecked`
(`span.rs:455`).

**Issue.** The gate reads the candidate type's basicsize via
`ty.getattr(intern!("__basicsize__"))?.extract::<usize>()`. `getattr` on a *type object*
performs normal attribute lookup, which consults the **metaclass**. A pure-Python attacker can
therefore shadow `__basicsize__` with a metaclass property that returns the expected value
(24 for `SourceText`) while the instance keeps a completely unrelated CPython allocation. No
`__slots__` padding is needed, and the instance does **not** have the genuine
`PyStaticClassObject<SourceText>` layout at all.

Verified live (Python 3.10):

```python
class Meta(type):
    @property
    def __basicsize__(cls):
        return 24                      # forged value the Rust gate reads

class Forge(metaclass=Meta):
    _fltk_cst_core_abi = SourceText._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout

getattr(type(Forge()), "__basicsize__")  # -> 24  (what the Rust gate sees)
# real C-level tp_basicsize of this type (ctypes) -> 16  (default object)
```

The value the Rust gate compares (24) passes the gate; the object's real `tp_basicsize` is 16
and its memory is a bare `object`, so `cast_unchecked::<SourceText>()` + `st.get().inner.clone()`
reinterprets non-`SourceText` bytes as `Arc<SourceInner>` and clones a forged "Arc" pointer.

**Trust boundary / data flow.** Untrusted input: any Python caller constructs `Forge()` and
calls the public classmethod `native.Span._with_source_unchecked(0, 5, Forge())`. It enters
`extract_source_text`, fails the fast `cast` (foreign type), passes `check_abi_pair` (markers
copied), then passes `check_instance_layout` because the forged metaclass property returns the
expected size. Control reaches `cast_unchecked` (`cross_cdylib.rs:136`) and the type-confusion
read.

**Consequence.** The exact segfault / type-confusion primitive this change exists to close is
**still reachable from pure Python**, and via a *worse* object than the design's accepted
"padded-forge" residual: the metaclass forge needs no `__slots__` tuning and has the default
`object` layout (16 bytes, no Rust fields anywhere), so the bytes reinterpreted as
`Arc<SourceInner>` are CPython header fields — an attacker-influenceable pointer fed into Arc
refcount decrement on drop (a write-what-where-style primitive on a crafted address), not merely
an out-of-contract read. This directly defeats Requirement 1 of the design ("reject pure-Python
forged objects"). The regression test `test_forged_source_text_raises_type_error`
(`test_rust_span.py:884`) passes only because it uses the *trivial* forge (default `object`,
basicsize 32 ≠ 24, caught); it does not exercise the metaclass-property forge, so CI is green
while the hole is open.

Note the design (§2.A) explicitly chose `getattr("__basicsize__")` over
`PyType_GetSlot(ty, Py_tp_basicsize)` and asserted basicsize "is read off the type object
itself, not a copyable class attribute" and "a forger cannot present it by writing
`_fltk_cst_core_abi_layout = 24` on a class." That premise is false for the chosen access path:
the metaclass property is exactly such a Python-level override, and it is what the mandated path
reads. The rejected `PyType_GetSlot` path reads the real C slot (verified: returns 16 for the
forge) and is **not** shadowable by a Python property — i.e. the design rejected the one
primitive that would have held, in favor of the one that does not.

**Suggested fix.** Read the genuine C-level slot, which a metaclass cannot shadow:
`unsafe { pyo3::ffi::PyType_GetSlot(ty.as_type_ptr(), pyo3::ffi::Py_tp_basicsize) } as usize`
(abi3-valid; the documented quirk is that the returned `*mut c_void` *is* the `Py_ssize_t`
value reinterpreted — cast `as usize`, never deref). The design's stated reason for avoiding it
(footgun of dereferencing) is a lesser hazard than the security hole the `getattr` path leaves
open, and the cast-`as usize` discipline is a one-line comment. If the project insists on a safe
wrapper, no stable-ABI safe pyo3 API exposes the real slot, so `PyType_GetSlot` (with the
`as usize` discipline) is the correct tool here. Add a regression test using the metaclass-property
forge above asserting `TypeError` (subprocess-isolated, since a regression segfaults).

---

## security-2 — cache-seeding invariant inherits the security-1 bypass, persisting acceptance of a forged type

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:104-127` (cache-hit branch + seeding).

**Issue.** §2.B's load-bearing invariant is that `FLTK_FOREIGN_SOURCE_TEXT_TYPE` can only ever
hold a basicsize-validated type, so the cache-hit branch (`:104-110`) can skip re-validation and
`cast_unchecked` on pointer identity alone. Because `check_instance_layout` is bypassable
(security-1), a metaclass-property forge type passes both gates at `:118-122` and is seeded into
the cache at `:127`. Every subsequent instance of that forged type then hits the cache-hit
`cast_unchecked` at `:106` with **no** checks at all.

**Trust boundary / data flow.** Same untrusted entry as security-1
(`Span._with_source_unchecked`); the first forged instance seeds the cell, later forged instances
of the same class take the unchecked fast path.

**Consequence.** The forged type's acceptance is not a one-shot: once seeded, the process-global
cache treats it as genuine provenance for the rest of the process lifetime, so the type-confusion
read at `:106` recurs with zero gating for all further instances. This is a strict amplification
of security-1, not an independent bug — it resolves automatically once security-1's gate is made
unforgeable (then the forged type never reaches `get_or_init`, so the invariant holds as the
design intends). Flagged separately because the SAFETY comment at `:101-103` asserts the
invariant as a guarantee, and that guarantee is currently false.

---

## security-3 (informational) — documented padded-`__slots__` residual remains; out of scope of the blocker but still a pure-Python UB path

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs:133-136`, `span.rs` docstring.

The `__slots__`-padded forge (basicsize tuned to 24, real `object`-subclass layout, no
`SourceText` fields) is acknowledged by the design and code as an accepted, not-closed residual.
It is a genuine pure-Python-reachable type-confusion / UB path of the same kind as security-1
(though it requires the right slot count rather than a metaclass trick). Recording it only for
completeness: the design consciously accepted it and the user signed off on "narrow now."
Unlike security-1, this one matches the documented contract; security-1 does not, because the
design claimed the gate was unforgeable. If security-1 is fixed with the real C slot, this
residual still stands and remains the honest documented limitation. No action required beyond
what the design already states — but note that a real fix for security-1 does *not* close this,
so the "rejects pure-Python forged objects" framing in the `span.rs` docstring
(`span.rs:447-449`) remains partially aspirational either way.

---

## Not flagged (checked, clean)

- `check_abi_pair` ordering (runs before basicsize gate): correct per design; pinned-message
  tests preserved. No security impact.
- Error-message construction routes all interpolated type names / exception strings through
  `escape_control_chars` (`:280, :288, :150-151, :164-165`) — no log/terminal-injection via a
  crafted `__name__` or raising `__getattr__`. Good.
- `extract_span` (`:378-406`) unchanged and gated by `is_instance` against the non-subclassable
  canonical `Span` type; no forged object reaches its `cast_unchecked`. Consistent with §2.C.
- No secrets, no network/SSRF, no path/command/SQL injection, no auth surface in this diff.
- Test file uses `subprocess.run([sys.executable, "-c", script], ...)` with a static script and
  no untrusted interpolation — `# noqa: S603` is appropriate.
