# Fix Forged ABI Segfault -- Design (Plain-English Explanation)

## What this is about

FLTK is a toolkit for building parsers -- programs that read structured text and turn it into a tree-shaped data structure called a Concrete Syntax Tree (CST). Historically FLTK was written entirely in Python. Recently a Rust backend was added to make parsing faster, and a production-readiness assessment reviewed whether that backend is safe to ship.

The assessment found one hard blocker: a publicly accessible method that crashes the Python interpreter when given certain bad input. In the Python-only version of FLTK, the equivalent method raises a polite error. In the Rust version, it causes a segmentation fault -- an unrecoverable, instant crash of the entire process. This design describes what is going wrong, why it happens, and how to fix it.

### The players

To follow the rest of this document, you need to know about a few pieces of the system.

**Span** is a class that records where a piece of parsed text came from in the original source. It tracks a start position, an end position, and optionally a reference to the source text itself.

**SourceText** is a Rust-backed class that holds the actual source string. When a Span carries source text, it holds a reference to a SourceText.

**`_with_source_unchecked`** is a method on Span that attaches a SourceText to a Span. It is underscore-prefixed by convention (suggesting it is internal), but it is fully accessible to any Python code that imports the library.

**pyo3** is the library that bridges Python and Rust. When Rust code needs to work with Python objects, pyo3 manages the translation. A key concept: pyo3 maintains a "type registry" per compiled library. When you ask "is this Python object really a SourceText?", pyo3 checks whether the object's type is the SourceText that *this specific compiled library* registered.

**cdylib** (compiled dynamic library) is the compiled form of a Rust extension. FLTK ships one cdylib (`fltk._native`), but downstream consumers who use FLTK to generate their own parsers compile their own separate cdylibs. These consumer cdylibs link the same Rust source code but produce independent compiled libraries, each with its own pyo3 type registry.

## The crash

### How it works normally

When `_with_source_unchecked` receives a SourceText, it needs to extract the inner source string from it. The function that does this (`extract_source_text`) has two paths:

**Fast path**: Ask pyo3 "is this object a SourceText registered by this exact cdylib?" This is a safe, checked operation. It works when the SourceText was created by the same compiled library that is now reading it.

**Slow path**: If the fast path fails (because the SourceText came from a *different* compiled library -- a real scenario when downstream consumers use FLTK), fall back to a validation-then-trust approach. Read two identifying attributes off the object's type (`_fltk_cst_core_abi` and `_fltk_cst_core_abi_layout`), check that they match expected values, and then perform an *unchecked cast* -- tell pyo3 "trust me, this object's memory is laid out as a SourceText" and read the source string directly from memory.

### How it crashes

The two identifying attributes are plain Python class attributes. Any Python code can read them off a real SourceText and copy them onto a fake class:

```python
class Forge:
    _fltk_cst_core_abi = SourceText._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout
```

An instance of this Forge class passes all the validation checks (the attributes match), reaches the unchecked cast, and then the Rust code interprets the Forge object's memory as if it were a SourceText. But it is not a SourceText -- its memory contains completely different data. The Rust code tries to read a pointer (an `Arc<SourceInner>`) from a memory location that contains something else entirely. The result is a segmentation fault: the process crashes immediately.

This was verified to happen 100% of the time in testing. The Python backend's equivalent method does a simple `isinstance` check and raises a TypeError for bad input -- always memory-safe.

### Why the slow path exists and must be preserved

The slow path is not dead code. It is the normal path for a real, legitimate use case: when a downstream consumer's compiled library creates a SourceText and passes it to `fltk._native`'s Span. In that scenario, the SourceText is genuine -- it was allocated by pyo3 with the correct memory layout -- but it was registered by a different cdylib, so the fast path's type-identity check fails. The slow path exists precisely to handle this cross-library case.

Any fix must continue to accept these genuine cross-library SourceText objects while rejecting fakes.

## The fix

### Why copying attributes is not enough as a gate

The fundamental problem is structural: **anything readable from Python is replayable from Python.** The two ABI marker attributes are class attributes that can be read and copied. This generalizes -- any check based on values that Python code can observe (attribute values, class names, flags) can be defeated by a forger who copies those values.

The fix therefore needs something that a pure-Python object cannot fake: a property of the object's actual type that is set by the Python runtime itself, not by user code.

### The basicsize gate

The fix adds a check on `tp_basicsize` -- a property of the type object that records how many bytes each instance of that type occupies in memory. This value is set by CPython itself when the type is created; it is not a copyable class attribute.

When pyo3 creates a SourceText type, CPython sets its `tp_basicsize` to the size of the Rust struct that backs it (24 bytes, in practice). The fix reads this value off the incoming object's type (via the stable `__basicsize__` attribute) and compares it to the compile-time size of the SourceText layout.

**Why this works for the common forgery**: A plain Python class like the Forge example above has a different `tp_basicsize` (32 bytes, because Python allocates space for an instance dictionary and other bookkeeping). The gate rejects it because 32 does not equal 24.

**Why this works for legitimate cross-library objects**: Every cdylib that links the same Rust source code with the same version of pyo3 produces a SourceText type with the same `tp_basicsize` (24 bytes), because the size is determined by the shared Rust struct definition. This was verified empirically.

**Why not use the raw C API to read this value**: CPython provides a C-level function (`PyType_GetSlot`) to read `tp_basicsize`, but it returns the value as a pointer that must be reinterpreted as an integer -- a quirk that is easy to get wrong (treating it as a real pointer would read garbage). The design mandates reading `__basicsize__` as a Python attribute instead, which returns a normal Python integer. This avoids the footgun entirely.

### The honest residual

The basicsize gate narrows the attack surface but does not close it completely. A determined forger can pad a Python class with `__slots__` to make its `tp_basicsize` match exactly:

```python
class Forge:
    __slots__ = ('x',)  # produces tp_basicsize == 24, matching SourceText
```

This padded forge passes the basicsize gate, reaches the unchecked cast, and the cast is still unsound -- the memory where Rust expects an `Arc<SourceInner>` pointer actually contains a Python object reference. This is the same *kind* of residual risk that the codebase already accepts and documents for the existing attribute-based checks. The design is explicit that this residual exists and is not closed.

### Closing the cache-seeding bypass

There is a second, subtler problem. The slow path caches the first validated type it encounters, so that subsequent objects of the same type skip validation entirely and go straight to the unchecked cast. Before this fix, a type became cache-eligible by passing only the forgeable attribute checks. A forged type could therefore seed the cache, and then later instances of that same forged type would bypass even the attribute checks.

The fix ensures that a type can only enter the cache after passing *both* the attribute checks *and* the basicsize gate. This makes the cache path's residual risk identical to the direct path's: only a `__slots__`-padded forge (which passes both checks) could seed the cache.

**The ordering matters**: The attribute checks (`check_abi_pair`) must run *before* the basicsize gate, and both must pass *before* the type is offered to the cache. This ordering is load-bearing for two reasons. First, it preserves the existing diagnostic error messages (the attribute checks produce specific, informative TypeErrors that existing tests pin). Second, it ensures the cache can never hold a type that was not basicsize-validated. If an implementer reversed this ordering or placed the basicsize check after the cache-seeding step, the fix would be defeated.

### Why not a stronger fix (PyCapsule on instances)

There is a technique that would close the residual entirely: store a PyCapsule (a special Python object that wraps a raw C/Rust pointer) on each genuine SourceText *instance*. Python code cannot manufacture a capsule containing a valid Rust pointer, so this would be unforgeable. However, this adds per-instance construction cost and API surface on a hot path that the codebase deliberately chose to keep lightweight. It closes a residual that the project already accepts elsewhere. The design records this as a deferred option (see Open Questions below) rather than requiring it for the blocker fix.

### What about the Span path?

There is a parallel code path (`extract_span`) that performs a similar unchecked cast for Span objects. The design analyzed this path and determined that it is not vulnerable to the same forgery: it uses an `isinstance` check against the canonical Span type, and Span is not subclassable, so any object that passes `isinstance` genuinely *is* the canonical Span type. A pure-Python forge cannot pass that check. Adding the basicsize gate to this path would add code with no observable effect on the hot span-read path, so the design defers it as a consistency cleanup item, not a safety fix.

## What changes in the code

The changes are narrow:

- **`cross_cdylib.rs`**: Add a small helper function that reads `__basicsize__` off a type and compares it to the expected layout size. Apply it in the slow path of `extract_source_text`, after the existing attribute checks and before cache seeding. Update the safety comments to reflect the new gate and the narrowed (not closed) residual.

- **`span.rs`**: Update the docstring on `_with_source_unchecked` to state that the method now rejects non-native objects with a TypeError, rather than documenting forged input as silent undefined behavior.

- **`test_rust_span.py`**: Add subprocess-isolated regression tests (see below).

No generated code changes. No public API renames. No Python-side changes. The method keeps its name and signature. Consumer code that calls it legitimately is unaffected.

## Edge cases

- **Same-library SourceText**: Takes the fast path (checked cast). Never reaches the new gate. Unchanged.
- **Genuine cross-library SourceText**: Fails the fast cast, passes attribute checks, passes the basicsize gate (verified: both libraries report 24 bytes), gets cached, unchecked cast is sound. Must stay working.
- **Trivial forge (copied attributes, no slots)**: Basicsize is 32, not 24. Rejected with TypeError. This is the crash that was verified 4/4; it can no longer segfault.
- **Padded forge (slots tuned to match basicsize)**: Passes the basicsize gate. Documented residual, not closed. Same kind of residual the codebase already accepts.
- **Missing or unreadable `__basicsize__`**: Surfaced as a TypeError, following the same error-handling discipline as the existing attribute checks.
- **Cache races**: Two threads validating a genuine type simultaneously both pass and cache the same pointer. Harmless, as already documented.

## Test plan

### Crash regression test

A new test class runs the forgery scenario in a subprocess (so a crash cannot take down the test suite). One test creates the Forge class, passes it to `_with_source_unchecked`, and asserts that a TypeError is raised (before the fix, this test fails because the subprocess crashes with signal 11). Another test checks that the TypeError message is diagnostic -- it names the specific mismatch so a future regression that swaps the gate for a silent pass would be caught.

A third test documents the residual by constructing the `__slots__`-padded forge and asserting that its `__basicsize__` matches SourceText's layout value (confirming that the basicsize gate alone cannot distinguish it). Critically, this test does *not* call `_with_source_unchecked` on the padded forge -- doing so would be undefined behavior, and the runtime outcome (crash, silent corruption, or apparent success) is not stable enough to assert on. The test documents the residual as a tested fact without depending on a UB-dependent outcome.

### Cross-library non-regression

Existing tests already exercise the legitimate cross-library path end-to-end and must stay green. One new focused test asserts that the foreign SourceText's `__basicsize__` matches the native layout value -- pinning the precondition that the basicsize gate checks, so a future change that breaks the cross-library basicsize equality is caught at the gate's own input, not only through an end-to-end failure.

### Existing tests preserved

The existing test suite includes tests that call `_with_source_unchecked` with various malformed objects and pin the exact error messages produced by the attribute checks. These tests all use plain Python classes without `__slots__`, so their basicsize is 32 (not 24). The basicsize gate would *also* reject them, but with a *different* error message. To preserve the existing pinned messages, the attribute checks must run *before* the basicsize gate -- so the attribute-check errors fire first for these inputs. This ordering requirement is not just a nice-to-have; the existing test assertions enforce it.

## What is still open

### Should this fix close the residual entirely, or only narrow it?

This is the one genuinely open question, and it is a cost-versus-risk judgment.

**What the question is**: The basicsize gate narrows the forgery surface to only `__slots__`-padded forges -- objects that happen to have the right size but the wrong internal field layout. Should the fix go further and close this residual entirely?

**What the options are**:

- **Option A (what this design proposes): Narrow only.** Add the basicsize gate, accept the padded-forge residual, and move on. This is consistent with what the codebase already accepts elsewhere for the same kind of residual, and it keeps the hot cross-library path lightweight.

- **Option B: Close it with a per-instance PyCapsule.** Store a PyCapsule wrapping a real Rust pointer on every genuine SourceText instance. Python code cannot manufacture such a capsule, so this is truly unforgeable. However, it adds per-instance construction cost and API surface on a path the codebase deliberately kept lean (there is an existing code comment that says "deliberately not a PyCapsule"). It closes a residual that is identical in kind to one the project already lives with.

**What hangs on the answer**: If you choose Option A, the padded-forge residual remains -- a deliberate attacker who knows the exact `__slots__` padding needed can still reach the unchecked cast with a non-genuine object. In practice this requires the attacker to write Rust-level-aware Python code targeting a specific internal layout size. If you choose Option B, the residual is fully closed, but every SourceText construction pays a capsule-creation cost that may matter on the hot path.

The design recommends Option A (narrow now) and records Option B as a deferred hardening item.
