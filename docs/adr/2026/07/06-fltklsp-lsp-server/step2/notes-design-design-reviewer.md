# Design review findings — round 2 (`fltk-lsp` pygls server, M2)

Reviewed: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/design.md` against code at
dd442340/a17ba80 and `step2/exploration.md`.

Verified clean (spot list, not exhaustive): `HighlightResult` shape and `highlight` body
(`engine.py:26-36, 77-98`); the wall-clock docstring (`engine.py:83-88`); `parse_text`
discard path and `ParseResult` fields (`plumbing.py:193-199`, `plumbing_types.py:26-32`);
`longest_parse_len` is a codepoint offset (`errors.py:131`, `terminalsrc.py:248-261`);
`\n`-only line math in `terminalsrc.py:271` and `Span.line_col` (`terminalsrc.py:133`);
`TOKEN_LEGEND` = 16 members, `LSP_STANDARD_MODIFIERS` = 10, both frozensets
(`lsp_config.py:27-64`); classifier modifiers ⊆ standard set (`lsp_config.py:167-168, 627`);
sorted/non-overlapping token invariant (`classify.py:212-213, 378-379`); the four
non-LSP-predefined legend members (`punctuation`, `text`, `constant`, `label`) are indeed
not in the LSP 3.17 predefined set; engine does not currently retain the pre-transform
grammar (`engine.py:47-57`), so the `source_grammar` one-line claim is accurate;
`formatter_config or FormatterConfig()` (`plumbing.py:311`); "Unparsing failed" `None`
path (`plumbing.py:415-417`); `pyproject.toml:25` deps, `:27-28` scripts, `:42-45` test
group; `highlight_cli.py:99-111` error style; `kind == SpanKind.SPAN` node/span
discrimination and `kind_to_rule` keying (`classify.py:101-111, 192, 269`); step1
two-parser delta (`step1/design.md:478`); ADR M2 list (`README.md:107-108`); Bazel
`glob(["**/*.py"])` means new modules need no BUILD change (`BUILD.bazel:26`).

## design-1: §4.8 formatting — `RendererConfig` (indent/width) is never constructed, and the "policy comes from `.fltkfmt`" rationale is wrong for those knobs

Quote: "Handler, per request (client `FormattingOptions` — tab size etc. — are ignored;
formatting policy comes from `.fltkfmt`, which is the whole point of the pipeline)" and
step 2: "`unparse_cst` → `render_doc`."

What's wrong: `render_doc(doc, config=None)` defaults to `RendererConfig()` — hardcoded
`indent_width=4`, `max_width=80` (`fltk/unparse/renderer.py:22-26`,
`fltk/plumbing.py:422-433`). `FormatterConfig` / `.fltkfmt` carries no width or indent
setting at all (grep for `width` in `fltk/unparse/fmt_config.py` returns nothing), so the
stated rationale — that `.fltkfmt` is the source of formatting policy, making
`FormattingOptions` ignorable — is factually false for the two most user-visible
formatting knobs. The existing in-tree formatting flow treats these as caller-supplied:
`unparse_cli.py:37-38, 125` exposes `--width` (default 80) and `--indent` (default **2**)
and builds `RendererConfig(max_width=width, indent_width=indent)` explicitly. The design
never mentions `RendererConfig` anywhere.

Consequence: `fltk-lsp` formats every language with an unconfigurable indent of 4 and
width of 80. A downstream language whose users format with `fltk-unparse` (default indent
2, or any explicit `--width/--indent`) gets *different output* from editor format-on-save
than from their CLI/CI formatter — formatting churn on every save for out-of-tree
consumers, with no flag to fix it. The client's `FormattingOptions.tab_size` — the one
place LSP actually supplies an indent preference — is discarded on an incorrect premise.

Suggested fix: construct `RendererConfig` explicitly in the handler and decide its inputs
deliberately — e.g. `--width`/`--indent` CLI flags mirroring `fltk-unparse`, and/or map
`FormattingOptions.tab_size` to `indent_width`. At minimum, correct the rationale and
record the hardcoded-defaults choice as a called-out decision like §2.5/§2.6.

## design-2: §4.1 startup does not validate `--rule`, contradicting the fail-fast promise

Quote: §4.1: "Startup sequence, fail-fast, before any protocol I/O"; §5: "never a running
server that half-works."

What's wrong: `AnalysisEngine.from_paths(..., start_rule=rule)` stores the rule name
without checking it (`engine.py:47-57`); a nonexistent rule surfaces only at the first
`parse_text` as the no-such-rule `ParseResult` (`plumbing.py:187-189`), which §4.4
deliberately leaves `error_pos=None`. So per §4.7 every document in the workspace gets a
zero-length `Diagnostic` at 0,0 reading "No parse method for rule 'X'" — a running server
that half-works, which is exactly what §4.1/§5 promise cannot happen for the *other three*
CLI inputs (`--grammar`, `--lsp`, `--fmt` are all validated at startup).

Consequence: the most common misconfiguration a downstream editor-config author can make
(typo'd start rule) produces the worst diagnostic experience the design has (cryptic
position-less error on every file) instead of a stderr startup failure, and is
inconsistent with the design's own stated failure-mode policy.

Suggested fix: at startup step 2, check the rule name against the engine grammar's rule
names (analysis transform preserves rule names, so one check covers the formatting parser
too); exit 1 with a message listing valid rules.

## design-3: §4.5 encoding negotiation — who owns the advertised `position_encoding` is unresolved, and pygls's own negotiation may pick an encoding `LineIndex` cannot produce

Quote: "read the client's `general.positionEncodings` from `InitializeParams`; pick
`utf-32` if offered, else `utf-16`; advertise the choice in
`ServerCapabilities.position_encoding`. pygls ≥1.1 ships its own negotiation/codec
machinery; use it for the capability handshake where it fits."

What's wrong: pygls is not in the repo or venv (`ModuleNotFoundError`), so this is an
unverified integration claim — and it is load-bearing. pygls 1.x builds
`ServerCapabilities` itself (its capabilities builder negotiates `position_encoding` from
client capabilities against pygls's *own* supported set, which includes utf-8) and wires
the result into its `Workspace` position codec. The design specifies its own picker
(utf-32-else-utf-16, utf-8 deliberately unimplemented) *and* delegation to pygls "where it
fits", without stating which one determines the value the client actually sees, or what
happens if pygls negotiates utf-8 for a client that offers it first. Two decision-makers
computing the same value independently is exactly the coordinate-mixing class of bug
§4.7's `_GoodAnalysis` is designed to rule out.

Consequence: if the advertised encoding and the `PositionEncoding` fed to `LineIndex`
diverge (e.g. pygls advertises utf-8, or advertises utf-16 while the server computes in
utf-32), every position, range, token delta, and text edit is wrong on any line containing
non-ASCII text — silently, for exactly the clients the negotiation feature exists to serve.

Suggested fix: make one owner explicit in the design: either constrain pygls's
supported-encodings set to {utf-32, utf-16} and read the negotiated result back from pygls
as the single source of truth, or bypass pygls's negotiation entirely and set the
capability from the design's own picker — and add a `test_server.py` case pinning that the
advertised encoding matches the encoding the emitted tokens are computed in (the current
test plan checks negotiation and token encoding separately, not their agreement).

## design-4: §4.3 `grammar_tables` property publicly exposes the private `_GrammarTables` type

Quote: "`grammar_tables` — the engine's precomputed `classify.build_grammar_tables` output
(`self._tables`, currently private)."

What's wrong: `build_grammar_tables` returns `_GrammarTables`, an underscore-private
dataclass (`classify.py:63-68`), and its two current consumers are private call paths. A
public read-only engine property whose type is unnameable-by-convention becomes API that
out-of-tree server/tooling authors (the module's stated audience) will type against — and
`TODO(lsp-rule-surface-index)` (`classify.py:72`, `lsp_config.py:280`) already plans to
restructure exactly this table into a unified rule-surface index. Folding needs only "is
this kind a trivia rule" (`kind_to_rule` → `rule.is_trivia_rule`).

Consequence: freezing an internal structure into public engine surface immediately before
its planned redesign creates the annotation-churn / breaking-change situation CLAUDE.md
tells us to avoid, for a consumer (folding) that needs one bit of it.

Suggested fix: expose the narrow query instead — e.g. `AnalysisEngine.is_trivia_kind(kind_name: str) -> bool`
or a `trivia_kind_names: frozenset[str]` property — keeping `_GrammarTables` private.

## design-5: §4.8 formatting failure handling covers `ValueError` only; the lazy pipeline build has no specified failure mode

Quote: "Any `ValueError` (including the unparser's 'Unparsing failed' `None` path,
`plumbing.py:415-417`) → log, return `None`" and "Built on first `textDocument/formatting`
request and memoized on the server."

What's wrong: two unhandled paths. (a) The design's own §4.8 motivation cites the
silent-`None` unparser-bug family (c0534e3); bugs of that family in generated unparsers
are not confined to `ValueError` — a malformed generated method can equally raise
`KeyError`/`AttributeError`/`TypeError`, which the handler as specified does not catch, so
they propagate out of the request handler. (b) The memoized lazy build itself
(`generate_parser` + `generate_unparser`, both exec-based codegen that can raise) has no
specified failure disposition: is a failed build memoized (formatting permanently dead
with no operator signal beyond one traceback) or rebuilt per request (a multi-second
codegen retry on every format keystroke)? §5's "Formatter failure of any kind → no edits,
logged" claims broader coverage than §4.8 actually specifies.

Consequence: the first formatter-generation or unparser bug a downstream grammar hits
bypasses the designed "log + return None" containment — the editor shows a raw LSP
request error (or silently retries expensive codegen), which is precisely the failure UX
the verify-reparse guard was added to prevent.

Suggested fix: catch `Exception` (not just `ValueError`) around build + format on the
worker, log, return `None`; state explicitly that a failed build is memoized-as-failed (or
retried) and add that case to `test_server.py`.
