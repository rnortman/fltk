# TODOs

## `example-placeholder`

This is a placeholder entry. Leave it here so the file is never empty. It is not a real TODO. You would reference it in code with `// TODO(example-placeholder)` comments. This is the basic TODO system design: An entry here with a slug used to join to code comments. Add real TODOs below this one in this format.

## `bazel-rules-rust`

Add `rules_rust` to `MODULE.bazel` so that the PyO3 native extension (`fltk._native`) is buildable via Bazel. Currently, Bazel builds do not include the Rust extension. Deferred from Phase 0 because Bazel Rust support is orthogonal to the Python/maturin build path. Location: `MODULE.bazel`.

## `backend-with-source-signature`

Unify the `Span.with_source` construction API across backends. Currently the Python backend takes a raw `str` while the Rust backend takes a `SourceText` handle. Code using `from fltk.fegen.pyrt.span import Span` that calls `Span.with_source(start, end, src_str)` breaks silently when the Rust backend is active. Options: expose a `SourceText`-like wrapper in the Python backend, or accept both types in the Rust backend. Deferring until the parse path is wired to produce source-bearing spans (Phase 2+). Location: `fltk/fegen/pyrt/span.py`.

## `pin-ci-actions`

SHA-pin all GitHub Actions references in `.github/workflows/ci.yml` to immutable commit SHAs rather than mutable branch/tag refs. Currently `dtolnay/rust-toolchain@stable`, `actions/checkout@v4`, and `astral-sh/setup-uv@v6` use mutable refs. A compromised action repo could execute arbitrary code in CI and tamper with build artifacts. Use Dependabot to manage SHA-pinned action updates. Location: `.github/workflows/ci.yml:12,15,21`.

## `extract-rule-name-to-class-name`

Extract the underscore-to-CamelCase rule-name-to-class-name transform into a shared helper. Currently four independent copies exist: `CstGenerator.class_name_for_rule_node` (`gsm2tree.py`), `UnparserGenerator.class_name_for_rule_node` (`gsm2unparser.py`), an inline list-comp (`gsm2unparser.py`), and `_rust_variant_name` (`gsm2tree_rs.py`). A behavioral change (e.g. digit handling, consecutive underscores) must be applied in four places. Candidate location: `fltk/fegen/gsm2tree.py` or a new `fltk/fegen/naming.py`. Location: `fltk/fegen/gsm2tree_rs.py:18`.

## `test-class-is-type-body`

Strengthen or remove the `isinstance(cls, type)` assertion in `TestAllClassesImportable.test_class_is_type`. The assertion passes for any imported object including a misimported alias; import success is the real AC-7 check. Option: replace with `cls()` construction (already covered by AC-8a tests). Location: `tests/test_fegen_rust_cst.py:67`.

## `perf-label-identity-comparison`

The generated `tup.get_item(0)?.eq(&label_obj)?` pattern in label-accessor methods performs an O(children) linear scan with equality comparison per access. Identity comparison (`is`) or pre-grouped storage would be O(1). Defer until profiling confirms a bottleneck. Location: `fltk/fegen/gsm2tree_rs.py` (template in `_per_label_methods`).

## `rust-cst-shared-rlib`

If user extensions ever need to link Rust-level shared types (e.g. a typed `Span`), a `fltk-cst-common` rlib combined with a Cargo workspace (Option D) is the clean answer. Today the node's `span` is an opaque `PyObject`; no Rust-level linkage between the user's crate and FLTK's crate is needed. Revisit when user extensions need to link Rust-level shared types. Location: `fltk/fegen/gsm2tree_rs.py` (`_preamble` method).

## `rust-cst-abi-pinning`

No version handshake exists between a user's standalone Rust CST extension and `fltk._native`. If `Span`/`UnknownSpan` shape changes between FLTK versions, a user extension built against an older FLTK could misbehave silently. If skew proves fragile, add an ABI-version check at the sentinel fetch inside the generated `UNKNOWN_SPAN_CACHE` init. Location: `fltk/fegen/gsm2tree_rs.py` (`_new_method` method).

## `fegen-cst-rs-single-source`

`src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` are identical files committed independently. When one is updated (e.g. by regeneration after a grammar change), the other must be separately regenerated and committed; silent divergence is possible. Fix: remove `tests/rust_cst_fegen/src/cst.rs` from the repo and generate it from `src/cst_fegen.rs` at build time (via symlink, Makefile copy step, or Rust `include!` macro), making the single source of truth explicit. Location: `tests/rust_cst_fegen/src/cst.rs`.

## `rust-cst-pyi`

Emit a `.pyi` (or equivalent static surface) for the Rust CST extension from GSM alongside `gen-rust-cst`, and add B4 Rust-backend verification (compile + import + pyright check that the real PyO3 surface genuinely satisfies `CstModule`). Deferred per ADR `05-cst-type-annotations-regression` B3a: the shared `CstModule` Protocol covers B1/B6 for the Rust path via a boundary cast at the injection site (`plumbing.py`); the `.pyi`'s sole remaining function is verifying the cast doesn't mask a real surface gap. Location: `fltk/fegen/genparser.py` (`gen_rust_cst` command).

## `cst-protocol-label-free`

Protocol classes for label-free CST nodes declare `children: list[tuple[None, T]]` while label-bearing nodes use `list[tuple[Optional[Label], T]]`. This asymmetry means generic code iterating children of arbitrary node types must case-split on whether the node has labels, which is not inferrable from the Protocol type alone. Fix: introduce a vacuous `Label` class for label-free nodes (or a `_NoLabel = None` alias) so all node `children` share the same tuple shape. Location: `fltk/fegen/gsm2tree.py` (`_protocol_class_for_model`).

## `parse-result-typed`

Make `ParseResult` generic (`class ParseResult(Generic[T]): cst: T | None`) so that `result.result` is typed at each call site rather than `Any`, eliminating the five scattered `cast("cstp.GrammarNode", result.result)` calls in `fltk/fegen/genparser.py`, `fltk/plumbing.py` (×2), `fltk/unparse/genunparser.py`, and `fltk/test_plumbing.py`. Currently `ParseResult.cst` is `Any` (`fltk/fltk/plumbing_types.py`), which forces per-site casts that can silently degrade if the parser's return type changes. Location: `fltk/plumbing_types.py`.

## `cst-protocol-generator-refactor`

Unify `protocol_annotation_for_model_types` with `py_annotation_for_model_types` (gsm2tree.py) and `_protocol_class_for_model` with `py_class_for_model` (gsm2tree.py). Both pairs share identical structure (Union building, label quintet ordering) with only the annotation resolver, Label body, method bodies, and base class differing. A shared skeleton with injected strategies would eliminate ~120 lines of parallel code; currently any new per-label accessor (e.g. `count_<l>`) or Union syntax change must be applied in both generators. Location: `fltk/fegen/gsm2tree.py`.

## `rust-cst-child-span-test`

No focused test verifies that Rust-backed CST child-accessor results expose `.start`/`.end` attributes (required by `fltk2gsm.Cst2Gsm.visit_identifier`, `visit_literal`, `visit_regex`). The AC8 equality test exercises this indirectly but a regression would only surface in the full parse path. Add a direct test calling `node.child_name()` (or `child_value()`) on a Rust-backed fegen node and asserting `.start`/`.end` are accessible and correct. Location: `tests/test_phase4_fegen_rust_backend.py`.

## `canonical-name-cache`

The Rust `__hash__` implementation allocates a fresh `PyString` (for the salted CPython hash) on every call; the allocation is load-bearing for cross-backend hash agreement (AC4) but can be amortized. Cache the computed `isize` per variant via `GILOnceCell` so the `PyString` is built at most once per variant per process. (The Python-side canonical-name property was replaced with a plain per-member string attribute in this iteration, restoring cheap same-backend hashing there.) Location: `fltk/fegen/gsm2tree_rs.py` (`_emit_rust_cross_backend_eq_hash`).

## `kind-field-dataclass-eq`

The `kind` dataclass field joins the generated `__eq__`/`__hash__` for every node, but it is invariant within a node type (a node of type `Item` always has `kind == NodeKind.Item`). The comparison is cheap (same singleton, `other is self` fast path), but it is pure overhead on every structural node equality. Mark `kind` with `dataclasses.field(compare=False, repr=False)` if node-equality performance becomes a concern. Location: `fltk/fegen/gsm2tree.py` (`py_class_for_model`, `kind` field emit).

## `protocol-label-member-bridge-unify`

`_emit_protocol_label_member_class` in `gsm2tree.py` emits `__eq__`/`__hash__` via a raw `ast.parse()` string instead of calling the existing `_emit_cross_backend_eq_hash` helper. This creates two independent implementations of the cross-backend bridge that can drift independently. Refactor `_emit_protocol_label_member_class` to call `_emit_cross_backend_eq_hash` (or extract a pygen-based helper shared by both) so any future bridge change propagates everywhere. The divergence today (non-enum uses `_fltk_canonical_name` name comparison in the same-type fast-path; enum uses `.name`) is intentional but the coupling between the docstring note and the actual code is informal. Location: `fltk/fegen/gsm2tree.py` (`_emit_protocol_label_member_class`, `_emit_cross_backend_eq_hash`).

## `protocol-label-member-private`

`_ProtocolLabelMember` is emitted as a module-level class in the generated public protocol module (`fltk_cst_protocol.py`). It appears in `from fltk_cst_protocol import *` and in IDE autocompletion; downstream consumers could accidentally take a dependency on it, making it de-facto public API subject to breaking-change rules. Options: (a) emit a module-level `__all__` listing only the intended public symbols, suppressing `_ProtocolLabelMember` from wildcard imports; or (b) move the class to `fltk.fegen.pyrt.bridge` (or similar) and import it into the generated module from there, keeping the implementation out of the public-API file. Location: `fltk/fegen/gsm2tree.py` (`_emit_protocol_label_member_class`, `gen_protocol_module`).


