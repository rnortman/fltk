# Deep error-handling review — fltkfmt integration tests

Commit reviewed: 2728a78246ccadcb6c34b1430188603ef82bcf28 (base 9233540d)

No findings.

Scope: pure test addition (`crates/fltkfmt/tests/cli.rs`) plus a TODO-comment
deletion in `main.rs` and TODO.md/docs edits. No product error paths change.

Considered and cleared:
- `.expect(...)` throughout the harness (`spawn`, `write_all`, `wait_with_output`,
  `status.code()`, `read`) — in test code these panics ARE the reporting mechanism;
  each carries a diagnostic message and fires only on genuine harness/invariant
  failure (e.g. child killed by signal). Correct use, not swallowed input errors.
- `let _ = std::fs::remove_file(...)` on temp-file cleanup — intentionally ignoring
  cleanup errors is appropriate; a cleanup failure should not fail an otherwise
  passing assertion, and no state depends on it.
- Assertion messages include file/config context and, where relevant, the captured
  stderr via `String::from_utf8_lossy` — failures are diagnosable.
- Pipe write/read ordering in `run()` (write-all-stdin-then-read) cannot deadlock
  for this corpus: the formatter drains stdin fully before emitting output, and
  inputs/outputs are well under the pipe buffer. Not an error-handling defect.
- The `assert_ne!` carve-out pins a known non-idempotency bug and trips loudly if
  the bug is fixed — reported and responded to correctly.
