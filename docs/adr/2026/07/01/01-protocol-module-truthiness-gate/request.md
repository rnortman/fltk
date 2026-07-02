### 22. `protocol-module-truthiness-gate` — DO

- **Problem:** a code generator decides whether to emit precise `kind: Literal[...]`
  discriminants based on the *truthiness of an unrelated field*, silently degrading to
  `kind: object` for empty-module-backed generators; the Rust backend works around it by
  constructing a throwaway generator with a fake module name.
- **Ground truth:** fully verified, and better than claimed: `py_module` has **no other
  live use** anywhere in the protocol-emission path, so an explicit
  `emit_kind_literal` parameter doesn't just rename the trap — it lets the Rust backend
  reuse its existing generator and **delete the throwaway construction** (including its
  redundant context + full rule-model re-derivation). Two production callers; a defaulted
  keyword keeps both source-compatible. (TODO.md misnames the containing method; the
  gate is in `_protocol_class_for_model` — exploration has exact lines.)
- **The case for skipping:** the trap is documented at the gate; both callers work today.
- **Recommendation: Do** — removes a rediscovered-per-caller trap and net-deletes code.
