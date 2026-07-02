### 15. `spanprotocol-native-linecol` — DO

- **Problem:** native `fltk._native.Span` is not *statically* assignable to
  `SpanProtocol` (pyright-reproduced) because the two backends return two nominally
  distinct `LineColPos` classes. Downstream code annotating with `SpanProtocol` — the
  documented cross-backend pattern — type-fails when handed native spans.
- **What the work looks like:** the shape consistent with every verified constraint is a
  structural `LineColPosProtocol` in `span_protocol.py` (mirroring how `SpanProtocol`
  itself already bridges the two nominal `Span` types), with `line_span` retyped to
  `SpanProtocol`. Touches exactly three hand-written files (`span_protocol.py`,
  `terminalsrc.py`, native `.pyi`); generated artifacts don't name `LineColPos` at all.
  **Load-bearing constraint (verified real and untested):** `span_protocol.py` itself must
  keep naming zero `fltk._native` symbols, and the fix must add a stub-stability guard
  since no existing test covers that transitive property.
- **The case for skipping:** the gap is contained today (one deliberate
  assignability-pin site in pyright scope) and conformance holds at runtime.
- **Recommendation: Do** — this is the "near-drop-in Rust backend" promise made static.
