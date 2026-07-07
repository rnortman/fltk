# Judge verdict — design review (round 2 design, `fltk-lsp` M2)

Phase: design. Doc: `docs/adr/2026/07/06-fltklsp-lsp-server/step2/design.md`. Round 1.
Notes: `step2/notes-design-design-reviewer.md` (5 findings). Dispositions: `step2/dispositions-design.md`.

## Other findings walk

All five findings dispositioned Fixed. Each verified against the current design text and,
where the fix rests on code facts, against source.

### design-1 — Fixed (render geometry / `RendererConfig` never constructed)
Claim: design's ".fltkfmt is the formatting policy" rationale is false — `RendererConfig`
(indent 4, width 80 defaults) is the actual geometry owner and the design never constructs
it; consequence is format-on-save output diverging from `fltk-unparse` (default indent 2)
for every downstream language, with no knob.
Code facts verified: `fltk/unparse/renderer.py:22-26` defaults `indent_width=4, max_width=80`;
`fltk/unparse_cli.py:37-38, 125` exposes `--width` (80) / `--indent` (2) and builds
`RendererConfig` explicitly; `fmt_config.py` carries only a per-nest `indent` override
(line 118), no global width/indent — reviewer's premise holds.
Design now: new §2.7 records the decision; CLI usage (§1, §4.1) gains `--width`/`--indent`
with `fltk-unparse`'s defaults (80/2) so editor and CLI/CI output agree out of the box;
§4.7 `create_server(..., renderer_config, ...)` carries it; §4.8 step 2 passes
`render_doc(doc, renderer_config)`; §6 tests that formatted output honors the flags and
matches `fltk-unparse` for the same flags. The false rationale is replaced: client
`FormattingOptions` remain ignored, but now for a stated, correct reason (per-client
`tab_size` would make output editor-dependent, defeating cross-client/CI determinism),
recorded as a challengeable decision in §2.7 and §8.
Owner-lens note: the reviewer floated mapping `tab_size` to `indent_width` as one option;
the design chose the flags-only route with a sound determinism rationale and called it
out for challenge — a deliberate decision, not an evasion. Assessment: fix complete. Accept.

### design-2 — Fixed (`--rule` not validated at startup)
Claim: `AnalysisEngine.from_paths` stores the rule unchecked; a typo'd `--rule` yields a
position-less "No parse method" diagnostic on every document, contradicting §4.1/§5
fail-fast.
Code facts verified: `engine.py` `__init__` does `self._start_rule = start_rule` with no
check; `plumbing.py` no-such-rule path returns a `ParseResult` the design's §4.4
deliberately leaves `error_pos=None`.
Design now: §4.1 startup step 3 validates `--rule` against the grammar's rule names
(one check covers both parsers since the analysis transform preserves names); unknown
rule → stderr listing valid rules, exit 1. §6 `test_server_cli.py` adds the
unknown-`--rule` case with the valid-rule listing asserted. Assessment: fix complete,
matches the reviewer's suggested fix exactly. Accept.

### design-3 — Fixed (encoding-negotiation ownership unresolved)
Claim: design specified both its own encoding picker and delegation to pygls's negotiator
(whose supported set includes utf-8, which `LineIndex` doesn't implement) with no stated
arbiter; divergence silently corrupts every position on non-ASCII lines.
Design now: §4.5 names one owner — constrain pygls's supported set to {utf-32, utf-16} if
its API permits, otherwise set `ServerCapabilities.position_encoding` explicitly from the
server's picker, overriding pygls; in **both** branches the server reads the *advertised*
capability value back and derives `PositionEncoding` from that single variable, feeding
`LineIndex`, token encoding, and every emitted `Range`. §6 `test_server.py` pins
advertised-encoding/token-encoding agreement, including a client offering utf-8 first.
The "if its API permits" branch is not a residual ambiguity: the invariant (advertised
value is the single source, never utf-8) holds on either branch and is test-pinned.
Assessment: fix complete. Accept.

### design-4 — Fixed (`grammar_tables` property exposed private `_GrammarTables`)
Claim: publishing the underscore-private `_GrammarTables` as engine API right before its
planned restructuring (`TODO(lsp-rule-surface-index)`) creates the annotation-churn
pattern CLAUDE.md forbids, when folding needs one bit per kind.
Code facts verified: `_GrammarTables` is underscore-private with `kind_to_rule`
(`classify.py:64-68`); `TODO(lsp-rule-surface-index)` at `classify.py:72-73` plans to
unify exactly this structure.
Design now: §4.3 exposes `trivia_kind_names: frozenset[str]`, derived once in `__init__`
from `self._tables.kind_to_rule` filtering `rule.is_trivia_rule`; `_GrammarTables` stays
private; §4.6 `folding_ranges(tree, trivia_kind_names, line_index)` and the §3 file-table
row updated consistently (no `grammar_tables` remains anywhere in the doc). Assessment:
fix complete, matches the reviewer's suggested narrow-query shape. Accept.

### design-5 — Fixed (formatting failure handling: `ValueError`-only + unspecified build failure)
Claim: (a) the c0534e3 unparser-bug family can raise `KeyError`/`AttributeError`/`TypeError`
from exec'd generated code, escaping the `ValueError`-only catch as a raw LSP request
error; (b) the memoized lazy build had no failure disposition (permanently-dead vs.
codegen-retry-per-keystroke), so §5's "formatter failure of any kind" overclaimed.
Design now: §4.8 specifies memoized-as-failed — exception caught, logged once in full via
`window/logMessage`, subsequent requests return `None` immediately with a one-line log,
recovery is restart (inputs fixed at startup, so retry cannot succeed — sound reasoning);
build + steps 2–3 wrapped in `catch Exception`, with the c0534e3 rationale stated inline;
§5's claim now matches the spec; §6 adds the build-failure case including no-rebuild on
the second request. Assessment: fix complete. Accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified, 0 Won't-Do, 0 TODOs.

---

## Verdict: APPROVED

All five fixes are present in the design, internally consistent (§1/§2.7/§3/§4/§5/§6/§8
all updated coherently, no stale references to the pre-fix text), and each rests on code
facts that check out against source.
