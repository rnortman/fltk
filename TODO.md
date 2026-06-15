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

## `extend-children-owned`

`extend_children(&Self)` clones every child Arc even though the donor node is immediately dropped after the call (inline-to-parent sub-expression and `+`/`*` loop paths). A consuming variant `extend_children_owned(other: Self)` using `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`, `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>` blocks). Re-open only with profiling evidence.

