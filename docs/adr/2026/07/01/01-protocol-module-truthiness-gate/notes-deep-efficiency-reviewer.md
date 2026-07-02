# Deep efficiency review — protocol-module-truthiness-gate

Commit reviewed: cc1e869c09866461a967f1b39e3e187c87400baf (base 5ce1fd8)
Scope: fltk/fegen/gsm2tree.py, fltk/fegen/gsm2tree_rs.py (+ tests, TODO.md)

No findings.

The change is net efficiency-positive: `RustCstGenerator.generate_protocol` previously
built a throwaway `CstGenerator(py_module=pyreg.Module(["_protocol"]),
context=create_default_context())` purely to make a truthiness sentinel truthy. That
re-ran the full per-rule model derivation and allocated a fresh compiler context whose
type registrations were dead work, on every protocol-emission call. The diff replaces it
with `self._py_gen.gen_protocol_module_text()`, reusing the already-built Builtins-backed
generator — eliminating the redundant model derivation and dead context allocation.

The gsm2tree.py side only threads an `emit_kind_literal` keyword through the emission
chain; no added per-node/per-rule work, no new allocations, no hot-path or loop changes.

Nothing on this path is per-request/per-render hot (codegen runs at generation time), and
the change removes work rather than adding it. No redundant computation, missed
concurrency, no-op update, existence check, memory-growth, or over-broad-read concern in
the diff.
