# Efficiency review notes — fltkfmt integration tests

Commit reviewed: 2728a78246ccadcb6c34b1430188603ef82bcf28 (base 9233540)

Scope: pure test addition (`crates/fltkfmt/tests/cli.rs` + golden fixture),
plus TODO bookkeeping. No product/runtime code paths, no startup, no per-request
or per-render hot path touched. `main.rs` change is deletion of a comment.

## Findings

No findings.

Notes considered and dismissed (test-only, not worth flagging):

- Each subprocess spawn (`run()`) rebuilds the corpus×config sweep: test 1 does
  ~33 binary invocations, others a handful more. This is inherent to end-to-end
  CLI integration testing (the design explicitly chose subprocess-driving to reach
  the macro error branches a real consumer exposes). Cargo runs `#[test]` fns in
  parallel threads, so wall-clock cost is amortized. Not an efficiency defect.
- `format_format_is_format` joins `root.join(rel)` inside the inner config loop
  rather than the outer file loop; negligible (one PathBuf alloc per iteration in
  a test), no consequence.
- `text.clone()`/`base.clone()` in test 3 copy the fegen.fltkg source a few times;
  one-shot, tiny, test-only.
