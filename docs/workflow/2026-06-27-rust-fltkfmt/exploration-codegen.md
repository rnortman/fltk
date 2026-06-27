# Exploration: Rust codegen surface for a standalone fltkg formatter

Scope: Rust parser generator, Rust CST generator, Rust unparser generator (commit 6f975eb).
Out of scope: Python formatter, Cargo workspace topology.

---

## 1. Generator locations

| Generator | File | Class |
|-----------|------|-------|
| Rust CST | `fltk/fegen/gsm2tree_rs.py` | `RustCstGenerator` |
| Rust parser | `fltk/fegen/gsm2parser_rs.py` | `RustParserGenerator` |
| Rust unparser | `fltk/unparse/gsm2unparser_rs.py` | `RustUnparserGenerator` |
| lib.rs wiring | `fltk/fegen/gsm2lib_rs.py` | `RustLibGenerator` / `LibSpec` |
| CLI subcommands | `fltk/fegen/genparser.py` | `gen_rust_cst`, `gen_rust_parser`, `gen_rust_unparser`, `gen_rust_lib` |

All three generators take a raw `gsm.Grammar` (not yet trivia-processed). Each applies trivia processing internally by constructing `RustCstGenerator`, which calls `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(...))` at `gsm2tree_rs.py:176`.

---

## 2. Rust parser generation

### Generator entry

`RustParserGenerator.__init__` (`gsm2parser_rs.py:117`) accepts:
- `grammar: gsm.Grammar` — raw grammar, no trivia
- `cst_mod_path: str = "super::cst"` — Rust path to the generated CST module
- `source_name: str | None` — optional doc-comment annotation

`generate() -> str` (`gsm2parser_rs.py:240`) returns the complete `.rs` source. Idempotent (memoized at `self._generated`).

### Generated Rust public API (`parser.rs`)

**Struct `Parser`** (`gsm2parser_rs.py:372`):
```rust
pub struct Parser {
    terminals: TerminalSource,
    packrat: PackratState,
    error_tracker: ErrorTracker,
    capture_trivia: bool,
    cache__parse_{rule}: Cache<Shared<cst::{ClassName}>>,  // one per rule
}
```

**Constructor signatures** (`gsm2parser_rs.py:390`):
```rust
pub fn new(text: &str, filename: Option<&str>, capture_trivia: bool) -> Self
pub fn from_source_text(source: SourceText, capture_trivia: bool) -> Self
```

**Per-rule parse entry points** (one per grammar rule, `gsm2parser_rs.py:508`):
```rust
pub fn apply__parse_{rule}(&mut self, pos: i64) -> Option<ApplyResult<Shared<cst::{ClassName}>>>
```

**Error / depth API** (`gsm2parser_rs.py:417–448`):
```rust
pub fn terminals(&self) -> &TerminalSource
pub fn capture_trivia(&self) -> bool
pub fn rule_names(&self) -> &'static [&'static str]
pub fn error_message(&self) -> String
pub fn error_position(&self) -> Option<i64>
pub fn set_max_depth(&mut self, max_depth: u32)
pub fn max_depth(&self) -> u32
pub fn depth_exceeded(&self) -> bool
```

**Constant** (`gsm2parser_rs.py:334`): `pub const RULE_NAMES: [&str; N]`

### PyO3 wrapper (`#[cfg(feature = "python")]`, `gsm2parser_rs.py:893`)

Classes exposed: `Parser` (Python name), `ApplyResult` (Python name).
Per-rule Python methods:
```python
def apply__parse_{rule}(self, py, pos: int) -> ApplyResult | None
```
Where `ApplyResult.result` is the `Py{ClassName}` handle, `ApplyResult.pos` is `i64`.

On `depth_exceeded()`, the Python wrapper raises `RecursionError` (`gsm2parser_rs.py:994`).

### Runtime crates

Parser links against `fltk_parser_core` (provides `apply`, `ApplyResult`, `Cache`, `ErrorTracker`, `PackratState`, `TerminalSource`, `regex_automata`) and `fltk_cst_core` (provides `Shared`, `SourceText`, `Span`). No pyo3 dependency in the pure-Rust parser layer.

### Regex portability guard

Every author-written regex is validated at generation time against `fltk/fegen/regex_portability.py:check_regex_portable` before being registered in the table (`gsm2parser_rs.py:804`). The internal `\s+` trivia pattern bypasses this check. A generated `#[test] fn all_regex_patterns_compile` verifies compile-time Rust engine acceptance (`gsm2parser_rs.py:1031`).

---

## 3. Rust CST generation

### Generated Rust types (per grammar rule)

`RustCstGenerator.generate()` emits one section per rule containing:

1. **`pub enum NodeKind`** — one variant per rule, module-level (`gsm2tree_rs.py:609`). Python-visible ALL_CAPS names via `#[pyo3(name = "...")]`. Dual `#[cfg(feature = "python")]` / `#[cfg(not(...))]` blocks (same pattern repeated for label enums).

2. **`pub enum {ClassName}Label`** — (Rust CamelCase name; Python-visible as `{ClassName}_Label` via `#[pyclass(name = "...")]`) emitted only when the rule has labeled items (`gsm2tree_rs.py:698`).

3. **`pub enum {ClassName}Child`** — child value enum (`gsm2tree_rs.py:829`):
   ```rust
   pub enum {ClassName}Child {
       Span(Span),           // present iff any terminal child
       {RefClass}(Shared<{RefClass}>),  // one per referenced rule class
   }
   ```

4. **`pub struct {ClassName}`** — the CST data struct (`gsm2tree_rs.py:1045`):
   ```rust
   pub struct {ClassName} {
       span: Span,
       children: Vec<(Option<{ClassName}Label>, {ClassName}Child)>,
   }
   ```
   Fields are private; access is through the stable Rust API methods.

5. **`pub struct Py{ClassName}`** — PyO3 handle, gated `#[cfg(feature = "python")]` (`gsm2tree_rs.py:1228`):
   ```rust
   #[pyclass(frozen, weakref, name = "{ClassName}")]
   pub struct Py{ClassName} {
       inner: Shared<{ClassName}>,
   }
   ```
   Python-visible class name is `{ClassName}` (unchanged from Python CST surface).

### CST data struct stable native API (`impl {ClassName}`, `gsm2tree_rs.py:1148`)

```rust
pub fn new(span: Span) -> Self
pub fn kind(&self) -> NodeKind
pub fn span(&self) -> &Span
pub fn set_span(&mut self, span: Span)
pub fn children(&self) -> &[(Option<{ClassName}Label>, {ClassName}Child)]
pub fn push_child(&mut self, label: Option<{ClassName}Label>, child: {ClassName}Child)
pub fn child(&self) -> Result<&(Option<{ClassName}Label>, {ClassName}Child), CstError>
pub fn extend_children(&mut self, other: &Self)
// Per-label native accessors (append_{lbl}, children_{lbl}, child_{lbl}, maybe_{lbl})
```

### Handle Rust-side API (`impl Py{ClassName}`, non-pymethods, `gsm2tree_rs.py:1237`)

```rust
pub fn shared(&self) -> &Shared<{ClassName}>
pub fn to_py_canonical(py: Python<'_>, s: &Shared<{ClassName}>) -> PyResult<Py<Py{ClassName}>>
```

### Handle Python-visible API (pymethods)

Per-rule Python class `{ClassName}` exposes: `.kind`, `.span`, `.children`, `.append(child, label)`, `.extend(children, label)`, `.extend_children(other)`, `.child()`, `.insert(index, child, label)`, `.remove_at(index)`, `.replace_at(index, child, label)`, `.clear()`, and per-label quintet `append_{lbl}`, `extend_{lbl}`, `children_{lbl}`, `child_{lbl}`, `maybe_{lbl}`.

### .pyi stub (`RustCstGenerator.generate_pyi`, `gsm2tree_rs.py:321`)

Annotates every node using `_proto.{ClassName}` from the committed protocol module, and `fltk.fegen.pyrt.span_protocol.SpanProtocol` for span fields, so downstream callers need not update annotations when swapping parser backends.

### Naming invariants

- Data struct: `{ClassName}` (snake_to_upper_camel of rule name)
- PyO3 handle: `Py{ClassName}` (Rust name; Python class name is `{ClassName}`)
- Child enum: `{ClassName}Child`
- Label enum Rust name: `{ClassName}Label`; Python name: `{ClassName}_Label` (backward-compat)
- NodeKind Python name: ALL_CAPS (`rule_name.upper()`)

Collision guards at `gsm2tree_rs.py:192–266` reject reserved names (`NodeKind`, `Span`, `Shared`, etc.) and cross-rule identifier collisions at generation time.

---

## 4. Rust unparser generation (commit 6f975eb)

### Generator entry

`RustUnparserGenerator.__init__` (`gsm2unparser_rs.py:41`) accepts:
- `grammar: gsm.Grammar`
- `formatter_config: FormatterConfig | None` — spacing/anchor/disposition decisions baked at generation time; default `FormatterConfig()` when `None`
- `cst_mod_path: str = "super::cst"` — must match the CST module path used for the parser
- `source_name: str | None`

`generate() -> str` (`gsm2unparser_rs.py:69`) returns the complete `.rs` source (memoized).
`generate_pyi(protocol_module: str) -> str` (`gsm2unparser_rs.py:95`) returns a `.pyi` stub.

### Generated Rust public API (`unparser.rs`)

**Unit struct** (`gsm2unparser_rs.py:194`):
```rust
#[derive(Default)]
pub struct Unparser;
impl Unparser {
    pub fn new() -> Self { Unparser }
}
```

**Per-rule entry methods** (`gsm2unparser_rs.py:310`):
```rust
pub fn unparse_{rule}(&self, node: &cst::{ClassName}) -> Option<UnparseResult>
```
Takes a shared reference to the **data struct** (not the handle), returns `Option<UnparseResult>`.

Private helpers: `unparse_{rule}__alt{N}`, `unparse_{rule}__alt{N}__item{M}` (double-underscore names allowed by `#![allow(non_snake_case)]` at the top of the file).

**Trivia utilities** emitted once at the head of `impl Unparser` (`gsm2unparser_rs.py:281`):
```rust
fn _has_preservable_trivia(&self, _trivia_node: &cst::Trivia) -> bool
fn _count_newlines_in_trivia(&self, trivia: &cst::Trivia) -> usize
```

### Child access pattern in generated unparser

The generated per-item methods read directly from the data struct's stable API:
```rust
let children = node.children();      // &[(Option<Label>, Child)]
let child_tuple = &children[pos];
if child_tuple.0 != Some(cst::{ClassName}Label::Foo) { return None; }
let cst::{ClassName}Child::Span(span) = &child_tuple.1;
let text = span.text()?;             // Option<String> from Span::text()
```
`span.text_str()` (borrowed `&str`) is used for trivia newline counting (`unparser.rs:34`).

### Runtime crate: `fltk-unparser-core`

Located at `crates/fltk-unparser-core/`. No pyo3 dependency, no `fltk-cst-core` dependency. Public surface (`lib.rs:21–28`):
```rust
pub use accumulator::DocAccumulator;
pub use doc::{after_spec, before_spec, comment, concat, group, hardline, indent,
              join, line, nbsp, nest, nil, separator_spec, softline, text, Doc};
pub use render::{Renderer, RendererConfig};
pub use resolve::resolve_spacing_specs;
pub use result::UnparseResult;
```

`UnparseResult` (`result.rs:18`):
```rust
pub struct UnparseResult {
    pub accumulator: DocAccumulator,
    pub new_pos: usize,
}
```

### PyO3 wrapper (`#[cfg(feature = "python")]`, `gsm2unparser_rs.py:1695`)

Two Python classes: `Unparser` (name) and `Doc` (name).

**`Unparser`** — no-arg constructor; per-rule methods:
```python
def unparse_{rule}(self, node: Py{ClassName}, max_width: int = 80, indent_width: int = 4) -> str | None
def unparse_{rule}_doc(self, node: Py{ClassName}) -> Doc | None
```
The Python wrapper accepts only the **Rust CST handle** (`PyRef<'_, cst::Py{ClassName}>`), reads it via `node.shared().read()` (acquires the RwLock read guard), then calls the pure-Rust `self.inner.unparse_{rule}(&guard)`. A pure-Python CST object is rejected by PyO3 argument extraction.

Full pipeline in the string method (`gsm2unparser_rs.py:1805`):
```rust
let guard = node.shared().read();
let Some(r) = self.inner.unparse_{rule}(&guard) else { return Ok(None); };
let resolved = resolve_spacing_specs(r.accumulator.doc());
let cfg = RendererConfig { indent_width, max_width };
Ok(Some(Renderer::new(cfg).render(&resolved)))
```

**`Doc`** — `#[pyclass(name = "Doc", unsendable)]`; holds a resolved `fltk_unparser_core::Doc`; exposes `.render(max_width, indent_width) -> str` and `.__repr__()`.

### .pyi stub (unparser)

`generate_pyi` (`gsm2unparser_rs.py:95`) emits:
- `class Doc:` with `.render(max_width, indent_width) -> str` and `.__repr__()`
- `class Unparser:` with per-rule string and doc methods, `node` parameter typed as `_proto.{ClassName}`

### FormatterConfig: baked at generation time

`FormatterConfig` (`fltk/unparse/fmt_config.py`) drives all spacing/anchor/disposition decisions in the generator. It is consumed entirely during `generate()` — the emitted method bodies encode the choices statically. At runtime the only inputs are the CST node and the `max_width`/`indent_width` render parameters.

The `.fltkfmt` file format (example at `fltk/fegen/test_data/rust_parser_fixture.fltkfmt`) specifies: `ws_allowed`/`ws_required` defaults, before/after spacing per literal or label, and rule-level / item-level `group`/`nest`/`join` ranges.

---

## 5. CST wiring: parser → unparser

**Critical contract**: The pure-Rust `unparse_{rule}` method takes `&cst::{ClassName}` — the **data struct**, not the handle. The generated parser produces `Shared<cst::{ClassName}>` from `apply__parse_{rule}`. The caller must read-lock: `node.shared().read()` yields a `RwLockReadGuard<{ClassName}>` which deref-coerces to `&{ClassName}`.

Both generators must be constructed from the **same raw `gsm.Grammar`** and the same `cst_mod_path`. Both use `RustCstGenerator` internally and derive all class names, label enum names, and child enum names through the same `class_name_for_rule_node` / `child_enum_name` / `label_enum_name` helpers (`gsm2tree_rs.py:679–796`). If the CST module path drifts between parser and unparser, the generated `use super::cst;` lines point to different modules and the types do not unify at compile time.

**CST module import helper** (shared, `gsm2parser_rs.py:78`):
```python
def cst_module_import(cst_mod_path: str) -> str:
    # "use {path};" if last segment is "cst", else "use {path} as cst;"
```
Both `gsm2parser_rs._gen_header` and `gsm2unparser_rs._gen_header` call this function, preventing drift (`gsm2parser_rs.py:319`, `gsm2unparser_rs.py:185`).

**Span text extraction**: `Span::text() -> Option<String>` and `Span::text_str() -> Option<&str>` (`crates/fltk-cst-core/src/span.rs:421,433`). Returns `None` when no source is attached (sourceless / `Span::unknown()`). The unparser's item methods pattern-match on `None` (via `?`) to signal child mismatch.

---

## 6. lib.rs wiring (`gsm2lib_rs.py`)

`LibSpec.standard(module_name, with_parser=True, with_unparser=False)` (`gsm2lib_rs.py:70`) generates the standard submodule registration:
- Always: `cst` submodule
- Optional: `parser` submodule
- Optional: `unparser` submodule

Each submodule's `register_classes` function registers its PyO3 classes into a submodule. The unparser submodule registers `PyUnparser` and `PyDoc` (`gsm2unparser_rs.py:1829`).

---

## 7. CLI subcommands

All in `fltk/fegen/genparser.py`:

| Command | Input | Output |
|---------|-------|--------|
| `gen-rust-cst grammar.fltkg out.rs [--protocol-module M] [--pyi-output P]` | grammar | `cst.rs` + optional `.pyi` |
| `gen-rust-parser grammar.fltkg out.rs [--cst-mod-path P]` | grammar | `parser.rs` |
| `gen-rust-unparser grammar.fltkg out.rs [--cst-mod-path P] [--format-config F] [--protocol-module M] [--pyi-output P]` | grammar + optional `.fltkfmt` | `unparser.rs` + optional `.pyi` |
| `gen-rust-lib out.rs --module-name N [--no-parser] [--unparser]` | (no grammar) | `lib.rs` |

`_parse_grammar_raw` (`genparser.py:291`) parses the `.fltkg` without trivia processing (correct input for `RustCstGenerator`).

`--protocol-only` on the Python `generate` subcommand generates only `{base_name}_cst_protocol.py` (no CST, no parsers) — used to produce the protocol module that the Rust `.pyi` stubs reference.

---

## 8. Open factual questions

- The `Span::text()` return type is `Option<String>` (allocated). For a formatter hot path this is called once per terminal child. Whether the unparser uses `text_str()` (borrowed) in all cases or only some is partially visible: `unparser.rs:67` uses `text()?` (owned), `unparser.rs:34` uses `text_str()` (borrowed for newline counting). A standalone binary would bypass the PyO3 wrapper entirely, so the `Option<String>` allocation is the native cost.
- The `fltk-unparser-core` `Doc` type uses `Rc` internally (`gsm2unparser_rs.py:1764`: "`unsendable` because the core `Doc` uses `Rc`"). This means `Doc` and the `PyDoc` wrapper are single-threaded only. A standalone binary formatter would have the same constraint unless the core crate is changed to use `Arc`.
- Whether `Unparser` (pure-Rust) is `Send + Sync` is not stated in the generator; since it is a unit struct with no fields it should be. `DocAccumulator` thread-safety is not confirmed here.
