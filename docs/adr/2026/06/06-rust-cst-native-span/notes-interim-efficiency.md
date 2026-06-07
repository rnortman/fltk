# Efficiency review — interim (Rust CST native span/children)

Base 6fd32e7 → HEAD 767315f. Scope: native node state per design.md. Out-of-scope gaps
(§2.5 in progress, §2.6/§2.7/remaining §2.8) not reported.

Concise. Precise. No padding.

## efficiency-1 — `FLTK_NATIVE_SPAN_TYPE` resolution duplicated in every accessor

`fltk/fegen/gsm2tree_rs.py` emits the same 6-line `FLTK_NATIVE_SPAN_TYPE.get_or_try_init(py, ||
{ py.import("fltk._native")... })` block inline in: span getter (`_span_getter_setter`:501),
`children` getter (`_children_getter`:548), `append` (:573), `extend` (:618), `child` (:664),
and all five per-label methods × every labeled rule (`_per_label_methods`:691,709,731,753,786).
231 copies in `src/cst_fegen.rs` alone.

Problem: each call site re-runs the `GILOnceCell` get + closure-setup + `.bind(py)`. The cell
caches the *type object* (so the import only happens once process-wide — good), but the
per-call cost is paid on every accessor invocation: a cell load, a bind, and dead closure code
the compiler must keep. The `span` getter / per-label accessors are on the per-node read hot
path (every CST traversal hits them).

Consequence: per-accessor-call overhead on every CST read/write; shows up at parse time and in
any downstream traversal that calls accessors in a loop. Scales with tree size × accessor calls.
Also bloats the generated `.rs` (code size → compile time, i-cache).

Fix: emit one free function in the preamble, e.g.
`fn native_span_type(py) -> PyResult<&Bound<'_, PyType>>` that wraps the `get_or_try_init`, and
have every accessor call it. Single definition, single cache load, ~225 fewer emitted blocks.
`extract_span` already lives in the preamble as the model for this.

## efficiency-2 — span getter / `to_pyobject` Span variant: per-call PyObject construction, source dropped

`_span_getter_setter` (:507-510) builds the Python `Span` via `span_cls.call1((start, end))`
every getter call; `<Name>Child::to_pyobject` Span arm (`_child_enum_block`:371) does the same
per child per `children`/`child`/`children_<label>` call. Each call allocates a fresh
`fltk._native.Span` pyobject from raw `(start, end)`.

Problem (efficiency facet only — source-loss correctness is correctness-reviewer's lane): the
`children` getter is documented as rebuilt-per-call (design §2.3/§3); combined with a fresh Span
alloc per terminal child, a single `node.children` read on a node with N terminal children does
N PyObject allocations, repeated on every getter call. fltk2gsm-style consumers that read
children in a loop pay O(children) allocation each pass.

Consequence: per-traversal allocation cost proportional to terminal-child count; bites any
consumer that reads `children` repeatedly. The `TODO(rust-cst-child-node-identity)` boundary
cache (design §3) would also amortize this if/when added.

Direction: acceptable for now given the design explicitly accepts rebuild-on-call and defers
the identity cache. Flag only: if traversal-heavy consumers appear, the same per-node `Py`
cache that fixes identity also removes the repeated allocation.

## efficiency-3 — cross-backend enum `__hash__` allocates a PyString per call

`_emit_rust_cross_backend_eq_hash` (`gsm2tree_rs.py`:221-225) emits `__hash__` that does
`PyString::new(py, self.__repr__())` then hashes it — a heap PyString allocation on every hash
of any `NodeKind` / `<Name>_Label` value.

Consequence: hashing labels/kinds (e.g. using them as dict keys or set members in a consumer
loop) allocates per hash. Per-call cost on any hash-keyed lookup over these enums.

Status: the design comment (gsm2tree_rs.py:204-206) explicitly defers amortization ("amortizing
this via GILOnceCell is deferred"). Recorded as a known, accepted cost — not a new regression.
The salted-string-hash requirement (AC4) forces the PyString today; a `GILOnceCell<isize>` per
variant would cache the computed hash. Revisit if enum hashing shows on a profile.

## Notes

- `extend_children` (:646) correctly takes `PyRef` (borrows other, no whole-node clone); per-child
  `.clone()` is inherent to native ownership. No issue.
- `_generic_extend` resolves `span_type` once before the loop (good); `child_<label>`/`maybe_<label>`
  early-break after the second match (good). No N+1 in the loops themselves beyond efficiency-1.
- `Span` is 24 bytes with thin-pointer `SourceInner` (span.rs:14-19) and `Arc`-clone-on-copy — good.

No other findings.
