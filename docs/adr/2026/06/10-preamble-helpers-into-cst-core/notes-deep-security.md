# Security review notes — preamble-helpers-into-cst-core

Commit reviewed: 5e29293 (base 87bf19e). Single pass.

Scope of change: byte-for-byte move of five cross-cdylib span helpers from the
generator-emitted preamble (`fltk/fegen/gsm2tree_rs.py::_preamble`, mirrored in
three committed generated `.rs` files) into a new module
`crates/fltk-cst-core/src/cross_cdylib.rs`, with `extract_span`,
`get_span_type`, `get_source_text_type` re-exported `pub` from the crate root.
No new logic, no new input handling, no secrets, no new dependencies (pyo3 0.23
already a dependency). Moved bodies verified identical to the deleted preamble
strings, including the SAFETY / INVARIANT VIOLATION comment block.

## security-1

- **File:line:** `crates/fltk-cst-core/src/cross_cdylib.rs:36` (`pub fn extract_span`), re-exported at `crates/fltk-cst-core/src/lib.rs:4`.
- **Issue:** `extract_span` is a *safe* `pub fn` whose slow path performs
  `unsafe { obj.downcast_unchecked::<Span>() }` after only a Python
  `isinstance` check against `fltk._native.Span`. Its soundness rests on a
  link/deployment invariant (every cdylib in the process links the *same*
  `fltk-cst-core` rlib as the installed `fltk._native` wheel) that the function
  cannot verify and the caller cannot express in code. This change widens who
  can reach the unsafe path: previously the helper was a private `fn` inside
  each generated cdylib, reachable only through code the FLTK generator itself
  emitted (a pipeline that co-builds against one rlib). It is now a public,
  safe-to-call API of `fltk-cst-core` callable by any downstream Rust crate.
- **Trust boundary / data flow:** `obj` is an arbitrary Python object crossing
  the Python→Rust boundary (e.g. a span argument from downstream Python
  application code). Under version skew — consumer crate pins fltk-cst-core
  revision A while the installed `fltk._native` wheel was built from revision B
  with a different `Span` layout — `isinstance` still passes (the Python type
  object is the genuine `fltk._native.Span`) but the unchecked downcast
  reinterprets a differently-laid-out `PyCell` payload.
- **Consequence:** memory corruption in-process (type confusion, wild
  `Arc<SourceText>` pointer deref on the subsequent `.borrow().clone()`), i.e.
  potentially exploitable UB rather than a clean error. Conditions: mixed
  fltk-cst-core versions loaded in one interpreter — a plausible downstream
  packaging mistake, not attacker-controlled per se, but it converts a
  dependency-pinning error into a memory-safety failure that Python code
  passing ordinary Span objects can trigger. Asset: process memory integrity
  of any application embedding generated parsers. Pre-existing behavior
  (moved verbatim, per design constraint) and documented in the SAFETY
  comment; the new exposure is the public-API promotion without a runtime
  guard.
- **Suggested fix (forward-looking; behavior-preservation was a stated
  constraint of this change, so this is a follow-up, not a blocker):** add a
  cheap runtime ABI sentinel before the downcast — e.g. export a
  `__fltk_cst_core_abi__` string/int attribute from `fltk._native` derived
  from `env!("CARGO_PKG_VERSION")` (or a layout hash) and have
  `get_span_type`/`extract_span` verify it once in the `GILOnceCell` init,
  failing with a clear `PyRuntimeError` on mismatch instead of proceeding to
  UB. Alternatively mark the cross-cdylib slow path `unsafe fn` with the
  invariant as a documented safety precondition and keep a safe checked
  wrapper for generated code. Worth a `TODO(slug)` + `TODO.md` entry per the
  repo's TODO system.

No other findings. Specifically checked: no injection surface (preamble is a
constant string; no grammar-derived content flows into the moved code), no
secrets in the diff, no auth/CSRF/SSRF/path/deserialization surface, test-file
changes are assertion inversions only, `pub(crate)` statics correctly prevent
external mutation of the `GILOnceCell` caches, and the `py.import("fltk._native")`
fixed-name import adds no new attack surface beyond standard sys.path semantics.
