# Parser Generation Pipeline — Exhaustive Fact Report

No fluff. All claims anchored to file:line.

---

## 1. Grammar Semantic Model (GSM)

**File:** `fltk/fegen/gsm.py`

### Data structures

| Class | Location | Fields |
|---|---|---|
| `Grammar` | gsm.py:20-22 | `rules: Sequence[Rule]`, `identifiers: Mapping[str, Rule]` |
| `Rule` | gsm.py:26-51 | `name: str`, `alternatives: Sequence[Items]`, `is_trivia_rule: bool = False`; memoised `_can_be_nil`, `_computing_nil` |
| `Separator` (Enum) | gsm.py:54-67 | `NO_WS` (`.`), `WS_REQUIRED` (`:`), `WS_ALLOWED` (`,`) |
| `Items` | gsm.py:70-98 | `items: Sequence[Item]`, `sep_after: Sequence[Separator]`, `initial_sep: Separator = NO_WS` |
| `Item` | gsm.py:101-111 | `label: str \| None`, `disposition: Disposition`, `term: Term`, `quantifier: Quantifier` |
| `Identifier` | gsm.py:114-121 | `value: str` |
| `Literal` | gsm.py:124-130 | `value: str` |
| `Regex` | gsm.py:133-154 | `value: str`, memoised `_can_be_nil` |
| `Invocation` | gsm.py:249-256 | `method_name: str`, `expression: Optional[Expression]` |
| `Var` | gsm.py:267-270 | `name: str`, `init_value: str \| None` |
| `Add` | gsm.py:262-264 | `lhs: Expression`, `rhs: Expression` |
| `Disposition` (Enum) | gsm.py:176-179 | `SUPPRESS`, `INCLUDE`, `INLINE` |
| `Quantifier` (ABC) | gsm.py:188-201 | abstract `min() -> Arity`, `max() -> Arity`; concrete subclasses below |
| `Required` | gsm.py:205-212 | min=ONE, max=ONE |
| `NotRequired` | gsm.py:216-224 | min=ZERO, max=ONE |
| `OneOrMore` | gsm.py:227-235 | min=ONE, max=MULTIPLE |
| `ZeroOrMore` | gsm.py:238-246 | min=ZERO, max=MULTIPLE |
| `Arity` (Enum) | gsm.py:182-185 | `ZERO=0`, `ONE=1`, `MULTIPLE=object()` |

**Type aliases:**
- `Term = Union[Invocation, Identifier, Literal, Regex, Sequence[Items]]` — gsm.py:157-163 (the `Sequence[Items]` case is a parenthesised sub-expression)
- `Expression = Union[Add, Invocation, Identifier]` — gsm.py:259

**Singleton constants:** `REQUIRED`, `NOT_REQUIRED`, `ONE_OR_MORE`, `ZERO_OR_MORE` at gsm.py:213,224,235,246.

**Key constant:** `TRIVIA_RULE_NAME: Final[str] = "_trivia"` — gsm.py:16.

### Validation and transformation functions

- `classify_trivia_rules(grammar)` — gsm.py:273-301. Marks rules reachable from `_trivia` as `is_trivia_rule=True`, then calls three validators.
- `validate_trivia_separation` — gsm.py:359-377. Raises if any non-trivia rule references a trivia rule by `Identifier`.
- `validate_trivia_rule_not_nil` — gsm.py:328-337. Raises if `_trivia` can match empty string.
- `validate_no_repeated_nil_items` — gsm.py:340-356. Raises if any `+` or `*` item can match empty string (infinite loop guard).
- `add_trivia_rule_to_grammar` — gsm.py:380-407. Injects a default `_trivia := content:/[\s]+/;` rule if none exists.

---

## 2. gsm2parser.py — Parser Code Generation

**File:** `fltk/fegen/gsm2parser.py` (756 lines)

### Does it emit Python strings directly?

**No.** It builds an `iir.ClassType` (IIR in-memory object graph) and populates it with `iir.Method`, `iir.Block`, `iir.If`, `iir.WhileLoop`, `iir.Var`, `iir.Return`, `iir.Assign`, etc. That IIR class is later compiled to a Python `ast.ClassDef` by `fltk/iir/py/compiler.py:compile_class`.

### Class: `ParserGenerator`

**Instantiation** — gsm2parser.py:27-210. The `__init__` does all generation work:

1. Calls `gsm.classify_trivia_rules(grammar)` — line 33.
2. Creates `iir.ClassType.make(cname="Parser", ...)` — line 42-46.
3. Registers `Packrat`, `TerminalSource`, `ErrorTracker` types in `context.python_type_registry` — lines 48-54, 61-67, 75-79.
4. Defines fields `packrat`, `terminalsrc`, `error_tracker`, `rule_names` on the IIR class — lines 56-87.
5. Defines a constructor — lines 88-98.
6. Builds two shared methods `consume_literal` and `consume_regex` in IIR — lines 100-188.
7. Pre-registers a `ParserFn` entry for every rule (first pass) — lines 195-200.
8. Calls `gen_alternatives_parser` for each rule (second pass, recursive descent over grammar structure) — lines 201-210.

### Inner dataclass: `ParserGenerator.ParserFn`

gsm2parser.py:19-26:
```python
@dataclass
class ParserFn:
    name: str           # e.g. "parse_grammar"
    apply_name: str     # e.g. "apply__parse_grammar" (memoised wrapper) or same as name
    cache_name: str | None   # e.g. "_cache__parse_grammar"
    result_type: iir.Type
    rule_id: int | None
    inline_to_parent: bool
```

### Inner dataclass: `ParserGenerator.ConsumeTermInfo`

gsm2parser.py:231-235:
```python
@dataclass(slots=True, frozen=True)
class ConsumeTermInfo:
    expr: iir.Expr
    result_type: iir.Type
    inline_to_parent: bool
```

### Method call chain

```
ParserGenerator.__init__
  gen_alternatives_parser(path=(rule.name,), ...)   [per rule]
    gen_alternative_parser(path=(rule.name, "alt0"), ...)   [per alternative]
      gen_item_parser(path=(rule.name, "alt0", "item0"), ...)   [per item]
        gen_item_parser_single_or_optional   OR   gen_item_parser_multiple
          _gen_consume_term_expr  →  returns ConsumeTermInfo with iir.Expr
      _gen_separator_handling  [per separator]
```

### _gen_parser_callable

gsm2parser.py:341-407. Creates:
1. An `iir.Method` named `parser_info.name` (the parse function body).
2. If `memoize=True`, also creates a wrapping `iir.Method` named `parser_info.apply_name` whose single statement is `return self.packrat.apply(rule_callable=self.<name>, rule_id=N, rule_cache=self._cache__<name>, pos=pos)` — lines 375-397.
3. A field `_cache__<name>: MutableMapping[int, MemoEntry[...]]` — lines 398-406.

### _gen_consume_term_expr

gsm2parser.py:237-309. Switches on term type:
- `gsm.Identifier` → calls `self.apply__parse_<rule_name>(pos=pos)` — lines 244-259.
- `gsm.Literal` → calls `self.consume_literal(pos=pos, literal="...")` — lines 260-272.
- `gsm.Regex` → calls `self.consume_regex(pos=pos, regex="...")` — lines 273-288.
- `Sequence[Items]` (sub-expression) → recursively calls `gen_alternatives_parser` and calls that method — lines 289-306.

### gen_item_parser_multiple

gsm2parser.py:439-535. Generates a while-loop in IIR:
- Initialise result node with `span.start=pos, span.end=-1`.
- `while (one_result := <consume_term_expr>):` — uses `iir.WhileLoop` with `iir.LetExpr`.
- Inside loop: `pos = one_result.pos`; then either `result.children.extend(one_result.result.children)` (if `inline_to_parent`) or `result.append_<label>(one_result.result)`.
- After loop: if `quantifier.min() != ZERO`, check `pos == result.span.start` → return `Failure` — line 512-515.
- Fix span, return `Success`.

### gen_alternative_parser

gsm2parser.py:653-756. Generates a linear sequence of item parsers in IIR:
- Creates a mutable `pos` parameter and a `result` node var.
- Calls `_gen_separator_handling` for `alternative.initial_sep` — line 677.
- For each item: creates per-item parse method via `gen_item_parser`; generates `if (item_N := self.<item_method>(pos=pos)):` block (IIR `If`).
  - On success: `pos = item_N.pos`; append or extend children.
  - On failure of required item: `else: return None`.
- After all items: fix span, `return ApplyResult(pos=pos, result=result)`.

### _gen_separator_handling

gsm2parser.py:537-614. Three modes:
- `NO_WS`: no-op.
- Trivia rule context: uses raw `consume_regex(r"\s+")` to avoid recursion — lines 573-590.
- Non-trivia context: calls `self.apply__parse__trivia(pos=pos)` — lines 592-611.
- If `WS_REQUIRED` and trivia fails: `return Failure` — line 613-614.
- If `context.capture_trivia`: appends trivia node to result — lines 585-590, 605-611.

### Naming conventions for generated methods

- `parse_<rule>` — the actual parse body.
- `apply__parse_<rule>` — memoisation wrapper; calls `self.packrat.apply(...)`.
- `parse_<rule>__alt<N>` — per-alternative parser.
- `parse_<rule>__alt<N>__item<M>` — per-item parser.
- `parse_<rule>__alt<N>__item<M>__alts` — sub-expression alternatives.
- `_cache__parse_<rule>` — `MutableMapping[int, MemoEntry[...]]` field.

---

## 3. gsm2tree.py — CST Node Class Generation

**File:** `fltk/fegen/gsm2tree.py` (303 lines)

### Does it go through IIR?

**Partially.** `CstGenerator` uses IIR types (`iir.Type.make`, `iir.Type` for type keys) to represent node types and register them in `context.python_type_registry`. However, it **does not build IIR method/block trees**. Instead it directly constructs `ast` nodes via `fltk.pygen` helpers (gsm2tree.py:95-243). It builds Python `ast.ClassDef`, `ast.FunctionDef`, and statements as string expressions passed to `pygen.stmt(...)`.

### Class: `CstGenerator`

Constructor gsm2tree.py:34-44: takes `grammar`, `py_module: pyreg.Module`, `context: CompilerContext`. For each rule, computes `rule_models[rule.name]`.

**Key methods:**

| Method | Lines | Purpose |
|---|---|---|
| `iir_type_for_rule(rule_name)` | 69-78 | Creates/caches `iir.Type.make(cname=<PascalCase>)` and registers it in `context.python_type_registry` |
| `class_name_for_rule_node(rule_name)` | 46-47 | Converts `snake_case` to `PascalCase` by splitting on `_` and capitalising each part |
| `gen_py_module()` | 95-107 | Builds an `ast.Module` with imports + one `ast.ClassDef` per rule |
| `py_class_for_model(class_name, model)` | 109-244 | Builds `ast.ClassDef` directly |
| `model_for_rule(rule, inline_stack)` | 285-303 | Computes `ItemsModel` for a rule, handling inline items recursively |
| `model_for_items(items, inline_stack)` | 259-277 | Iterates items; suppressed items contribute nothing; INLINE items fold in another rule's model |
| `model_for_alternatives(alternatives, inline_stack)` | 279-283 | Merges models across alternatives |

### Inner dataclass: `ItemsModel`

gsm2tree.py:23-30:
```python
@dataclass()
class ItemsModel:
    labels: MutableMapping[str, set[ModelType]] = ...   # label name → set of rule names or type keys
    types: set[ModelType] = ...   # all child types (union of all alternatives)
```
`ModelType = str | typemodel.TypeKey` — gsm2tree.py:19. `str` = rule name; `TypeKey` = `Span.key` for terminals.

### Generated class shape (per rule)

Each rule node class (gsm2tree.py:109-244) contains:

1. Nested `class Label(enum.Enum)` with one entry per label in alphabetical order — lines 112-115.
2. Fields (generated as string stmts):
   - `span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan` — line 126.
   - `children: list[tuple[Optional[Label], <child_union_type>]] = dataclasses.field(default_factory=list)` — lines 127-130.
3. Methods (built as `ast.FunctionDef` via `pygen.function`):
   - `append(self, child, label=None)` — lines 138-143.
   - `extend(self, children, label=None)` — lines 146-151.
   - `child(self)` — lines 154-168.
   - For each label `lbl`:
     - `append_<lbl>(self, child)` — lines 171-177.
     - `extend_<lbl>(self, children)` — lines 179-187.
     - `children_<lbl>(self) -> Iterator[...]` — lines 189-204.
     - `child_<lbl>(self) -> T` — lines 206-220 (asserts exactly one).
     - `maybe_<lbl>(self) -> Optional[T]` — lines 222-241 (asserts at most one).

**Error if no types:** If `model.types` is empty, raises `RuntimeError` — gsm2tree.py:117-121.

**Trivia injection:** If a rule has whitespace separators, its model is expanded to include either `Span` (for trivia rules) or `"_trivia"` rule type (for non-trivia rules) — gsm2tree.py:296-301.

---

## 4. Generated Parser Code Shape — fltk_parser.py

**File:** `fltk/fegen/fltk_parser.py`

### Imports (lines 1-8)

```python
import collections.abc
import typing
import fltk.fegen.fltk_cst
import fltk.fegen.pyrt.errors
import fltk.fegen.pyrt.memo
import fltk.fegen.pyrt.terminalsrc
```

### Class `Parser` — `__init__` (lines 13-74)

Fields:
- `self.terminalsrc: TerminalSource` — line 14.
- `self.packrat: Packrat[int, int] = Packrat()` — line 15.
- `self.error_tracker: ErrorTracker[int] = ErrorTracker()` — line 16.
- `self.rule_names: Sequence[str] = [...]` — lines 17-32 (list of all rule names; used for error reporting).
- One `_cache__parse_<rule>: MutableMapping[int, MemoEntry[int, int, <CstNode>]]` per rule — lines 33-74.

### Pattern: memoised rule parser (lines 92-102)

```python
def parse_grammar(self, pos: int) -> ApplyResult[int, Grammar] | None:
    if alt0 := self.parse_grammar__alt0(pos=pos):
        return alt0
    return None

def apply__parse_grammar(self, pos: int) -> ApplyResult[int, Grammar] | None:
    return self.packrat.apply(
        rule_callable=self.parse_grammar, rule_id=0,
        rule_cache=self._cache__parse_grammar, pos=pos
    )
```

### Pattern: alternative parser (lines 104-118)

```python
def parse_grammar__alt0(self, pos: int) -> ApplyResult[int, Grammar] | None:
    result: Grammar = Grammar(span=Span(start=pos, end=-1))
    if initial_ws := self.apply__parse__trivia(pos=pos):
        pos = initial_ws.pos
    if item0 := self.parse_grammar__alt0__item0(pos=pos):
        pos = item0.pos
        result.children.extend(item0.result.children)   # inline_to_parent case
    else:
        return None
    result.span = Span(start=result.span.start, end=pos)
    return ApplyResult(pos=pos, result=result)
```

### Pattern: item parser with `+` quantifier (lines 120-132)

```python
def parse_grammar__alt0__item0(self, pos: int) -> ApplyResult[int, Grammar] | None:
    result: Grammar = Grammar(span=Span(start=pos, end=-1))
    while one_result := self.apply__parse_rule(pos=pos):
        pos = one_result.pos
        result.append_rule(child=one_result.result)
    if pos == result.span.start:   # OneOrMore: fail if zero matches
        return None
    result.span = Span(start=result.span.start, end=pos)
    return ApplyResult(pos=pos, result=result)
```

### Pattern: required item with label (lines 142-173)

```python
def parse_rule__alt0(self, pos: int) -> ApplyResult[int, Rule] | None:
    result: Rule = Rule(span=Span(start=pos, end=-1))
    if item0 := self.parse_rule__alt0__item0(pos=pos):
        pos = item0.pos
        result.append_name(child=item0.result)   # labeled append
    else:
        return None
    if ws_after__item0 := self.apply__parse__trivia(pos=pos):
        pos = ws_after__item0.pos
    # ... more items ...
    result.span = Span(start=result.span.start, end=pos)
    return ApplyResult(pos=pos, result=result)
```

---

## 5. Generated CST Code Shape — fltk_cst.py

**File:** `fltk/fegen/fltk_cst.py`

### Imports (lines 1-5)

```python
import dataclasses
import enum
import typing
import fltk.fegen.pyrt.terminalsrc
```

### Class shape — Grammar (lines 8-49)

```python
@dataclasses.dataclass
class Grammar:
    class Label(enum.Enum):
        RULE = enum.auto()
    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Rule", "Trivia"]]] = dataclasses.field(default_factory=list)
    def append(self, child: ..., label: Label | None = None) -> None: ...
    def extend(self, children: ..., label: Label | None = None) -> None: ...
    def child(self) -> tuple[...]: ...
    def append_rule(self, child: "Rule") -> None: ...
    def extend_rule(self, children: ...) -> None: ...
    def children_rule(self) -> typing.Iterator["Rule"]: ...
    def child_rule(self) -> "Rule": ...
    def maybe_rule(self) -> typing.Optional["Rule"]: ...
```

Note: `Trivia` appears in the union because `Grammar` has whitespace separators (`WS_ALLOWED` or `WS_REQUIRED` between rules). The `Trivia` class is the `_trivia` rule's CST node.

### Class shape — Rule (lines 52-125)

Two labels: `ALTERNATIVES`, `NAME`. Union child type: `Alternatives | Identifier | Trivia`.

### Class shape — Items (lines 172-...)

Four labels: `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`. Child union: `Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span`.

---

## 6. Runtime Support

Generated code depends on three runtime modules in `fltk/fegen/pyrt/`:

### fltk.fegen.pyrt.terminalsrc

**File:** `fltk/fegen/pyrt/terminalsrc.py`

- `Span(start: int, end: int)` — frozen dataclass, represents `[start, end)` range — lines 7-10.
- `UnknownSpan: Final = Span(-1, -1)` — line 15.
- `TerminalSource(terminals: str)` — line 25. Methods:
  - `consume_literal(pos, literal) -> Span | None` — lines 31-38. Linear character comparison.
  - `consume_regex(pos, regex) -> Span | None` — lines 40-43. Uses `re.compile(regex).match(terminals, pos=pos)`.
  - `pos_to_line_col(pos) -> LineColPos` — lines 46-68. Builds `line_ends` lazily.

### fltk.fegen.pyrt.memo

**File:** `fltk/fegen/pyrt/memo.py`

- `ApplyResult(pos: PosType, result: ResultType)` — frozen dataclass, line 68-71. Return type of all parse methods.
- `MemoEntry(result: Poison | ResultType | None, final_pos: PosType)` — line 60-63. Cache value.
- `Poison(recursion_info: RecursionInfo | None)` — line 44-57. Sentinel placed in cache to detect left recursion.
- `RecursionInfo(rule_id, involved, eval_set)` — line 28-41. Tracks active left-recursive cycle.
- `Packrat[RuleId, PosType]` — line 77. Core packrat engine.
  - `invocation_stack: list[RuleId]` — used by error tracker to identify current rule.
  - `apply(rule_callable, rule_id, rule_cache, pos)` — lines 82-156. Implements memoisation + left-recursion via seed-growing (based on Warth/Douglass/Millstein paper but with simplifications — see line 142 comment).

### fltk.fegen.pyrt.errors

**File:** `fltk/fegen/pyrt/errors.py`

- `ErrorTracker[RuleId]` — line 25. Tracks the farthest-right parse failure position and all tokens expected at that position.
  - `fail_literal(pos, rule_id, literal)` — line 29. Updates `longest_parse_len` and `expected_context`.
  - `fail_regex(pos, rule_id, regex)` — line 40.
- `format_error_message(tracker, terminals, rule_name_lookup)` — line 52. Produces human-readable syntax error with line/col and expected tokens.

---

## 7. IIR and Python Compiler

The IIR (Intermediate Representation) is in `fltk/iir/model.py`. It is a typed in-memory AST used by `gsm2parser.py` but **not** by `gsm2tree.py` (which uses Python `ast` directly via `pygen`).

### IIR expression types used by gsm2parser.py

All defined in `fltk/iir/model.py`:

| IIR class | Python output (from compiler.py) |
|---|---|
| `SelfExpr` | `"self"` |
| `MemberAccess` / `FieldAccess` | `"<expr>.<name>"` |
| `MethodAccess.call(...)` → `MethodCall` | `"<expr>.<name>(<args>)"` |
| `BoundMethod` | `"<expr>.<name>"` (for `rule_callable=self.parse_x`) |
| `Load` / `Move` | same as inner expr (no-op in Python) |
| `Store` | same as inner expr |
| `Construct.make(typ, **kwargs)` | `"<constructor>(<kwargs>)"` |
| `Failure(result_type)` | `"None"` |
| `Success(result_type, expr)` | same as `expr` |
| `LiteralString(value)` | `repr(value)` |
| `LiteralInt(typ, value)` | `repr(value)` |
| `LiteralNull()` | `"None"` |
| `LiteralSequence(values)` | `"[<...>]"` |
| `LiteralMapping(key_values)` | `"{<...>}"` |
| `Var` / `VarByName` | variable name string |
| `Equals(lhs, rhs)` | `"(<lhs>) == (<rhs>)"` |
| `Subscript(target, index)` | `"(<target>[<index>])"` |
| `LetExpr(var, result)` | `"(<var.name> := <result>)"` (walrus operator) |

Compiler entry points: `compiler.compile_class(klass, context) -> ast.ClassDef` — `fltk/iir/py/compiler.py:77`. Called in `genparser.py:81`.

### CompilerContext

`fltk/iir/context.py:43-48`:
```python
@dataclass
class CompilerContext:
    python_type_registry: TypeRegistry = field(default_factory=TypeRegistry)
    capture_trivia: bool = False
```
`capture_trivia=True` causes trivia nodes to be appended to CST node children (separator handling, gsm2parser.py:585-590, 605-611). `capture_trivia=False` (default) skips them.

### TypeRegistry

`fltk/iir/context.py:13-39`. Maps `TypeKey → TypeInfo`. Used by compiler to look up Python module and name for each IIR type. `pyreg.TypeInfo` holds `typ: iir.Type`, `module: pyreg.Module`, `name: str`, optional `concrete_name: str` (e.g. `list` vs `Sequence`).

---

## 8. Full Pipeline — genparser.py

**File:** `fltk/fegen/genparser.py`

### parse_grammar_file (lines 26-55)

1. Opens grammar `.fltkg` file.
2. `TerminalSource(text)` — wraps string.
3. `fltk_parser.Parser(terminalsrc=terminals)` — uses the **bootstrapped** parser (itself generated).
4. `parser.apply__parse_grammar(0)` — runs packrat parsing.
5. `fltk2gsm.Cst2Gsm(terminals.terminals).visit_grammar(result.result)` — converts CST to GSM.
6. Calls `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))`.

### generate_parser (lines 58-101)

1. `gsm.add_trivia_rule_to_grammar(grammar, context)`.
2. `CstGenerator(grammar, cst_module, context)` — builds CST model.
3. `ParserGenerator(grammar, cstgen, context)` — builds IIR parser class.
4. `compiler.compile_class(pgen.parser_class, context)` → `ast.ClassDef`.
5. Wraps in `ast.Module` with standard imports.
6. `ast.unparse(parser_mod)` → writes Python source string to file.

### generate command (lines 104-220)

Generates **three** files by default:
- `<base>_cst.py` — from `cstgen.gen_py_module()` → `ast.unparse`.
- `<base>_parser.py` — via `generate_parser(..., preserve_trivia=False)`.
- `<base>_trivia_parser.py` — via `generate_parser(..., preserve_trivia=True)`.

`--trivia-only` / `--no-trivia-only` suppress one parser variant.

---

## 9. Complexity Assessment

### Hard parts

**Packrat memoisation with left recursion** (`memo.py`): Implements seed-growing algorithm (Warth/Douglass/Millstein). The `_recall`, `_setup_recursion`, `_grow_seed` triad handles left-recursive rules. Comment at memo.py:142 notes the original paper's `LR-ANSWER` was "overly complex and buggy"; the implementation replaces it.

**IIR builder API** (`gsm2parser.py`): gsm2parser.py never writes string expressions. Instead it chains proxy objects: `iir.SelfExpr().fld.terminalsrc.method.consume_literal.call(pos=..., literal=...)` — lines 122-126. These proxies (`FieldLookupProxy`, `MethodLookupProxy`) use `__getattr__` — model.py:607-627. The full chain of proxy dereferences constructs nested `FieldAccess`/`MethodAccess`/`MethodCall` objects at build time.

**Inline items and inline_to_parent flag**: Items with `Disposition.INLINE` fold a referenced rule's children into the parent node. The `inline_to_parent` flag on `ParserFn` and `ConsumeTermInfo` propagates this distinction — gsm2parser.py:233, 495-509, 713-716. Inline items in alternatives are currently **not implemented** (gsm2parser.py:692-694 raises `NotImplementedError`), but parenthesised sub-expressions use `inline_to_parent=True` (line 305) and work via `children.extend(...)`.

**Trivia recursion guard**: Trivia rules use a raw `\s+` regex instead of calling the trivia parser recursively — gsm2parser.py:572-590. This is necessary because the `_trivia` rule itself may have whitespace separators (it is reachable from `_trivia`), and recursive trivia parsing would cause infinite recursion.

**Two-phase type annotation**: `gsm2tree.py` emits string annotations with forward references (`"Rule"`) using `in_module=True` mode (gsm2tree.py:123, 90). The `py_annotation_for_model_types` method strips the module prefix and wraps in quotes — gsm2tree.py:85-93.

**Not yet implemented**: `Invocation` terms (gsm.py:249-256; `Expression`, `Add`) appear in the GSM data model but `_gen_consume_term_expr` has no branch for them and falls through to `raise NotImplementedError` — gsm2parser.py:308-309. Similarly `model_for_item` in gsm2tree.py:246-257.
