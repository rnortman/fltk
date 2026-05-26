# Phase 0 Exploration: Rust/PyO3 Infrastructure and Grammar Baseline

Concise. Precise. No padding. Audience: smart human/LLM implementing Phase 0.

---

## 1. Build System: Current State and Maturin Migration

### pyproject.toml (`/home/rnortman/src/fltk/pyproject.toml`)

- **Build backend** (lines 1–3): `setuptools>=61` + `wheel`, `build-backend = "setuptools.build_meta"`
- **Package config** (line 28): `[tool.setuptools]` with `packages = ["fltk"]` — single flat package, no `src/` layout
- **Runtime deps** (line 25): `["astor", "typer"]`
- **Dev groups** (lines 35–43): `test = [coverage, pytest]`, `lint = [pyright, ruff]`
- **No maturin, no pyo3** — no Rust tooling anywhere in the file
- **Pyright config** (lines 45–49): `include = ["fltk", "*.py"]`, `pythonVersion = "3.10"`, `venvPath = ".venv"`

**For maturin migration**: Replace `[build-system]` block (lines 1–3), remove `[tool.setuptools]` (line 27–28), add `[tool.maturin]` section. Maturin takes over the `fltk` package but the Python sources stay in their current location (no `src/` layout required — maturin supports both flat and `src/` layouts).

### MODULE.bazel (`/home/rnortman/src/fltk/MODULE.bazel`)

- **Lines 1–19**: Only `rules_python = "1.5.0"` declared as a Bazel dep. No `rules_rust`.
- Python 3.10 toolchain, pip hub named `"pypi"`, `requirements_lock.txt` as the lock file.
- No Rust Bazel support exists. Phase 0 plan says: document the gap as TODO, Bazel users won't get the Rust extension until `rules_rust` is added later.

### No setup.cfg, no setup.py
Only `pyproject.toml` and `MODULE.bazel` are build manifests. No `WORKSPACE.bazel` rules needed for Python.

### Repo layout

```
/home/rnortman/src/fltk/
  pyproject.toml          # build manifest (setuptools currently)
  MODULE.bazel            # Bazel manifest (rules_python only)
  fltk/                   # Python package root — flat layout (NOT src/)
    __init__.py
    plumbing.py
    plumbing_types.py
    fegen/                # grammar engine
    iir/                  # intermediate representation
    unparse/              # unparser/formatter pipeline
```

**Cargo.toml placement**: Repo root (`/home/rnortman/src/fltk/Cargo.toml`), with `src/lib.rs` at `/home/rnortman/src/fltk/src/lib.rs`. This is the standard maturin layout for a mixed Python/Rust package. The `fltk` Python package stays at `fltk/` (maturin `python-packages = ["fltk"]` in `[tool.maturin]`).

---

## 2. Grammar Baseline: The Mismatch

### Three grammar files exist

**`fltk/fegen/bootstrap.fltkg`** — the grammar the system actually uses to bootstrap itself. 11 non-trivia rules:
`grammar, rule, alternatives, items, item, term, disposition, quantifier, identifier, raw_string, literal` + `_trivia := whitespace | line_comment | block_comment`, `whitespace, line_comment, block_comment`.
Separators use only two tokens: `"."` (NO_WS) and `","` (WS_ALLOWED) in `items`.

**`fltk/fegen/fegen.fltkg`** — current production grammar used by `fltk_parser.py`/`fltk_trivia_parser.py`. 11 non-trivia rules (same as bootstrap but with additions):
`grammar, rule, alternatives, items, item, term, disposition, quantifier, identifier, raw_string, literal` + `_trivia`, `line_comment, block_comment`.
`items` rule supports three separators: `no_ws:"."`, `ws_allowed:","`, `ws_required:":"`.
`_trivia` rule is more complex: `( line_comment | line_comment? : | block_comment )+` (supports WS_REQUIRED colon in trivia).
**No `whitespace` rule** — trivia is handled inline.

**`fltk/fegen/fltk.fltkg`** — the "extended" grammar with line 2 comment: "This grammar is actually broken and was never completed." Contains 18 rule definitions:
`grammar, rule, alternatives, items, item, term, disposition, quantifier, invocation, expression, var, identifier, raw_string, literal, _trivia, whitespace, line_comment, block_comment`.
Problems:
- Line 9: references `rule_options` which is never defined anywhere in the file.
- Adds `invocation`, `expression`, `var` rules not in `fegen.fltkg` or `fltk_cst.py`.
- Has a `whitespace` rule (like `bootstrap.fltkg`) but `fegen.fltkg` does not.

### `fltk_cst.py` — what it actually corresponds to

`/home/rnortman/src/fltk/fltk/fegen/fltk_cst.py` has **14 classes** (lines 9, 53, 129, 173, 313, 441, 571, 663, 755, 799, 843, 887, 971, 1039):
`Grammar, Rule, Alternatives, Items, Item, Term, Disposition, Quantifier, Identifier, RawString, Literal, Trivia, LineComment, BlockComment`.

These 14 classes match `fegen.fltkg` + its trivia rules, **not** `fltk.fltkg`.

Specifically:
- No `Whitespace` class (fegen.fltkg has no separate `whitespace` rule; bootstrap.fltkg does)
- No `Invocation`, `Expression`, `Var` classes (fltk.fltkg adds these but fegen.fltkg does not)
- The `Grammar.Label` has only `RULE` (not `VARS` — the `vars:var` in fltk.fltkg line 4 would add a `VARS` label)
- `fltk2gsm.py:13` calls `grammar.children_rule()` — consistent with single-label `RULE` in `Grammar`
- `Items.Label` has `ITEM, NO_WS, WS_ALLOWED, WS_REQUIRED` — matching fegen.fltkg's three-separator items rule

### Conclusion on grammar mismatch

**`fltk_cst.py` was generated from `fegen.fltkg`, not from `fltk.fltkg`.**

`fltk.fltkg` is a dead-end experimental file never brought to completion. The correct baseline for Phase 0 is `fegen.fltkg` (which already matches `fltk_cst.py` and `fltk_parser.py`/`fltk_trivia_parser.py`).

**Confirming**: no Python file references `fltk.fltkg` by path (grep returned no matches). The parsers are generated from `fegen.fltkg` and committed as static files. `plumbing.parse_grammar()` uses `fltk_parser.Parser` which was generated from `fegen.fltkg`.

**Phase 0 grammar task**: Add a regression test that verifies `fegen.fltkg` can be parsed by `fltk_parser.Parser` and the output matches what `fltk_cst.py` + `fltk_parser.py` + `fltk_trivia_parser.py` were generated from. `fltk.fltkg` can be ignored (or deleted — it is not used by anything).

---

## 3. The Genparser/Plumbing Pipeline

### `fltk/plumbing.py` — the runtime pipeline

`generate_parser()` (lines 86–147) is the key function:

```python
def generate_parser(grammar: gsm.Grammar, *, capture_trivia: bool = True) -> ParserResult:
    # Lines 99–112: build CST module
    grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
    cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)
    cst_module_ast = cstgen.gen_py_module()
    cst_globals = {}
    exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)
    module_name = f"fltk_grammar_{id(grammar)}"
    cst_module = types.ModuleType(module_name)
    for name, obj in cst_globals.items():
        if not name.startswith("_"):
            setattr(cst_module, name, obj)
    sys.modules[module_name] = cst_module
    # Lines 114–147: build parser
    pgen = gsm2parser.ParserGenerator(grammar=grammar_with_trivia, cstgen=cstgen, context=context)
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    parser_globals = {...}
    parser_globals.update(cst_globals)
    exec(compile(parser_module, "<parser>", "exec"), parser_globals)
    ...
    return ParserResult(parser_class=..., cst_module=cst_module, cst_module_name=module_name, ...)
```

`ParserResult` (plumbing_types.py:14–21) holds `parser_class: type`, `cst_module: types.ModuleType`, `cst_module_name: str`, `grammar`, `capture_trivia`.

`parse_grammar()` (lines 34–60): uses `fltk_parser.Parser` (the static generated parser) to parse `.fltkg` text, then `fltk2gsm.Cst2Gsm` to convert CST to GSM.

**plumbing.py is at `/home/rnortman/src/fltk/fltk/plumbing.py`** — NOT inside `fltk/fegen/`. The `fltk/fegen/plumbing.py` mentioned in the phase plan **does not exist** at that path.

### `fltk/fegen/genparser.py` — the CLI

`generate` command (lines 104–216): parses grammar, calls `CstGenerator.gen_py_module()` → writes `{base_name}_cst.py`, then `generate_parser()` (lines 58–101, a different local function) writes `{base_name}_parser.py` and `{base_name}_trivia_parser.py`.

`parse_grammar_file()` (lines 26–55): same pipeline as `plumbing.parse_grammar()`.

`generate_parser()` (lines 58–101, the CLI version): takes a pre-existing `cst_module_name` string and generates parser without regenerating CST — used for the two parser variants after CST is written.

### `fltk/fegen/gsm2tree.py` — the CST generator

`CstGenerator.__init__` (lines 34–44): eagerly calls `model_for_rule()` for every rule, populating `self.rule_models: dict[str, ItemsModel]`. Also calls `self.context.python_type_registry.register_type()` (line 76) for each rule's IIR type.

`gen_py_module()` (lines 95–107): returns `ast.Module`. Iterates `self.rule_models` to emit one Python `@dataclass` per rule.

`py_class_for_model()` (lines 109–244): emits one class. Per label: `append_{label}`, `extend_{label}`, `children_{label}`, `child_{label}`, `maybe_{label}` methods. Plus unlabeled `append`, `extend`, `child` methods.

`model_for_rule()` (lines 285–303): trivia injection at lines 296–303 — if rule has whitespace separators AND is a trivia rule, adds `Span` to model types; otherwise adds `"_trivia"` rule reference.

`class_name_for_rule_node()` (line 47): `"".join(part.capitalize() for part in rule_name.lower().split("_"))` — e.g., `"raw_string"` → `"RawString"`, `"_trivia"` → `"Trivia"` (after stripping leading underscore? Let's verify: `"_trivia".lower().split("_")` → `["", "trivia"]` → `["", "Trivia"]` → `"Trivia"`). Yes, `"_trivia"` → `"Trivia"`.

`ModelType = str | typemodel.TypeKey` (line 19): string = rule name reference; `TypeKey` = IIR primitive (e.g., `Span.key`).

---

## 4. Existing Test Coverage Relevant to Phase 0

### Tests that exercise the grammar pipeline

**`fltk/fegen/test_gsm2parser.py`**:
- `test_single()`: exercises `gen_item_parser()` on a single literal item
- `test_bootstrap()`: exercises `ParserGenerator` on `bootstrap.grammar` (the hardcoded bootstrap grammar from `fltk/fegen/bootstrap.py`, NOT parsed from a `.fltkg` file)

**`fltk/fegen/test_gsm2tree.py`**:
- `test_gsm2model()`: calls `CstGenerator` on `bootstrap.grammar`, logs models — no assertions beyond not crashing

**`fltk/test_plumbing.py`**:
- `TestGrammarParsing.test_parse_simple_grammar()`: parses inline grammar text via `plumbing.parse_grammar()`
- `TestGrammarParsing.test_parse_invalid_grammar()`: negative test
- Additional tests for `generate_parser`, `parse_text`, etc. using inline grammars

**`fltk/test_plumbing_integration.py`**:
- Uses `toy.fltkg` at `fltk/unparse/toy.fltkg` for full pipeline tests
- Skips if file not found

**`fltk/fegen/test_trivia_whitespace_capture.py`**:
- Uses `plumbing.parse_grammar()` + `plumbing.generate_parser()` on inline grammar text

### No test parses fegen.fltkg or fltk.fltkg directly

Confirmed by grep: zero Python files reference `fltk.fltkg` or `fegen.fltkg` by path. The baseline regeneration round-trip (`fegen.fltkg` → parse via `fltk_parser.Parser` → GSM → `CstGenerator.gen_py_module()` → matches committed `fltk_cst.py`) is **not tested anywhere**.

### Static consumers of `fltk_cst`

- `fltk_parser.py`: line 4 `import fltk.fegen.fltk_cst` — static generated parser
- `fltk_trivia_parser.py`: line 4 `import fltk.fegen.fltk_cst` — static generated trivia parser
- `fltk2gsm.py`: line 4 `from fltk.fegen import fltk_cst as cst` — uses children slicing `children[::2]` (line 52), `isinstance` checks, label comparisons (lines 36–60)

---

## 5. Project Structure and Rust Placement

### Current layout

```
/home/rnortman/src/fltk/
  pyproject.toml            # build manifest
  fltk/                     # Python package (NOT under src/)
    __init__.py
    plumbing.py             # high-level API: parse_grammar, generate_parser, etc.
    plumbing_types.py       # ParserResult, ParseResult, UnparserResult dataclasses
    fegen/                  # grammar engine
      fegen.fltkg           # production grammar (matches fltk_cst.py)
      fltk.fltkg            # broken experimental grammar (unused)
      bootstrap.fltkg       # bootstrap grammar (simpler, used for initial parser)
      fltk_cst.py           # 14-class CST (generated from fegen.fltkg)
      fltk_parser.py        # static parser for .fltkg files
      fltk_trivia_parser.py # static trivia parser for .fltkg files
      fltk2gsm.py           # CST → GSM converter
      gsm.py                # Grammar Semantic Model
      gsm2tree.py           # CstGenerator: GSM → Python AST for CST classes
      gsm2parser.py         # ParserGenerator: GSM → Python AST for parser
      genparser.py          # CLI: generate parsers from .fltkg files
      pyrt/                 # Python runtime support
        terminalsrc.py      # Span dataclass (lines 7–12), TerminalSource, UnknownSpan (line 15)
        errors.py
        memo.py
    iir/                    # intermediate representation
    unparse/                # formatter/unparser pipeline
      unparsefmt_cst.py     # CST for format config grammar
      unparsefmt_parser.py
      unparsefmt_trivia_parser.py
      toy_cst.py            # CST for toy test grammar
      toy_parser.py
      toy_trivia_parser.py
      toy.fltkg
      fmt_config.py         # on production path via plumbing.py
```

### Where Rust code should live (Phase 0)

- `Cargo.toml` at `/home/rnortman/src/fltk/Cargo.toml` (repo root — standard maturin location)
- `src/lib.rs` at `/home/rnortman/src/fltk/src/lib.rs` — minimal `#[pymodule]` exporting `fltk._native`
- `[lib]` in Cargo.toml: `name = "fltk_native"`, `crate-type = ["cdylib"]`
- maturin `[tool.maturin]` in pyproject.toml: `python-packages = ["fltk"]`, `module-name = "fltk._native"`

The repo currently has no `src/` directory. Creating `/home/rnortman/src/fltk/src/lib.rs` is the first Rust file.

---

## 6. Span Dataclass (Phase 1 Target, Relevant Context for Phase 0)

`terminalsrc.py` lines 7–12:
```python
@dataclass(frozen=True, eq=True, slots=True)
class Span:
    start: int
    end: int
```
`UnknownSpan: Final = Span(-1, -1)` at line 15.

`Span` construction sites:
- `terminalsrc.consume_literal()` line 38: `Span(pos, pos + len(literal))` — positional
- `terminalsrc.consume_regex()` line 43: `Span(pos, match.end())` — positional
- `fltk_parser.py`: ~80 construction sites (positional)
- `fltk2gsm.py` line 24: `self.terminals[span.start : span.end]` — attribute access

Phase 0 does not modify `terminalsrc.py`, but the Rust extension must not conflict with future Phase 1 replacement of `Span`.

---

## 7. Open Factual Questions

1. **`fltk/fegen/genparser.py` vs `fltk/plumbing.py`**: The phase plan mentions `plumbing.py` at `fltk/fegen/plumbing.py` (phase-plan.md:130) but the actual file is `fltk/plumbing.py`. The generate flow in `fltk/fegen/genparser.py:generate()` calls a local `generate_parser()` (lines 58–101), not `fltk.plumbing.generate_parser`. These are separate implementations of similar logic. Phase 4's "adapt `plumbing.py`" refers to `fltk/plumbing.py:generate_parser()` (lines 86–147).

2. **`fegen.fltkg` vs `fltk.fltkg` for Phase 0**: The phase plan says "reconcile `fltk.fltkg` with `fltk_cst.py`." The actual situation is `fltk_cst.py` was generated from `fegen.fltkg`, not `fltk.fltkg`. `fltk.fltkg` is a dead-end. The Phase 0 grammar baseline work is: add a test that parses `fegen.fltkg` via `fltk_parser.Parser` and verifies the resulting GSM produces the same CST classes as the committed `fltk_cst.py`. `fltk.fltkg` can be left as-is (it is unused) or deleted.

3. **`setuptools` `packages = ["fltk"]`**: This is a flat-list config, not auto-discovery. Maturin's `python-packages` setting replaces this. The `fltk.egg-info/` directory at repo root suggests the package is currently installed in editable mode. After migration, `uv pip install -e .` becomes `maturin develop`.
