errhandling-1

File: crates/fltk-cst-core/src/span.rs lines 201-263 (resolve_line_col docstring preconditions)

Broken error path: The documented preconditions for `resolve_line_col` state "pos >= 0
(negative-index sentinels must be short-circuited by the caller)" and "pos < text.chars().count()
(EOF clamp must be applied before calling; pos == len is not accepted here — the caller must
decrement to len - 1)". Both preconditions are violated in practice by both callers:

- `TerminalSource::pos_to_line_col` (terminalsrc.rs:181): accepts `pos ∈ [-1, len]`; for
  `pos == -1` (the initial `ErrorTracker.longest_parse_len` sentinel) it does NOT
  short-circuit before calling `resolve_line_col`. It passes `pos = -1` directly.
- `Span::line_col_inner` (span.rs:526): for empty source (`len = 0`, `start = 0`) the EOF
  clamp fires (`start == len → pos = start - 1 = -1`) and then calls
  `resolve_line_col("", -1, ...)`. The precondition says `pos == len` is not accepted and
  the caller must decrement — but `len - 1 = -1` in the empty case, so the function is
  called with `pos = -1`.

Why it matters / what goes wrong: The function happens to return the correct result for `pos = -1`
because the `-1` sentinel pushed into `line_ends` for empty input participates correctly in the
bisect. But the documented precondition is false, so it cannot be safely enforced. A maintainer
who reads the precondition, trusts it, and adds a guard (`if pos < 0 { return None; }` to
`resolve_line_col`) would silently break both callers' empty-source behavior (the initial parse
error at `longest_parse_len = -1` would produce no line/col in `format_error_message`, degrading
to "Syntax error at unknown position"). There is also no test that directly calls
`resolve_line_col` with `pos = -1` and asserts the result; the behavior is only covered
indirectly through `TerminalSource::pos_to_line_col(-1)` tests.

Consequence: Maintainability trap. The function has a documented contract it does not enforce and
that its own callers violate. On-call cannot diagnose the "Syntax error at unknown position"
fallback (errors.rs:137) if a future enforcement of the precondition breaks the `-1` path,
because the degraded path leaves no structured log.

What must change: Expand the documented preconditions to state that `pos = -1` is accepted when
`len = 0` (the empty-source sentinel case), matching the actual behavior. Or: add an explicit
guard `if pos < 0 && pos != -1 { return None; }` (rejecting all negative positions except the
one sentinel), document that `-1` is the sentinel, and add a `resolve_line_col("", -1, ...)` unit
test that asserts `Some(LineColPos { line: 0, col: -1, ... })` to lock the contract. The sentinel
test in `resolve_line_col_tests::resolve_empty_input` already passes `pos = -1`, but its comment
("pos=-1 expected to return col=-1") does not explain that this violates the stated precondition.

---

errhandling-2

File: crates/fltk-cst-core/src/span.rs line 795

Broken error path: `line_col_or_raise` uses a bare `.unwrap()` on `self.source.as_ref()` after an
earlier `self.source.is_none() → return Err(...)` guard. The same guard-then-unwrap pattern in
`text_or_raise` (same file, line 664) uses `.expect("invariant: source is Some — is_none() guard
above returned Err already")` instead. The two methods are structurally identical; only one has the
invariant message.

Why it matters / what goes wrong: If a future refactor reorders the guards in `line_col_or_raise`
(e.g. moves the `start < 0` check before the `is_none()` check, or wraps the body in a helper that
loses the early return), the bare `.unwrap()` panics with `called Option::unwrap() on a None value`
and no context — the on-call message is identical to any other unwrap in the process, with no
indication that it is a supposed-invariant-protected site.

Consequence: Silent diagnostic regression relative to the existing `text_or_raise` pattern. If this
panic fires in production, the thread/process crash message contains no information linking it to
span line-col resolution or explaining which guard was supposed to have prevented it.

What must change: Replace `.unwrap()` at line 795 with
`.expect("invariant: source is Some after is_none() guard returned Err already")` to match the
`text_or_raise` pattern at line 664.

---

errhandling-3

File: crates/fltk-cst-core/src/span.rs lines 803-808

Broken error path: `line_col_or_raise` has a final fallthrough arm:

    None => Err(PyValueError::new_err(format!(
        "Span({}, {}) could not resolve line/col",
        self.start, self.end
    )))

This arm fires when `line_col_inner()` returns `None` after all three prior guard checks
(`source.is_none()`, `start < 0`, `start > len`) have already passed. Under the current
implementation this path is unreachable: once source is present, `start >= 0`, and
`start <= len`, `line_col_inner` → `resolve_line_col` cannot return `None` because the bisect
invariant always holds for inputs in that domain (the `line_ends` sentinel guarantees at least
one element and `partition_point` always finds an index in range).

Why it matters / what goes wrong: The error message "could not resolve line/col" is diagnostic
dead weight. It names the symptom, not the cause, and gives the on-call engineer no information
about which precondition was unexpectedly violated. Compare to the three specific messages that
precede it ("has no source", "has negative indices", "is out of bounds for source of length N"),
which all identify the violated invariant. If this arm is ever reached (e.g. through a future
change to `resolve_line_col` that adds new `None` returns), the error message will not help
diagnosis. An on-call engineer seeing `ValueError: Span(5, 10) could not resolve line/col` has
no starting point.

Consequence: If ever reachable, on-call has zero structured context about which guard failed or
which part of the bisect returned unexpectedly. The fallthrough message adds no information beyond
what the span's `(start, end)` already shows.

What must change: Replace the fallthrough message with one that identifies the unexpected-state
nature: e.g. `"Span({}, {}) line_col_inner returned None despite passing all guards — internal
invariant violation; start={}, source_len={}"`, including the already-computed `len` value, so the
error carries enough data to reconstruct what happened. Alternatively, since the path is provably
unreachable, replace the `match` with an `expect` on the `line_col_inner()` call:
`self.line_col_inner().ok_or_else(|| PyValueError::new_err(format!("...")))` with the full context.
