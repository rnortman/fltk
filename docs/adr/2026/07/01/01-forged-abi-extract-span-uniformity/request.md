### 8. `forged-abi-extract-span-uniformity` — DO, reframed (the "no rejection power" claim is wrong)

- **Problem as written:** a "revisit only if a future change makes `extract_span` reachable
  by forged objects" note.
- **Ground truth:** the exploration traced a **pre-existing** forge path, no future change
  needed: `get_span_type` resolves `fltk._native.Span` **by name from a mutable module
  namespace** and validates it only via forgeable class attributes. Reassign
  `fltk._native.Span` to a classattr-matching plain-Python class before the first lookup
  (the existing ABI-gate tests already perform exactly this pre-init reassignment pattern)
  and `extract_span`'s `cast_unchecked` reinterprets a plain Python object's memory as a
  Rust `Span` — the same undefined-behavior class the `fix-forged-abi-segfault` work
  closed for `extract_source_text`. `check_instance_layout` (already built, generic)
  would reject it via the immutable `type.__basicsize__` descriptor.
- **What the work looks like:** TDD — subprocess test forging a classattr-matching
  `FakeSpan` through `extract_span`'s slow path first, then apply `check_instance_layout`
  on that path. Small, pattern-established.
- **The case for skipping:** an attacker who can reassign module attributes already runs
  arbitrary Python; this hardens against UB/segfault, not privilege escalation. But the
  project already decided that class of hardening is worth it for `extract_source_text`.
- **Recommendation: Do.**
