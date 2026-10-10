# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Serde frontend: new `fltk_serde_core::positioned_error`. A hand-written `Deserialize` impl
  that rejects a value after building it (say, a duplicate element found by comparing a list's
  `Spanned<T>` items) can now report the error at the offending element's source position, with
  related locations attached, instead of at the enclosing field or with no position at all.
  Under a non-FLTK deserializer the message is kept and only the position is dropped. See
  `docs/rust-serde-guide.md`.
- Bazel: `generate_rust_parser` gains `unparser` (emit `unparser.rs`), `format_config` (bake a
  `.fltkfmt` spec into it), and `out_dir` (declare the generated `.rs` files at a
  package-relative directory such as `src/`, so a pure-Rust `rust_library` can glob its own
  sources alongside them and needs no copy genrule). `fltk_pyo3_cdylib` gains `unparser`; as
  with `ast` / `serde`, a hand-authored `lib_rs` must declare and register the module itself.
- Bazel: every runtime crate now has a pyo3-free `:no_python` target
  (`//crates/fltk-cst-core:no_python` and the same on `fltk-parser-core`, `fltk-ast-core`,
  `fltk-serde-core`), and `//crates/fltk-unparser-core` and `//crates/fltk-fmt-cli` have Bazel
  targets for the first time. The existing default target labels, features, and deps are
  unchanged. Never link both flavors of a runtime crate into one binary — rustc refuses two
  crates with the same name.
- `Span.spells_at(cursor, literal)` and `Span.shares_source(other)` on both backends and on
  `SpanProtocol`. `spells_at` answers whether the source at an absolute codepoint index spells a
  literal, reading only within the span; `shares_source` answers span-source identity — not text
  equality, which is the looser question `merge` asks — directly rather than through a `merge`
  that is discarded for its failure mode.
- `docs/bazel-consumer-guide.md`: per-configuration recipes (pure Python, PyO3 extension, pure
  Rust, unparser/formatter, serde), the one-serde rule for serde-mode pure-Rust consumers, the
  pin-lockstep rule, and no-pyo3 verification queries for both build systems.

### Changed

- **Breaking (narrow)** — LSP server: the `--resolver HEAD:attr` flag now decides whether `HEAD`
  is a file or a Python module from the text alone. It is a file if it ends in `.py` or contains a
  `/` or `\`; anything else is imported as a module. Before, a bare head like `mylang.resolvers`
  was treated as a file whenever a file of that exact name happened to sit in the directory the
  editor started the server in, so one configuration worked in one workspace and failed to start
  in the next with a misleading error. To load a file without a `.py` suffix (a `.pyc`, say),
  prefix it with `./`. When a module head cannot be found, the error now suggests this. Any failure
  while importing a resolver module is now reported as a clean startup error rather than a
  traceback.
- **Breaking (narrow)** — AST, both backends: a `transparent;` (erased) product whose one label mixes a literal with a regex or
  rule reference now erases to the same payload a non-erased field of that label would carry —
  text for the literal, not a bare span. Where the label also carries a rule reference, the
  `<Rule><Label>` payload enum loses its `Span` variant (`LwordV::Span` → `LwordV::Text`; the
  Python alias loses `SpanProtocol`). Where the label mixes a literal with regexes only and the
  rule also references another rule outside the label (a suppressed `%sep?`, say), the
  `<Rule><Label>` type is **removed** on both backends (Rust enum, Python alias and converter) and
  the payload is a plain `String` / `str`; code that named that type must drop the name. A rule
  of literals and regexes alone is terminal-only, already erased to text, and is unaffected. Before,
  every non-literal value of such a rule unparsed as the literal, so no working code could depend
  on either old type; now parsed input round-trips and out-of-set text is refused.
- **Breaking (narrow)** — `fltk-fmt-cli`: a formatter binary's `--version`/`-V` now prints its
  own identity, `<name> <version>`, instead of the scaffolding's (`fltk-fmt-cli 0.4.0`).
  `fltk_formatter_main!` invocations need no edit: `name` and `version` default to the invoking
  crate's `CARGO_PKG_NAME` / `CARGO_PKG_VERSION` — under Bazel, the `rust_binary` target name
  and its `version` attribute, which rules_rust sets to `0.0.0` when absent. Add `version` to
  your formatter's `rust_binary`, or it reports `0.0.0`. `run_main(about, format_fn)` becomes
  `run_main(FormatterInfo { about, name, version }, format_fn)`; a direct caller builds the
  struct. `FmtArgs`'s derived command no longer declares a version, so `FmtArgs::parse()` used
  on its own has no `--version` flag; `run_main` supplies it. New optional `name:` and
  `version:` macro keys (after `about:`, in that order) override the defaults — useful when the
  Bazel target name is not what users should see.
- `fltk_unparser_core::Doc::SeparatorSpec` gains a `preserved_blank_lines: u32` field (the capped
  source blank count a spacing-only separator carries; `0` when none), and
  `preserved_blank_separator_spec(blank_lines, required)` is a new re-exported constructor.
  `separator_spec()` is unchanged and, with the new one, is the supported way to build the variant;
  code constructing or exhaustively matching the variant literally must add the field. The Python
  `SeparatorSpec` gains the same field, defaulted to `0`.
- Formatter, both backends: one format pass is now enough for `--check` to accept the result.
  When deciding whether a group (a run of content the formatter lays out on one line if it
  fits, else breaks) fits, the formatter now counts the indentation it is about to write before
  the group's first text; previously it measured against the full `-w` width. Groups whose
  indented one-line form overran `-w` by up to one indent width now break, and an outer group
  that now breaks may let an inner one join onto a single line — expect golden diffs where
  this applies. The in-tree corpus at width 80 / indent 2 is unchanged. Generated CST, parser
  and AST APIs are untouched.
- Formatter: a comment just inside a `nest` region — right after the opening delimiter (`{`,
  `(`) or right before the closing one — is now indented with the nest's content instead of
  sitting flush with the delimiter, matching comments between the nest's items. Expect golden
  diffs wherever such comments exist. Knock-on effects in that gap:
  - The closing delimiter after an own-line comment stays at the enclosing indent; preserved
    blank lines keep their count.
  - The comment's own whitespace now wins over `after`/`before` spacing for that gap: a trailing
    comment followed by `before "}" { hard; }` no longer gets an extra blank line, and a
    same-line `/* c */` before the delimiter keeps the source's spacing (fixing a non-idempotent
    `*/)` → `*/ )` → `*/  )`).
  - A delimiter left on a same-line comment's line stays there even when the enclosing group
    breaks.
  - A `group` that shares an anchor with the `nest` (or is declared before it over the same
    anchors) now contains the comment and breaks on it, where it used to stay flat. With `nest`
    declared first it still stays flat — an ordering quirk tracked as
    `TODO(join-nest-same-anchor)`.
  - Grammars whose whitespace is a byte-rendered token (e.g. the gear demo's `ws := /\s+/`) keep
    the comment at its source column, but the line after a block-opening comment now drifts one
    indent per format pass, as it already did after mid-block comments
    (`TODO(preserved-trivia-ws-bytes)`).
- Formatter: `before X` spacing on an optional item (`X?` or `X*`) now appears only when `X` is
  actually printed. Previously an absent `X` (or a `*` with zero matches) still left its spacing
  behind. With a common spec such as `before ";" { nil; }` on an optional statement terminator,
  that stray spacing produced an extra blank line before a closing `}` that follows a
  `}`-ended statement, and could delete an authored blank line under `preserve_blanks`. A
  non-empty `*` run still gets one spacing ahead of the run. Unchanged: spacing on a suppressed
  item (`%X?`, or an unlabelled literal) still always applies, so formatting stays idempotent,
  and `after` spacing is unchanged everywhere. Formatted output changes only for specs that set
  `before X` on an included optional `X`; expect golden diffs there, each one removing spacing
  where no `X` was printed. For hand-built or edited trees without source positions, an absent `X`
  between two comments now drops the second comment, the same as when no `before X` is set. Blank
  lines between two items that are both present can still be lost (tracked separately).
- Formatter: newline-spanning tokens (multi-line strings, heredocs), multi-line block comments
  inside a nest, and `.fltkfmt` `text("…")` doc literals containing `\n` now render
  byte-for-byte on both backends. Previously the nest indent was written into the token's value
  after every embedded newline, again on every pass, so the output was never a fixed point. A
  `join` separator that spelled its line break as `text("\n")` (or `text(",\n")`) now leaves the
  next element at column 0 inside a nest — spell the break `hard`, e.g.
  `concat([text(","), hard])`.
- Formatter: a grammar literal that is exactly `"\n"` is a hard line break. A line comment's
  terminator now forces an otherwise-flat enclosing group to break (a trailing comment no longer
  leaves the next token flat after a physical newline), and a column-0 comment inside a nest no
  longer renders a spurious blank line before the next token.
- Formatter: a hard line break directly followed by `hard`/`blank` spacing from the `.fltkfmt`
  spec now produces one break (keeping the requested blank lines) instead of two. This covers
  `render X as hard|blank` and `hard`/`blank` join separators.
- Formatter: the column after a multi-line token is the width of its last line, so a following
  group may now fit flat where it previously broke. This is correct column accounting, not a
  regression.
- **Breaking (cargo):** `fltk-cst-core`'s `python` feature is no longer a default feature
  (`default = ["python"]` → `default = []`), so a cargo consumer that took the crate without
  `default-features = false` and relied on the default now builds without pyo3 and without the
  `#[pyclass]` surface. If you want the PyO3 flavor, ask for it explicitly:
  `fltk-cst-core = { version = "...", features = ["python"] }`. Pure-Rust consumers are the
  ones this fixes: they no longer link pyo3 by accident. Bazel targets are unaffected —
  `//crates/fltk-cst-core` still carries the feature and `:no_python` still does not.

- Generated CST mutators (`append`, `extend`, `extend_children`, `append_<label>`,
  `extend_<label>`, `insert`, `replace_at`) now validate every child on both backends and raise
  `TypeError` on a value the node cannot hold, where the Python backend previously stored it and
  failed far away in the unparser or a converter. Children must be backend-native: pass the
  backend's own node classes and its own span type (`fltk.fegen.pyrt.terminalsrc.Span` for the
  Python backend, `fltk._native.Span` for the Rust backend) rather than a structural
  implementation of the protocol. Labels, by contrast, are now matched by canonical name and
  normalized, so a protocol label sentinel or the other backend's enum member is accepted
  everywhere it type-checks — a relaxation.
- Rust generated `children_<label>()` returns a fresh single-pass iterator instead of a `list`,
  matching the `Iterator[T]` its stub and the generated protocol module have always declared and
  matching the Python backend. If you index or re-iterate the result, wrap it:
  `list(node.children_<label>())`. The bare `<label>()` accessor still returns a `list`.
  The Python backend's return type is unchanged, but its semantics moved: the iterator is now
  over a snapshot taken at call time, where it previously read `self.children` lazily as it was
  consumed. Children appended or removed after the call are no longer observed by an iterator
  already in flight.
- Generated `.pyi` stubs for a Rust CST extension annotate node-typed *return* positions with the
  stub's own concrete classes instead of the protocol classes, so code annotated against one
  backend's concrete node types can descend a tree with the accessors on either backend.
  Parameter positions keep the protocol annotations. Returns only narrowed, so existing
  annotations stay valid.
- Multi-valued accessors on the generated protocol module are declared `typing.Sequence`, not
  `list`. Protocol-typed code that mutated an accessor result in place must copy it into a
  `list` first.

### Fixed

- AST converters, both backends: `to_cst` on a product rule whose alternatives split one label
  between a labeled literal and a regex or rule reference now selects by the value's text. A
  parsed `42` under `x := v:"lit" | v:/[0-9]+/ | v:item` used to render as `lit`; it round-trips
  now. A hand-built string that is none of the label's spellings raises `AstError` instead of
  rendering the literal — "no alternative fits the populated fields" where no alternative admits
  it, or the refusal of the alternative whose regex position it fails. Sibling spellings under
  one label still canonicalise to the first. One Python-only exception: where the label's other
  kind is a `transparent;` rule erased to text, a Python `str` does not record which kind it is,
  so a value equal to a spelling takes the literal alternative even when the parse read it
  through the erased rule — under `x := v:"lit" . ";" | v:word ;` with `word` transparent, parsed
  `lit` renders `lit;` on Python (which reads back as the same value) and `lit` on Rust. Tracked
  as `TODO(ast-select-untagged-erased-text)`.

- Rust AST backend: the generated `to_cst` for a terminal-only rule whose alternatives build
  identical children (`top := v:"lit" | v:/[0-9]+/`) no longer fails clippy under `-D warnings`
  (`if_same_then_else`, `manual_range_patterns`). Such alternatives now share one arm, written as
  `0 | 1` or as a range like `0..=2`. Generated bytes change for these rules; behaviour does not.

- AST converters, both backends: converting an AST value to a CST and back
  (`from_cst(to_cst(v))`) no longer fails for `fold_left:` / `fold_right:` rules with two or
  more operands whose operands are plain tokens — a regex child, a terminal-only rule, or a
  `transparent;` number as in the AST guide's quick start. It used to raise "the operands of a
  fold come from different sources" (and on Python only for some inputs: `1+2` failed, `1+1`
  passed with a wrong span). The span on each fold link is now the range covering its operands
  when they sit in order in one source text — always true for parsed input, so parsed spans are
  unchanged — and unknown otherwise, matching every other node `to_cst` builds. A CST hand-stitched
  from two parses also converts now, with unknown link spans, instead of being refused.

- Rust backend: reading a span's text (`Span::text` / `text_str` in Rust, `Span.text()` /
  `text_or_raise()` from Python, and the generated `*_text()` CST accessors) no longer rescans
  the source from the beginning on every call. Each read used to cost time proportional to how
  far into the file the span sat, which made the Rust formatter roughly quadratic in document
  size (about 4× slower per doubling); a read now costs only the span's length, after a one-time
  index built per source. Results are unchanged. The first read on a large non-ASCII source now
  builds and keeps that index (about 8 bytes per character).

- Formatter: blank lines kept by `preserve_blanks` are no longer lost at a gap that has an anchor
  spacing on each side — an `after "x" { ... }` rule on the item before the gap and a
  `before "y" { ... }` rule on the item after it (e.g. `after ";"` plus `before "}"`), in both
  backends. Before this a gap with one anchor kept `min(B, N)` blank lines and the same gap with an
  anchor on each side kept none. An explicit anchor asking for more blank lines than the source
  held still wins. Expect golden diffs at gaps with an anchor on
  each side that held a blank line in the source; where such a gap sits inside a `group`, the
  restored line break also breaks the group, so its other soft breaks render as newlines, as the
  one-anchor path already does for the same source. Configured `blank(N)` defaults, `join`
  separators and comment-bearing gaps resolve as before.
- `preserve_blanks` now actually preserves blank lines. The generated unparsers counted a gap's
  blank lines but emitted the configured spacing for the gap instead of the counted line break,
  so `preserve_blanks: N` was a no-op in every gap holding only whitespace, and a blank line
  following a preserved comment was dropped along with the comment's own line terminator.
- Trivia now binds to the gap it was written in, around a suppressed literal. The generated
  unparsers walked separators and items in grammar order while taking trivia children in child
  order, and a rule node's children are not index-aligned with its alternative's separators — a
  suppressed literal contributes no child, and the parser pushes a trivia child only where
  whitespace or a comment matched. A separator standing for an empty gap therefore took the
  trivia belonging to a later one and re-emitted it ahead of the suppressed text between them.
  The visible symptom was a suppressed terminator stranded on a line of its own after a blank
  line or a comment: a rule ending `, %";" ,` formatted `a;` followed by a blank line as `a`,
  blank, `;`. Both backends now decide ownership from source positions; where the tree's
  positions stop being positions in one source — a hand-built or mutated CST — trivia is
  consumed in child order as before. A trivia child the walk has already passed — a position
  inconsistency no ownership rule can resolve — halts the unparse naming the rule, the child
  position and a line/col, instead of failing the alternative and surfacing as an unlocatable
  "unparser returned None". See `docs/format-specs.md` §Trivia Preservation.
- `Span.shares_source` on the Python backend answered `True` for two distinct sources holding
  equal text, where the Rust backend answers source identity. Both are identity now.
- `Span.spells_at` on a non-ASCII source no longer scans the text from the start on every call:
  the codepoint→byte resolution goes through a table built once per source, as the all-ASCII
  path's identity always did.

## [0.5.0] - 2026-08-06

### Added

- Generated AST layer. A grammar can now be given a `.fltkast` sidecar and generate typed AST
  node classes beside its CST: plain owned data (dataclasses on Python, structs and enums on
  Rust), one type per rule, with converters in both directions (`from_cst` / `to_cst`) and
  one-call entry points (`parse`/`unparse` on Python, `parse_str`/`unparse_str` on Rust) that
  carry text in and out. Spans never take part in equality, so values converted from identical
  text at different offsets compare equal. The sidecar shapes the result: `transparent;` erases a
  rule to its payload, `flatten;` splices a wrapper's fields into its parents, `type:` coerces a
  terminal to a scalar (integers, floats, `uuid`, `decimal`, or a `custom(...)` type of your own),
  `key:` turns a collection into an insertion-ordered map, `fold_left:`/`fold_right:` folds a
  repetition into a binary chain, and `name:`/`field`/`variant` rename anything generated.
  See `docs/ast-guide.md`.
- `key: <label> multi;` in the `.fltkast` sidecar: an accumulating keyed collection. Elements
  sharing a key group instead of colliding, so the map is `IndexMap<K, Vec<T>>` / `dict[K,
  list[T]]` and a repeated key is no longer an error. A key takes its place where its first
  element appeared, and the write direction renders a group together — adopting `multi` on a
  region canonicalizes its unparse to grouped order.
- Rust serde frontend (`gen-rust-serde`, `crates/fltk-serde-core`). A grammar can now generate a
  `serde::Deserializer` over its CST, so source text deserializes straight into a consumer's own
  `#[derive(Deserialize)]` types: `de::from_str(src, filename)` for the goal rule and
  `de::from_<rule>_cst(node)` for any rule. It generates no types of its own — the target structs
  are the schema, scalar targets run the same gates as the AST layer's `type:` coercions, and
  serde's unknown-field / missing-field / invalid-type errors come back positioned by CST span.
  A keyed region serves either a map (key omitted from the value, duplicates refused with both
  locations) or a sequence (key included, source order), whichever the target declares.
  `Spanned<T>` carries a field's position, `Raw<cst::T>` holds a subtree as syntax for later, and
  with `--ast-mod-path` a field can be declared as a generated AST type and means that rule's
  `from_cst`. Wired into the Makefile (`gen-rust-serde`) and Bazel (`ast_config` / `ast` /
  `serde` / `goal` on `generate_rust_parser` and `fltk_pyo3_cdylib`, which also closes the
  `.fltkast` plumbing gap for `ast.rs`). See `docs/rust-serde-guide.md`.

### Changed

- The formatter's labeled-literal trial matching is now text-aware. A CST child whose text one
  spelling of a label cannot produce is declined by that spelling instead of being rendered
  through it, so trees that previously rendered *wrongly* now render the branch that matches, or
  fail loudly.
- Unparser generation now rejects an always-present labeled literal with more than one spelling
  under one label: the unparser cannot know which spelling a value came from. The error message
  names the rule, the label and the spellings, and is the migration path.
- AST generation rejects two indistinguishable branches of one alternation (values of the two
  cannot be told apart at runtime, so one branch would render every one of them) and a capture
  group named more than once in the pattern that rebuilds a terminal-only rule's text. Both were
  previously silent corruption or a panic at the first serialize.
- Python generated converters raise `AstError` on a child of the wrong kind, where they
  previously failed incidentally further down.

## [0.4.0] - 2026-08-03

This release is about the shape of the tree you get back. The `!` (inline) disposition
finally works, so a grammar can flatten a helper rule into its caller instead of forcing
consumers to walk through a wrapper node, and generated CST classes gained a short,
typed accessor surface — `foo()`, `foo_text()`, `text()`, `variant()` — so reading a
child no longer means picking the right `child_*`/`maybe_*` method by hand. Both land on
the Python and the Rust backend. Everything here is additive: no existing generated
symbol, signature, node shape or error message changed.

### Added

- The `!` (inline) grammar disposition is now implemented in both parser backends. `!inner`
  splices `inner`'s children into the calling node instead of nesting an `Inner` node; the
  quantifier applies to the whole spliced body. The inlined rule keeps its own node class,
  parser entry point and `RULE_NAMES` entry. `!` on a literal, regex or sub-expression, a
  labeled `x:!inner`, a reference to a trivia-reachable rule, and `!` cycles are all errors
  at grammar-load time. See `docs/cst-structure.md`. Grammars using `!` previously could not
  generate a parser at all, so no working grammar changes behavior.
- Generated CST node classes gained an ergonomic accessor surface on both backends,
  documented in `docs/cst-structure.md`:
  - a bare `foo()` per label, typed by the label's whole-rule multiplicity (`T`,
    `T | None`, or `list[T]`);
  - `foo_text()` for single-valued span labels, and `text()` on terminal-only rules;
  - `variant()` on dispatch rules (every alternative a single labeled item), returning the
    `Label` of the matched alternative.

  These are purely additive. Where a new member's name would collide with an existing one —
  a label named `text` or `children`, a label that duplicates another label's
  `append_*`/`child_*` name, a `__`-leading label, a keyword — the new member is skipped
  rather than renamed, and generation logs the rule, member and reason. Existing members are
  never displaced, so a grammar that generates today still generates.

### Changed

- The new Rust **native** accessors panic on a tree that violates the grammar's guarantees
  (wrong child count, sourceless span) rather than returning `Result`. This is a deliberate
  departure from the "no accessor ever panics" rule that governs the `child_*`/`maybe_*`
  family, which is unchanged and remains the checked surface for code that builds or mutates
  trees. The Python-facing bindings never panic — they raise `ValueError`, matching the
  Python backend message for message.

### Fixed

- Rust `Span.text()` / `text_str()` no longer decline a valid empty span whose start sits at
  the end of the source (`Span(n, n)` for a rule that matched nothing at end of input). They
  now return an empty slice, matching both the documented contract and the pure-Python
  `Span`, where they previously returned `None` — which made the new `text()` accessor panic
  on the Rust native surface for a perfectly ordinary parse result.

### Notes for downstream consumers

- Every new member is additive; no existing generated symbol, signature, error message,
  node shape or `RULE_NAMES` entry changed.
- Two error wordings on the new text accessors are backend-specific, inherited from the
  surfaces they report: the `maybe_*` duplicate-child count message and the out-of-range
  span message. Match on the exception type rather than the message if you switch backends.
- If you **subclass** a generated node class, a method of yours named like a new member
  (`text`, `variant`, a bare label name) will now shadow the generated one. Generated
  classes are not intended to be subclassed.
- If you **hand-implement** a generated `*_cst_protocol` class, it will no longer conform:
  the protocol grows the new members along with the classes it describes.

## [0.3.0] - 2026-07-24

This release adds two major capabilities on top of a year of hardening: an optional
**Rust backend** for generated parsers and CSTs, and a full **language-server
toolchain** for FLTK grammars. The alpha unparser/formatter from 0.2.0 also matured.
The Python backend remains the default and its public API is unchanged.

### Rust backend (alpha)

FLTK can now generate a Rust implementation of the CST and parser alongside the Python
one. The goal is a near-drop-in replacement: a downstream project can switch its
generated parser and CST to the Rust backend and, at most, update its import
statements — type annotations and call sites are meant to keep working unchanged.

- CST and parser code generation in Rust, with a backend selector so a grammar can
  target the Python or the Rust implementation.
- A Rust implementation of the unparser/formatter, plus a standalone pure-Rust
  `fltkfmt` binary that formats `.fltkg` files without a Python runtime.
- Generated Rust nodes own their children as `Shared<T>` (an `Arc<RwLock<T>>` newtype),
  so cloning a node is a shallow reference clone. Child identity now matches the Python
  backend: reading the same child twice yields the same object, and mutations are
  visible through every reference and across the language boundary.
- Type-stub (`.pyi`) emission for the generated extension, and hardening of the
  cross-cdylib ABI so a compiled parser can be loaded safely from a consumer module.

Treat the Rust backend as early alpha.

### Language Server Protocol tooling

- `fltk-lsp`, a pygls-based language server that drives editor features directly from
  an FLTK grammar.
- A `.fltklsp` spec language and classification engine for semantic highlighting, with
  a companion `fltk-highlight` CLI.
- Definition, reference, and namespace navigation for grammars; prefix-CST exposure so
  incomplete input still highlights gracefully; a resolver plugin API; and a VS Code
  integration.
- FLTK now dogfoods these servers on its own grammars.

### Unparser and formatter improvements

- New `preserve_blanks: N` directive to preserve and normalize runs of blank lines.
- Comment handling fixes: inline comments stay on the line they annotate, comments
  between rules attach to the following rule, and spurious blank lines no longer appear
  between commented alternatives.
- New documentation: `docs/format-specs.md` (format-spec reference) and `docs/usage.md`
  (CLI usage).

### Robustness and security

- Generated parsers enforce a configurable recursion-depth limit, preventing
  stack-exhaustion denial-of-service on pathological input.
- A forged-ABI code path that could segfault the Rust backend was closed, and error
  messages emitted by generated parsers are now properly escaped.
- Grammar generation catches more latent bugs up front: non-portable regexes, empty
  `_`-named rules, and identifier collisions are now rejected at generation time.

### Build, CI, and dependencies

- Supply-chain and toolchain hardening: `cargo-deny` gating, pinned CI actions managed
  by Dependabot, a pinned Rust toolchain mirrored across the cargo and Bazel lanes, and
  lockfile-drift gates.
- Dependencies were refreshed across the board (Python, Rust, and CI actions), which
  included moving to a newer ruff and clearing the resulting lint/format findings.

## [0.2.0]

The main feature here is alpha-level support for generating unparsers and source
code formatters from FLTK grammars. Various small bugs and enhancements are also
included; see detailed chages in the changelog.

### Utilities for dynamically generating and running parsers/unparsers

There is a new `fltk.plumbing` module that makes it easy to dynamically generate
and run parsers/unparsers, and also `unparse_cli` which lets you do this from
the command line.

### Detect repeated potentially-nil items

If you have a rule like:

foo := ("a"? ,)*;

This can match the empty string an arbitrary number of times, which previously
would lead to the parser hanging in an infinite loop. We fix this bug by
detecting potentially-nil repeated items at parser generation time, making it
easier to detect this grammar bug.

### Unparser and Formatter support (alpha)

A huge new feature: We can generate unparsers and formatters from FLTK grammars.
This means that given a CST, you can generate source code that parses to that
CST, meaning you can round-trip source and reformat it, as well as write
refactoring tools that parse a file, modify the CST, and then write out the
modified source without relying on fragile regex-based string matching and
replacement.

Unparsing will not always regenerate exactly the same source text, but it should
regenerate something semantically equivalent (i.e., something that produces the
same CST result). Formatting is based on Wadler-Lindig Pretty-Printing
Combinators with some extensions, and is controlled by a new fltkfmt DSL.

Unparsing and formatting support should be considered early alpha. It may be
buggy and we may make breaking changes to the fltkfmt DSL or how it works.
Unparsing is substantially more complex, it turns out, than parsing.

### Allow leading whitespace/trivia

Rule alternatives can now start with a separator spec to indicate leading
trivia. In particular this is very useful for allowing the grammar as a whole to
begin with trivia.

### Move python files out of repo root

All python source was moved into the fltk package. This is a breaking change for
anything directly referring to those files, though anything using the bazel
rules will not need to change since the rules were updated as well.

## [0.1.1] - 2025-07-03

Fix a regression caused by renaming the trivia rule to use all caps. This turns
out to be a bit of a problem with linters on the generated parsers, so we now
use `_trivia` instead of `_TRIVIA`.

## [0.1.0] - 2025-07-02

The major change in 0.1.0 is the addition of trivia support, i.e. being able to
have comment syntax in your language. ("Trivia" is just compiler-nerd jargon for
"comments and whitespace".) This release also includes a lot of general code
cleanups and modernization.

### Dev environment modernization and build integration
- Migrate dev environment from hatch to uv and mypy to PyRight
- Fix all PyRight errors and update formatting rules
- Update Bazel rules for uv and dual-parser generation
- Small code cleanups; remove dead code
- Overhaul genparser.py CLI with Typer interface

### Add trivia support (comments and whitespace)
- Implement trivia as normal grammar productions under special name _TRIVIA
- Force trivia-within-trivia to be plain whitespace
- Generate CST node clases for trivia
- Generate two different parsers per grammar: One which produces trivia CST nodes and a faster one that doesn't
- Add comment support to FLTK grammar itself

### Refactoring and cleanup
- Add a README
- Fix linting and typing issues
- Remove global singleton type registry
- Add regression test for recursive rules inlining bug
- Add regression test for WS_REQUIRED walrus operator precedence bug
- Regression test for Fix error reporting at EOF
- Add regression test for empty N-ary nodes bug
- Add regression test for top-level rule recursion bug
- Add regression test for line/col error reporting bug
- Fix trailing character parsing bug

### Bug Fixes (June 2024)
- Fix bug with inlining recursive rules

### Bug Fixes (Spring 2024)
- Fix bug in WS_REQUIRED
- Fix error reporting at end of file
- Fix bug with detecting empty N-ary nodes
- Fix bug with recursion on top-level rule
- Fix bug in line/col error reporting
- Fix a bug with multi-path left recursion

## [0.0.1] - 2023-11-06

### Initial Build System Setup
- Set up pyproject, linters, reformatting
- Set up Bazel workspace and rule
- Small fixes to Bazel module definition
- Fix unnecessary type cast in gencode
- Small mypy fixes, and add py.typed
- Add missing srcs/deps

### Core Features Implemented
- Custom grammar notation (.fltkg format) for defining parsers
- Self-hosting parser generator - the grammar parser is itself generated from a grammar
- Packrat parsing with memoization for O(N) performance
- Type-safe Concrete Syntax Tree (CST) generation
- Source span tracking for all parsed nodes
- Python code generation for parsers
- Support for left-recursive grammars
- Development tooling with ruff, pyright, and pytest

[Unreleased]: https://github.com/rnortman/fltk/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/rnortman/fltk/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/rnortman/fltk/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/rnortman/fltk/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rnortman/fltk/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/rnortman/fltk/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rnortman/fltk/releases/tag/v0.1.0
[0.0.1]: https://github.com/rnortman/fltk/releases/tag/v0.0.1
