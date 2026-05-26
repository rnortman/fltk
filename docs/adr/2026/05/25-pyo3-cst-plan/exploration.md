# PyO3 CST Implementation: Codebase Ground Truth

Concise. Precise. Token-dense. No fluff.

---

## 1. gsm2tree.py — Python CST Code Generator

**File:** `fltk/fegen/gsm2tree.py` — 303 lines.

**Class:** `CstGenerator` (line 33). Constructor (`__init__`, line 34) takes `grammar: gsm.Grammar`, `py_module: pyreg.Module`, `context: CompilerContext`. Immediately calls `model_for_rule` for every rule, building `self.rule_models: dict[str, ItemsModel]`.

**Data model:** `ItemsModel` (line 23) — two fields:
- `labels: MutableMapping[str, set[ModelType]]` — maps label names to the set of possible child types
- `types: set[ModelType]` — union of all child types (used for the `children` field annotation)

`ModelType = str | typemodel.TypeKey` (line 19). Strings are rule names; `TypeKey` is the IIR key for `Span`.

**What it emits** (`gen_py_module`, line 95): an `ast.Module` containing one dataclass per grammar rule. Each class has:
- Nested `Label(enum.Enum)` with one enum value per labeled item (uppercased), line 112-115
- `span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan`, line 126
- `children: list[tuple[Optional[Label], <union-of-child-types>]]`, line 127-131
- `append(self, child, label=None)`, `extend(self, children, label=None)`, `child(self)` — generic methods, lines 138-168
- For each label: `append_{label}`, `extend_{label}`, `children_{label}`, `child_{label}`, `maybe_{label}` — lines 170-242

Trivia handling (line 296-303): if a rule has whitespace separators AND is a trivia rule, adds `Span` to types; otherwise adds `"_trivia"` (the rule name) to types. This inserts `Trivia` into the `children` union of any rule that allows whitespace.

**Class name mapping:** `class_name_for_rule_node` (line 46) — `"_".join(parts).capitalize()` per part, so `raw_string` → `RawString`.

**Complexity to write a parallel Rust emitter:** The analysis logic (model-building, trivia classification, label collection) is ~130 lines and must be replicated. The code-emission logic is ~130 lines of `ast.Xxx` construction that would be replaced with Rust struct/method emission. The hardest part is faithfully reproducing the `ModelType` union annotation and the `typing.cast` in `children_{label}` (line 194-196). The whitespace/trivia type insertion (lines 296-303) is an invariant that a Rust emitter must also enforce.

---

## 2. plumbing.py — Dynamic Module Registration

**File:** `fltk/plumbing.py` — 328 lines. Primary entry point is `generate_parser` (line 86).

**CST compilation pipeline** (lines 101-112):
```python
cst_module_ast = cstgen.gen_py_module()        # returns ast.Module
cst_globals = {}
exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)  # noqa: S102
module_name = f"fltk_grammar_{id(grammar)}"
cst_module = types.ModuleType(module_name)
for name, obj in cst_globals.items():
    if not name.startswith("_"):
        setattr(cst_module, name, obj)
sys.modules[module_name] = cst_module
```

The module name is `fltk_grammar_{id(grammar)}` — unique per grammar object identity. Consumers receive a `ParserResult` (`fltk/plumbing_types.py:14`) with fields `cst_module: types.ModuleType` and `cst_module_name: str`.

**Parser compilation** (lines 114-139): The generated parser AST is exec'd with `cst_globals` merged into `parser_globals` (line 127), so the parser class sees CST node types by name without import. The parser class is found by scanning for names ending in `"Parser"` (line 132-135).

**Unparser** (line 238, `generate_unparser`): takes `cst_module_name: str` and passes it to `gsm2unparser.generate_unparser`. The string is used to emit `import <cst_module_name>` in the generated unparser code (gsm2unparser.py:1882).

**What needs to change for PyO3:** The `exec()` + `types.ModuleType` pattern replaces the CST class definitions. A PyO3 extension module provides classes as real Python types instead of `exec`'d dataclasses. `plumbing.generate_parser` would need to call into the Rust extension to get node classes instead of running `cstgen.gen_py_module()` + `exec()`. The module registration into `sys.modules` is still needed because `gsm2unparser` uses the module name as an import path in generated code.

---

## 3. fltk_cst.py — Generated CST (Bootstrap Grammar)

**File:** `fltk/fegen/fltk_cst.py` — 1127 lines.

**Classes (13 total, lines):**
| Class | Labels | Child types |
|---|---|---|
| `Grammar` (9) | `RULE` | `Rule`, `Trivia` |
| `Rule` (53) | `ALTERNATIVES`, `NAME` | `Alternatives`, `Identifier`, `Trivia` |
| `Alternatives` (129) | `ITEMS` | `Items`, `Trivia` |
| `Items` (173) | `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED` | `Item`, `Trivia`, `Span` |
| `Item` (313) | `DISPOSITION`, `LABEL`, `QUANTIFIER`, `TERM` | `Disposition`, `Identifier`, `Quantifier`, `Term`, `Trivia` |
| `Term` (441) | `ALTERNATIVES`, `IDENTIFIER`, `LITERAL`, `REGEX` | `Alternatives`, `Identifier`, `Literal`, `RawString`, `Trivia` |
| `Disposition` (571) | `INCLUDE`, `INLINE`, `SUPPRESS` | `Span` only |
| `Quantifier` (663) | `ONE_OR_MORE`, `OPTIONAL`, `ZERO_OR_MORE` | `Span` only |
| `Identifier` (755) | `NAME` | `Span` only |
| `RawString` (799) | `VALUE` | `Span` only |
| `Literal` (843) | `VALUE` | `Span` only |
| `Trivia` (887) | `BLOCK_COMMENT`, `LINE_COMMENT` | `BlockComment`, `LineComment`, `Span` |
| `LineComment` (971) | `CONTENT`, `PREFIX` | `Span` only |
| `BlockComment` (1038) | `CONTENT`, `END`, `START` | `Span` only |

**Method count:** 202 `def` statements across 28 classes/inner-classes.

**Uniform API per class:**
- `span: Span = UnknownSpan`
- `children: list[tuple[Label | None, Union[...]]]`
- `append`, `extend`, `child` (generic)
- Per label: `append_{label}`, `extend_{label}`, `children_{label}` (Iterator), `child_{label}`, `maybe_{label}`

`fltk_cst.py` is used by `fltk_parser.py` (static import `import fltk.fegen.fltk_cst`, line 4 of fltk_parser.py) and by `fltk2gsm.py` (`from fltk.fegen import fltk_cst as cst`, line 4).

---

## 4. Existing Rust/Cargo/Maturin Infrastructure

**None exists.** `find` for `*.rs`, `Cargo.toml`, `Cargo.lock` returns empty. `pyproject.toml` uses `setuptools>=61` / `wheel` build backend (lines 1-3), no maturin. No `[tool.maturin]` section. No `.cargo/` directory.

---

## 5. Test Infrastructure

### Test files exercising CST nodes

**`fltk/test_plumbing.py`** — tests `generate_parser`, asserts `hasattr(parser_result.cst_module, "Expr")` etc. (lines 66-67). CST nodes accessed dynamically via `cst_module` attribute. 15+ test methods.

**`fltk/test_plumbing_integration.py`** — more integration tests; `generate_unparser(grammar, parser_result.cst_module_name)` (line 108). Also uses `hasattr(parser_result.cst_module, ...)` to verify node class presence.

**`fltk/fegen/test_gsm2tree.py`** — 17 lines. Only test: `test_gsm2model` calls `CstGenerator` on `bootstrap.grammar` and calls `model_for_rule` on each rule. No assertion on generated classes.

**`fltk/fegen/test_gsm2parser.py`** — tests parser generation; CST nodes are exec-constructed in test helpers (lines ~70-80): `exec(compile(cst_module_ast, ...), cst_globals)`.

**`fltk/fegen/test_trivia_capture.py`** — comment at line 12: `# TriviaNode is now generated from grammar rules, not imported`. Uses inline exec pattern.

**`fltk/fegen/test_regression_*.py`** files — several directly call `cstgen.gen_py_module()` and `compile(cst_module_ast, "<cst_module>", "exec")` (e.g., `test_regression_empty_nary.py:87-88`, `test_regression_recursive_inlining.py:102-103`).

### Import pattern summary

Tests never import generated CST classes by name. They either:
1. Use the `plumbing` API and access classes via `parser_result.cst_module.<ClassName>` (dynamic attribute lookup)
2. Exec the `ast.Module` from `cstgen.gen_py_module()` directly into a dict and use that dict

The static `fltk_cst.py` is only used by the **bootstrap** pipeline: `fltk_parser.py` (static import), `fltk2gsm.py` (static import). Everything else goes through exec.

---

## 6. gsm2unparser.py — CST Type References

**File:** `fltk/unparse/gsm2unparser.py` — 1894 lines.

**Module path handling:** `UnparserGenerator.__init__` takes `cst_module: str` (a dotted module path string, e.g. `"fltk_grammar_140234567"`). In `_setup_type_system` (line 74), for every grammar rule, it registers an IIR type with:
```python
cst_module_parts = tuple(self.cst_module.split("."))
node_type_info = pyreg.TypeInfo(
    typ=node_type,
    module=pyreg.Module(cst_module_parts),
    name=class_name,
)
```
(lines 168-177)

`Trivia` type (line 774-784): looked up in the same `cst_module` — `pyreg.Module(tuple(self.cst_module.split(".")))` with `name="Trivia"`.

**Generated imports** (`generate_unparser` function, lines 1867-1894): emits `ast.Import(names=[ast.alias(name=cst_module)])` (line 1882) and `ast.ImportFrom(module=cst_module, names=[...all rule class names...])` (lines 1889-1892). The generated unparser code does `from <cst_module_name> import Grammar, Rule, ...` — so the module must be importable in `sys.modules` with those class names as attributes.

**Access pattern in generated code:** unparser accesses `node.children` (list of tuples), `node.fld.children`, label enum members like `ClassName.Label.LABELNAME` (line 303-308). Label enum lookup is by string interpolation: `f"{class_name}.Label.{expected_label.upper()}"`.

---

## 7. Bootstrap / Self-Hosting Situation

**Two separate pipelines exist:**

### Bootstrap pipeline (hand-written, not generated from .fltkg by the system itself):
- `fltk/fegen/bootstrap.py` (498 lines) — hand-written `gsm.Grammar` (Python data structures, not parsed from a file)
- `fltk/fegen/bootstrap_cst.py` (885 lines) — hand-written CST classes (same shape as generated ones)
- `fltk/fegen/bootstrap_parser.py` (843 lines) — hand-written parser

These exist so the system can parse its **own** `.fltkg` grammar files. `bootstrap.py` hardcodes the grammar as `gsm.Rule(...)` objects (lines 4+).

### Full grammar pipeline:
- `fltk/fegen/fltk.fltkg` — source grammar
- `fltk/fegen/fltk_cst.py` — **generated** from `fltk.fltkg`; committed to repo
- `fltk/fegen/fltk_parser.py` (1260 lines) — **generated** from `fltk.fltkg`; committed to repo
- `fltk/fegen/fltk2gsm.py` — CST-to-GSM visitor using `fltk_cst as cst`

`genparser.py` in `fltk/fegen/` is the CLI tool that regenerates `fltk_parser.py` and `fltk_cst.py` from the `.fltkg` source.

**Bootstrap cycle concern:** Changing CST node types affects two layers:
1. **Generated CST for user grammars** — constructed at runtime via `exec`. Replacing with PyO3 types changes how `plumbing.generate_parser` returns node classes. The parser exec still needs the node class names available in its `parser_globals`.
2. **`fltk_cst.py` / `fltk_parser.py` (committed files)** — these are static imports. `fltk_parser.py` directly accesses `fltk.fegen.fltk_cst.Grammar`, `fltk.fegen.fltk_cst.Rule`, etc. by fully-qualified name (lines 34+). Changing `fltk_cst.py` to use PyO3-backed classes would require `fltk_cst.py` to re-export classes from the Rust extension. `fltk_parser.py` does not need to change if the re-exported names have the same API.
3. **Bootstrap CST (`bootstrap_cst.py`)** — fully independent; no generated code involved. Not affected by PyO3 changes unless the `children: list[tuple[Label | None, ...]]` API changes.

**Critical invariant:** `fltk_parser.py` and `fltk2gsm.py` do `import fltk.fegen.fltk_cst` and use `fltk.fegen.fltk_cst.Grammar`, etc. directly. If PyO3 classes replace the dataclasses, the existing attribute API (`node.children`, `node.span`, `node.append_rule(child)`, etc.) must be preserved exactly — or `fltk_parser.py` and `fltk2gsm.py` must be regenerated.

---

## Open Factual Questions

1. `fltk_trivia_parser.py` exists in `fltk/fegen/` — not yet examined. Unclear if it also statically imports `fltk_cst`.
2. How `pyreg.Builtins` is used as `py_module` in `CstGenerator` — the module path affects annotation generation (`in_module=True` path at line 90). Not examined.
3. Whether `genparser.py` CLI can regenerate both `fltk_cst.py` and `fltk_parser.py` in a single invocation, or if they're separate steps.
