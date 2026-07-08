# Deep review — efficiency (round 5)

Base `1e920dc` .. HEAD `fe10193`. Scope: resolver plugin API (`resolver.py`), project layer
(`project.py`), server wiring (`server.py`, `features.py`), gear demo (`examples/gear/`).

Framing note: the per-keystroke hot path (analysis → semantic tokens) is deliberately kept
resolver-free (§4.5), and I confirmed the diff adds no work there — the no-resolver paths are
untouched and `_GoodAnalysis.text` only re-references the string `LineIndex._text` already
retained, so no new per-document memory. The findings below are all on the
definition/references/rename (user-action-rate) path.

## efficiency-1 — ProjectHost (and its parse/extract cache) is rebuilt per request; every find-references re-parses the whole workspace

`server.py:475-484` (`_project`) constructs a **new** `ProjectHost` on every
definition/references/rename call (called from each `_*_blocking`, `server.py:503,536,569`),
and there is no server-level persistent host (grep confirms: no `self._project_host`). The
host's analysis cache (`project.py:77` `self._cache`) therefore lives only for the duration of
one request and is discarded afterward.

`ProjectNavigator.references` scans **every** `host.workspace_files()` document
(`project.py:210,235`), calling `host.document()` → `_engine.analyze()` (parse + symbol
extract) on each. Because the host is thrown away between requests, two consecutive
find-references (or a find-references followed by a go-to-def) re-parse and re-extract every
workspace file from scratch — the cache never gets a warm hit across requests.

Note the mismatch with the machinery that was built: `_CachedDoc.version_key`
(`project.py:41-51`) does `(mtime_ns, size)` disk validation and LSP-version validation
"on every access" precisely so an unchanged file can be reused without re-analysis
(`project.py:112-137,159-162`). Under a per-request host that reuse can only ever happen
*within* one request (e.g. an import target that is also a scanned workspace file); the
cross-request reuse the version keying is designed for never occurs. In particular the
`path.stat()` on every `_source` access (`project.py:155`) becomes pure per-request overhead —
it re-stats a file the same request just read and cached, and the validation it enables is
discarded when the host is.

**Consequence** — cost shows up on repeated cross-file navigation: each find-references on an
N-file workspace pays N parse+extract passes *every time*, even when nothing changed since the
last request. Go-to-def is milder (it only `document()`s the single import target). At demo
scale it's invisible; on a clockwork-scale project repeated find-references / go-to-def get
linearly slower than the already-built cache allows. §5 defers a *persistent index +
didChangeWatchedFiles*, but that is a different, larger thing — this is about not discarding the
cache the code already maintains and already validates for safe reuse.

**Fix direction** — hold one `ProjectHost` on the server across requests and refresh only the
volatile inputs per request: re-point its `open_docs` snapshot and `root_path` on each call
(both are cheap loop-thread copies), letting `version_key` validation reuse unchanged disk/open
analyses. The single-worker invariant (§4.2) still holds — only the worker touches the host — so
no locking is added; only the open-docs snapshot needs swapping in on the loop thread before
each submit. If per-request hosts are kept deliberately, the design should say so and drop the
`(mtime_ns, size)` re-validation as unreachable-across-requests, because as written the
invalidation cost is paid for a benefit that never lands.

## efficiency-2 — rename guard double-resolves the requesting doc and materializes the full sorted occurrence set to answer a boolean

`_rename_guard_blocking` (`server.py:559-580`) calls `self._resolver.resolve(doc, host)`
directly, then calls `navigator.references(doc, offset, include_declaration=True)`.
`references` builds its own fresh `resolutions={}` and re-computes `resolve(doc)` for the
requesting document inside `_target_for`/`_canonical` (`project.py:203-204,249-251,260`) — so the
requesting document is resolved twice per rename. It then builds and **sorts** the entire
deduplicated cross-file occurrence list (`project.py:225`) only for the guard to iterate it and
return on the first foreign URI (`server.py:576-579`).

**Consequence** — per rename request: one redundant tree-walk + import-map rebuild of the
requesting document (import-target `document()` calls hit cache, so the extra cost is the walk
itself), plus a full set-build+sort of all occurrences discarded after a single `any()`-style
check. Both are small relative to the workspace scan that dominates a rename guard, so this is a
minor cleanup, not a scaling problem — it bites on every rename but the absolute cost is low.
Note the common successful ("ok") rename must scan all files anyway to prove *no* cross-file
reference exists, so a short-circuit only helps the refusal case.

**Fix direction** — give the navigator a boolean `has_cross_file_reference(doc, offset)` (or let
`references` accept a pre-computed resolution / an "any foreign, stop early" mode) so the guard
reuses its already-computed `resolution` for the requesting doc and can bail on the first
cross-file hit without materializing/sorting the full list.

## efficiency-3 (minor) — gear resolver rebuilds the target export map per `use` statement

`gear_resolver.py:81` builds `exports = {s.name: s for s in target_doc.symbols.root.symbols}`
inside the per-`use_stmt` loop. Two `use` statements importing from the same module
(`use lib::shapes::{Circle}; use lib::shapes::{Square};`) rebuild the same export dict twice
(the `host.document()` call itself is cached, so only the dict comprehension repeats).

**Consequence** — negligible in practice (gear groups imports in one brace list, so same-module
repeats are rare) and only re-derives a small dict. Worth noting only because this file is the
*documented reference implementation* downstream authors copy (§4.8), so the pattern propagates.

**Fix direction** — memoize `exports` per `target_uri` within a single `resolve()` call
(`dict[str, dict[str, Symbol]]` keyed by target URI).

---

No concurrency findings: serializing all resolver work on the single analysis worker is a
deliberate, documented invariant (§4.2, no locking on `ProjectHost`); parallelizing the
per-file parse during a references scan would violate it. The O(files) references scan itself is
a documented, accepted limitation (§4.4, §5) and is not re-flagged here — efficiency-1 is about
*repeating* that scan across requests when the cache could avoid it, which the design does not
claim to accept.
