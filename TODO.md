# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

Implementation in progress — see ADR at `docs/adr/2026/06/13-rust-bazel-packaging/`.

## `verify-pyo3-ext-module`

At implementation spike time, confirm that `extension-module` is active on the `@fltk_crates//:pyo3` target after `crate_universe` resolution. Run `bazel build //:native` on a clean checkout; if pyo3 links libpython the feature is not activated and a `crate.annotation(crate = "pyo3", crate_features = ["extension-module"])` is needed in `MODULE.bazel`'s `crate.from_cargo` block. Also confirm that dev-dep crates from the root workspace do not leak into the hub. Location: `MODULE.bazel` (`crate.from_cargo` block).

## `native-submodule-error-context`

`register_submodule` propagates errors from `register_classes` via `?` with no added context naming which submodule failed. A future improvement: annotate the error with the submodule name before propagating, so an `ImportError` at module import time names `"cst"` or `"parser"` as the culprit. Location: `crates/fltk-cst-core/src/py_module.rs` (`register_submodule` definition, line ~87).

## `native-span-init-error-context`

When `Py::new(m.py(), Span::unknown())` fails during `fltk._native` module init, the Python import raises a generic pyo3 `RuntimeError` with no indication the failure was in UnknownSpan sentinel creation. Wrap with a structured message so on-call can distinguish this from submodule registration failures. Location: `fltk/fegen/gsm2lib_rs.py` (`RustLibGenerator.generate()`, body for `unknown_span_static`).

## `submodule-register-fn-convention`

`Submodule.register_fn` is validated for Rust identifier syntax but not for the convention that it should be `register_classes` (the name the codegenned `pub fn register_classes` uses). A caller with a non-standard name gets a Rust compile error rather than a Python-level error. Document or enforce the `register_classes` convention in `Submodule.validate()`. Location: `fltk/fegen/gsm2lib_rs.py` (`Submodule.validate()`).

## `bazel-lib-rs-no-cst`

`fltk_pyo3_cdylib`'s assembly genrule unconditionally declares `cst.rs` and `parser.rs` as required outputs, even when `lib_rs=None` (auto-generated path). Every current caller is a grammar crate and supplies both files. A future runtime-only (span-only) crate built via this macro would hit the `test -f` guards with a misleading error. At that point, split into grammar and span-only assembly variants. Location: `rust.bzl` (`_assemble_crate` genrule, line ~239).

## `gsm-for-each-item-public`

`gsm._for_each_item` is a private function used internally by `gsm.py` for validation passes, but `fltk/fegen/regex_corpus.py` is the first cross-module caller. Promote it to a public name (`for_each_item`) in `gsm.py`, or add a public `iter_regexes(grammar)` helper that encapsulates the walk so callers never need to touch the structural walk API. Gives callers a stable, tested contract instead of a private-name dependency that mypy/pyright won't flag across modules. Location: `fltk/fegen/gsm.py` (`_for_each_item`), `fltk/fegen/regex_corpus.py:58` (call site).

## `forged-abi-extract-span-uniformity`

`check_instance_layout` is generic and could be applied to `extract_span` for uniformity.
Currently `extract_span` is not reachable by forged objects (it is gated by `is_instance`
against the non-subclassable canonical `fltk._native.Span` type, plus `check_abi_pair::<Span>`
in `get_span_type`), so adding `check_instance_layout` there would add no rejection power.
Revisit only if a future change makes `extract_span` reachable by non-canonical types.
Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`extract_span`).

## `regex-unicode-class-divergence`

The regex portability lint admits `\d`/`\w`/`\s` (and negations), `\b`/`\B` word boundaries, and `(?i)` as ASCII-portable constructs. However, these constructs have a non-ASCII semantic residual: the Unicode-class tables and case-folding tables differ between Python `re` and `regex-automata` by Unicode DB version. A grammar using these constructs with non-ASCII input may get different parse results on the two backends without any error. This is documented as a permanent limit of any static approach (both engines agree on syntax but differ on semantics for non-ASCII). Tracking here to ensure the `document-scope-boundary` burndown item covers the full ledger: `\d`/`\D`/`\w`/`\W`/`\s`/`\S`, `\b`/`\B`, and `(?i)` over non-ASCII. Location: `fltk/fegen/regex_portability.py` (module-level docstring), `fltk/fegen/regex.fltkg` (comments on `class_shorthand`, `assertion`, `anchor_escape`, `flag_chars`).

## `regex-portability-target-list-drift`

`tests/test_regex_portability.py:test_committed_rust_target_grammar_regex_is_portable` hand-copies the list of Rust-parser-target grammars from the `make gencode` recipe (Makefile lines ~276, 279, 284-285). If a new grammar is added to `gen-rust-parser` in the Makefile without being added to `_RUST_PARSER_TARGET_GRAMMARS` in the test, the completeness check silently fails to cover it. Single-source this list — e.g. a small manifest or glob that both `make gencode` and the test read — to close the drift hole. Tie this to the `gencode-drift-gate` family when that item is burned down. Location: `tests/test_regex_portability.py` (`_RUST_PARSER_TARGET_GRAMMARS` list), `Makefile` (`gencode` recipe).

## `regex-portability-roundtrip-test`

Design §7 specifies a "positive-control round-trip" test that pins the committed `regex_parser.py` as having been generated from a clean `regex.fltkg` — either by regenerating into a temp dir and comparing, or by asserting the committed parser re-classifies all admitted/excluded test cases identically. The whole-tree completeness test partially discharges this (grammar drift that changes classification on in-tree patterns surfaces there), but it does not catch drift that reclassifies no currently-committed pattern. Add a round-trip gate, e.g. a test that generates the parser into a temp dir and byte-compares it to the committed `regex_parser.py`, or extends the completeness test to include all unit-test `_PORTABLE_PATTERNS` / `_NON_PORTABLE_PATTERNS` cases as an oracle. Location: `tests/test_regex_portability.py` (new test function), `fltk/fegen/regex_parser.py` (committed artifact being guarded).

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

## `linecol-cache-consolidate`

`TerminalSource` carries its own `line_ends: OnceLock<Vec<i64>>` (`crates/fltk-parser-core/src/terminalsrc.rs:46`) while `SourceInner` (the allocation `TerminalSource` is built over) also carries `line_ends: OnceLock<Vec<i64>>` (`crates/fltk-cst-core/src/span.rs`). Both derive deterministically from the same immutable `text`, so they cannot disagree, but they duplicate state. A follow-up could point `TerminalSource::pos_to_line_col` at `&self.source.inner.line_ends` (the shared `resolve_line_col` function already accepts a caller-supplied `OnceLock`) and drop `TerminalSource`'s own field. Location: `crates/fltk-parser-core/src/terminalsrc.rs:46` (`line_ends` field) and the `pos_to_line_col` wrapper (~line 167,178).

## `py-span-linecol-cache`

Python `Span.line_col()` recomputes the O(N) line-ends scan on every call because the frozen-slots Python `Span` carries only a raw `str` and cannot reach a mutable cache. The `SourceText` dataclass already gains a `_filename` field in the span-line-col-api change; a parallel `_line_ends` list on `SourceText` threaded through `with_source` would let the Python span amortize the scan the same way the Rust backend does via `SourceInner.line_ends`. Deferred because error reporting is a cold path and the added `with_source` plumbing is non-trivial. Location: `fltk/fegen/pyrt/terminalsrc.py:133` (`Span.line_col` implementation).

## `spanprotocol-native-linecol`

`SpanProtocol.line_col` / `line_col_or_raise` are typed to return `terminalsrc.LineColPos`. The native `fltk._native.Span.line_col` returns the native `LineColPos` (a distinct nominal class declared in `fltk/_native/__init__.pyi`), so `fltk._native.Span` is **not statically** assignable to `SpanProtocol` — it conforms only by runtime `isinstance` plus its `.pyi` `span: SpanProtocol` declaration. This is a contained, pre-existing gap (the pure-Python parser, the only place a span *value* is statically assigned into a `SpanProtocol` slot within `make check`'s pyright scope, feeds `terminalsrc.Span`, which *is* statically conformant). Close it by unifying `LineColPos` across the two backends (one shared nominal type) so native spans conform statically too. Deferred per design-delta D5.2/D8; it does not block the span-isolation work. Location: `fltk/fegen/pyrt/span_protocol.py` (`line_col`/`line_col_or_raise` return annotations), `fltk/_native/__init__.pyi` (native `LineColPos`).

Constraint when closing this: the generated pipeline (parser/CST/protocol/unparser) imports `SpanProtocol`, and its R2 pyright stub-stability holds structurally only because `SpanProtocol`'s own definition names no `fltk._native` symbol (delta D5.1). The source-level "generated files name no native" tests (`fltk/fegen/test_cst_protocol.py`, `test_genparser.py`, `test_gsm2tree_rs.py`, `test_is_span_guard.py`) do NOT cover transitive stub-sensitivity introduced via `span_protocol.py` itself. If a fix makes `SpanProtocol`'s structural surface native-dependent, add a differential (stub-present-vs-absent) or structural stub-stability guard for the generated pipeline at the same time.


## `span-selector-broken-native-diagnostic`

`fltk/fegen/pyrt/span.py`'s backend-selector `try: from fltk._native import ... except Exception:` falls back to the pure-Python backend silently for ANY exception, not just `ImportError`/`ModuleNotFoundError`. A present-but-broken native extension (ABI mismatch after a Python upgrade, corrupted `.so`, C-level init crash raising `OSError`/`SystemError`) is therefore swallowed with no diagnostic: `span.Span` silently becomes `terminalsrc.Span` and the only signal is `tests/test_span_protocol.py`'s `span.Span is fltk._native.Span` assertion failing. Decide deliberately between (a) narrowing the catch so a genuinely broken extension propagates (trades selector robustness for diagnosability — note ABI errors often surface as `ImportError` anyway, and a pure-Python namespace-package install raises `ImportError` for the missing `Span`, so narrowing must stay correct for that case) and (b) keeping silent fallback but logging the swallowed exception at WARNING with `exc_info=True` (re-adds a diagnostic the user asked to remove for the *absent* case — would need to fire only for non-`ImportError`). Pre-existing breadth (the diff only removed the `warnings.warn`); the identical pattern lives at `fltk/fegen/pyrt/span_protocol.py` (`AnySpan` block) and should move in lockstep. `span.py` is now out of the generated pipeline, so impact is confined to the standalone selector utility. Location: `fltk/fegen/pyrt/span.py:8` (the `try/except` selector), `fltk/fegen/pyrt/span_protocol.py` (`AnySpan`).

## `unparser-source-helper`

`fltk/unparse/test_is_span_guard.py`'s `_generate_unparser_source` re-implements `plumbing.generate_unparser`'s 7-step assembly pipeline (`create_default_context` → `add_trivia_rule_to_grammar` → `classify_trivia_rules` → `gsm2unparser.generate_unparser` → `compiler.compile_class` → `ast.Module` assembly → `ast.unparse`) because `plumbing.generate_unparser` exposes no way to retrieve the generated source before it `exec`s the module. The helper is called 4x in that file, and any change to the assembly list (new imports, reordered trivia steps) must be mirrored in both places or they drift. Expose a source-returning entry point — e.g. `plumbing.generate_unparser_source(grammar, cst_module_name, formatter_config)` returning the unparsed source, with `generate_unparser` exec'ing its output — and have the test call it, single-sourcing the pipeline. Location: `fltk/unparse/test_is_span_guard.py` (`_generate_unparser_source`), `fltk/plumbing.py` (`generate_unparser`, line ~257).
