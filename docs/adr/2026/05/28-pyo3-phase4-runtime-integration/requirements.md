# Phase 4 Runtime Integration: Requirements

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

This document supersedes the original Phase 4 / Phase 5 split in `docs/adr/2026/05/25-pyo3-cst-plan/phase-plan.md`. It defines a selectable dual-backend Phase 4: the caller chooses the Rust CST backend or the Python CST backend when FLTK parses a grammar. The original "compile from Python at runtime" and "replace `fltk_cst.py`" framings no longer apply.

---

## Framing

FLTK is a framework for generating parsers and CST that live **in a user's application**, not inside `fltk`. The Rust CST backend's primary deliverable is the general capability: a user takes their grammar, generates Rust CST source, builds it into a **standalone Python extension module they name, build, and install in their own project**, and points FLTK's runtime at it by module name. The user controls the module name and the build process.

**The central capability of this phase is backend selection.** When FLTK parses a grammar, the caller CAN CHOOSE the Rust CST backend OR the Python CST backend, explicitly, at the call site. This selection necessarily reaches the code that imports and consumes CST nodes — FLTK's own grammar-parsing path (`fltk2gsm.py`, the `fltk_parser`/`fltk_trivia_parser` constructing parsers) must be able to run against *either* backend, selectable. Adding that backend-selection seam to those consumers is **in scope for this phase**.

FLTK dogfooding its own `fegen` grammar with a Rust CST backend is **one test case** of this general capability, not the organizing goal. Where this document specifies acceptance criteria, the binding case is a **non-FLTK** user grammar; FLTK dogfooding is secondary. But FLTK's own grammar-parse path (`plumbing.parse_grammar` → `fltk2gsm.Cst2Gsm`) running against both backends, selectable, IS part of the acceptance criteria — it is the proof that the seam reaches the real consumers, not just synthetic tests.

---

## Goals

Let a caller select, per call, whether FLTK parses a grammar using the existing Python-dataclass CST backend OR a **pre-compiled, standalone, user-named** Rust CST backend. Two selection points exist and both must be backend-selectable:

1. **`plumbing.generate_parser`** — produces CST node classes + a parser for an arbitrary user grammar, from either backend, selected by a backend argument.
2. **`plumbing.parse_grammar` / `parse_grammar_file`** — FLTK's own path that parses `.fltkg` text into a `gsm.Grammar`, using the *fegen* grammar's parser + `fltk2gsm.Cst2Gsm`. This path must also be backend-selectable: parse the grammar text into a CST of the chosen backend and run the real `Cst2Gsm` consumer against it.

No `cargo`/`maturin`/`rustc` invocation from Python at runtime; build orchestration is the user's (FLTK ships build targets only for its own test/dogfooding artifacts). Selecting an unavailable Rust backend is a hard error, never a silent fallback.

---

## In Scope

- A backend-selection parameter on `plumbing.generate_parser` (Python dataclass vs Rust CST), where the Rust selector is a **user-supplied dotted module name** identifying an installed, importable extension.
- A backend-selection seam on `plumbing.parse_grammar` / `parse_grammar_file` (FLTK's own fegen-grammar parse path), so FLTK parses its own grammar input using either the Python CST backend or a Rust CST backend for the **fegen** grammar, selectable.
- **Modifying the real CST consumers to add the backend-selection seam.** Specifically:
  - `fltk2gsm.Cst2Gsm` — replace the module-level static binding `from fltk.fegen import fltk_cst as cst` with an injected CST module/namespace, so the *real* `Cst2Gsm` runs against either backend.
  - The fegen-grammar parser construction path used by `parse_grammar` — route node construction to the chosen backend's classes.
  - These edits are IN SCOPE and expected. The previous "static consumers must work unmodified" constraint is **dropped**; it is superseded by the backend-selection requirement.
- Importing a pre-compiled, standalone Rust CST extension module (built and installed by the user) and reading its CST node classes and label-enum types off the imported module.
- Producing a **standalone, independently buildable** Rust CST artifact: a `gsm2tree_rs.py` generator change that removes the `crate::UNKNOWN_SPAN` link-time coupling so the generated `.rs` compiles into a `cdylib` extension separate from FLTK's own crate.
- Hard-error semantics when a Rust backend is selected but its module is missing or fails to load.
- A FLTK-provided primitive that emits `.rs` CST source from a grammar (no compilation). The user compiles and installs it with their own build tool.
- Preserving the existing Python-dataclass CST path as a co-equal, first-class backend (the default).
- FLTK-internal build targets (Makefile) that build FLTK's *own* test/dogfooding Rust artifacts: a committed standalone-extension test fixture for a non-FLTK grammar, and a Rust CST extension for FLTK's own **fegen** grammar (so `parse_grammar` can run on the Rust backend).

## Out of Scope

- Any `cargo`/`maturin`/`rustc` invocation from `plumbing.py` or any runtime Python path. (Build is the user's; FLTK invokes it only for its own test artifacts via the Makefile.)
- Generating the user's `cdylib` crate scaffolding (`Cargo.toml` + the `#[pymodule]` wrapper that calls `register_classes`). FLTK emits `.rs` node source and documents the thin wrapper; full scaffolding is a follow-up (Open question `user-crate-scaffolding`).
- Backend selection for the *formatter* pipeline (`fmt_config.py`, `unparsefmt_parser.py`, `unparsefmt_cst.py`, `toy_cst.py`). These parse `.fltkfmt`/toy input, not user grammars, and do not flow through `generate_parser`/`parse_grammar`. They stay Python-only in Phase 4. (Their consumers may follow the same injection pattern in a later phase; not required here.)
- Type stubs (`.pyi`) for Rust CST classes.
- Performance benchmarking targets (the Python backend remains available as a benchmarking/reference baseline; no benchmark acceptance criteria are set here).
- A Rust-level shared-types crate (Option D, `fltk-cst-common` rlib + Cargo workspace). Not needed in Phase 4 because the node's `span` is an opaque `PyObject` and links no Rust-level FLTK type; recorded as `TODO(rust-cst-shared-rlib)` for a future where user extensions need to link Rust-level shared types.
- An ABI/version handshake between a user extension and `fltk._native`. Recorded as `TODO(rust-cst-abi-pinning)`.

---

## System Behavior

### Backend selection — `generate_parser`

`generate_parser` gains a way to select the CST backend. Two backends:

- **Python** (default when no Rust module name is supplied): the current `gsm2tree.CstGenerator.gen_py_module()` + `exec()` path (`plumbing.py:101-112`).
- **Rust**: import the user's pre-built, standalone extension by its dotted module name and read its CST node classes (and label-enum types) off the imported module.

Inputs → outputs:

- Input: a grammar, `capture_trivia` flag (unchanged), and a backend selector. The Rust selector is the **dotted module name** of the user's installed extension; that name is both the selection signal and the artifact location.
- Output: an unchanged `ParserResult` (`plumbing_types.py:14-23`) — `parser_class`, `cst_module` (a `types.ModuleType`), `cst_module_name`, `grammar`, `capture_trivia`. The `cst_module` abstraction is backend-agnostic; no new `ParserResult` field is required.

### Backend selection — `parse_grammar` (FLTK's own fegen path)

`parse_grammar` / `parse_grammar_file` parse `.fltkg` text into a `gsm.Grammar`. Today they hardcode the Python `fltk_parser.Parser` and `fltk2gsm.Cst2Gsm` bound to the Python `fltk_cst` module (`plumbing.py:46-60`). They gain a backend selector for the **fegen** grammar's CST:

- **Python** (default): current behavior — `fltk_parser.Parser` constructs Python `fltk_cst` nodes; `Cst2Gsm` consumes them.
- **Rust**: parse the grammar text into fegen CST nodes from a Rust backend (FLTK's own `fegen` Rust CST extension), and run the *real* `Cst2Gsm` against those Rust-backed nodes via the injection seam.

This is the user-facing "I can choose Rust or Python CST when I parse a grammar" capability for FLTK's own grammar, and it exercises the real consumer (`Cst2Gsm`) against both backends.

### Consumer injection seam (the in-scope consumer edits)

`fltk2gsm.Cst2Gsm` currently binds `from fltk.fegen import fltk_cst as cst` at module scope (`fltk2gsm.py:4`) and references `cst.Item`, `cst.Items.Label.NO_WS`, `isinstance(item, cst.Item)`, etc. throughout. This static binding is replaced by an **injected CST namespace**:

- `Cst2Gsm.__init__` accepts the CST module (the namespace providing `Item`, `Items`, `Disposition`, `Quantifier`, `Identifier`, `Literal`, `RawString`, etc., with their `.Label` attributes). It defaults to the Python `fltk_cst` module so existing callers are unaffected by default.
- All `cst.X` references inside `Cst2Gsm` resolve through the injected namespace, so the *same* `Cst2Gsm` code runs against Python-dataclass nodes or Rust-backed nodes depending on what is injected.
- `isinstance` and label-equality dispatch resolve against the injected backend's class/label objects — the exact objects the parser used to construct the nodes (type-identity invariant below).

The fegen parser path (`parse_grammar`) selects a backend and (a) constructs CST nodes with that backend's fegen classes and (b) injects that backend's CST namespace into `Cst2Gsm`. Both halves must reference the same backend so `isinstance` dispatch holds.

### Rust-backend path behavior (`generate_parser`)

When the Rust backend is selected (a module name is supplied):

1. The Python `CstGenerator` is still instantiated (needed by `ParserGenerator` at `plumbing.py:114`); only `gen_py_module()` + `exec()` are replaced.
2. The user's standalone extension is imported by name. Its CST node classes were registered by the module's own `register_classes` **at the extension's `#[pymodule]` init time** (the generated `register_classes`, `gsm2tree_rs.py:460-471`, is called by the user's crate init). By the time Python imports the module, it is already populated. The runtime **reads the classes off the imported module** and sets them as attributes on the per-call CST `types.ModuleType`.
3. **The binding contract is "the CST classes end up as attributes on `sys.modules[cst_module_name]`."** The per-call `types.ModuleType` registered under `cst_module_name` is the binding target; the user's extension is the *source* of the class objects. They are distinct module objects (see "Module-name convention").
4. That per-call module is registered in `sys.modules[cst_module_name]` before `generate_unparser` is callable — mandatory and unchanged in purpose.
5. Parser-namespace injection: the CST classes must reach `parser_globals`. Where the Python path does `parser_globals.update(cst_globals)` (`plumbing.py:127`), the Rust path injects the classes read from the imported user module.

### Standalone-artifact requirement and the `crate::UNKNOWN_SPAN` linkage

The generated `.rs` today references `crate::UNKNOWN_SPAN` (`gsm2tree_rs.py:127, 232-235`), a `pub(crate)` symbol in FLTK's crate (`lib.rs:10`) with `crate-type = ["cdylib"]` only (`Cargo.toml:8`). A separately compiled extension cannot link it. A standalone artifact is a requirement, so **resolving this linkage is in scope**.

The requirement: the generated `.rs` must compile into a `cdylib` extension that is **independent of FLTK's crate at link time** and depends on `fltk._native` only at **runtime** (for the `UnknownSpan` sentinel, already exposed as a Python object `fltk._native.UnknownSpan`, `lib.rs:25`). The mechanism is a `gsm2tree_rs.py` generator change that removes the `crate::` coupling; the build itself is the user's.

### Runtime dependency on `fltk._native`

A Rust-backed parser's process must have `fltk._native` importable (the user's extension lazily imports it for the `UnknownSpan` sentinel; the `Span` objects the parser writes into nodes are `fltk._native.Span` instances, stored opaquely). This is a documented runtime contract for the user's extension. No version-pinning is introduced (`TODO(rust-cst-abi-pinning)`).

### Hard-error semantics

When a Rust backend is selected and the module is missing, not loadable (import error, ABI/Python-version mismatch), or exposes no CST classes, the selecting function (`generate_parser` or `parse_grammar`) **raises** immediately. It does NOT fall back to the Python backend. Selecting the Python backend never attempts any Rust load. A missing `fltk._native` runtime dependency surfaces later — at first node construction during parsing (lazy sentinel fetch) — as a normal, loud `ImportError`, not a silent fallback.

### `isinstance` / type-identity invariant

The CST node type used to construct nodes MUST be the same Python type object the consumer (`Cst2Gsm` or the generated unparser) dispatches against. For `generate_parser`/unparser this holds because both reference the single `types.ModuleType` cached in `sys.modules[cst_module_name]`. For `parse_grammar`/`Cst2Gsm` this holds because the same backend's fegen classes are used to construct nodes and injected into `Cst2Gsm`. This invariant must hold for both backends and both paths.

### Module-name convention (`generate_parser`)

Two distinct names exist on the Rust path:

- **`cst_module_name`** — the per-call binding name `f"fltk_grammar_{id(grammar)}"` (`plumbing.py:107`), the coupling string between parser and unparser phases. Unchanged for both backends.
- **The user's Rust module name** — a user-controlled dotted name (e.g. `"mypkg.mygrammar_cst"`), the importable extension the user built. It is the *source* of class objects; it is NOT `fltk._native.<submodule>` and NOT the per-call name.

The Rust path imports the user's module, reads its public classes, sets them as attributes on the per-call `types.ModuleType`, and registers that under `cst_module_name`. This keeps the parser↔unparser coupling identical to today for both backends.

### Build workflow

The user builds and installs their extension; FLTK does not build it. FLTK provides:

- A documented primitive to **emit `.rs` CST source** from a grammar (no compilation), reusing `RustCstGenerator.generate()`. Invocable and testable.
- The `register_classes` contract and documentation of the thin `#[pymodule]` wrapper the user writes.
- Documentation of the one runtime dependency (`fltk._native` must be importable).

FLTK's Makefile targets build **FLTK's own** test/dogfooding artifacts only: a Rust CST extension for FLTK's own **fegen** grammar (so `parse_grammar` can run on the Rust backend) and a committed standalone-extension test fixture for a non-FLTK grammar. The runtime never invokes any build target.

---

## API Contract Both Backends Must Satisfy

For any grammar processed by `generate_parser`, and for the fegen grammar processed by `parse_grammar`, the CST module's classes must support all of the following (exploration lines 439-456). The real consumers (`Cst2Gsm`, the generated parser, the generated unparser) depend on these:

1. **Construction**: `ClassName(span=Span(start=s, end=e))` — keyword `span` arg, default `UnknownSpan`.
2. **Span write**: `node.span = new_span` — settable.
3. **Span read**: `node.span.start`, `node.span.end`.
4. **Children mutate via extend**: `node.children.extend(other.children)` — `children` is a live Python list (not a snapshot).
5. **Typed append**: `node.append_{label}(child=value)` — keyword `child` arg.
6. **Full list protocol on `children`**: `len()`, `[i]`, `[i:]`, `[::2]`, `[1::2]`, `[-1]`. (Items 4, 6, 7 are the most constraining; `fltk2gsm.py` uses stride and negative indices, exploration line 408.)
7. **Tuple items**: `node.children[i]` is `(label_or_None, value)`, indexable as a 2-tuple.
8. **Label equality and containment**: `label == ClassName.Label.FOO`, `label in (ClassName.Label.FOO, ...)` — requires `__eq__` + `__hash__` on the label enum.
9. **Class-attribute label access**: `ClassName.Label.VARIANT`.
10. **`isinstance` dispatch**: `isinstance(node, ClassName)`.
11. **Iterator methods**: `node.children_{label}()` iterable; `node.child_{label}()` single value; `node.maybe_{label}()` Optional.
12. **Generic `child()`**: returns `(label, value)`.

The Python dataclass backend satisfies these today. The Rust backend is verified against these by AC5 (the contract operations against a generated **non-FLTK** standalone extension) and AC8 (the *real* `Cst2Gsm` running against the Rust fegen backend) — not pre-discharged by Phase 2, which validated only two hand-written nodes.

---

## User-Visible Surface

- **`generate_parser` signature**: a `rust_cst_module: str | None = None` parameter. `None` ⇒ Python backend (default, current behavior exactly); a dotted module name ⇒ Rust backend, importing that module. (If an explicit `backend=` enum is preferred, that is a surface-only change — see Open question `selector-surface-form`.)
- **`parse_grammar` / `parse_grammar_file` signature**: a backend selector for FLTK's fegen CST (default Python). When the Rust backend is selected, the FLTK fegen Rust CST extension is used to construct nodes and `Cst2Gsm` runs against them. Surface shape resolved in design.
- **`Cst2Gsm` signature**: an injected CST namespace parameter, defaulting to the Python `fltk_cst` module.
- **Error on missing/unloadable Rust module**: a clear exception type and message naming the selected module name. No silent degradation.
- **`.rs`-emit primitive**: a documented, testable FLTK-provided way to emit `.rs` CST source from a grammar without compiling. Resolved to a `gen-rust-cst` subcommand.
- **User build, documented not encoded**: FLTK documents how the user (1) emits `.rs`, (2) writes a `cdylib` crate whose `#[pymodule]` init calls the emitted `register_classes`, (3) builds/installs with their own tool, (4) passes the resulting module name to `generate_parser`.
- **FLTK Makefile targets**: named targets that build FLTK's own test/dogfooding artifacts only. Discoverable via `make` and documented as FLTK-internal.

---

## Constraints

- **No runtime compilation**: `plumbing.py` and all runtime Python paths must not invoke `cargo`, `maturin`, or `rustc`.
- **No silent fallback**: hard error on Rust-backend selection failure.
- **Real consumers must run on the selected backend**: the *actual* `fltk2gsm.Cst2Gsm` (not a hand-written substitute) must run against both backends, selectable. A hand-written contract test is NOT an acceptable substitute for running the real consumer on the Rust backend.
- **Default behavior unchanged**: with no backend argument supplied, `generate_parser`, `parse_grammar`, and `Cst2Gsm` behave exactly as today (Python backend). All existing tests pass unchanged, including the module-registration invariants (`test_plumbing.py:53-67, 81-88`) and the unparser bridge via `cst_module_name`.
- **Python-visible CST API preserved by the generator change**: the `gsm2tree_rs.py` change that removes the `crate::UNKNOWN_SPAN` coupling must not alter the Python-visible CST API (nodes still expose `span`/`children` and the same methods). The change is localized to source emission.
- **Security**: Rust CST source generation already validates rule names / labels against `^[_a-z][_a-z0-9]*$` before emission (`gsm2tree_rs.py:54-72`); the new runtime-sentinel emission introduces no user-controlled identifiers, so no new injection surface.
- **Backend parity**: the Python backend is retained deliberately as a first-class testing/benchmarking/reference backend, not as a deprecated fallback.

---

## Acceptance Criteria

The primary binding Rust case is a **non-FLTK** user grammar built as a standalone extension. FLTK dogfooding (the fegen Rust CST) is secondary — but the *real* `Cst2Gsm` running on the Rust fegen backend (AC8) is now a binding criterion, not deferred.

Acceptance criteria split into two tiers. **Tier 1 (runtime-contract, Python-side)** — ACs 1, 4, and the Python halves of 7/8 — are independent of any Rust artifact. **Tier 2 (artifact-dependent)** — ACs 2, 3, 5, 6, the Rust half of 7, and AC8 — require a real, loadable Rust CST extension and are gated on the relevant fixture/extension being built.

1. (Tier 1) `generate_parser`/`parse_grammar`/`Cst2Gsm` with the Python backend (default) behave exactly as today; all existing `test_plumbing.py` / `test_plumbing_integration.py` / fegen tests pass unchanged.
2. (Tier 2) `generate_parser` with the Rust backend selected and a valid pre-built **standalone** extension: the returned `cst_module` is in `sys.modules[cst_module_name]`, exposes the grammar's node classes, and `hasattr(cst_module, "<RuleClass>")` holds per rule. Verified against the **non-FLTK standalone extension fixture**.
3. (Tier 2) With the Rust backend, a full `parse → CST → unparse` round trip on the **non-FLTK** grammar succeeds via the standalone, user-named extension: parser constructs Rust-backed nodes, generated unparser reads them, `isinstance` dispatch resolves.
4. (Tier 1) Selecting the Rust backend with a missing or unloadable module raises a clear exception and performs NO Python-backend fallback (assertable: `sys.modules` is not populated with a Python-exec'd CST module for that grammar, and no parse occurs).
5. (Tier 2) **PRIMARY binding API-Contract verification:** the full set of API-Contract operations (items 1-12) executes correctly against node instances constructed from the **non-FLTK standalone extension's** classes. This discharges the API Contract for the general capability.
6. (Tier 2) FLTK's Makefile produces a loadable **standalone** Rust CST extension for the non-FLTK fixture grammar, and a Rust CST extension for FLTK's own **fegen** grammar, with no Python-side compilation invoked at parse time.
7. Both backends produce CST modules satisfying every item in the API Contract section. The Python half is Tier 1; the Rust half is Tier 2 (verified by AC5 against the non-FLTK standalone extension).
8. (Tier 2 — **binding, not deferred**) The *real* `fltk2gsm.Cst2Gsm` runs against the Rust **fegen** CST backend, selected via `parse_grammar` (or directly via the injected-namespace seam): parse a real `.fltkg` grammar with the Rust backend selected and assert the resulting `gsm.Grammar` is equivalent to the one produced by the Python backend on the same input. This proves the seam reaches the real consumer on both backends. No hand-written substitute may stand in for `Cst2Gsm` here.

**Test wiring for Rust-path ACs**: ACs 2, 3, 5, 6, 8 require a built Rust artifact. Per `rust-test-policy`: skip-when-absent for the local `uv run pytest`; CI runs the FLTK build targets before pytest so the standalone-extension and fegen-Rust-backend paths are actually exercised. A CI lane that skips every Tier-2 test is a failure signal (artifacts not built).

---

## Open Questions

### default-backend [RESOLVED → Python]
The default when no backend is selected is the **Python backend** — the only option consistent with "explicit selection" + "no silent fallback" + "existing tests pass unchanged." The Rust backend is strictly opt-in.

### selector-surface-form [USER]
`generate_parser`'s selector is resolved to a single `rust_cst_module: str | None = None` module-name parameter. `parse_grammar`'s fegen-backend selector and `Cst2Gsm`'s namespace parameter are resolved in design. If the user prefers an explicit `backend: Literal["python","rust"]` enum, that is a surface-only change with no behavioral consequence.
- Proposed: **single `rust_cst_module` parameter** for `generate_parser`; a `backend`-style selector for `parse_grammar`. To redirect: state the desired parameter set.

### user-crate-scaffolding [USER]
Should FLTK generate the user's `cdylib` crate scaffolding (`Cargo.toml` + the `#[pymodule]` wrapper that calls `register_classes`), or only emit the `.rs` node source and document the thin wrapper?
- Consequence: emitting only `.rs` keeps FLTK agnostic about the user's build tool; full scaffolding is more turnkey but opinionated about layout.
- Proposed: **emit `.rs` + document the wrapper** for Phase 4; a `gen-rust-crate` scaffolding command is a clean follow-up.

### rust-backend-grammar-consistency-check [USER]
Should `generate_parser` verify that `rust_cst_module` was generated from the same `grammar` (compare rule/class names), or is a mismatch a caller responsibility surfacing as a normal parse-time error?
- The API Contract requires no check; a mismatch fails loudly at node construction.
- Proposed: **no runtime check** (caller responsibility). Cheap follow-up if desired.

### rust-test-policy [USER]
Do the Rust-path acceptance tests (ACs 2, 3, 5, 6, 8) run in the default `uv run pytest`, and what happens when no Rust artifact has been built?
- Options: (a) skip-when-absent — Rust-path tests skip if the fixture/extension is not importable; CI runs the FLTK build target before pytest; (b) hard-require — fail if absent (breaks Python-only contributors); (c) gate behind a pytest marker in a dedicated lane.
- Proposed: **(a) skip-when-absent + CI builds the artifacts before pytest.** To redirect: state the desired policy.
