# Deep correctness review — round 2 (9719bab7..d9ab841, HEAD d9ab841)

Scope: logic/control-flow/data-flow/races in the M2 diff (`fltk/lsp/server.py`,
`server_cli.py`, `positions.py`, `features.py`, `engine.py`, `plumbing.py`,
`plumbing_types.py`). Verified against installed pygls 1.x sources where the server
depends on pygls behavior (`capabilities.choose_position_encoding` reads the
`_SUPPORTED_ENCODINGS` module global at call time, so `_constrain_pygls_encodings` is
sound; `Workspace.get_text_document` creates a from-disk document for an unknown URI).
Position math (`LineIndex`, surrogate-pair clamping, `\r`/`\r\n`/`\n` handling), the
relative token encoding (including the multi-line split and the `delta_line != 0`
absolute-column branch), folding line math (`span.end - 1`), selection-chain dedup, the
`error_pos` fallback chain (`ApplyResult` is a plain frozen dataclass, so `elif result:`
is a correct None-check), and the single-flight `_inflight` identity-guarded cleanup all
check out.

## correctness-1: a cancelled debounce task's `finally` evicts its replacement from `_debounce`

- **File:line:** `fltk/lsp/server.py:231-247` (`_debounced_analyze` / `schedule_debounced`)
- **What's wrong:** `_debounced_analyze` unconditionally runs
  `self._debounce.pop(uri, None)` in its `finally`, including on the cancellation path.
  But `schedule_debounced` is synchronous: it pops the old task, calls
  `existing.cancel()`, and immediately installs the *new* task at `self._debounce[uri]`
  — all before yielding to the event loop. The old task's `CancelledError` is only
  delivered on a later loop iteration, at which point its `finally` pops `uri` and
  removes the **new** task's dict entry (without cancelling the new task, which keeps
  running untracked). The same eviction happens on the normal-completion path if a
  `didChange` lands in the window between the sleep future resolving and the task
  resuming.
- **Why:** trace: didChange#1 → `_debounce[uri] = T1` (T1 sleeping). didChange#2 →
  pop T1, `T1.cancel()`, `_debounce[uri] = T2`. Loop resumes T1 with `CancelledError`
  → `except` returns → `finally` executes `pop(uri)` → removes T2's entry. T2 is still
  scheduled but invisible to both `schedule_debounced` and `drop`.
- **Consequence:** two distinct failures.
  1. Debounce coalescing is broken for every reschedule after the first: didChange#3
     finds no entry to cancel, so the untracked T2 fires mid-burst — an extra analysis
     per edit in a burst, exactly what `_DEBOUNCE_SECONDS` exists to prevent (it
     re-reads the latest text, so output is not wrong, just uncoalesced).
  2. `drop()` (didClose) cannot cancel the untracked timer. ~0.2s after a
     close-during-edit-burst, T2 fires, `self.workspace.get_text_document(uri)`
     silently creates a **from-disk** document (pygls `workspace.py:142-151`), the
     server analyzes the on-disk content, `_store`'s `setdefault` resurrects
     `_docs[uri]` after `drop()` cleared it, and `analyze_and_publish` publishes
     diagnostics for a **closed** document (its version-match check passes: both
     versions are `None` for a from-disk document). The client shows phantom
     diagnostics for a file the user closed, and the just-published empty-diagnostics
     clear from `drop()` is undone. This also seeds the state-resurrection wedge in
     correctness-2.
- **Suggested fix:** in the `finally`, only remove the entry if it is this task:
  `if self._debounce.get(uri) is asyncio.current_task(): del self._debounce[uri]`
  (or capture the task object in `schedule_debounced` and pass it in for an identity
  compare). Additionally, `_debounced_analyze` can bail out early when
  `uri not in self.workspace.text_documents` so a legitimately-fired timer never
  analyzes a from-disk ghost.

## correctness-2: `drop()` does not stop an in-flight analysis from resurrecting `_docs[uri]`; a reopened document can then be pinned to its pre-close analysis

- **File:line:** `fltk/lsp/server.py:147-163` (`_store`), `:249-256` (`drop`),
  `:165-183` (`_analysis_for`)
- **What's wrong:** `drop()` removes `self._docs[uri]` and `self._inflight[uri]`, but
  any analysis already submitted to the worker keeps running, and when its awaiter
  resumes, `_store`'s `self._docs.setdefault(uri, _DocState())` recreates the per-URI
  state after the close. Nothing marks the state as dead. There is no
  "URI still open?" check anywhere on the store path (the only guard is the
  version-ordering comparison).
- **Why:** trace: a pull request (`semantic_tokens_full`, version 7) is awaiting
  `_analysis_for`; didClose arrives; `drop()` clears `_docs[uri]`; the worker finishes;
  `_store(uri, 7, ...)` runs `setdefault` → fresh `_DocState` with
  `analyzed_version=7`, `analysis`/`last_good` for the closed text. (The leaked
  debounce timer from correctness-1 produces the same resurrection without needing an
  in-flight pull.) Now the user reopens the file: per LSP, a new document lifetime's
  version typically restarts at 0/1 (the spec only requires versions to increase
  *within* a lifetime). `did_open` → `analyze_and_publish(uri, 1, text)` →
  `_analysis_for` analyzes the new text, but `_store`'s guard
  `version < state.analyzed_version` (1 < 7) **refuses to store it** and returns the
  resurrected state. `analyze_and_publish` then checks `document.version == version`
  (1 == 1, true) and calls `_publish(uri, 1, state)` — publishing the **pre-close**
  analysis's diagnostics (computed against the pre-close text and its `LineIndex`)
  labeled with the new document's version.
- **Consequence:** after a close/reopen race, the document is wedged: every analysis
  for versions ≤ 7 is discarded by `_store`, `_ensure_analyzed` never finds a matching
  `analyzed_version` (so every pull re-parses, then discards), diagnostics shown are
  those of the pre-close text at pre-close positions, and `last_good` (hence semantic
  tokens, folding, selection) is served from the pre-close text — against a possibly
  completely different current buffer. The state model's core invariant
  ("`_docs[uri]` exists only for open documents, and `analyzed_version` belongs to the
  current document lifetime") is violated. Self-heals only once the new lifetime's
  version counter exceeds the old one.
- **Suggested fix:** give each URI an epoch/generation: `drop()` increments it (or
  simply records that the URI is closed); `_analysis_for` captures the epoch before
  submitting and `_store` discards results whose epoch is stale instead of
  `setdefault`-resurrecting. Equivalently: `_store` may only create state when the
  workspace currently tracks `uri` (`uri in self.workspace.text_documents`), and the
  version-ordering guard must reset (not persist) across `drop()`.

No other findings. Everything else traced clean, including: `_line_segments` empty-
segment skipping at line terminators, `encode_semantic_tokens` prev-line/char updates,
`folding_ranges` dedup-keeps-outermost (matches its documented contract),
`_spans_containing` single-containing-child break (children are sorted and
non-overlapping), `position_to_offset` surrogate-pair clamp, `parse_text` unknown-rule
path leaving `error_pos=None`, `_publish`'s `offset+1` end clamped at EOF, the
memoized `_fmt_failed`/`_fmt_built` flags (only ever touched on the single worker
thread), and the verify-reparse guard's control flow in `_format_blocking`.
