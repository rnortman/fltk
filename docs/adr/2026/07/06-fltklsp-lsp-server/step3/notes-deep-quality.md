# Deep review — quality (step3 M4 implementation)

Reviewed: `git diff 1ad3141..8966d8e` (HEAD 8966d8ee42840c5f7fbf26090b14ef20eafc28e0), against
`step3/design.md` (frozen). Files read in full: `symbols.py`, `features.py`, `lsp_config.py`,
`server.py`, `engine.py`, `classify.py`.

No design-doc-referencing or changelog-style comments found in the added non-test code; the
round-3 activation docstring updates (e.g. `resolve_config`) describe current behavior only.

---

## quality-1: Six new feature handlers copy the same request preamble (now 9 copies total)

- `fltk/lsp/server.py:593-656` (`document_symbol`, `definition`, `references`,
  `document_highlight`, `prepare_rename` in `create_server`), alongside the pre-existing
  copies in `semantic_tokens_full`/`semantic_tokens_range`/`folding_range`/`selection_range`.

Every pull handler repeats the identical block: `uri` → `get_text_document` →
`_ensure_analyzed(uri, document.version, document.source)` → `_serveable(state)` → `None`
check → `_encoding()`; four of the new handlers additionally repeat the identical
`position_to_offset(params.position...)` line. The diff tripled the number of copies of this
pattern (3 → 9).

**Consequence**: any change to the serving policy (stale-serving, encoding lookup, offset
clamping) must now be applied at nine call sites and can silently drift at one of them; M5
(cross-file features) will add more handlers that copy the same block again.

**Fix**: extract a helper on `FltkLanguageServer`, e.g.
`async def _serveable_for(self, uri: str) -> tuple[_GoodAnalysis, PositionEncoding] | None`
(document fetch + ensure-analyzed + `_serveable` + encoding), plus a one-liner
`_offset(good, position, enc)` for the position-bearing handlers. Each handler collapses to
its one distinguishing line.

## quality-2: Per-child "surface decode" block duplicated between the symbol walk and the paint walk

- `fltk/lsp/symbols.py:205-215` (`_walk`) vs `fltk/lsp/classify.py:252-262`
  (`_explicit_intervals`).

Both walks contain a byte-for-byte-equivalent block deriving `is_span`, `cstart`/`cend`,
`child_text`, `child_rule_name`, and `label_name` for each child before calling the shared
`lsp_config.match_applies`. The design deliberately moved `match_applies` to `lsp_config` so
"neither should reach into the other's privates" — but the *inputs* to that predicate are
still computed by two private near-duplicates.

**Consequence**: `match_applies` only means the same thing in both modules if both decode the
child identically; the two walks already diverge on an adjacent axis (`_walk` skips trivia
subtrees, `_explicit_intervals` does not), so a future tweak to one decode block (e.g. label
normalization, Rust-backend span access) can silently make paint and symbol extraction
disagree about which child a matcher hits. The planned M3/M5 walks will copy the block a
third time. This also compounds the `TODO(lsp-classify-hotpath)` unification debt.

**Fix**: a shared helper next to `match_applies` (e.g.
`child_surface(label, child, text, tables) -> tuple[int, int, str | None, str | None, str | None, bool]`
or a tiny frozen dataclass), consumed by both walks. The trivia-descent difference stays a
per-walk decision; only the decode unifies.

## quality-3: `resolve_config` expands each `def` anchor twice and builds the same `Tier` in two places

- `fltk/lsp/lsp_config.py:686-692`.

The def-statement branch calls `_resolve_local_anchor` (which internally iterates
`_local_anchor_matches` and builds `Tier(SOURCE_RANK_DEF, anchor_rank, BLOCK_RANK_RULE,
def_stmt.index)`) for the declaration paint, then immediately re-iterates
`_local_anchor_matches` and rebuilds the *identical* `Tier` inline for the `DefMatcher`.

**Consequence**: the paint tier and the semantic tier for one `def` statement are supposed to
be the same precedence key (the design leans on this: extraction "matches the painter's
precedence"). Two independent constructions can drift under a future precedence change,
making declaration-site paint and symbol extraction pick different winners for the same child
— a bug class that is very hard to notice from either feature alone.

**Fix**: one loop over `_local_anchor_matches(def_stmt.anchor, rule_index)` building the tier
once and appending both the `ChildMatcher` (when the kind's first segment is in the legend)
and the `DefMatcher` from it.

## quality-4: Rename failures raise bare `JsonRpcException` → wire code `-32603` (InternalError)

- `fltk/lsp/server.py:393-394` and `server.py:410-411`.

`JsonRpcException(msg)` leaves `code` defaulting to the class `CODE = -32603`
(JSON-RPC InternalError). Both raises are deliberate domain refusals ("document has parse
errors", "new name would leave the document unparseable"), not server faults; LSP 3.17
defines `LSPErrorCodes.RequestFailed` (`-32803`) for exactly this case.

**Consequence**: clients and client-side telemetry treat `-32603` as a server crash — some
editors log it as an extension error or prompt to report a bug rather than showing the
message as an expected refusal. During incident triage, real internal errors become
indistinguishable from routine rename refusals in client logs.

**Fix**: `raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)` (or a small
module-level `class RenameRefused(JsonRpcException): CODE = lsp.LSPErrorCodes.RequestFailed`).

## quality-5: `_symbol` is underscore-named but used

- `fltk/lsp/server.py:400-402` (`rename_document`): `_symbol, occurrences = found` followed by
  `if new_name == _symbol.name:`.

**Consequence**: the leading underscore signals "intentionally unused" to every reader and to
lint conventions; the next editor either "cleans it up" to `_` (breaking the no-op check) or
has to stop and re-verify the convention. Small, but it is exactly the kind of misleading
name that costs review time on every future pass through this function.

**Fix**: rename to `symbol`.

## quality-6: `prepare_rename` re-derives the lookup and needs an assert because `symbol_target` discards the span

- `fltk/lsp/features.py:317-326`.

`prepare_rename` calls `symbol_target(table, offset)` (which internally does
`symbol_at` then `reference_at`), then calls `table.symbol_at` and `table.reference_at`
*again* to recover which span is under the cursor, and needs an
`assert reference is not None` to paper over the information `symbol_target` threw away.
Up to five containment scans per request, plus an assert guarding a structurally-guaranteed
case.

**Consequence**: the assert encodes a cross-function invariant ("symbol_target resolved ⇒ one
of the two lookups hits") that any future change to `symbol_target` (e.g. M5 cross-file
targets, where a ref resolves to a symbol in another document) can silently violate, turning
it into a crash path. The recompute pattern will be copied by the next feature that needs the
addressed span (completion, hover).

**Fix**: add the span-carrying variant as the primitive, e.g.
`target_span(table, offset) -> tuple[Symbol, tuple[int, int]] | None` (symbol + the exact
span under the cursor), implement `symbol_target` as its projection, and have
`prepare_rename` use it directly — no second lookup, no assert.

## quality-7: Avoidable `type: ignore` in `rename_edits`

- `fltk/lsp/features.py:358-366`.

`edits` is inferred `list[lsp.TextEdit]`, and `TextDocumentEdit.edits` wants
`list[TextEdit | AnnotatedTextEdit]`; the invariance mismatch is silenced with
`# type: ignore[arg-type]`.

**Consequence**: the ignore suppresses *all* future arg-type errors at that call site (e.g. a
refactor passing the wrong list entirely), and normalizes ignore-comments where a one-token
annotation suffices.

**Fix**: annotate the local as
`edits: list[lsp.TextEdit | lsp.AnnotatedTextEdit] = [...]` and drop the ignore.
