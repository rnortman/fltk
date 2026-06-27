# Design: Rust Unparser Backend

Status: draft. See `requirements.md` and `exploration.md` in this directory for the
problem statement and code survey; this document does not restate them.

## 1. Root cause / context

FLTK can emit two artifacts per grammar: a parser and an unparser. The parser
generator gained a Rust backend (`fltk/fegen/gsm2parser_rs.py`,
`RustParserGenerator`) that emits a single `.rs` file with a pure-Rust layer plus
an optional `#[cfg(feature = "python")]` PyO3 wrapper, backed by a pyo3-free
runtime crate `crates/fltk-parser-core`. The unparser generator
(`fltk/unparse/gsm2unparser.py`, `UnparserGenerator`) is still Python-only.

The Python unparser is not a string emitter. It is a three-stage pipeline:

1. **Unparse** — the generated `Unparser` class walks the CST and builds a `Doc`
   combinator tree through an immutable `DocAccumulator`
   (`fltk/unparse/combinators.py`, `fltk/unparse/accumulator.py`). Each rule gets
   `unparse_{rule}(node) -> Optional[UnparseResult]`; alternatives/items/quantified
   loops get helper methods taking `(node, pos, accumulator)`
   (`gsm2unparser.py:190`, `:689`, `:1561`, `:1669`). The walk is positional over
   `node.children` (a list of `(label, value)` tuples), checks labels against
   `{ClassName}.Label.{LABEL}`, dispatches with `isinstance` for rule nodes and
   `fltk.unparse.pyrt.is_span` for terminals, and reads terminal text via
   `extract_span_text(span, terminals)` (`gsm2unparser.py:1764`).
2. **Resolve specs** — `resolve_spacing_specs` (`fltk/unparse/resolve_specs.py`)
   rewrites `AfterSpec`/`BeforeSpec`/`SeparatorSpec`/`Join` control nodes into
   concrete spacing, handling trivia preservation, spec merging, and HardLine
   collapsing.
3. **Render** — the Wadler-Lindig `Renderer` (`fltk/unparse/renderer.py`) turns the
   resolved `Doc` into a string, making flat-vs-break decisions per `Group` against
   `RendererConfig(indent_width, max_width)`.

The `FormatterConfig` (`fltk/unparse/fmt_config.py`) is consumed entirely at
**generation time**: spacing defaults, anchor operations (group/nest/join begin/end),
item dispositions (Omit/RenderAs), and trivia preservation are baked into the emitted
method bodies. The only runtime input to the generated `Unparser` is `terminals`
(the source string), used solely so spans can yield their text.

The requirement is to give the unparser the same Rust treatment: a pyo3-free core
that reproduces all three stages in Rust over the Rust CST, plus an optional PyO3
wrapper that accepts only the Rust CST handles (`Py{ClassName}`), so a Python caller
of the Rust unparser must also use the Rust parser. None of the `Doc`/accumulator/
resolve/render machinery exists in Rust today.

Key structural facts that shape the port (from the exploration):

- The Rust CST (`gsm2tree_rs.py`) gives each rule a data struct `{ClassName}` with a
  native, pyo3-free API: `children(&self) -> &[(Option<{ClassName}Label>, {ClassName}Child)]`
  (`gsm2tree_rs.py:1143`), `span(&self) -> &Span` (`:1130`). The child enum
  `{ClassName}Child` (`:796`) has a `Span(Span)` variant for terminals and one
  `{ChildClass}(Shared<{ChildClass}>)` variant per referenced rule. `Shared<T>` is
  `Arc<RwLock<T>>` with `.read()`/`.write()`.
- The PyO3 handle `Py{ClassName}` (`:1195`) wraps `inner: Shared<{ClassName}>` and
  exposes `shared(&self) -> &Shared<{ClassName}>` (`:1207`).
- `Span` carries its own source and exposes `text(&self) -> Option<String>`;
  sourceless spans return `None` (exploration §Span).
- Naming helpers are static and already shared with the parser backend:
  `child_enum_name`, `py_handle_name`, `label_enum_name`
  (`gsm2tree_rs.py:763`, `:772`, `:668`).

Because the child enum *is* the child-species discriminant, the dual-backend
`is_span` probe and the whole `terminals`-slicing fallback collapse to a Rust
`match` arm — the Rust unparser never needs a `terminals` parameter (requirements
§"A key difference", exploration OQ-2). Regex portability is irrelevant here: the
unparser reads captured spans and never compiles a regex, so the parser's
portability guard (`gsm2parser_rs.py` module docstring) has no analog.

## 2. Proposed approach

Three new pieces, mirroring the parser backend one-for-one:

1. A pyo3-free runtime crate `crates/fltk-unparser-core` providing `Doc`,
   `DocAccumulator`, `UnparseResult`, `resolve_spacing_specs`, and `Renderer`.
2. A generator `fltk/unparse/gsm2unparser_rs.py` (`RustUnparserGenerator`) that emits
   one `.rs` file: a pure-Rust `Unparser` plus a `#[cfg(feature = "python")]`
   `PyUnparser` wrapper.
3. CLI + Makefile + `LibSpec` wiring, and a test fixture + cross-backend parity
   harness.

The existing Python `UnparserGenerator` and the `fltk/unparse/*` runtime modules are
**not** touched. We follow the parser-backend precedent of writing a separate
string-emitting generator rather than retargeting the IIR; this keeps the Python
backend (and its public API) at zero risk and keeps the two generators
side-by-side auditable, exactly as `gsm2parser.py` and `gsm2parser_rs.py` sit today.

### 2.1 New crate: `crates/fltk-unparser-core`

A direct, faithful port of `combinators.py`, `accumulator.py`, `resolve_specs.py`,
and `renderer.py`. No pyo3 dependency (structural absence, matching
`crates/fltk-parser-core/Cargo.toml`'s comment). It needs no `fltk-cst-core`
dependency either: the runtime operates on `Doc`, not on spans — terminal text is
extracted in the *generated* code (which depends on `fltk-cst-core`) and handed in
as `Doc::text(String)`.

Modules:

- `doc.rs` — the `Doc` enum with the same ~15 variants as the Python hierarchy:
  `Text(String)`, `Comment(String)`, `Line`, `Nbsp`, `SoftLine`,
  `HardLine { blank_lines: u32 }`, `Group(Rc<Doc>)`, `Nest { indent: u32, content: Rc<Doc> }`,
  `Concat(Vec<Rc<Doc>>)`, `Join { docs: Vec<Rc<Doc>>, separator: Rc<Doc> }`, `Nil`,
  `AfterSpec { spacing: Rc<Doc> }`, `BeforeSpec { spacing: Rc<Doc> }`,
  `SeparatorSpec { spacing: Option<Rc<Doc>>, preserved_trivia: Option<Rc<Doc>>, required: bool }`.
  Children are `Rc`-wrapped so accumulator clones and resolve-pass rewrites share
  structure cheaply, mirroring Python's frozen-dataclass sharing. Helper
  constructors (`text`, `concat` with Nil/Concat flattening as in
  `combinators.py:172`, `hardline`, `group`, `nest`, `join`) port the Python helpers.
- `accumulator.rs` — `DocAccumulator` as an immutable persistent structure: an
  `Rc`-linked `DocNode { doc, tail }` chain plus `last_was_trivia`, optional
  `parent`, and optional `nesting_doc`, exactly as `accumulator.py`. Methods:
  `add_non_trivia`, `add_trivia`, `add_accumulator`, `push_group`/`pop_group`,
  `push_nest`/`pop_nest`, `push_join`/`pop_join`, and `doc(&self) -> Doc` (the
  flatten-to-`concat` property at `accumulator.py:116`). `Clone` is cheap (Rc bumps).
  The pop-mismatch invariants (`accumulator.py:75`, `:81`, `:87`) become `Result`
  or `panic!` with the same diagnostic; these fire only on generator bugs.
- `resolve.rs` — `resolve_spacing_specs(doc: &Doc) -> Doc` and the private passes
  (`_expand_joins`, `_extract_all_boundary_specs`, `_resolve_patterns` with the
  ordered pattern mutators, `_collapse_hardline_sequences`, `_merge_spacing`). This
  is a literal port of `resolve_specs.py`; the deque-based working set becomes a
  `VecDeque<Rc<Doc>>`.
- `render.rs` — `RendererConfig { indent_width: usize, max_width: usize }`
  (defaults 4/80, matching `renderer.py:22`) and `Renderer::render(&self, doc: &Doc) -> String`,
  a port of the queue-based Wadler-Lindig algorithm and its `_fits` helper. The
  Python renderer is already iterative (queue, not call stack); the port preserves
  that.
- `result.rs` — `UnparseResult { accumulator: DocAccumulator, new_pos: usize }`
  (port of `pyrt.py:16`), plus a `doc()` convenience.
- `lib.rs` — re-exports the public surface.

Add `"crates/fltk-unparser-core"` to the root workspace `members` in `Cargo.toml`.

### 2.2 New generator: `fltk/unparse/gsm2unparser_rs.py`

`RustUnparserGenerator(grammar, formatter_config=None, cst_mod_path="super::cst", source_name=None)`.
Like `RustParserGenerator`, it internally constructs a `RustCstGenerator` to reuse
trivia processing and the static naming helpers (`child_enum_name`, `label_enum_name`,
`class_name_for_rule`, `rule_has_labels`). `generate() -> str` is idempotent
(memoized, per `gsm2parser_rs.py:225`).

The emitted algorithm is a re-expression of `UnparserGenerator` from
IIR-building-Python into string-emitting-Rust. The control structure is identical;
only the target API changes. Per-construct mapping:

- **Rule entry** (`gsm2unparser.py:190`): emit
  `pub fn unparse_{rule}(&self, node: &cst::{CN}) -> Option<UnparseResult>` that
  creates `let mut acc = DocAccumulator::new();`, applies any RULE_START anchor ops
  (group/nest/join begin), then dispatches alternatives starting at `pos = 0`,
  applying RULE_END anchor ops (pop) on success.
- **Alternatives / items / quantified loops** (`:721`, `:533`, `:1561`): emit private
  methods `unparse_{rule}__alt{N}`, `__item{M}`, `__inner` with signature
  `(&self, node: &cst::{CN}, pos: usize, acc: DocAccumulator) -> Option<UnparseResult>`.
  Accumulators are threaded by value (cheap clone); `?`-style early `return None`
  replaces the Python `if not result: return None`.
- **Child extraction + validation** (`_extract_and_validate_nonsequence_child`,
  `:254`): bounds-check `pos >= node.children().len()`; read `&node.children()[pos]`;
  if the term is labeled, check the tuple's label equals
  `Some(cst::{CN}Label::{Variant})`; then `match` the `{CN}Child` value:
  - rule-ref term → expect `cst::{CN}Child::{ChildClass}(shared)`; on a different
    variant, `return None`.
  - literal/regex term → expect `cst::{CN}Child::Span(span)`; otherwise `return None`.
  This replaces the `isinstance`/`is_span` dispatch with an exhaustive `match`.
- **Identifier term** (`:1680`): from `cst::{CN}Child::{ChildClass}(shared)`, do
  `let guard = shared.read();` and call `self.unparse_{ref_rule}(&guard)`; merge with
  `acc.add_accumulator(child_result.accumulator)`; advance `pos + 1`.
- **Literal term** (`:1719`): `acc.add_non_trivia(Doc::text("<literal>"))`; advance
  `pos + 1` only for INCLUDE disposition (matching `:1740`).
- **Regex term** (`:1750`): read text via the span: `span.text()`. Because the Rust
  CST has no `terminals` fallback, a `None` here (sourceless span) makes the rule
  `return None` (see §3). On `Some(t)`: `acc.add_non_trivia(Doc::text(t))`.
- **Nested alternatives / sub-expression** (`:1791`): emit `__alts` method, same as
  the parser backend's sub-expression handling.
- **Suppressed quantified items** (`_gen_suppressed_quantified_item_body`, `:485`):
  optional → emit nothing; required literal → emit `Doc::text`; required
  regex/identifier → raise `RuntimeError`/`ValueError` at generation time, identical
  messages to `:514`/`:520`.
- **Trivia processing** (`_gen_trivia_processing`, `:1084`): port both branches.
  Trivia rules consume unlabeled `cst::{CN}Child::Span` whitespace children and count
  newlines; non-trivia rules look for a `cst::{CN}Child::Trivia(shared)` child, call
  the generated `unparse__trivia`, and wrap preserved output in a `SeparatorSpec`. The
  `_has_preservable_trivia`, `_count_newlines`, `_count_newlines_in_trivia` utility
  methods (`:846`, `:931`, `:971`) port to Rust methods; `_count_newlines(span)`
  becomes `span.text().map(|t| t.matches('\n').count()).unwrap_or(0)`.
- **Anchors / spacing / dispositions**: generation-time `FormatterConfig` queries
  (`get_anchor_config`, `get_after_spacing`, `get_before_spacing`,
  `get_item_disposition`, `get_spacing_for_separator`) are reused unchanged — the
  generator imports `fltk.unparse.fmt_config`. Their `Doc` results are emitted as Rust
  `Doc` constructor expressions by a `_doc_to_rust_expr(doc)` helper that mirrors
  `_doc_to_combinator_expr` (`:396`) **exactly**: it covers `Nil`, `Nbsp`, `Line`,
  `SoftLine`, `HardLine{blank_lines}`, `Text`, and `Concat`, and raises the same
  `ValueError("Unknown Doc type: …")` on anything else — including `Group`, `Nest`, and
  `Join`. This matters for join separators: a `.fltkfmt` `join … by group(…)` /
  `nest(…)` / `join(…)` yields a `Group`/`Nest`/`Join` separator `Doc`
  (`fmt_config.py:_doc_literal_cst_to_doc:408-419`, reached via `_process_join_statement`
  `:708`), and the **Python** backend already *rejects* such a config at generation time
  through that `ValueError` (the JOIN_BEGIN separator is fed to `_doc_to_combinator_expr`
  at `gsm2unparser.py:240`, `:1512`, `:1556`). The Rust helper must reject it
  identically rather than silently emit a `Doc::Group/Nest/Join`, or the two backends
  diverge (Python errors, Rust generates and formats). Extending separator support to
  group/nest/join is out of scope here and would have to be a deliberate
  both-backends change, not an incidental Rust-only superset.
- **Item-level anchor operations** (`_gen_anchor_operations_before_item` `:1472`,
  `_gen_anchor_operations_after_item` `:1517`, both invoked from
  `gen_alternative_unparser` at `:1602`/`:1656`): in addition to the rule-level
  RULE_START/RULE_END anchors handled at "Rule entry", the Python unparser emits
  accumulator push/pop at *item* granularity for label-/literal-selected anchors. These
  are accumulator **state transitions**, not `Doc` results, so they are not covered by
  the `_doc_to_rust_expr` framing above. Emit them parallel to the rule-level case:
  GROUP_BEGIN / NEST_BEGIN / JOIN_BEGIN → `acc = acc.push_group()` /
  `acc.push_nest(indent)` / `acc.push_join(sep)`, and GROUP_END / NEST_END / JOIN_END →
  `acc = acc.pop_group()` / `acc.pop_nest()` / `acc.pop_join()`, threaded into the
  alternative's accumulator immediately before/after each item, exactly as the Python
  helpers do (SPACING ops are skipped here — already handled by before/after-item
  spacing). This is the path that implements `group from label:X to label:Y`,
  `nest from … to …`, and `join from … to …`; the `push_join` separator goes through the
  same `_doc_to_rust_expr` and therefore inherits the group/nest/join rejection above.

The generated struct is a unit struct (`pub struct Unparser;`) with `Unparser::new()`
taking no arguments: the `FormatterConfig` is baked in and `terminals` is unnecessary.
Render config is supplied at render time, not construction.

String/identifier escaping reuses the parser backend's `_rust_str_lit`
(`gsm2parser_rs.py:59`) for literal text and source-name comments.

File header: `use fltk_unparser_core::{DocAccumulator, Doc, UnparseResult, RendererConfig, Renderer, resolve_spacing_specs};`
and the CST import (`use super::cst;` or `use {cst_mod_path} as cst;`), mirroring
`gsm2parser_rs._gen_header`.

### 2.3 PyO3 wrapper layer

A `#[cfg(feature = "python")] mod python_bindings { ... }` block emitted by a
`_gen_python_bindings()` method, paralleling `gsm2parser_rs.py:883`:

- `#[pyclass(name = "Unparser")] struct PyUnparser { inner: Unparser }` with
  `#[new] fn new() -> Self`.
- Per rule, a method that runs the **full pipeline** and returns the formatted string:

  ```rust
  #[pyo3(signature = (node, max_width = 80, indent_width = 4))]
  fn unparse_{rule}(&self, node: PyRef<'_, cst::Py{CN}>, max_width: usize, indent_width: usize)
      -> PyResult<Option<String>> {
      let guard = node.shared().read();
      let Some(r) = self.inner.unparse_{rule}(&guard) else { return Ok(None); };
      let resolved = resolve_spacing_specs(&r.accumulator.doc());
      let cfg = RendererConfig { indent_width, max_width };
      Ok(Some(Renderer::new(cfg).render(&resolved)))
  }
  ```

  The wrapper accepts only the Rust CST handle `cst::Py{CN}` (via `PyRef`), unwraps
  `shared()` and read-locks it, exactly as the parser bindings unwrap handles
  (constraint in exploration §"Parser Python Bindings Constraint"). A pure-Python CST
  object is rejected by pyo3's argument extraction, enforcing the "pair Rust unparser
  with Rust parser" rule.
- `pub fn register_classes(module) -> PyResult<()>` registering `PyUnparser`, plus the
  `#[cfg(feature = "python")] pub use python_bindings::register_classes;` re-export.

The Python-visible class name is `Unparser` and the methods are `unparse_{rule}`,
preserving the public symbol names from the Python backend (CLAUDE.md "public API",
exploration §"Out-of-Tree Consumer API"). Two deliberate, documented differences from
the Python backend's Python surface remain — both called out here rather than left as
incidental side effects: (1) the constructor — Python's `Unparser(terminals)` vs Rust's
`Unparser()` — blessed by the requirements because Rust spans carry their own source;
and (2) the per-rule method's return type and signature — see §2.4.

### 2.4 Python-facing API contract

The Rust PyO3 `unparse_{rule}(node, max_width=80, indent_width=4) -> PyResult<Option<String>>`
runs the full pipeline (unparse → resolve → render) in Rust and returns the formatted string.
This is a **deliberate, documented divergence** from the Python backend, whose
`Unparser.unparse_{rule}(node) -> Optional[UnparseResult]` (`gsm2unparser.py:198`)
returns an intermediate `UnparseResult` that the caller must itself feed through
`resolve_spacing_specs` + `Renderer.render` (that chaining lives in
`plumbing.unparse_cst`/`render_doc`, `plumbing.py:302`, `:336`, not in the generated
class). We accept this divergence rather than mirror the Python method's return type
because the intermediate `Doc`/`UnparseResult` are pure-Rust types with no PyO3 bindings
in this design; mirroring the Python contract would require wrapping the whole `Doc`
hierarchy (and `UnparseResult`) in pyo3, which the requirements do not ask for. The
cross-backend contract is therefore **rendered-string parity**, not per-method
return-type parity, and rendered-string parity is exactly what the parity tests (§4)
assert. Returning the rendered string is consistent with the requirement that the
pipeline must run ("producing strings directly without the formatting pipeline is not
acceptable" forbids *skipping* the pipeline, not returning its final product).

Migration note for out-of-tree Python consumers: moving a call site from the Python
unparser to the Rust unparser changes both the constructor (§2.3) and the per-rule call
shape — `r = unp.unparse_x(node); doc = resolve_spacing_specs(r.accumulator.doc);
render_doc(doc, cfg)` becomes `unp.unparse_x(node, max_width, indent_width)`. This is a
called-out, bounded change at a small number of sites, not the wholesale annotation/
call-site churn CLAUDE.md forbids. Whether to *additionally* expose the intermediate
`Doc` to Python (an additive surface, not a replacement for the string method) is
open question 2.

A pure-Rust consumer chains the stages directly: `unparse_{rule}(node)` →
`resolve_spacing_specs(&r.accumulator.doc())` → `Renderer::new(cfg).render(&doc)`. The
core deliberately keeps the per-rule methods Doc-producing (not string-producing) so
Rust consumers retain access to the intermediate Doc and resolution stages; the
string convenience lives only in the PyO3 layer, matching how the Python driver
(`plumbing.unparse_cst` + `render_doc`) — not the generated class — owns the chaining.

### 2.5 CLI / Makefile / LibSpec wiring

- `genparser.py`: add `gen-rust-unparser`:
  ```
  gen-rust-unparser GRAMMAR OUTPUT [--cst-mod-path super::cst] [--format-config FILE.fltkfmt]
  ```
  Parse the grammar raw (`_parse_grammar_raw`), optionally parse the format file via
  `fltk.plumbing.parse_format_config_file` into a `FormatterConfig`, build
  `RustUnparserGenerator`, write `generate()`. `--cst-mod-path` is validated by the
  existing `_CST_MOD_PATH_RE`. Errors (`ValueError`/`RuntimeError`) map to
  `typer.Exit(1)`, as the sibling subcommands do.
- `Makefile`: add a `gen-rust-unparser` target mirroring `gen-rust-parser`, wire the
  fixture's unparser regeneration into `gencode`, and add the fixture's unparser to the
  clippy/`cargo test` lanes. The new crate joins the `cargo clippy`/`cargo test
  --no-default-features` lanes and (since it has no pyo3) is implicitly covered by the
  `check-no-pyo3` cargo-tree assertion through the fixture graph.
- `gsm2lib_rs.py`: generalize `LibSpec.standard(module_name, *, with_parser=True,
  with_unparser=False)` to append `Submodule("unparser", "unparser")` when requested,
  and add a `--unparser` flag to `gen-rust-lib`. `register_fn` stays `register_classes`,
  consistent with the existing two-submodule convention (exploration
  §"LibSpec.standard Two-Submodule Convention").

### 2.6 Test fixture

Extend the existing `tests/rust_parser_fixture/` crate (it already hosts `cst.rs` +
`parser.rs` for `rust_parser_fixture.fltkg`): add a generated `unparser.rs`, declare
`pub mod unparser;` in `lib.rs`, and register it under the `python` cfg. The fixture
already exercises literals, regex terminals, labels, all quantifiers, WS-required and
WS-allowed separators, sub-expressions, union labels, suppress/include, and left
recursion — a broad unparser surface. Add a small `.fltkfmt` format config for this
grammar to exercise spacing defaults, before/after anchors, rule-level group/nest/join,
and at least one *item-level* (label- or literal-anchored) `group`/`nest`/`join from …
to …` range operation, so the non-trivial pipeline paths — including the item-level
push/pop anchor path (§2.2) — are covered, not just default spacing and rule-wide
ranges. The fixture's
`Cargo.toml` gains `fltk-unparser-core = { path = "../../crates/fltk-unparser-core" }`.

## 3. Edge cases / failure modes

- **Deep Doc trees (stack safety).** The Doc tree depth is proportional to CST depth,
  which is attacker-controlled for parsers over untrusted input — the same hazard that
  forced iterative `Drop`/`PartialEq`/`Debug` in the Rust CST
  (`gsm2tree_rs.py:1039` ff.). `resolve_spacing_specs` recurses through
  `Concat`/`Group`/`Nest`, and the natural `Drop` for an `Rc<Doc>` chain recurses too.
  Python hits a catchable `RecursionError`; an unguarded Rust port would hit an
  *uncatchable* stack-overflow abort. Decision for this design: (a) give `Doc` an
  iterative `Drop` (worklist drain, cheap, matches the CST precedent — this matters
  because Drop fires on the happy path); (b) treat `resolve`/`render` recursion-depth
  hardening as deferred, since the renderer is already iterative and resolve mirrors
  Python's recursion exactly, so initial parity is preserved. Scope of (b) is open
  question 1.
- **Sourceless spans (`span.text()` → None).** Hand-built CSTs or `Span::unknown()`
  leaves yield no text. With no `terminals` fallback available, an INCLUDE literal/regex
  whose span returns `None` makes the enclosing rule `unparse` return `None` (failure),
  rather than silently emitting empty text. This mirrors the Python guard that a
  source-bearing span returning `None` is an error (`pyrt.py:47`); CSTs produced by the
  Rust parser always carry source, so this is an off-the-happy-path safeguard.
- **Required suppressed regex / identifier.** Cannot be reconstructed from the CST;
  the generator raises at generation time with the same messages as the Python backend
  (`gsm2unparser.py:514`, `:520`). Required suppressed literals are reconstructed from
  the literal text.
- **Union labels.** A label spanning multiple child types is handled by matching the
  specific `{CN}Child` variant the term expects; a mismatched variant yields `return
  None` for that alternative, letting the next alternative be tried — the same control
  flow as the Python `isinstance` failure path.
- **Unparse failure → next alternative.** A `None` from any item makes the alternative
  return `None`; the rule tries the next alternative and ultimately returns `None`,
  identical to the Python semantics. The PyO3 layer surfaces this as `Ok(None)`.
- **Lock discipline.** Traversal only read-locks `Shared<T>` children and performs no
  Python callbacks mid-walk (it builds a Rust `Doc`), so holding nested read guards
  down the tree is safe and deadlock-free. The render config and the GIL are the only
  external state; no node is mutated.
- **Generation drift.** Committed fixture `.rs` files must equal generator output; the
  existing `make gencode` + `git diff` discipline catches hand-patches.

## 4. Test plan

After this work the following tests exist:

- **`fltk-unparser-core` unit tests** (`#[test]`, GIL-free): `Doc` construction and
  `concat` flattening; `DocAccumulator` add/merge and push/pop group/nest/join,
  including pop-mismatch panics; `resolve_spacing_specs` for after/before/sep merge,
  join expansion, standalone-spec collapse, preserved-trivia precedence, and HardLine
  collapsing; `Renderer` flat-vs-break group decisions, nest indentation, HardLine
  blank-line counts, and width-driven breaking. Cases are seeded from the existing
  Python suites (`test_resolve_specs.py`, `test_renderer.py`, `test_unparser.py`).
- **Generator tests** (Python, e.g. `tests/test_rust_unparser_generator.py`): generated
  source contains the expected per-rule methods and structures (smoke); generation
  raises on required-suppressed-regex; idempotent `generate()`.
- **Cross-backend parity** (`tests/test_rust_unparser_parity_fixture.py`, with
  `pytest.importorskip("rust_parser_fixture")`): a shared corpus of `(rule, text)`,
  parsed with both backends (capture_trivia=True), unparsed with both, rendered to
  strings with matching `RendererConfig`, asserted byte-equal — run with both the
  default `FormatterConfig` and the fixture `.fltkfmt`. A small parity helper module
  (`tests/unparser_parity.py`) factors the dispatch, analogous to `parser_parity.py`.
  Corpus includes bounded nesting depths to exercise recursion without triggering the
  deep-tree limit.
- **Native fixture test** (`rust_parser_fixture` `native_tests.rs`): build a CST via the
  native Rust API, run the core unparser GIL-free, assert the rendered string —
  proving the core links and runs with no Python runtime.

## 5. Open questions

1. **Deep-tree stack-safety scope.** This design hardens `Doc::drop` iteratively but
   defers iterative `resolve_spacing_specs`/`render` (they mirror Python's recursion;
   the renderer is already iterative). Is parity-first acceptable for this milestone
   with a `TODO(unparser-deep-tree)` for hardening `resolve` against adversarial depth,
   or must adversarial-depth safety be in scope now (matching the CST's iterative
   teardown bar)?
2. **Additionally exposing the intermediate `Doc` to Python.** §2.3/§2.4 settle the
   PyO3 surface on a rendered-string return; that decision is made. Beyond it: should the
   PyO3 layer *also* expose the resolved `Doc` (or per-stage handles) — e.g. to render at
   multiple widths without re-walking the CST, or to inspect formatting — which would
   require wrapping the `Doc` hierarchy in pyo3? This is purely additive; the
   string-returning method stays regardless of the answer.
3. **`.pyi` stub for the unparser's Python surface.** The CST backend emits a `.pyi`
   for `CstModule` conformance; the unparser has no such protocol. Should we emit a
   `.pyi` so downstream code gets a type-checked `Unparser` surface, or leave it
   untyped for now?

Answers from user:

1. Leaving resolve_spacing_specs recursive is fine for now.
2. Please expose the intermediate Doc.
3. Yes, emit .pyi.
