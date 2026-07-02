### 18. `unparser-none-path-diagnostics` — DO, reframed (backends already diverge)

- **Problem:** two silent `None` paths in the generated Rust unparser: (1) a confirmed
  comment can be silently dropped from formatted output; (2) a bad span silently nulls the
  whole `unparse_*` result with no record of which span failed.
- **Ground truth that changes the framing:** the TODO says a policy must be applied to both
  backends "so behavior stays in parity" — but for site 2 **parity does not exist today**:
  the Python unparser already raises a `ValueError` naming the span for the source-bearing
  bad-offset case, while Rust silently propagates `None`. So this is reconciling an
  existing divergence, and the direction is nearly forced: bring Rust up to Python's
  established raise-with-context behavior. Site 1 is genuinely symmetric (both drop
  silently) and needs one small policy call applied to both.
- **What the work looks like:** small design note (site-1 policy + exact Rust error
  shape), then generator changes in both backends' emitters + regen + tests.
- **The case for skipping:** both are invariant-violation paths unreachable in the
  shipping `fltkfmt` pipeline (every span carries source).
- **Recommendation: Do** — silent data loss in a formatter is the worst failure mode to
  leave undiagnosed, and half the "policy decision" turns out to be already made.
