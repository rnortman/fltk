## Increment 1 — sub-task B: fix concrete generator for label-free nodes

- `fltk/fegen/gsm2tree.py:204-215`: wrapped `Label` enum emission in `if labels:` (was unconditional).
- `fltk/fegen/gsm2tree.py:219`: introduced `label_annotation = "typing.Optional[Label]" if labels else "None"` mirroring `_protocol_class_for_model`'s existing pattern.
- `fltk/fegen/gsm2tree.py:232`: `children` field uses `{label_annotation}` instead of `typing.Optional[Label]`.
- `fltk/fegen/gsm2tree.py:246,252`: `append`/`extend` `label` param uses `{label_annotation}` instead of `typing.Optional[Label]`.
- `fltk/fegen/gsm2tree.py:268`: `child()` return uses `{label_annotation}` instead of `typing.Optional[Label]`.
- `fltk/fegen/gsm2tree.py:582`: removed `TODO(cst-protocol-label-free)` comment block from `_protocol_class_for_model` (the TODO is now resolved).
- `TODO.md`: removed `cst-protocol-label-free` entry.
- `tests/test_gsm2tree_py.py`: new test file with `TestLabelFreeConcreteClass` (6 tests: no Label class, children/child/append/extend annotations, no post-class assignments) and `TestLabelBearingConcreteClassUnchanged` (4 tests: guards against regression on label-bearing path). All 10 pass.
- All 947 tests pass. ruff and pyright clean. In-tree CST/Protocol artifacts regenerated; zero diff (all grammars are label-bearing, so no in-tree change — byte-identity confirmed).

## Increment 3 — sub-task A: emit `__all__` in generated protocol modules (commit 2e8fe69)

- `fltk/fegen/gsm2tree.py:490-506` (`gen_protocol_module`): after building full module body, insert a sorted `__all__ = [...]` at index 5 (after the 5 import stmts) listing all protocol node names + `NodeKind`, `Span`, `CstModule`, excluding `_ProtocolLabelMember`. Built from `self.rule_models` iteration — cannot drift from emitted classes.
- `fltk/fegen/gsm2tree.py:424-435` (`_emit_protocol_label_member_class` docstring): removed `TODO(protocol-label-member-private)` paragraph.
- `TODO.md`: removed `protocol-label-member-private` entry.
- `tests/test_gsm2tree_py.py:219-337`: new `TestProtocolModuleAll` class with 7 tests covering: `__all__` present, contains protocol node names and fixed names, excludes `_ProtocolLabelMember`, `_ProtocolLabelMember` still a `ClassDef`, list is sorted, appears in first 10 stmts. Deviation: tests added to `tests/test_gsm2tree_py.py` (existing generator test file) rather than `fltk/fegen/test_cst_protocol.py` — same style, better colocation with other generator unit tests.
- In-tree artifacts regenerated (`fltk_cst_protocol.py`, `bootstrap_cst_protocol.py`, `toy_cst_protocol.py`, `unparsefmt_cst_protocol.py`): `__all__` added to each. 954 tests pass; ruff and pyright clean.

## Increment 2 — sub-task C: extract shared per-label quintet loop (commit 5ec9b0b)

- `fltk/fegen/gsm2tree.py:1`: added `Callable` to `collections.abc` import.
- `fltk/fegen/gsm2tree.py` (new method `_emit_label_quintet`): helper owning the `for label in labels:` iteration and the five accessor names/signatures, parameterized by `annotation_for: Callable[[str], str]` (per-label child type) and `body_for: Callable[[str, str], list[ast.stmt]]` (method name × label → body). Returns `list[ast.FunctionDef]` for callers to extend into their class body.
- `py_class_for_model`: replaced the 73-line inline quintet loop with a `concrete_body_for` closure (captures `class_name`, `child_annotation_by_labels`, `multi_type`) and a `klass.body.extend(self._emit_label_quintet(...))` call.
- `_protocol_class_for_model`: replaced the 29-line inline quintet loop with a `protocol_annotation_for` closure and a call using `lambda _method, _label: [pygen.stmt("...")]` for bodies. (`_` prefix silences ARG005 on unused lambda params.)
- Removed `TODO(cst-protocol-generator-refactor)` comment block (3 lines) from `protocol_annotation_for_model_types`.
- `TODO.md`: removed `cst-protocol-generator-refactor` entry.
- Generated output byte-identical for all in-tree grammars (only `gsm2tree.py` changed among Python files after `make gencode`; all 947 tests pass; ruff and pyright clean).
