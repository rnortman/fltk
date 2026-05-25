# Unparser/Formatter Generation Pipeline

Concise, precise, token-dense. No fluff.

---

## 1. Code Surface

### `fltk/unparse/gsm2unparser.py` (1549 lines)

**`UnparserGenerator`** class (line 30) — main generator. Constructed once per grammar; `__init__` wires everything.

Constructor call sequence (lines 50–71):
1. `_setup_type_system()` — registers all IIR types with the Python type registry
2. Constructs `iir.ClassType` named `"Unparser"` (line 52)
3. `_setup_unparser_class()` — adds `terminals: str` field and constructor (lines 178–191)
4. Pre-registers one `UnparserFn` entry per rule (line 64–65) — ensures forward references work
5. `_gen_has_preservable_trivia_method()` (line 67)
6. `_generate_rule_unparser(rule)` for each rule (lines 69–70)

**`generate_unparser()`** (lines 1522–1549) — module-level function called by `genunparser.py`. Returns `(iir.ClassType, list[ast.Import])`. The imports list (lines 1531–1547) covers: `typing`, `fltk.unparse.combinators`, `fltk.unparse.pyrt`, `fltk.unparse.accumulator`, `fltk.unparse.resolve_specs`, the cst_module, `collections.abc`, `fltk.fegen.pyrt.terminalsrc`, plus a `from <cst_module> import <ClassName>...` for each rule.

**Key internal methods:**

| Method | Lines | Role |
|---|---|---|
| `_setup_type_system` | 72–176 | Registers `Doc`, `Span`, `UnparseResult`, `DocAccumulator`, `AfterSpec`, `BeforeSpec`, `SeparatorSpec`, `Group`, `Nest`, `Join`, one CST node type per rule — all via `pyreg.TypeInfo` |
| `_generate_rule_unparser` | 192–254 | Entry per rule: creates method `unparse_<rule_name>`, emits `DocAccumulator()`, handles rule-start anchor ops, delegates to `gen_alternatives_unparser` |
| `gen_alternatives_unparser` | 701–770 | Emits try-each-alternative code; handles rule-end anchor ops on success |
| `gen_alternative_unparser` | 1256–1362 | Emits sequential item processing with separators and trivia handling |
| `gen_item_unparser` | 440–463 | Dispatches: suppressed-quantified → `_gen_suppressed_quantified_item_body`; multi-quantified → `_gen_quantified_item_body`; else → `gen_term_unparser` |
| `gen_term_unparser` | 1364–1519 | Emits code for one term: `Identifier` (recurse into child rule), `Literal` (emit `text(literal_text)`), `Regex` (extract span text via `pyrt.extract_span_text`), `list` (nested alternatives) |
| `_gen_trivia_processing` | 929–1122 | Emits code to consume/preserve a `Trivia` CST node between items, inserting a `SeparatorSpec` |
| `_gen_has_preservable_trivia_method` | 826–909 | Emits `_has_preservable_trivia(trivia_node)` method that checks child types against `trivia_config.preserve_node_names` |
| `_doc_to_combinator_expr` | 376–406 | Converts a compile-time `Doc` value to an IIR expression referencing `fltk.unparse.combinators.*` |
| `_create_after_spec`, `_create_before_spec`, `_create_separator_spec` | 408–438 | Build IIR `Construct` expressions for control nodes |
| `_gen_anchor_operations_before_item`, `_gen_anchor_operations_after_item` | 1167–1254 | Emit `push_group`, `push_nest`, `push_join`, `pop_*` accumulator calls at label/literal anchor points |

**Generated method signatures** (constructed via IIR):
- Rule-level: `def unparse_<rule>(self, node: <CstClass>) -> UnparseResult | None`
- Sub-methods: `def unparse_<rule>__alt0__item0__inner(self, node, pos: int, accumulator: DocAccumulator) -> UnparseResult | None`

### `fltk/unparse/genunparser.py` (168 lines)

Entry point / driver. `main()` (line 104):
1. Parses `.fltkg` grammar via `fltk_parser.Parser` + `fltk2gsm.Cst2Gsm` (lines 32–48)
2. Optionally parses `.fltkfmt` format file via `unparsefmt_parser.Parser` + `fmt_config.fmt_cst_to_config` (lines 51–76)
3. Calls `generate_unparser(grammar, context, cst_module, formatter_config)` (line 149)
4. Compiles IIR class to Python AST via `compiler.compile_class(unparser_class, context)` (line 154)
5. Outputs `ast.unparse(module)` (line 160)

The compilation path is: GSM → IIR ClassType (via `gsm2unparser`) → Python AST (via `iir.py.compiler`) → source string. This is the same IIR pathway used by the parser generator.

---

## 2. Uses IIR — Not Direct Python Emission

`gsm2unparser.py` builds an **`iir.ClassType`** object (line 52) using `iir.Method`, `iir.Block`, `iir.Var`, `iir.If`, `iir.WhileLoop`, `iir.BinOp`, `iir.IsInstance`, `iir.Construct`, `iir.LiteralString`, `iir.LiteralInt`, `iir.SelfExpr`, `iir.VarByName`, `iir.MethodCall`, etc. — the full IIR expression/statement API.

The IIR is then compiled to Python AST by `fltk/iir/py/compiler.py:compile_class()` (line 77). `gsm2unparser.py` never writes a Python string or `ast.*` node directly (except the module-level import list returned by `generate_unparser()`, lines 1531–1547, which are plain `ast.Import`/`ast.ImportFrom`).

This matches how the parser is generated (same `CompilerContext`, same `pyreg.TypeInfo` registration pattern).

---

## 3. Combinator System (`fltk/unparse/combinators.py`)

All types are `@dataclass(slots=True, frozen=True)` subclasses of `Doc` (ABC, line 10).

**Leaf docs:**

| Class | Singleton | Behavior |
|---|---|---|
| `Text(content: str)` | none | Literal text |
| `Comment(content: str)` | none | Text with re-indentation on line breaks |
| `Nil` | `NIL` | Empty, produces no output |
| `Nbsp` | `NBSP` | Always space, never newline |
| `Line` | `LINE` | Space in flat mode, newline in break mode |
| `SoftLine` | `SOFTLINE` | Nothing in flat mode, newline in break mode |
| `HardLine(blank_lines: int = 0)` | `HARDLINE`, `HARDLINE_BLANK` | Always newline; `blank_lines` adds extra blank lines |

**Wrapper/structural docs:**

| Class | Fields | Behavior |
|---|---|---|
| `Group(content: Doc)` | inherits `ContentWrapper` | Tries flat; if doesn't fit, breaks all soft/hard lines within |
| `Nest(content: Doc, indent: int)` | inherits `ContentWrapper` | Increases indent by `indent * config.indent_width` on break |
| `Concat(docs: Sequence[Doc])` | inherits `DocListWrapper` | Sequential concatenation |
| `Join(docs: Sequence[Doc], separator: Doc)` | inherits `DocListWrapper` | Docs with separator between each pair |

**Control nodes (not rendered directly — consumed by `resolve_specs`):**

| Class | Fields | Role |
|---|---|---|
| `AfterSpec(spacing: Doc)` | line 221 | Spacing to apply after the preceding content |
| `BeforeSpec(spacing: Doc)` | line 232 | Spacing to apply before the following content |
| `SeparatorSpec(spacing: Doc|None, preserved_trivia: Doc|None, required: bool)` | line 241 | Fallback separator; `preserved_trivia` takes priority over `spacing` |

**Helper functions** (lines 143–218): `text()`, `line()`, `hardline()`, `group()`, `nest()`, `concat()` (flattens nested concats), `nil()`, `nbsp()`, `softline()`, `comment()`, `indent()` (= `group(nest(amount, content))`), `join()`.

---

## 4. Accumulator (`fltk/unparse/accumulator.py`)

**`DocAccumulator`** (line 18) — immutable, frozen dataclass. Fields:
- `head: DocNode | None` — singly-linked list (newest at head)
- `last_was_trivia: bool` — tracks whether the last-added item was trivia
- `parent: DocAccumulator | None` — nesting parent (for group/nest/join)
- `nesting_doc: Doc | None` — placeholder doc for the current nesting level

**`DocNode`** (line 10) — `doc: Doc`, `tail: DocNode | None`. Linked list node.

**Methods:**

| Method | Lines | What it does |
|---|---|---|
| `add_non_trivia(doc)` | 26–29 | Prepend to linked list, `last_was_trivia=False` |
| `add_trivia(doc)` | 31–34 | Prepend to linked list, `last_was_trivia=True` |
| `add_accumulator(other)` | 36–51 | Merge a *already-flattened* (no parent/nesting_doc) accumulator; raises if other has open nesting |
| `push_group()` | 53–58 | Create child accumulator with `nesting_doc=Group(NIL)` |
| `push_nest(indent)` | 60–65 | Create child accumulator with `nesting_doc=Nest(NIL, indent)` |
| `push_join(separator)` | 67–72 | Create child accumulator with `nesting_doc=Join((), separator)` |
| `pop_group()` | 74–78 | Validates nesting_doc is Group, calls `_pop()` |
| `pop_nest()` | 80–84 | Validates nesting_doc is Nest, calls `_pop()` |
| `pop_join()` | 86–90 | Validates nesting_doc is Join, calls `_pop_join()` |
| `_pop()` | 92–99 | Flattens current level's doc, wraps in nesting_doc with `replace()`, adds to parent |
| `_pop_join()` | 101–114 | Like `_pop()` but extracts Concat's docs list to populate `Join.docs` |
| `doc` (property) | 116–126 | Rebuilds Doc from linked list; reverses (since head is newest); calls `concat()`. Has a TODO: should be memoized |

The accumulator is purely immutable — every mutation returns a new instance. The generated unparser code does `accumulator = accumulator.add_non_trivia(...)` etc.

---

## 5. Renderer (`fltk/unparse/renderer.py`)

**`Renderer`** class (line 41) implements the **Wadler-Lindig pretty-printing algorithm**.

**`RendererConfig`** (line 22): `indent_width: int = 4`, `max_width: int = 80`.

**`Mode`** enum (line 29): `FLAT` / `BREAK`.

**`render(doc: Doc) -> str`** (line 47): Processes a queue of `(indent, mode, doc)` triples. Initial item: `(0, Mode.FLAT, Group(doc))` (line 74).

Doc handling per type:
- `Nil` → skip
- `Text` / `Comment` → `append_content()`; handles embedded `\n` via `break_line()`
- `Line` → space (FLAT) or newline (BREAK)
- `SoftLine` → nothing (FLAT) or newline (BREAK)
- `Nbsp` → always space
- `HardLine` → always newline(s); `1 + blank_lines` newlines total
- `Concat` → expand children in-order into queue front
- `Nest` → `new_indent = indent + doc.indent * config.indent_width`
- `Group` → calls `_fits()` to check if content fits flat; if yes push `FLAT`, else `BREAK`

**`_fits(width, items)`** (line 147): Linear scan in FLAT mode, tracks column; returns `False` immediately on `HardLine`. Groups are flattened (always `FLAT`) during the fits check. Shared `Text`/`Comment` branch (line 159): `isinstance(doc, Text | Comment)`.

Note: `Join` and control nodes (`AfterSpec`, `BeforeSpec`, `SeparatorSpec`) are **not** handled by the renderer. They must be resolved by `resolve_specs.resolve_spacing_specs()` before rendering.

---

## 6. `resolve_specs.py` — Spacing Resolution Pass

**`resolve_spacing_specs(doc: Doc) -> Doc`** (line 30) — three-pass post-processor. Called on the raw Doc from the accumulator before passing to the renderer.

**Pass 1: `_expand_joins(doc)`** (line 73) — converts `Join` nodes into `Concat` sequences with `SeparatorSpec` nodes between elements. The join separator is placed in `preserved_trivia` of the `SeparatorSpec` to give it priority (line 101).

**Pass 2: `_extract_all_boundary_specs(doc)`** (line 127) — recursively extracts leading `BeforeSpec`/`SeparatorSpec` and trailing `AfterSpec`/`SeparatorSpec` from `Concat` sequences, flattening them to the outermost level. Returns `(processed_doc, leading, trailing)`. `Group` and `Nest` children are also processed recursively, but their extracted specs float outward.

**Pass 3: `_resolve_patterns(doc)`** (line 177) — walks tree; for `Concat`, calls `_resolve_concat_patterns()`.

**`_resolve_concat_patterns(docs)`** (line 204): Sliding-window pattern matcher using a `deque`. Fills window to `max_pattern_size + 1 = 4`. Mutators in order of precedence (lines 217–230):

| Pattern | Mutator | Rule |
|---|---|---|
| AfterSpec, SeparatorSpec, BeforeSpec | `_mutate_after_sep_before` | Merge after+before via `_merge_spacing`, or use preserved trivia |
| AfterSpec, SeparatorSpec | `_mutate_after_sep` | Preserved trivia wins; else use after spacing |
| SeparatorSpec, BeforeSpec | `_mutate_sep_before` | Preserved trivia wins; else use before spacing |
| Text('\n') + SeparatorSpec | `_mutate_text_newline` | Collapse to `HARDLINE` |
| standalone SeparatorSpec | `_mutate_standalone_sep` | Use preserved_trivia or spacing; remove if both None |
| standalone AfterSpec or BeforeSpec | `_mutate_standalone_after_before` | Drop (ignored without separator) |

**`_mutate_consecutive_specs`** (line 409) — runs before other mutators; collapses runs of same-type specs. For `SeparatorSpec` pairs: if one has `preserved_trivia` and the other doesn't, the one with trivia wins.

**`_merge_spacing(s1, s2)`** (line 506) — precedence order: `HardLine` > `Line` > `Nbsp` > `SoftLine` > anything. If both are `HardLine`, uses the one with more `blank_lines`.

---

## 7. Formatting Configuration (`fltk/unparse/fmt_config.py`)

### Data Structures

**`FormatterConfig`** (line 134):
- `global_ws_allowed: Doc = NIL` — default spacing for `.`-separated (whitespace-allowed) items
- `global_ws_required: Doc = LINE` — default spacing for `:`-separated (whitespace-required) items
- `anchor_configs: dict[str, AnchorConfig]` — global anchors keyed by `"{position}:{selector_type}:{selector_value}"`
- `rule_configs: dict[str, RuleConfig]` — per-rule overrides
- `trivia_config: TriviaConfig | None`

**`RuleConfig`** (line 121):
- `ws_allowed_spacing: Doc | None`
- `ws_required_spacing: Doc | None`
- `anchor_configs: dict[str, AnchorConfig]`

**`AnchorConfig`** (line 105):
- `selector_type: ItemSelector` — LABEL | LITERAL | RULE_START | RULE_END
- `selector_value: str`
- `disposition: None | Normal | Omit | RenderAs`
- `operations: list[FormatOperation]`

**`FormatOperation`** (line 91):
- `operation_type: OperationType` — SPACING | GROUP_BEGIN | GROUP_END | NEST_BEGIN | NEST_END | JOIN_BEGIN | JOIN_END
- `spacing: Doc | None`
- `indent: int | None`
- `separator: Doc | None`

**`ItemSelector`** enum (line 43): LABEL, LITERAL, RULE_START, RULE_END.

**Item dispositions** (lines 52–77): `Normal` (singleton `NORMAL`), `Omit` (singleton `OMIT`), `RenderAs(spacing: Doc)`.

**`TriviaConfig`** (line 30): `preserve_node_names: set[str] | None`. `None` = preserve all; empty set = preserve none.

### Config Lookup

**`get_anchor_config(rule_name, position, selector_type, selector_value)`** (line 146): Merges rule-specific and global anchor configs. Merge logic (lines 184–213):
- Rule spacing overrides global spacing
- Non-END global ops come first (outside rule ops)
- Rule ops in middle
- END global ops last (for correct unwinding)

**`get_spacing_for_separator(rule_name, separator)`** (line 216): Returns `NIL` for `NO_WS`; checks rule-specific then global defaults for `WS_ALLOWED`/`WS_REQUIRED`.

**`get_item_disposition(rule_name, item)`** (line 287): Checks label anchor first, then literal anchor; returns `NORMAL` if no anchor with a disposition.

### CST-to-Config Transformation

**`fmt_cst_to_config(formatter, terminal_src)`** (line 728) — top-level converter. Iterates `formatter.children_statement()` and dispatches to:

| Statement type | Processor | Effect |
|---|---|---|
| `default` | `_process_default_statement` | Sets `ws_allowed_spacing` or `ws_required_spacing` |
| `group` | `_process_group_statement` | Adds GROUP_BEGIN/END ops at from/to anchors |
| `nest` | `_process_nest_statement` | Adds NEST_BEGIN/END ops; reads optional indent int |
| `join` | `_process_join_statement` | Adds JOIN_BEGIN/END ops; reads separator doc literal |
| `after` | `_process_after_statement` | Adds SPACING op at `after:{selector}` anchor |
| `before` | `_process_before_statement` | Adds SPACING op at `before:{selector}` anchor |
| `trivia_preserve` | `_process_trivia_preserve_statement` | Sets `config.trivia_config` |
| `omit` | `_process_omit_statement` | Sets anchor `disposition = OMIT` |
| `render` | `_process_render_statement` | Sets anchor `disposition = RenderAs(spacing)` |
| `rule_config` | inline loop | Nested rule-specific versions of above |

**`_process_range_operation`** (line 520): Handles `from/to` specs for group/nest/join. `from_spec` with `after` modifier → BEGIN placed at `"after:{anchor}"`; else `"before:{anchor}"`. Absent from_spec → `"before:rule_start:"`. Similarly for to_spec. END ops are inserted at position 0 of operations list (line 598) for proper unwinding order.

**Spacing doc literals** (`_spacing_cst_to_doc`, line 313): Maps CST tokens `nil/nbsp/bsp/soft/hard/blank` → `NIL/NBSP/LINE/SOFTLINE/HARDLINE/HardLine(n)`.

**Doc literals** (`_doc_literal_cst_to_doc`, line 346): Handles `concat_literal`, `join_literal`, `compound_literal` (group/nest), `text_literal`, `spacing` — recursive.

---

## 8. Runtime Support (`fltk/unparse/pyrt.py`)

Two exports:

**`UnparseResult`** (line 15) — frozen dataclass:
- `accumulator: DocAccumulator`
- `new_pos: int`
- `doc` property (line 28) — `return self.accumulator.doc` (backward compat)

**`extract_span_text(span: Span, terminals: str) -> str`** (line 33): `return terminals[span.start : span.end]`. Used in generated code for `Regex` terms to recover original text from the CST.

The generated unparser class also uses:
- `fltk.unparse.combinators` — `text()`, `NIL`, `HARDLINE`, etc.
- `fltk.unparse.accumulator.DocAccumulator` — created in each rule-level method
- `fltk.unparse.resolve_specs` — imported but not called from generated code directly; must be called by user code after unparsing
- `fltk.fegen.pyrt.terminalsrc.Span` — for type checks on regex/literal children

---

## 9. Complexity Comparison: Unparser vs. Parser Generation

The unparser generator (`gsm2unparser.py`, 1549 lines) is substantially more complex than a comparable parser generator would be at the same level of feature support, for the following structural reasons:

**Structural complexity sources:**

1. **Immutable accumulator threading** (lines 513–602, 1256–1362): Every item call passes `accumulator` as a parameter and returns a new `UnparseResult` containing the updated accumulator plus the new position. Position *and* accumulated Doc both flow forward through every sub-call. Parser generators only thread position.

2. **Two-phase output** (separate `resolve_specs` pass): The generated unparser produces a raw Doc with control nodes (`AfterSpec`, `BeforeSpec`, `SeparatorSpec`). A separate runtime pass (`resolve_specs.resolve_spacing_specs`) resolves them. The pattern-matching engine in `resolve_specs.py` (lines 204–287) handles 7 mutator patterns with a sliding deque window.

3. **Trivia handling** (`_gen_trivia_processing`, lines 929–1122): The generated code must dynamically detect `Trivia` CST nodes at runtime (not known at grammar compile time), check if they have preservable content, call the trivia unparser, and embed the result in a `SeparatorSpec.preserved_trivia`. This generates ~100 lines of IIR per separator position.

4. **Formatter config merge logic** (`get_anchor_config`, lines 146–213): Three-way merge (rule ops, global ops, END unwinding order) is non-trivial and required for correct group/nest nesting across global/per-rule configs.

5. **Suppressed items** (lines 465–511): Parser skips suppressed items; unparser must regenerate them from scratch or raise a `RuntimeError` if they're non-literal.

6. **Anchor-based structural operations** (`_gen_anchor_operations_before_item`, lines 1167–1210): GROUP_BEGIN/NEST_BEGIN/JOIN_BEGIN push new accumulator levels; GROUP_END/NEST_END/JOIN_END pop them. These must be emitted in the correct order around item processing.

7. **Quantified items with loop structure** (`_gen_quantified_item_body`, lines 513–602): `+`/`*` items require a while loop in generated code that re-invokes the inner unparser per occurrence, threading accumulator through the loop variable.

---

## 10. Hard Parts

1. **Join node expansion** (`_expand_joins`, lines 73–124): A `Join(docs=[...], separator=sep)` in the raw Doc must be expanded to individual docs with `SeparatorSpec(preserved_trivia=sep)` between them. The separator is placed in `preserved_trivia` (not `spacing`) to give it priority over other specs. Leading/trailing `SeparatorSpec` nodes within the join docs need special handling to not misplace separators.

2. **Spec resolution precedence** (`_merge_spacing`, lines 506–539; `_mutate_consecutive_specs`, lines 409–485): The system has a 5-level precedence ordering (HardLine > Line > Nbsp > SoftLine > Nil/other) and consecutive-spec collapsing must handle 4 cases for SeparatorSpec pairs (both trivia, only first, only second, neither).

3. **Nested nesting_doc tracking** in `DocAccumulator._pop_join` (lines 101–114): `Join.docs` must be reconstructed from a flat `Concat` produced by the linked-list accumulation. The code extracts `Concat.docs` as a list and puts it into `Join(docs=..., separator=separator)` via `replace()`.

4. **Group/Nest wrapping order at anchor points** (`get_anchor_config` merge, lines 195–207): For a global `group` encompassing the rule and a rule-specific `nest`, the rule's BEGIN op must be *inside* the group (closer to content) and its END must come *before* the global END to properly unwind. This is achieved by putting global non-END ops first, then rule ops, then global END ops.

5. **Trivia round-trip** (`_gen_trivia_processing`, lines 929–1122): The generated code checks `accumulator.last_was_trivia` to avoid double-trivia; checks bounds; checks `isinstance(child, Trivia)`; calls `_has_preservable_trivia`; calls the trivia sub-unparser; extracts `trivia_accumulator.doc`; and wraps it in `SeparatorSpec(preserved_trivia=trivia_doc)`. Each of those steps generates several IIR statements. The two fallback paths (no trivia found, trivia found but not preservable) must both add a `SeparatorSpec` with the grammar-configured default spacing instead.

6. **CST child position tracking**: Each sub-method takes `pos: int` (index into `node.children`) and returns `new_pos` in the `UnparseResult`. The rule-level method starts at 0 but child-level methods must increment pos only for INCLUDE-disposition items (not SUPPRESS). The distinction between `pos` advancing (INCLUDE) vs. not (SUPPRESS) is handled separately in `gen_term_unparser` at lines 1434–1442 and 1475–1481.
