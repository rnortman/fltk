# ADR: Auto-generated editor tooling for FLTK grammars — `.fltklsp` spec language and a generic LSP server

- Status: Proposed
- Date: 2026-07-06
- Supporting docs: [`brainstorm.md`](brainstorm.md) (exploration record), [`fltklsp-spec.md`](fltklsp-spec.md) (proposed syntax and semantics)

## Context

FLTK's primary purpose is powering out-of-tree DSLs (e.g. clockwork). Those DSLs currently
have no editor support: no syntax highlighting, no diagnostics-as-you-type, no go-to-definition.
Almost all of the groundwork already exists in FLTK:

- Runtime grammar loading and in-memory parser generation (`fltk.plumbing.parse_grammar`,
  `generate_parser`) — a tool can serve *any* `.fltkg` with zero codegen.
- Cross-backend `SpanProtocol` with `line_col()` — LSP position math is nearly free.
- `ErrorTracker` furthest-failure diagnostics with expected-token sets.
- A working formatter pipeline (parse → unparse → render) driven by `.fltkfmt` specs.
- Structured, optionally-captured trivia.

What does **not** exist, and cannot be inferred from a grammar alone (demonstrated against
clockwork's grammar; see `brainstorm.md` §3):

- Reliable token classification. Scannerless PEG grammars have contextual keywords; a
  grammar-only classifier collapses booleans, unit suffixes, enum values, and builtin
  functions into "keyword", and grammars like clockwork that model comments as structural
  `doc` rules (not trivia) get no comment highlighting at all.
- Any notion of definitions vs. references.

## Decisions

### D1. A new sidecar spec language, `.fltklsp`, covering highlighting **and** defs/refs

One language for both (they share the "classify grammar positions" shape and grow together
into document symbols / navigation). Designed up front for both phases even though
implementation is incremental: highlighting first, defs/refs second. Syntax and semantics in
[`fltklsp-spec.md`](fltklsp-spec.md).

### D2. Separate from `.fltkfmt`, but the same language *family*

`.fltkfmt` is a codegen input baked into generated unparsers and shipped formatter binaries;
`.fltklsp` is runtime configuration for editor tooling. Merging them couples the LSP
language's (initially fast) evolution to the fmt language's stability contract, and the
symbol/namespace machinery defs/refs need has no formatting counterpart. Instead, `.fltklsp`
reuses `.fltkfmt`'s proven addressing core: global statements + `rule <name> { ... }`
blocks, anchors resolved as label | literal | referenced-rule-name, `//` comments, identical
lexical conventions, and load-time validation of every anchor against the GSM.

Cleanup noted in passing: `.fltkfmt`'s `trivia_preserve` addresses generated node-class
names (`LineComment`) while everything else uses grammar rule names (`line_comment`). The
shared selector convention should canonicalize on grammar rule names.

### D3. No tree-sitter compilation target

PEG ordered choice does not map to (G)LR in the general case, and FLTK grammars are
partially whitespace-sensitive (significant newlines, explicit `" "*` matching, `.` vs `,`
separators). Tree-sitter's global `extras` model cannot express per-boundary trivia
discipline. Rejected, not deferred.

### D4. Python-first generic server, with the existing per-grammar Rust parser as the opt-in fast path

Product shape: `fltk-lsp` — a generic pygls-based server invoked as
`fltk-lsp --grammar lang.fltkg [--lsp lang.fltklsp] [--fmt lang.fltkfmt]` (or via a
workspace config file). It loads the grammar and specs at startup and serves any FLTK
language with **no compilation step**.

Performance escape hatch: FLTK already supports per-grammar compiled pyo3 parser/CST
modules (`generate_parser(grammar, rust_cst_module=...)`). The server accepts an optional
`--native-module` pointing at such a module; the parse hot path then runs in Rust while the
server logic stays generic Python. Projects that need keystroke-scale latency on large files
build that module once with their existing maturin setup; everyone else uses the dynamic
pure-Python parser with debouncing.

Why not Rust-first: with VS Code Remote-SSH (the dominant "Mac laptop, Linux VPS" setup),
the language server runs **on the remote host**, so binaries must match the machine where
the code lives — and because FLTK's Rust path is per-grammar codegen, FLTK itself cannot
ship prebuilt binaries; every downstream language would have to cross-build and distribute
its own server per platform. That is a real installation/configuration burden for marginal
benefit: LSP startup cost is irrelevant (one process per session), protocol handling is not
the bottleneck, and the parse hot path can be natively accelerated via the existing pyo3
mechanism without changing the distribution story. A fully-native `fltk_lsp_main!` macro
binary (mirroring `fltk_formatter_main!`/`fltkfmt`) remains a possible later tier for
projects that already ship per-platform binaries; nothing in this design precludes it.

### D5. Declarative specs for in-file semantics; a resolver plugin for cross-file

`.fltklsp` declaratively covers highlighting, document symbols, and same-file def/ref
(go-to-def, references, rename within a file, folding by symbol). Cross-file resolution
(clockwork's `use @repo::path::Type` with aliases) encodes a project model that no selector
language can express; it is handled by an optional per-language Python resolver hook loaded
by the server. Without a resolver, features degrade gracefully to same-file behavior.

### D6. Parse-then-paint, with graceful degradation on parse failure

Highlighting is computed from the real CST (per-occurrence classification — the only way to
get contextual keywords right; see `brainstorm.md` §3). On parse failure the server serves
the last-good token set plus a fresh diagnostic from `ErrorTracker`. Planned improvement
(small FLTK change, big UX win): expose the successfully-parsed prefix CST that
`plumbing.parse_text` / `fully_consumed()` currently discard, so only the region after the
error degrades. Generated error *recovery* in parsers is explicitly out of scope for this
ADR (a future, much larger project).

## Incremental plan

1. **M0** — `.fltklsp` grammar + loader + GSM validation + built-in default classifier.
2. **M1** — Standalone highlighter CLI (`fltk-highlight`, ANSI/HTML output). Small,
   immediately useful, and the test harness for classification semantics.
3. **M2** — `fltk-lsp` (pygls): diagnostics, semantic tokens, folding ranges, selection
   ranges, document formatting via the existing unparse pipeline. Stale-tokens-on-failure.
4. **M3** — Prefix-CST exposure in `fltk.plumbing` (both backends) for degraded-mode
   highlighting past the last-good parse.
5. **M4** — defs/refs: document symbols, go-to-def, find-references, same-file rename,
   `namespace` scoping.
6. **M5** — Resolver plugin API for cross-file navigation; optional native-module
   acceleration documentation; evaluate a Rust `fltk_lsp_main!` tier if demand exists.

## Consequences

- Every FLTK-based DSL gets editor support for the cost of writing one `.fltklsp` file
  (~15–30 lines for a clockwork-sized grammar) — no per-language server code.
- A new public surface: the `.fltklsp` language and the server CLI become API for
  out-of-tree consumers, with the same compatibility obligations as generated code.
- Two sidecar files per grammar (`.fltkfmt`, `.fltklsp`) rather than one; authors handle
  two small files with a shared idiom instead of one entangled language.
- Pure-Python keystroke latency on large files is a known risk, mitigated by debouncing,
  stale-token serving, prefix exposure (M3), and the native-module fast path.
- Semantic-token collection walks pyo3 node objects from Python when the native module is
  used; if boundary-crossing overhead proves significant, a generated native token-collection
  visitor is a possible follow-up (noted, not designed).
