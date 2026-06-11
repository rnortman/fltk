Style: concise, precise, complete, unambiguous. No padding, no preamble. Audience: smart LLM/human.

Commit reviewed: d442f56

---

## errhandling-1

**File**: `crates/fltk-parser-core/src/memo.rs:168`

**Broken error path**: `apply` decrements `state(parser).depth` unconditionally after `apply_inner` returns, but `apply_inner` contains several `panic!` sites (memo invariant violations at lines 196, 202–204, 280, 282). A panic unwinds past line 168 without executing the decrement. This leaves `depth` one too high for the remainder of the unwinding frame's call chain — but that frame is already panicking, so the parser state is abandoned.

**Why**: The design doc acknowledges this in §1 ("The invariant-violation `panic!`s inside `apply_inner` skip the decrement — irrelevant, since those panics abandon the parser state entirely"). However, if a caller wraps the top-level parse in `std::panic::catch_unwind` (which is architecturally possible and is exactly how Python C extensions recover from Rust panics — pyo3 uses it internally), the parser instance is returned with a stale `depth` counter. Subsequent calls will see inflated depth and may hit the limit prematurely, or worse, report `depth_exceeded` for inputs that didn't actually exceed it.

**Consequence**: A `PyParser` or Rust-native caller that catches a memo-invariant panic (pyo3 converts Rust panics to Python `PanicException` before handing control back to the caller) and then makes further calls on the same instance will experience an inflated depth counter. In the Python binding case, the design says the instance is spent after `RecursionError`, but memo-invariant panics propagate as `PanicException` — a distinct exception type. There is no code path that sets `depth_exceeded` on panic, so the instance is *not* marked spent, yet the depth counter is corrupted. Calls on a reused post-panic instance may return `RecursionError` (or silently wrong `None`) on inputs far below the actual limit with no diagnosable cause.

**What must change**: Either (a) set `depth_exceeded = true` before invoking `apply_inner`, and clear it only on clean return (i.e., replace post-call decrement with a guard struct or equivalent), so any panic leaves the instance in the spent state; or (b) document, at both the `apply` function level and the `PyParser` level, that the instance must not be reused after any panic/`PanicException` — and add an explicit doc note that pyo3 converts memo-invariant panics to `PanicException`, not `RecursionError`. Option (a) is strictly safer and keeps the "instance is spent" invariant coherent across all failure modes.

---

## errhandling-2

**File**: `fltk/fegen/gsm2parser_rs.py:920–927` / generated `tests/rust_parser_fixture/src/parser.rs:1292–1305` (pattern repeated for every rule)

**Broken error path**: The per-rule binding checks `self.inner.depth_exceeded()` *after* the call, which is correct for the truncated-`Some` hazard. However, the check is **not guarded by the sticky property on entry**. If the instance is already in the spent state (`depth_exceeded` true before the call — e.g., user calls a second `apply__parse_X` after a prior call already raised `RecursionError`), the flow is: `check_pos` (passes), `self.inner.apply__parse_X(pos)` (apply guard fires immediately, returns `None` without touching depth), `depth_exceeded()` check (true, raises `RecursionError`). This is *functionally correct* — the instance does raise `RecursionError` on the second call as documented and tested (T3 / `test_t5_spent_instance_raises_on_subsequent_call`).

**Why this is a finding despite being functionally correct**: the `error_message` and `error_position` methods on the spent instance are callable without error and return the state from the *original* parse, not from the failed depth-exceeded parse. A downstream handler that catches `RecursionError` and then calls `p.error_message()` to diagnose which rule failed gets the longest-match position from the first parse, not from the depth-exceeded invocation, with no indication it is stale. There is no error message or structured signal for "parse was aborted due to depth limit" — `error_message()` produces whatever the error tracker accumulated before depth-rejection, which may be a confusing match-failure message for a position deep inside the nesting, or the entirely wrong parse's message on a second call.

**Consequence**: On-call cannot distinguish "parse failed normally (no match)" from "parse failed due to depth limit" using `error_message()` alone; `depth_exceeded` is a separate getter that must be consulted. There is no structured log entry emitted at depth-rejection time — the only signal is the `RecursionError` exception itself. If the exception is caught and the handler logs `p.error_message()`, it produces misleading diagnostics.

**What must change**: Either (a) `error_message()` should check `depth_exceeded()` and return a distinct string ("parse aborted: depth limit exceeded (max_depth=N)") when the flag is set, so any diagnostic path that calls `error_message()` gets the correct signal; or (b) the `RecursionError` message should be self-sufficient (it currently carries `max_depth` but not the rule name or position at which depth was exceeded), and the doc for `error_message()` must note it is unreliable when `depth_exceeded` is set. Option (a) is low-cost and closes the diagnostic gap entirely.

---

## errhandling-3

**File**: `crates/fltk-parser-core/src/memo.rs:161–163`

**Broken error path**: When `st.depth_exceeded` is already `true` on entry to `apply`, the guard re-sets `depth_exceeded = true` (a no-op) and returns `None`. The guard also increments nothing and decrements nothing — correct. But the guard does not distinguish "depth just now exceeded" from "depth was already exceeded by a prior call." Both paths return `None`. This is intentional (stickiness).

However: `st.depth >= st.max_depth` with `max_depth = 0` fires on the first call, sets the flag, and returns `None` — correct per design ("max_depth == 0: first apply fails with flag set"). The design explicitly covers this as well-defined. No finding here, but note that this edge case is *not tested* in the new test suite (T1–T4, T5–T6): there is no test for `max_depth = 0`. A future regression (e.g. changing `>=` to `>`) would silently allow one level of recursion with `max_depth = 0`.

**Consequence**: Not a current bug but a test gap. If `max_depth = 0` semantics are relied upon by any downstream caller as a "disable all parsing" sentinel, a regression would be silent.

**What must change**: Add a test for `max_depth = 0` to memo_toy.rs (one-liner: `DepthParser::new(vec!["1".to_owned()], 0)` → `apply__nest(0)` returns `None` + flag set). Low effort; closes a gap the design doc mentions is well-defined.
