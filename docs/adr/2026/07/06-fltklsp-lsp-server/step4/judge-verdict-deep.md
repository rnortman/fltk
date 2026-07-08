# Judge verdict — deep review

Phase: deep. Base `dcac826`..HEAD `80418ae` (reviewers reviewed `1060867`; fix commit `80418ae`). Round 1.
Notes: 7 reviewer files (correctness, security, reuse, efficiency: "No findings"); 9 findings
across error-handling (2), quality (4), test (3). Dispositions:
`docs/adr/2026/07/06-fltklsp-lsp-server/step4/dispositions-deep.md`.
Duplicate pairs acknowledged by responder: errhandling-1≈quality-3, errhandling-2≈quality-4.
Full LSP test suite run locally: 299 passed.

## Added TODOs walk

No TODOs were added in this round. `git diff dcac826..80418ae` grep for `TODO(` shows only the
in-scope removal of `TODO(lsp-start-rule-dedup)` (comment at old `server.py:534` and the matching
`TODO.md` entry, per design §3.1 item 6 — both sides removed, convention satisfied) plus
implementation-log mentions. No TODO-dispositioned findings exist.

## Other findings walk

### errhandling-1 / quality-3 — Fixed (one shared fix)
Claim: the inner `except RecursionError` around prefix `symbols.extract`/`classify.classify`
(`engine.py`) swallowed the recursion event silently; consequence: a classifier stack overflow on a
well-formed prefix is indistinguishable in logs from an ordinary hard failure, no on-call signal.
Evidence: `fltk/lsp/engine.py:27` adds `_LOGGER = logging.getLogger(__name__)`;
`engine.py:186-190` emits `_LOGGER.warning(...)` in the inner handler, recording the abandoned
prefix length (`parsed.prefix_pos`) — exactly what quality-3 asked for ("note the prefix length
that was abandoned"). The degrade-to-parse-error return is unchanged, which both findings
explicitly permitted (errhandling-1: "does not require changing the returned outcome").
Assessment: fix addresses both findings at the named lines. Accept.

### errhandling-2 / quality-4 — Fixed (one shared fix)
Claim: `analysis.prefix_end or 0` in `_analyze_blocking` silently converts an invariant violation
into boundary `(0,0)`; consequence: overlapping fresh+stale segments, possible negative
`deltaStartChar`, corrupted highlighting with no crash or log.
Evidence: `fltk/lsp/server.py:218-222` — `or 0` replaced with
`assert analysis.prefix_end is not None` plus a comment citing the `DocumentAnalysis` invariant
and stating why defaulting is rejected. The invariant itself is documented in the
`DocumentAnalysis` docstring table (`engine.py:59-68`), so the assert is narrowing a documented
contract, not inventing one.
Assessment: exactly the reviewers' requested fix. Accept.

### quality-1 — Fixed
Claim: `_ServedTokens.version` was write-only dead state; consequence: false belief that
serve-time version consistency is checked.
Evidence: `server.py:110-122` — `version` field removed from `_ServedTokens`; docstring now states
"Staleness ordering is enforced by `_store`'s `analyzed_version` guard before this record is
written, so it carries no version of its own." Grep confirms no remaining read/write of
`served_tokens.version` anywhere in `server.py`. The ordering guard at `server.py:247` runs before
the `served_tokens` write at `server.py:253`, so dropping the field loses nothing.
Assessment: correct and complete. Accept.

### quality-2 — Fixed
Claim: `_ServedPair` tuple and `_ServedTokens` were two shapes for one value, unpacked/rewrapped
across the worker/`_store` seam; consequence: independent drift, positional-tuple hazards.
Evidence: `_ServedPair` alias deleted; `_AnalysisResult` at `server.py:44` now references
`"_ServedTokens | None"`; `_analyze_blocking` constructs `_ServedTokens(segments=..., encoded=...)`
directly (`server.py:225`); `_store` stores it without unpack (`server.py:252-253`) and reads
`served.segments` for `_GoodAnalysis` (`server.py:262`). This is the reviewer's own proposed fix
verbatim (return `_ServedTokens | None` directly, delete `_ServedPair`).
Assessment: accept.

### test-1 — Fixed
Claim: no test raised `RecursionError` from `classify.classify` on a *complete* parse (design
test-plan item 9); consequence: narrowing the outer `try` would let a success-path
`RecursionError` escape `analyze()` with no test catching it.
Evidence: `test_analyze_classification_recursion_error_on_complete_parse_degrades`
(`fltk/lsp/test_engine_analyze.py:151-168`) monkeypatches `engine_module.classify.classify` to
raise on `"let x ;\nuse x ;\n"` and asserts the failed outcome with `"nesting depth"` in the
message and `offset is None`. The assertion is self-verifying for the path taken: had the text
parsed only partially, the *inner* handler would surface the parse error (not the nesting-depth
message) and the assertion would fail; the test passing proves the outer `try` covers the
classify call on the complete path. Mirrors the extraction sibling as the reviewer specified.
Assessment: pins exactly the invariant the finding named. Accept.

### test-2 — Fixed
Claim: folding and selection during partial serving were untested (design test-plan item 18)
despite `_GoodAnalysis`'s shape changing this round; consequence: a regression blanking
folding/selection on partial states would go uncaught.
Evidence: `test_folding_served_from_last_good_during_partial` and
`test_selection_served_from_last_good_during_partial` (`fltk/lsp/test_server.py:778-808`) each
open a good document, `_change` to a broken one, drive `textDocument/foldingRange` /
`textDocument/selectionRange`, and assert substantive content (the comment fold at lines 0-1; a
selection chain widened around `alice` with a non-None parent) rather than mere non-emptiness.
Minor observation, not disputed: the asserted fold/selection targets sit inside the fresh prefix
as well as the last-good tree, so the tests pin "not blanked/degraded" rather than
distinguishing last-good-serving from hypothetical prefix-serving. That is the failure mode the
finding actually named ("confirm they still return the last-good tree's folds/selection chains
rather than an empty/degraded result"), and both handlers route through the same
`_serveable`/`last_good` mechanism the documentSymbol test already exercises, so the residual gap
is negligible.
Assessment: satisfies the finding. Accept.

### test-3 — Fixed
Claim: no single `semanticTokens/range` request straddled the merge boundary (design test-plan
item 17's literal "spanning the boundary" case); consequence: compensating off-by-ones in the two
bisects could cancel out across disjoint queries.
Evidence: `test_semantic_tokens_range_on_partial_state` extended
(`fltk/lsp/test_server.py:758-762`) with a single range from line 0 char 0 (fresh prefix) to
line 1 char 10 (stale tail), asserting the decoded result equals `prefix + tail` from the two
existing disjoint queries — the exact assertion the reviewer proposed.
Assessment: accept.

## Disputed items

None.

## Approved

9 findings: 9 Fixed verified (two duplicate pairs sharing one fix each, correctly
cross-referenced). No Won't-Do, no TODOs.

---

## Verdict: APPROVED

Every disposition verified against the code at `80418ae`; full LSP suite (299 tests) passes
locally.
