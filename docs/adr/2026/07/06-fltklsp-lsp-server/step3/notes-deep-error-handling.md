# Deep error-handling review — step3 (.fltklsp M4)

Scope: base `1ad3141` .. HEAD `8966d8ee42840c5f7fbf26090b14ef20eafc28e0`.
Lane: error observability and response only.

Files reviewed in depth: `fltk/lsp/symbols.py`, `fltk/lsp/features.py`,
`fltk/lsp/server.py` (rename + six handlers), `fltk/lsp/engine.py`,
`fltk/lsp/lsp_config.py`, `fltk/lsp/classify.py`, plus `positions.py` (clamping
behavior of `position_to_offset`) and pygls `JsonRpcException` semantics.

Overall the error-handling posture is deliberate and mostly sound: unresolved
references are a documented first-class silent state (§5); `rule_for_node`
raises `AssertionError` loudly on an invariant miss and that surfacing path now
correctly covers extraction; feature functions uniformly return `None` for
"nothing under cursor"; `prepare_rename`'s `assert reference is not None`
(features.py:325) is a correct invariant guard, not a swallow; handler offset
math is fully clamped in `positions.position_to_offset`, so out-of-range client
positions cannot crash a handler; the debounce push path already wraps analysis
in a logged `except Exception` (server.py:320-327). Two findings below.

---

## errhandling-1

- File:line: `fltk/lsp/server.py:386-394` (`rename_document`).
- Broken error path: a single guard folds five distinct conditions into one
  raise with the message `"cannot rename while the document has parse errors"`:
  `state.analyzed_version != version`, `analysis is None`, `analysis.error is
  not None`, `analysis.symbols is None`, `state.line_index is None`.
- Why: only one of these five actually is "the document has parse errors"
  (`analysis.error is not None`). Two others are categorically different and are
  mislabeled by the message:
  - `state.analyzed_version != version` is the **client-race** case — a
    `didChange` landed on the loop during the `_ensure_analyzed` await, so the
    freshly analyzed version no longer equals the version the rename targeted.
    The document is well-formed; nothing about parse errors is true. This is
    expected, transient, and retryable.
  - `analysis.symbols is None` (with `analysis.error is None`) and
    `state.line_index is None` (with `analysis` non-None) are, by the engine's
    own construction, **unreachable** — `engine.analyze` always sets `symbols`
    on the success path and `_store`/`_analysis_for` always set `line_index`
    alongside a stored analysis. If either ever fires it is an internal
    invariant violation (a bug in the engine/store contract), not user input.
    Folding it into an "expected bad input" message and the generic JSON-RPC
    internal-error code (`JsonRpcException` defaults to `-32603`) erases the
    distinction the mandate cares about: expected-bad-input vs
    invariant-violation.
- Consequence: on a well-formed document, a rename that merely raced a keystroke
  reports "cannot rename while the document has parse errors." The user sees a
  false claim about their document; on-call reading the client's error log sees
  a parse-error complaint against a file that parses cleanly and cannot tell a
  benign race (retry succeeds) from a genuine parse failure (edit the file)
  from a real engine invariant break (symbols/line_index unexpectedly `None`).
  The invariant break in particular would be permanently disguised as ordinary
  "parse errors" and never diagnosed.
- What must change: split the guard. The race case
  (`state.analyzed_version != version`) should get its own message (e.g.
  "document changed during rename; retry") — and ideally a
  content-modified/request-cancelled style signal rather than internal-error.
  The `symbols`/`line_index` `None`-with-no-error cases should either be
  asserted as invariant violations (distinct message identifying which
  invariant broke, so a crash/error names the real bug) or, if kept as defense,
  logged with their true cause instead of the parse-error text. Reserve the
  "parse errors" message for `analysis.error is not None`.

---

## errhandling-2

- File:line: `fltk/lsp/server.py:320-327` (`_debounced_analyze`'s catch), as
  now exercised by the new `symbols.extract` call in `engine.py:152`.
- Broken error path: the diff routes a new, structurally non-trivial tree walk
  (`symbols.extract` → `_walk` → `classify.rule_for_node`, which can raise
  `AssertionError` on a kind/grammar divergence) through the engine's success
  path, which catches only `RecursionError` (`engine.py:159`). On the debounced
  push path any other exception from extraction propagates to
  `_debounced_analyze`'s `except Exception`, which logs `f"...: {exc!r}"` —
  repr only, no traceback and no indication of which stage (parse vs
  extraction vs classification) failed.
- Why: the log line is the sole record for this fire-and-forget task, and it
  discards the stack. Before this round the walk that ran here was
  parse+classify; extraction adds a new failure surface (scope walk, matcher
  dispatch, resolution) whose exceptions now all collapse to the same
  repr-only line.
- Consequence: when an extraction invariant fires in the field (e.g. a
  `rule_for_node` miss triggered by a grammar/naming drift, or a bug in the
  scope/hoist walk), on-call gets one line naming the exception type and the
  URI but not the offending code path or the CST location — enough to know
  "analysis failed," not enough to localize it to extraction or reproduce it.
  Note this handler is pre-existing and unchanged by the diff; the finding is
  that the new failure surface makes its lossiness materially more likely to
  matter, not that the diff introduced the catch.
- What must change: log with a traceback (e.g. `exc_info`/`traceback.format_exc`
  into the message) so an extraction/classification invariant break is
  diagnosable from the client server-log alone. Optionally distinguish the
  stage. (Lower confidence than errhandling-1, since the handler predates the
  diff; flagged because M4's new walk is what makes it bite.)
