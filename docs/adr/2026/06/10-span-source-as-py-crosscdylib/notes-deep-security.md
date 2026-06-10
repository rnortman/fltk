# Deep security review: span-source-as-py-crosscdylib

Commit reviewed: HEAD 588d55f (base 9db20de).
Scope: changed code only; OWASP + memory-safety / FFI trust-boundary classes.
Note repeated for downstream docs: Concise. Precise. Complete. Unambiguous.

## security-1 — Forgeable ABI-marker gate exposes `downcast_unchecked` as a pure-Python-reachable memory-corruption primitive

File: `crates/fltk-cst-core/src/cross_cdylib.rs:50-87` (`extract_source_text`), reached
via `crates/fltk-cst-core/src/span.rs:236-245` (`Span::_with_source_unchecked`).

Issue. `_with_source_unchecked` is a real, Python-callable classmethod on
`fltk._native.Span` (registered in `#[pymethods]`, declared in
`fltk/_native/__init__.pyi:42-50`). Its only validation of the `source` argument is the
ABI-marker gate in `extract_source_text`: it reads `type(source)._fltk_cst_core_abi` and,
if that string equals `FLTK_CST_CORE_ABI`, performs
`obj.downcast_unchecked::<SourceText>()` and dereferences `st.get().inner` as an
`Arc<SourceInner>`.

Trust boundary / data flow. Untrusted input = any Python object reaching
`_with_source_unchecked` from in-process Python. The "private by underscore" convention
is not an enforcement boundary — the method is fully bound on the public type. The gate
value is trivially knowable and replayable from pure Python:
`fltk._native.SourceText._fltk_cst_core_abi` is a readable classattr, and the design
(§2.2) itself documents that anything readable is replayable. A four-line pure-Python
class (`class Fake: _fltk_cst_core_abi = fltk._native.SourceText._fltk_cst_core_abi`)
passes the gate. `downcast_unchecked` then reinterprets that object's memory as
`PyClassObject<SourceText>` and reads `inner` (an `Arc` pointer) from an attacker-chosen
offset, then clones it (refcount increment write through that pointer).

Consequence. Any Python code able to call this method turns a forged object into
type confusion: arbitrary-pointer read of the `Arc` field plus a refcount write at a
controlled address, with subsequent `Arc` drop. This is a memory-corruption / potential
code-execution primitive in native code, reachable with no C extension — only pure
Python. It escalates a Python-level foothold (sandboxed interpreter, eval/exec injection,
a malicious dependency, untrusted plugin) into native memory unsafety. Contrast
`extract_span` (`cross_cdylib.rs:129-162`), which gates on `isinstance` against the
canonical type object — unforgeable from pure Python. This change weakens that property
for the `SourceText` path while presenting the marker as a safety check.

The design (§2.2, §3) acknowledges this as an accepted "contract delta" and defers
hardening to `TODO(crosscdylib-abi-sentinel)`. Flagging regardless: the accepted-risk
note lives in an ADR, not at the call site's threat model, and the realistic consequence
(Python→native memory-safety escalation) is understated as "out of contract."

Suggested fix (defense-in-depth that defeats the trivial pure-Python forge without a
full sentinel redesign): before `downcast_unchecked`, compare the foreign type's
`__basicsize__` against `size_of::<PyClassObject<SourceText>>()` and reject mismatches
with `TypeError`. A pure-Python class cannot match the native C layout's basicsize, so
this converts the trivial forge from UB into a clean error; it does not fix deliberate
ABI/layout skew (security-2) but removes the pure-Python-reachable UB that is the
exploitable case. The §2.2 soundness argument's "no inherited-marker-with-extended-layout
case" assumes a genuine pyo3 object; the basicsize check makes that assumption checkable.
If feasible, also restrict the gate to objects that are genuine pyo3 instances (non-forgeable
type provenance) rather than any object exposing the attribute.

## security-2 — ABI marker derived from `CARGO_PKG_VERSION` alone does not detect layout skew → silent UB

File: `crates/fltk-cst-core/src/cross_cdylib.rs:22`
(`FLTK_CST_CORE_ABI = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))`).

Issue. The marker that authorizes `downcast_unchecked` encodes only the crate version
(`0.1.0`, effectively never bumped). Two cdylibs linking the same `fltk-cst-core` version
but resolving different `pyo3` versions (consumer crates are standalone workspaces, e.g.
`tests/rust_cst_fixture/Cargo.toml`; real out-of-tree crates likewise) produce identical
markers over different `PyClassObject<SourceText>` layouts. The gate passes; the cast is
UB.

Trust boundary / data flow. This is the genuine cross-cdylib case the feature exists for:
a foreign-registered `SourceText` crossing into `_with_source_unchecked` via
`span_to_pyobject`'s slow path. The "input" is a build/deployment artifact, not a runtime
attacker, so this is lower-likelihood than security-1.

Consequence. Silent memory corruption (type confusion, bad `Arc` deref) in a consumer
process built against a skewed pyo3, with no error surfaced. The marker advertises a
version-skew guarantee it does not provide for the most likely skew axis (pyo3
resolution).

Suggested fix. As the `TODO(crosscdylib-abi-sentinel)` comment already states, fold the
pyo3 version and/or a layout hash (e.g. `size_of`/`align_of` of `PyClassObject<SourceText>`)
into the marker so mismatched layouts fail the string compare and produce the existing
clean `TypeError` instead of proceeding to the cast. Already tracked; recorded here so the
memory-safety consequence is explicit in the security review, not only in the design's
edge-case list.

## Other areas — no findings

- `span_to_pyobject` fast path (`cross_cdylib.rs:99-105`): `Span::type_object(py).is(...)`
  pointer-identity then `Py::new` of a `Clone`d `Span`; no unsafe, source `Arc` refcount
  bump only. Sound.
- `extract_source_text` fast path (`downcast::<SourceText>()`, lines 52-56): checked
  downcast, safe.
- Negative-gate error paths (`_fltk_cst_core_abi` absent, non-string, or non-matching
  string) all return `TypeError` before any `unsafe`. Correct.
- Generated accessor changes (`gsm2tree_rs.py`, regenerated `cst_*.rs`) only swap the
  O(N) copy path for `span_to_pyobject`; no new untrusted input handling, no injection,
  no secrets, no auth surface.
- No secrets, network, filesystem, deserialization, or templating surface in the diff.
