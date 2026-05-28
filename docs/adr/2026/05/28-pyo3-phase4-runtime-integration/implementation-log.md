# Phase 4 Runtime Integration: Implementation Log

## Increment 8 — user-facing "Build a Rust CST extension" guide (commit TBD)

- `docs/rust-cst-extension-guide.md`: 4-step guide: (1) emit `.rs` via `gen-rust-cst`, (2) write the thin `cdylib` crate with `#[pymodule]` calling `register_classes`, including `Cargo.toml` and `lib.rs` templates, (3) build/install with user's tool, (4) pass module name to `generate_parser`. Documents the `fltk._native` runtime dependency, no-grammar-consistency-check limitation, no-ABI-pinning limitation, and points to `tests/rust_cst_fixture/` and `tests/rust_cst_fegen/` as working examples.

## Increment 2 — `gsm2tree_rs.py` standalone sentinel change (commit 641a8dc)

- `fltk/fegen/gsm2tree_rs.py:120-140`: `_preamble()` drops `use crate::UNKNOWN_SPAN;`, adds `use pyo3::sync::GILOnceCell;`, emits `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();` with a `TODO(rust-cst-shared-rlib)` comment.
- `fltk/fegen/gsm2tree_rs.py:225-244`: `_new_method()` replaces `UNKNOWN_SPAN.get(py).expect(...)` with `UNKNOWN_SPAN_CACHE.get_or_try_init(py, || Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind()))?`.
- `src/cst_generated.rs`, `src/cst_fegen.rs`: regenerated under new sentinel scheme; `use crate::UNKNOWN_SPAN;` removed, `UNKNOWN_SPAN_CACHE` used instead. Both still compile inside `fltk._native` crate (crate's own `UNKNOWN_SPAN` static unused by generated files now, but harmless).
- `tests/test_gsm2tree_rs.py`: updated 4 existing tests to assert `use crate::UNKNOWN_SPAN;` absent and `GILOnceCell`/`UNKNOWN_SPAN_CACHE` present; added `test_no_crate_unknown_span_import`, `test_sentinel_cache_declared`, `test_sentinel_fetches_fltk_native_at_runtime` to `TestPreamble`; updated `TestFegenGrammar` and `TestMinimalGrammar` preamble assertions. 695 tests pass.
- `TODO.md`: added `rust-cst-shared-rlib` and `rust-cst-abi-pinning` entries (design Open Questions §TODO).
- Deviation: `test_gen_rust_cst_no_double_trivia` deferred to `genparser.py` increment (depends on `_parse_grammar_raw` not yet implemented).

## Increment 3 — `genparser.py` `gen-rust-cst` subcommand (commit 44e12ec)

- `fltk/fegen/genparser.py:13`: added `gsm2tree_rs` import.
- `fltk/fegen/genparser.py:219-251`: `_parse_grammar_raw(grammar_file)` — parses a `.fltkg` file via the Python path but does NOT apply `add_trivia_rule_to_grammar` or `classify_trivia_rules`. Returns the raw `gsm.Grammar`. This is the correct input for `RustCstGenerator`, which applies trivia processing internally; feeding a pre-processed grammar would double-apply (idempotent but the contract is explicit).
- `fltk/fegen/genparser.py:254-275`: `@app.command(name="gen-rust-cst")` — Typer subcommand that calls `_parse_grammar_raw`, passes the raw grammar to `RustCstGenerator(grammar).generate()`, and writes the `.rs` source to the output file.
- `fltk/fegen/test_genparser.py`: 3 new Tier 1 tests — `test_gen_rust_cst_command_emits_source` (CLI invocation via `typer.testing.CliRunner`, asserts `pub fn register_classes`, class name, no `use crate::UNKNOWN_SPAN;`), `test_gen_rust_cst_sentinel_decoupled` (asserts `UNKNOWN_SPAN_CACHE` declaration and `fltk._native` runtime fetch present, old crate patterns absent), `test_gen_rust_cst_no_double_trivia` (calls `_parse_grammar_raw` directly on a no-trivia grammar, asserts `_trivia` not in result identifiers). 698 tests pass.
- Note: crashed increment recovered — `genparser.py` edits were complete and sound; only the test file and log finalization were missing.

## Increment 4 — `plumbing.py` Rust backend path for `generate_parser` (commit b86c34f)

- `fltk/plumbing.py:34-43`: `RustBackendUnavailableError` — RuntimeError subclass, stores `module_name`, formats message with optional detail.
- `fltk/plumbing.py:46-72`: `_load_rust_cst_classes(module_name)` — imports via `importlib.import_module`, wraps `ImportError` → `RustBackendUnavailableError`, filters to `isinstance(obj, type)` public names; returns `dict[str, object]`.
- `fltk/plumbing.py:127-190`: `generate_parser` gains `rust_cst_module: str | None = None`; Python backend path refactored to produce `public` dict (same semantics); Rust backend calls `_load_rust_cst_classes` and uses `public` for `cst_module` population and `parser_globals.update`. `sys.modules[module_name]` registration only after both backends succeed — AC4 invariant holds.
- `fltk/test_plumbing.py`: added `TestRustBackendUnavailableError` (3 tests), `TestLoadRustCstClasses` (4 tests), `TestGenerateParserRustBackend` (5 tests), `TestNoRuntimeCompilation` (1 test). All 711 tests pass.

## Increment 5 — `parse_grammar` Rust backend path (commit 3aebf22)

- `fltk/plumbing.py:34-51`: `_fegen_grammar_cache: list[gsm.Grammar]` + `_load_fegen_grammar()` — parses `fegen/fegen.fltkg` via the Python path, caches result in a module-scope list (avoiding PLW0603). Call is lazy; no recursion because the Python path in `parse_grammar` does not call `_load_fegen_grammar`.
- `fltk/plumbing.py:91-155`: `parse_grammar` gains `rust_fegen_cst_module: str | None = None`. Python path (default) is byte-for-byte unchanged. Rust path: calls `_load_fegen_grammar()`, then `generate_parser(fegen_grammar, rust_cst_module=rust_fegen_cst_module)`, builds the parser, runs it, and constructs `Cst2Gsm(terminals.terminals, cst=pr.cst_module)` — same backend's classes for construction and injection, so `isinstance` dispatch in `Cst2Gsm` resolves.
- `fltk/plumbing.py:158-183`: `parse_grammar_file` gains matching `rust_fegen_cst_module` parameter, threads it to `parse_grammar`.
- `fltk/test_plumbing.py`: `TestParseGrammarRustBackend` — 4 new Tier 1 tests: Python-default unchanged, missing-module hard-error (`parse_grammar`), no-fallback assertion, missing-module hard-error (`parse_grammar_file`). 715 tests pass.

## Increment 6 — standalone non-FLTK user-extension fixture crate (commit b1785a0)

- `fltk/fegen/test_data/phase4_roundtrip.fltkg`: fixture grammar — config/entry/operator/identifier/literal with labeled children, zero-or-more repetition, and a 3-variant Operator label enum (assign/append/remove). Satisfies AC5 multi-variant label requirement.
- `tests/rust_cst_fixture/src/cst.rs`: generated Rust CST source (6 node classes + their label enums + `register_classes`) via `uv run python -m fltk.fegen.genparser gen-rust-cst`. Contains `GILOnceCell` sentinel, no `crate::` coupling.
- `tests/rust_cst_fixture/Cargo.toml` + `src/lib.rs`: standalone `cdylib` crate whose `#[pymodule]` init calls `cst::register_classes`. Independent of `fltk._native` at link time. Imports as `phase4_roundtrip_cst`. Builds via `make build-test-user-ext` (`cd tests/rust_cst_fixture && maturin develop`).
- `tests/test_phase4_rust_fixture.py`: 38 Tier-2 tests guarded by `pytest.importorskip`. Covers: AC2 (cst_module registered, exposes all rule classes), AC3 (parse→CST→unparse→render roundtrip for assign/append/string-literal/multi-entry), AC5 (all 12 API-Contract items against Rust nodes), AC7 (both-backend parametrized sweep for construction, label equality/hash, isinstance, children list protocol, full roundtrip).
- `Makefile`: added `build-native`, `build-test-user-ext`, `gen-rust-cst` targets (FLTK-internal only; documented as such).
- Deviation: AC Contract item 3 ("span read: node.span.start, node.span.end") — Rust `fltk._native.Span` intentionally does NOT expose `.start`/`.end` as Python attributes (they are `pub(crate)` Rust fields; `test_rust_span.py` documents this). The test verifies span readability and equality instead, which is what `fltk2gsm.py` actually requires. This is an existing design constraint, not a new gap.
- 753 tests pass (38 new).

## Increment 7 — fegen Rust CST fixture crate + AC8 test (commit 66745be)

- `tests/rust_cst_fegen/Cargo.toml` + `src/lib.rs`: standalone `cdylib` crate; `#[pymodule]` init calls `cst::register_classes`. Imports as `fegen_rust_cst`. Independent of `fltk._native` at link time.
- `tests/rust_cst_fegen/src/cst.rs`: generated from `fegen.fltkg` via `gen-rust-cst`. 14 node classes + label enums + `register_classes`. No `crate::` coupling; uses `UNKNOWN_SPAN_CACHE` sentinel.
- `Makefile`: added `build-fegen-rust-cst` target (`cd tests/rust_cst_fegen && uv run --group dev maturin develop`) and `.PHONY` entry.
- `fltk/fegen/fltk2gsm.py:31-70`: `visit_items` — filter out `None`-labeled children (Trivia nodes) before stride indexing. The Rust-backed fegen parser (generated with trivia capture) inserts `(None, Trivia(...))` entries between Items children; the committed Python `fltk_parser` does not. The fix is backward-compatible: the Python backend produces no `None`-labeled Items children.
- `tests/test_phase4_fegen_rust_backend.py`: 21 Tier-2 tests guarded by `pytest.importorskip`. Covers: AC8 (simple grammar, multi-rule grammar, `fegen.fltkg` itself, `parse_grammar_file`, injection-seam monkeypatch verifying non-default `cst=` arg), AC6 partial (14 expected classes exposed, module distinct from `fltk._native.fegen_cst`), DI-seam construction test.
- 774 tests pass (21 new).
- Deviation: `fltk2gsm.visit_items` required a bug fix (Trivia-filter) not anticipated by design. The Rust-backed fegen parser captures Trivia into Items children; the design assumed `Cst2Gsm` was already compatible. The fix is a 2-line filter at `fltk2gsm.py:37` (`labeled_children = [(l, v) for l, v in items.children if l is not None]`) and is strictly additive — no semantic change for the Python backend.

## Increment 1 — `fltk2gsm.Cst2Gsm` DI refactor (commit 932fe28)

- `fltk/fegen/fltk2gsm.py:1-12`: replaced `from fltk.fegen import fltk_cst as cst` with `from fltk.fegen import fltk_cst as _default_cst`; added `from types import ModuleType`.
- `fltk2gsm.py:10-12`: `Cst2Gsm.__init__` gains `cst: ModuleType = _default_cst` parameter; stores as `self.cst`.
- `fltk2gsm.py:14-132`: all method signatures updated (type annotations removed for bare CST types); all `cst.Items.Label.*`, `cst.Disposition.Label.*`, `cst.Quantifier.Label.*`, and `isinstance(item, cst.Item)` references changed to `self.cst.*`.
- 692 existing tests pass; no callers modified (default behavior unchanged).
