# Correctness review: rust-bindings-module-split

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: `3157b59..4fe645d`. Deep pass: diff + surrounding code, empirical runtime verification against the built extensions (confirmed fresh: `.so` symbol/string contents match the new `register_submodule` code, build timestamps precede commit by minutes).

Verified clean (not findings):

- `parent.name()` at `#[pymodule]` init time really is the fully qualified spec name (CPython single-phase init copies `_Py_PackageContext` into `__name__` inside `PyModule_Create`). The design doc's §2.2 claim that it is unqualified is wrong; the implementation is right. Empirically confirmed: `sys.modules` keys `fltk._native.poc_cst`, `fltk._native.fegen_cst`, `fegen_rust_cst.cst/.parser`, `rust_parser_fixture.{cst,parser,collision_cst,collision_parser}`, `phase4_roundtrip_cst.cst` all correct.
- Cold-process imports work without prior parent import: `import fegen_rust_cst.cst`, `from fltk._native.poc_cst import Identifier`, `importlib.import_module("rust_parser_fixture.collision_parser")`.
- Ordering in `register_submodule` (`register` → `add_submodule` → `sys.modules` insert) leaves no dangling `sys.modules` entry for the failing submodule; partial-init residue for *earlier* submodules is design-accepted (§3) and documented.
- `_RESERVED_CLASS_NAMES` check (`gsm2tree_rs.py:79-83`) fires for `node_kind`/`span`/`shared`/`cst_error`, passes `source_text`/`parser`/`apply_result`; single chokepoint holds (`RustParserGenerator` constructs `RustCstGenerator`).
- `plumbing.py` needs no code change: `_load_rust_cst_classes("…​.cst")` scrape returns only NodeKind + node classes + label enums; the prior silent clobber of `parser_globals["ApplyResult"]`/`["Span"]` by Rust types is gone, as the design claims.
- Mechanical test import-path updates (incl. the five ABI-gate subprocess scripts in `test_rust_span.py`) are consistent; `phase4.Span`/`phase4.SourceText` top-level references correctly retained per §2.4.
- Test runs: `tests/test_module_split.py` + 5 related suites, 360 passed; `cargo test -p fltk-cst-core --no-default-features --lib`, 28 passed (the with-python `cargo test` link failure is environmental: no `libpython3.10` for the test binary linker).
- pyright errors on `fltk._native.poc_cst` / `fegen_rust_cst.cst` imports exist in `tests/` but `tests/` is outside the pyright gate (`pyproject.toml` include = `["fltk", "*.py"]`); not a gate regression.
- No in-tree embedded/inittab init of these pymodules; the inittab caveat (no `_Py_PackageContext` → unqualified name) is moot for top-level module names anyway.

## correctness-1: `user_facing_name` strips legitimately doubled module paths, producing wrong `sys.modules` keys

- File: `crates/fltk-cst-core/src/py_module.rs:17-36` (used at `py_module.rs:80-81`).
- What's wrong: the maturin double-nesting detection is purely lexical — *any* parent whose last two dotted segments are equal is stripped. The maturin re-export layout and a plain extension module that genuinely lives at `a.b.b` (e.g. `b.abi3.so` placed inside a regular package `b` without a re-exporting `__init__.py`, as non-maturin build systems can produce — this repo itself documents Bazel as an alternative build path) are lexically indistinguishable; the helper silently assumes maturin.
- Why: `user_facing_name("a.b.b")` returns `"a.b"` unconditionally (unit test `triple_nested_double_match` enshrines this), so `register_submodule` inserts `sys.modules["a.b.cst"]` instead of `sys.modules["a.b.b.cst"]`.
- Consequence: for an out-of-tree consumer with such a layout, (a) `import a.b.b.cst` / `importlib.import_module("a.b.b.cst")` raises `ModuleNotFoundError`, so `plumbing.generate_parser(rust_cst_module="a.b.b.cst")` raises `RustBackendUnavailableError` even though the extension loaded fine; (b) the bogus key `a.b.cst` shadows or pre-empts a genuine module `a.b.cst` if package `a.b` has one — a later `import a.b.cst` silently returns the extension's submodule instead of the real file. CLAUDE.md: absence of an in-tree consumer is not evidence of safety; consumers are out-of-tree. The design's original API (explicit `parent_qualified_name` parameter, §2.2) had no such ambiguity; the doc comment documents only the intended pattern, not the false-positive direction.
- Suggested fix: keep the heuristic as the zero-config default but add an escape hatch — a `register_submodule_with_parent_name(parent, parent_qualified_name, name, register)` variant (or an `Option<&str>` override) that bypasses `user_facing_name`; document the lexical ambiguity in the helper's doc comment.

## correctness-2: registered submodule's `__name__` stays leaf-only, violating the `sys.modules[k].__name__ == k` invariant

- File: `crates/fltk-cst-core/src/py_module.rs:86-101`.
- What's wrong: `PyModule::new(py, name)` creates the submodule with `__name__ = "cst"` and nothing later upgrades it, while the `sys.modules` key is `"fegen_rust_cst.cst"`. Observed: `repr(fegen_rust_cst.cst)` is `<module 'cst'>`; `sys.modules["fegen_rust_cst.cst"].__name__ == "cst"`.
- Why: CPython's import system maintains `sys.modules[k].__name__ == k` for every module it creates; code legitimately relies on it. `importlib.reload(fegen_rust_cst.cst)` looks up `sys.modules[module.__name__]` → `"cst"` → `ImportError: module cst not in sys.modules`, or — worse — if any unrelated module named `cst` is importable/loaded, reload targets the wrong module. `inspect.getmodule`-style reverse lookups and any `importlib.import_module(mod.__name__)` round-trip likewise resolve to top-level `"cst"`, not the real module.
- Consequence: introspection/reload tooling run by downstream consumers misbehaves on every generated extension's submodules (the helper is the documented pattern for all consumer crates). Pre-existing for `fltk._native.fegen_cst` under the old open-coded version (same leaf-named `PyModule::new`), so not a regression — but the helper now generalizes the defect to the whole public consumer surface.
- Suggested fix: after `parent.add_submodule(&sub)` (must be after — pyo3's `add_submodule` derives the attribute name from the module's current name), set `sub.setattr("__name__", &qualified_name)?` before the `sys.modules` insert.
