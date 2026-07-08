# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `rule-preserve-blanks`

Rule-level `preserve_blanks` is parsed and stored but never consumed. `RuleConfig.preserve_blanks`
(`fltk/unparse/fmt_config.py`) and `FormatterConfig.get_preserve_blanks(rule_name)` exist, but both
unparser generators read the *global* `trivia_config.preserve_blanks` as a generation-time constant
rather than calling the rule-aware method, so a per-rule `preserve_blanks` directive has no effect.
Pre-existing feature gap, orthogonal to the blank-line-preservation bug fix. To close it, thread the
rule name to the newline-spacing emission and read `get_preserve_blanks(rule_name)`. Location:
`fltk/unparse/gsm2unparser.py` (both `# Get preserve_blanks from config` sites in
`_gen_trivia_processing`), `fltk/unparse/gsm2unparser_rs.py` (`_get_preserve_blanks`).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `fmt-cli-per-consumer-version`

`fltk-fmt-cli`'s `FmtArgs` carries `#[command(version)]`, which clap expands to `CARGO_PKG_VERSION` where `FmtArgs` is defined — the scaffolding crate — so every consumer binary reports `fltk-fmt-cli`'s version, not its own. This is an observable defect today: `fltkfmt` is `0.1.0` (`crates/fltkfmt/Cargo.toml`; deliberately outside the root workspace with its own `[workspace]`), while `fltk-fmt-cli` is `0.2.0` (`crates/fltk-fmt-cli/Cargo.toml`), so `fltkfmt --version` prints `0.2.0` for a `0.1.0` binary. Fix by threading `version` (and possibly `name`) through `run_main` / `fltk_formatter_main!` the same way `about` is threaded (commit for `fmt-cli-per-consumer-about`), so `<consumer> --version` prints the consumer's own version. Do NOT add a second bare `&'static str` positional argument next to `about` on `run_main`: two adjacent indistinguishable string params can be swapped silently (a version string rendered as the `--help` description). Introduce an identity struct instead (e.g. `FormatterInfo::new(about).version(..)`, keeping `about` required) so this fix — and any later per-consumer knob — is a non-breaking addition rather than another signature break. Location: `crates/fltk-fmt-cli/src/lib.rs` (`#[command(version)]` on `FmtArgs`, and `run_main`).

## `lsp-cst-text-helpers`

`fltk/lsp/lsp_config.py`'s `_span_text` / `_identifier_text` and the inline literal-extraction
sequence in `_parse_anchor` duplicate helpers that already exist for `.fltkfmt`:
`fltk/unparse/fmt_config.py` (`_span_text`, `_extract_identifier_text`, `_extract_literal_text`)
and the more careful `fltk/unparse/pyrt.py:extract_span_text` (which guards against a
source-bearing span whose `text()` returns `None` — a guard the `fmt_config` and `lsp_config`
copies both lack). There is also a fourth single-backend copy at `fltk/fegen/fltk2gsm.py`
(`Cst2Gsm._span_text`). Consolidate into one canonical, `SpanProtocol`-typed helper (dropping
the `hasattr` probe and `type: ignore`s now that `SpanProtocol` includes `text()`), keeping the
pyrt source-bearing guard, and migrate all copies to it. Deferred because it touches out-of-round
modules (`fmt_config`, `unparse.pyrt`). Location: `fltk/lsp/lsp_config.py` (`_span_text`,
`_identifier_text`, `_parse_anchor`).

## `lsp-test-parse-helper`

`fltk/lsp/test_lsp_config.py` (`_load`) and `fltk/lsp/test_lsp_validation.py` (`_parse`) each
hand-roll the same `TerminalSource` → `Parser` → `apply__parse_lsp_spec` → full-consumption
check, diverging only on failure reporting (`_load` renders a caret diagnostic; `_parse`
bare-asserts). The design's `plumbing.parse_lsp_config` wrapper (not yet built) is the intended
home for this sequence; fold both helpers onto it once it lands, rather than building a throwaway
interim shared helper. Location: `fltk/lsp/test_lsp_config.py`, `fltk/lsp/test_lsp_validation.py`.

## `formatter-group-idempotency`

The formatter is not idempotent on grouped alternations at narrow widths: `fltk/fegen/test_data/rust_parser_fixture.fltkg` formatted at width 40 / indent 4 changes between pass 1 and pass 2 (a grouped alternation `( inner:rec_via_sub . "+" | inner:atom ) .` re-breaks into a multi-line `(` … `)` block on the second pass), converging only at pass 2. Single-pass cross-backend parity holds, so this is a shared formatter-layout bug present in both the Python and Rust backends, not a backend divergence. Fixing it is a formatter behavior change to both backends and was out of scope for the pure test addition that discovered it (`fltkfmt` integration tests). The idempotency integration test (`crates/fltkfmt/tests/cli.rs`, `format_format_is_format`) carves this one case out explicitly, pinning current behavior (`out2 != out1`, `out3 == out2`); when the formatter is fixed that carve-out's `assert_ne!` trips, forcing its removal alongside this entry. Location: `crates/fltkfmt/tests/cli.rs` (the `TODO(formatter-group-idempotency)` carve-out in `format_format_is_format`); the layout logic lives in the shared unparser/renderer (`fltk/unparse/` and the generated Rust unparser).

## `resolver-spec-file-recognition`

`fltk/lsp/resolver.py`'s `_looks_like_path` treats a `--resolver` spec head as a file whenever
`pathlib.Path(head).is_file()` — a cwd-relative check — even for a head that reads as a plain
module (no `.py`, no separator). So whether `--resolver mylang.resolvers:create_resolver` imports
the installed module `mylang.resolvers` or `exec`s a file literally named `mylang.resolvers`
depends on the server's cwd contents. Editors commonly spawn LSP servers with cwd = workspace
root, so a hostile project that plants a file matching a known resolver module name could get
arbitrary Python exec'd at startup for a user who configured a bare-module resolver spec. No
shipped config is affected (the gear demo and README use explicit `.py` paths). The fix — drop the
bare `is_file()` recognition, keeping only the unambiguous `.py`/separator signals — contradicts
the frozen step5 design §4.3 ("a path is recognized by an existing file"), so it requires a design
delta before landing; do it there, not by editing the frozen doc. Location: `fltk/lsp/resolver.py`
(`_looks_like_path`).

## `rename-guard-incomplete-scan`

`ProjectNavigator.rename_hazard` (`fltk/lsp/project.py`) decides whether a same-file rename is safe
by scanning the workspace for cross-file references. When that scan is incomplete -- a directory
`os.walk` error (surfaced only as an advisory `window/logMessage` warning), or a neighbor file that
is unreadable/unparseable and therefore dropped by `host.document()` -- the guard still returns
`Hazard.NONE` and permits the rename, so a cross-file reference hiding in the skipped file goes
undetected and the rename can silently break another file. This is the one fail-closed path (frozen
step5 design §4.6) meeting the read path's deliberate silent-degradation policy (§5:
transiently-broken neighbors are the normal state of live editing); the design did not resolve the
tension. Refusing on any imperfect scan would make rename nearly unusable during editing; permitting
weakens the guard. Reconciling requires a design delta (e.g. refuse only on walk/IO errors while
tolerating unparseable neighbors, or track scan completeness explicitly), not a respond-mode patch.
Location: `fltk/lsp/project.py` (`ProjectNavigator.rename_hazard`).

## `lsp-analysis-watchdog`

`fltk/lsp/server.py`'s analysis runs on a single-worker `ThreadPoolExecutor`, and Python worker
threads cannot be preempted. The engine already catches `RecursionError` and reports it as a normal
parse-failure diagnostic, but a truly non-terminating parse — catastrophic regex backtracking or an
unbounded grammar recursion that never hits the interpreter's recursion limit — starves every later
analysis for that server process: the protocol loop stays responsive (it is never blocked on the
worker) but that document, and every document analyzed after it, stops updating. Honoring the
engine's wall-clock promise fully needs either process isolation (run each analysis in a killable
subprocess) or a parser-level step/time budget threaded down into the generated parser — real design
work that would dominate this round. Deferred with the stale-token policy covering the degraded mode
meanwhile. Location: `fltk/lsp/server.py` (`FltkLanguageServer._analyze_blocking`).

## `lsp-classify-hotpath`

`fltk/lsp/classify.py`'s `classify` / `default_tokens` are the per-document hot path the M2
server will sit on. The once-per-grammar table build is now hoisted: `AnalysisEngine` builds a
`_GrammarTables` once in `__init__` and threads it into `classify` via the optional `tables`
parameter, so `highlight` no longer re-walks the grammar and recompiles every terminal regex per
call. Two internal inefficiencies remain, both confined to `classify.py` and neither forcing a
change to the engine seam's signature: (1) `_winner_segments` rescans all intervals per boundary
pair (O(n^2)); a sweep line maintaining the active set reaches the intended O(n log n); (2)
`classify` walks the analysis tree twice (`_explicit_intervals` then `_default_intervals`) — fold
default emission into the explicit walk. Both are the design-stage sweep-line/walk-fusion rewrite
of the interval-resolution core, best batched (shared walk/segment logic). Address before the M2
server ships (it drives `classify` per keystroke), or when profiling on a real grammar shows
`classify` latency dominates. Location: `fltk/lsp/classify.py` (`_winner_segments`, the second
`_default_intervals` loop in `classify`).

## `lsp-rule-surface-index`

`fltk/lsp/lsp_config.py`'s `_index_rule` (`RuleIndex`: labels / literals / invoked rules) and
`fltk/lsp/classify.py`'s `_build_terminal_table` (`_TerminalTable`: literals / regexes,
label-keyed) are two parallel per-rule walks over `rule.alternatives` × `gsm.for_each_item`, each
collecting an overlapping slice of a rule's item surface (literals appear in both). The definition
of "what a rule's items expose to anchors/classification" thus lives in two mirrored walkers in
two modules; the planned INLINE-support change (splicing invoked rules' terminals into the parent
surface) must then be implemented twice, and any drift shows up as validation accepting an anchor
the classifier can't match. Unify into one per-rule surface index (labels, literals, regexes,
invoked rules; label-keyed views derived from it) consumed by validation, resolution, and the
classifier tables. Deferred rather than done in respond-mode because it restructures private
surfaces across two modules; best landed with INLINE support, which is what forces both walks to
change. Location: `fltk/lsp/lsp_config.py` (`_index_rule`), `fltk/lsp/classify.py`
(`_build_terminal_table`).
