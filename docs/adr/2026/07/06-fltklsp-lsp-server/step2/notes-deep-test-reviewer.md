# Deep test review — round 2 (`fltk-lsp` server, M2)

Base `9719bab7` → HEAD `d9ab841`. All 188 tests in `fltk/lsp/` pass locally
(`uv run --group dev pytest fltk/lsp/ -q`).

## test-1: `test_early_success_without_full_consumption_has_offset` doesn't exercise the branch it claims to

File: `fltk/lsp/test_plumbing_error_pos.py:33-39`.

The test uses `top := x:"a"? ;` against `"bb"`. The design (`design.md` §4.4) describes
`plumbing.py`'s new `error_pos` logic as having two failure sources: `tracker_pos` (the
`ErrorTracker`'s recorded furthest terminal failure) when `>= 0`, else `result.pos` (the
`elif result:` branch, meant for "a rule succeeded early without consuming all input and
no alternative failed beyond it").

I instrumented the actual parse for this test's input: the optional `"a"?` still attempts
to match `"a"` against `"b"`, that attempt fails, and the `ErrorTracker` records it
(`longest_parse_len == 0`). So `plumbing.parse_text`'s `if tracker_pos >= 0:` branch fires
— the *same* branch `test_mid_input_terminal_failure_has_offset` already covers — not the
`elif result: error_pos = result.pos` branch the test's name and docstring claim to
target. I confirmed the intended branch is reachable with a different grammar
(`top := x:"a" ;` against `"ab"`): the literal succeeds outright, nothing is ever recorded
by the tracker (`longest_parse_len == -1`), and `parse_text` falls through to
`error_pos = result.pos` (`error_pos == 1`, `Expected:` list empty in the message) — a
materially different code path from what the shipped test exercises.

Consequence: the `elif result: error_pos = result.pos` branch in `plumbing.py:200-201` has
**zero** test coverage anywhere in the suite. A regression there (e.g. reversing the
`elif`/`else` order, or a typo turning `result.pos` into `0`) would not be caught, and the
test suite would keep reporting this scenario as "tested" when it isn't.

Fix: change the test's grammar to one where the rule can succeed without any prior tracked
failure (e.g. `top := x:"a" ;` parsed against `"ab"`, as verified above), and assert
`error_pos == 1` (not just "not None") to pin the actual branch and value.

## test-2: `semanticTokens/range` has no test at any level

`server.py:380-392` registers `TEXT_DOCUMENT_SEMANTIC_TOKENS_RANGE` with nontrivial logic
unique to this handler: converting the requested `Range` to codepoint offsets via
`position_to_offset`, filtering `good.tokens` by overlap (`token.start < end and token.end
> start`), and re-encoding the subset with `features.encode_semantic_tokens`. Neither
`test_features.py` nor `test_server.py` calls this handler or the overlap-filter logic in
isolation — grep confirms no occurrence of `semantic_tokens_range` in any test file.

Consequence: a regression in the overlap predicate (off-by-one at range boundaries), in
line/character→offset conversion for the range endpoints, or in how the subset is
delta-encoded (e.g. accidentally re-basing deltas to the range start instead of document
start) would go undetected. This is a protocol-facing feature the design explicitly lists
among the server's deliverables (§3, §4.7) with no corresponding test in the §6 test plan
gap either — it's simply missing.

Fix: add at least one `test_server.py` case that opens a multi-line document, requests
`semanticTokens/range` for a sub-range, and asserts the returned `data` matches the tokens
actually inside that range (e.g. by comparing against a hand-computed subset of the full
`semanticTokens/full` result for the same document).

## test-3: Debounce coalescing and single-flight dedup are unexercised

`server.py`'s `schedule_debounced` (`server.py:242-247`) cancels any pending debounce task
before scheduling a new one, and `_analysis_for` (`server.py:165-183`) reuses an in-flight
analysis future when a request and the debounce timer race on the same version
(`server.py`'s docstring: "Per-URI single-flight bookkeeping prevents duplicate work when
a request and the debounce timer race"). No test in `test_server.py` issues two rapid
`didChange` notifications within the `_DEBOUNCE_SECONDS` window to verify the first is
cancelled and only one analysis/publish happens, and none drives a pull request
(`semanticTokens/full`, etc.) concurrently with a pending debounced analysis to verify the
in-flight future is reused rather than a second parse being submitted.

Consequence: a regression that drops the `existing.cancel()` call (double-publishing stale
diagnostics), or one that breaks the `inflight[0] == version` reuse check (silently
doubling analysis work, defeating the single-worker-executor design premise), would pass
the whole suite undetected.

Fix: at minimum, a test that calls `_change` twice back-to-back with different text before
the first publish would arrive (`asyncio.sleep` less than `_DEBOUNCE_SECONDS` between them)
and asserts only one diagnostics publish reflects the *second* text, not an intermediate
state from the first. A second test could call `_analysis_for` directly (in-process, no
subprocess) with two overlapping calls for the same version and assert the underlying
`_analyze_blocking` executor submission happened once (e.g. via a counting wrapper).

## test-4: `_store`'s out-of-order-version guard is untested

`server.py:150-151`: `_store` drops an incoming analysis result if its `version` is older
than the state's `analyzed_version`, and `analyze_and_publish` (`server.py:224-229`)
separately discards publishing if the document has moved on to a newer version by the time
analysis completes. Both are exactly the invariants that make the async
debounce/single-worker scheduling design safe against out-of-order completions, and
neither is exercised by any test — there is no scenario in `test_server.py` where an older
analysis result arrives after state has already advanced (e.g. by directly calling
`_store` twice out of order, or `analyze_and_publish` with a stale `version` while
`workspace.get_text_document(uri).version` has already advanced).

Consequence: a regression that removes or inverts this guard (e.g. always overwriting
`state.analysis` regardless of version, or always publishing regardless of version match)
would let stale diagnostics/tokens clobber fresher ones under real editor load, and no
test would catch it — this is precisely the "classic stale-token corruption bug" class the
design (§4.7) says `_GoodAnalysis` and the version checks are built to rule out "by
construction," but only the `_GoodAnalysis`-snapshot half of that claim is actually pinned
by a test (`test_breaking_edit_reports_error_and_serves_stale_tokens`); the version-
ordering half is not.

Fix: a focused unit test on `FltkLanguageServer._store` (constructed via `create_server`
or directly) that calls it with `version=2` then `version=1` and asserts the state still
reflects `version=2`'s analysis; similarly a test that calls `analyze_and_publish` with a
`version` that no longer matches `workspace.get_text_document(uri).version` and asserts no
publish happened (a spy/monkeypatch on `text_document_publish_diagnostics`).

## test-5: The `--fmt`-absent default-formatting-config path (§2.6) is never run

Design §2.6 calls out, as a deliberate and explicitly "challengeable" decision (repeated in
§8's Open questions), that formatting is registered *always*, using `FormatterConfig()`
defaults when `--fmt` is omitted. Every server started in `test_server.py` uses the fixed
`_SERVER_COMMAND` (`test_server.py:31-45`), which always passes `--fmt`. No test starts the
server (or calls `create_server`) without a `formatter_config`/`--fmt` and confirms
formatting still registers and produces sensible default-config output.

Consequence: a regression that makes the no-`--fmt` path crash, silently disable
formatting, or use a config other than `FormatterConfig()` defaults would be invisible —
despite this being one of the three decisions the design explicitly flags for reviewer
scrutiny as not yet battle-tested by construction.

Fix: add an e2e (or in-process `create_server`) test that opens a document against a
server built with `formatter_config=None`, requests `textDocument/formatting`, and asserts
it returns a sensible edit (not `None`, not a crash).

## test-6: Selection-range ancestor chain only ever tested to 2 collapsed levels

`test_features.py`'s `_greeting_tree()` (`test_features.py:179-185`) has `TOP` and
`GREETING` sharing the same `[0,13)` span, so `test_selection_innermost_span_is_head_and_
widens_strictly` collapses them into a single ancestor step (span → one collapsed parent →
`None`). The e2e `test_selection_widens_outward` (`test_server.py:183-197`) only asserts
`head.parent is not None`, not the shape of any further ancestor. No test — hand-built or
real-engine — exercises `_spans_containing`'s recursive case with three or more *distinct*
enclosing spans (e.g. `document → item → greeting → name` in the real fixture grammar,
where `document`, `item`, `greeting`, and `name` all have different `[start, end)` extents),
so the recursive branch in `features.py:182-184` (`elif child.span.start <= offset <
child.span.end: chain.extend(_spans_containing(child, offset)); break`) beyond one level of
recursion is only reached, never asserted against.

Consequence: a bug in the recursive multi-level case (e.g. losing an intermediate
ancestor, or mis-ordering the chain) would only manifest with 3+ genuinely distinct nested
spans — exactly the case no test builds — and would not be caught.

Fix: extend `_greeting_tree` (or add a new hand-built tree) with a genuinely 3-level chain
of distinct spans and assert the full ordered list of ranges from innermost to
document-root, not just that a parent exists.

## test-7: Unparse/render-time broad-exception catch in `_format_blocking` is untested

`server.py:309-314` wraps `unparse_cst`/`render_doc` in a broad `except Exception`,
motivated (§4.8) by the same "silent-`None` unparser-bug family" as the build-failure
catch — but only the *build*-failure catch (`generate_unparser` raising) is exercised, via
`test_format_build_failure_is_memoized`'s monkeypatch of `plumbing.generate_unparser`
(`test_server.py:255-276`). No test monkeypatches `plumbing.unparse_cst` or
`plumbing.render_doc` to raise a non-`ValueError` exception (e.g. `KeyError`/
`AttributeError`/`TypeError`, the exact families the design's rationale calls out) and
confirms the handler degrades to `None` + a logged message rather than propagating.

Consequence: a regression that narrows this catch back to `ValueError` (undoing the fix
this design deliberately calls out as necessary, referencing commit `c0534e3`'s silent-None
diagnosis) would not be caught by any test — the one existing failure test only reaches
the *build*-step catch, not this one.

Fix: a test analogous to `test_format_build_failure_is_memoized` that monkeypatches
`plumbing.unparse_cst` (or `render_doc`) to raise e.g. `KeyError` and asserts
`_format_blocking` returns `(None, logs)` with an error-level log, not a propagated
exception.
