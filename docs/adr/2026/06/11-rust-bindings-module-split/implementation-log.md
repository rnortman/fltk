## Increment 9 — cleanup (obsolete TODO, docstrings, help text) + acceptance tests §4.3-§4.6 (commit 4fe645d)

- `fltk/fegen/gsm2parser_rs.py:845-852`: removed obsolete `TODO(parser-bindings-name-collision)` docstring from `_gen_python_bindings` — collision now impossible after module split.
- `TODO.md`: removed `parser-bindings-name-collision` entry; added `rust-generated-ident-collisions` entry (pairwise cross-rule Rust-ident collisions, pre-existing, deferred, requires cross-rule analysis).
- `fltk/plumbing.py`: updated docstrings for `_load_rust_cst_classes`, `generate_parser` (`rust_cst_module`), and `parse_grammar` (`rust_fegen_cst_module`) — all now say callers pass the cst submodule path (e.g. `"fegen_rust_cst.cst"`) not the top-level module name.
- `Makefile:111-114`: updated `build-fegen-rust-cst` comment to show example submodule path.
- `fltk/fegen/gsm2tree_rs.py:155-161`: updated `generate_pyi` docstring to describe stub-package layout (`<name>/cst.pyi`); removed stale "Safety note" inline comment from pyi generator body.
- `fltk/fegen/genparser.py:281-316`: updated `--pyi-output` help text and `gen-rust-cst` docstring — describe stub-package convention, Span import location, and module wiring pattern.
- `tests/test_module_split.py`: new file with 35 tests covering §4.3 (collision fixture headline: `collision_cst.Parser` is CST class, `collision_parser.Parser` is parser machinery, they are distinct types), §4.4 (import mechanics: attribute, from-import, importlib.import_module, sys.modules for fegen_rust_cst.cst and .parser), §4.5 (Span/SourceText absent from fegen_rust_cst and rust_parser_fixture top-level and submodules; present in rust_cst_fixture and fltk._native), §4.6 (fltk._native.poc_cst reachable; Identifier/Items absent from fltk._native top level). All 1393 pytest tests pass; pre-commit clean.

---

## Increment 8 — _RESERVED_CLASS_NAMES check in RustCstGenerator + tests (§2.6) (commit 14052e9)

- `fltk/fegen/gsm2tree_rs.py:27-41`: added `_RESERVED_CLASS_NAMES` dict (`NodeKind`, `Span`, `Shared`, `CstError`) with inline `TODO(rust-generated-ident-collisions)` comment for the pairwise cross-rule case deferred by design.
- `fltk/fegen/gsm2tree_rs.py:73-82`: added class-name check in `RustCstGenerator.__init__` (after `self._py_gen` is set) using `class_name_for_rule_node`; raises `ValueError` naming rule, derived class name, and collision target.
- `tests/test_gsm2tree_rs.py`: added `_make_single_rule_grammar` helper and `TestReservedClassNameRejection` class — 4 parametrized rejection tests (`node_kind`/`span`/`shared`/`cst_error`), `source_text` acceptance test, and `parser`/`apply_result` acceptance tests (2 parametrized). 7 new tests; all pass (139 total).

---

## Increment 7 — wire tests/rust_parser_fixture/src/lib.rs with cst + parser + collision submodules; add collision_fixture.fltkg + generated Rust sources; update Makefile and dependent tests (§2.3, §2.9) (commit 6891869)

- `fltk/fegen/test_data/collision_fixture.fltkg`: new grammar with rules `parser`, `apply_result`, `root`, `name`, `item` — proves Parser/ApplyResult CST classes and parser machinery coexist after the split.
- `tests/rust_parser_fixture/src/collision_cst.rs`: generated via `gen-rust-cst` from collision_fixture.fltkg; `NodeKind` enum contains `PARSER`/`APPLYRESULT` variants; CST classes `Parser` and `ApplyResult` present.
- `tests/rust_parser_fixture/src/collision_parser.rs`: generated via `gen-rust-parser --cst-mod-path super::collision_cst`; imports `super::collision_cst as cst`.
- `tests/rust_parser_fixture/src/lib.rs`: replaced flat `cst::register_classes(m)` + `parser::register_classes(m)` + Span/SourceText top-level registrations with four `register_submodule` calls (`cst`, `parser`, `collision_cst`, `collision_parser`); added `pub mod collision_cst` / `pub mod collision_parser`; dropped `SourceText`/`Span` use imports.
- `Makefile`: added two regen targets after existing rust_parser_fixture targets — `collision_cst.rs` via `gen-rust-cst` and `collision_parser.rs` via `gen-rust-parser --cst-mod-path super::collision_cst`.
- `tests/test_rust_parser_parity_fixture.py:50`: `rust_parser_fixture.Parser` → `rust_parser_fixture.parser.Parser`.
- `tests/test_rust_parser_fixture_bindings.py`: all `rust_parser_fixture.Parser(` → `rust_parser_fixture.parser.Parser(` (8 occurrences including `_default_max_depth` helper).
- All 1351 pytest tests pass; cargo clippy + cargo test (fixture crate, python and no-python features) pass.

---

## Increment 6 — wire src/lib.rs (fltk._native) with poc_cst submodule; update test_rust_cst_poc.py (§2.5) (commit 2c10c05)

- `src/lib.rs`: replaced hand-rolled `fegen_cst` submodule wiring and top-level `cst_generated::register_classes(m)` with two `register_submodule` calls — `poc_cst` for PoC grammar classes and `fegen_cst` for fegen grammar classes; removed now-unused `pyo3::sync::GILOnceCell` import for fegen_cst; added `use fltk_cst_core::register_submodule`.
- `tests/test_rust_cst_poc.py:7-8`: split `from fltk._native import Identifier, Items, SourceText, Span, UnknownSpan` into two imports; `Identifier`/`Items` now from `fltk._native.poc_cst`.
- `fltk/_native/__init__.pyi`: updated header comment — PoC classes now described as being in `fltk._native.poc_cst` submodule (not top-level).
- All 1351 pytest tests pass.

---

## Increment 5 — wire tests/rust_cst_fegen/src/lib.rs with cst + parser submodules; drop Span/SourceText; update dependent tests (§2.3, §2.4) (commit d03cf02)

- `tests/rust_cst_fegen/src/lib.rs`: replaced flat registration with `register_submodule(m, "cst", cst::register_classes)` and `register_submodule(m, "parser", parser::register_classes)`; dropped `Span`/`SourceText` registrations and their `use` imports; updated module comment.
- `tests/test_rust_parser_bindings.py`: all `fegen_rust_cst.Parser(...)` → `fegen_rust_cst.parser.Parser(...)`; `fegen_rust_cst.Rule` → `fegen_rust_cst.cst.Rule`; added `fegen_rust_cst_cst` and `fegen_rust_cst_parser` aliases for concision.
- `tests/test_rust_parser_parity_fegen.py`: `fegen_rust_cst.Parser` → `fegen_rust_cst.parser.Parser` in `_rust_parser` factory.
- `tests/test_phase4_fegen_rust_backend.py`: node classes (`Identifier`, `Literal`, `RawString`, `Items`, `Grammar`) → `fegen_rust_cst.cst.*`; `fegen_rust_cst.Parser` → `fegen_rust_cst.parser.Parser`; `_EXPECTED_CLASSES` assertion against `fegen_rust_cst.cst`; all `rust_fegen_cst_module="fegen_rust_cst"` → `"fegen_rust_cst.cst"`.
- `tests/test_cross_backend_label_equality.py`: `_BACKENDS["ext"]` → `fegen_rust_cst.cst`; direct `fegen_rust_cst.Items` → `fegen_rust_cst.cst.Items`.
- `tests/test_clean_protocol_consumer_api.py`: `fegen_rust_cst.NodeKind` → `fegen_rust_cst.cst.NodeKind`; `fegen_rust_cst.Items` → `fegen_rust_cst.cst.Items`; `rust_fegen_cst_module="fegen_rust_cst"` → `"fegen_rust_cst.cst"`.
- `crates/fltk-cst-core/src/py_module.rs`: gated `user_facing_name` with `#[cfg(any(feature = "python", test))]` to fix no-default-features clippy dead-code warning.
- All 1351 pytest tests pass; all cargo checks pass.

---

## Increment 2 — wire tests/rust_cst_fixture/src/lib.rs with cst submodule; keep top-level Span/SourceText; fix register_submodule sys.modules key derivation (§2.2, §2.4)

- `crates/fltk-cst-core/src/py_module.rs`: redesigned `register_submodule` signature: removed `parent_qualified_name` parameter (design's assumption that `parent.name()` returns unqualified leaf was wrong — it returns the fully-qualified name). Added `user_facing_name()` helper that strips maturin's double-nested pattern (e.g. `"fegen_rust_cst.fegen_rust_cst"` → `"fegen_rust_cst"`) so sys.modules keys use the clean package name. 4 new unit tests (not python-feature-gated).
- `crates/fltk-cst-core/src/lib.rs`: `mod py_module` no longer gated by `#[cfg(feature = "python")]` (needed so unit tests for `user_facing_name` compile without the python feature).
- `tests/rust_cst_fixture/src/lib.rs:16-20`: converted to `register_submodule(m, "cst", cst::register_classes)`; kept top-level `Span`/`SourceText` registrations per §2.4; corrected wrong comment about registration being "needed for span extraction" (it is needed so Python can construct foreign-cdylib instances).
- `tests/test_rust_span.py:455,486,524,564,604`: subprocess scripts updated from `cst.Config(...)` → `cst.cst.Config(...)` (CST classes now in `cst` submodule).
- `tests/test_rust_span.py:636,647`: inline test code updated `phase4.Config` → `phase4.cst.Config`.
- `tests/test_phase4_rust_fixture.py:54`: `rust_cst_module="phase4_roundtrip_cst"` → `"phase4_roundtrip_cst.cst"`.
- All 1351 pytest tests pass; `cargo test -p fltk-cst-core --no-default-features`: 28/28 pass (4 new).
- Deviation: design §2.2 specified a `parent_qualified_name: &str` parameter and a last-segment sanity check. Dropped entirely: `parent.name()` returns the fully-qualified name at `#[pymodule]` init time (contrary to design's assumption), making the explicit parameter unnecessary and the segment check incorrect. The `user_facing_name()` helper abstracts the maturin double-nesting case.

---

## Increment 1 — register_submodule helper in fltk-cst-core (§2.2) (commit b62f721)

- `crates/fltk-cst-core/src/py_module.rs`: new file; `register_submodule` function, `#[cfg(feature = "python")]`-gated. Sanity-checks last segment of `parent_qualified_name` against `parent.name()?` (PyValueError on mismatch), creates submodule, runs register closure, calls `add_submodule`, inserts into `sys.modules` under `"{parent_qualified_name}.{name}"`, returns the submodule.
- `crates/fltk-cst-core/src/lib.rs:4-5,13`: added `mod py_module` (python-gated) and `pub use py_module::register_submodule` (python-gated).
- `cargo test --no-default-features` (GIL-free Rust tests): 24/24 pass. `cargo build -p fltk-cst-core`: clean. All pre-commit hooks pass.
