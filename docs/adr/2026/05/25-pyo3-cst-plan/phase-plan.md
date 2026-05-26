# PyO3 CST Implementation: Phased Project Plan

Concise. Precise. No padding. Audience: smart human/LLM.

---

## Context

FLTK generates Python dataclass-based CST nodes. The Rust backend ADR (`25-rust-backend-exploration/`) chose PyO3-wrapped Rust CST nodes as the first deliverable. The feasibility analysis (`analysis-rust-cst-first.md`) confirmed viability with Option B (children stored as `Py<PyList>`), but identified unvalidated assumptions requiring PoC work: nested-enum workaround and `Py<PyList>` mutation semantics (both validated in Phase 2).

**Primary deliverable:** `plumbing.generate_parser()` produces Rust-backed CST nodes for ANY user grammar. The code generator (`gsm2tree_rs.py`) and the runtime integration (`plumbing.py` adaptation) are the core of this plan. The FLTK grammar's own `fltk_cst.py` replacement is secondary — it is just one grammar that happens to be self-hosted, useful for dogfooding but not the goal.

**Static consumers of `fltk_cst`:** `fltk_parser.py`, `fltk_trivia_parser.py`, `fltk2gsm.py` — all import `fltk.fegen.fltk_cst`. Additional static CST modules exist in the formatter pipeline: `unparsefmt_cst.py`, `toy_cst.py`, consumed by `unparsefmt_parser.py`, `unparsefmt_trivia_parser.py`, `toy_parser.py`, `toy_trivia_parser.py`, and `fmt_config.py` (which is on the production path via `plumbing.py`). The bootstrap pipeline (`bootstrap_cst.py`) is independent of the *generated* CST classes but shares `terminalsrc.Span`, so Phase 1 affects it; the full test suite covers bootstrap and is the safety net.

**Runtime pipeline:** `plumbing.py:101-112` constructs CST modules via `exec()` + `types.ModuleType`, registers them in `sys.modules`. The generated unparser imports from these dynamic modules (`gsm2unparser.py:1876-1892`). This is the pipeline that every user grammar flows through, and adapting it for Rust CST is the central design problem.

---

## Phase 0: Rust/PyO3 Infrastructure Bootstrap (and Grammar Fix)

**Goal:** Establish the build toolchain and fix the stale grammar baseline. No CST logic yet.

**Prerequisite — grammar round-trip:** The committed `fltk.fltkg` is broken (line 2: "This grammar is actually broken and was never completed"; references undefined `rule_options`; adds `invocation`, `expression`, `var` rules not present in the committed `fltk_cst.py`). The committed `fltk_cst.py` (14 classes) was generated from an older grammar version (18 rule definitions in current `fltk.fltkg` vs 14 classes in `fltk_cst.py`). Before any Rust work: either revert `fltk.fltkg` to match the committed `fltk_cst.py`, or fix the grammar and regenerate `fltk_cst.py` / `fltk_parser.py` so the Python pipeline round-trips cleanly. Add a regression test that verifies regeneration from `fltk.fltkg` succeeds (currently no test exercises this — `grep -rln 'fltk.fltkg' fltk/ --include=*.py` returns no matches). This establishes the baseline for Phase 3/4 "API equivalence" validation.

**Scope:**
- Add `Cargo.toml` at repo root with PyO3 dependency.
- Add `src/lib.rs` with a minimal `#[pymodule]` exporting one trivial `#[pyclass]` (e.g., a `Ping` class with a `pong()` method). The Rust extension exposes `fltk._native` as the top-level native module, with submodules added in later phases. Submodules keep grammar-specific generated code separate from shared types like `Span`.
- Switch `pyproject.toml` build backend from `setuptools` to `maturin`. Current build backend is `setuptools>=61` (`pyproject.toml:2`). Maturin is the standard PyO3 build tool and handles the Cargo build, Python packaging, and editable installs in one step. The existing `[tool.setuptools]` config is replaced, not extended.
- Verify `uv run pytest` still works — the compiled extension loads and existing tests pass unchanged.
- Bazel integration: The current `MODULE.bazel` uses only `rules_python` — no Rust support. Adding `rules_rust` to Bazel is out of scope for this phase. Document the gap as a TODO. Bazel users will not get the Rust extension until `rules_rust` is added in a future phase.

**Inputs:** None.

**Outputs:** A repo that builds a Python package with a Rust extension module. All existing tests pass.

**Done when:** `uv run pytest` passes, and Python code can `from fltk._native import Ping; assert Ping().pong() == "pong"`.

---

## Phase 1: Span PoC

**Goal:** Replace `terminalsrc.Span` with a PyO3 `#[pyclass(frozen)]` and validate it works throughout the codebase.

**Scope:**
- Implement `Span` in Rust: `#[pyclass(frozen)]` with `#[pyo3(get)] start: i64`, `#[pyo3(get)] end: i64`, `#[new]` accepting both positional and keyword args (positional construction is used on the hot path in `terminalsrc.consume_literal`/`consume_regex` and throughout `bootstrap_parser.py`), `__richcmp__` (Eq), `__hash__`, `__repr__`.
- Implement `UnknownSpan` as a module-level constant (`Span(-1, -1)`).
- Replace the `Span` dataclass definition in `terminalsrc.py` with an import from the Rust extension (`from fltk._native import Span`). `terminalsrc.py` currently defines `Span` as a `@dataclass(frozen=True, eq=True, slots=True)` with fields `start: int`, `end: int` (line 7-12), and `UnknownSpan: Final = Span(-1, -1)` (line 15). All existing import paths (`fltk.fegen.pyrt.terminalsrc.Span`) continue to work because `terminalsrc.py` re-exports the Rust class.
- Run the full test suite. `Span` is used pervasively: as node fields (80 construction sites in `fltk_parser.py`), as child values in leaf nodes, and in `fltk2gsm.py:24` (`terminals[span.start : span.end]`).

**Inputs:** Phase 0 (build infrastructure).

**Outputs:** Rust-backed `Span` used by all existing Python code. All tests pass.

**Done when:** `uv run pytest` passes with `Span` coming from the Rust extension. Positional (`Span(1, 2)`) and keyword (`Span(start=1, end=2)`) construction both work. `isinstance`, `==`, and `hash` all work.

**Why this is a separate phase:** Span is the simplest PyO3 class (frozen, no mutation, no children) and is used everywhere. If something fails here — positional/keyword construction, equality semantics, hash behavior, import path resolution — it's cheapest to discover now. It also validates the re-export pattern needed for the full CST.

**Risk:** Low. Frozen dataclass to `#[pyclass(frozen)]` is the simplest PyO3 pattern.

---

## Phase 2: Nested Enum PoC

**Goal:** Validate the `NodeClass.Label.FOO` workaround for PyO3's lack of nested `#[pyclass]`.

**Scope:**
- Hand-write two CST node classes in Rust: `Identifier` (one label `NAME`, child type `Span` only — simplest case) and `Items` (four labels: `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED` — needed to validate label discrimination).
- Implement `Identifier_Label` as a standalone `#[pyclass]` enum with `__eq__`, `__hash__`, `__repr__`.
- Attach as class attribute: `#[classattr] fn Label() -> Identifier_Label` on `Identifier`.
- Implement `children` as `Py<PyList>` (Option B).
- Implement all methods: `append`, `extend`, `child`, `append_name`, `extend_name`, `children_name`, `child_name`, `maybe_name`.
- Implement `__eq__` (recursive comparison of `span` + `children`) and `__repr__`.
- Write a focused test that validates:
  - `Identifier.Label.NAME == Identifier.Label.NAME` (identity/equality)
  - `label in (Identifier.Label.NAME,)` (containment via `__hash__` + `__eq__`)
  - Discrimination test: use a second node type with multiple labels (e.g., `Items` has `ITEM`, `NO_WS`, `WS_ALLOWED`, `WS_REQUIRED`) to verify `Items.Label.ITEM != Items.Label.NO_WS`
  - `node.children` returns a mutable Python list
  - `node.children[0]` returns a tuple `(label, child)`
  - `node.append_name(span)` works
  - `node.child_name()` returns the child
  - `isinstance(node, Identifier)` works
  - `node.span = Span(1, 2)` works (setter)

**Inputs:** Phase 1 (Span exists in Rust).

**Outputs:** Two working hand-written Rust CST nodes. Validation of the nested-enum workaround (including multi-label discrimination), the `Py<PyList>` children strategy, and the method API surface.

**Done when:** The focused test passes. The node is not wired into `fltk_cst.py` — this is a standalone validation.

**Why this is a separate phase:** Two unvalidated PoC assumptions live here: (1) the `#[classattr]` enum attachment pattern and (2) `Py<PyList>` children semantics (mutation visibility, tuple construction, iteration). If either fails, the entire approach needs rethinking before investing in the generator.

**Risk:** Medium. The `#[classattr]` enum pattern is documented in PyO3 but not widely used for this purpose. The `Py<PyList>` approach should work but needs validation that `node.children.extend(other.children)` mutates the backing list (not a copy).

---

## Phase 3: Generator — `gsm2tree_rs.py`

**Goal:** Build the Rust CST code generator and validate it produces compilable, API-equivalent output for any grammar.

**Scope:**
- Write `gsm2tree_rs.py` — a parallel to `gsm2tree.py` (303 lines). Reuse the analysis logic by instantiating (or subclassing) `CstGenerator` and consuming its `rule_models` dict (note: `CstGenerator.__init__` eagerly populates `rule_models` and registers IIR types via `self.context.python_type_registry`; `py_module` drives annotation paths). Emit Rust source text instead of `ast.Module`.
- The generator takes a `gsm.Grammar` and produces a `.rs` file containing:
  - One `#[pyclass]` struct per rule
  - One `#[pyclass]` enum per rule's labels
  - `#[pymethods]` block per rule with all methods
  - A `register_classes(module: &Bound<PyModule>)` function that adds all classes to a given PyO3 module
- The register-classes function (not a `#[pymodule]`) is the key interface: it allows the same generated Rust code to be registered into *any* module — a statically-compiled submodule of `fltk._native` for Phase 5 dogfooding, or a dynamically-named module for Phase 4 runtime integration.
- The generated Rust code for the FLTK grammar (`fltk.fltkg`, after Phase 0 reconciliation — currently 14 classes in `fltk_cst.py`) should compile and produce classes with the same API as the reconciled `fltk_cst.py`.
- Test: generate Rust source from the FLTK grammar, compile it, instantiate classes from Python, verify API equivalence with the existing Python dataclass CST module. Also test with at least one non-FLTK grammar from the test suite to validate generality.

**Inputs:** Phase 2 (validated struct/enum/method patterns to emit). Also requires `gsm2tree.py`'s analysis logic — the generator reuses `CstGenerator`'s `rule_models` via instantiation/subclassing, not standalone methods.

**Outputs:** `gsm2tree_rs.py` (~300-400 lines Python). Generated `.rs` file for the FLTK grammar.

**Done when:** Generated Rust code compiles. A test instantiates every node class, exercises every method, and verifies behavior matches the Python dataclass version. Tested on at least two grammars.

**Why this is a separate phase:** Generator-vs-handwrite is a key decision point. This phase proves the generator approach works before wiring it into the runtime pipeline. If the generated Rust code doesn't compile or has subtle behavioral differences, fixing the generator is isolated from integration concerns.

**Risk:** Medium. The generator must faithfully translate the `ModelType` union logic (`gsm2tree.py:19-93`), trivia type insertion (`gsm2tree.py:296-303`), and the class-name mapping (`gsm2tree.py:46-47`). Bugs here are subtle — wrong type in a `children` tuple, missing label enum variant, incorrect `__eq__` recursion.

---

## Phase 4: Runtime Integration — `plumbing.py` Adaptation

**Goal:** Make `plumbing.generate_parser()` produce Rust-backed CST nodes for any user grammar via ahead-of-time compilation.

This is the primary deliverable.

**Current flow** (`plumbing.py:101-112`):
```
gsm2tree.CstGenerator.gen_py_module()  ->  ast.Module
  -> compile() + exec()  ->  cst_globals dict
  -> types.ModuleType + sys.modules registration
```

**New flow — ahead-of-time compilation:**
- Add a CLI command to `genparser.py` that generates Rust CST source from a grammar and compiles it into a loadable `.so`/`.pyd` extension module. This uses `gsm2tree_rs.py` (Phase 3) to generate the `.rs` file, then invokes `maturin` or `cargo` to compile.
- The compiled extension module exposes a `register_classes(module)` function (Phase 3's interface). `plumbing.generate_parser` checks for a pre-compiled Rust module; if found, calls `register_classes` to populate the `types.ModuleType` that gets registered in `sys.modules`. If not found, falls back to the existing Python `exec()` path.
- The fallback is permanent, not a transitional crutch. User grammars work with or without the Rust compilation step. The Rust path is opt-in for performance.
- The module registration into `sys.modules` is preserved in both paths — the generated unparser imports from the dynamic module name (`gsm2unparser.py:1876-1892`) regardless of backing implementation.

**Key design detail — `register_classes` integration:**
`plumbing.py` currently builds a `cst_globals` dict from `exec()` output and copies non-underscore names to a `types.ModuleType`. With Rust: import the compiled extension, call its `register_classes(cst_module)` to populate the module directly, then register in `sys.modules` as before. The parser `exec()` path (`plumbing.py:118-129`) needs the CST classes in `parser_globals` — extract them from `cst_module.__dict__` instead of from `cst_globals`.

**Scope:**
- Extend `genparser.py` with a `compile-rust-cst` subcommand that: generates `.rs` source, compiles to `.so`/`.pyd`, places the artifact where `plumbing.py` can find it (e.g., alongside the grammar or in a configurable output directory).
- Modify `plumbing.generate_parser` to check for a pre-compiled Rust CST module and use it when available, falling back to Python `exec()` otherwise.
- The `gsm2unparser.py`-generated unparser imports from the CST module name. The module must be in `sys.modules` with the expected class names as attributes. This works with both paths as long as the module registration logic is preserved.
- All existing tests pass. New tests exercise: (a) the ahead-of-time compilation workflow end-to-end, (b) `plumbing.generate_parser` with a pre-compiled Rust module, (c) fallback to Python when no Rust module exists.

**Inputs:** Phase 3 (working generator producing compilable Rust CST code).

**Outputs:** `genparser.py` can compile a user grammar's CST to a Rust extension. `plumbing.generate_parser` loads it when available, falls back to Python otherwise. The full `parse -> CST -> unparse` pipeline works with Rust CST nodes.

**Done when:** A user grammar (not the FLTK grammar) goes through the full pipeline: `genparser.py compile-rust-cst` produces a `.so`, `plumbing.generate_parser` loads it, parsing produces Rust-backed CST nodes, unparsing reads them correctly. All existing tests pass. The Python fallback path also still works.

**Risk:** Medium. The main risks are: (a) the ahead-of-time compilation workflow (invoking `cargo`/`maturin` from Python, locating the output artifact, handling compilation errors); (b) the `register_classes` integration with `plumbing.py`'s parser-globals setup; (c) ensuring the dynamically-loaded Rust module's classes are compatible with the `isinstance` checks in generated unparser code.

**Decision point:** How should the compiled artifact be located? Options: (a) convention-based (same directory as grammar, predictable name), (b) explicit path argument to `plumbing.generate_parser`, (c) a manifest file. This affects DX but not correctness.

---

## Phase 5: Dogfooding — `fltk_cst.py` Replacement

**Goal:** Replace the committed `fltk_cst.py` (1127 lines of Python dataclasses) with a thin re-export module backed by the Rust extension. This is FLTK eating its own cooking — the FLTK grammar is just another grammar, and its CST should come from the same Rust pipeline built in Phases 3-4.

**Scope:**
- Use `gsm2tree_rs.py` (Phase 3) to generate the Rust CST module for the FLTK grammar. Compile it as part of the `fltk._native` extension (e.g., `fltk._native.fltk_cst`).
- Rewrite `fltk/fegen/fltk_cst.py` to re-export all classes from the Rust extension:
  ```python
  from fltk._native.fltk_cst import Grammar, Rule, Alternatives, Items, Item, Term, ...
  ```
- All static consumers of `fltk_cst` must work unchanged:
  - `fltk_parser.py` (line 4: `import fltk.fegen.fltk_cst`) — constructs nodes, sets spans, appends children.
  - `fltk_trivia_parser.py` (line 4: `import fltk.fegen.fltk_cst`) — same patterns.
  - `fltk2gsm.py` (line 4: `from fltk.fegen import fltk_cst as cst`) — reads `children` with indexing, slicing, striding (`children[::2]`), unpacks tuples, uses `isinstance`, compares labels.
- The formatter pipeline's static CST modules (`unparsefmt_cst.py`, `toy_cst.py` and their consumers) follow the same generated-CST pattern and share `terminalsrc.Span`; validated by the full test suite.
- All existing tests pass.

**Inputs:** Phase 4 (runtime integration proves the Rust CST classes work with parser and unparser for arbitrary grammars).

**Outputs:** `fltk_cst.py` backed by Rust. The full bootstrap pipeline works: parse `.fltkg` -> CST -> GSM -> generate parser/CST.

**Done when:** `uv run pytest` passes. `fltk_parser.py`, `fltk_trivia_parser.py`, and `fltk2gsm.py` work unmodified (no code changes to these files).

**Risk:** Low. By this phase, the generator and runtime integration are proven. This is a straightforward application of Phase 4's infrastructure to one specific grammar. The main risk is subtle API mismatch with static consumers that use advanced list operations (stride-2 slicing on odd-length list, etc.), but Phase 4's test coverage should have caught these.

---

## Dependency Graph

```
Phase 0 (build infra + grammar fix)
  |
  v
Phase 1 (Span PoC)
  |
  v
Phase 2 (nested enum PoC)
  |
  v
Phase 3 (generator)
  |
  v
Phase 4 (runtime integration — PRIMARY DELIVERABLE)
  |
  v
Phase 5 (dogfooding — fltk_cst.py replacement)
```

Strictly linear. Each phase validates assumptions required by the next. The core deliverable is Phase 4; Phase 5 is a nice-to-have that dogfoods the result.

---

## Risk Register

### R1: PyO3 nested-enum workaround fails
**Phase:** 2.
**Impact:** Blocks all subsequent phases. The `NodeClass.Label.FOO` access pattern is used in `fltk2gsm.py` (lines 36-42), in generated unparser code (`gsm2unparser.py:302-308`), and in generated parser code.
**Mitigation:** If `#[classattr]` doesn't work, alternative: define Label enums as module-level classes (`GrammarLabel`, `RuleLabel`, ...) and change `fltk_cst.py` re-exports to also alias `Grammar.Label = GrammarLabel`. This requires updating `fltk_parser.py` and `fltk2gsm.py`, which is undesirable but feasible since they're generated/regenerable.
**Likelihood:** Low. The `#[classattr]` pattern is documented in PyO3.

### R2: `Py<PyList>` mutation visibility
**Phase:** 2.
**Impact:** If `node.children` returns a copy rather than a live reference, `result.children.extend(item0.result.children)` (11 sites in `fltk_parser.py`) silently drops data.
**Mitigation:** Use `#[pyo3(get)]` on a `Py<PyList>` field. PyO3 returns the same Python object (increments refcount), not a copy. But this must be verified empirically.
**Likelihood:** Very low. `Py<PyList>` is a handle to the Python list object.

### R3: Maturin breaks existing build
**Phase:** 0.
**Impact:** Blocks everything. Switching from setuptools to maturin could break `uv run pytest`.
**Mitigation:** Maturin is a full replacement for setuptools, not a plugin. The migration is well-documented. Bazel is a separate concern — the current `MODULE.bazel` has no Rust support and won't get it in this phase. Bazel builds will not include the Rust extension until `rules_rust` is added later.
**Likelihood:** Low. Maturin is the standard build tool for PyO3 projects and handles mixed Python/Rust packages well.

### R4: Generator produces incorrect Rust
**Phase:** 3.
**Impact:** Delays Phase 4. Debugging generated Rust code is harder than debugging hand-written code.
**Mitigation:** Generate for a single simple rule first (e.g., `Identifier`), compile, test. Then scale to the full grammar. Keep the hand-written Phase 2 code as a reference implementation.
**Likelihood:** Medium. Code generation is fiddly. The trivia type insertion logic (`gsm2tree.py:296-303`) and the `ModelType` union handling (`gsm2tree.py:80-93`) are the most error-prone parts.

### R5: Performance regression
**Phase:** 4.
**Impact:** Rust CST nodes with `Py<PyList>` children may be *slower* than Python dataclasses due to FFI overhead on every method call. No baseline profiling data exists.
**Mitigation:** Benchmark before/after Phase 4. If performance regresses, investigate whether the regression is in node construction, method dispatch, or children list operations. Accept that this intermediate step trades performance for infrastructure establishment.
**Likelihood:** Medium. The analysis (`analysis-rust-cst-first.md`, section 9) acknowledges that Option B provides "marginal" performance benefit.

### R6: Ahead-of-time compilation workflow complexity
**Phase:** 4.
**Impact:** DX friction. Users must run a separate compilation step to get Rust CST nodes for their grammars. Compilation requires a Rust toolchain on the developer's machine.
**Mitigation:** The Python `exec()` fallback is always available — Rust compilation is opt-in. Keep the Python dataclass CST generation path (`gsm2tree.py`) fully functional. Document the Rust toolchain requirement clearly.
**Likelihood:** Low (technical); medium (adoption friction). Runtime Rust compilation (invoking `rustc`/`cargo` inside `plumbing.generate_parser`) is rejected — requires Rust toolchain on every end-user's machine; fragile and high-latency.

### R7: Dynamic module loading for compiled Rust CST
**Phase:** 4.
**Impact:** The compiled `.so`/`.pyd` must be loadable by `plumbing.py` at runtime. Finding the artifact, importing it, and calling `register_classes` could fail due to path issues, ABI mismatch, or Python version mismatch.
**Mitigation:** Use `importlib` for dynamic loading. The compilation step should produce artifacts compatible with the current Python interpreter. Test the full load path in CI.
**Likelihood:** Low. Python extension module loading is well-understood.

---

## Incremental Validation Strategy

| What | When validated | How |
|---|---|---|
| Rust extension loads in Python | Phase 0 | `import fltk._native` succeeds |
| Span API equivalence | Phase 1 | Full test suite passes with Rust Span |
| Nested enum access pattern | Phase 2 | Focused test: `Node.Label.FOO == Node.Label.FOO` |
| `Py<PyList>` mutation semantics | Phase 2 | Focused test: `node.children.extend(...)` modifies backing list |
| `isinstance` across FFI | Phase 2 | Focused test: `isinstance(node, Identifier)` |
| Generator correctness | Phase 3 | Generated code compiles; API equivalence test against Python CST |
| Generator generality | Phase 3 | Tested on FLTK grammar + at least one user grammar |
| Runtime pipeline with Rust CST | Phase 4 | `plumbing.generate_parser` loads pre-compiled Rust module; full parse/unparse pipeline works |
| Python fallback path | Phase 4 | `plumbing.generate_parser` works without Rust compilation (existing behavior preserved) |
| Static import compatibility | Phase 5 | `fltk_parser.py`, `fltk2gsm.py` work unmodified; full test suite |

Phase 0 is build infrastructure and grammar baseline fix. Phase 1 modifies `terminalsrc.py` (replacing the Span dataclass with a Rust import) but validates with the full test suite. Phase 2 adds standalone Rust code and focused tests — no existing code changes. Phase 3 adds `gsm2tree_rs.py` but doesn't touch existing code. Phase 4 is the first phase that modifies integration-critical code (`plumbing.py`, `genparser.py`). Phase 5 modifies `fltk_cst.py`. This front-loads risk validation and delays integration risk.

---

## What Cannot Be Validated Incrementally

- **Full-grammar CST node interaction**: Individual nodes can be tested in isolation (Phases 2-3), but the full grammar's node classes interacting via heterogeneous `children` lists can only be validated when all nodes exist and the parser/unparser exercise them together. This is Phase 4.
- **Unparser type dispatch**: The generated unparser uses `isinstance` checks against CST node types. These only exercise correctly when the full parser -> CST -> unparser pipeline runs end-to-end. Phase 4.
- **Performance**: Can only be measured after Phase 4 when a real grammar's full pipeline is Rust-backed. No useful micro-benchmark exists for isolated nodes.
- **Compilation workflow ergonomics**: The ahead-of-time compilation DX can only be evaluated in Phase 4 when real users (or tests acting as users) go through the `genparser.py compile-rust-cst` -> `plumbing.generate_parser` flow.

---

## Open Questions

1. **Type stubs (`.pyi`)?** Rust CST classes have no Python source for type checkers. Should `gsm2tree_rs.py` also generate `.pyi` stub files? Pyright is configured in `pyproject.toml:45-49`. Not blocking for correctness, but affects DX for type-checked code consuming CST nodes. Could defer to after Phase 4 since the re-export in `fltk_cst.py` (Phase 5) gives pyright *something* to analyze for that specific grammar.

2. **Artifact location convention**: How should `plumbing.generate_parser` find pre-compiled Rust CST modules? Convention-based (predictable name relative to grammar file), explicit path, or manifest? Affects Phase 4 implementation.

3. **Rust toolchain as user dependency**: The ahead-of-time compilation step requires a Rust toolchain. Should FLTK document this as an optional dependency? Should prebuilt wheels include Rust CST for the FLTK grammar itself (so end users get Rust CST for self-hosted operations without needing Rust)?
