# Exploration: Phase 2 — Rust Parser Generator

Style note: concise, precise, token-dense. Audience: smart LLM/human. No padding.

---

## 1. Phase 2 scope (from approved design)

`docs/adr/2026/06/10-rust-parser-codegen/design.md` §6 specifies:

> Phase 2 — generator, pure-Rust output: `gsm2parser_rs.py`, `gen-rust-parser` CLI,
> fixture crate `parser.rs` compiling python-off and python-on, Rust-side parse tests
> (test plan item 2).

No Python bindings in Phase 2 (those are Phase 3). The output is a `.rs` file that:
- Compiles with `--no-default-features` (pure Rust, no pyo3)
- Compiles with `default` features (pyo3-on) for Phase 3
- Uses `fltk-parser-core` (Phase 1 runtime, now committed at `crates/fltk-parser-core/`)
- Uses the CST data struct API from generated `cst.rs` (Phase 1 CST work)

---

## 2. Python parser generator: gsm2parser.py

**File:** `fltk/fegen/gsm2parser.py` — 832 lines. Emits IIR, compiled by the Python backend to Python source.

### 2.1 Class: `ParserGenerator`

Constructor (`__init__`, lines 27–253):
- Takes `grammar: gsm.Grammar`, `cstgen: gsm2tree.CstGenerator`, `context: CompilerContext`
- Calls `gsm.classify_trivia_rules(grammar)` immediately (line 33)
- Builds `self.parser_class: iir.ClassType` named `"Parser"`
- Registers `Packrat[IndexInt, IndexInt]`, `TerminalSource`, `SourceText`, `ErrorTracker[IndexInt]` as fields
- Defines `consume_literal` and `consume_regex` as methods on the parser class via IIR
- Iterates all rules in two passes: first builds `parsers` dict with `_make_parser_info` (assigns rule IDs via `rule_id_seq = itertools.count()`), then generates code bodies via `gen_alternatives_parser`

### 2.2 Named parsers dict + ParserFn dataclass

`ParserFn` (lines 19–26):
```python
@dataclass
class ParserFn:
    name: str            # "parse_rule_name"
    apply_name: str      # "apply__parse_rule_name" (memoized) or same as name
    cache_name: str | None   # "_cache__parse_rule_name" or None
    result_type: iir.Type
    rule_id: int | None
    inline_to_parent: bool
```

`self.parsers: dict[tuple[str, ...], ParserFn]` — keyed by path tuple; top-level rule is `("rule_name",)`, an alternative parser is `("rule_name", "alt0")`, an item parser is `("rule_name", "alt0", "item0")`, a subexpressions alternatives parser is `("rule_name", ..., "alts")`.

### 2.3 Generated Python parser structure (from fltk_parser.py sample)

`fltk/fegen/fltk_parser.py` (generated from `fegen.fltkg`, 14 rules):

**Constructor** (`__init__`):
- Fields: `terminalsrc`, `_source_text`, `packrat: Packrat[int,int]`, `error_tracker: ErrorTracker[int]`, `rule_names: Sequence[str]` (list of 14 rule name strings in rule-id order), then one `_cache__parse_<rule>: MutableMapping[int, MemoEntry[...]]` per rule (initialized as `{}`)

**`consume_literal(self, pos, literal)`** (lines 78–86):
- Calls `self.terminalsrc.consume_literal(pos, literal)` → span on success
- On success: returns `ApplyResult(pos=span.end, result=Span.with_source(span.start, span.end, self._source_text))`
- On failure: calls `self.error_tracker.fail_literal(pos, rule_id=self.packrat.invocation_stack[-1], literal=literal)`, returns `None`

**`consume_regex`** (lines 88–96): symmetric

**Per-rule methods** (pattern across all 14 rules):
- `parse_<rule>(self, pos)` — tries each alt in order, returns first success or `None`
- `apply__parse_<rule>(self, pos)` — calls `self.packrat.apply(rule_callable=self.parse_<rule>, rule_id=<N>, rule_cache=self._cache__parse_<rule>, pos=pos)`
- `parse_<rule>__alt<N>(self, pos)` — the alternative body
- `parse_<rule>__alt<N>__item<M>(self, pos)` — delegates to consume_literal/consume_regex/apply__parse_<child>

**Alternative body pattern** (from `parse_rule__alt0`, lines 150–182):
```python
def parse_rule__alt0(self, pos):
    _span_start: int = pos
    result: fltk_cst.Rule = fltk_cst.Rule(span=Span.with_source(pos, -1, self._source_text))
    if item0 := self.parse_rule__alt0__item0(pos=pos):
        pos = item0.pos
        result.append_name(child=item0.result)
    else:
        return None
    if ws_after__item0 := self.apply__parse__trivia(pos=pos):
        pos = ws_after__item0.pos
    # ... more items and separators ...
    result.span = Span.with_source(_span_start, pos, self._source_text)
    return ApplyResult(pos=pos, result=result)
```

**Multiple-item (`+`/`*`) pattern** (from `parse_grammar__alt0__item0`, lines 128–140):
```python
def parse_grammar__alt0__item0(self, pos):
    _span_start: int = pos
    result: fltk_cst.Grammar = fltk_cst.Grammar(span=Span.with_source(pos, -1, self._source_text))
    while one_result := self.apply__parse_rule(pos=pos):
        pos = one_result.pos
        result.append_rule(child=one_result.result)
    if pos == _span_start:
        return None  # + quantifier: must advance
    result.span = Span.with_source(_span_start, pos, self._source_text)
    return ApplyResult(pos=pos, result=result)
```

**Suppressed item / separator**: `if ws_after__item0 := self.apply__parse__trivia(pos=pos): pos = ws_after__item0.pos` — no append to result. SUPPRESS disposition skips the append call even on success.

**`extend_children`**: used when `item_parser.inline_to_parent == True` (sub-expression alternatives or `*`/`+` multiple-item parsers that return the parent node type rather than a child node).

### 2.4 Separator handling (gsm2parser.py:606–683)

`_gen_separator_handling` dispatches on `separator: gsm.Separator`:
- `NO_WS`: no code emitted (line 629)
- `WS_ALLOWED`: emit `if ws := self.apply__parse__trivia(pos=pos): pos = ws.pos` (or for trivia rules: `if ws := self.consume_regex(pos, r"\s+")`)
- `WS_REQUIRED`: same as `WS_ALLOWED` but with `orelse=True` — the else branch emits `return None`

For trivia rules (rule.is_trivia_rule == True, line 641): uses `consume_regex(r"\s+")` directly to avoid trivia recursion. For non-trivia rules: uses `apply__parse__trivia`.

**Initial separator** (line 754): handled for each alternative before its items.
**Separators after items** (line 807): handled after each item.

### 2.5 gsm2parser.py key methods

- `gen_alternatives_parser` (line 685): top-level dispatcher, tries each alt
- `gen_alternative_parser` (line 722): single alternative body
- `gen_item_parser` (line 475): dispatches to single/optional or multiple
- `gen_item_parser_single_or_optional` (line 483): single delegating call
- `gen_item_parser_multiple` (line 505): while-loop with progress check for `+`
- `_gen_consume_term_expr` (line 303): dispatches on `gsm.Identifier`/`gsm.Literal`/`gsm.Regex`/`Sequence[Items]`; raises `NotImplementedError` for `gsm.Invocation`/`Expression` (line 374)
- `_make_parser_info` (line 380): creates `ParserFn`, assigns rule_id from sequence counter, registers in `self.parsers`

---

## 3. GSM model (gsm.py)

**File:** `fltk/fegen/gsm.py`

Key types the generator consumes:

```
Grammar(rules: Sequence[Rule], identifiers: Mapping[str, Rule])
Rule(name: str, alternatives: Sequence[Items], is_trivia_rule: bool = False)
Items(items: Sequence[Item], sep_after: Sequence[Separator], initial_sep: Separator = NO_WS)
Item(label: str|None, disposition: Disposition, term: Term, quantifier: Quantifier)
```

`Term = Invocation | Identifier | Literal | Regex | Sequence[Items]`
- `Identifier(value: str)` — reference to another rule
- `Literal(value: str)` — string literal
- `Regex(value: str)` — regex pattern
- `Sequence[Items]` — sub-expression (parenthesized alternatives)

`Disposition`: `SUPPRESS` / `INCLUDE` / `INLINE`
`Quantifier` subclasses: `Required` (1..1), `NotRequired` (0..1), `OneOrMore` (1..*), `ZeroOrMore` (0..*). API: `.is_optional()`, `.is_required()`, `.is_multiple()`, `.min() -> Arity`, `.max() -> Arity`

`Separator` enum: `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`

`TRIVIA_RULE_NAME: Final[str] = "_trivia"` (line 16)

`classify_trivia_rules(grammar)` (line 273): marks `Rule.is_trivia_rule` for all rules reachable from `_trivia`. Must be called before generator; the generator calls it in its constructor.

---

## 4. fltk-parser-core runtime crate (Phase 1, now committed)

**Location:** `crates/fltk-parser-core/`
**Cargo.toml** (lines 1–17): `crate-type = ["rlib"]`; no `python` feature; deps: `fltk-cst-core` (default-features=false), `regex = "1"`.

### 4.1 Public API (lib.rs, lines 1–27)

Re-exports:
```rust
pub use regex;  // generated code uses fltk_parser_core::regex::Regex
pub use errors::{format_error_message, ErrorTracker, ParseContext, TokenType};
pub use memo::{apply, ApplyResult, Cache, MemoEntry, MemoResult, PackratState, RecursionInfo};
pub use terminalsrc::{LineColPos, TerminalSource};
```

### 4.2 memo.rs types

```rust
pub struct ApplyResult<T> { pub pos: i64, pub result: T }  // Clone, Debug, PartialEq
pub struct RecursionInfo { pub rule_id: u32, pub involved: HashSet<u32>, pub eval_set: HashSet<u32> }
pub enum MemoResult<T> { Poison(Option<RecursionInfo>), Value(T), Failure }
pub struct MemoEntry<T> { pub result: MemoResult<T>, pub final_pos: i64 }
pub type Cache<T> = HashMap<i64, MemoEntry<T>>;
#[derive(Debug, Default)]
pub struct PackratState { pub invocation_stack: Vec<u32>, recursions: HashMap<i64, RecursionInfo> }
```

The core function (lines 102–109):
```rust
pub fn apply<P, T: Clone>(
    parser: &mut P,
    rule_id: u32,
    pos: i64,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
    rule: fn(&mut P, i64) -> Option<ApplyResult<T>>,
) -> Option<ApplyResult<T>>
```

- `P` = generated `Parser` struct
- `state` = non-capturing fn pointer projector: `|p| &mut p.packrat_state`
- `cache` = per-rule fn pointer projector: `|p| &mut p.cache_parse_grammar`
- `rule` = the rule body: `Parser::parse_grammar`

### 4.3 terminalsrc.rs types

```rust
pub struct TerminalSource { source: SourceText, cp_to_byte: Vec<usize>, line_ends: OnceLock<Vec<i64>> }
pub struct LineColPos { pub line: i64, pub col: i64, pub line_span: Span }
```

Key methods:
- `TerminalSource::new(text: &str) -> Self`
- `TerminalSource::from_source_text(source: SourceText) -> Self`
- `source_text(&self) -> &SourceText` — used at span-construction sites
- `len(&self) -> i64` — codepoint count
- `consume_literal(&self, pos: i64, literal: &str) -> Option<Span>` — returns source-bearing span
- `consume_regex(&self, pos: i64, regex: &Regex) -> Option<Span>` — uses `find_at`, anchors by checking `m.start() == byte_pos`; TODO(consume-regex-anchor) in the source

### 4.4 errors.rs types

```rust
pub enum TokenType { Literal, Regex }
pub struct ParseContext { pub rule_id: u32, pub token_type: TokenType, pub token: &'static str }
#[derive(Debug)]
pub struct ErrorTracker { pub longest_parse_len: i64, pub expected_context: Vec<ParseContext> }
impl Default for ErrorTracker  // longest_parse_len: -1
```

Methods: `fail_literal(&mut self, pos: i64, rule_id: u32, literal: &'static str)`, `fail_regex(...)`.

Free function: `format_error_message(tracker: &ErrorTracker, terminals: &TerminalSource, rule_names: &[&str]) -> String`

**Critical constraint**: `token: &'static str` — all literal and regex strings from the generated parser must be `'static` (string literals in the generated `.rs` source, which they will be).

---

## 5. CST data struct API the generated parser builds against

From `gsm2tree_rs.py` generated output (sampled from `tests/rust_cst_fixture/src/cst.rs` and `tests/rust_cst_fegen/src/cst.rs`):

Each rule `foo` generates:
- `pub enum FooLabel { LabelA, LabelB, ... }` (only if rule has labels; dual-cfg python/not-python blocks)
- `pub enum FooChild { Span(Span), Bar(Shared<Bar>), Baz(Shared<Baz>), ... }`
- `pub struct Foo { span: Span, children: Vec<(Option<FooLabel>, FooChild)> }` (private fields)

**Construction API** (always compiled, GIL-free, `impl Foo`):
```rust
pub fn new(span: Span) -> Self
pub fn set_span(&mut self, span: Span)
pub fn span(&self) -> &Span
pub fn kind(&self) -> NodeKind
pub fn children(&self) -> &[(Option<FooLabel>, FooChild)]
pub fn push_child(&mut self, label: Option<FooLabel>, child: FooChild)
pub fn child(&self) -> Result<&(Option<FooLabel>, FooChild), CstError>
pub fn extend_children(&mut self, other: &Self)
// Per-label (for each label `lbl`):
pub fn children_lbl(&self) -> impl Iterator<Item = &Shared<T>> + '_  // or &Span
pub fn child_lbl(&self) -> Result<&Shared<T>, CstError>
pub fn maybe_lbl(&self) -> Result<Option<&Shared<T>>, CstError>
pub fn append_lbl(&mut self, child: impl Into<Shared<T>>)  // or Span
pub fn extend_lbl(&mut self, children: impl IntoIterator<Item = impl Into<Shared<T>>>)
```

**`Shared<T>`** (`crates/fltk-cst-core/src/shared.rs`): `Arc<RwLock<T>>` newtype. `Shared::new(value)`, `.read()`, `.write()`, `.ptr_eq()`, `.arc_ptr()`. `Clone` is shallow (Arc clone). `From<T> for Shared<T>` — so `append_lbl(node)` where `node: T` works via `.into()`.

**`Span`** (`crates/fltk-cst-core/src/span.rs`):
- `Span::unknown()` — `Span(-1,-1, source=None)`
- `Span::new_sourceless(start: i64, end: i64)`
- `Span::new_with_source(start: i64, end: i64, source: &SourceText)`
- `span.start() -> i64`, `span.end() -> i64`
- `PartialEq` ignores source (lines 168–172)

**Generated parser constructs nodes as:**
```rust
let mut result = Foo::new(Span::new_with_source(pos, -1, self.terminals.source_text()));
// ... after successful items:
result.set_span(Span::new_with_source(span_start, pos, self.terminals.source_text()));
```

---

## 6. gsm2tree_rs.py — reference for generator structure and Rust emission style

**File:** `fltk/fegen/gsm2tree_rs.py` — 1533 lines.

### 6.1 RustCstGenerator class (line 39)

Constructor: takes raw `gsm.Grammar`; calls `classify_trivia_rules(add_trivia_rule_to_grammar(grammar, context))` internally. Instantiates `CstGenerator` for type info (`self._py_gen`).

Identifier/label validation loop (lines 60–80): checks `_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")`, raises `ValueError` with the offending name.

### 6.2 Emission helpers

`_rule_info(self) -> list[tuple[str, list[str], str]]` (line 82): returns `(class_name, sorted_labels, rule_name)` for every rule. `class_name` comes from `self._py_gen.class_name_for_rule_node(rule.name)`.

`_child_variants_for_rule(self, rule_name) -> tuple[list[str], bool]` (line 110): returns `(sorted_child_class_names, has_span_child)` — used to emit `XChild` enum and decide which match arms exist.

### 6.3 generate() (line 239)

```python
def generate(self) -> str:
    parts = []
    parts.append(self._preamble())
    parts.append(self._node_kind_block())
    for class_name, labels, rule_name in self._rule_info():
        parts.append(self._label_enum_block(class_name, labels))
        parts.append(self._child_enum_block(class_name, rule_name))
        parts.append(self._node_block(class_name, labels, rule_name))
    parts.append(self._register_classes_fn())
    return "\n".join(parts)
```

### 6.4 Preamble (lines 261–279)

```rust
use fltk_cst_core::CstError;
use fltk_cst_core::Span;
use fltk_cst_core::Shared;
#[cfg(feature = "python")] use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};
#[cfg(feature = "python")] use fltk_cst_core::registry;
// ... pyo3 imports all gated #[cfg(feature = "python")]
```

### 6.5 Dual-cfg enum pattern (lines 344–368)

NodeKind and label enums emit **two full enum definitions**: one with `#[cfg(feature = "python")] #[pyclass(...)]` and pyo3 variant attrs, one with `#[cfg(not(feature = "python"))]` plain. Rationale documented in `_node_kind_block`: pyo3 0.23 `cfg_attr` on variant helper attrs fires before proc-macro expansion.

### 6.6 Naming helpers (lines 29–34)

```python
def _rust_variant_name(label: str) -> str:
    return naming.snake_to_upper_camel(label)  # 'no_ws' -> 'NoWs'

def _python_label_name(label: str) -> str:
    return label.upper()  # 'no_ws' -> 'NO_WS'
```

Label enum Rust name: `f"{class_name}Label"` (method `_label_enum_rust_name`, line 406). Python-visible name: `f"{class_name}_Label"` (preserved for out-of-tree compat).

### 6.7 `_label_type_info` (line 1038)

Returns `(return_ref_type: str, single_node_class_name_or_None: str|None, total_enum_variants: int)`:
- Single Span-typed label → `("&Span", None, total)`
- Single node-typed label → `(f"&Shared<ClassName>", "ClassName", total)`
- Union label (multiple types) → `(f"&{ClassName}Child", None, total)`

### 6.8 `_native_per_label_methods` (line 1071)

Emits native (GIL-free) per-label accessors on the data struct. The `need_wildcard` check (e.g. line 1099) avoids emitting `_ => None` in `filter_map` when there is only one child enum variant (prevents `clippy::unnecessary_filter_map`).

---

## 7. Generator plumbing (genparser.py)

**File:** `fltk/fegen/genparser.py` — 349 lines. Typer CLI.

Existing `gen-rust-cst` command (line 264):
```
genparser gen-rust-cst <grammar.fltkg> <output.rs> [--protocol-module X] [--pyi-output Y]
```
- Calls `_parse_grammar_raw(grammar_file)` (line 253) — does NOT apply `add_trivia_rule_to_grammar`; `RustCstGenerator` does it internally
- Instantiates `gsm2tree_rs.RustCstGenerator(grammar)`, calls `.generate()`

The new `gen-rust-parser` command (design §3.2) follows the same shape:
```
genparser gen-rust-parser <grammar.fltkg> <output.rs> [--cst-mod-path super::cst]
```

### 7.1 `parse_grammar_file` vs `_parse_grammar_raw`

`parse_grammar_file` (line 65): calls `add_trivia_rule_to_grammar` + `classify_trivia_rules`. Used by the Python parser generator path.
`_parse_grammar_raw` (line 253): does NOT apply trivia processing. Used for Rust CST generator (which does it internally).

The Rust parser generator will need its own choice. The Python `ParserGenerator` calls `classify_trivia_rules` in its constructor (line 33). `RustCstGenerator` calls `classify_trivia_rules(add_trivia_rule_to_grammar(grammar, context))` in its constructor (lines 47–53). The Rust parser generator similarly must do both, internally.

---

## 8. Fixture crate layout (existing pattern)

Two fixture crates for CST:
- `tests/rust_cst_fixture/` — from `fltk/fegen/test_data/phase4_roundtrip.fltkg`
- `tests/rust_cst_fegen/` — from `fltk/fegen/fegen.fltkg`

Both are **standalone workspaces** (excluded from root workspace, `[workspace]` at top of Cargo.toml). Both are `crate-type = ["cdylib"]` for Python extension use. Both have feature gates:
```toml
[features]
default = ["extension-module"]
extension-module = ["python", "pyo3/extension-module"]
python = ["fltk-cst-core/python"]
```

`lib.rs` pattern: `mod cst;` + `#[pymodule] fn <name>(m) { m.add_class::<Span>(); m.add_class::<SourceText>(); cst::register_classes(m)?; }`.

The parser fixture crate (new in Phase 2) will add `mod parser;` and expose `register_classes` from both `cst` and `parser` modules. The design specifies the fixture is `tests/rust_cst_fegen` extended (or a new fixture), with `src/cst.rs` (already present) + `src/parser.rs` (new).

**Pure-Rust tests in the fixture** (`tests/rust_cst_fixture/src/native_tests.rs`): `#[cfg(test)] mod tests { ... }` with `use crate::cst::{...}` imports; no `Python::with_gil`. These are `cargo test`-only, not Python tests.

---

## 9. Build / Makefile wiring (existing pattern)

`Makefile` (extracted lines 94–138):

```makefile
build-fegen-rust-cst:
	cd tests/rust_cst_fegen && uv run --group dev maturin develop

gen-rust-cst:  # GRAMMAR=... RS_OUT=...
	uv run python -m fltk.fegen.genparser gen-rust-cst $(GRAMMAR) $(RS_OUT)

gencode:  # regenerates all generated code
	# ... calls gen-rust-cst for fixture crates ...
```

`check-no-pyo3` stanza (existing for `fltk-cst-core`, `fltk-cst-spike`, `fltk-parser-core`):
```makefile
parser="$(cargo tree -p fltk-parser-core --edges normal,build)"
echo "$$parser" | grep -q fltk-cst-core  # positive control
! echo "$$parser" | grep -q pyo3          # negative assertion
```

`cargo-test-no-python` already includes `cargo test -q -p fltk-parser-core`.

The Phase 2 additions per design §3.4:
- New Makefile target `gen-rust-parser` (parallel to `gen-rust-cst`)
- `gencode` extended with a `gen-rust-parser` call for the fixture crate
- Fixture crate `cargo test` wired into `cargo-test` (workspace member or separate call)
- `check-no-pyo3` extended with the fixture parser crate pure-Rust check

---

## 10. Existing test files that supply the parity corpus

Located under `fltk/fegen/`:
- `test_regression_toplevel_recursion.py` — left-recursive grammars (exercises the packrat seed-grow)
- `test_regression_recursive_inlining.py` — recursive + inline items
- `test_regression_empty_nary.py` — `*` quantifier zero iterations
- `test_regression_ws_required.py` — `WS_REQUIRED` separator failure
- `test_regression_subexpr_separators.py`
- `test_regression_error_reporting.py`
- `test_regression_line_col_error.py`
- `test_leading_separators.py` — initial_sep handling
- `test_trivia_capture.py` — `capture_trivia=True` variant
- `test_trivia_whitespace_capture.py`

These supply inputs for the Phase 3 parity corpus (design §5 item 3). Phase 2 generates Rust-side tests that parse similar inputs pure-Rust.

---

## 11. CstGenerator shared front-end (reuse point)

`gsm2tree_rs.py` already imports from `gsm2tree.CstGenerator`:

```python
from fltk.fegen.gsm2tree import CstGenerator, ModelType
```

Line 49: `self._py_gen = CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)`

Key `CstGenerator` methods used by `RustCstGenerator`:
- `self._py_gen.rule_models[rule_name]` — `ModelType` with `.types`, `.labels`
- `self._py_gen.class_name_for_rule_node(rule_name) -> str`
- `self._py_gen.node_kind_member_name(rule_name) -> str`
- `self._py_gen.protocol_annotation_for_model_types(...)` (for pyi generation)

`gsm2parser_rs.py` reuses the same pattern: instantiates `CstGenerator` to obtain `class_name_for_rule_node` and `rule_models` for type-directed child append decisions (design §2.1 — the generator knows whether a label is span-typed, single-node-typed, or union).

From `gsm2tree.py` (`CstGenerator`), the `rule_models[name].types` is a list of `ModelType` values; `ModelType` is a string (rule name) for node-typed children or a `TypeKey` for span-typed children.

---

## 12. Naming helpers (naming.py)

`from fltk.fegen import gsm, naming` (already used in `gsm2tree_rs.py` line 12).

`naming.snake_to_upper_camel(s)` — used for label → CamelCase Rust variant name.
`_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")` (gsm2tree_rs.py line 18) — used for validation; `gsm2parser_rs.py` reuses same validation logic.

---

## 13. Open factual questions

None identified. The design is fully specified; the code context above provides concrete detail for every structural decision the implementer needs:
- GSM walk logic: §2.3–2.5 above
- Runtime call sites: §4 above
- CST construction API: §5 above
- Generator class shape: §6 above
- CLI plumbing: §7 above
- Fixture crate layout: §8 above
- Build wiring: §9 above
