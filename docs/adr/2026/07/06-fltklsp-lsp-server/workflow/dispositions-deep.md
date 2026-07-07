# Dispositions — deep review, final round (base 87dbc0d, reviewed HEAD 9a085e9)

Seven reviewer notes triaged. No `scope-N` findings; no escalation. Fixes committed in one revision
on top of 9a085e9. Several findings across notes are the same underlying issue reported by different
reviewers (from_paths/plumbing wrapper, _THEME/legend, CLI file-IO, duplicate test helper,
table-rebuild hot path) — cross-referenced below.

The task's spotlight — `TODO(lsp-classify-hotpath)`, whose deferral trigger ("when the §4.7
`AnalysisEngine` lands") has now arrived — is addressed at quality-1/efficiency-6: the
once-per-grammar table build is hoisted now; the remaining internal items keep the TODO alive under
a fresh, unmet trigger.

Note on prior-round findings carried in the note files: the error-handling note's checkpoint-2
section (errhandling-1/-2/-3) and the efficiency note's first section describe an earlier HEAD;
several were already resolved before 9a085e9. Those are dispositioned below as "already resolved",
verified against current source.

---

## error-handling

### errhandling-1 — unknown CST node kind silently under-classifies
- Disposition: Fixed (already resolved before this round)
- Action: no change needed — `classify._rule_for_node` (`classify.py:162-173`) raises
  `AssertionError` naming the offending `node.kind.name` on a `kind_to_rule` miss, at both the
  default and explicit walk sites. Verified against current source.
- Severity assessment: had it still been a silent `.get()` skip, an invariant violation would ship
  as missing highlight coverage with no diagnostic; the assertion converts it to a loud failure.

### errhandling-2 — second `.get()` folds a distinct desync into the same swallow
- Disposition: Fixed (already resolved before this round)
- Action: no change needed — `_default_intervals` indexes `tables.tables[rule.name]` directly
  (`classify.py:190`), so a table/kind-map desync raises `KeyError` at its origin. Verified.
- Severity assessment: same silent-under-classification class as errhandling-1; direct indexing keeps
  the two failure modes distinguishable.

### errhandling-3 — `parse_lsp_config_file` docstring understates its uncaught error paths
- Disposition: Fixed (already resolved before this round)
- Action: no change needed — the docstring at `plumbing.py:284-288` already lists `OSError` and
  `UnicodeDecodeError`. Verified.
- Severity assessment: low; documentation-accuracy only. The forward-looking CLI concern it predicted
  is handled at errhandling-4.

### errhandling-4 — CLI file-IO errors escape as raw tracebacks (§4.8 contract unmet)
- Disposition: Fixed
- Action: `highlight_cli.py:main` — widened the `try` to cover `file.read_text()` and broadened the
  handler from `except ValueError` to `except (ValueError, OSError)` (UnicodeDecodeError is a
  ValueError; missing/unreadable `--grammar`/`--lsp`/`FILE` are OSError subclasses), echoing
  `str(exc)` to stderr with `raise typer.Exit(1)`. The `--lsp` read now routes through
  `plumbing.parse_lsp_config_file` (reuse-1) so its curated "LSP config file not found" message is
  surfaced. Pinned by new tests `test_missing_grammar_exits_1`, `test_missing_lsp_exits_1`,
  `test_missing_input_file_exits_1`.
- Severity assessment: the most common CLI misuse (a typo'd path) got a multi-frame traceback instead
  of the designed "formatted message to stderr, exit 1"; an M2 server on this path would inherit it.

### errhandling-5 — `_render` trusts the sorted/non-overlapping invariant with no assertion
- Disposition: Fixed
- Action: `highlight_cli.py:_render` now asserts `token.start >= cursor` at the top of the loop, so a
  classifier invariant break fails loudly at the seam instead of rendering garbage.
- Severity assessment: low; display-only. Makes the trusted upstream invariant self-checking at
  negligible cost.

---

## correctness

No findings. The reviewer's two out-of-lane observations are covered: the `except ValueError`
traceback gap is fixed at errhandling-4; the `generate_parser` per-construction `sys.modules` entry
is preexisting plumbing behavior, not introduced this round, and out of scope.

---

## security

### security-1 — raw terminal-escape passthrough in `fltk-highlight` stdout
- Disposition: Fixed
- Action: `highlight_cli.py` — added `_sanitize`, which escapes control/bidi/zero-width characters via
  the existing `errors.escape_control_chars` (the same policy the error path already uses), applied
  per emitted source slice in `_render` (gaps, trailing text, painted segments) so the tool's own SGR
  framing stays intact. Newlines are preserved by splitting on `\n` before escaping; tabs pass through
  unchanged.
- Severity assessment: a hostile source file could drive the terminal (OSC 52 clipboard, title,
  cursor spoofing) or restyle malicious code as a comment — undermining the "read unfamiliar code with
  semantic highlighting" purpose the tool exists for. The golden ANSI test is unaffected (its input
  has no escapable characters).

### security-2 — untrusted grammar + input can hang or crash the highlight pipeline (DoS)
- Disposition: Fixed (bounded scope; the reviewer explicitly accepted "acceptable for the CLI this
  round, but make it a decision")
- Action: `engine.py:highlight` now catches `RecursionError` and returns it as a parse failure
  (`HighlightResult(tokens=None, error=...)`) instead of letting it escape the seam; the
  workspace-trust posture is documented on the `highlight` docstring. The remaining vector —
  catastrophic regex backtracking / non-terminating parse — cannot be bounded without a
  wall-clock/cancellation budget, which per design §4.7 is server policy layered on top of this
  one-shot seam; no new TODO, since the design already assigns it to the M2 server layer.
- Severity assessment: for the one-shot CLI, the recursion crash is now a clean reported failure; the
  unbounded-CPU vector remains a real concern for the long-lived server, already design-scoped to
  server-side cancellation.

---

## test

### test-1 — dogfood fixture's def/ref/namespace/rule-qualifier/global-punctuation paints unexercised
- Disposition: Fixed
- Action: added `test_dogfood.py::test_dogfood_highlights_def_ref_namespace_and_qualifier` — a sample
  with `def`, `ref`, `namespace` statements, a `rule:` qualifier (`rule:beta`), and a bare `;`,
  asserting `keyword` for each statement keyword, `type` for the addressed rule name, `keyword` for
  the qualifier's `rule`, and `punctuation` for the global `;`.
- Severity assessment: three of five statement-keyword blocks, the qualifier `"rule"` paint, and the
  whole global punctuation scope were committed but never exercised end-to-end.

### test-2 — no CLI test produces a `declaration`-modifier token (bold branch dead)
- Disposition: Fixed
- Action: added `test_highlight_cli.py::test_def_site_rendered_bold` — a `def name: variable;` spec
  paints `world` with `declaration`; asserts stdout contains `\x1b[1;<code>m...` (bold) and not the
  plain `\x1b[<code>m...` form.
- Severity assessment: def-site paint is a live round-1 feature (§4.6/§9); a bug in the bold SGR
  branch would have been invisible.

### test-3 — no test reuses one `AnalysisEngine` across `highlight` calls
- Disposition: Fixed
- Action: added `test_engine.py::test_highlight_reused_across_calls` — one engine, three calls
  (success, parse failure, success), asserting each result is independently correct and a prior
  failure doesn't corrupt a later success.
- Severity assessment: reuse is the engine's documented raison d'être (§4.7) and the exact pattern the
  M2 server imposes; accidental cross-call state would have gone undetected.

### test-4 — CLI's `except` clause only half-tested; nonexistent `--lsp` likely violated the contract
- Disposition: Fixed
- Action: added `test_missing_grammar_exits_1`, `test_missing_lsp_exits_1`,
  `test_missing_input_file_exits_1` (exit 1, empty stdout, non-empty stderr), passing against the
  errhandling-4 fix.
- Severity assessment: half the CLI's single catch clause was unverified and the nonexistent-`--lsp`
  path did violate §4.8; both now pinned.

### test-5 — dogfood `global_child_matchers` assertion checked only a count
- Disposition: Fixed
- Action: `test_dogfood_spec_loads_against_its_own_grammar` now asserts the matcher set equals
  `{ByLiteralText(";"), ByLiteralText(":")}` and that each paints `punctuation`.
- Severity assessment: the count-only assertion was satisfied by any two matchers regardless of which
  literals or paint they carried.

---

## reuse

### reuse-1 — `from_paths` reimplements `plumbing.parse_lsp_config_file` (dup of quality-2)
- Disposition: Fixed
- Action: `engine.py:from_paths` now calls `plumbing.parse_lsp_config_file(lsp_path, grammar)` for the
  file path (and `load_lsp_config("", grammar)` only for the no-file default), matching the codebase
  convention (`unparse_cli.py` → `plumbing.parse_format_config_file`). A missing `--lsp` now yields the
  wrapper's curated "LSP config file not found: <path>" message.
- Severity assessment: the two paths disagreed on the missing-file message and the engine (the
  canonical consumer) bypassed the wrapper, making it dead-in-practice API and forking future behavior.

### reuse-2 — `_THEME` re-enumerates the legend as unchecked strings (dup of quality-4)
- Disposition: Fixed
- Action: added `test_highlight_cli.py::test_theme_covers_the_legend` asserting
  `set(_THEME) == TOKEN_LEGEND`. Keeps the theme private/non-configurable while pinning coverage.
- Severity assessment: §4.5 anticipates legend growth; the first added member forgetting a theme entry
  would render uncolored, found by a user rather than CI.

### reuse-3 — exact-span token-lookup helper duplicated four ways (dup of quality-5 helper half)
- Disposition: Fixed
- Action: added `fltk/lsp/conftest.py` with canonical `token_for` / `token_type_at`; migrated all four
  copies (`test_classify.py`, `test_classify_painter.py`, `test_engine.py`, `test_dogfood.py`) to
  import from it, removing the local definitions.
- Severity assessment: four copies of nontrivial assertion semantics (exact bounds, exactly-one) would
  drift on the next behavior change; consolidation removes the drift surface.

---

## quality

### quality-1 — `TODO(lsp-classify-hotpath)` trigger arrived; table build not hoisted
- Disposition: Fixed (item 1 now; the sweep-line + walk-fusion items remain a re-triggered TODO —
  efficiency-4's `ByLabel.upper()` item was promoted to Fixed in rework round 2, see efficiency-4)
- Action: `AnalysisEngine.__init__` builds `classify.build_grammar_tables(...)` once (`engine.py`) and
  threads it into `classify` via a new optional `tables=` parameter
  (`classify.py:classify`/`default_tokens`); `highlight` passes the cached tables, so it no longer
  re-walks the grammar or recompiles every terminal regex per call. `TODO.md` `lsp-classify-hotpath`
  rewritten: item (1) recorded as done; the remaining `_winner_segments` O(n²), double-walk, and
  `ByLabel.upper()` items retained under a concrete unmet trigger ("before the M2 server ships / when
  profiling shows classify latency dominates"), all confined to `classify.py`/`lsp_config.py` with no
  seam-signature impact. Inline `TODO(lsp-classify-hotpath)` comments remain at `_winner_segments` and
  the second `_default_intervals` loop (the `_matches` comment was removed with efficiency-4's fix).
- Severity assessment: deferring the table build past the engine's landing would have baked
  O(grammar)+regex-compile cost into the per-keystroke path and forced a later public-signature change
  under M2 — the exact churn the TODO existed to prevent. The optional `tables` parameter is
  backward-compatible, so standalone `classify`/`default_tokens` callers are unaffected.

### quality-2 — `from_paths` reimplements `parse_lsp_config_file`
- Disposition: Fixed (same change as reuse-1)
- Action: see reuse-1.
- Severity assessment: see reuse-1.

### quality-3 — CLI error surface inconsistent; missing files produce raw tracebacks
- Disposition: Fixed (same change as errhandling-4)
- Action: see errhandling-4.
- Severity assessment: this is the project's first console script and the M2 CLI template; the
  inconsistent surface would have propagated.

### quality-4 — `_THEME` re-enumerates the token legend
- Disposition: Fixed (same change as reuse-2)
- Action: see reuse-2.
- Severity assessment: see reuse-2.

### quality-5 — copy-pasted test fixtures + helper under two names
- Disposition: Fixed
- Action: helper consolidated to `conftest.py` (reuse-3); the byte-identical `_GRAMMAR`/`_LSP` fixtures
  in `test_engine.py` and `test_highlight_cli.py` moved to `conftest.HELLO_GRAMMAR` / `HELLO_LSP` and
  imported by both. Genuinely-distinct per-file grammars (`test_classify`, `test_classify_painter`,
  `test_dogfood`) left local.
- Severity assessment: cloned fixtures fork on first divergent need; a shared source of truth prevents
  silent drift.

---

## efficiency

### efficiency-1 — `classify`/`default_tokens` rebuild the whole grammar table per call
- Disposition: Fixed (subsumed by quality-1)
- Action: resolved by the optional `tables=` parameter + `AnalysisEngine` building tables once; the
  hot-path caller no longer rebuilds. See quality-1.
- Severity assessment: 100%-redundant per-call grammar walk + regex recompilation on the text→tokens
  path; now paid once per engine.

### efficiency-2 — `_winner_segments` is O(n²), not the advertised O(n log n)
- Disposition: TODO(lsp-classify-hotpath)
- Action: retained under the rewritten TODO with its inline comment at `classify.py:_winner_segments`.
  Deferred: it is internal to `classify.py`, purely a performance (not correctness) improvement, and
  forces no engine-seam signature change; the sweep-line rewrite is best done with efficiency-3 (same
  walk/segment logic).
- Severity assessment: quadratic in explicit-paint interval count; a spec painting a common anchor over
  a large document is the scale ceiling. Output remains correct; the design's O(n log n) claim
  (§4.6/§6) is aspirational and now tracked in the TODO.

### efficiency-3 — `classify` walks the analysis tree twice
- Disposition: TODO(lsp-classify-hotpath)
- Action: retained under the rewritten TODO with its inline comment at the second `_default_intervals`
  loop in `classify.py`. Same rationale as efficiency-2 (internal, perf-only, no seam impact).
- Severity assessment: ~2x tree traversal on the hot path; linear, lower-stakes than efficiency-2,
  additive per highlight.

### efficiency-4 — `ByLabel` matcher re-uppercases its name on every comparison
- Disposition: Fixed (rework round 2 — promoted from TODO per judge verdict)
- Action: `ByLabel` (`lsp_config.py:442-453`) gained `name_upper: str =
  dataclasses.field(init=False, compare=False, repr=False)`, set in `__post_init__` via
  `object.__setattr__(self, "name_upper", self.name.upper())`; `_matches` (`classify.py:240-242`) now
  compares `label_name == match.name_upper` and its inline `TODO(lsp-classify-hotpath)` comment is
  removed. `compare=False`/`repr=False` keep the by-value equality surface keyed on `name` alone, so
  the `test_lsp_resolve.py` equality assertions are unchanged (12 pass). `TODO.md`
  `lsp-classify-hotpath` rewritten to two items (sweep-line + walk-fusion); the `ByLabel`/`_matches`
  location dropped. Confined to `classify.py`/`lsp_config.py`, no seam or public-surface change.
- Severity assessment: minor redundant short-string uppercase per (child × matcher) comparison on the
  hot path; no correctness impact. The judge's Q2 finding stands — the safe design was fully specified
  in the TODO's own text (no design cycle or owner input remained), so it is a mechanical change, not a
  batching deferral.

### efficiency-5 — `parse_lsp_config_file` pre-checks existence before opening (TOCTOU)
- Disposition: Won't-Do
- Action: no change.
- Severity assessment: minor; one extra `stat` off the hot path (config loaded once at construction),
  with a negligible TOCTOU window on an unlikely check→open race (both raise `FileNotFoundError`).
- Rationale: the `exists()` guard exists specifically to raise the curated "LSP config file not found:
  <path>" message (`plumbing.py:290-292`), and it mirrors the sibling `parse_format_config_file` the
  reuse reviewer confirmed is intended mirroring. reuse-1/quality-2/errhandling-4 now route
  `AnalysisEngine.from_paths`'s `--lsp` path *through* this wrapper precisely so that curated message
  reaches the CLI user. Applying the suggested fix (drop the guard, let `open()` raise) would regress
  that message to the bare `FileNotFoundError: [Errno 2] ...` text the reuse finding wants replaced —
  the two findings are in direct tension and the curated message is the load-bearing behavior. The
  suggested catch-and-re-raise alternative is behaviorally identical to the current pre-check while
  adding branch complexity, for a stat cost immaterial off the hot path. Doing the change would
  actively harm the message contract other findings depend on.

### efficiency-6 — `AnalysisEngine.highlight` rebuilds the per-grammar table on every call
- Disposition: Fixed (same change as quality-1)
- Action: see quality-1 — tables built once in `__init__`, threaded through `highlight` →
  `classify(..., tables=self._tables)`.
- Severity assessment: the concrete per-keystroke path the earlier findings anticipated; the redundant
  grammar walk + regex recompilation is now paid once per engine lifetime.
