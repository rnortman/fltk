# Deep correctness review — rust-cst-pyi

Reviewed: `46a6639..c78a014` (HEAD c78a014). Style: concise, precise, no padding. Audience: smart LLM/human.

## correctness-1 — generated Python CST modules now crash on import without the compiled extension

- **File:line:** `fltk/fegen/gsm2tree.py:181-184` (new `pyreg.Module(("fltk", "_native"))` import) and `:239-242` (span union); regenerated artifacts `fltk/fegen/fltk_cst.py:5`, `fltk/fegen/bootstrap_cst.py:5`, `fltk/unparse/toy_cst.py:5`, `fltk/unparse/unparsefmt_cst.py:5`.
- **What's wrong:** The concrete generated CST modules now contain a bare runtime `import fltk._native` and the class-body annotation `span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = ...`. These modules have **no** `from __future__ import annotations`, so the annotation expression — including the `fltk._native.Span` attribute access — is evaluated eagerly at class-definition time (Python 3.10–3.13). Contrast the protocol modules, which guard the same import under `if typing.TYPE_CHECKING:` (`fltk_cst_protocol.py:9-11`) precisely to avoid a runtime dependency.
- **Why (traced):** In an environment without the compiled extension:
  - If `fltk/_native/` (the new `.pyi`-only directory) is not shipped: `import fltk._native` → `ModuleNotFoundError`. Verified in-sandbox: blocking `fltk._native` makes `import fltk.fegen.bootstrap_cst` raise `ModuleNotFoundError`.
  - If the `.pyi`-only directory is shipped: the import succeeds as a namespace-package portion, but `fltk._native.Span` in the eagerly-evaluated annotation raises `AttributeError` (no `Span` attribute on the empty namespace package). Eager evaluation confirmed empirically (the error fires during class-body execution of `bootstrap_cst`).
  Either way every generated CST module — and therefore every generated parser that imports it — fails at import.
- **Contradicting invariants:** (a) `fltk/fegen/pyrt/span.py:12-18` implements an explicit, warning-emitting pure-Python fallback for exactly this no-native configuration — now unreachable, since the CST modules die first. At base, the only runtime references to `fltk._native` outside protocol files were try/except-guarded (`pyrt/span.py`, `pyrt/span_protocol.py:59-64`); this change introduces the first unguarded one on the parse path. (b) The Bazel path: `BUILD.bazel` `py_library(srcs = glob(["**/*.py"]))` ships these modules to downstream Bazel consumers, and Bazel cannot build the extension at all (`TODO(bazel-rules-rust)`, CLAUDE.md). Bazel was previously a working pure-Python consumption path for the generated parsers.
- **Consequence:** Any install lacking `_native.abi3.so` (Bazel downstream consumers; any pure-Python environment relying on the documented fallback) loses **all** parsing: `import fltk.fegen.fltk_parser` / `bootstrap_cst` raises at import time instead of warning and falling back. This is a runtime regression introduced solely to fix a static-typing problem (implementation log, Increment 4 deviation: 676 pyright errors); the log calls out the annotation widening but not the new hard runtime dependency.
- **Suggested fix:** Keep the widened annotation but make it lazy: emit `from __future__ import annotations` in generated CST modules (dataclasses tolerate string annotations), or quote the union (`"fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span"`) and move `import fltk._native` under `if typing.TYPE_CHECKING:` — the exact pattern the protocol generator already uses. Regenerate the four committed CST modules.

## correctness-2 — `_stub_class_names` reads `.parent` that is never set; crashes if called

- **File:line:** `tests/test_fltk_native_stub.py:57-64`, comment at `:74`.
- **What's wrong:** `_stub_class_names()` parses a fresh tree via `_parse_stub()` and filters on `isinstance(node.parent, ast.Module)`, but `.parent` is only annotated inside `_stub_classes_with_members()` — on a *different* tree from its own `_parse_stub()` call. The comment "annotate parents for `_stub_class_names()` above" claims cross-function state that does not exist.
- **Why:** `ast.parse` nodes have no `parent` attribute; the first top-level `ClassDef` reached in the generator expression raises `AttributeError`.
- **Consequence:** Latent crash. The function is currently dead (no caller), so no test fails today — but it is the natural helper for class-set assertions, and any future caller gets an `AttributeError` instead of class names. The misleading comment invites exactly that use.
- **Suggested fix:** Delete the function, or derive top-level classes from `tree.body` directly (as `_stub_top_level_names()` already does) without parent links; drop the false comment.

## correctness-3 — `--pyi-output` silently ignored without `--protocol-module`

- **File:line:** `fltk/fegen/genparser.py:265-330` (`gen_rust_cst`): `pyi_text` is set only when `protocol_module is not None`; `pyi_output` is consulted only inside `if pyi_text is not None:`.
- **What's wrong:** Invoking `gen-rust-cst grammar.fltkg out.rs --pyi-output some/path.pyi` (no `--protocol-module`) writes no stub, emits no diagnostic, and exits 0.
- **Consequence:** A caller who explicitly named a stub path believes it was (re)generated. Concretely: if a future Makefile/CI edit drops `--protocol-module` from the gencode invocation but keeps `--pyi-output fltk/_native/fegen_cst.pyi`, the committed stub silently stops being regenerated; `.rs`/`.pyi` drift then surfaces only via the B4 runtime tests (which skip when the extension isn't built) rather than at generation time.
- **Suggested fix:** Raise a usage error (`typer.BadParameter` / exit 1) when `pyi_output` is provided without `protocol_module`.

## correctness-4 — minor: stub-member collector excludes `__init__` despite docstring

- **File:line:** `tests/test_fltk_native_stub.py:67-95`.
- **What's wrong:** Docstring says members include "not dunder names (except `__init__`)", but the filter `not stmt.name.startswith("_")` excludes `__init__` along with all underscored names.
- **Consequence:** No impact today (`fegen_cst.pyi` declares no `__init__`), but if the emitter ever declares one, the stub-to-runtime direction silently skips verifying it — the test does less than its documentation claims.
- **Suggested fix:** Either implement the documented carve-out (`stmt.name == "__init__" or not stmt.name.startswith("_")`) or correct the docstring.

## correctness-5 — minor: dead variable in `generate_pyi`

- **File:line:** `fltk/fegen/gsm2tree_rs.py:184,193`.
- **What's wrong:** `python_label = label.upper()` is computed per label and never used; the `del python_label  # only used for documentation` comment is wrong (it is not used at all).
- **Consequence:** None at runtime; misleading data flow only.
- **Suggested fix:** Delete both lines.

---

Checked and clean: `.pyi` emitter member set vs `.rs` (both driven by one `_rule_info()`); quoted-rule-ref → `_proto.` regex (`"([A-Z]\w*)"` cannot match quoted lowercase library paths like `"fltk.fegen.pyrt.span.Span"`, and `protocol_annotation_for_model_types` quotes only rule refs); `kind` member naming (`class_name.upper()` == `node_kind_member_name`); `fltk/_native/__init__.pyi` vs `crates/fltk-cst-core/src/span.rs` pymethods (all declared members exist: `#[pyclass(frozen, eq, hash)]` supplies `__eq__`/`__hash__`; `SourceText` exposes only `new`); namespace-package vs extension import precedence claim (regular extension module wins over `.pyi`-only portion); `CstModule.Span` removal (property never satisfiable at runtime on either backend — removal loosens implementer requirements only); CLI partial-file ordering (`.pyi` text generated before any write); conformance fixture and B4 test directions. Deliberate, design-documented divergences not re-flagged: `children_<label>` typed `Iterator` while runtime returns `list`; `Label`/`NodeKind` typed as protocol identities while runtime objects are PyO3 enums.
