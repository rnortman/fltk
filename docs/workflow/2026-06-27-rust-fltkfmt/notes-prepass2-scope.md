# Scope prepass — increments 4-6 (partial review)

Commit reviewed: c52d998a09e4ce433289872be91a3ce7c249dca0
Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a

## Findings

**scope-1** — `crates/fltk-fmt-cli/src/lib.rs` test count mismatch: implementation log
(increment 4) claims "15 new `run_inner` integration tests … 25 tests pass." The base
commit had 12 tests; HEAD has 25 (confirmed via grep); the diff therefore adds 13 new
tests, not 15. The total of 25 is correct and all behaviors listed in the log and required
by design §4 for `fltk-fmt-cli` are present and tested; no behavior is missing. The
discrepancy is a log count error, not a coverage gap.

No other findings. Everything the log claims is done for increments 4-6 is present in the
diff. Both called-out deviations (`run_inner` testability seam; `$crate::` re-exports
instead of bare `fltk_unparser_core::` path) are accurately described and behaviorally
equivalent to the design. Items explicitly deferred by increment 6 (Makefile gating,
`crates/fltkfmt/tests/`, cross-backend parity pytest) are correctly excluded from this
partial review scope.
