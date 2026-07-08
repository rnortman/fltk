# Exploration: state of `.fltklsp` / FLTK LSP tooling ahead of the next round

Context for this survey, relayed verbatim per the requester: **"NO DECISIONS HAVE BEEN MADE.
This was a brainstorming session. Everything is malleable at this point."** The ADR
(`README.md`), `brainstorm.md`, and `fltklsp-spec.md` are directional/advisory only — not
ground truth. The step1/step2/step3 design docs and their `implementation-log.md`s are the
authoritative record of what was actually decided and built for M0–M2 and M4 (each explicitly
supersedes the advisory docs where they conflict, and says so in its own §2 "deltas"
section). The code, verified directly for this pass, is more authoritative still. Nothing
below is a recommendation, a diagnosis, or a scoping decision — that is the next round's
designer's job.

Repo state surveyed: HEAD at commit `46c17e5` ("feat(lsp): .fltklsp def/ref/namespace
semantics (M4)"), i.e. M0, M1, M2, and M4 are merged. M3 (prefix-CST exposure) and M5
(resolver plugin / native fast path) are not started.

## 1. What M0–M2 and M4 actually delivered, and how the plan changed along the way

### M0+M1 (round 1, commit range ending `a17ba80`) — `.fltklsp` language, loader, classifier, `fltk-highlight`

Delivered exactly what `step1/design.md` scoped, with the plan itself already having deviated
from the advisory ADR/brainstorm/spec in four load-bearing ways (`step1/design.md` §2, all
confirmed still true in code):

- **Suppressed terminals had to become visible.** `fltk2gsm.Cst2Gsm.visit_item` defaults
  unlabeled `Literal`/`Regex` items to `Disposition.SUPPRESS`, and `gsm2parser.py:848` omits
  suppressed items from the CST entirely — so the brainstorm's per-occurrence "paint the
  keyword literal" scheme is unimplementable against the ordinary CST (clockwork's
  `"name"`/`":"` literals are gaps, not nodes). Fix, built in this round:
  `fltk/lsp/analysis.py`'s `prepare_analysis_grammar(grammar) -> gsm.Grammar` — a GSM
  transform promoting every `SUPPRESS` disposition to `INCLUDE` recursively, so suppressed
  literals/regexes/subtrees surface as CST children with unchanged spans. This is the
  "analysis grammar," fed to `plumbing.generate_parser` and never written to disk — a second,
  fatter-CST parser instance distinct from the standard-disposition one used for formatting.
  `INLINE` (`!`) items are a separate, unsupported case: the Python generator raises a bare
  `NotImplementedError` on them (`gsm2parser.py:828-830`, Rust generator has the same gap), so
  `prepare_analysis_grammar` scans up front and raises a clean `ValueError` instead of letting
  that escape. `INLINE`-bearing grammars (the only in-tree one, `fltk.fltkg`, is marked
  "intentionally broken" in the Makefile) cannot be loaded by any analysis engine today.
- **`.fltkfmt` has no load-time GSM validation to "reuse."** The ADR/spec both claimed
  `.fltklsp` reuses `.fltkfmt`'s anchor validation; `fmt_config.fmt_cst_to_config` never
  consults a `gsm.Grammar`, and unmatched anchors silently no-op at unparser-codegen time.
  `.fltklsp` reuses only the *addressing idiom* (anchors, `rule` blocks); load-time GSM
  validation is new, built-from-scratch surface in this round
  (`fltk/lsp/lsp_config.py:validate_config`).
- **No `rust_cst_module=` parameter exists** on `plumbing.generate_parser` (the ADR D4 cited
  one). The Rust path is exclusively offline per-grammar codegen via `fltk.fegen.genparser`
  (`gen-rust-cst`/`gen-rust-parser`/`gen-rust-unparser`), compiled by the consumer's own
  Cargo/maturin build — confirmed still true (§3 below). This doesn't affect M0/M1 (pure
  Python) but changes the M5 native-fast-path story: it would need a new `genparser` flag
  that emits Rust from the *analysis*-grammar variant, which does not exist.
- **Global-anchor ambiguity: union semantics, not the spec's error rule.** The spec says an
  identifier anchor that is both a label and a rule name is a load error requiring
  `label:`/`rule:` disambiguation. But `fltk2gsm` gives every unlabeled rule invocation an
  implicit label equal to the rule name, so "is both a label and a rule name" is the *norm*
  for invoked-rule anchors, not an edge case — the spec's rule would reject nearly every
  rule-name anchor. Round 1 replaced it with union semantics: an unqualified global anchor
  matches both readings. Explicitly called out as a forward compatibility commitment (once
  out-of-tree `.fltklsp` files rely on union semantics, tightening to an error later is a
  breaking change).

Deliverables (all present, `fltk/lsp/`): grammar `fltklsp.fltkg` (25 lines) + 4 committed
generated files (`fltklsp_cst.py`, `fltklsp_cst_protocol.py`, `fltklsp_parser.py`,
`fltklsp_trivia_parser.py`, generated via a `Makefile` `gencode` step mirroring the
`unparsefmt` precedent); `lsp_config.py` (config dataclasses, `GrammarIndex`/`RuleIndex`,
`validate_config`, `resolve_config`, `load_lsp_config`); `analysis.py`
(`prepare_analysis_grammar`); `classify.py` (`Token`, default classifier, two-layer painter
engine, `classify()`); `engine.py` (`AnalysisEngine`, `HighlightResult`); `highlight_cli.py`
(`fltk-highlight`, the project's first `[project.scripts]` entry); `plumbing.py` gained
`parse_lsp_config`/`parse_lsp_config_file` wrappers. A user decision recorded in §9 of the
design: **def-site paint is live starting in round 1**, not deferred to M4 — a `def` statement
already paints its declaration site (kind's first legend segment + `declaration` modifier)
even though `ref`/`namespace` stayed fully inert until M4.

### M2 (round 2, commit `76124f9`) — `fltk-lsp` pygls server

Delivered the ADR's M2 feature list (diagnostics, semantic tokens full+range, folding ranges,
selection ranges, document formatting, stale-tokens-on-failure) plus position-encoding
negotiation, with these deltas from the step1 plan and advisory docs (`step2/design.md` §2):

- `HighlightResult` (tokens|None, error|None) wasn't enough for a server (no CST for folding/
  selection, no structured error position for `Diagnostic.range`). The engine grew a richer
  sibling: `AnalysisEngine.analyze(text) -> DocumentAnalysis` (tree, tokens, `ParseErrorInfo`),
  with `highlight()` demoted to a thin delegating wrapper — round-1 callers untouched.
- `plumbing.parse_text` gained `ParseResult.error_pos: int | None` (populated from
  `error_tracker.longest_parse_len`, or `result.pos` on early-success-without-full-consumption,
  or `0`; `None` only for an unknown start rule) — additive, defaulted, no existing caller
  changes.
- The engine's docstring assigns wall-clock/runaway-parse enforcement to "the long-lived
  server layer"; the server can only partially discharge that (Python threads aren't
  preemptible) — recorded as `TODO(lsp-analysis-watchdog)`, not solved.
- Position encoding: negotiates `utf-32` (free — codepoints) or falls back to the
  LSP-mandated `utf-16`; `utf-8` deliberately unsupported. A private `positions.py:LineIndex`
  (recognizing all three LSP line separators `\n`/`\r\n`/`\r`, unlike
  `TerminalSource.pos_to_line_col`, which is `\n`-only) does all protocol position math.
- **pygls landed as `pygls>=2,<3`**, not the design's placeholder `pygls>=1.3,<2` — the design
  explicitly deferred the exact pin to implementation time ("verifies the current stable"),
  and pygls 2.x was current + required by `pytest-lsp` (the e2e test tool) at implementation
  time. It's an optional extra (`[project.optional-dependencies] lsp = ["pygls>=2,<3"]`); core
  `dependencies` are unaffected. `fltk-lsp` is always installed as a console script but imports
  pygls lazily, printing an actionable `pip install 'fltk[lsp]'` message on `ImportError`.
- Formatting is registered **always** (not gated on `--fmt` being passed) — a
  `FormatterConfig()`-defaults mode is a first-class case of the existing pipeline, and
  render geometry comes from server-invocation `--width`/`--indent` flags (defaults 80/2,
  matching `fltk-unparse`'s CLI), with client `FormattingOptions` deliberately ignored so
  the same server invocation formats identically regardless of which client asked.

Deliverables: `positions.py` (`LineIndex`, `PositionEncoding`), `features.py` (pure
`(DocumentAnalysis, LineIndex, PositionEncoding) -> lsprotocol` functions: semantic-token
legend/encoding, folding, selection), `server.py` (pygls wiring: `FltkLanguageServer`,
single-worker `ThreadPoolExecutor`, debounced `didChange`, stale-serving via `_GoodAnalysis`
snapshots, lazy memoized formatting pipeline with a verify-reparse guard), `server_cli.py`
(`fltk-lsp` CLI/startup validation).

### M4 (round 3, commit `46c17e5`) — defs/refs/namespace semantics

The ADR's ordering put M3 before M4; this round deliberately reordered them, because M3's
central factual question ("can the packrat parser yield a useful partial CST on failure at
all?") was still open and would need its own exploration of `fltk/fegen/pyrt/memo.py` first
(confirmed in this pass — see §2 below), whereas M4 was fully grounded in code that already
existed (`def`/`ref`/`namespace` already parsed, validated, and (for `def`) painted since
round 1). `step3/design.md` §2 records the deltas:

- **Namespace scoping is hoisted, deviating from the spec's literal wording.** The spec says
  "symbols defined in [a namespace rule's] subtree are visible only within it." Read
  literally, `rule cog { def identifier: type.cog; namespace; }` would trap the cog's own
  *name* inside its own scope — no reference elsewhere could ever resolve to it, breaking the
  spec's own worked example. Decision: a symbol whose `def` is anchored in a namespace rule is
  defined into the scope *enclosing* that rule's namespace node (construct name visible where
  the construct is used, à la every mainstream language's class-name-vs-members scoping);
  other symbols in the subtree belong to the namespace's own scope. Namespace-ness is a
  property of the rule, not any one block (multiple `rule X { }` blocks for one rule
  accumulate).
- **Ref-site paint needed a new `classify()` input.** Which kind a reference resolves to is
  document-dependent, so it can't be precomputed into `ResolvedLspConfig` the way scope/def
  paints are. `classify()` gained a keyword-only `symbol_table: SymbolTable | None = None`
  (defaults to `None`, so round-1/2 callers are byte-identical — pinned by regression tests).
  A resolved reference contributes one explicit-layer interval at `SOURCE_RANK_REF = 1`
  (`== SOURCE_RANK_DEF`, both below `SOURCE_RANK_SCOPE = 2`), reusing the existing depth/tier
  precedence machinery unchanged.
- **Qualified names (spec OQ1) degrade, not block.** `ns::Type`/`a.b.c` refs compare their
  whole span text against symbol names and simply don't resolve (no error, defaults paint the
  span). A `qualified ref` form is deferred to whatever round designs the M5 resolver.
- **Two features added beyond the ADR's M4 list**: `documentHighlight` and `prepareRename`,
  both near-zero-marginal-cost over the same occurrence query find-references already needs.
- **Rename gets a stricter safety policy than every other (read-only, stale-tolerant) feature**:
  refuses to run against a stale analysis; applies edits in-memory and reparses
  (verify-reparse, mirroring the formatter's guard) before returning; returns versioned
  `documentChanges` when the client supports it (closing a race where a `didChange` lands
  between the handler's two worker awaits), else falls back to plain `changes` for clients
  without that capability (residual race, undocumented-away by LSP itself).

Deliverables: `symbols.py` (new — `Symbol`, `Reference`, `Scope`, `SymbolTable`, `extract()`);
`lsp_config.py` gained `DefMatcher`/`RefMatcher`, `ResolvedLspConfig.def_matchers` /
`ref_matchers` / `namespace_rules`, and the child-match predicate `match_applies` moved here
from `classify._matches` (now shared by both `symbols.py` and `classify.py`); `classify.py`'s
`_GrammarTables`/`_rule_for_node` promoted to public `GrammarTables`/`rule_for_node`;
`engine.py`'s `DocumentAnalysis` gained `symbols: SymbolTable | None = None`; `features.py`
gained `SYMBOL_KINDS` + pure translation functions for all six new features; `server.py`
gained six new handlers plus the rename policy.

## 2. M3 (prefix-CST exposure) — status: not started; the factual groundwork now verified

M3 was skipped in both M2 and M4 and remains fully unstarted. It is still in the ADR's scope
(step2/step3 both explicitly defer it, not drop it). This pass independently verified the
central open question from `step2/design.md`/`step3/exploration.md` — whether a partial CST is
obtainable from the parser machinery on a failed parse — by reading the packrat internals
directly on both backends:

- **Python** (`fltk/fegen/pyrt/memo.py`): `Packrat.apply()` returns `ApplyResult[pos, result]
  | None`. Any rule invocation that fails (its `rule_callable` returns `None` from deep in a
  sequence/alternation) returns `None` all the way up the call stack — `ApplyResult` has no
  concept of "the longest successful sub-parse we found along the way." The `rule_cache`
  (`MemoEntry` per `(rule_id, pos)`) *does* retain successful sub-parse results for
  individual rules that succeeded at various positions during the attempt, but nothing walks
  or collects that cache into a usable partial tree, and the cache is local to one `Packrat`
  instance, discarded with the parser object. `fltk/plumbing.py:parse_text` (`:170-208`)
  checks `if not result or result.pos != len(terminals.terminals)` — the only currently
  distinguished case besides hard failure is *early success without full consumption*
  (the top-level start rule matched and returned a real CST, but didn't consume the whole
  input) — a fundamentally different situation from "a syntax error partway through, want the
  successfully-parsed prefix as a tree." No code path extracts the latter today.
- **Rust** (`crates/fltk-parser-core/src/memo.rs`): explicitly documented as "a port of
  `memo.py`" with the same `ApplyResult<T> { pos, result }` shape and the same
  poison/recursion bookkeeping (structurally reorganized for Rust ownership, "observably
  equivalent" per its own doc comment). Same absence of partial-tree extraction.
- **Rust's analogous discard point**: `crates/fltk-fmt-cli/src/lib.rs:88`,
  `pub fn fully_consumed(src: &str, pos: i64) -> bool` — a pure boolean gate on parsed
  length vs. source length, used identically by the `fltk_formatter_main!` macro
  (`:316-369`) and its CLI plumbing: `parser.$parse(0)` → `None` ⇒ `Err(error_message())` →
  `fully_consumed` check ⇒ a partial parse is treated as a hard error, exactly like the Python
  `parse_text` path. No partial-tree extraction exists on this side either.

Net: the ADR's framing ("expose the successfully-parsed prefix CST that
`plumbing.parse_text`/`fully_consumed()` currently discard") accurately describes a *discard
point* that exists identically on both backends, but this pass — like step2's and step3's —
did not find (and did not find evidence ruling out) a way to obtain a "useful" partial CST
from the current packrat machinery without new engineering: the memo cache holds fragments,
not an assembled tree, and nothing today walks it. A definitive yes/no on what's cheaply
achievable (e.g., "take the memo cache's entry with the largest `final_pos` at the outermost
rule that was attempted" vs. some more principled partial-tree assembly) was not attempted in
this pass and would be exploratory work for whichever round picks up M3 — `step3/exploration.md`
flagged the same gap ("would require reading the packrat/memo internals... in more depth").

What M3 would need to touch, per the step1/step2 designs (still accurate against current code):

- `AnalysisEngine.analyze()` (`fltk/lsp/engine.py:130-170`) — currently on any parse failure
  returns `tree=None, tokens=None, symbols=None`. M3 changes only this method's failure branch
  (`step1/design.md:480-481`: "purely a change inside `highlight()`'s parse step"); `classify`
  and `symbols.extract` already operate on any subtree passed to them, so nothing downstream
  needs to change once a partial tree exists.
- `plumbing.parse_text`/`ParseResult` (`fltk/plumbing.py:170-208`,
  `fltk/plumbing_types.py:26-36`) — `ParseResult.error_pos` (added in M2) is "the first half of
  the surface M3 needs" per `step2/design.md:555-556`; a partial tree would be the second
  field. Whether that requires a new `ParseResult.partial_cst`-shaped field, a change to
  `parse_text`'s signature, or lower-level packrat API surface is unresolved.
- The server's stale-token policy (`fltk/lsp/server.py`, `_GoodAnalysis`/`_serveable`) is
  explicitly built to become "stale-past-the-error" with no protocol-layer changes once a
  partial tree exists (`step2/design.md:557-558`) — the seam is already shaped for this.
- Both backends need the same treatment for cross-backend parity to hold (the project's
  stated compatibility bar), so M3 is not a Python-only change even though the current
  server is Python-only; the `fully_consumed`/CLI formatter path on the Rust side does the
  same discard and is a second site to reconcile if Rust-side prefix behavior ever matters
  (e.g., for a future native fast path per M5).

## 3. FLTK plumbing/parser/CST/span seams the LSP code depends on

- **`fltk/plumbing.py`** (441 lines) is the seam nearly everything in `fltk/lsp/` sits on:
  - `parse_grammar`/`parse_grammar_file` (`:37-88`) — `.fltkg` text/file → `gsm.Grammar`,
    raising `ValueError` on failure.
  - `generate_parser(grammar, *, capture_trivia=True) -> ParserResult` (`:91-167`) — execs a
    freshly-generated Python CST module + parser class **in memory**, registered under
    `sys.modules[f"fltk_grammar_{id(grammar)}"]` only after success. No `rust_cst_module=`
    parameter exists (confirmed; the ADR D4 citation of one does not exist in code — this was
    already corrected in `step1/design.md` §2.3 and reconfirmed here). `AnalysisEngine`
    calls this on `prepare_analysis_grammar(grammar)`; the server's lazy formatting pipeline
    calls it on `engine.source_grammar` (the *original*, pre-analysis-transform grammar,
    because analysis CSTs contain suppressed terminals the generated unparser doesn't expect)
    — the server therefore holds two parser instances simultaneously.
  - `parse_text(parser_result, text, rule_name=None) -> ParseResult` (`:170-208`) — the parse
    entry point every `.fltklsp`-driven engine and the formatter's verify-reparse guard use.
    On failure populates `error_pos` (`:199-205`); the no-such-rule early return
    (`:189`) leaves `error_pos` at its default `None`.
  - `parse_lsp_config`/`parse_lsp_config_file` (`:265-304`) — thin wrappers around
    `lsp_config.load_lsp_config`, mirroring `parse_format_config[_file]` (`:211-262`).
  - `generate_unparser`/`generate_unparser_source`/`unparse_cst`/`render_doc`
    (`:307-441`) — the formatting pipeline the server's lazy `_ensure_format_pipeline` /
    `_format_blocking` call: `parse_text` (standard parser) → `unparse_cst` → `render_doc`
    → verify-reparse.
- **`ParseResult`** (`fltk/plumbing_types.py:25-36`): `cst: Any | None`, `terminals: str`,
  `success: bool`, `error_message: str | None`, `error_pos: int | None` (M2 addition,
  defaulted). `ParserResult` (`:14-22`) carries `parser_class`, `cst_module`,
  `cst_module_name`, `grammar` (the trivia-classified grammar actually used to generate,
  **not** necessarily the caller's original — `AnalysisEngine` keeps its own copy of the
  pre-transform grammar separately as `source_grammar` for exactly this reason), and
  `capture_trivia`.
- **`SpanProtocol`** (`fltk/fegen/pyrt/span_protocol.py`): a `runtime_checkable` Protocol
  exposing `start`/`end` (codepoint indices), `kind` (`SpanKind.SPAN` discriminant used
  throughout `fltk/lsp/` to tell terminal-span children from node children during tree walks),
  `text()`/`text_or_raise()`, `merge`/`intersect`, `line_col()`. Both backends (pure-Python
  `terminalsrc.Span` and, if present, `fltk._native.Span`) satisfy it structurally, but the LSP
  code stays codepoint-only end-to-end and does its own UTF-16 conversion at the protocol edge
  (`positions.py:LineIndex`) rather than relying on `line_col()` for anything protocol-facing
  (`line_col()`/`TerminalSource.pos_to_line_col` are `\n`-only; LSP needs all three separators).
- **`fltk/fegen/pyrt/errors.py`**: `ErrorTracker` (`longest_parse_len`,
  `expected_context: list[ParseContext]`) and `format_error_message(...)` — the single
  rendering path every parse-failure message in this codebase (grammar, `.fltklsp`, and
  target-language parses) shares; `ParseErrorInfo.offset` in `engine.py` is
  `error_tracker.longest_parse_len` surfaced through `ParseResult.error_pos`.
  `expected_context` itself is not yet consumed anywhere in `fltk/lsp/` — `step2/design.md`
  §7 notes it as the natural seam for both terser diagnostics and future keyword-completion,
  neither built yet.
- **Trivia classification**: `gsm.classify_trivia_rules`/`gsm.add_trivia_rule_to_grammar`
  set/synthesize `Rule.is_trivia_rule`, consumed directly by `classify.py`'s default-comment
  rule and by `engine.py`'s `trivia_kind_names` property (used for `FoldingRangeKind.Comment`).
  Grammars with no `_trivia` rule at all (clockwork) get a synthesized whitespace-only trivia
  rule; `classify.py`'s trivia-handling explicitly special-cases whitespace-only trivia nodes
  to emit no token (otherwise every synthesized trivia match would paint useless `comment`
  tokens over plain whitespace).
- **Native/Rust path**: confirmed absent as an in-process option. `fltk.fegen.genparser`
  subcommands (`gen-rust-cst`, `gen-rust-parser`, `gen-rust-unparser`) are offline codegen
  only, each writing a `.rs` file the consumer's own Cargo/maturin build compiles into a
  separate cdylib. Nothing in `fltk/lsp/` or `fltk/plumbing.py` loads a compiled pyo3 module
  for a given grammar; `AnalysisEngine.__init__` unconditionally builds its parser via
  `plumbing.generate_parser(prepare_analysis_grammar(grammar))` (pure Python, always).

## 4. Rough edges, inconsistencies, and foundation gaps recorded for the next round

All of the following are open, currently-tracked items — either an explicit `TODO(slug)` in
code + `TODO.md`, or a design-doc-recorded deviation. None are new findings beyond what's
already recorded in the repo; this section collects them in one place for a next-round
designer, re-verified against current code (all grep hits below are live at HEAD).

- **`TODO(lsp-classify-hotpath)`** (`fltk/lsp/classify.py:310`, `:416`; `TODO.md`) — two
  confirmed inefficiencies in the per-document hot path the server's `didChange`/pull handlers
  drive: `_winner_segments` rescans all intervals per boundary pair (O(n²); a sweep-line
  maintaining an active set would be O(n log n)), and `classify()` walks the analysis tree
  twice (`_explicit_intervals` then `_default_intervals`) rather than fusing default emission
  into the explicit walk. M4 added a third O(tree) walk (`symbols.extract`) to the same
  per-analysis cost, noted in the TODO as part of the same planned unification, not a new
  entry. Table-building itself is already hoisted to once-per-engine
  (`AnalysisEngine.__init__` builds `_tables` once and threads it through), so this TODO is
  specifically about the per-call walks, not per-call table rebuilding.
- **`TODO(lsp-rule-surface-index)`** (`lsp_config.py:280`, `classify.py:74`) —
  `lsp_config._index_rule` (`RuleIndex`: labels/literals/invoked_rules) and
  `classify._build_terminal_table` (`_TerminalTable`: literals/regexes, label-keyed) are two
  parallel per-rule walks over the same `rule.alternatives` × `gsm.for_each_item` structure,
  each collecting an overlapping slice of "what a rule's items expose." Deferred rather than
  unified now because the planned `INLINE` support (splicing invoked rules' terminals into the
  parent surface, needed before any `!`-bearing grammar can be an analysis-engine target) is
  what would force both walks to change simultaneously; landing the unification separately
  risks doing it twice.
- **`TODO(lsp-analysis-watchdog)`** (`server.py:187`) — the single-worker
  `ThreadPoolExecutor` has no wall-clock or cancellation bound on a runaway analysis
  (catastrophic regex backtracking, non-terminating recursion below the interpreter's
  recursion-limit floor). `RecursionError` specifically *is* caught and reported as a normal
  diagnostic; anything that doesn't hit that limit starves every later analysis on that server
  process (protocol loop itself stays responsive — it's never blocked on the worker — but
  that document and every document analyzed after it stops updating). Fix would need process
  isolation or a parser-level step/time budget; recorded as real design work, not attempted.
- **`TODO(lsp-start-rule-dedup)`** (`server.py:140`) — `start_rule` is threaded as a
  `create_server`/`FltkLanguageServer` constructor parameter *and* separately stored inside
  `AnalysisEngine` (`self._start_rule`); nothing ties the two together except the CLI passing
  the same variable twice, so a second `create_server` caller (e.g. a test, or a future
  embedding) could pass a mismatched pair with no error. Fix (exposing a read-only
  `AnalysisEngine.start_rule` property and reading it in the server, dropping the parameter)
  is deferred because it's a `create_server` signature change — a deliberate surface decision
  per the note, not a drive-by fix.
- **`TODO(lsp-cst-text-helpers)`** (`lsp_config.py:118`) — `lsp_config._span_text`/
  `_identifier_text` and the inline literal-extraction in `_parse_anchor` duplicate near-
  identical helpers in `fmt_config.py` (`_span_text`, `_extract_identifier_text`,
  `_extract_literal_text`), a more careful guarded version in `unparse/pyrt.py`
  (`extract_span_text`, which guards against a source-bearing span whose `text()` returns
  `None` — a guard the `fmt_config`/`lsp_config` copies both lack), and a fourth copy in
  `fltk2gsm.py` (`Cst2Gsm._span_text`). Four near-duplicate implementations across the
  codebase; consolidation deferred because it touches modules outside any one round's scope.
- **Def/ref/namespace validation gaps recorded as deliberate, not bugs**: `def`/`ref` kind
  vocabulary is intentionally unvalidated (open vocabulary — any dotted name is accepted;
  `lsp_config.py` rule 7 in the validation table). Unresolved references are silent by design
  (no diagnostic) since cross-file imports are the *normal* source of unresolved references
  until M5's resolver exists — diagnosing them now would be sustained false-positive noise
  (`step3/design.md` §5).
- **Known parse-level grammar quirk** (documented, not a bug to fix): an anchor literally
  named `label` or `rule` written flush against a colon (`scope label:comment;`) fails to
  parse, because the optional `qualifier` group in `fltklsp.fltkg` commits once it consumes
  `label:` (PEG `e?` doesn't backtrack after succeeding) — `scope label : comment;` (space
  before the colon) works. Pinned by tests in both directions; the failure mode is always a
  visible parse error, never silent misclassification.
- **Formatter idempotency bug, shared infrastructure, not LSP-specific**:
  `TODO(formatter-group-idempotency)` (`TODO.md`) — the formatter is not idempotent on grouped
  alternations at narrow render widths (a shared unparser/renderer bug affecting both Python
  and Rust backends identically). The LSP server's `_format_blocking` verify-reparse guard
  checks that rendered output *re-parses*, not that formatting is idempotent or preserves
  meaning, so this bug is not caught by the server's existing safety net; it would only matter
  to a next round if idempotent-formatting were made a server guarantee.
- **`fltk-lsp`'s wall-clock promise is only partially true today** (documented limitation,
  not tracked as a bug beyond the watchdog TODO above): `engine.analyze`'s own docstring
  assigns runaway-parse bounding to "the long-lived server layer," but the server can only
  serialize-and-stay-protocol-responsive, not actually bound or cancel a stuck worker-thread
  parse (Python threads aren't preemptible).
- **`fltk-highlight`/`fltk-lsp` packaging is genuinely new public surface**, per CLAUDE.md's
  out-of-tree-consumer rules: the project's *first* two `[project.scripts]` console-script
  entries and its first `[project.optional-dependencies]` extra. Both were explicit,
  called-out user decisions in the step1/step2 designs, not incidental.
- **Dogfood fixture stability note**: `fltk/lsp/fltklsp.fltklsp` (the `.fltklsp` spec for the
  `.fltklsp` language itself) intentionally contains only `scope` statements — no
  `def`/`ref`/`namespace` — because M4's own design doc records that "what a good symbol
  vocabulary for the `.fltklsp` language itself looks like... is its own design decision, not
  a test-time improvisation on a public example file." `test_dogfood.py`'s M4 semantics test
  instead uses a test-local spec. A next round designing anything user-facing about the
  `.fltklsp` language's own tooling should know this fixture was deliberately left
  highlighting-only.

## 5. Test and file inventory (current, for orientation)

`fltk/lsp/` (non-test, non-generated `.py` sizes as of this pass): `classify.py` 423 lines,
`engine.py` 183, `features.py` 441, `lsp_config.py` 744, `positions.py` 119, `server.py` 680,
`server_cli.py` 71, `symbols.py` 296, `analysis.py` 81, `highlight_cli.py` 117. Generated +
committed: `fltklsp_cst.py` (~2400 lines), `fltklsp_cst_protocol.py` (~1030),
`fltklsp_parser.py` (~1380), `fltklsp_trivia_parser.py` (~1410). Test suite: ~20 `test_*.py`
modules colocated per-module under `fltk/lsp/`, plus `fltk/lsp/test_data/` (the `greet.*`
fixture language: grammar + `.fltklsp` + `.fltkfmt` triple, extended in M4 with
definition/usage/module constructs for def/ref/namespace coverage) and `fltk/lsp/conftest.py`
(a small `HELLO_GRAMMAR`/`HELLO_LSP` fixture + shared helpers). `pyproject.toml`: `lsp` extra
(`pygls>=2,<3`), `pytest-lsp` in the `test` dependency group, two console scripts
(`fltk-highlight`, `fltk-lsp`).
