## quality-1

**File:line:** `fltk/fegen/genparser.py:26-55` vs `fltk/fegen/genparser.py:219-251`

**Issue:** `parse_grammar_file` and `_parse_grammar_raw` are near-duplicates. Both open the file, build a `TerminalSource`, run `fltk_parser.Parser.apply__parse_grammar`, format error messages identically, and call `Cst2Gsm`. The only difference is that `parse_grammar_file` calls `add_trivia_rule_to_grammar` / `classify_trivia_rules` and `_parse_grammar_raw` does not. The shared work (file I/O, parsing, error formatting, `Cst2Gsm.visit_grammar`) is copy-pasted verbatim.

**Consequence:** Any future change to error formatting, parser invocation, or file-read handling must be made in two places. The pattern will propagate if more grammar-file consumers are added (e.g. a `gen-python-cst` subcommand), and the two copies are already diverged in their error message phrasing (`"Failed to parse grammar file"` vs the same).

**Fix:** Extract the shared file-read-and-parse step into a private helper (e.g. `_parse_grammar_file_to_cst(path) -> tuple[str, TerminalSource, CstNode]` or directly to `gsm.Grammar`). `parse_grammar_file` calls it then applies trivia rules; `_parse_grammar_raw` calls it without the trivia step. Alternatively, `_parse_grammar_raw` can simply call `plumbing.parse_grammar` (which already exists) and skip the trivia step, since `plumbing.parse_grammar` already centralizes the same logic with no trivia applied.

---

## quality-2

**File:line:** `fltk/plumbing.py:207-223`

**Issue:** `sys.modules[module_name] = cst_module` (line 223) is executed before the parser `exec` succeeds. If `compiler.compile_class`, `ast.fix_missing_locations`, or the parser `exec` raises — or if no `Parser`-named class is found and the function raises `RuntimeError` at line 249 — the partially-constructed `cst_module` remains registered in `sys.modules` under `fltk_grammar_<id>`. A subsequent call with the same grammar object (same `id`) would retrieve the stale module.

**Consequence:** A grammar object that fails parser generation leaves a poisoned entry in the global module registry. Any code that later imports or introspects `sys.modules` could observe the broken module. The stale entry can also cause `test_rust_backend_missing_module_hard_errors` to give a false pass on subsequent test-order permutations if the grammar id is reused.

**Fix:** Move `sys.modules[module_name] = cst_module` to after the parser class is confirmed (after line 246), or wrap lines 225-250 in a try/except that calls `sys.modules.pop(module_name, None)` on failure.

---

## quality-3

**File:line:** `fltk/fegen/gsm2tree_rs.py` (`_preamble`) and all generated / committed `.rs` files (`src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`)

**Issue:** Each generated `.rs` file declares its own module-level `static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject>`, and every struct's `#[new]` method duplicates the same `get_or_try_init` body (`py.import("fltk._native")?.getattr("UnknownSpan")?.unbind()`). Within a single compiled extension (one `.so`) that contains many node types, this is harmless because `GILOnceCell` ensures the init closure runs only once per cache. But the closure body — a raw string of import code — is copy-pasted into every `#[new]` method (14 times in `cst_fegen.rs`). The generator in `gsm2tree_rs.py` emits this closure inline in `_new_method` for every class with no abstraction.

**Consequence:** If `fltk._native` is renamed or `UnknownSpan` moves, every emitted `.rs` file must be regenerated. The raw attribute path `"fltk._native"` / `"UnknownSpan"` is a stringly-typed contract with no central definition. Additionally, `src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` are identical files (verified by `diff`: zero output) committed independently. When `src/cst_fegen.rs` is updated by hand or by the generator, `tests/rust_cst_fegen/src/cst.rs` must be separately regenerated and committed; the two copies will silently diverge.

**Fix (stringly-typed):** Define constants for `"fltk._native"` and `"UnknownSpan"` in the generator (`gsm2tree_rs.py`) and use them in the emitted closure. Consider emitting a file-level `fn get_unknown_span(py: Python<'_>) -> PyResult<PyObject>` helper and calling it from each `#[new]`, reducing the inline duplication.

**Fix (duplicate committed file):** Remove `tests/rust_cst_fegen/src/cst.rs` from the repo and generate it from `src/cst_fegen.rs` at build time (symlink, copy step, or `include!` macro), making the single source of truth explicit.
