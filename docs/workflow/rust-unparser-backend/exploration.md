# Exploration: Rust Unparser Backend

## Code Surface

### Python-Only Unparser Generator

**`fltk/unparse/gsm2unparser.py`**

- `class UnparserGenerator` (line 30): main generator. Constructor signature:
  ```python
  def __init__(self, grammar: gsm.Grammar, context: CompilerContext,
               cst_module: str, formatter_config: FormatterConfig | None = None)
  ```
  Receives `cst_module` as a dotted Python import path (e.g., `"fltk.unparse.toy_cst"`). Registers one
  `iir.Type` per CST rule class into the compiler context; those types carry the module + class name
  and drive every generated `isinstance` check and annotation in the emitted Python.

- `generate_unparser(grammar, context, cst_module, formatter_config) -> tuple[iir.ClassType, list[ast.stmt]]`
  (line 1827): module-level entry function. Returns the IIR class and a list of `import`/`from … import`
  AST nodes. The `iir.ClassType` is then compiled to a Python `ast.ClassDef` by
  `fltk.iir.py.compiler.compile_class()`.

- Generated class name: always `Unparser`.

- Class fields (set in `_setup_unparser_class`, line 176):
  - `terminals: str` — initialized from constructor parameter.

- Public rule-level methods (one per grammar rule, `_generate_rule_unparser`, line 190):
  ```python
  def unparse_{rule_name}(self, node: {ClassName}) -> Optional[UnparseResult]
  ```
  Entry point: called with the CST root node for that rule. Starts at child position 0.

- Internal helper methods (generated for each alternative, item, quantified loop, etc.):
  ```python
  def unparse_{rule_name}__alt{N}(self, node, pos: int, accumulator: DocAccumulator) -> Optional[UnparseResult]
  def unparse_{rule_name}__alt{N}__item{M}(self, node, pos, accumulator) -> Optional[UnparseResult]
  def unparse_{rule_name}__alt{N}__item{M}__inner(self, node, pos, accumulator) -> Optional[UnparseResult]
  ```
  The `pos` integer is an index into `node.children`.

- Fixed utility methods (always generated, `_gen_has_preservable_trivia_method` etc.):
  - `_has_preservable_trivia(self, trivia_node: Trivia) -> bool` (line 846)
  - `_count_newlines(self, span: Span) -> int` (line 931) — delegates to `fltk.unparse.pyrt.count_span_newlines`
  - `_count_newlines_in_trivia(self, trivia: Trivia) -> int` (line 971)

**`fltk/unparse/genunparser.py`**

- `main()` (line 108): CLI entry point. Accepts `grammar.fltkg [format.fltkfmt source.toy]`.
  When given just a grammar, runs `generate_unparser(grammar, context, "fltk.unparse.toy_cst")` and
  prints `ast.unparse(module)` to stdout. No equivalent Rust codegen subcommand exists here yet.

**`fltk/plumbing.py`**

- `generate_unparser(grammar, cst_module_name, formatter_config) -> UnparserResult` (line 257):
  High-level driver. Calls `gsm2unparser.generate_unparser()`, compiles to AST, `exec`s the
  resulting Python module, and wraps the `Unparser` class in `UnparserResult`.

- `unparse_cst(unparser_result, cst, terminals, rule_name) -> Doc` (line 302):
  Instantiates `unparser_result.unparser_class(terminals)`, calls `unparse_{rule_name}(cst)`,
  then runs `resolve_spacing_specs(result.accumulator.doc)`.

- `UnparserResult` (in `fltk/plumbing_types.py`, line 36):
  ```python
  @dataclass
  class UnparserResult:
      unparser_class: type
      grammar: gsm.Grammar
      formatter_config: FormatterConfig
      trivia_config: TriviaConfig
  ```

---

### Rust Parser Backend (reference implementation of the split pattern)

**`fltk/fegen/gsm2tree_rs.py` — `RustCstGenerator`** (line 167)

Constructor: `RustCstGenerator(grammar: gsm.Grammar, source_name: str | None = None)`.
Internally wraps a `CstGenerator` (Python CST generator) to reuse naming logic.

- `generate() -> str` (line 446): returns a complete `.rs` file.
- `generate_pyi(protocol_module: str) -> str` (line 310): returns a `.pyi` stub.
- Static naming helpers (all public, called by `gsm2parser_rs.py`):
  - `child_enum_name(class_name) -> str` → `"{ClassName}Child"` (line 763)
  - `py_handle_name(class_name) -> str` → `"Py{ClassName}"` (line 772)
  - `label_enum_name(class_name) -> str` → `"{ClassName}Label"` (line 668)

**`fltk/fegen/gsm2parser_rs.py` — `RustParserGenerator`** (line 95)

Constructor: `RustParserGenerator(grammar, cst_mod_path="super::cst", source_name=None)`.
Internally creates a `RustCstGenerator` to share naming.

- `generate() -> str` (line 225): idempotent; second call returns memoized string.
- Generates two layers in the same file:
  1. Pure-Rust layer (always compiled): `pub struct Parser`, `apply__{rule_name}()` methods,
     per-rule `parse_{rule_name}()` methods, `parse_{rule_name}__alt{N}__item{M}()` helpers.
  2. Python layer: `#[cfg(feature = "python")] mod python_bindings { … }` (line 896–1015)
     containing `PyParser`, `PyApplyResult`, per-rule `apply__{rule_name}` PyO3 methods, and
     `register_classes(module)`.
  The function `_gen_python_bindings()` (line 883) emits the entire gated block as a string.

**`fltk/fegen/gsm2lib_rs.py` — `RustLibGenerator`** (line 100)

- `LibSpec` dataclass (line 53): `module_name`, `submodules: tuple[Submodule, …]`,
  `register_span_types: bool`, `unknown_span_static: bool`.
- `LibSpec.standard(module_name, *, with_parser=True)` (line 70): convenience constructor.
  With `with_parser=True`: `submodules = [Submodule("cst", "cst"), Submodule("parser", "parser")]`.
- `RustLibGenerator(spec).generate() -> str`: emits `use`, `mod`, and `#[pymodule]` boilerplate.
- Currently no `with_unparser` parameter.

**`fltk/fegen/genparser.py` — CLI**

Three Rust-related subcommands (lines 270–483):
- `gen-rust-cst grammar_file output_file [--protocol-module …] [--pyi-output …]`
- `gen-rust-parser grammar_file output_file [--cst-mod-path …]`
- `gen-rust-lib output_file --module-name … [--no-parser] [--no-cst] [--register-span-types] [--unknown-span-static]`

No `gen-rust-unparser` subcommand exists.

---

## Schemas / Contracts

### CST Node Access Pattern (Python Unparser)

The generated Python unparser accesses CST nodes exclusively through:

1. `node.children` — a list of `(label_or_None, value)` 2-tuples (line 287 in gsm2unparser.py):
   - `child_tuple[0]` — label (compared against `{ClassName}.Label.{LABEL}` enum value or `None`)
   - `child_tuple[1]` — value (Span or node reference)
2. `len(node.children)` — for bounds checking (via `_get_children_count`, line 624)
3. `isinstance(value, NodeType)` — for type-checking node-typed children (line 334)
4. `fltk.unparse.pyrt.is_span(value)` — for recognizing span children of either backend (line 380)
5. `fltk.unparse.pyrt.extract_span_text(span, self.terminals)` — for text of Regex/Literal terms (line 1764)
6. `fltk.unparse.pyrt.count_span_newlines(span, self.terminals)` — for trivia newline counting (line 964)

The current Python unparser does NOT use:
- `node.span`
- `node.kind`
- Any per-label typed accessors (`child_foo()`, `children_foo()`, etc.)

### Rust CST Data Struct Layout (generated by `gsm2tree_rs.py`)

Each rule `{rule_name}` → class `{ClassName}`:

```rust
pub struct {ClassName} {
    span: Span,
    children: Vec<(Option<{ClassName}Label>, {ClassName}Child)>,
}
```

Child value enum (file: `cst.rs`, emitted by `_child_enum_block`, line 796):
```rust
pub enum {ClassName}Child {
    Span(Span),                              // terminal (Literal/Regex)
    {ChildClass}(Shared<{ChildClass}>),      // one variant per referenced rule
}
```

Label enum (emitted by `_label_enum_block`, line 687; only when rule has labels):
```rust
pub enum {ClassName}Label {
    {RustVariant},   // e.g. NoWs for label "no_ws"
    …
}
```

Native Rust API on `impl {ClassName}` (emitted in `_node_block`, starting line 1112):
- `pub fn new(span: Span) -> Self`
- `pub fn span(&self) -> &Span`
- `pub fn set_span(&mut self, span: Span)`
- `pub fn children(&self) -> &[(Option<{ClassName}Label>, {ClassName}Child)]`
- `pub fn push_child(&mut self, label: Option<{ClassName}Label>, child: {ClassName}Child)`
- `pub fn extend_children(&mut self, other: &{ClassName})`
- `pub fn child(&self) -> Result<&(…, {ClassName}Child), CstError>`
- Per-label: `pub fn append_{label}(…)`, `pub fn extend_{label}(…)`, `pub fn children_{label}(…)`, `pub fn child_{label}(…)`, `pub fn maybe_{label}(…)`

PyO3 handle (gated `#[cfg(feature = "python")]`, emitted in `_node_block`):
```rust
pub struct Py{ClassName} {
    inner: Shared<{ClassName}>,
}
```
The handle exposes `pymethods` for `.span`, `.span =`, `.children`, `.append()`, `.extend()`,
`.extend_children()`, `.child()`, per-label accessors, `__eq__`, `__hash__`, `__repr__`, `kind`.

### `fltk_cst_core::Span` (file: `crates/fltk-cst-core/src/span.rs`)

Native Rust `Span` struct fields:
```rust
pub struct Span {
    pub(crate) start: i64,
    pub(crate) end: i64,
    pub(crate) source: Option<Arc<SourceTextInner>>,
}
```

Key methods:
- `Span::new_with_source(start: i64, end: i64, source: &SourceText) -> Span`
- `Span::new_sourceless(start: i64, end: i64) -> Span`
- `Span::unknown() -> Span` (sentinel: start=-1, end=-1, no source)
- `span.text() -> Option<String>` — `None` for sourceless, out-of-range, or invalid offsets; `Some(text)` otherwise
- `span.start() -> i64`, `span.end() -> i64`
- `span.has_source() -> bool`

Public exports from `crates/fltk-cst-core/src/lib.rs` (line 18):
```rust
pub use span::{resolve_line_col, LineColPos, SourceText, Span, SpanError};
pub use shared::Shared;
pub use error::CstError;
pub use registry;   // only with cfg(feature = "python")
pub use cross_cdylib::{extract_span, …};  // only with cfg(feature = "python")
```

`Shared<T>` = `Arc<RwLock<T>>` (from `crates/fltk-cst-core/src/shared.rs`).

### `UnparseResult` (runtime type, `fltk/unparse/pyrt.py`, line 16)

```python
@dataclass(frozen=True, slots=True)
class UnparseResult:
    accumulator: DocAccumulator
    new_pos: int
```

`DocAccumulator` (from `fltk/unparse/accumulator.py`, line 18):
- Immutable linked-list of `Doc` nodes plus nesting state (`last_was_trivia`, `parent`, `nesting_doc`).
- `add_non_trivia(doc) -> DocAccumulator`
- `add_trivia(doc) -> DocAccumulator`
- `add_accumulator(other) -> DocAccumulator`
- `push_group()`, `push_nest(indent)`, `push_join(separator)` / `pop_*()` for formatter config
- `.doc` property → `concat(docs)` or `NIL`

`Doc` hierarchy (from `fltk/unparse/combinators.py`):
- `Text(content: str)`, `Comment(content: str)`, `Line`, `Nbsp`, `SoftLine`, `HardLine(blank_lines=0)`
- `Concat(docs: tuple[Doc, …])`, `Group(content: Doc)`, `Nest(content: Doc, indent: int)`, `Join(docs: tuple, separator: Doc)`
- `AfterSpec(spacing: Doc)`, `BeforeSpec(spacing: Doc)`, `SeparatorSpec(spacing, preserved_trivia, required)`

No Rust equivalents of these types exist in the codebase.

### `fltk.unparse.pyrt` helper functions (line 34, 53, 61)

```python
def extract_span_text(span: Span, terminals: str) -> str
def count_span_newlines(span: Span, terminals: str) -> int
def is_span(obj: object) -> bool
```

- `extract_span_text`: for Rust spans calls `span.text()`; for Python sourceless spans slices `terminals[span.start:span.end]`.
- `is_span`: recognizes both `terminalsrc.Span` (always) and `fltk._native.Span` (lazily, only if `fltk._native` already imported).
- No Rust equivalents exist.

---

## Invariants / Constraints

### Out-of-Tree Consumer API (per CLAUDE.md)

- Generated unparser class name `Unparser` is public API; renaming is a breaking change.
- Method names `unparse_{rule_name}(node)` are public API for out-of-tree consumers.
- The `cst_module_name` parameter in `generate_unparser()` / `plumbing.generate_unparser()` is the
  dotted Python import path the generated unparser imports CST node classes from.
- A generated Rust unparser would need to pair with the Rust CST from the same grammar; the pairing
  is at compile time via Cargo features, not at Python import time.

### Feature-Gate Invariant (from `Cargo.toml` and test fixture `Cargo.toml`)

- `python` feature: enables all PyO3 code; does NOT imply `extension-module`.
- `extension-module` feature: implies `python` + `pyo3/extension-module`; required for `cdylib` linking.
- `test-introspection` feature: implies `python`; adds registry snapshot function.
- The check `check-no-pyo3` (`Makefile` line ~160) asserts pyo3 is absent from all `--no-default-features` dependency graphs.

### Parser Python Bindings Constraint (parser.rs `_gen_python_bindings`, line 883)

The PyO3 wrapper's per-rule apply method calls `cst::Py{ClassName}::to_py_canonical(py, &r.result)?`
to convert a `&Shared<{ClassName}>` into a Python object via the canonical-wrapper registry. Any
analogous PyO3 wrapper for the unparser must unwrap a Python handle (e.g., `Py{ClassName}`) to
get `Shared<{ClassName}>` and lock-read it before calling the native unparser.

### `LibSpec.standard()` Two-Submodule Convention (`gsm2lib_rs.py`, line 70)

Standard consumer crates get exactly two submodules: `cst` and `parser`. The lib.rs generator would
need a new `with_unparser` parameter (or a third `Submodule` entry) for an unparser submodule.
Current convention: `register_fn = "register_classes"` on every `Submodule`.

### Cargo Workspace Layout (root `Cargo.toml`, line 2)

```toml
[workspace]
members = [".", "crates/fltk-cst-core", "crates/fltk-parser-core"]
```

Test fixtures are independent workspaces (their `Cargo.toml` has `[workspace]` at the top).
A new `fltk-unparser-core` crate would be added to the root workspace members.
Each fixture crate that gains an unparser would add it as a `members` entry in its own workspace.

---

## Build / Codegen Entry Points

### Makefile targets (Makefile, lines ~85–155)

| Target | Command |
|--------|---------|
| `gen-rust-cst` | `uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT) $(EXTRA_ARGS)` |
| `gen-rust-parser` | `uv run python -m fltk.fegen.genparser gen-rust-parser $(GRAMMAR) $(RS_OUT)` |
| `gen-rust-lib` | `uv run python -m fltk.fegen.genparser gen-rust-lib $(RS_OUT) --module-name …` |
| `build-rust-parser-fixture` | `cd tests/rust_parser_fixture && uv run maturin develop --features extension-module` |
| `gencode` | runs all `gen-rust-*` targets and Python codegen; then `ruff check --fix` + `ruff format` |

No `gen-rust-unparser` Makefile target or `genparser.py` subcommand exists.

### `pyproject.toml` (not read; entry point scripts)

The `genparser` CLI is invoked as `uv run python -m fltk.fegen.genparser`.

### `crates/fltk-parser-core/Cargo.toml` (no Python dependency)

Referenced by all generated parser crates as:
```toml
fltk-parser-core = { path = "../../crates/fltk-parser-core" }
```
Contains: `PackratState`, `ErrorTracker`, `TerminalSource`, `Cache`, `apply`, `ApplyResult`,
`DEFAULT_MAX_DEPTH`, and `regex_automata` re-export.

A `fltk-unparser-core` crate would be a parallel new crate under `crates/` with no Python dependency,
containing unparser runtime types analogous to the Python `DocAccumulator`, `Doc`, and related
combinators — or alternatively just a String output abstraction.

---

## Existing Tests

### Unparser tests (`fltk/unparse/test_*.py`)

- `test_unparser.py`: integration tests using `plumbing.generate_parser` + `generate_unparser` + `unparse_cst` + `render_doc` on the toy grammar.
- `test_unparser_edge_cases.py`, `test_initial_sep_unparser.py`: edge-case coverage.
- Many feature-specific tests: `test_control_nodes.py`, `test_fmt_config.py`, `test_group_support.py`, `test_nest_support.py`, `test_join_support.py`, `test_after_directive.py`, `test_omit_functionality.py`, `test_resolve_specs.py`, `test_renderer.py`, `test_is_span_guard.py`, `test_nest_fmt_config.py`, etc.
- No test exercises the unparser against a Rust CST (all use Python-backend CSTs).

### Rust Parser Backend Tests

- `tests/test_rust_parser_parity_fixture.py`: `@pytest.mark.parametrize` over `_CORPUS` of (rule, text, expected) triples; runs `_py_parser` and `_rust_parser` side-by-side via `run_parity_corpus_entry` from `tests/parser_parity.py`.
- `tests/test_rust_parser_bindings.py`, `tests/test_rust_parser_fixture_bindings.py`: binding-level tests.
- `tests/test_phase4_rust_fixture.py`: AC5/AC7 API-contract tests. Tests `_rust_cst = pytest.importorskip("phase4_roundtrip_cst.cst")`. Uses `generate_unparser(_grammar, _python_pr.cst_module_name)` then `unparse_cst(ur, result.cst, result.terminals, "config")` — exercises the Python unparser with a Python-backend CST only.
- `tests/test_fegen_rust_cst.py`, `tests/test_rust_cst_poc.py`: CST-only tests (no parser or unparser).
- `tests/rust_parser_fixture/src/native_tests.rs`: pure-Rust tests (GIL-free) exercising `Parser` directly and building deep CST trees via `Shared<cst::Expr>`.

### Cross-Backend Parity Pattern (reference: `tests/parser_parity.py`)

```python
def run_parity_corpus_entry(py_parser, rust_parser, ts, rule, text, expected):
    ...
```
The same pattern (shared corpus + two parser backends) would apply to unparser parity tests.

---

## Open Factual Questions

1. **What output type does the Rust core unparser produce?** The Python unparser outputs `Doc` combinators (a tree of formatting instructions) rather than a `String`. No Rust `Doc` type exists in the codebase. Whether the Rust unparser would output `String` directly, a new `fltk-unparser-core::Doc` enum, or something else is not determined by existing code.

2. **`terminals` parameter in Python unparser vs. Rust.** The Python unparser constructor takes `terminals: str` and passes it to `pyrt.extract_span_text(span, terminals)` for sourceless Python spans. Rust spans carry their own source via `Arc<SourceTextInner>` and call `span.text()` directly (no `terminals` string needed). A Rust unparser would not need a `terminals` constructor parameter.

3. **Formatter config (`FormatterConfig`) in Rust.** The Python `FormatterConfig` drives spacing, grouping, trivia preservation, and `BeforeSpec`/`AfterSpec`/`SeparatorSpec` emission. Whether the Rust unparser would bake formatter config into generated code at generation time (as the Python unparser does) or carry a Rust runtime config struct is not determined by existing code.

4. **`genparser.py` subcommand shape.** The new `gen-rust-unparser` subcommand signature (grammar file, output file, optional `--cst-mod-path`, any formatter-config input) is not specified by existing code.

5. **`LibSpec` extension.** Whether the `with_parser` boolean is generalized to an enumerated set of submodules or simply a `with_unparser: bool` is not determined by existing code.
