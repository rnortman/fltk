# Design: split generated Rust-backend Python bindings into cst and parser modules

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Inputs: `request.md`, `exploration.md` (same dir).

## 1. Root cause / context

All registrations for a generated Rust extension land in one flat pyo3 module: `Span`, `SourceText`, `NodeKind`, per-rule node classes + label enums, `ApplyResult`, `Parser` (`tests/rust_cst_fegen/src/lib.rs:17-23`, `src/lib.rs:18-29`). pyo3 `add_class` is an unconditional `setattr` (exploration §"Does pyo3 add_class silently shadow"); a rule named `parser` or `apply_result` makes its CST class silently unreachable. The Python backend is immune because it emits separate `*_cst.py` / `*_parser.py` modules. Per user direction (request.md), the fix is to mimic that separation, not to bolt a reserved-name check onto the flat layout.

Three sub-problems ride along:

1. **Near-vestigial module-local `Span`/`SourceText`.** `span_to_pyobject` routes span construction through canonical `fltk._native.Span` (`crates/fltk-cst-core/src/cross_cdylib.rs:208-237`), so spans a consumer module *returns* are canonical-type instances. Extraction accepts both types: `extract_span` has a fast path for locally-registered instances (`obj.extract::<Span>()`, `cross_cdylib.rs:258`) before the canonical-type check; `extract_source_text` likewise (`downcast::<SourceText>()`, `cross_cdylib.rs:68`). The real effect of `m.add_class::<Span>()` in a consumer module is exposing a Python-side *constructor* for module-local instances — never needed on main parse paths (returned spans are canonical), but the only way Python code can construct a *foreign-cdylib* `Span`/`SourceText`, which the cross-cdylib test suite depends on (§2.4). Registration is not needed for extraction itself: pyo3 type objects are created lazily on first use (`PyTypeInfo::type_object`), so extract-path type checks do not depend on `add_class`. The comment in `tests/rust_cst_fixture/src/lib.rs:6-7` ("needed for span extraction") states the wrong reason; that registration is load-bearing for a different reason (§2.4).
2. **Residual `NodeKind` collision.** `NodeKind` shares the cst module with per-rule classes (`gsm2tree_rs.py:1517-1531`); a rule named `node_kind` clobbers it — and also fails Rust compilation (emitted `pub struct NodeKind` vs the emitted `pub enum NodeKind`). Rules named `span`/`shared`/`cst_error` already produce uncompilable Rust (E0255 against the `use fltk_cst_core::{Span, Shared, CstError}` preamble, `gsm2tree_rs.py:261-279`). A small generation-time check is warranted.
3. **`fltk._native` top level mixes canonical `Span`/`SourceText`/`UnknownSpan` with PoC grammar classes** (`src/lib.rs:29`), leaving the Span-clobber hazard live in the canonical module itself.

### Verification: dependents of module-local Span/SourceText (request item)

- **`tests/test_rust_span.py` depends on `phase4_roundtrip_cst`'s registrations** (the `tests/rust_cst_fixture` crate): `phase4.SourceText("hello world")` in the foreign-cdylib `_with_source_unchecked` tests (lines 340, 350, 360); `phase4.Span(3, 7)` / `phase4.Span.with_source(...)` in `TestSpanToPyobjectCaching` (lines 636-647); and five ABI-gate subprocess scripts (`cst.Config(span=cst.Span(0, 5))`, lines 454-455 et seq.) — the entire `TestSpanPathAbiGate` suite. These tests construct foreign-cdylib instances from Python, which is possible *only* through the consumer module's registered classes; there is no substitute import path.
- No other dependents: grep over `tests/`, `fltk/`, `docs/` finds no access to `fegen_rust_cst.Span`, `rust_parser_fixture.Span`, or `.SourceText` on those modules. Other tests use `fltk._native.Span`, `fltk.fegen.pyrt.terminalsrc.Span`, or the `fltk.fegen.pyrt.span` selector (`tests/test_span_protocol.py`, `tests/test_rust_span.py:224` targets `fltk._native`).
- `tests/test_phase4_fegen_rust_backend.py` `_EXPECTED_CLASSES` lists only grammar node classes.
- `docs/adr/2026/06/06-rust-cst-pyi/design.md:58` documents `mod.Span` as nonexistent on generated modules; dropping from `rust_cst_fegen`/`rust_parser_fixture` aligns reality with it. `rust_cst_fixture` is a deliberate, documented exception (§2.4).

Conclusion: drop is safe for `rust_cst_fegen` and `rust_parser_fixture`; `rust_cst_fixture` keeps its registrations (§2.4).

## 2. Proposed approach

### 2.1 Module topology: attribute submodules + `sys.modules` registration

A generated extension cdylib exposes one top-level `#[pymodule]` containing only submodules (two exceptions keep top-level Span types: `fltk._native`, the canonical home — §2.5; `rust_cst_fixture`, the cross-cdylib test fixture — §2.4):

- `<module>.cst` — `NodeKind`, per-rule node classes, label enums.
- `<module>.parser` — `Parser`, `ApplyResult`.

Submodules are created with `PyModule::new`, attached via `add_submodule`, and inserted into `sys.modules` under their fully qualified dotted name so `import <module>.cst` and `from <module>.parser import Parser` work (precedent: `src/lib.rs:33-47`). CPython's `_find_and_load` honors `sys.modules` entries created as parent-import side effects, so `importlib.import_module("<module>.cst")` works even when the parent was not yet imported.

Class names are unchanged (`Parser`, `ApplyResult`, `NodeKind`, node classes, `ClassName_Label`) — only import paths move, which the compat rule explicitly permits. No transitional top-level aliases: the request authorizes import-statement updates, and aliases would re-create the collision surface the split removes.

Class names are CamelCase (`naming.snake_to_upper_camel`) and submodule attribute names are lowercase, so no rule can collide with the `cst`/`parser` attributes themselves.

### 2.2 Shared helper in fltk-cst-core

New function in `crates/fltk-cst-core` (python-gated, exported alongside `span_to_pyobject` etc. in `src/lib.rs`; implementation can live in `cross_cdylib.rs` or a new `py_module.rs`):

```rust
#[cfg(feature = "python")]
pub fn register_submodule<'py>(
    parent: &Bound<'py, PyModule>,
    parent_qualified_name: &str,
    name: &str,
    register: impl FnOnce(&Bound<'py, PyModule>) -> PyResult<()>,
) -> PyResult<Bound<'py, PyModule>>
```

Behavior, in order: sanity-check that the last dotted segment of `parent_qualified_name` equals `parent.name()?` (catches copy-paste typos; `PyValueError` on mismatch); `PyModule::new(py, name)`; run `register`; `parent.add_submodule(&sub)`; insert `sys.modules["{parent_qualified_name}.{name}"] = sub` (last, so a registration failure leaves no entry for *this* submodule); return the submodule.

`parent_qualified_name` is an explicit parameter because at `#[pymodule]` init time the module's `__name__` is the unqualified def name (`"_native"`, not `"fltk._native"`) — the reason `src/lib.rs:42` hardcodes the path today. The existing open-coded sys.modules dance in `src/lib.rs:33-47` is replaced by this helper.

Each consumer cdylib statically links its own fltk-cst-core copy; the helper is stateless pyo3 mechanics, so cross-cdylib duplication is harmless.

### 2.3 Generated emitters: signatures unchanged

`cst::register_classes(module)` (`gsm2tree_rs.py:1517-1531`) and `parser::register_classes(module)` (`gsm2parser_rs.py:914-921`) keep their signatures and bodies — they register their classes into whatever module they are handed. What changes is the handwritten `lib.rs` wiring (lib.rs files are not generated; confirmed by grep — no emitter writes them). Canonical consumer pattern, applied to all in-tree crates and documented in `genparser.py` help text and the fixture lib.rs comments:

```rust
#[pymodule]
fn fegen_rust_cst(m: &Bound<'_, PyModule>) -> PyResult<()> {
    fltk_cst_core::register_submodule(m, "fegen_rust_cst", "cst", cst::register_classes)?;
    fltk_cst_core::register_submodule(m, "fegen_rust_cst", "parser", parser::register_classes)?;
    Ok(())
}
```

The obsolete `TODO(parser-bindings-name-collision)` comment at `gsm2parser_rs.py:816-820` is removed, along with its `TODO.md` entry (TODO.md:88) — the parser module contains no per-rule names, so `Parser`/`ApplyResult` collisions are structurally impossible after the split.

### 2.4 Drop Span/SourceText registrations from consumer modules (scoped)

Remove `m.add_class::<Span>()` / `m.add_class::<SourceText>()` from `tests/rust_cst_fegen/src/lib.rs` and `tests/rust_parser_fixture/src/lib.rs` (no dependents — §1 verification), and from the documented consumer pattern. Document `fltk._native.Span` / `fltk._native.SourceText` as the import location in the gen-rust-cst help text; `fltk._native` (`src/lib.rs:20-23`) keeps its registrations as the canonical home.

**Exception: `tests/rust_cst_fixture/src/lib.rs` keeps both registrations, at the extension's top level** (alongside the `cst` submodule — they are not per-grammar classes). It is the dedicated cross-cdylib fixture, and `tests/test_rust_span.py` requires a Python-side constructor for foreign-cdylib `Span`/`SourceText` instances (§1) — the registration is what makes those instances constructible, and they flow through the extract fast paths. Replace the wrong comment at `lib.rs:6-7` with the correct rationale: registered so tests can construct foreign-cdylib instances; not required for span extraction. After the split, `test_rust_span.py` references become `phase4.Span` / `phase4.SourceText` (unchanged, top level) and `phase4.cst.Config` (moved); the five ABI-gate subprocess scripts update accordingly (§4.7).

### 2.5 `fltk._native` restructure

- Top level keeps: `Span`, `SourceText`, `UnknownSpan` (canonical, per request constraint).
- PoC grammar classes move from top level (`cst_generated::register_classes(m)`, `src/lib.rs:29`) into a new submodule `fltk._native.poc_cst` via the helper. Removes the live hazard of PoC rule classes clobbering canonical `Span`. The only in-tree consumer of top-level PoC classes is `tests/test_rust_cst_poc.py` (`from fltk._native import Identifier, Items, ...`; verified by grep — all other tests reach PoC/fegen classes via `fltk._native.fegen_cst` or `fegen_rust_cst`); its imports move to `fltk._native.poc_cst`.
- `fltk._native.fegen_cst` keeps its name and contents (already split-style, cst-only — `fltk._native` hosts two grammars, so per-grammar submodule names apply there instead of plain `cst`); its registration switches to the helper.
- `fltk/_native/__init__.pyi`: PoC classes stay omitted (unchanged policy, see its header note); update the header comment for the `poc_cst` move. `fltk/_native/fegen_cst.pyi` unchanged.

### 2.6 Residual reserved-name check (the `node_kind` decision)

Decision: **reject at generation time** (not a separate namespace — `NodeKind` is part of the cst surface and the protocol; moving it would churn annotations).

In `RustCstGenerator.__init__` (`gsm2tree_rs.py:56-80`), alongside the existing identifier/label validation, add:

```python
_RESERVED_CLASS_NAMES: dict[str, str] = {
    "NodeKind": "the generated NodeKind enum",
    "Span":     "fltk_cst_core::Span (imported by generated cst.rs and parser.rs)",
    "Shared":   "fltk_cst_core::Shared (imported by generated cst.rs and parser.rs)",
    "CstError": "fltk_cst_core::CstError (imported by generated cst.rs)",
}
```

For each rule, if `class_name_for_rule_node(rule.name)` is in the set, raise `ValueError` naming the rule, the derived class name, and the collision target (precedent: `_RESERVED_LABELS`, `gsm2tree_rs.py:24-26, 73-80`). Rationale per entry: `NodeKind` is both a silent Python clobber inside the cst module and a Rust conflict (emitted `pub struct NodeKind` vs the emitted `pub enum NodeKind`); `Span`/`Shared`/`CstError` are Rust E0255 against cst.rs's `use` preamble (`gsm2tree_rs.py:263-265`) — today these grammars produce uncompilable output with an opaque rustc error, so a clear generation-time error is strictly an improvement. The check lives in `RustCstGenerator.__init__` because `RustParserGenerator` constructs one (`gsm2parser_rs.py:82`), giving a single chokepoint for both `gen-rust-cst` and `gen-rust-parser`.

`SourceText` is deliberately **excluded**: a rule named `source_text` emits `pub struct SourceText` into cst.rs, whose preamble does not import `SourceText` (`gsm2tree_rs.py:263-267`); parser.rs's `use fltk_cst_core::{Shared, SourceText, Span}` (`gsm2parser_rs.py:274`) lives in a different module with all rule references `cst::`-qualified — no E0255 on either side. Post-split, no fixed `SourceText` is registered in any generated submodule, so there is no Python-level collision either. Rejecting it would impose a needless restriction on grammar authors. §4.2 includes a positive generation test for a `source_text` rule.

Out of scope, recorded as a new TODO (`TODO(rust-generated-ident-collisions)` in `gsm2tree_rs.py` + `TODO.md` entry): pairwise Rust-identifier collisions between rule-derived names (`foo_child` → `FooChild` vs `Foo`'s child enum; `foo_label`/`Py`-prefix analogues). Pre-existing, unaffected by the split, requires cross-rule analysis rather than a fixed set.

### 2.7 `fltk/plumbing.py` parameter semantics

`rust_cst_module` / `rust_fegen_cst_module` keep their meaning — "dotted module name of the CST module" — but the value callers pass becomes the cst submodule path, e.g. `"fegen_rust_cst.cst"`. `_load_rust_cst_classes` (`plumbing.py:81-110`) needs no code change: `importlib.import_module` resolves the dotted submodule via the sys.modules registration, and the `vars()` scrape finds the classes. Passing the top-level module by mistake yields the existing clear `RustBackendUnavailableError(... "exposes no CST classes")` (submodules are not `type` instances). Docstrings and the Makefile comment (`Makefile:109-110`) updated.

Behavioral cleanup worth noting in the docstring: previously the flat module's scrape included Rust `Parser`/`ApplyResult`/`Span`/`SourceText`, and `parser_globals.update(public)` (`plumbing.py:264`) silently overwrote the Python parser's `ApplyResult`/`Span` globals with constructor-less Rust types. After the split, `public` contains only `NodeKind` + node classes + label enums.

### 2.8 .pyi stub layout

`generate_pyi` output (the cst surface) is unchanged in content. Documented placement for a consumer module `<name>` becomes the stub-package form: directory `<name>/` containing `__init__.pyi` (may be comment-only) and `cst.pyi`, never an `__init__.py` (runtime: regular extension module beats namespace-dir portion — established by `fltk/_native/__init__.pyi:1-7`). Update the `--pyi-output` help text (`genparser.py:281-293`) and the generator-source comment at `gsm2tree_rs.py:142-143` (a Python comment in the generator itself; it is not emitted into stubs — stub content is unchanged). No parser stub exists today and none is added (unchanged gap). No in-tree consumer-crate stubs exist; `fltk/_native` stubs are covered in §2.5.

### 2.9 Collision fixture: compile-level proof for `parser` / `apply_result` rules

The request requires a compiled grammar with rules named `parser` and `apply_result` whose CST classes and parser are both reachable. Do **not** add these rules to `rust_parser_fixture.fltkg`: the Python parity harness generates a Python parser from the same grammar at runtime, and `plumbing.generate_parser` execs cst classes and the parser class into one globals dict (`plumbing.py:264-266`), where a cst class named `Parser` collides with the generated parser class — a Python-backend plumbing issue that is an explicit non-goal here.

Instead, piggyback on the existing `tests/rust_parser_fixture` crate (avoids a new Cargo crate, build target, and CI wiring):

- New grammar `fltk/fegen/test_data/collision_fixture.fltkg` — minimal, with rules `parser` and `apply_result` (referenced from a root rule so the grammar is meaningful and parseable).
- Generate `collision_cst.rs` (gen-rust-cst) and `collision_parser.rs` (gen-rust-parser, `--cst-mod-path super::collision_cst`) into the crate; Makefile regen target alongside the existing ones (`Makefile:120-132`).
- `tests/rust_parser_fixture/src/lib.rs` registers four submodules: `cst`, `parser` (existing grammar), `collision_cst`, `collision_parser`. This doubles as the in-tree demonstration that one cdylib can host multiple grammars (matching `fltk._native`).

### 2.10 Files touched (summary)

| File | Change |
|---|---|
| `crates/fltk-cst-core/src/lib.rs` (+ impl file) | `register_submodule` helper |
| `fltk/fegen/gsm2tree_rs.py` | `_RESERVED_CLASS_NAMES` check; stub-layout generator-source comment update (§2.8); new TODO comment |
| `fltk/fegen/gsm2parser_rs.py` | remove obsolete TODO comment |
| `fltk/fegen/genparser.py` | help-text updates (wiring pattern, Span import location, stub layout) |
| `src/lib.rs` | helper-based wiring; `poc_cst` submodule; keep canonical Span/SourceText/UnknownSpan |
| `tests/rust_cst_fegen/src/lib.rs` | `cst` + `parser` submodules; drop Span/SourceText |
| `tests/rust_parser_fixture/src/lib.rs` | same + collision submodules |
| `tests/rust_cst_fixture/src/lib.rs` | `cst` submodule; keep top-level Span/SourceText (cross-cdylib fixture, §2.4); correct comment |
| `fltk/fegen/test_data/collision_fixture.fltkg` + generated `collision_*.rs` | new |
| `fltk/plumbing.py`, `Makefile` | docstrings/comments; regen target |
| `fltk/_native/__init__.pyi` | header-comment update |
| `TODO.md` | remove `parser-bindings-name-collision`; add `rust-generated-ident-collisions` |
| Tests (see §4) | import-path updates + new tests |

Coordination: `rust-naming-shared` (`docs/adr/2026/06/11-rust-naming-shared/`) is sequenced after/with this; this design adds no new inline naming-convention duplication (the reserved set lives next to the existing validation), so commits stay separable.

## 3. Edge cases / failure modes

- **Partial init failure.** If `parser` submodule registration fails after `cst` succeeded, the parent import fails but `sys.modules["<module>.cst"]` lingers. Registration failures are deterministic build bugs (not data-dependent); same failure class as the existing hand-rolled code in `src/lib.rs`. Accepted; helper doc-comment notes it.
- **Wrong `parent_qualified_name`.** Typo breaks `import <module>.cst` while attribute access still works — subtle. Mitigated by the last-segment-vs-`parent.name()` check (§2.2); a full-path typo in the package prefix (e.g. `"ftlk._native"`) is not detectable at init and is caught by the import-mechanics tests (§4).
- **`__module__` of pyclasses.** No `#[pyclass(module = "...")]` is emitted today, so `repr(type)` shows `builtins.*`; unchanged by this work (the module name is a lib.rs-time fact the generator doesn't know). Known cosmetic limitation, not a regression.
- **Multiple consumer extensions.** `sys.modules` keys are qualified by the parent module name, which Python guarantees unique per import path; no cross-extension key collisions.
- **Rule named `node_kind`/`span`/`shared`/`cst_error`.** Rejected with `ValueError` at generator construction (§2.6); `gen-rust-cst`/`gen-rust-parser` CLIs already surface `ValueError` as a clean error (`genparser.py:319-322, 369-374`). A rule named `source_text` is valid (§2.6).
- **`fegen_cst`-style multi-grammar hosts.** Per-grammar submodule names (`poc_cst`, `fegen_cst`, `collision_cst`, ...) coexist with the plain `cst`/`parser` convention for single-grammar crates; the helper is name-agnostic.
- **Downstream breakage.** Out-of-tree consumers must update import statements (`fegen_rust_cst.Parser` → `fegen_rust_cst.parser.Parser`, etc.) and `rust_cst_module=` values. Explicitly authorized by the request; class names, annotations, and call sites are untouched.

## 4. Test plan

Generator-level (fast, no compile):

1. `tests/test_gsm2tree_rs.py`: grammar with rule `node_kind` (and parametrized `span`, `shared`, `cst_error`) → `RustCstGenerator` raises `ValueError` naming rule, class name, and collision target.
2. `tests/test_gsm2tree_rs.py` / `fltk/fegen/test_gsm2parser_rs.py`: grammar with rules `parser`, `apply_result`, and `source_text` generates cst and parser sources without error; cst source contains `name = "Parser"` / `name = "ApplyResult"` handle pyclasses; parser source still contains the fixed `name = "Parser"` / `name = "ApplyResult"` — proving the split (not a rename) is what resolves the collision. The `source_text` rule documents that it is *not* reserved (§2.6).

Compiled-extension level (require built fixtures, `importorskip` as today):

3. Collision fixture (§2.9): `rust_parser_fixture.collision_cst.Parser` and `.ApplyResult` are CST node classes; `rust_parser_fixture.collision_parser.Parser` parses a sample input and `.ApplyResult` wraps results; the two `Parser` attributes are distinct types. **This is the headline acceptance test.**
4. Import mechanics, on `fegen_rust_cst`: `import fegen_rust_cst.cst`, `from fegen_rust_cst.parser import Parser`, `importlib.import_module("fegen_rust_cst.cst")` all succeed; `sys.modules["fegen_rust_cst.cst"] is fegen_rust_cst.cst`.
5. Span drop (scoped per §2.4): `not hasattr(fegen_rust_cst, "Span")` / `"SourceText"`, ditto on `.cst` and `.parser`, and same for `rust_parser_fixture`; `phase4_roundtrip_cst.Span` / `.SourceText` still present at top level (deliberate exception); `fltk._native.Span` still present; existing `node.span`-is-`fltk._native.Span` tests (`tests/test_gsm2tree_rs.py:322`) unchanged.
6. `fltk._native.poc_cst`: PoC classes reachable at new path; absent from `fltk._native` top level; `fltk._native.fegen_cst` unchanged.

Updated existing suites (mechanical import-path changes, no assertion-logic changes):

7. `test_phase4_fegen_rust_backend.py` (`_EXPECTED_CLASSES` against `.cst`; `rust_fegen_cst_module="fegen_rust_cst.cst"`), `test_rust_parser_bindings.py`, `test_rust_parser_parity_fegen.py`, `test_rust_parser_parity_fixture.py`, `test_clean_protocol_consumer_api.py`, `test_cross_backend_label_equality.py`, `test_rust_cst_poc.py`, `fltk/test_plumbing.py`, and `tests/test_rust_span.py` (node-class references move to `phase4_roundtrip_cst.cst.*` — including inside the five ABI-gate subprocess scripts; `phase4.Span`/`phase4.SourceText` constructor references unchanged per §2.4).
8. Parity suites green — cross-backend behavior is untouched (only registration moved); `uv run pytest`, `cargo test` (workspace + fixture crates incl. `--no-default-features`), `make fix` + `make check` clean after regen.

## 5. Open questions

None. The two judgment calls — no transitional top-level aliases (§2.1) and rejection over renamespacing for `node_kind` (§2.6) — are resolved by the request's compat rule and constraints.
