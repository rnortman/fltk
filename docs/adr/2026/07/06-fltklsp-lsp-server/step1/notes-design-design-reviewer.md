# Design review findings — round 1 `.fltklsp` design

Reviewed: `docs/adr/2026/07/06-fltklsp-lsp-server/workflow/design.md` at base a8fcc3d.
Advisory docs treated as directional only per requester ("NO DECISIONS HAVE BEEN MADE...").

Verification status of the design's factual corrections (§2): all four check out.
§2.1 confirmed at `fltk/fegen/fltk2gsm.py:113-122` (implicit labels for invocations;
unlabeled Literal/Regex default SUPPRESS) and `fltk/fegen/gsm2parser.py:848` (SUPPRESS
gates child emission). §2.2 confirmed — no GSM anchor validation anywhere in
`fmt_config.py`/`plumbing.parse_format_config` (`plumbing.py:203-231`). §2.3 confirmed —
`generate_parser(grammar, *, capture_trivia=True)` only (`plumbing.py:90-94`). §2.4's
factual basis confirmed (`fltk2gsm.py:114-115`). Also verified: `for_each_item`
(`gsm.py:291-302`), `add_trivia_rule_to_grammar` synthesizing whitespace-only trivia
(`gsm.py:477-504`), `node_kind_member_name` (`gsm2tree.py:95, 262-266`),
`SpanKind.SPAN` discriminant (`span_protocol.py:76-79`),
`format_source_line(span, message, *, filename)` (`error_formatter.py:67-120`),
empty-config short-circuit (`plumbing.py:215-216`), unparsefmt keyword style
(`unparsefmt.fltkg:40-56` uses `"after" : anchor`) and lexical tail (`:87-92`),
genparser gencode invocation shape (`Makefile` gencode target, unparsefmt step),
typer as existing runtime dep and absence of `[project.scripts]` (`pyproject.toml:25`,
no scripts table), and the `$"tag"` unlabeled-INCLUDE precedent being exercised on the
*Python* backend too (`tests/test_rust_parser_parity_fixture.py:33-37,76` runs
`plumbing.generate_parser` over `rust_parser_fixture.fltkg`, which includes `tagged`).
The `label:`-flush parse quirk (§4.1) traces correctly through the generated-parser
optional-item logic (`gsm2parser.py:841-864`: optional group success is committed, no
backtracking within the sequence).

## design-1: INLINE splicing machinery is designed against parser behavior that does not exist

Sections: §4.3 validation item 2 ("recursed ... through `INLINE`-disposition invocations —
see §4.5 on splicing"), §4.3 item 8 (warn for rules "invoked solely with `!` disposition"),
§4.5 ("terminal tables ... **include the terminals (and labels) of transitively `INLINE`d
rules**, since `!` splices their children into the parent node"), §6 ("their spliced
terminals classify correctly via the parent-rule terminal tables"), and §4.4's claim that
disposition affects "only CST construction, not matching (`gsm2parser.py:848` gates child
emission, nothing else)".

What's wrong: the Python runtime parser generator does not implement `!` at all.
`gsm2parser.py:828-830`:

```python
if item.disposition == gsm.Disposition.INLINE:
    msg = "Inline items not yet supported: {item}"
    raise NotImplementedError(msg)
```

The Rust generator likewise rejects it (`gsm2parser_rs.py:879-880, 1065-1066`). No TODO or
transform provides splicing anywhere in the `plumbing.generate_parser` path (only
sub-*expression* splicing via `inline_to_parent` exists, which is a different mechanism).
Only `gsm2tree.py:629-634` models INLINE — for CST class generation, which never runs to
completion for such a grammar because parser generation is part of the same
`generate_parser` call. So a target `.fltkg` containing `!` cannot be loaded by the round-1
engine at all: `AnalysisEngine.from_paths` would die inside `generate_parser` with a raw
`NotImplementedError`, before any of the designed INLINE handling could run. (`fltk.fltkg`,
the one in-tree grammar using `!alternatives`, is labeled "intentionally broken" in the
Makefile gencode comments.)

Consequence: the implementer is directed to build inline-aware terminal tables, an
inline-recursing anchor-validation path, and a "rule only ever inlined" load-time warn —
all unreachable dead code that cannot be tested (no test grammar with `!` can produce a
parser to classify against). §6's promised edge-case behavior ("spliced terminals classify
correctly") is unverifiable as specified and false in effect: the actual behavior for an
INLINE grammar is an unhandled crash with no diagnostic, which contradicts the design's own
error-reporting standards (§4.3, §4.8). §4.4's "nothing else" claim is also literally
falsified by `:828-830`.

Suggested fix: declare INLINE-bearing grammars unsupported in round 1, mirroring the parser
generators' reality — have the engine/loader surface a clean "grammar uses `!`, not
supported" error instead of the raw NotImplementedError — and delete the inline-splicing
recursion from §4.3/§4.5/§6, leaving a one-line roadmap note that inline handling must be
designed if/when `gsm2parser` gains INLINE support.

## design-2: The union-semantics compatibility rationale (§2.4) is inverted

Section: §2.4, "This is strictly more permissive, so it can be tightened later without
breaking existing files; the reverse would not be true."

What's wrong: the direction is backwards. Under union semantics, `.fltklsp` files with
unqualified ambiguous anchors are valid and have defined behavior; "tightening" to the
spec's error rule later would reject those previously-valid files — that is precisely a
breaking change under the project's own compatibility standard (CLAUDE.md: `.fltklsp`
files written by out-of-tree consumers are public-API surface; the design itself says so in
§1). The non-breaking evolution direction is the reverse: start strict, relax later.

The *substantive* argument for union semantics stands on its own and is verified: because
`fltk2gsm.py:114-115` gives every unlabeled rule invocation an implicit label equal to the
rule name, the spec's both-a-label-and-a-rule-name error would fire for essentially every
rule-name anchor, and the two readings coincide except under explicit relabeling. That is a
sufficient reason to replace the spec's rule.

Consequence: a future round (M4, or a post-adoption cleanup) could rely on the false "can
tighten later without breaking" claim and introduce the ambiguity error believing it is
safe, breaking downstream `.fltklsp` files. The freeze rationale for a public-API surface
should not contain an inverted compatibility argument.

Suggested fix: keep union semantics; replace the compatibility sentence with the real
rationale (ambiguity is the norm; readings coincide except under relabeling; a strict rule
would make the language unusable), and note explicitly that union semantics is itself a
commitment — tightening later would be a breaking change.

## design-3: Default-layer precedence among overlapping defaults is unspecified

Sections: §4.5 (defaults per CST occurrence: "Node of an `is_trivia_rule` rule → `comment`
over the whole node span" *and* "Terminal (span) children classify by provenance...") and
§4.6 layer 2 ("defaults ... emitted per terminal span / trivia node during the same walk
and simply filtered against explicit coverage"), versus §4.6's output invariants ("sorted
by `start`, non-overlapping").

What's wrong: the default layer can generate overlapping intervals of *different* token
types, and the design defines resolution only between the explicit and default layers
(painter rule 2), never *within* the default layer. Two concrete collisions in grammars the
round itself exercises:

1. Nested trivia nodes: in any fegen-family grammar — including the dogfood target
   `fltklsp.fltkg` itself (§4.1: `_trivia := ( line_comment | ... )+`,
   `line_comment := prefix:"//" . content:... . newline:"\n"`) — the trivia walk yields a
   `Trivia` node (is_trivia_rule) containing `LineComment` nodes (also is_trivia_rule),
   both of which the §4.5 rule paints `comment` over overlapping spans.
2. Terminals inside trivia nodes: `LineComment`'s children are spans with Literal/Regex
   provenance; per the §4.5 terminal table, the `"//"` prefix literal is not word-shaped
   and not in the punctuation set `( ) [ ] { } , ; : .`, so it defaults to `operator` —
   overlapping the enclosing node's `comment` paint with a different type. The spec's own
   painter rule 2 (`fltklsp-spec.md` §2.1: "the `\"//\"` literal inside doesn't repaint as
   punctuation") solves exactly this for *explicit* `scope doc: comment;`, but the design
   never states the analogous rule for the built-in trivia default.

Consequence: the token-stream invariant (non-overlapping) is unsatisfiable as specified, or
the implementer resolves the conflict by guesswork; the plausible wrong guess (terminal
defaults win, being emitted per-span during the same walk) paints `//` as `operator` inside
every comment. The §8 dogfood test (highlight a sample `.fltklsp` file) would hit this
immediately, since `.fltklsp` comments are structured trivia.

Suggested fix: one sentence in §4.5/§4.6 — e.g. "the default walk does not descend into
`is_trivia_rule` nodes: the outermost trivia node emits one `comment` interval and its
subtree contributes no further defaults" (explicit paints inside still apply per painter
rule 1). Add the `//`-inside-comment case to the §8 classify tests.

## design-4: Understated list of non-LSP-standard legend members (minor)

Section: §4.5, "(`punctuation`/`text` are not LSP-standard token types; ...)".

What's wrong: `constant` and `label` are also absent from LSP 3.17's predefined
`SemanticTokenTypes` (which contains namespace, type, class, enum, interface, struct,
typeParameter, parameter, variable, property, enumMember, event, function, method, macro,
keyword, modifier, comment, string, number, regexp, operator, decorator — no `constant`,
no `label`, and also no `none`, though `none` never reaches output by design). The
parenthetical implies exactly two custom registrations for M2.

Consequence: minor — the mitigation the design already states (legend is server-defined
strings; clients without a theme mapping just don't color them) applies identically to
`constant` and `label`, and `constant` matters in practice: the spec's worked clockwork
example leans on `scope boolean, unit_identifier: constant;`, so default VS Code theming of
those tokens will silently not color them unless M2/theme docs account for it. An M2
designer taking §4.5's claim at face value would register the wrong custom-type set.

Suggested fix: correct the parenthetical to list all four non-standard members
(`punctuation`, `text`, `constant`, `label`).

## Notes (not findings)

- Scope discipline is otherwise good: def-site paint is correctly isolated as open
  question 2 rather than silently frozen; HTML output, UTF-16, and server concerns are
  cleanly deferred; the analysis-grammar transform (§4.4) is genuinely required by the
  verified §2.1 fact and its rejected alternative is argued from real code behavior.
- The §4.1 grammar was traced against `fegen.fltkg` item/separator semantics and the
  generated-parser optional-commit behavior; the documented `label`/`rule` flush quirk and
  its whitespace workaround are correctly analyzed, and the deviations from the spec sketch
  (labeled qualifier literals, `kind_list` wildcard fix, `part`-labeled `dotted_name`) are
  each justified by the verified suppression rule.
