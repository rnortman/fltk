### 4. `native-span-init-error-context` — DO, reframed (rider on a real drift bug)

- **The real problem found:** committed `src/lib.rs` **has drifted from its generator**.
  Someone added `LineColPos` registration to `src/lib.rs` without teaching
  `gsm2lib_rs.py` about it — so the next `make gencode` run will silently **drop
  `LineColPos` from `fltk._native`**, breaking the native module. This is a live
  regression trap, found incidentally during validation.
- **The TODO itself:** wrap one generated `Py::new(...)?` with an error message naming the
  UnknownSpan sentinel. Failure is OOM-only — marginal on its own (prior judge:
  "marginal-yes"), but it's a 3-line generator change with an established sibling pattern.
- **What the work looks like:** teach the generator to emit `LineColPos` registration
  (fixing the drift), add the `map_err` wrap, regenerate `src/lib.rs`, pin both with
  generator tests.
- **The case for skipping:** none for the drift fix; the wrap alone would be skippable.
- **Recommendation: Do** — drift fix is the substance, error-context wrap rides along.
