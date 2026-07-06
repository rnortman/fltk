# Brainstorm record: LSP servers and syntax highlighters from FLTK grammars

Interactive exploration, 2026-07-06. Two codebase surveys plus a real-world grammar case
study (clockwork). This document records the reasoning trail behind the ADR's decisions.

## 1. What already exists in FLTK (survey findings)

Full survey notes were produced during exploration; the load-bearing facts:

**Runtime everything.** `fltk.plumbing.parse_grammar(text) -> gsm.Grammar` and
`generate_parser(grammar, capture_trivia=True)` build a working parser fully in-process
(exec'd generated source, no files). A generic tool can load any `.fltkg` at runtime.
The GSM (`fltk/fegen/gsm.py`) exposes rules, alternatives, items, labels, dispositions,
literal vs regex terminals, separators, and trivia-rule classification (`is_trivia_rule`).

**Spans are LSP-ready.** `SpanProtocol` (`fltk/fegen/pyrt/span_protocol.py`) spans both
backends: codepoint `start`/`end`, `line_col()` (lazy line index), `line_span`, `filename`,
`merge`/`intersect`. Note: LSP defaults to UTF-16 positions — needs a per-line conversion
shim or `positionEncoding` negotiation (LSP 3.17).

**Diagnostics half-built.** `ErrorTracker` (`fltk/fegen/pyrt/errors.py`, Rust port in
`fltk-parser-core`) records furthest-failure position + expected tokens grouped by rule.
Adapting to one LSP `Diagnostic` is trivial. `error_formatter.format_source_line` is a
general span+message renderer already used by a downstream project (clockwork).

**Formatting done.** parse → unparse-to-Doc → resolve-spacing → render, in both backends,
driven by `.fltkfmt`. `textDocument/formatting` is a thin wrapper.

**CST walking is generic by convention.** Every generated node has `kind`/`span`/`children`
plus identical mutator names — but no cross-grammar base class (Python) or trait (Rust).
Generic Python tools walk structurally (docs recommend exactly this). Generic *Rust* tools
cannot exist; Rust genericity comes from macros over generated types (the
`fltk_formatter_main!` precedent).

**Hard limits.**
- Parsers are hard pass/fail. No recovery, no error nodes. Even a successfully parsed
  *prefix* is discarded at the call sites (`plumbing.py` length check, Rust
  `fully_consumed()`).
- No incremental reparse; every parse is whole-document (packrat, so linear-ish).
- Per-grammar Rust artifacts are separately compiled cdylibs built by the consumer;
  `fltk._native` itself only ships Span primitives.
- Nothing editor-related exists in-repo; "language servers" appears only as rationale
  prose for trivia capture.

## 2. Tree-sitter as a compilation target: rejected

The general argument: PEG prioritized choice with unbounded backtracking is not translatable
to tree-sitter's (G)LR model in the general case; it only works when the grammar happens to
be nearly-LR — i.e., when you're lucky.

The decisive concrete argument: FLTK grammars are **partially whitespace-sensitive**.
Clockwork terminates `use` statements with significant `"\n"+`, does explicit `" "*`
matching inside attribute rules, and distinguishes `.` (no trivia) from `,`/`:` boundaries.
Tree-sitter `extras` is a global "skip anywhere" set — it structurally cannot express
per-boundary trivia discipline. Rejected outright rather than deferred.

## 3. Case study: can token classes be inferred from the grammar alone? (clockwork)

Proposed mechanical classifier (per-occurrence, from the CST): word-shaped `Literal` →
keyword; other `Literal` → operator/punctuation; `Regex` by shape (quote-anchored → string,
digit-leading → number, identifier-shaped → variable); trivia rules → comment.

Run against `clockwork/dsl/clockwork.fltkg` on a representative fragment:

| Span | Provenance | Inferred | Verdict |
|---|---|---|---|
| `cog`, `configs`, `execute when` | word literals | keyword | correct (incl. multi-word literal) |
| `engine_monitor` | `identifier` regex | variable | tolerable (really a type definition) |
| `Float64` | `identifier` under `config_type:expr` | variable | wrong — should be type |
| `any_message` | literal alternative | keyword | tolerable (really builtin function) |
| `true`/`false`, `s`/`ms`/`us`, `single`/`multiple` | word literals | keyword | wrong — constants/units/enum values collapse into keyword |
| `// doc comment` | `doc` rule | **nothing** | badly wrong |

Two structural lessons:

1. **Comments are not reliably trivia.** Clockwork has *no* `_trivia` rule; comments are
   the structural, sometimes-mandatory `doc` rule. "Trivia → comment" inference yields
   nothing here. The single most important highlight class is uninferable without
   annotation.
2. **Parse-then-paint vs spelling-based is a category difference.** Clockwork's keywords
   are contextual: `name`, `type`, `version`, `port`, `package`, `signal` are option-key
   literals *and* plausible user identifiers in textually identical positions
   (`config_def := identifier , ":" , expr` vs `channel_name := "name" , ":" , expr`).
   Only the parser can tell occurrences apart. A spelling-based (TextMate-style) generated
   highlighter is a false-positive machine for this grammar class; its safe subset
   (punctuation, strings, numbers) is anemic. Per-occurrence CST classification gets the
   keyword/identifier *boundary* right by construction and is only wrong about
   *sub-categories* — which is exactly what a small sidecar spec can fix.

Conclusion: a `.fltklsp` sidecar is load-bearing for quality, not an enhancement tier. But
because the parser does all segmentation, the sidecar stays tiny (~15–30 lines for
clockwork) and every selector in it is validatable against the GSM at load time.

## 4. One spec language or three? (highlighting / defs-refs / formatting)

Agreed: highlighting + defs/refs belong in **one** language (`.fltklsp`) — same
classify-grammar-positions shape, and highlighting grows into symbols naturally (def sites
want `declaration` styling; ref kinds want type-colored rendering).

Formatting stays **separate** (`.fltkfmt`), same language *family*:

- For merging: identical addressing scheme (`rule X { ... }` + anchors by label/literal/
  rule-name — already proven in unparsefmt); one file per grammar is nicer to discover;
  authors think per-rule about both concerns.
- Against merging (decisive): `.fltkfmt` is a codegen input baked into generated unparsers
  and shipped binaries with a stability contract; `.fltklsp` is runtime config that should
  iterate fast early on. Defs/refs will grow symbol/namespace machinery with no formatting
  counterpart — one language serving both becomes a franken-DSL. And "one file is
  convenient for the LSP" is a non-argument: the server consumes both files regardless
  (it needs `.fltkfmt` to serve formatting).

Shared-core commitments: same lexical conventions, same anchor semantics, canonical
addressing by grammar rule names (fixing `trivia_preserve`'s node-class-name inconsistency),
same load-time validation approach.

## 5. Python vs Rust for the server

Deployment reality check: with VS Code Remote-SSH, the language server executes on the
**remote** host — binaries must match where the code lives (typically Linux VPS), not the
laptop. Because FLTK's Rust backend is per-grammar codegen, FLTK cannot ship prebuilt
server binaries at all; each downstream language would have to cross-compile and distribute
its own. That is a large adoption tax.

Latency reality check: LSP startup time is irrelevant (one process per editor session;
Python import + in-memory parser generation is well under a second). The keystroke path is
parsing + token collection. Pure-Python packrat on multi-thousand-line files is the real
risk; mitigations in order of cost:

1. Debounce + serve stale tokens (standard practice; zero cost).
2. Prefix-CST exposure so failures don't blank the file (small FLTK change).
3. The **existing** per-grammar pyo3 parser module (`rust_cst_module=`) as an opt-in
   native fast path — consumers who care already run maturin builds; the server stays
   generic Python either way.
4. (Future, if ever needed) generated native token-collection visitor to avoid
   per-node pyo3 boundary crossings; and/or a fully-native `fltk_lsp_main!` binary tier
   mirroring `fltkfmt` for projects that already ship per-platform artifacts.

Decision: Python-first generic server (pygls), native acceleration opt-in via existing
mechanisms. Nothing precludes a native tier later.

## 6. Error recovery position

Generated recovery (sync points at repetition boundaries, PEG labeled-failure literature)
is the only path to full-fidelity in-error highlighting, and it is a large design project
in `gsm2parser(_rs)`. Deliberately out of scope. The 80% alternative: last-good tree +
fresh diagnostic now, prefix-CST exposure next. Revisit recovery only if real usage shows
the degraded mode is insufficient.
