# Dispositions — Deep Review Round 1

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

errhandling-1:
- Disposition: Fixed
- Action: Wrapped `fegen_fltkg.open()` in `try/except FileNotFoundError` in `_load_fegen_grammar`; re-raises as `RuntimeError` with an actionable message naming the internal path and directing the user to reinstall fltk. `fltk/plumbing.py:47-57`.
- Severity assessment: A corrupted or mis-packaged install surfaces as a bare `FileNotFoundError` with an internal path, giving no diagnosis hint to the user or operator.

errhandling-2:
- Disposition: Fixed
- Action: Changed `except RuntimeError` to `except OSError` in `genparser.py` `generate` command's shared CST file write block. `fltk/fegen/genparser.py:174`. Pre-existing bug in diff-touched code; `open()`/`write()` raises `OSError`, never `RuntimeError`.
- Severity assessment: A permission error or missing output directory on the `gen-rust-cst` path crashes with a raw Python traceback instead of the intended "Error: Failed to write…" CLI message.

correctness-1:
- Disposition: Fixed
- Action: Added a comment block to `src/lib.rs:10` explaining that `crate::UNKNOWN_SPAN` is set at module init and exposed as `fltk._native.UnknownSpan`, but is no longer read by generated code (which uses per-extension `UNKNOWN_SPAN_CACHE` instead). Added a `TODO(rust-cst-shared-rlib)` reference. No behavioral change; the static and its `m.add("UnknownSpan", ...)` initialization are retained for back-compat.
- Severity assessment: No runtime defect. Latent dead-code/coupling-confusion risk if a future editor assumes `crate::UNKNOWN_SPAN` is still the source of truth for generated code.

security-1:
- Disposition: Fixed
- Action: Added a trust-boundary note to the `_load_rust_cst_classes` docstring in `fltk/plumbing.py:82-87`. The note explicitly states that `module_name` must be a statically known, trusted value and explains that `importlib.import_module` executes the module's top-level code, making an attacker-controlled module name equivalent to arbitrary code execution.
- Severity assessment: No active vulnerability — `rust_cst_module` is developer-controlled throughout. Risk is latent; an application that forwards config-file or request-derived strings into this parameter would gain an arbitrary-module-import surface.

security-2:
- Disposition: Won't-Do
- Action: No change. The `exec()` of generated parser/unparser code is pre-existing and predates this diff. This diff reduces exec surface for the Rust CST path (no `exec` of CST code). The standing assumption — grammars are trusted developer artifacts — applies to the whole toolkit, not just this phase.
- Severity assessment: Pre-existing architectural assumption, not a new path. Won't-Do because fixing it would require redesigning the code generator, which is out of scope for any review round.
- Rationale (Won't-Do): This is a standing trust assumption of the toolkit (noted as such), not a regression introduced by this diff. The diff actually reduces exec surface by skipping CST exec on the Rust path. A fix would require a fundamental redesign of the generator architecture, entirely out of scope here.

test-1:
- Disposition: Fixed
- Action: Deleted `test_rust_backend_no_python_exec_fallback` from `fltk/test_plumbing.py`. It was byte-for-byte identical to `test_rust_backend_missing_module_hard_errors` (same grammar, same module name, same assertions). The remaining test covers both failure mode assertions.
- Severity assessment: Zero additional coverage — a regression where `sys.modules` is polluted in one failure mode would be caught equally by either test. Duplicate adds noise without signal.

test-2:
- Disposition: Fixed
- Action: Replaced `try/except` sentinel pattern with `with pytest.raises(RustBackendUnavailableError):` in `test_parse_grammar_rust_missing_module_no_fallback`. `fltk/test_plumbing.py:545-548`.
- Severity assessment: A regression where the wrong exception type is raised (e.g. a plain `RuntimeError`) would cause the old test to silently pass with `result is None`; the new form correctly fails.

test-3:
- Disposition: Fixed
- Action: Deleted `test_parse_grammar_file_rust_backend` from `tests/test_phase4_fegen_rust_backend.py`. Body was identical to `test_fegen_grammar_itself_rust_equals_python` (same inputs, same assertion). `tests/test_phase4_fegen_rust_backend.py:88-92`.
- Severity assessment: Zero additional coverage; both tests call `parse_grammar_file(_FEGEN_FLTKG_PATH, ...)` and assert equality.

test-4:
- Disposition: Fixed
- Action: Added `assert pr.parser_class is not None` to `test_rust_backend_uses_provided_classes`. `fltk/test_plumbing.py:524`.
- Severity assessment: Without the assertion, a `ParserResult` with a `None` parser class would still pass the existing `in sys.modules` and `hasattr` assertions, hiding the defect.

test-5:
- Disposition: TODO(rust-cst-child-span-test)
- Action: Added TODO comment at `tests/test_phase4_fegen_rust_backend.py:120` and entry in `TODO.md`. The finding is valid: `fltk2gsm.Cst2Gsm.visit_identifier/visit_literal/visit_regex` call `.start`/`.end` on results of `child_name()`/`child_value()` on fegen CST nodes. No focused test verifies these properties on Rust-backed nodes (AC8 covers it indirectly).
- Severity assessment: A regression where `child_name()` returns an object without `.start`/`.end` would only surface in the full AC8 parse path, making root-cause diagnosis harder.

test-6:
- Disposition: Fixed
- Action: Replaced `assert "UNKNOWN_SPAN\n" not in poc_source` with `assert "\nuse crate::UNKNOWN_SPAN" not in poc_source` at `tests/test_gsm2tree_rs.py:207`. The new assertion targets the exact import form that would re-introduce crate-level linkage, rather than a fragile newline-suffix pattern.
- Severity assessment: The old assertion would pass vacuously if the coupling re-appeared without a trailing newline (e.g. `UNKNOWN_SPAN.get`). The stronger check at line 208 (`UNKNOWN_SPAN.get(py)`) also covers the behavioral invariant; line 207 is now the structural import check.

test-7:
- Disposition: Fixed
- Action: Moved `sys.modules[module_name] = cst_module` to after the parser exec and `parser_class` validation in `generate_parser`. `fltk/plumbing.py:248`. A codegen failure (bad AST, missing Parser class) no longer leaves a stale entry under `fltk_grammar_{id(grammar)}`.
- Severity assessment: A grammar object that fails parser generation leaves a poisoned `sys.modules` entry; a subsequent call with the same grammar `id` (possible under CPython object reuse) would observe the broken module.

reuse-1 / quality-1:
- Disposition: Fixed
- Action: Extracted `_read_and_parse_grammar` private helper in `fltk/fegen/genparser.py:26-57`. Both `parse_grammar_file` (now at genparser.py:60-63) and `_parse_grammar_raw` (now at genparser.py:222-230) delegate to it; `parse_grammar_file` applies trivia rules after the call, `_parse_grammar_raw` returns directly. The now-resolved `TODO(genparser-parse-dedup)` was removed from `TODO.md` and `genparser.py`.
- Severity assessment: Two places in the same file must be updated if fltk_parser invocation, error formatting, or TerminalSource semantics change. Each additional grammar-emitter subcommand would copy the bug.

reuse-2:
- Disposition: Won't-Do
- Action: No change. `genparser.parse_grammar_file` and `genunparser.parse_grammar_file` pre-date this diff and were not touched by the Phase 4 implementation. The finding describes pre-existing technical debt (three independent `parse_grammar_file` implementations). Introducing a refactor of pre-existing untouched code in a respond round would widen scope without a design mandate.
- Severity assessment: Pre-existing; not a regression. Any future Phase 5 / cleanup increment should consolidate these.
- Rationale (Won't-Do): Not introduced by this diff. Refactoring pre-existing code in respond mode — touching `genparser.parse_grammar_file`, `genunparser.parse_grammar_file`, and `plumbing.parse_grammar` — is scope beyond what respond mode should do. The TODO system (`genparser-parse-dedup`) tracks the related work at the right level.

quality-2:
- Disposition: Fixed
- Action: Same as test-7 — `sys.modules` registration moved to after exec. See test-7.
- Severity assessment: See test-7.

quality-3:
- Disposition: TODO(fegen-cst-rs-single-source)
- Action: Added TODO comment at top of `tests/rust_cst_fegen/src/cst.rs:1-3` and entry in `TODO.md`. The duplicate committed file is a maintenance hazard but fixing it requires a build-system change (Makefile copy step, symlink, or `include!` macro) that is out of respond-round scope. Stringly-typed `"fltk._native"` / `"UnknownSpan"` constants in the generator are noted but deferred to `TODO(rust-cst-abi-pinning)` already present in `TODO.md`.
- Severity assessment: Silent divergence is possible when `src/cst_fegen.rs` is updated; the build will still succeed but the fegen Rust CST fixture tests the wrong code.

efficiency-1:
- Disposition: Fixed
- Action: Added `_fegen_rust_parser_cache: dict[str, ParserResult] = {}` at module scope in `fltk/plumbing.py:41`. The Rust-backend branch of `parse_grammar` now checks the cache before calling `generate_parser`; on cache hit only `TerminalSource` construction, the parse call, and `Cst2Gsm` are per-call. `fltk/plumbing.py:143-152`.
- Severity assessment: Every Rust-backend grammar parse previously paid full parser-codegen + `exec` cost (milliseconds per call). On a test suite parsing many `.fltkg` files with the Rust backend, this was a gratuitous multiplier over the Python path.

efficiency-2:
- Disposition: Won't-Do
- Action: No change. The `labeled_children` list allocation in `visit_items` is acknowledged as modest per-node overhead on the Python path where the filter is a no-op. The uniform code path has clarity value; the cost is small (grammar conversion is not a tight inner loop).
- Severity assessment: O(total children) extra allocation during CST-to-GSM conversion on both backends, even when no None-labeled children exist.
- Rationale (Won't-Do): Design doc and efficiency reviewer both acknowledge the tradeoff and flag it as low priority. Adding a backend-conditional branch or empty-check optimization adds complexity for negligible real-world benefit in a one-shot grammar conversion path.
