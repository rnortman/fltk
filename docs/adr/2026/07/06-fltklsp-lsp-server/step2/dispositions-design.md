# Dispositions — round-2 design review findings

Design: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/design.md`
Findings: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/notes-design-design-reviewer.md`

All five findings were fact-checked against source and confirmed accurate.

design-1:
- Disposition: Fixed
- Action: New §2.7 records the render-geometry decision: `fltk-lsp` gains
  `--width`/`--indent` flags mirroring `fltk-unparse` (defaults 80/2 per
  `unparse_cli.py:37-38`, so editor and CLI/CI formatting agree out of the box) and
  builds an explicit `RendererConfig(max_width, indent_width)`. §4.8 handler now passes
  `render_doc(doc, renderer_config)`; §4.1 usage line and §4.7 `create_server` signature
  carry the config; §6 adds a test that formatted output honors the flags and matches
  `fltk-unparse` for the same flags. The false ".fltkfmt is the formatting policy"
  rationale is replaced: `FormattingOptions` remain ignored, but now for a stated,
  correct reason (per-client `tab_size` would make output editor-dependent, defeating
  determinism across clients and CI), recorded in §2.7 and §8 as a called-out decision.
- Severity assessment: Confirmed against `renderer.py:22-26` (defaults 4/80),
  `plumbing.py:422-433` (implicit default), and grep of `fmt_config.py` (no global
  width/indent). As designed, every downstream language would format with unconfigurable
  4-space indent while their CLI formatter defaults to 2 — churn on every format-on-save
  for out-of-tree consumers, with an incorrect rationale masking it.

design-2:
- Disposition: Fixed
- Action: §4.1 startup gains step 3: validate `--rule` against the grammar's rule names
  (analysis transform preserves names, so one check covers both parsers); unknown rule →
  stderr listing valid rules, exit 1. §6 `test_server_cli.py` adds the unknown-`--rule`
  case.
- Severity assessment: Confirmed: `engine.py:47-57` stores the rule unchecked and
  `plumbing.py:187-189` surfaces it only as the position-less no-such-rule
  `ParseResult`, which §4.4 deliberately leaves `error_pos=None`. A typo'd start rule —
  the likeliest operator misconfiguration — would produce a cryptic 0,0 diagnostic on
  every file, directly contradicting the design's own fail-fast/never-half-works policy.

design-3:
- Disposition: Fixed
- Action: §4.5 negotiation paragraph rewritten to name a single owner: constrain pygls's
  supported-encodings set to {utf-32, utf-16} if its API permits, otherwise set
  `ServerCapabilities.position_encoding` explicitly from the server's picker, overriding
  pygls; in both cases the server derives its `PositionEncoding` from the *advertised*
  capability value — one variable feeding `LineIndex`, token encoding, and every emitted
  `Range`. §6 `test_server.py` now pins advertised-encoding/token-encoding agreement,
  including a client offering utf-8 first.
- Severity assessment: pygls is not installed here, so its negotiation behavior is
  unverifiable in-repo — which is exactly the finding's point: the design left two
  independent decision-makers (pygls's negotiator, whose supported set includes utf-8,
  and the design's own picker) with no stated arbiter. Divergence would silently corrupt
  every position on non-ASCII lines for the clients negotiation exists to serve.

design-4:
- Disposition: Fixed
- Action: §4.3 replaces the `grammar_tables` property with
  `trivia_kind_names: frozenset[str]` (derived once in `__init__` from
  `self._tables.kind_to_rule` filtering `rule.is_trivia_rule`); `_GrammarTables` stays
  private. §4.6 `folding_ranges` and the §3 file-table row updated to match.
- Severity assessment: Confirmed: `_GrammarTables` is underscore-private
  (`classify.py:64-68`) and `TODO(lsp-rule-surface-index)` (`classify.py:72`) already
  plans to restructure it. Publishing it as engine API for a consumer that needs one
  boolean per kind would freeze an internal structure immediately before its planned
  redesign — the annotation-churn/breaking-change pattern CLAUDE.md forbids.

design-5:
- Disposition: Fixed
- Action: §4.8 now specifies (a) the lazy build's failure disposition:
  memoized-as-failed, logged in full once via `window/logMessage`, subsequent requests
  return `None` immediately with a one-line log (no codegen retry per keystroke;
  recovery is a restart since the inputs are fixed at startup); (b) build + steps 2–3
  wrapped in a catch of `Exception`, not just `ValueError`, since the c0534e3
  unparser-bug family can surface as `KeyError`/`AttributeError`/`TypeError` from
  generated code. §5's "formatter failure of any kind" claim now matches the spec.
  §6 `test_server.py` adds the build-failure case including no-rebuild on the second
  request.
- Severity assessment: Confirmed: the handler as previously specified caught only
  `ValueError`, so any other exception from exec'd generated code would escape as a raw
  LSP request error, and the memoized build had no defined failure mode — either
  silently-dead formatting or repeated multi-second codegen. Both bypass the containment
  the verify-reparse guard was added to provide.
