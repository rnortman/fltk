# Deep review — security — step3 (.fltklsp M4)

Reviewed: `git diff 1ad3141..8966d8e` (HEAD 8966d8ee42840c5f7fbf26090b14ef20eafc28e0),
against the frozen design `docs/adr/2026/07/06-fltklsp-lsp-server/step3/design.md`.

Threat model applied: the LSP client (editor) is semi-trusted; document text is
untrusted input; the one write-path is `textDocument/rename`, whose output the client
applies to the user's buffer — the asset at risk is the integrity of the user's file.

## security-1 — rename mixes document versions across its awaits; verify-reparse runs on live text and no post-await version re-check exists

- **File:line**: `fltk/lsp/server.py:374-414` (`rename_document`), esp. `:406`
  (`renamed = _apply_edits(document.source, occurrences, new_name)`).
- **Issue**: `version` and the analysis snapshot are captured at handler entry, but
  `document.source` is re-read *after* `await self._ensure_analyzed(...)` (and the
  verify result is used after a second await, `run_in_executor`). pygls updates the
  workspace `TextDocument` in place when a `didChange` is dispatched, and the loop can
  dispatch a `didChange` while this handler is suspended on either await (the design
  §2.6 itself concedes this interleave). The stale-tree guard
  (`state.analyzed_version != version`) only compares against the entry-time version, so
  it still passes after such an interleave. Net effect in the raced case:
  `_apply_edits` splices version-N occurrence offsets into version-N+1 text, the
  verify-reparse guard (the mechanism §2.6 relies on to never return corrupting edits)
  evaluates garbage — it can spuriously pass — and version-N edits are returned.
- **Trust boundary / data flow**: client-driven `didChange` (untrusted timing/content)
  → pygls workspace text mutated on the loop → re-read by `document.source` mid-handler
  → verify guard and returned `WorkspaceEdit` computed from mixed versions.
- **Consequence**: for any client that does not advertise
  `workspace.workspaceEdit.documentChanges` (the plain `changes` fallback carries no
  version), the client applies version-N offsets to version-N+1 buffer text: silent
  corruption of the user's document, triggered by an ordinary keystroke racing a rename
  (or by anything else editing the buffer — collaboration plugins, format-on-type).
  Capable clients are protected at apply time by the versioned `documentChanges`
  payload, but even for them the verify guard is unreliable in exactly the raced case.
  The design accepts an *unclosable wire-level* residual race for capability-less
  clients; the implementation leaves a much larger, closable window open server-side.
- **Suggested fix**: capture `text = document.source` once at entry next to `version`
  and use that snapshot for `_apply_edits` (deterministic verify, always against the
  analyzed version); after each await, re-fetch the document and raise
  `JsonRpcException` if `document.version != version`. That shrinks the corruption
  window for capability-less clients to the response wire only — the minimum LSP allows
  — and makes the verify guard trustworthy for everyone.

## security-2 — `version is None` (never-opened, disk-backed URIs) silently disables every rename safety mechanism

- **File:line**: `fltk/lsp/server.py:382-394` (guard), `:406` (second disk read),
  `fltk/lsp/features.py:440-469` (`rename_edits` with `version=None`).
- **Issue**: `workspace.get_text_document(uri)` for a URI the client never opened
  creates a disk-backed `TextDocument`: `version` is `None` and **every** access to
  `.source` re-reads the file from disk (verified against installed pygls:
  `TextDocument.source` does `pathlib.Path(self.path).read_text(...)` when `_source is
  None`). Consequences chain: (a) the current-version guard degenerates —
  `state.analyzed_version != version` is `None != None` → `False`, so the "rename
  refuses to run against a stale tree" policy (§2.6) never fires on this path; (b) the
  two `.source` reads at `:384` and `:406` are two independent disk reads, so
  occurrences and the verify text can come from two different on-disk states with no
  detection (same mixing as security-1, but with no version to check); (c) the
  "versioned" `documentChanges` payload carries
  `OptionalVersionedTextDocumentIdentifier(version=None)`, which per LSP means "do not
  version-check" — so the design's one remaining client-side protection is also off.
- **Trust boundary / data flow**: client-supplied URI (rename requests are not limited
  to opened documents) → disk file, mutable by anything on the machine (build steps,
  `git checkout`, watchers) → occurrence offsets and verify text from potentially
  different file states → unversioned edit returned to the client.
- **Consequence**: rename invoked on a file the server never saw opened (editors can and
  do send requests for such URIs, e.g. cross-file navigation flows) while that file is
  concurrently rewritten on disk yields edits computed from one file state, verified
  against another, applied by the client to a third — corruption of a file the user may
  not even have on screen, with every §2.6 safeguard inert. Low likelihood, but it is
  precisely the "stale offsets applied to current text is a corruption bug" scenario
  §2.6 declares unacceptable.
- **Suggested fix**: in `rename_document`, refuse (raise `JsonRpcException`) when
  `document.version is None` / the URI is not in the workspace's managed documents —
  rename should only operate on documents the client has opened and is syncing. (The
  read-only features serving disk-backed URIs is pre-existing behavior and harmless;
  the write path is what needs the restriction.)

## Checked and not flagged

- **`new_name` content injection** (multi-token payloads, comment openers, newlines —
  parses but re-means): explicitly documented and accepted as residual risk in design
  §2.6; verify-reparse rejects the parse-breaking subset. Not re-litigated.
- **Hostile positions/offsets from the client**: `LineIndex.position_to_offset` clamps
  all out-of-range input (`positions.py:91-115`); no exception/DoS path.
- **Recursion on hostile documents**: `symbols.extract`'s recursive `_walk` /
  `_sort_scope_symbols` / `_gather_symbols` run inside `engine.analyze`'s existing
  `RecursionError` catch (`engine.py:152-167`); the rename verify path goes through
  `engine.analyze` and inherits it.
- **CPU exhaustion via quadratic resolution** (`symbols._resolve` is O(refs ×
  scope-chain × symbols)): acknowledged in design §5 and covered by the existing
  `TODO(lsp-classify-hotpath)` / `TODO(lsp-analysis-watchdog)` worker-starvation
  posture; single worker thread, protocol loop unaffected.
- **Arbitrary file read via client URI** (`get_text_document` reads from disk for
  unopened URIs): pre-existing pattern shared by all round-1/2 handlers, standard LSP
  server behavior with a same-user client; not new in this diff.
- **Secrets**: none in the diff (test data is toy grammars/specs).
- **Error messages / logging**: new error strings are static; no untrusted content newly
  logged or serialized.
