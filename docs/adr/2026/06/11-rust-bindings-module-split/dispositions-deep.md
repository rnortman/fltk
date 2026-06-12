Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 4fe645d. Respond commit: d8233c6.

---

errhandling-1:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/py_module.rs:77-84` — wrapped `parent.name()?` with `map_err` producing `PyRuntimeError` naming the submodule and the underlying error.
- Severity assessment: Build-time deterministic failure; impact was diagnostic difficulty only (no silent data corruption). Error message now identifies which submodule registration was in progress.

errhandling-2:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/py_module.rs:87-97` — wrapped `register(&sub)` and `parent.add_submodule(&sub)` failures with `map_err` producing `PyRuntimeError` naming the qualified submodule path. `qualified_name` construction moved to before these calls so it is available for the error messages.
- Severity assessment: Same build-time deterministic failure class as errhandling-1; diagnostic messages now include submodule identity.

errhandling-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer correctly classified this as a correctly-handled invariant violation (double-init panic); not a finding. Included for completeness.
- Rationale (Won't-Do): Reviewer's own assessment: "Not a finding — correctly handled invariant violation." Panic is the correct response to an invariant violation; the message is accurate.

errhandling-4:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Reviewer correctly found no bug: `"Trivia"` is not in `_RESERVED_CLASS_NAMES` and the latent fragility requires a future expansion of the reserved set that adds `"Trivia"`, which would be obviously wrong and caught immediately.
- Rationale (Won't-Do): Reviewer's own assessment: "No finding." Current reserved set is correct; latent fragility is theoretical.

errhandling-5:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: `from exc` chaining preserves the original `ImportError` in `__cause__`; adequate for interactive debugging. `detail=None` in structured logging is a cosmetic gap.
- Rationale (Won't-Do): Reviewer's own assessment: "Not a finding; the propagation is correct."

errhandling-6:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Correctly handled — top-level module passed by mistake yields clear `RustBackendUnavailableError` with diagnostic detail string.
- Rationale (Won't-Do): Reviewer's own assessment: "Correctly handled. Not a finding."

correctness-1:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/py_module.rs` — added `register_submodule_with_parent_name` public function and private `register_submodule_impl` helper; `register_submodule` now delegates to the impl. `crates/fltk-cst-core/src/lib.rs:13` — re-exports `register_submodule_with_parent_name`. Removed the `TODO(register-submodule-non-maturin)` comment from `user_facing_name` doc (replaced with a cross-reference to `register_submodule_with_parent_name`). Removed `register-submodule-non-maturin` entry from `TODO.md`. Updated `triple_nested_double_match` unit test comment to document the known false-positive and point to the escape hatch.
- Severity assessment: Without the fix, out-of-tree consumers placing an extension at `a.b.b` (non-maturin layout) got the wrong `sys.modules` key `a.b.cst` instead of `a.b.b.cst`, causing `ModuleNotFoundError` for `importlib.import_module("a.b.b.cst")`. All in-tree builds use maturin and are unaffected. The new `register_submodule_with_parent_name` variant bypasses the heuristic entirely by accepting the correct parent name explicitly; existing callers are unchanged.

correctness-2:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/py_module.rs:100` — added `sub.setattr("__name__", &qualified_name)?` after `parent.add_submodule(&sub)` and before `sys.modules` insertion, so the submodule's `__name__` matches the `sys.modules` key.
- Severity assessment: Without this fix, `importlib.reload(mod)` resolves `sys.modules[mod.__name__]` to `"cst"` (not found or wrong module), and any `importlib.import_module(mod.__name__)` round-trip is broken. Pre-existing for `fltk._native.fegen_cst` under the old open-coded path, but the helper generalizes the defect to all consumer crates' submodules. Now fixed uniformly.

test-1:
- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:1298-1318` — `test_parser_apply_result_rules_accepted` now calls `gen.generate()` and asserts `'name = "Parser"'` / `'name = "ApplyResult"'` appear in the generated cst source; added `test_source_text_rule_cst_class_name_in_source` positive case asserting `'name = "SourceText"'` appears. `fltk/fegen/test_gsm2parser_rs.py:1151-1182` — new `test_parser_apply_result_grammar_rules_coexist_with_fixed_pyclass_names` asserting the parser source contains both fixed machinery pyclass names when grammar rules use those rule names.
- Severity assessment: Design §4 test plan item 2 specified source-level content checks; the original test only checked no exception was raised, missing silent rename/drop regressions in either generated artifact.

test-2:
- Disposition: Fixed
- Action: `tests/test_module_split.py:279-295` — added `test_sys_modules_poc_cst` and `test_sys_modules_fegen_cst` asserting `sys.modules["fltk._native.poc_cst"]` and `sys.modules["fltk._native.fegen_cst"]` are set and point to the correct objects. (The `fegen_cst` test mirrors the `fegen_rust_cst` coverage in `TestImportMechanics`.)
- Severity assessment: `import fltk._native.poc_cst` succeeds via attribute traversal even without a `sys.modules` entry; the original tests did not exercise the `register_submodule` helper's key-insertion behavior for `fltk._native` submodules.

test-3:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/py_module.rs` — added `assert_eq!(user_facing_name("fltk._native.sub"), "fltk._native.sub")` and `assert_eq!(user_facing_name("a.b.c"), "a.b.c")` to the `different_segments_unchanged` unit test, covering three-distinct-segment paths.
- Severity assessment: Latent coverage gap: three-distinct-segment behavior was untested; a regression in `user_facing_name` for such paths would go undetected until out-of-tree consumers report wrong `sys.modules` keys.

test-4:
- Disposition: Fixed
- Action: `tests/test_module_split.py:121-123` — replaced `if parser_child is not None:` guard with unconditional `assert parser_child is not None, "..."` before the `isinstance` check.
- Severity assessment: The original test could pass vacuously if `maybe_p()` returned `None`; input `"foo"` should reliably match the `parser` alternative, so the unconditional assertion correctly documents and enforces that expectation.

test-5:
- Disposition: Fixed
- Action: `tests/test_module_split.py:293-295` — added `test_poc_cst_has_node_kind` asserting `fltk._native.poc_cst.NodeKind` is present.
- Severity assessment: A registration defect dropping `NodeKind` from `poc_cst` (or misplacing it at the top level) would be missed by the previous test suite.

quality-1:
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py:305-315` — added the canonical `lib.rs` wiring snippet (showing `register_submodule` calls for `cst` and `parser` submodules) to the `gen-rust-cst` command docstring, immediately after the submodule placement sentence. Matches the snippet in design §2.3.
- Severity assessment: Design §2.3 explicitly required the pattern be "documented in genparser.py help text"; without it, out-of-tree consumers reading `--help` learned that output goes into a `cst` submodule but had no guidance on how to wire it via `register_submodule`.
