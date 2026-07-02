### 20. `fltkfmt-integration-tests` — DO (user-accepted deferral, now due)

- **Problem:** the `fltkfmt` binary crate has **zero tests**. Four design-specified
  integration tests (idempotency, golden, trailing-newline, parse-error path) were
  user-accepted as a deferral during review and never picked up. They're also the only
  way to exercise the `fltk_formatter_main!` macro's two error branches.
- **Ground truth:** all four confirmed absent; the parity pytest covers single-pass
  byte-parity only. The TODO's framing is stale in one way that *helps*: check-gating
  already happened, so landing the tests auto-gates them — no Makefile work needed.
- **The case for skipping:** the parity test already catches gross formatting breakage.
- **Recommendation: Do** — write the four tests in `crates/fltkfmt/tests/`.
