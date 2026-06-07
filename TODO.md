# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `pin-ci-actions`

SHA-pin all GitHub Actions references in `.github/workflows/ci.yml` to immutable commit SHAs rather than mutable branch/tag refs. Currently `dtolnay/rust-toolchain@stable`, `actions/checkout@v4`, and `astral-sh/setup-uv@v6` use mutable refs. A compromised action repo could execute arbitrary code in CI and tamper with build artifacts. Use Dependabot to manage SHA-pinned action updates. Location: `.github/workflows/ci.yml:12,15,21`.

## `extract-rule-name-to-class-name`

Extract the underscore-to-CamelCase rule-name-to-class-name transform into a shared helper. Currently four independent copies exist: `CstGenerator.class_name_for_rule_node` (`gsm2tree.py`), `UnparserGenerator.class_name_for_rule_node` (`gsm2unparser.py`), an inline list-comp (`gsm2unparser.py`), and `_rust_variant_name` (`gsm2tree_rs.py`). A behavioral change (e.g. digit handling, consecutive underscores) must be applied in four places. Candidate location: `fltk/fegen/gsm2tree.py` or a new `fltk/fegen/naming.py`. Location: `fltk/fegen/gsm2tree_rs.py:18`.

## `test-class-is-type-body`

Strengthen or remove the `isinstance(cls, type)` assertion in `TestAllClassesImportable.test_class_is_type`. The assertion passes for any imported object including a misimported alias; import success is the real AC-7 check. Option: replace with `cls()` construction (already covered by AC-8a tests). Location: `tests/test_fegen_rust_cst.py:67`.

## `fegen-cst-rs-single-source`

`src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` are identical files committed independently. When one is updated (e.g. by regeneration after a grammar change), the other must be separately regenerated and committed; silent divergence is possible. Fix: remove `tests/rust_cst_fegen/src/cst.rs` from the repo and generate it from `src/cst_fegen.rs` at build time (via symlink, Makefile copy step, or Rust `include!` macro), making the single source of truth explicit. Location: `tests/rust_cst_fegen/src/cst.rs`.

## `rust-cst-pyi`

Emit a `.pyi` (or equivalent static surface) for the Rust CST extension from GSM alongside `gen-rust-cst`, and add B4 Rust-backend verification (compile + import + pyright check that the real PyO3 surface genuinely satisfies `CstModule`). Deferred per ADR `05-cst-type-annotations-regression` B3a: the shared `CstModule` Protocol covers B1/B6 for the Rust path via a boundary cast at the injection site (`plumbing.py`); the `.pyi`'s sole remaining function is verifying the cast doesn't mask a real surface gap. Location: `fltk/fegen/genparser.py` (`gen_rust_cst` command).

## `cst-protocol-label-free`

Protocol classes for label-free CST nodes declare `children: list[tuple[None, T]]` while label-bearing nodes use `list[tuple[Optional[Label], T]]`. This asymmetry means generic code iterating children of arbitrary node types must case-split on whether the node has labels, which is not inferrable from the Protocol type alone. Fix: introduce a vacuous `Label` class for label-free nodes (or a `_NoLabel = None` alias) so all node `children` share the same tuple shape. Location: `fltk/fegen/gsm2tree.py` (`_protocol_class_for_model`).

## `cst-protocol-generator-refactor`

Unify `protocol_annotation_for_model_types` with `py_annotation_for_model_types` (gsm2tree.py) and `_protocol_class_for_model` with `py_class_for_model` (gsm2tree.py). Both pairs share identical structure (Union building, label quintet ordering) with only the annotation resolver, Label body, method bodies, and base class differing. A shared skeleton with injected strategies would eliminate ~120 lines of parallel code; currently any new per-label accessor (e.g. `count_<l>`) or Union syntax change must be applied in both generators. Location: `fltk/fegen/gsm2tree.py`.

## `rust-cst-child-span-test`

No focused test verifies that Rust-backed CST child-accessor results expose `.start`/`.end` attributes (required by `fltk2gsm.Cst2Gsm.visit_identifier`, `visit_literal`, `visit_regex`). The AC8 equality test exercises this indirectly but a regression would only surface in the full parse path. Add a direct test calling `node.child_name()` (or `child_value()`) on a Rust-backed fegen node and asserting `.start`/`.end` are accessible and correct. Location: `tests/test_phase4_fegen_rust_backend.py`.


## `rust-cst-child-node-identity`

Native child ownership (`Box<ChildNode>` in the native Vec) means a child returned twice through a Python getter/accessor wraps a fresh `Py<ConcreteNode>` per call; the same child read twice is not the same Python object (identity differs). Tests in `tests/test_phase4_rust_fixture.py` that formerly used `is` for child identity were relaxed to `==` (value equality). If a consumer requires stable Python child-object identity, add a per-node boundary cache (e.g. `Py` cache indexed by position) at the generated accessor layer. Deferred: no in-tree consumer currently requires identity stability. Location: `fltk/fegen/gsm2tree_rs.py` (accessor methods in `_per_label_methods`); see also `tests/test_phase4_rust_fixture.py:242,276,291,350,371`.

## `gencode-poc-fltkg`

`src/cst_generated.rs` is regenerated by an inline Python one-liner in the `gencode` Makefile target (via `_make_poc_grammar` from `tests/test_gsm2tree_rs.py`) rather than through the standard `gen-rust-cst` path. Create a `.fltkg` source file for the PoC grammar so `make gencode` can regenerate `src/cst_generated.rs` through `fltk.fegen.genparser gen-rust-cst`, matching the regeneration path of all other generated files and picking up any future preamble changes automatically. Location: `Makefile:83-88`.

## `span-source-as-py-crosscdylib`

`Span::source_as_py` (crates/fltk-cst-core/src/span.rs) clones only the Arc (O(1)) and is the correct API for source-preservation in span-returning accessors, but cannot be used in generated code for out-of-tree consumer crates because the locally-registered `SourceText` type object differs from `fltk._native.SourceText`. Currently, generated accessors call `source_full_text_str()` + `get_source_text_type(py)?.call1(full_text)` which copies the full source string twice per accessor call (O(source length) per node read). Fix: add an `extract_source_text` helper to the generated preamble (analogous to `extract_span`, using the shared-rlib invariant and `downcast_unchecked`) so generated code can use `source_as_py` cross-cdylib without a string copy. Location: `fltk/fegen/gsm2tree_rs.py` (preamble and span-getter/to_pyobject emission); `crates/fltk-cst-core/src/span.rs:source_as_py`.

## `protocol-label-member-private`

`_ProtocolLabelMember` is emitted as a module-level class in the generated public protocol module (`fltk_cst_protocol.py`). It appears in `from fltk_cst_protocol import *` and in IDE autocompletion; downstream consumers could accidentally take a dependency on it, making it de-facto public API subject to breaking-change rules. Options: (a) emit a module-level `__all__` listing only the intended public symbols, suppressing `_ProtocolLabelMember` from wildcard imports; or (b) move the class to `fltk.fegen.pyrt.bridge` (or similar) and import it into the generated module from there, keeping the implementation out of the public-API file. Location: `fltk/fegen/gsm2tree.py` (`_emit_protocol_label_member_class`, `gen_protocol_module`).


