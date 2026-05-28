# Phase 4 Runtime Integration: Exploration

Concise. Precise. No padding. Every claim anchored to code. Audience: smart LLM/human.

---

## Code Surface

### `fltk/plumbing.py` — Primary Integration Point

**`generate_parser`** (`plumbing.py:86-147`): The function Phase 4 modifies.

Current flow in full (line refs to `plumbing.py`):

1. `create_default_context(capture_trivia=capture_trivia)` → `context` (line 97)
2. `gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))` → `grammar_with_trivia` (line 99)
3. `CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)` → `cstgen` (line 101)
4. `cstgen.gen_py_module()` → `cst_module_ast: ast.Module` (line 102)
5. `exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)` — loads CST classes into `cst_globals` dict (lines 104-105)
6. `module_name = f"fltk_grammar_{id(grammar)}"` — dynamic, unique per call (line 107)
7. Build `cst_module: types.ModuleType`, copy non-underscore names from `cst_globals` to it, register in `sys.modules[module_name]` (lines 108-112)
8. `ParserGenerator(grammar=grammar_with_trivia, cstgen=cstgen, context=context)` → `pgen` (line 114)
9. `compiler.compile_class(pgen.parser_class, context)` → `parser_class_ast` (line 115)
10. Build `parser_globals` dict: `{"ApplyResult": ..., "Span": ..., "Optional": ..., "typing": ..., "terminalsrc": ..., "fltk": ..., "errors": ...}` (lines 118-126)
11. `parser_globals.update(cst_globals)` — CST classes injected into parser namespace (line 127)
12. `exec(compile(parser_module, "<parser>", "exec"), parser_globals)` — parser class loaded live (line 129)
13. Find parser class: `for name, obj in parser_globals.items(): if isinstance(obj, type) and name.endswith("Parser"):` (lines 132-135)
14. Return `ParserResult(parser_class, cst_module, module_name, grammar_with_trivia, capture_trivia)` (lines 141-147)

**Key coupling point**: `parser_globals.update(cst_globals)` at line 127. The parser's `exec` environment gets CST classes from `cst_globals`, not from `cst_module`. This is the join point that must change for Rust CST: with Rust, there is no `cst_globals` dict; classes must be extracted from `cst_module.__dict__`.

**`generate_unparser`** (`plumbing.py:238-280`): Receives `cst_module_name: str` (not the module object). Passes it directly to `gsm2unparser.generate_unparser` (line 265). The unparser's generated code imports the CST module by name at runtime — it does not receive the module object.

**`ParserResult`** (`plumbing_types.py:14-23`): `dataclass` with fields `parser_class: type`, `cst_module: types.ModuleType`, `cst_module_name: str`, `grammar: gsm.Grammar`, `capture_trivia: bool`. No field for "backend type" (Python vs Rust). Phase 4 adds no new fields here; the module object is the abstraction.

### `fltk/fegen/genparser.py` — CLI to Extend

**Typer app** (`genparser.py:19-23`): `typer.Typer(name="genparser")`. Phase 4 adds a `compile-rust-cst` subcommand via `@app.command()`.

**`generate` subcommand** (`genparser.py:104-216`): Calls `parse_grammar_file` then generates `{base_name}_cst.py`, `{base_name}_parser.py`, `{base_name}_trivia_parser.py`. The CST generation path (`genparser.py:166-176`):
```python
grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
cst_module = pyreg.Module(cst_module_name.split("."))
cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=create_default_context())
cst_mod = cstgen.gen_py_module()
with shared_cst.open("w") as f:
    f.write(ast.unparse(cst_mod))
```

The `parse_grammar_file` helper (`genparser.py:26-55`) already handles parsing, CST conversion via `fltk2gsm.Cst2Gsm`, and trivia classification. The Phase 4 `compile-rust-cst` subcommand reuses this.

**Entry point**: `genparser.py` is not registered as a `[project.scripts]` entry point in `pyproject.toml`. It is invoked as `uv run python -m fltk.fegen.genparser` (or `python -m fltk.fegen.genparser`). The `if __name__ == "__main__": app()` guard is at line 219.

### `fltk/fegen/gsm2tree_rs.py` — Phase 3 Generator (Input to Phase 4)

**`RustCstGenerator`** (`gsm2tree_rs.py:35-471`): Takes a raw `gsm.Grammar`, internally applies trivia processing and `CstGenerator`. The `generate()` method (`gsm2tree_rs.py:102-114`) returns a complete `.rs` file as a string.

**`register_classes` emission** (`gsm2tree_rs.py:460-471`): Emits:
```rust
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<{ClassName}_Label>()?;
    module.add_class::<{ClassName}>()?;
    // ...
    Ok(())
}
```
This is the function Phase 4 must call from Python after loading the compiled `.so`.

**Security validation** (`gsm2tree_rs.py:54-72`): Constructor validates all rule names and item labels against `r"^[_a-z][_a-z0-9]*$"` before any emission, preventing identifier injection into generated Rust source.

**`UNKNOWN_SPAN` dependency** (`gsm2tree_rs.py:232-235`): Generated node constructors reference `crate::UNKNOWN_SPAN`. This is a `GILOnceCell<PyObject>` defined in `src/lib.rs:10`. The generated `.rs` files are `mod`-included into the `fltk._native` extension — they depend on this crate-level symbol. Any separately compiled `.so` for a user grammar does not have access to `crate::UNKNOWN_SPAN` from `fltk._native`.

**This is the central unresolved build architecture problem for Phase 4.** The plan says "compile to a loadable `.so`/`.pyd` extension module," but the generated Rust code uses `crate::UNKNOWN_SPAN`, which is only available within the `fltk-native` crate. A separate `cargo build --crate-type cdylib` for a user grammar would not resolve this symbol.

### `src/lib.rs` — Rust Extension Module

**Module init** (`lib.rs:13-52`): `fn _native(m: &Bound<'_, PyModule>) -> PyResult<()>`. Sets up `Span`, `SourceText`, `UnknownSpan`, then calls `cst_generated::register_classes(m)` and registers the `fegen_cst` submodule.

**UNKNOWN_SPAN** (`lib.rs:10`): `pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject> = GILOnceCell::new();` — initialized once in the `_native` module init, used by every generated node's `#[new]` constructor.

**Submodule registration pattern** (`lib.rs:35-49`): `PyModule::new` + `register_classes` + `add_submodule` + manual `sys.modules` insertion. This pattern is reusable for Phase 4's dynamically-named modules.

**Cargo.toml** (`Cargo.toml:1-16`):
- Crate name: `fltk-native`, lib name: `fltk_native`
- `crate-type = ["cdylib"]` — shared library only, no `rlib`
- `pyo3 = { version = "0.23", features = ["abi3-py310"] }` — ABI3 stable ABI
- No `rlib` output means external crates cannot link against `fltk_native`. This is the root of the `crate::UNKNOWN_SPAN` problem.

**`pyproject.toml`** (`pyproject.toml:27-30`):
```toml
[tool.maturin]
python-packages = ["fltk"]
module-name = "fltk._native"
features = ["pyo3/extension-module"]
```
Maturin is the build backend (`pyproject.toml:1-3`). `uv run --group dev maturin develop` rebuilds the extension.

### `src/cst_generated.rs` and `src/cst_fegen.rs` — Committed Generated Artifacts

- `cst_generated.rs`: 913 lines — PoC grammar (Identifier, Items, Trivia)
- `cst_fegen.rs`: 4,588 lines — fegen grammar (14 classes)

Both are committed and compiled as part of `fltk._native`. They use `crate::UNKNOWN_SPAN`. They are not separately loadable `.so` files.

### `gsm2tree.py` — Python Generator (Fallback Path)

**`CstGenerator`** (`gsm2tree.py:33-303`): `rule_models: dict[str, ItemsModel]` populated eagerly in `__init__` (line 44). `gen_py_module()` returns `ast.Module` (line 95). Used in the current `plumbing.py:101-102` path. The `RustCstGenerator` in `gsm2tree_rs.py` instantiates `CstGenerator` internally for model analysis.

**`class_name_for_rule_node`** (`gsm2tree.py:46-47`): `"".join(part.capitalize() for part in rule_name.lower().split("_"))`. Same transform used in `gsm2unparser.py:638` and inlined at `gsm2unparser.py:1888`. Duplicated in `gsm2tree_rs.py` as `_rust_variant_name` (but used differently there — for label names, not class names). The class name transform is called via `self._py_gen.class_name_for_rule_node(rule.name)` in the Rust generator.

### `gsm2unparser.py` — Unparser Generator

**`generate_unparser`** (`gsm2unparser.py:1868-1894`): Takes `cst_module: str` (the module name). Emits `import {cst_module}` (line 1882) and `from {cst_module} import {ClassName}, ...` (lines 1889-1892) as AST `Import`/`ImportFrom` nodes in the returned `imports` list. The generated unparser class accesses CST node types via these imports.

**`isinstance` checks** in generated unparser: `iir.IsInstance(expr=child_var.load(), typ=expected_type)` (`gsm2unparser.py:332`). The `expected_type` is an `iir.Type` registered against the CST module name (`gsm2unparser.py:171-178`). When compiled to Python by `iir/py/compiler.py`, this becomes `isinstance(child_var, ClassName)` where `ClassName` is imported from `cst_module_name`. For the `isinstance` check to work, the CST classes in `sys.modules[cst_module_name]` must be the same type objects as what the parser constructed nodes from.

**Label access in generated unparser**: `iir.VarByName(name=f"{class_name}.Label.{expected_label.upper()}", ...)` (`gsm2unparser.py:303-308`). The generated code accesses `ClassName.Label.VARIANT` as a dotted name. The class name is imported from `cst_module_name`. This works with Rust CST classes because `#[classattr] Label` makes `ClassName.Label` accessible as a class attribute (validated in Phase 2).

---

## Build / Compilation Architecture

### Current State (Phases 0-3)

All Rust CST code is compiled as part of the single `fltk._native` extension:
- `maturin develop` compiles `src/lib.rs`, `src/span.rs`, `src/cst_generated.rs`, `src/cst_fegen.rs` into one `fltk/_native.*.so`
- Modules for specific grammars (`fegen_cst`) are submodules registered within `_native`'s init function, not separate `.so` files
- Grammar-specific `.rs` files reference `crate::UNKNOWN_SPAN` from `lib.rs`

### Phase 4 Build Problem

The plan (`phase-plan.md:137-138`) says: "Add a CLI command to `genparser.py` that generates Rust CST source from a grammar and compiles it into a loadable `.so`/`.pyd` extension module." The compiled extension exposes `register_classes(module)`.

The generated Rust code (from `gsm2tree_rs.py`) contains `crate::UNKNOWN_SPAN` references (`gsm2tree_rs.py:232-235`). This symbol is `pub(crate)` in `src/lib.rs:10` — not exported from `fltk._native`. A separately compiled `.so` cannot link against it.

**Option A — Recompile the whole `fltk._native` crate**: Include the user grammar's `.rs` file as a new `mod` in `lib.rs`, rebuild `fltk._native`. Maturin handles this, but it requires rebuilding the entire extension (slow, requires Rust toolchain on the compile machine). The artifact is the `fltk/_native.*.so` itself, replaced in-place. Finding/registering the new grammar submodule in `_native`'s init function requires modifying `lib.rs`.

**Option B — Change the `UNKNOWN_SPAN` dependency**: Instead of `crate::UNKNOWN_SPAN`, import `UnknownSpan` from `fltk._native` at runtime in the user grammar's extension. Generated code would call `py.import("fltk._native")?.getattr("UnknownSpan")?` in the `#[new]` constructor if `span` is `None`. This removes the `crate::` coupling, allowing the user grammar extension to be a separate `cdylib`. Cost: import overhead on every node construction (mitigated by caching), code generation change in `gsm2tree_rs.py`.

**Option C — Export `UNKNOWN_SPAN` from `fltk._native`**: Make `fltk._native` expose a stable C-ABI symbol or a PyO3-registered function that returns the `UnknownSpan` object. Requires `fltk._native` to also be compiled as an `rlib` (changing `crate-type`), which conflicts with the `cdylib` requirement for Python extension modules. Not feasible without a separate build.

**Option D — Embed `UNKNOWN_SPAN` logic in a Rust helper crate**: Extract `UNKNOWN_SPAN` and shared types into a separate `fltk-cst-common` crate compiled as `rlib`. Both `fltk._native` and user grammar extensions link against it. Requires Cargo workspace restructuring, significant build system changes. Not a Phase 4 scope.

**Option E (Phase 3's actual pattern, adapted)**: All user grammar Rust CST is compiled into `fltk._native` as additional submodules, registered with manual `sys.modules` insertion. The "compile-rust-cst" CLI command generates the `.rs` file and modifies `lib.rs` to add a new `mod` + submodule registration block, then calls `maturin develop`. The `plumbing.py` lookup checks for `fltk._native.{grammar_module_name}` in `sys.modules`.

### How Phase 3 Already Handles Multiple Grammars

`lib.rs:35-49` shows the exact pattern for submodule registration:
```rust
let fegen_sub = PyModule::new(m.py(), "fegen_cst")?;
cst_fegen::register_classes(&fegen_sub)?;
m.add_submodule(&fegen_sub)?;
sys.getattr("modules")?.set_item("fltk._native.fegen_cst", &fegen_sub)?;
```

For Phase 4, user grammar classes would go into `fltk._native.{grammar_id}` following this same pattern. The key difference: the module name must be deterministic (not `fltk_grammar_{id(grammar)}`) so `plumbing.py` can find it.

---

## `plumbing.py` Integration Points

### `cst_globals` → `cst_module.__dict__` Transition

Current: `parser_globals.update(cst_globals)` (line 127) — CST classes come from the `exec()` global dict.

With Rust CST: `cst_globals` does not exist. CST classes are attributes on `cst_module`. The adaptation:
```python
# Replace: parser_globals.update(cst_globals)
# With:
for name, obj in vars(cst_module).items():
    if not name.startswith("_"):
        parser_globals[name] = obj
```
Or simply: `parser_globals.update({k: v for k, v in vars(cst_module).items() if not k.startswith("_")})`.

`vars(cst_module)` on a `types.ModuleType` returns `__dict__`, which includes dunder attributes. The current code (`plumbing.py:109-111`) already filters `not name.startswith("_")` when copying into `cst_module`, so `cst_module.__dict__` has the filtered view. Thus `parser_globals.update(vars(cst_module))` would pull in dunders; use explicit filtering or `{k: v for k, v in cst_module.__dict__.items() if not k.startswith("_")}`.

### `sys.modules` Registration — Must Be Preserved

`generate_unparser` (`plumbing.py:238-280`) accepts `cst_module_name: str`. It passes this string to `gsm2unparser.generate_unparser` (line 265), which emits `import {cst_module_name}` and `from {cst_module_name} import ...` into the generated unparser code (lines 1882, 1889-1892). When the generated unparser is `exec()`-d (`plumbing.py:273`), these import statements execute at that moment.

**The `sys.modules[module_name]` registration at `plumbing.py:112` is mandatory** — it is what makes `import {cst_module_name}` work inside the `exec()` environment. Without it, the unparser's `exec()` at line 273 fails with `ModuleNotFoundError`.

For the Rust path, this registration is still required. `cst_module` must be in `sys.modules[module_name]` before `generate_unparser` is called. The Rust CST classes must be attributes on this `types.ModuleType` instance.

### `module_name` Convention Problem

Current: `module_name = f"fltk_grammar_{id(grammar)}"` (line 107). This is not stable across process restarts — it is based on Python object identity. For ahead-of-time compiled Rust CST, the module name must be deterministic so `plumbing.py` can find the pre-compiled artifact.

The `cst_module_name` is threaded from `ParserResult.cst_module_name` → `generate_unparser(grammar, parser_result.cst_module_name)` → into the generated unparser code. Changing the naming convention for the Rust path is possible without breaking the Python path, as long as the name is set before `generate_unparser` is called.

**Naming options for the Rust path**:
- `fltk._native.{grammar_hash}` — stable if hash is of grammar text or grammar structure
- `fltk._native.{user_supplied_name}` — explicit, requires CLI arg
- Convention from grammar file path — only available in the `compile-rust-cst` CLI, not in `plumbing.generate_parser`

### `isinstance` Correctness Requirement

The generated unparser does `isinstance(child, ClassName)` where `ClassName` is the type imported from `cst_module_name` at unparser `exec()` time. The parser constructs nodes from CST classes in `parser_globals`, which are populated from `cst_module`.

**Invariant**: The `ClassName` used to construct nodes (via parser) must be the same Python type object as the `ClassName` imported by the unparser. This is satisfied if both come from the same `types.ModuleType` object registered under the same `sys.modules` key.

For Rust CST: `cst_module.Grammar` (the PyO3 class) must be the same object as what `import fltk_grammar_{id}; from fltk_grammar_{id} import Grammar` resolves to. This works because Python caches module objects in `sys.modules` and imports return the cached object.

**Risk**: If the Rust CST module is loaded from `fltk._native.{submodule}` and its classes are then set as attributes on a `types.ModuleType`, the class objects on `cst_module` are the same objects as those from the submodule (attribute reference, not copy). `isinstance` still works.

---

## Generated Unparser's Import Chain

`generate_unparser` in `plumbing.py:238-280`:
1. `gsm2unparser.generate_unparser(grammar_with_trivia, context, cst_module_name, ...)` returns `(unparser_class: iir.ClassType, imports: list)` (line 262-267)
2. `imports` includes `ast.Import(name=cst_module_name)` and `ast.ImportFrom(module=cst_module_name, names=[ClassName, ...])` (gsm2unparser.py:1882, 1889-1892)
3. `exec(ast.unparse(module), exec_globals)` at line 273 — `exec_globals` is `{}`, no pre-loaded modules; the `import` statements in the generated code execute via normal `sys.modules` lookup

This means the CST module must be in `sys.modules` with the exact name that was passed as `cst_module_name` to `generate_unparser`. The `plumbing.py` flow ensures this by registering at line 112 before calling `generate_unparser` at line 262.

---

## Existing Tests Relevant to Phase 4

### `fltk/test_plumbing.py`

- `TestParserGeneration.test_generate_parser_with_trivia` (`test_plumbing.py:53-67`): Checks `parser_result.cst_module_name in sys.modules` and `hasattr(parser_result.cst_module, "Expr")`.
- `TestParserGeneration.test_parser_module_cleanup` (`test_plumbing.py:81-88`): Checks `sys.modules[parser_result.cst_module_name] is parser_result.cst_module`.
- Unparser tests (`test_plumbing.py:203, 217, 230, 247, 268, 281, 332, 361`): All call `generate_unparser(grammar, parser_result.cst_module_name)`.

These tests validate the module registration invariant. The Rust path must pass all of these unchanged.

### `fltk/test_plumbing_integration.py`

Similar pattern at lines 108, 142, 171, 234, 264, 293 — all use `parser_result.cst_module_name` as the bridge between parser generation and unparser generation.

---

## `genparser.py` CLI Extension Pattern

The `@app.command()` decorator registers a new Typer subcommand. A `compile-rust-cst` command follows the same pattern as `generate` (`genparser.py:104`). It would:
1. Accept `grammar_file`, `output_name`, and optionally `output_dir` args
2. Call `parse_grammar_file(grammar_file)` (already defined at `genparser.py:26`)
3. Instantiate `RustCstGenerator(grammar)` and call `.generate()` → `.rs` source string
4. Write `.rs` source to a temp or output location
5. Invoke build step (see architecture problem above)
6. Report artifact location

The `parse_grammar_file` function at `genparser.py:26-55` already calls `add_trivia_rule_to_grammar` and `classify_trivia_rules` internally (line 54), but `RustCstGenerator.__init__` also does this internally (`gsm2tree_rs.py:44-46`). Double-processing is harmless (idempotent) but means a raw grammar (not yet trivia-augmented) should be passed to `RustCstGenerator`.

**Discrepancy**: `genparser.parse_grammar_file` returns an already-trivia-processed grammar (line 54 applies `add_trivia_rule_to_grammar` + `classify_trivia_rules`). `RustCstGenerator.__init__` expects a raw grammar and applies these internally. If `parse_grammar_file`'s output is passed to `RustCstGenerator`, the trivia augmentation happens twice. The `add_trivia_rule_to_grammar` function in `gsm.py` would add a second `_trivia` rule if one does not already exist in the grammar — but since the first call already added `_trivia`, the second call is a no-op (it checks first). The `classify_trivia_rules` call is also idempotent. Net effect: double-processing is safe but wasteful. A `compile-rust-cst` command should either use a different grammar-loading function or pass the raw grammar to `RustCstGenerator`.

---

## Open Factual Questions

1. **`UNKNOWN_SPAN` linkage**: How does a separately compiled user grammar `.so` access `UNKNOWN_SPAN` from `fltk._native`? No viable Rust-level solution exists without architectural changes (separate crate, `rlib` output, or runtime import in the `#[new]` constructor). This is the central unresolved technical question for Phase 4.

2. **Module name stability**: The current `fltk_grammar_{id(grammar)}` is not stable. What identifier makes a user grammar's compiled Rust CST findable by `plumbing.generate_parser`? This must be decided before the artifact-location convention can be designed.

3. **`plumbing.generate_parser` discovery mechanism**: The plan says "checks for a pre-compiled Rust module." What triggers the check? Grammar file path? An explicit flag? A `sys.modules` lookup for a known name? The answer depends on (2) and how the name is communicated from the compile step to the runtime step.

4. **`maturin develop` vs `cargo build`**: `maturin develop` rebuilds the entire `fltk._native` extension, including all committed `.rs` files. If user grammars are compiled by adding to `fltk._native`, each user grammar compilation triggers a full crate rebuild — slow. If user grammars are separate extensions, the `UNKNOWN_SPAN` problem applies. No middle ground exists without the `rlib` approach.

5. **`register_classes` receives `types.ModuleType` or `Bound<PyModule>`**: The current `register_classes` signature is `pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()>`. `types.ModuleType` instances are callable from PyO3 as `Bound<PyModule>` via `m.py().import(module_name)`. But a freshly created `types.ModuleType` on the Python side — before it is registered in `sys.modules` — may not be accessible this way. The `lib.rs` pattern passes a `PyModule::new` Rust-created module directly; Phase 4 would need to pass a Python-created `types.ModuleType`. Compatibility needs verification.

---

## Scope Update: Phase 4 Reframe — Runtime Contract Only

Per coordinator update: Phase 4 is "runtime contract only." No `cargo`/`maturin` invocation from Python at runtime. Build orchestration (generate `.rs`, compile to `.so`) moves to the project Makefile. `plumbing.generate_parser` loads a **pre-compiled** Rust CST module and registers its classes in `sys.modules`. The Python `exec()` path is still available but is a deliberate choice, not a fallback; selecting the Rust backend when its module is missing or unloadable is a hard error.

### Current Makefile

`Makefile` (24 lines): Six `.PHONY` targets. No grammar-generation targets yet:

```
check: lint typecheck test cargo-check cargo-clippy cargo-test
lint:     uv run --group lint --group test ruff check .
typecheck: uv run --group lint --group test pyright
test:     uv run --group lint --group test pytest
cargo-check: cargo check
cargo-test:  cargo test
cargo-clippy: cargo clippy -- -D warnings
```

No `maturin develop`, no `.rs` generation, no artifact placement targets. Phase 4 adds targets for: generating user grammar `.rs` source, compiling via `maturin develop`, and placing artifacts. The `maturin develop` command is already in `CLAUDE.md` as the manual build step but is absent from the Makefile.

### Current Build Flow (Phases 0-3)

- `maturin develop` (or `uv run --group dev maturin develop`) compiles `src/lib.rs`, `src/span.rs`, `src/cst_generated.rs`, `src/cst_fegen.rs` into one shared library installed as `fltk/_native.*.so`.
- `pyproject.toml:27-30`: `module-name = "fltk._native"`, `python-packages = ["fltk"]`.
- `Cargo.toml:7-8`: `crate-type = ["cdylib"]` — cdylib only, no rlib. No stable C ABI exports other than the Python module init.
- `lib.rs:10`: `pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject>` — crate-internal, not exported.

### Backend-Selection Seam in `plumbing.generate_parser`

The current `generate_parser` (`plumbing.py:86-147`) has no backend selection. The entire CST construction path is:

```python
cstgen = gsm2tree.CstGenerator(...)         # line 101: Python analysis
cst_module_ast = cstgen.gen_py_module()      # line 102: Python AST
exec(compile(cst_module_ast, ...), ...)      # line 105: Python exec
# ... build types.ModuleType from cst_globals ...
```

**The natural seam for backend selection is between steps (b) and (c)**: after the grammar model is analyzed, before the CST module is populated. With a `rust_cst_module_path` argument or flag, `generate_parser` would either:

- **Python path**: run `gen_py_module()` + `exec()` as today
- **Rust path**: `importlib.util.spec_from_file_location()` + `importlib.util.module_from_spec()` + `loader.exec_module()` to load the pre-compiled `.so`, then call `register_classes(cst_module)` to populate a fresh `types.ModuleType`

The `cstgen` object (`CstGenerator`) is still needed on the Rust path: it is passed to `ParserGenerator` at `plumbing.py:114`. The `RustCstGenerator` internally creates its own `CstGenerator` for analysis, but `plumbing.py` uses the `CstGenerator` directly for `ParserGenerator`. This means the Python `CstGenerator` must still be instantiated on the Rust path; only the `gen_py_module()` + `exec()` steps are replaced.

**Hard-error semantics**: If `rust_cst_module_path` is provided but the `.so` is missing or fails to load, `generate_parser` raises immediately — no silent Python fallback. This is a deliberate API contract change from the current behavior (which has no Rust path at all).

### How CST Module Identity Flows Through the Pipeline

```
generate_parser(grammar, rust_cst_module_path=path) -> ParserResult
    ParserResult.cst_module_name = "fltk_grammar_{id(grammar)}"  [line 107]
    ParserResult.cst_module = types.ModuleType(module_name)      [line 108]
    sys.modules[module_name] = cst_module                        [line 112]

generate_unparser(grammar, parser_result.cst_module_name)
    -> gsm2unparser.generate_unparser(..., cst_module_name=module_name)
    -> imports: [ast.Import(name=module_name),
                 ast.ImportFrom(module=module_name, names=[ClassName, ...])]
    -> exec(ast.unparse(module), {})   # imports resolve via sys.modules
```

The `module_name` string is the **only coupling** between the parser phase and the unparser phase. Changing how `cst_module` is populated (Python exec vs Rust register_classes) does not affect this coupling, as long as the `types.ModuleType` is registered in `sys.modules[module_name]` with the correct class attributes.

---

## Scope Update: Dual Backend — Static Consumer Survey

Per coordinator update: Both Python dataclass CST and Rust CST are first-class backends. Neither replaces the other. Static consumers (`fltk_parser.py`, `fltk_trivia_parser.py`, `fltk2gsm.py`, formatter pipeline CST modules) must work against either backend unmodified. This section surveys what API surface each consumer uses — which defines the contract both backends must satisfy.

### `fltk_cst.py` — Current Python Dataclass Backend

`fltk/fegen/fltk_cst.py` (1127 lines): 14 dataclass node classes + Label enums. Generated from `fegen.fltkg`. The Rust equivalent is `src/cst_fegen.rs` (4588 lines, 14 classes), already compiled into `fltk._native.fegen_cst`. The two share the same API contract but are not currently wired together — `fltk_parser.py` imports `fltk.fegen.fltk_cst` (Python), not the Rust version.

### `fltk_parser.py` and `fltk_trivia_parser.py` — Parser Pattern

Both files (`fltk_parser.py:1-5`, `fltk_trivia_parser.py:1-5`):
```python
import fltk.fegen.fltk_cst
import fltk.fegen.pyrt.terminalsrc
```

Construction pattern (`fltk_parser.py:107-109`):
```python
result: fltk.fegen.fltk_cst.Grammar = fltk.fegen.fltk_cst.Grammar(
    span=fltk.fegen.pyrt.terminalsrc.Span(start=pos, end=-1)
)
```

Operations used (counts from `fltk_parser.py`):
- `ClassName(span=Span(start=..., end=-1))` — constructor with keyword `span` arg (40 construction sites)
- `result.children.extend(other.result.children)` — extend list from another node (11 sites, e.g. line 114)
- `result.append_{label}(child=...)` — typed append with keyword `child` arg (~30 sites, e.g. line 128)
- `result.span = Span(start=result.span.start, end=pos)` — span reassignment (40 sites, e.g. line 117)
- `result.span.start` — span field read for reassignment (40 sites, via `result.span.start`)

Type annotation usage: `fltk.fegen.fltk_cst.Grammar` appears in `MemoEntry` type annotations on lines 34-73. These are Python type annotations only (`dict[int, fltk.fegen.pyrt.memo.MemoEntry[int, int, fltk.fegen.fltk_cst.Grammar]]`); they do not affect runtime behavior.

**Contract required of both backends:**
- `ClassName(span=Span(...))` — keyword-only or positional keyword `span` arg
- `children` is a mutable Python list (live reference, not copy)
- `result.children.extend(iterable)` — must mutate the backing list
- `append_{label}(child=value)` — keyword `child` arg accepted
- `result.span = new_span` — span field is writable
- `result.span.start` — readable

### `fltk2gsm.py` — CST Consumer Pattern

`fltk/fegen/fltk2gsm.py` (131 lines): Imports `from fltk.fegen import fltk_cst as cst` (line 4).

**Operations used:**

| Operation | Line | Pattern |
|---|---|---|
| `items.children[0][0] in (...)` | 36 | Index + containment: label identity via `__eq__`/`__hash__` |
| `cst.Items.Label.NO_WS` | 37 | Class attribute access to label enum |
| `cst.Items.Label.WS_ALLOWED` | 38 | Same |
| `cst.Items.Label.WS_REQUIRED` | 39 | Same |
| `sep_label, _ = items.children[0]` | 41 | Tuple unpack from list item |
| `sep_label == cst.Items.Label.WS_REQUIRED` | 42 | Label equality comparison |
| `items.children[start_idx:]` | 51 | Slice — returns list-like, iterable |
| `children[::2]` | 52 | Stride-2 slice |
| `children[1::2]` | 52 | Stride-2 slice (offset) |
| `len(children)` implied by `len(children) % 2` | 62 | `__len__` |
| `children[-1]` | 63 | Negative index |
| `isinstance(item, cst.Item)` | 53, 64 | `isinstance` check |
| `grammar.children_rule()` | 13 | Per-label iterator method |
| `rule.child_name()` | 18 | Per-label accessor |
| `identifier.child_name()` | 23 | Same |
| `span.start`, `span.end` | 24 | Span field read: `self.terminals[span.start : span.end]` |
| `alternatives.children_items()` | 27 | Per-label iterator |
| `item.child_term()` | 71 | Per-label accessor |
| `item.maybe_label()` | 73 | Optional accessor |
| `item.maybe_disposition()` | 77 | Optional accessor |
| `item.maybe_quantifier()` | 84 | Optional accessor |
| `disposition.child()` | 103 | Generic child (returns `(label, value)`) |
| `label == cst.Disposition.Label.INCLUDE` | 104 | Label equality |
| `quantifier.child()` | 114 | Generic child |
| `label == cst.Quantifier.Label.ONE_OR_MORE` | 115 | Label equality |
| `literal.child_value()` | 125 | Per-label accessor |
| `regex.child_value()` | 129 | Per-label accessor |

**Critical operations**: `children[::2]`, `children[1::2]`, `children[-1]`, `children[0][0] in (...)`. The `children` list must support Python's full slice protocol including stride and negative indices. This is exactly why `Py<PyList>` (Option B) was chosen — it delegates to a real Python list. A custom `__getitem__` implementation would need to handle all these cases.

**`isinstance` contract**: `isinstance(item, cst.Item)` at lines 53 and 64. The type object imported as `cst.Item` (from `fltk.fegen.fltk_cst`) must be the same object used to construct the `item` node. If `fltk_cst.py` re-exports from `fltk._native.fegen_cst`, then `cst.Item` is the PyO3 class, and `isinstance` works because the parser constructed the node with the same PyO3 class.

### Formatter Pipeline CST Modules

**`unparsefmt_cst.py`** (`fltk/unparse/unparsefmt_cst.py`, 2947 lines): Python dataclasses for the `.fltkfmt` format grammar. Consumed by:
- `fltk/unparse/unparsefmt_parser.py` (line 7: `import fltk.unparse.unparsefmt_cst`) — constructs nodes, same pattern as `fltk_parser.py` (keyword `span`, `append_{label}`, `result.children.extend`, `result.span = ...`)
- `fltk/unparse/unparsefmt_trivia_parser.py` (line 7: same import)
- `fltk/unparse/fmt_config.py` (line 11: `from fltk.unparse import unparsefmt_cst as fmt_cst`) — calls only per-label typed methods (`maybe_{label}()`, `child_{label}()`, `children_{label}()`) — no direct `.children` list access

**`toy_cst.py`** (`fltk/unparse/toy_cst.py`, 325 lines): Python dataclasses for the toy grammar (arithmetic expressions). Consumed by:
- `fltk/unparse/toy_parser.py` (line 7: `import fltk.unparse.toy_cst`) — same parser pattern
- `fltk/unparse/toy_trivia_parser.py` (line 7: same)

**`fmt_config.py` pattern**: Calls only method-API methods on `unparsefmt_cst` nodes — `maybe_{label}()`, `child_{label}()`, `children_{label}()`, `child()`. Zero direct `.children` list accesses (`grep` confirms: 0 occurrences of `.children[` or `.children\b` in `fmt_config.py`). The method API alone is sufficient for `fmt_config.py`; the list-protocol requirement comes only from `fltk2gsm.py`.

**Formatter CST and dual-backend question**: `unparsefmt_cst.py` and `toy_cst.py` are static generated Python files, not generated at runtime by `plumbing.generate_parser`. They are only consumed by their respective parsers and `fmt_config.py`. A Rust backend for these grammars would require the same treatment as `fltk_cst.py` (compile to `.so`, re-export or swap). They are NOT going through `plumbing.generate_parser`; they use statically-imported module paths. Phase 4 (user grammar runtime integration) does not directly affect them.

### Backend Selection Seam: Where It Currently Lives

No backend selection exists today. The seam is entirely in `plumbing.generate_parser`:

- Lines 101-112: CST module construction (Python `exec()` path)
- Line 114: `ParserGenerator(cstgen=cstgen)` — `cstgen` is from the Python analysis, always needed
- Line 127: `parser_globals.update(cst_globals)` — CST classes injected into parser namespace from the Python exec dict; the Rust equivalent extracts from `cst_module.__dict__`

For the Rust path, the seam is a new parameter (e.g., `rust_cst_so_path: Path | None = None`) to `generate_parser`. When provided and module is loadable: use Rust path. When provided and module fails to load: hard error. When not provided: Python path.

**No existing seam in the formatter pipeline**: `fmt_config.py` is on the production path via `plumbing.generate_unparser` → `plumbing.parse_format_config` → `FmtParser` (unparsefmt_parser.py). `plumbing.parse_format_config` (`plumbing.py:184-212`) directly instantiates `FmtParser` (which uses `unparsefmt_cst`). There is no injection point for a Rust backend here without modifying `unparsefmt_parser.py` or `fmt_config.py`. Backend selection for the formatter pipeline would require a separate mechanism or is out of Phase 4 scope.

### API Contract Summary: Both Backends Must Satisfy

For any grammar processed by `plumbing.generate_parser`, the CST module's classes must support:

1. **Construction**: `ClassName(span=Span(start=s, end=e))` — keyword `span` arg, default `UnknownSpan`
2. **Span write**: `node.span = new_span` — settable attribute
3. **Span read**: `node.span.start`, `node.span.end` — readable fields on Span
4. **Children mutate via extend**: `node.children.extend(other.children)` — `children` is a live Python list, not a snapshot
5. **Typed append**: `node.append_{label}(child=value)` — keyword `child` arg
6. **List protocol on `children`**: `len()`, `[i]`, `[i:]`, `[::2]`, `[-1]` — full Python list semantics
7. **Tuple items in children**: `node.children[i]` is `(label_or_None, value)` — indexable as 2-tuple
8. **Label equality and containment**: `label == ClassName.Label.FOO`, `label in (ClassName.Label.FOO, ...)` — requires `__eq__` and `__hash__` on label enum
9. **Class attribute label access**: `ClassName.Label.VARIANT` — accessible as `ClassName.Label` class attribute
10. **`isinstance` dispatch**: `isinstance(node, ClassName)` — works for PyO3 `#[pyclass]` types natively
11. **Iterator methods**: `node.children_{label}()` returns iterable; `node.child_{label}()` returns single value; `node.maybe_{label}()` returns Optional
12. **Generic `child()`**: returns `(label, value)` tuple

Items 6 (stride slice), 7 (tuple items), and 8 (label containment via hash) are the most constraining. All are satisfied by Phase 2's `Py<PyList>` approach (validated in Phase 2 acceptance tests).
