# Round-2 deep-review dispositions (M2 fltk-lsp)

Base 9719bab7 · reviewed HEAD d9ab841. Fixes committed on top. `make check` passes.

Two findings were raised by multiple reviewers and are reconciled into single dispositions:
- The pygls private-attr encoding monkeypatch: **errhandling-2 + security-1 + quality-1** → one fix.
- The fire-and-forget debounce task swallowing exceptions: **errhandling-3 + quality-2** → one fix.
- The `drop()`/`_store` resurrection bug: **correctness-2 + quality-4** → one fix (epoch counter).

---

## errhandling-1
- Disposition: Fixed
- Action: `fltk/lsp/server.py` `_format_blocking` — the step-1 `parse_text` on the input is now
  wrapped in `except Exception` (log + `return None, logs`), symmetric with the unparse/render and
  verify-reparse guards. A deeply nested valid document raising `RecursionError` from the generated
  parser now degrades to no-edits + a logged breadcrumb rather than a raw LSP request error.
- Severity assessment: real. Formatting a deeply-nested document produced an opaque editor error
  popup and violated §4.8's "never a raw LSP request error" guarantee.

## errhandling-2  (reconciled with security-1, quality-1)
- Disposition: Fixed
- Action: `_constrain_pygls_encodings` (`server.py`) now raises `RuntimeError` at import if
  `pygls.capabilities._SUPPORTED_ENCODINGS` is absent, so a pygls upgrade that renames/removes the
  private makes fltk-lsp fail loudly at startup instead of silently resuming utf-8 advertisement.
  `_encoding` additionally logs a warning if it ever reads an advertised value outside
  `{utf-16, utf-32}` instead of silently coercing. Together these convert the worst failure mode
  (silent coordinate corruption / file-truncating format edits on non-ASCII text) into a visible
  startup crash or log line.
- Severity assessment: high under the drifted-dependency condition (silent wrong ranges, including
  file corruption on format). The guard closes the drift at both ends.

## errhandling-3  (reconciled with quality-2)
- Disposition: Fixed
- Action: `_debounced_analyze` (`server.py`) body after the debounce sleep is wrapped in
  `except Exception` that reports via `window/logMessage`. A non-`RecursionError` exception from the
  generated parser/classifier no longer vanishes as asyncio GC-time stderr noise on the orphaned
  task; it lands in the client's server log.
- Severity assessment: real observability gap — "diagnostics froze on this file" was previously
  undiagnosable from the editor's LSP log.

## errhandling-4
- Disposition: Fixed
- Action: `fltk/lsp/features.py` — `_modifier_bits` and `encode_semantic_tokens` now emit a
  `logging.warning` naming the offending modifier/type before dropping it (module logger), rather
  than a bare silent `continue`. Kept the drop-not-crash behavior the design specifies (§4.6), while
  giving a legend↔classifier drift the breadcrumb the design's "assert-level check" intent wanted.
  An `assert` was not used because §4.6 explicitly says the check must *drop* rather than crash the
  handler; a logged warning satisfies both "reported" and "responded to".
- Severity assessment: low-likelihood (classify only emits legend members) but zero-observability if
  it ever drifts.

## correctness-1
- Disposition: Fixed
- Action: `_debounced_analyze`'s `finally` (`server.py`) now only pops the debounce slot when the
  running task still owns it (`self._debounce.get(uri) is asyncio.current_task()`), so a cancelled
  task's cleanup no longer evicts the replacement installed by a reschedule. New test
  `test_debounce_reschedule_cancels_prior_and_keeps_replacement` pins it.
- Severity assessment: real — broke debounce coalescing after the first reschedule and left a
  from-disk-ghost analysis path; the eviction also seeded correctness-2.

## correctness-2  (reconciled with quality-4)
- Disposition: Fixed
- Action: added a per-URI epoch (`server.py`): `drop()` bumps it, `_analysis_for` captures it at
  submit, and `_store` discards a result whose epoch no longer matches — so a late-completing
  analysis for a closed document never resurrects `_docs[uri]`, and the version-ordering wedge
  across close/reopen cannot form. New tests `test_store_after_drop_does_not_resurrect_state` and
  `test_store_ignores_older_version_result` pin both halves.
- Severity assessment: real, timing-dependent wrong-answer + slow leak in code whose docstrings
  advertise no cross-version coordinate mixing.

## security-1  (reconciled with errhandling-2, quality-1)
- Disposition: Fixed
- Action: as errhandling-2 — import-time `hasattr` guard on the pygls private (fail-closed startup
  crash on drift) plus the `_encoding` warning. The code comment now flags that the mechanism rides
  on a private name that must be re-verified per pygls bump. Note: the pin is already `pygls>=2,<3`
  (design §2.5 allowed the implementer to pick the current stable line, which is 2.x); tightening it
  further is optional and not done, since the loud import-time guard is the load-bearing protection.
- Severity assessment: high under drift (silent non-ASCII file corruption on format). Closed.

## test-1
- Disposition: Fixed
- Action: `test_plumbing_error_pos.py::test_early_success_without_full_consumption_has_offset` now
  uses `top := x:"a"` against `"ab"` (literal succeeds outright, tracker records nothing) and asserts
  `error_pos == 1`, actually exercising the `elif result: error_pos = result.pos` branch that had
  zero coverage; the old grammar tripped the tracker branch instead.
- Severity assessment: real coverage gap masquerading as coverage.

## test-2
- Disposition: Fixed
- Action: added `test_server.py::test_semantic_tokens_range_returns_line_subset` — opens a two-line
  document, requests `semanticTokens/range` for line 1, asserts a strict subset of the full-document
  tokens with all emitted tokens on line 1.
- Severity assessment: real — a protocol-facing deliverable had no test at any level.

## test-3
- Disposition: Fixed
- Action: added `test_debounce_reschedule_cancels_prior_and_keeps_replacement` (cancellation
  bookkeeping) and `test_analysis_for_single_flight_shares_one_submission` (two concurrent analyses
  for one version share one worker submission). Both deterministic and in-process.
- Severity assessment: real — the coalescing/single-flight premises were unexercised.

## test-4
- Disposition: Fixed
- Action: added `test_store_ignores_older_version_result` (the out-of-order-version guard) alongside
  the drop-resurrection test.
- Severity assessment: real — the version-ordering half of the stale-token invariant was untested.

## test-5
- Disposition: Fixed
- Action: added `test_formatting_without_fmt_uses_default_config` — builds a server with
  `formatter_config=None` and asserts formatting still returns edits (not None/crash) with no error
  log, covering the §2.6 default-config path.
- Severity assessment: real — one of the three explicitly "challengeable" decisions was untested.

## test-6
- Disposition: Fixed
- Action: added `test_features.py::test_selection_three_distinct_levels_widen_in_order` over a
  hand-built `DOCUMENT > ITEM > GREETING > name-span` tree with four genuinely distinct spans,
  asserting the full innermost-to-root ordered chain.
- Severity assessment: real — the recursive multi-level selection case was reached but never
  asserted beyond one collapsed level.

## test-7
- Disposition: Fixed
- Action: added `test_format_render_exception_degrades_to_none` — monkeypatches `plumbing.unparse_cst`
  to raise `KeyError` and asserts `_format_blocking` returns `(None, logs)` with an error log,
  covering the broad-`Exception` unparse/render catch (only the build-step catch was tested before).
- Severity assessment: real — a regression narrowing the catch back to `ValueError` would have gone
  uncaught.

## reuse-1
- Disposition: Fixed
- Action: added `build_hello_engine(config_text, *, start_rule)` to `fltk/lsp/conftest.py` returning
  `(engine, grammar)`; `test_engine.py` and `test_engine_analyze.py` now both delegate to it,
  removing the two diverging private `_engine` helpers.
- Severity assessment: minor — two helpers had already begun to diverge with no linkage.

## reuse-2
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: minor. The utf-16 column formula in `LineIndex._column` duplicates pygls's
  `position_codec` code-unit counting.
- Rationale (Won't-Do): design §4.5 deliberately keeps *all* conversion math in `LineIndex` so
  "correctness never depends on pygls internals" — the same pygls-internals-coupling that
  errhandling-2/security-1/quality-1 independently flag as a hazard. Delegating `_column` to
  `pygls.workspace.position_codec.impls[enc].code_units_for_char` would reintroduce exactly that
  coupling for a formula fixed by the UTF-16 standard (the `0xFFFF` BMP boundary is not going to
  change). Doing so would actively work against the design's stated single-owner/independence
  principle, so it should not be done.

## quality-1  (reconciled with errhandling-2, security-1)
- Disposition: Fixed
- Action: as errhandling-2/security-1 (import-time `hasattr` guard + `_encoding` warning + comment
  noting the private-name dependency to re-verify per bump). The process-global narrowing of pygls's
  supported-encodings set itself is inherent to the design's chosen mechanism (§4.5 mandates
  constraining pygls's negotiation to the two encodings `LineIndex` implements) and is retained; the
  fix targets the silent-failure mode, which is the damaging half.
- Severity assessment: high under drift; the loud-failure conversion is the key mitigation.

## quality-2  (reconciled with errhandling-3)
- Disposition: Fixed
- Action: as errhandling-3 (debounce task body wrapped, exception reported via `window/logMessage`).
- Severity assessment: real observability gap.

## quality-3
- Disposition: Fixed
- Action: `server.py` — the four-field format-pipeline tri-state (`_fmt_parser`, `_fmt_unparser`,
  `_fmt_built`, `_fmt_failed`) collapses to `_fmt_pipeline: tuple[ParserResult, UnparserResult] | None`
  plus `_fmt_failed`. `_ensure_format_pipeline` returns the pipeline-or-`None`; `_format_blocking`
  unpacks it, and the two narrowing `assert`s are gone (illegal field combinations are no longer
  representable).
- Severity assessment: minor maintainability smell; cheap to remove while already in the file.

## quality-4  (reconciled with correctness-2)
- Disposition: Fixed
- Action: as correctness-2 (per-URI epoch counter; result discarded on epoch mismatch).
- Severity assessment: real.

## quality-5
- Disposition: TODO(lsp-start-rule-dedup)
- Action: `TODO.md` entry + `TODO(lsp-start-rule-dedup)` comment at `FltkLanguageServer.__init__`
  (`server.py`). No code change to the surface.
- Severity assessment: real-but-latent drift risk (only in-tree caller passes the engine's own rule).
- Rationale for deferral: the reviewer's fix drops the `start_rule` parameter from `create_server`,
  which the frozen design (§4.7) specifies. Collapsing it is a deliberate pre-release surface
  decision better made explicitly than as an incidental respond-mode signature change; recorded as a
  concrete TODO (expose `AnalysisEngine.start_rule`, read it in the server) rather than done here.

## quality-6
- Disposition: Fixed
- Action: `server.py` — `_SERVER_VERSION = "0.2.0"` replaced by `_server_version()` reading
  `importlib.metadata.version("fltk")` (falling back to `"unknown"`), so the `initialize`-advertised
  version tracks the package instead of drifting after the next release bump.
- Severity assessment: minor but bites during triage.

## quality-7
- Disposition: Fixed
- Action: rewrote the workflow-referencing comments to state the actual contract, in the files this
  round changed: `engine.py` ("thin wrapper over `analyze` preserving its original result type and
  behavior"), `features.py` ("must set-equal `lsp_config.TOKEN_LEGEND` (pinned by a test)"),
  `server.py` ("not configurable"), `test_engine_analyze.py` docstring, and renamed the two
  `..._set_equal_round1_...` tests to `..._set_equal_token_legend` / `..._set_equal_standard_modifiers`.
  Per the standing project standard, workflow-round references in shipped code are removed. The
  round-1 instances outside this round's diff (`lsp_config.py`, `highlight_cli.py`) were left
  untouched (out of the code this round describes).
- Severity assessment: real per the project's comment-hygiene standard.

## efficiency-1
- Disposition: Fixed
- Action: `server.py` — semantic-token encoding moved off the event loop into `_analyze_blocking`
  (worker thread), which now returns `(analysis, line_index, encoded_tokens)`; `_store` just assigns
  the precomputed data. The O(tokens × line-prefix) encode no longer runs on the protocol loop on
  every settled analysis, and the single-flight double-encode noted in the review's non-findings is
  gone too.
- Severity assessment: real keystroke-scale loop stall on large documents; also dead work for
  diagnostics-only clients (now on the worker regardless, but off the loop).

## efficiency-2
- Disposition: Fixed
- Action: `analyze_and_publish` now routes through `_ensure_analyzed` (which short-circuits when the
  current version is already analyzed) instead of calling `_analysis_for` unconditionally, so a
  debounce timer firing after a pull handler already analyzed the same version no longer re-parses.
- Severity assessment: real — a redundant full parse+classify per settled edit in the common
  edit-then-request-tokens sequence.

## efficiency-3
- Disposition: Fixed
- Action: `server.py` `semantic_tokens_range` — the linear
  `[token for token in good.tokens if token.start < end and token.end > start]` scan is replaced by
  two `bisect` calls over the already-sorted, non-overlapping `good.tokens`: `good.tokens` is sorted
  by `start` (so `end` is monotonic too), so `lo = bisect.bisect_right(tokens, start,
  key=lambda tok: tok.end)` (first token with `end > start`) and `hi = bisect.bisect_left(tokens,
  end, key=lambda tok: tok.start)` (first token with `start >= end`) bracket the overlap window as
  `tokens[lo:hi]` in O(log n + subset). Added `import bisect`; removed the
  `TODO(lsp-range-token-bisect)` comment and the `TODO.md` entry.
  `test_semantic_tokens_range_returns_line_subset` (added for test-2) pins the behavior and still
  passes; full LSP suite 196 passed. The subset re-encode on the loop is left as-is: per the
  reviewer's own fix menu that half is acceptable since the subset is small.
- Severity assessment: minor — O(n) scan per range request recurring on scroll; the reviewer called
  it "not catastrophic". Reworked per the judge's round-1 verdict: the bisect needs no design cycle
  or owner input (it lives entirely within design §4.7's existing filter-then-encode structure and
  `key=` is available on the project's Python floor), so it fails the TODO rubric's Q2 and is a
  do-now rather than a deferral.

## efficiency-4
- Disposition: Fixed
- Action: `features.py` `_line_segments` now uses `line_index.line_of(token.start/end)` for the line
  bounds instead of `offset_to_position(...)`, dropping two redundant per-token column computations
  (the column is still computed once per emitted segment).
- Severity assessment: minor constant-factor overhead multiplying the encode cost.
