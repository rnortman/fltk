"""Generator unit tests for CstGenerator (gsm2tree.py).

Tests validate AST-level output of py_class_for_model, not compiled execution.
"""

from __future__ import annotations

import ast

import pytest

import fltk.fegen.gsm2tree as gsm2tree_mod
from fltk.fegen import gsm
from tests.gsm2tree_helpers import make_generator as _make_generator
from tests.gsm2tree_helpers import make_labeled_grammar as _make_labeled_grammar
from tests.gsm2tree_helpers import make_zero_label_grammar as _make_zero_label_grammar


def _get_class_def(stmts: list[ast.stmt], name: str) -> ast.ClassDef:
    for stmt in stmts:
        if isinstance(stmt, ast.ClassDef) and stmt.name == name:
            return stmt
    msg = f"ClassDef {name!r} not found in stmts"
    raise AssertionError(msg)


def _find_nested_class(klass: ast.ClassDef, name: str) -> ast.ClassDef | None:
    for stmt in klass.body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == name:
            return stmt
    return None


def _find_function(klass: ast.ClassDef, name: str) -> ast.FunctionDef | None:
    for stmt in klass.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == name:
            return stmt
    return None


def _annotation_source(annotation: ast.expr | None) -> str:
    """Return the source text of an annotation AST node."""
    if annotation is None:
        return ""
    return ast.unparse(annotation)


# ---------------------------------------------------------------------------
# Sub-task B: label-free concrete class shape
# ---------------------------------------------------------------------------


class TestLabelFreeConcreteClass:
    """py_class_for_model with a zero-label rule must match the Protocol/Rust reference.

    Required shape (per design §B):
    - No nested Label ClassDef.
    - children: list[tuple[None, T]]
    - child() -> tuple[None, T]
    - append / extend: label: None = None
    """

    @pytest.fixture(scope="class")
    def stmts(self) -> list[ast.stmt]:
        gen = _make_generator(_make_zero_label_grammar())
        model = gen.rule_models["foo"]
        return gen.py_class_for_model("Foo", model, "foo")

    @pytest.fixture(scope="class")
    def klass(self, stmts: list[ast.stmt]) -> ast.ClassDef:
        return _get_class_def(stmts, "Foo")

    def test_no_label_class(self, klass: ast.ClassDef) -> None:
        """Label-free node must NOT emit a nested Label enum."""
        label_cls = _find_nested_class(klass, "Label")
        assert label_cls is None, "Label-free node should not have a nested Label ClassDef"

    def test_children_annotation_none_tuple(self, klass: ast.ClassDef) -> None:
        """children field annotation must be list[tuple[None, T]] (not Optional[Label])."""
        src = ast.unparse(klass)
        assert "tuple[None," in src, f"Expected tuple[None, ...] in children annotation; got:\n{src}"
        assert "Optional[Label]" not in src, f"Label-free node must not use Optional[Label]:\n{src}"

    def test_append_label_is_none(self, klass: ast.ClassDef) -> None:
        """append() label param must be annotated None=None (no Optional[Label])."""
        append_fn = _find_function(klass, "append")
        assert append_fn is not None, "append function not found"
        fn_src = ast.unparse(append_fn)
        # ast.unparse may or may not include a space around =; check for the annotation type "None"
        assert "label: None" in fn_src, f"Expected 'label: None' in append; got:\n{fn_src}"
        assert "Optional[Label]" not in fn_src

    def test_extend_label_is_none(self, klass: ast.ClassDef) -> None:
        """extend() label param must be annotated None=None (no Optional[Label])."""
        extend_fn = _find_function(klass, "extend")
        assert extend_fn is not None, "extend function not found"
        fn_src = ast.unparse(extend_fn)
        assert "label: None" in fn_src, f"Expected 'label: None' in extend; got:\n{fn_src}"
        assert "Optional[Label]" not in fn_src

    def test_child_return_is_none_tuple(self, klass: ast.ClassDef) -> None:
        """child() return annotation must be tuple[None, T]."""
        child_fn = _find_function(klass, "child")
        assert child_fn is not None, "child function not found"
        ret_src = _annotation_source(child_fn.returns)
        assert ret_src.startswith("tuple[None,"), f"Expected tuple[None, ...] return; got: {ret_src}"
        assert "Optional[Label]" not in ret_src

    def test_no_post_class_label_assignments(self, stmts: list[ast.stmt]) -> None:
        """No post-class Label canonical-name assignment stmts for zero-label node."""
        # Post-class stmts are ast.Expr/ast.Assign with Foo.Label.X._fltk_canonical_name
        for stmt in stmts[1:]:
            src = ast.unparse(stmt)
            assert "Label" not in src, f"Unexpected Label assignment for zero-label node: {src}"

    def test_extend_children_present(self, klass: ast.ClassDef) -> None:
        """extend_children must be present and correctly shaped on a label-free node."""
        fn = _find_function(klass, "extend_children")
        assert fn is not None, "extend_children not found on label-free node"
        fn_src = ast.unparse(fn)
        # Parameter must be typed with the class forward-ref, not Label-annotated
        assert "other: 'Foo'" in fn_src, f"Expected 'other: \\'Foo\\'' in extend_children; got:\n{fn_src}"
        # Return type must be None
        assert _annotation_source(fn.returns) == "None", (
            f"extend_children must return None; got: {_annotation_source(fn.returns)}"
        )


# ---------------------------------------------------------------------------
# Sub-task B: label-bearing node unchanged
# ---------------------------------------------------------------------------


class TestLabelBearingConcreteClassUnchanged:
    """Label-bearing nodes must still emit Label enum and Optional[Label] annotations."""

    @pytest.fixture(scope="class")
    def stmts(self) -> list[ast.stmt]:
        gen = _make_generator(_make_labeled_grammar())
        model = gen.rule_models["bar"]
        return gen.py_class_for_model("Bar", model, "bar")

    @pytest.fixture(scope="class")
    def klass(self, stmts: list[ast.stmt]) -> ast.ClassDef:
        return _get_class_def(stmts, "Bar")

    def test_has_label_class(self, klass: ast.ClassDef) -> None:
        """Label-bearing node must have a nested Label ClassDef."""
        label_cls = _find_nested_class(klass, "Label")
        assert label_cls is not None, "Label-bearing node must have a nested Label ClassDef"

    def test_children_annotation_optional_label(self, klass: ast.ClassDef) -> None:
        """children field annotation must use Optional[Label]."""
        src = ast.unparse(klass)
        assert "Optional[Label]" in src, f"Label-bearing node must use Optional[Label]:\n{src}"

    def test_append_label_optional(self, klass: ast.ClassDef) -> None:
        """append() label param must be Optional[Label] = None for labeled nodes."""
        append_fn = _find_function(klass, "append")
        assert append_fn is not None
        fn_src = ast.unparse(append_fn)
        assert "Optional[Label]" in fn_src

    def test_per_label_methods_present(self, klass: ast.ClassDef) -> None:
        """Label-bearing node must have append_name, extend_name, children_name, child_name, maybe_name."""
        for method in ("append_name", "extend_name", "children_name", "child_name", "maybe_name"):
            fn = _find_function(klass, method)
            assert fn is not None, f"Missing per-label method: {method}"

    def test_child_name_return_annotation(self, klass: ast.ClassDef) -> None:
        """child_name must return the labeled child type (not Optional[...])."""
        fn = _find_function(klass, "child_name")
        assert fn is not None, "child_name not found"
        ret = _annotation_source(fn.returns)
        assert not ret.startswith("typing.Optional["), (
            f"child_name should return the bare child type, not Optional; got: {ret}"
        )
        assert ret, "child_name must have a return annotation"

    def test_maybe_name_return_annotation(self, klass: ast.ClassDef) -> None:
        """maybe_name must return Optional[child_type]."""
        fn = _find_function(klass, "maybe_name")
        assert fn is not None, "maybe_name not found"
        ret = _annotation_source(fn.returns)
        assert ret.startswith("typing.Optional["), f"maybe_name should return Optional[...]; got: {ret}"


# ---------------------------------------------------------------------------
# Sub-task A: __all__ in the generated protocol module
# ---------------------------------------------------------------------------


def _make_simple_grammar() -> gsm.Grammar:
    """Grammar with two rules (alpha and beta) for __all__ content testing."""
    alpha_rule = gsm.Rule(
        name="alpha",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="val",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("a"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    beta_rule = gsm.Rule(
        name="beta",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="val",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Literal("b"),
                        quantifier=gsm.REQUIRED,
                    ),
                ],
                sep_after=[gsm.Separator.NO_WS],
            ),
        ],
    )
    return gsm.Grammar(
        rules=(alpha_rule, beta_rule),
        identifiers={"alpha": alpha_rule, "beta": beta_rule},
    )


class TestProtocolModuleAll:
    """gen_protocol_module must emit a module-level __all__ with the correct contents."""

    @pytest.fixture(scope="class")
    def protocol_ast(self) -> ast.Module:
        grammar = _make_simple_grammar()
        gen = _make_generator(grammar)
        return gen.gen_protocol_module()

    def _find_all_assign(self, module: ast.Module) -> ast.Assign | None:
        for stmt in module.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        return stmt
        return None

    def test_all_is_present(self, protocol_ast: ast.Module) -> None:
        """Protocol module must have a module-level __all__ assignment."""
        assign = self._find_all_assign(protocol_ast)
        assert assign is not None, "__all__ assignment not found in generated protocol module"

    def test_all_contains_protocol_node_names(self, protocol_ast: ast.Module) -> None:
        """__all__ must include the Protocol node class name for every grammar rule."""
        assign = self._find_all_assign(protocol_ast)
        assert assign is not None
        # Extract the list literal values
        assert isinstance(assign.value, ast.List)
        all_names = {elt.s for elt in assign.value.elts if isinstance(elt, ast.Constant)}  # type: ignore[attr-defined]
        assert "Alpha" in all_names, f"Expected 'Alpha' in __all__; got: {all_names}"
        assert "Beta" in all_names, f"Expected 'Beta' in __all__; got: {all_names}"

    def test_all_contains_fixed_names(self, protocol_ast: ast.Module) -> None:
        """__all__ must include NodeKind, Span, and CstModule."""
        assign = self._find_all_assign(protocol_ast)
        assert assign is not None
        assert isinstance(assign.value, ast.List)
        all_names = {elt.s for elt in assign.value.elts if isinstance(elt, ast.Constant)}  # type: ignore[attr-defined]
        for name in ("NodeKind", "Span", "CstModule"):
            assert name in all_names, f"Expected '{name}' in __all__; got: {all_names}"

    def test_all_excludes_protocol_label_member(self, protocol_ast: ast.Module) -> None:
        """__all__ must NOT include _ProtocolLabelMember."""
        assign = self._find_all_assign(protocol_ast)
        assert assign is not None
        assert isinstance(assign.value, ast.List)
        all_names = {elt.s for elt in assign.value.elts if isinstance(elt, ast.Constant)}  # type: ignore[attr-defined]
        assert "_ProtocolLabelMember" not in all_names, (
            "_ProtocolLabelMember must not appear in __all__ (it is a private helper)"
        )

    def test_protocol_label_member_still_present_as_classdef(self, protocol_ast: ast.Module) -> None:
        """_ProtocolLabelMember must still be present as a ClassDef (still importable by name)."""
        class_names = {node.name for node in protocol_ast.body if isinstance(node, ast.ClassDef)}
        assert "_ProtocolLabelMember" in class_names, (
            "_ProtocolLabelMember ClassDef must remain in the module body (still importable by explicit name)"
        )

    def test_all_is_sorted(self, protocol_ast: ast.Module) -> None:
        """__all__ list must be sorted for deterministic output."""
        assign = self._find_all_assign(protocol_ast)
        assert assign is not None
        assert isinstance(assign.value, ast.List)
        all_names = [elt.s for elt in assign.value.elts if isinstance(elt, ast.Constant)]  # type: ignore[attr-defined]
        assert all_names == sorted(all_names), f"__all__ is not sorted: {all_names}"

    def test_all_appears_near_top(self, protocol_ast: ast.Module) -> None:
        """__all__ must immediately follow the last import / TYPE_CHECKING block.

        Structural invariant: the statement directly before __all__ must be an import
        or a typing.TYPE_CHECKING if-block.  A magic-constant position check cannot
        verify this contract.
        """

        def _is_import_or_type_checking(stmt: ast.stmt) -> bool:
            if isinstance(stmt, ast.ImportFrom | ast.Import):
                return True
            if (
                isinstance(stmt, ast.If)
                and isinstance(stmt.test, ast.Attribute)
                and isinstance(stmt.test.value, ast.Name)
                and stmt.test.value.id == "typing"
                and stmt.test.attr == "TYPE_CHECKING"
            ):
                return True
            return False

        all_idx: int | None = None
        for i, stmt in enumerate(protocol_ast.body):
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        all_idx = i
                        break
            if all_idx is not None:
                break

        assert all_idx is not None, "__all__ not found in the generated protocol module"
        assert all_idx > 0, "__all__ must not be the very first statement"
        prev_stmt = protocol_ast.body[all_idx - 1]
        assert _is_import_or_type_checking(prev_stmt), (
            f"__all__ must immediately follow an import or TYPE_CHECKING block, "
            f"but the preceding statement is: {ast.unparse(prev_stmt)}"
        )


# ---------------------------------------------------------------------------
# Sub-task C: _emit_label_quintet ValueError guard
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Named mutators (insert / remove_at / replace_at / clear) emission
# ---------------------------------------------------------------------------


class TestMutatorsEmittedPyConcreteClass:
    """py_class_for_model emits all four named mutators with correct signatures."""

    @pytest.fixture(scope="class")
    def labeled_stmts(self) -> list[ast.stmt]:
        gen = _make_generator(_make_labeled_grammar())
        model = gen.rule_models["bar"]
        return gen.py_class_for_model("Bar", model, "bar")

    @pytest.fixture(scope="class")
    def labeled_klass(self, labeled_stmts: list[ast.stmt]) -> ast.ClassDef:
        return _get_class_def(labeled_stmts, "Bar")

    @pytest.fixture(scope="class")
    def zero_label_stmts(self) -> list[ast.stmt]:
        gen = _make_generator(_make_zero_label_grammar())
        model = gen.rule_models["foo"]
        return gen.py_class_for_model("Foo", model, "foo")

    @pytest.fixture(scope="class")
    def zero_label_klass(self, zero_label_stmts: list[ast.stmt]) -> ast.ClassDef:
        return _get_class_def(zero_label_stmts, "Foo")

    def test_insert_present_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """insert is emitted on a labeled node."""
        fn = _find_function(labeled_klass, "insert")
        assert fn is not None, "insert not found on labeled node"

    def test_remove_at_present_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """remove_at is emitted on a labeled node."""
        fn = _find_function(labeled_klass, "remove_at")
        assert fn is not None, "remove_at not found on labeled node"

    def test_replace_at_present_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """replace_at is emitted on a labeled node."""
        fn = _find_function(labeled_klass, "replace_at")
        assert fn is not None, "replace_at not found on labeled node"

    def test_clear_present_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """clear is emitted on a labeled node."""
        fn = _find_function(labeled_klass, "clear")
        assert fn is not None, "clear not found on labeled node"

    def test_insert_present_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """insert is emitted on a label-free node."""
        fn = _find_function(zero_label_klass, "insert")
        assert fn is not None, "insert not found on label-free node"

    def test_remove_at_present_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """remove_at is emitted on a label-free node."""
        fn = _find_function(zero_label_klass, "remove_at")
        assert fn is not None, "remove_at not found on label-free node"

    def test_replace_at_present_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """replace_at is emitted on a label-free node."""
        fn = _find_function(zero_label_klass, "replace_at")
        assert fn is not None, "replace_at not found on label-free node"

    def test_clear_present_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """clear is emitted on a label-free node."""
        fn = _find_function(zero_label_klass, "clear")
        assert fn is not None, "clear not found on label-free node"

    def test_insert_index_param_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """insert first param (after self) is 'index: int'."""
        fn = _find_function(labeled_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert "index: int" in fn_src, f"Expected 'index: int' in insert; got:\n{fn_src}"

    def test_insert_label_param_optional_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """insert label param is 'Optional[Label] = None' for labeled nodes."""
        fn = _find_function(labeled_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert "Optional[Label]" in fn_src, f"Expected 'Optional[Label]' in insert; got:\n{fn_src}"

    def test_insert_label_param_none_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """insert label param is 'None = None' for label-free nodes."""
        fn = _find_function(zero_label_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert "label: None" in fn_src, f"Expected 'label: None' in insert; got:\n{fn_src}"

    def test_insert_returns_none(self, labeled_klass: ast.ClassDef) -> None:
        """insert returns None."""
        fn = _find_function(labeled_klass, "insert")
        assert fn is not None
        assert _annotation_source(fn.returns) == "None", (
            f"insert must return None; got: {_annotation_source(fn.returns)}"
        )

    def test_remove_at_returns_tuple_labeled(self, labeled_klass: ast.ClassDef) -> None:
        """remove_at returns tuple[Optional[Label], <child>] for labeled nodes."""
        fn = _find_function(labeled_klass, "remove_at")
        assert fn is not None
        ret = _annotation_source(fn.returns)
        assert ret.startswith("tuple["), f"remove_at must return a tuple; got: {ret}"
        assert "Optional[Label]" in ret, f"remove_at return must include Optional[Label]; got: {ret}"

    def test_remove_at_returns_tuple_zero_label(self, zero_label_klass: ast.ClassDef) -> None:
        """remove_at returns tuple[None, <child>] for label-free nodes."""
        fn = _find_function(zero_label_klass, "remove_at")
        assert fn is not None
        ret = _annotation_source(fn.returns)
        assert ret.startswith("tuple[None,"), f"remove_at must return tuple[None, ...] for label-free node; got: {ret}"

    def test_remove_at_has_no_extra_params(self, labeled_klass: ast.ClassDef) -> None:
        """remove_at takes only (self, index: int) — no child or label param."""
        fn = _find_function(labeled_klass, "remove_at")
        assert fn is not None
        # The only params besides self must be 'index'.
        param_names = [arg.arg for arg in fn.args.args if arg.arg != "self"]
        assert param_names == ["index"], f"remove_at must take only 'index'; got: {param_names}"

    def test_replace_at_returns_none(self, labeled_klass: ast.ClassDef) -> None:
        """replace_at returns None."""
        fn = _find_function(labeled_klass, "replace_at")
        assert fn is not None
        assert _annotation_source(fn.returns) == "None", (
            f"replace_at must return None; got: {_annotation_source(fn.returns)}"
        )

    def test_clear_takes_only_self(self, labeled_klass: ast.ClassDef) -> None:
        """clear takes only self."""
        fn = _find_function(labeled_klass, "clear")
        assert fn is not None
        param_names = [arg.arg for arg in fn.args.args if arg.arg != "self"]
        assert param_names == [], f"clear must take no arguments besides self; got: {param_names}"

    def test_clear_returns_none(self, labeled_klass: ast.ClassDef) -> None:
        """clear returns None."""
        fn = _find_function(labeled_klass, "clear")
        assert fn is not None
        assert _annotation_source(fn.returns) == "None", (
            f"clear must return None; got: {_annotation_source(fn.returns)}"
        )


class TestMutatorsEmittedPyProtocol:
    """Protocol stubs for all four named mutators are emitted in the protocol class."""

    @pytest.fixture(scope="class")
    def protocol_klass(self) -> ast.ClassDef:
        gen = _make_generator(_make_labeled_grammar())
        model = gen.rule_models["bar"]
        # _protocol_class_for_model returns the ClassDef directly.
        return gen._protocol_class_for_model("Bar", model, "bar")

    def test_insert_present_protocol(self, protocol_klass: ast.ClassDef) -> None:
        fn = _find_function(protocol_klass, "insert")
        assert fn is not None, "insert not found on protocol class"

    def test_remove_at_present_protocol(self, protocol_klass: ast.ClassDef) -> None:
        fn = _find_function(protocol_klass, "remove_at")
        assert fn is not None, "remove_at not found on protocol class"

    def test_replace_at_present_protocol(self, protocol_klass: ast.ClassDef) -> None:
        fn = _find_function(protocol_klass, "replace_at")
        assert fn is not None, "replace_at not found on protocol class"

    def test_clear_present_protocol(self, protocol_klass: ast.ClassDef) -> None:
        fn = _find_function(protocol_klass, "clear")
        assert fn is not None, "clear not found on protocol class"

    def test_insert_signatures_match_concrete(self, protocol_klass: ast.ClassDef) -> None:
        """Protocol insert has same signature shape as concrete insert."""
        fn = _find_function(protocol_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert "index: int" in fn_src
        assert "Optional[Label]" in fn_src

    def test_remove_at_returns_tuple_protocol(self, protocol_klass: ast.ClassDef) -> None:
        """Protocol remove_at returns a tuple (matches concrete)."""
        fn = _find_function(protocol_klass, "remove_at")
        assert fn is not None
        ret = _annotation_source(fn.returns)
        assert ret.startswith("tuple["), f"Protocol remove_at must return a tuple; got: {ret}"

    def test_mutators_between_child_and_per_label(self, protocol_klass: ast.ClassDef) -> None:
        """Protocol mutators appear between child and the per-label quintet (§2.4 ordering)."""
        klass = protocol_klass
        method_names = [stmt.name for stmt in klass.body if isinstance(stmt, ast.FunctionDef)]
        # child, insert, remove_at, replace_at, clear must all precede the per-label methods
        # per-label methods start with append_name for the labeled fixture grammar
        assert "child" in method_names
        assert "insert" in method_names
        idx_child = method_names.index("child")
        idx_insert = method_names.index("insert")
        idx_remove = method_names.index("remove_at")
        idx_replace = method_names.index("replace_at")
        idx_clear = method_names.index("clear")
        idx_append_name = method_names.index("append_name")
        assert idx_child < idx_insert, "insert must come after child"
        assert idx_insert < idx_remove, "remove_at must come after insert"
        assert idx_remove < idx_replace, "replace_at must come after remove_at"
        assert idx_replace < idx_clear, "clear must come after replace_at"
        assert idx_clear < idx_append_name, "per-label methods must come after clear"


class TestMutatorNoLabelCollision:
    """Reserved-name regression: no per-label prefix can equal any fixed mutator name."""

    def test_no_per_label_prefix_collides_with_insert(self) -> None:
        """A label named 'insert' would produce method 'append_insert'; the base name 'insert' is a fixed method."""
        # Per-label prefixes: append_, extend_, children_, child_, maybe_
        # None of these produce a bare name that equals insert/remove_at/replace_at/clear.
        fixed_names = {"insert", "remove_at", "replace_at", "clear"}
        per_label_prefixes = ("append_", "extend_", "children_", "child_", "maybe_")
        for label in fixed_names:
            for prefix in per_label_prefixes:
                generated = f"{prefix}{label}"
                assert generated not in fixed_names, (
                    f"Per-label method '{generated}' (from label '{label}' + prefix '{prefix}') "
                    f"would collide with fixed mutator name"
                )

    def test_fixed_mutator_names_not_in_reserved_labels(self) -> None:
        """The _RESERVED_LABELS dict in gsm2tree_rs contains only 'children'; mutator names are safe."""
        import fltk.fegen.gsm2tree_rs as gsm2tree_rs_mod  # noqa: PLC0415

        reserved = set(gsm2tree_rs_mod._RESERVED_LABELS.keys())
        # Per-label methods: for label L, methods are append_L, extend_L, children_L, child_L, maybe_L.
        # These all have underscores, so bare names "insert", "remove_at", "replace_at", "clear" are never produced.
        # Confirm none of the fixed mutator names can come from a label:
        fixed_mutator_names = {"insert", "remove_at", "replace_at", "clear"}
        per_label_prefixes = ("append_", "extend_", "children_", "child_", "maybe_")
        for lbl in reserved:
            for prefix in per_label_prefixes:
                generated = f"{prefix}{lbl}"
                assert generated not in fixed_mutator_names


def test_emit_label_quintet_unknown_method_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """concrete_body_for must raise ValueError for unrecognised method names.

    The guard is a local closure inside py_class_for_model; we force its execution
    by monkey-patching _emit_label_quintet to make one extra body_for call with an
    unknown method name after the real quintet, so the closure is in scope and callable.
    """
    gen = _make_generator(_make_labeled_grammar())

    original_quintet = gsm2tree_mod.CstGenerator._emit_label_quintet

    raised: list[Exception] = []

    def patched_quintet(self: gsm2tree_mod.CstGenerator, *, labels, annotation_for, body_for):  # type: ignore[type-arg]
        result = original_quintet(self, labels=labels, annotation_for=annotation_for, body_for=body_for)
        if labels:
            try:
                body_for("nonexistent_method", labels[0])  # type: ignore[arg-type]
            except ValueError as exc:
                raised.append(exc)
        return result

    monkeypatch.setattr(gsm2tree_mod.CstGenerator, "_emit_label_quintet", patched_quintet)

    model = gen.rule_models["bar"]
    gen.py_class_for_model("Bar", model, "bar")

    assert raised, "Expected ValueError from concrete_body_for with unknown method; none raised"
    assert "Unknown method" in str(raised[0])
