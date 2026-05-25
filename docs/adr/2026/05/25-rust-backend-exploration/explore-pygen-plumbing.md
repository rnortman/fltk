# Code Generation Plumbing: pygen, plumbing, bootstrap, and pipeline

Style note: concise, precise, no fluff. Every claim anchored to file:line.

---

## 1. pygen.py — Python Code Generation Utilities

**File:** `fltk/pygen.py` (124 lines)

pygen.py is a thin factory layer over Python's `ast` module. It provides helpers that parse small code strings into `ast` nodes rather than requiring callers to construct AST nodes manually. All functions return stdlib `ast` objects.

| Function | Signature | Returns | Notes |
|----------|-----------|---------|-------|
| `module` | `(imports: Iterable[str|Sequence[str]]) -> ast.Module` | `ast.Module` | Empty module; appends `import` stmts for each entry. Line 19. |
| `import_` | `(imp: str|Sequence[str]) -> ast.Import` | `ast.Import` | Joins sequence with `.`, parses `import {name}`. Line 27. |
| `function` | `(name, args, return_type) -> ast.FunctionDef` | `ast.FunctionDef` | Parses `def name(args) -> return_type: pass`, empties body. Line 35. |
| `expr` | `(expr_py: str) -> ast.expr` | `ast.expr` | Parses in `eval` mode. Line 42. |
| `stmt` | `(stmt_py: str) -> ast.stmt` | `ast.stmt` | Parses as single statement. Line 49. |
| `dataclass` | `(name, bases) -> ast.ClassDef` | `ast.ClassDef` | Emits `@dataclasses.dataclass class name(bases): pass`, empties body. Line 53. |
| `klass` | `(name, bases) -> ast.ClassDef` | `ast.ClassDef` | Plain class, empties body. Line 68. |
| `if_` | `(condition, body, orelse) -> ast.If` | `ast.If` | Parses template then replaces test/body/orelse. Line 82. |
| `while_` | `(condition, body) -> ast.While` | `ast.While` | Parses template then replaces test/body. Line 112. |

**Pattern:** Parse a minimal snippet to get the right AST node shape, then surgically replace `.body`, `.test`, etc. with actual content. The `_strip_module` helper (`pygen.py:9`) asserts the parsed module has exactly one statement and returns it cast to the expected type.

pygen.py does **not** perform any code generation logic itself. It is purely a convenience factory. All generation logic lives in callers.

---

## 2. plumbing.py and plumbing_types.py — High-Level Pipeline API

**Files:** `fltk/plumbing.py` (327 lines), `fltk/plumbing_types.py` (42 lines)

### Data Types (`plumbing_types.py`)

Three dataclasses, all in `fltk/plumbing_types.py`:

- `ParserResult` (line 15): holds `parser_class: type`, `cst_module: types.ModuleType`, `cst_module_name: str`, `grammar: gsm.Grammar`, `capture_trivia: bool`
- `ParseResult` (line 25): holds `cst: Any|None`, `terminals: str`, `success: bool`, `error_message: str|None`
- `UnparserResult` (line 35): holds `unparser_class: type`, `grammar: gsm.Grammar`, `formatter_config: FormatterConfig`, `trivia_config: TriviaConfig`

### Functions (`plumbing.py`)

**`parse_grammar(grammar_text: str) -> gsm.Grammar`** (line 34)
1. Wraps text in `terminalsrc.TerminalSource`
2. Instantiates `fltk_parser.Parser` (the pre-generated parser for `.fltkg` format)
3. Calls `parser.apply__parse_grammar(0)` — produces a CST
4. Constructs `fltk2gsm.Cst2Gsm(terminals)` and calls `.visit_grammar(result.result)` — yields `gsm.Grammar`

**`generate_parser(grammar: gsm.Grammar, *, capture_trivia: bool = True) -> ParserResult`** (line 86)
1. `create_default_context(capture_trivia=capture_trivia)` — `CompilerContext`
2. `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))` — augments grammar with trivia rule
3. `CstGenerator(grammar, py_module=pyreg.Builtins, context)` — builds CST type model
4. `cstgen.gen_py_module()` — `ast.Module` of CST class definitions (uses pygen.py)
5. `exec(compile(cst_module_ast, ...))` — loads CST classes into `cst_globals`
6. `ParserGenerator(grammar, cstgen, context)` — builds IIR model of parser class
7. `compiler.compile_class(pgen.parser_class, context)` — compiles IIR to `ast.ClassDef`
8. `exec(compile(parser_module, ...))` — loads parser class live
9. Searches `parser_globals` for class whose name ends with `"Parser"` (line 133)
10. Returns `ParserResult`

**`parse_text(parser_result, text, rule_name) -> ParseResult`** (line 150)
Uses the live `parser_class` from `ParserResult` directly.

**`generate_unparser(grammar, cst_module_name, formatter_config) -> UnparserResult`** (line 238)
1. `gsm2unparser.generate_unparser(...)` returns `(unparser_class: iir.ClassType, imports)`
2. `compiler.compile_class(unparser_class, context)` — IIR to `ast.ClassDef`
3. `exec(ast.unparse(module), exec_globals)` — note: uses `ast.unparse` (string) not `compile()` directly (line 272)
4. Returns `UnparserResult` with live `unparser_class`

**`unparse_cst(unparser_result, cst, terminals, rule_name) -> Doc`** (line 282)
Calls method `unparse_{rule_name}` on instantiated unparser. Returns `resolve_spacing_specs(result.accumulator.doc)`.

**`render_doc(doc, config) -> str`** (line 316)
Instantiates `Renderer(config)` and calls `.render(doc)`.

### Role in the pipeline
plumbing.py is the **facade layer**: it wires together grammar parsing, CST generation, parser generation, IIR compilation, and dynamic `exec` into a single callable API. Callers only need to pass text/grammar objects; they never touch `gsm2parser`, `gsm2tree`, `iir`, or `compiler` directly.

---

## 3. Bootstrap Pipeline

### Bootstrap grammar definition (`fltk/fegen/bootstrap.py`)

`bootstrap.py` is **not a parser** — it is a hand-written Python module that constructs a `gsm.Grammar` object directly by assembling `gsm.Rule`, `gsm.Items`, `gsm.Item`, `gsm.Literal`, `gsm.Regex`, `gsm.Identifier` instances inline in Python code (lines 3–459). There is no parsing step; the grammar is expressed directly as Python data structures.

The bootstrap grammar covers a restricted subset of the full fltkg format: rules `grammar`, `rule`, `alternatives`, `items`, `item`, `term`, `disposition`, `quantifier`, `identifier`, `raw_string`, `literal`.

Key difference from full grammar:
- Items use only two separators: `WS` / `NO_WS` (no `WS_REQUIRED`)
- No support for `:` (WS_REQUIRED) separator, no trivia annotations
- No leading-separator support

The `if __name__ == "__main__"` block (line 461) is the bootstrap generation CLI:
1. Takes `parser_filename cst_filename cst_module_name` as argv
2. Calls `gsm2tree.CstGenerator(grammar=grammar, ...)` and `gsm2parser.ParserGenerator(...)`
3. Compiles both via IIR compiler
4. Writes to files using `astor.to_source(...)` — **astor**, not `ast.unparse`

Output of bootstrap generation: `fltk/fegen/bootstrap_parser.py` and `fltk/fegen/bootstrap_cst.py`.

### `bootstrap2gsm.py` — Bootstrap CST to GSM

`fltk/fegen/bootstrap2gsm.py` defines `class Cst2Gsm` (line 8). Takes `bootstrap_cst` (the CST node types generated from the bootstrap grammar) and converts to `gsm.*` objects. Used to interpret bootstrap grammar output as a GSM.

Key methods:
- `visit_grammar(cst.Grammar) -> gsm.Grammar` (line 12)
- `visit_items(cst.Items) -> gsm.Items` (line 29): reads `cst.Items.Label.NO_WS`/`WS` to determine separators; only handles `WS_ALLOWED`/`NO_WS` (no `WS_REQUIRED`)
- `visit_literal(cst.Literal) -> gsm.Literal` (line 116): uses `ast.literal_eval` to decode string literals
- `visit_regex(cst.RawString) -> gsm.Regex` (line 120)

This class is **not imported by plumbing.py**. `plumbing.py` uses `fltk2gsm.Cst2Gsm` exclusively. `bootstrap2gsm` is only used when regenerating the bootstrap parser itself.

---

## 4. fltk2gsm.py — Full Grammar Format to GSM

**File:** `fltk/fegen/fltk2gsm.py` (131 lines)

Defines `class Cst2Gsm` (line 8), structurally parallel to `bootstrap2gsm.Cst2Gsm` but operates on `fltk_cst` (CST node types from the full grammar) rather than `bootstrap_cst`.

Differences vs. bootstrap2gsm:
- `visit_items` handles three separator labels: `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED` (lines 36–48, 55–61), mapping to all three `gsm.Separator` values including `WS_REQUIRED`
- Imports `fltk_cst as cst` (line 4) vs bootstrap2gsm's `bootstrap_cst as cst`
- Otherwise structurally identical

**Key logic in `visit_item`** (line 70-88): applies default disposition heuristics:
- If no explicit disposition: if term is `gsm.Identifier` or `Sequence`, `INCLUDE`; else `SUPPRESS`
- If no explicit label but term is `gsm.Identifier`: uses identifier name as label

**`visit_literal`** (line 124-126): uses `ast.literal_eval()` to decode quoted string literals from source spans.

Used in `plumbing.py:59` and `genparser.py:48`:
```python
cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
return cst2gsm.visit_grammar(result.result)
```

---

## 5. Complete Code Generation Pipeline

### 5.1 Artifact: bootstrap_parser.py + bootstrap_cst.py

**Input:** `fltk/fegen/bootstrap.py` (hand-written GSM as Python data)

**Pipeline:**
```
bootstrap.py (gsm.Grammar, hand-written Python)
    -> gsm2tree.CstGenerator(grammar, py_module, context)        [gsm2tree.py:33]
        -> .gen_py_module() -> ast.Module                         [gsm2tree.py:95]
            uses pygen.module(), pygen.dataclass(), pygen.klass(),
                 pygen.function(), pygen.stmt(), pygen.expr(),
                 pygen.if_() throughout py_class_for_model()      [gsm2tree.py:109-244]
    -> astor.to_source(cst_mod) -> write bootstrap_cst.py         [bootstrap.py:497-498]
    -> gsm2parser.ParserGenerator(grammar, cstgen, context)       [bootstrap.py:479]
        builds iir.ClassType model entirely in IIR (no pygen.py)  [gsm2parser.py throughout]
    -> compiler.compile_class(pgen.parser_class, context)         [bootstrap.py:481]
        IIR ClassType -> ast.ClassDef via pygen.klass(),
            pygen.function(), pygen.stmt(), pygen.expr(),
            pygen.if_(), pygen.while_()                           [compiler.py:77-168, 172-198]
    -> pygen.module(imports) + .append(parser_ast)                [bootstrap.py:490-491]
    -> astor.to_source(parser_mod) -> write bootstrap_parser.py  [bootstrap.py:493-494]
```

**Tools used:** pygen.py (by gsm2tree and iir/py/compiler), IIR model (by gsm2parser, then compiled by iir/py/compiler), `astor.to_source` for final string output.

### 5.2 Artifact: fltk_cst.py + fltk_parser.py + fltk_trivia_parser.py

**Input:** `fltk/fegen/fltk.fltkg` (full grammar text)

**Pipeline (via genparser.py CLI):**
```
fltk.fltkg text
    -> terminalsrc.TerminalSource(text)                          [genparser.py:36]
    -> fltk_parser.Parser(terminalsrc=terminals)                 [genparser.py:38]
        (fltk_parser.py is itself a generated artifact -- see 5.1)
    -> parser.apply__parse_grammar(0) -> fltk_cst.Grammar node   [genparser.py:39]
    -> fltk2gsm.Cst2Gsm(terminals).visit_grammar(result.result)  [genparser.py:48]
        -> gsm.Grammar
    -> gsm.add_trivia_rule_to_grammar(grammar, context)           [genparser.py:51]
    -> gsm.classify_trivia_rules(grammar)                         [genparser.py:51]

    CST generation:
    -> gsm2tree.CstGenerator(grammar, cst_module, context)        [genparser.py:168]
    -> cstgen.gen_py_module() -> ast.Module                       [genparser.py:170]
        uses pygen.py (see 5.1 above)
    -> ast.unparse(cst_mod) -> write fltk_cst.py                  [genparser.py:173]

    Parser generation (x2: no-trivia and trivia variants):
    -> gsm2parser.ParserGenerator(grammar, cstgen, context)       [genparser.py:78]
        builds iir.ClassType -- all IIR, no pygen.py
    -> compiler.compile_class(pgen.parser_class, context)         [genparser.py:81]
        IIR -> ast.ClassDef -- uses pygen.py internally
    -> pygen.module(imports)                                       [genparser.py:92]
    -> ast.unparse(parser_mod) -> write *_parser.py               [genparser.py:98]
```

### 5.3 Artifact: In-memory parser (plumbing.py dynamic path)

```
grammar text
    -> parse_grammar() -> gsm.Grammar                            [plumbing.py:34-60]
    -> generate_parser(grammar) -> ParserResult                  [plumbing.py:86-147]
        -> gsm2tree.CstGenerator -> gen_py_module() -> ast.Module [plumbing.py:101-102]
            uses pygen.py
        -> exec(compile(cst_module_ast, ...))                     [plumbing.py:105]
            CST classes loaded live, no file written
        -> gsm2parser.ParserGenerator -> iir.ClassType            [plumbing.py:114]
        -> compiler.compile_class() -> ast.ClassDef               [plumbing.py:115]
            uses pygen.py
        -> exec(compile(parser_module, ...))                      [plumbing.py:129]
            Parser class loaded live, no file written
```

### 5.4 Artifact: In-memory unparser (plumbing.py)

```
gsm.Grammar
    -> gsm2unparser.generate_unparser() -> (iir.ClassType, imports) [plumbing.py:261]
    -> compiler.compile_class() -> ast.ClassDef                      [plumbing.py:268]
        uses pygen.py
    -> ast.Module(body=[*imports, unparser_ast])                     [plumbing.py:269]
    -> exec(ast.unparse(module), exec_globals)                       [plumbing.py:272]
        round-trips through string; unparser class loaded live
```

---

## 6. Stage-by-Stage: IIR vs pygen.py vs Raw Strings

| Stage | Uses IIR? | Uses pygen.py? | Raw string code? |
|-------|-----------|----------------|------------------|
| `gsm2tree.CstGenerator.gen_py_module()` | No (only `iir.Type` for type registry) | **Yes** — pygen.module, dataclass, klass, function, stmt, expr, if_ | Only f-strings inside pygen.stmt()/function() args |
| `gsm2parser.ParserGenerator` | **Yes** — builds entire iir.ClassType with methods, fields, blocks, exprs | No — zero imports of pygen | No |
| `iir/py/compiler.compile_class/function` | **Yes** — walks IIR nodes | **Yes** — pygen.klass, function, stmt, expr, if_, while_ | f-strings in pygen.stmt() args |
| `iir/py/compiler.compile_expr()` | **Yes** — pattern-matches iir.Expr nodes | Callers pass result to pygen | **Yes** — returns Python expression strings via f-strings |
| `gsm2unparser` (output) | **Yes** — returns iir.ClassType | No directly; compiled via compile_class | No |
| `bootstrap.__main__` | No direct | **Yes** — pygen.module() | No |
| `genparser.generate_parser` CLI | No direct | **Yes** — pygen.module() | No |
| `plumbing.generate_parser` | No direct (delegates) | No direct | No |

**Key asymmetry:** `gsm2tree` uses pygen directly with no IIR. `gsm2parser` uses IIR exclusively with no pygen. Both produce `ast` nodes, but via completely different paths.

**`compile_expr()` in `iir/py/compiler.py`** (line 294-344) is the only place raw Python expression strings are generated from scratch. It returns `str`. The callers then pass these strings to `pygen.stmt()` or `pygen.expr()` to get AST nodes. Example:
- `iir.BinOp` (line 303): `f"({compile_expr(expr.lhs)}) {expr.op} ({compile_expr(expr.rhs)})"`
- `iir.MethodCall` (line 307): `f"{compile_expr(bound_to)}.{member_name}(...)"`
- `iir.Construct` (line 314): `f"{constructor}({args_str})"`

---

## 7. Key Structural Facts

**gsm2parser.py never calls pygen.py.** It imports pygen nowhere. pygen is used only by gsm2tree.py and iir/py/compiler.py.

**Two serialization paths for .py files:**
- `astor.to_source()` — used only in `bootstrap.py:__main__` (lines 494, 498); `astor` is an optional dev dependency; produces formatted source
- `ast.unparse()` — used in `genparser.py` (lines 98, 173) and `plumbing.generate_unparser` (line 272); produces compact single-line source

**In-memory path:** `plumbing.generate_parser` uses `compile(ast_module, "<name>", "exec")` + `exec()` (lines 105, 129). No `ast.unparse()` step — the AST is compiled directly to bytecode.

**`generate_unparser` inconsistency** (plumbing.py:272): uses `exec(ast.unparse(module), ...)` rather than `exec(compile(module, ...))`. The AST is serialized to string then re-parsed, while the parser path uses the AST directly.

**`CompilerContext`** (`iir/context.py:43`): carries `python_type_registry: TypeRegistry` and `capture_trivia: bool`. The registry maps IIR `Type.key` to `pyreg.TypeInfo(module, name, concrete_name)`. `create_default_context()` (line 50) pre-registers builtins and parser-specific types (ApplyResult, Span, MemoEntry, ErrorTracker).

**The bootstrap grammar is self-contained Python** — regenerated by running `python -m fltk.fegen.bootstrap` with file args. The resulting `bootstrap_parser.py` / `bootstrap_cst.py` are committed to the repo and used to parse restricted bootstrap-format grammars. The full-grammar parser (`fltk_parser.py`, `fltk_cst.py`) is generated from `fltk.fltkg` using the genparser CLI, which itself uses `fltk_parser.py` already existing — bootstrapped from the bootstrap parser.

**Separator types:** `bootstrap2gsm.visit_items` (line 29-60) knows only `WS`/`NO_WS` labels. `fltk2gsm.visit_items` (line 29-68) additionally handles `WS_REQUIRED`. This is the primary functional difference between the two `Cst2Gsm` classes.

**`gsm2tree` does not use IIR for code structure**, only for type identity (`iir.Type.make()`, `iir_type_for_rule()` at gsm2tree.py:69-78). Type keys are used to look up Python annotation strings via `iir_type_to_py_annotation()` (compiler.py:49). The CST class bodies (fields, methods) are generated entirely via pygen string-snippet parsing.
