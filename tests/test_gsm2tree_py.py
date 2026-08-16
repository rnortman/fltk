"""Generator unit tests for CstGenerator (gsm2tree.py).

Tests validate AST-level output of py_class_for_model, not compiled execution.
"""

from __future__ import annotations

import ast

import pytest

import fltk.fegen.gsm2tree as gsm2tree_mod
from fltk.fegen import fltk_cst, fltk_cst_protocol, gsm
from tests.gsm2tree_helpers import make_generator as _make_generator
from tests.gsm2tree_helpers import make_labeled_grammar as _make_labeled_grammar
from tests.gsm2tree_helpers import make_multi_label_grammar as _make_multi_label_grammar
from tests.gsm2tree_helpers import make_rule_ref_grammar as _rule_ref_grammar
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

    Required shape:
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

    def test_no_children_snapshot_helper(self, klass: ast.ClassDef) -> None:
        """The snapshot helper's signature names `Foo.Label`, which a label-free node lacks."""
        assert _find_function(klass, "_children_snapshot") is None
        assert "_children_snapshot" not in ast.unparse(klass)

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
        assert f"other: {gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo" in fn_src, (
            f"Expected the protocol-typed 'other' param in extend_children; got:\n{fn_src}"
        )
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

    def test_append_label_is_the_agnostic_label(self, klass: ast.ClassDef) -> None:
        """append() takes any conforming backend's label, not just this class's enum."""
        append_fn = _find_function(klass, "append")
        assert append_fn is not None
        fn_src = ast.unparse(append_fn)
        assert f"label: typing.Optional[{gsm2tree_mod.LABEL_PROTOCOL_ANNOTATION}]" in fn_src, fn_src

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


class TestConcreteModuleSharesNodeKind:
    """The concrete module takes NodeKind from its protocol module instead of defining one.

    One enum means a concrete node's ``kind: typing.Literal[NodeKind.X]`` is the *same* type as its
    protocol counterpart's, which is what protocol-attribute invariance demands, and it makes
    ``cst.NodeKind.X`` and ``cstp.NodeKind.X`` the same object rather than two bridged singletons.
    """

    @pytest.fixture(scope="class")
    def module_ast(self) -> ast.Module:
        return _make_generator(_make_simple_grammar()).gen_py_module("pkg.simple_cst_protocol")

    def test_node_kind_is_imported_from_the_named_protocol_module(self, module_ast: ast.Module) -> None:
        imports = [ast.unparse(stmt) for stmt in module_ast.body if isinstance(stmt, ast.ImportFrom)]
        assert "from pkg.simple_cst_protocol import NodeKind" in imports, imports

    def test_the_import_precedes_every_non_import_statement(self, module_ast: ast.Module) -> None:
        """Emitted with the imports, so the module has no E402 to fix up after generation."""
        first_other = next(
            i for i, stmt in enumerate(module_ast.body) if not isinstance(stmt, ast.Import | ast.ImportFrom)
        )
        node_kind_import = next(
            i
            for i, stmt in enumerate(module_ast.body)
            if isinstance(stmt, ast.ImportFrom) and any(alias.name == "NodeKind" for alias in stmt.names)
        )
        assert node_kind_import < first_other

    def test_no_node_kind_class_is_defined(self, module_ast: ast.Module) -> None:
        class_names = {stmt.name for stmt in module_ast.body if isinstance(stmt, ast.ClassDef)}
        assert "NodeKind" not in class_names, class_names

    def test_no_canonical_name_assignments_are_emitted(self, module_ast: ast.Module) -> None:
        """The protocol module owns the members, so it owns their canonical-name assignments."""
        source = ast.unparse(module_ast)
        assert "_fltk_canonical_name = 'NodeKind." not in source, source

    def test_kind_fields_still_default_to_the_shared_members(self, module_ast: ast.Module) -> None:
        source = ast.unparse(module_ast)
        assert "kind: typing.Literal[NodeKind.ALPHA] = NodeKind.ALPHA" in source, source

    def test_a_committed_pair_shares_one_enum_object_at_runtime(self) -> None:
        assert fltk_cst.NodeKind is fltk_cst_protocol.NodeKind
        assert fltk_cst.NodeKind.GRAMMAR is fltk_cst_protocol.NodeKind.GRAMMAR
        assert fltk_cst.Grammar().kind is fltk_cst_protocol.NodeKind.GRAMMAR


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

    def test_insert_label_param_is_the_agnostic_label(self, labeled_klass: ast.ClassDef) -> None:
        """insert takes any conforming backend's label; the isinstance guard rejects a foreign one."""
        fn = _find_function(labeled_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert f"label: typing.Optional[{gsm2tree_mod.LABEL_PROTOCOL_ANNOTATION}]" in fn_src, fn_src

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
        return gen._protocol_class_for_model("Bar", model, "bar", emit_kind_literal=True)

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
        """Protocol insert has same signature shape as concrete insert, over the agnostic label."""
        fn = _find_function(protocol_klass, "insert")
        assert fn is not None
        fn_src = ast.unparse(fn)
        assert "index: int" in fn_src
        assert f"Optional[{gsm2tree_mod.LABEL_PROTOCOL_ANNOTATION}]" in fn_src

    def test_remove_at_returns_tuple_protocol(self, protocol_klass: ast.ClassDef) -> None:
        """Protocol remove_at returns a tuple (matches concrete)."""
        fn = _find_function(protocol_klass, "remove_at")
        assert fn is not None
        ret = _annotation_source(fn.returns)
        assert ret.startswith("tuple["), f"Protocol remove_at must return a tuple; got: {ret}"

    def test_mutators_between_child_and_per_label(self, protocol_klass: ast.ClassDef) -> None:
        """Protocol mutators appear between child and the per-label quintet."""
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

    def patched_quintet(self: gsm2tree_mod.CstGenerator, *, labels, annotation_for, body_for, **kwargs):  # type: ignore[type-arg]
        result = original_quintet(self, labels=labels, annotation_for=annotation_for, body_for=body_for, **kwargs)
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


class TestWidenedMutatorInputs:
    """Concrete mutator *inputs* name the protocol surface; every read stays concrete.

    This is the annotation half of the conformance package: a concrete node can only satisfy its
    protocol counterpart if its mutator parameters accept what the protocol's do (parameters are
    contravariant), so `append`, `extend`, `insert`, `replace_at`, `extend_children` and the
    per-label pair take protocol node types and `LabelProtocol`.  Widening a parameter is
    non-breaking for downstream callers, and the runtime isinstance guards still reject a
    foreign-backend argument — but only if the widening is confined to the input side, which is
    what the accessor assertions below pin.
    """

    @pytest.fixture(scope="class")
    @staticmethod
    def klass() -> ast.ClassDef:
        gen = _make_generator(_rule_ref_grammar(labeled=True))
        return _get_class_def(gen.py_class_for_model("Baz", gen.rule_models["baz"], "baz"), "Baz")

    @pytest.fixture(scope="class")
    @staticmethod
    def span_only_klass() -> ast.ClassDef:
        """A node whose only children are spans: nothing on it can name another node's class."""
        gen = _make_generator(_make_zero_label_grammar())
        return _get_class_def(gen.py_class_for_model("Foo", gen.rule_models["foo"], "foo"), "Foo")

    @staticmethod
    def _param(klass: ast.ClassDef, method: str, param: str) -> str:
        fn = _find_function(klass, method)
        assert fn is not None, f"{method} not found"
        arg = next((a for a in fn.args.args if a.arg == param), None)
        assert arg is not None, f"{method} has no {param!r} parameter"
        return _annotation_source(arg.annotation)

    @pytest.mark.parametrize("method", ["append", "insert", "replace_at"])
    def test_the_child_param_is_the_protocol_node_type(self, klass: ast.ClassDef, method: str) -> None:
        assert self._param(klass, method, "child") == f"{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo"

    def test_extend_takes_an_iterable_of_protocol_nodes(self, klass: ast.ClassDef) -> None:
        assert self._param(klass, "extend", "children") == (
            f"typing.Iterable[{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo]"
        )

    def test_extend_children_takes_this_class_protocol_counterpart(self, klass: ast.ClassDef) -> None:
        assert self._param(klass, "extend_children", "other") == f"{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Baz"

    def test_the_per_label_mutators_widen_too(self, klass: ast.ClassDef) -> None:
        assert self._param(klass, "append_inner", "child") == f"{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo"
        assert self._param(klass, "extend_inner", "children") == (
            f"typing.Iterable[{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo]"
        )

    def test_the_runtime_guards_take_the_widened_types(self, klass: ast.ClassDef) -> None:
        """The guards are what turns a statically accepted foreign node into a TypeError."""
        assert self._param(klass, "_check_child_type_for_mutators", "child") == (
            f"{gsm2tree_mod.PROTOCOL_MODULE_ALIAS}.Foo"
        )
        assert self._param(klass, "_check_label_type_for_mutators", "label") == (
            f"typing.Optional[{gsm2tree_mod.LABEL_PROTOCOL_ANNOTATION}]"
        )

    @pytest.mark.parametrize("method", ["children_inner", "child_inner", "maybe_inner", "inner"])
    def test_every_accessor_still_returns_the_concrete_class(self, klass: ast.ClassDef, method: str) -> None:
        """Reads stay concrete, so no downstream annotation churn on the accessor surface."""
        fn = _find_function(klass, method)
        assert fn is not None, f"{method} not found"
        ret = _annotation_source(fn.returns)
        assert gsm2tree_mod.PROTOCOL_MODULE_ALIAS not in ret, ret
        assert "Foo" in ret, ret

    @pytest.mark.parametrize("method", ["child", "remove_at"])
    def test_child_and_remove_at_still_return_the_concrete_entry(self, klass: ast.ClassDef, method: str) -> None:
        fn = _find_function(klass, method)
        assert fn is not None, f"{method} not found"
        ret = _annotation_source(fn.returns)
        assert ret == "tuple[typing.Optional[Label], 'Foo']", ret

    def test_the_children_field_stays_concrete(self, klass: ast.ClassDef) -> None:
        """The stored entries keep their concrete types; only what may be handed in widens."""
        field = next(
            stmt
            for stmt in klass.body
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "children"
        )
        assert _annotation_source(field.annotation) == "list[tuple[typing.Optional[Label], 'Foo']]"

    @pytest.mark.parametrize("method", ["append", "extend", "insert", "replace_at"])
    def test_a_span_only_node_names_no_protocol_class(self, span_only_klass: ast.ClassDef, method: str) -> None:
        """Span children are already backend-agnostic (`SpanProtocol`), so nothing widens.

        `extend_children` is the exception and is checked separately: its argument is this node's
        own protocol class whatever the children are.
        """
        fn = _find_function(span_only_klass, method)
        assert fn is not None, f"{method} not found"
        source = ast.unparse(fn)
        assert gsm2tree_mod.PROTOCOL_MODULE_ALIAS not in source, source
        assert "fltk.fegen.pyrt.span_protocol.SpanProtocol" in source, source
        assert "label: None" in source, source


class TestMutatorEntryShapes:
    """Every mutator builds its children entry from the two checkers' returns, never from a raw
    argument, so no entry needs a ``typing.Any`` escape hatch.

    Both checkers declare concrete returns — the node's own child union and its own ``Label`` — so
    the entry's arity, its label slot and its element type stay checked by pyright inside every
    generated module.  The generic mutators inline the label fast path (one isinstance against a
    constant) and call ``_check_label_type_for_mutators`` only on the miss, because the generated
    parser appends every trivia child through the generic ``append``.
    """

    _GRAMMARS = (
        (_make_zero_label_grammar(), "foo", "Foo", False),
        (_make_labeled_grammar(), "bar", "Bar", True),
        (_rule_ref_grammar(labeled=False), "baz", "Baz", False),
        (_rule_ref_grammar(labeled=True), "baz", "Baz", True),
    )

    @staticmethod
    def _method_source(grammar: gsm.Grammar, rule_name: str, class_name: str, method: str = "append") -> str:
        gen = _make_generator(grammar)
        klass = _get_class_def(gen.py_class_for_model(class_name, gen.rule_models[rule_name], rule_name), class_name)
        fn = _find_function(klass, method)
        assert fn is not None, f"{method} not found on {class_name}"
        return ast.unparse(fn)

    @staticmethod
    def _label_check(class_name: str, *, labeled: bool, method: str) -> str:
        if labeled:
            return (
                f"checked_label = label if label is None or isinstance(label, {class_name}.Label)"
                f" else self._check_label_type_for_mutators(label, '{method}')"
            )
        return f"if label is not None:\n        self._check_label_type_for_mutators(label, '{method}')"

    @pytest.mark.parametrize("method", ["append", "extend", "insert", "replace_at"])
    def test_the_label_fast_path_is_inlined(self, method: str) -> None:
        """The miss-only call keeps the parser's append path at one isinstance and no call."""
        for grammar, rule, class_name, labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name, method=method)
            assert self._label_check(class_name, labeled=labeled, method=method) in src, (method, class_name, src)

    @pytest.mark.parametrize("method", ["append", "extend", "insert", "replace_at"])
    def test_the_label_is_checked_before_the_child(self, method: str) -> None:
        """One validation order on both backends: label, then child, then (where it exists) index."""
        for grammar, rule, class_name, _labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name, method=method)
            assert src.index("_check_label_type_for_mutators") < src.index("_check_child_type_for_mutators"), (
                method,
                class_name,
                src,
            )

    def test_append_stores_both_checkers_returns(self) -> None:
        for grammar, rule, class_name, labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name)
            label_expr = "checked_label" if labeled else "None"
            assert "checked_child = self._check_child_type_for_mutators(child)" in src, src
            assert f"self.children.append(({label_expr}, checked_child))" in src, src
            assert "typing.Any" not in src, src

    def test_extend_resolves_its_label_once_outside_the_comprehension(self) -> None:
        """Resolving per element would repeat the lookup; a bad label must abort before any read."""
        for grammar, rule, class_name, labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name, method="extend")
            label_expr = "checked_label" if labeled else "None"
            entries = f"[({label_expr}, self._check_child_type_for_mutators(child)) for child in children]"
            assert f"self.children.extend({entries})" in src, src
            assert "typing.Any" not in src, src

    @pytest.mark.parametrize("method", ["insert", "replace_at"])
    def test_the_strict_mutators_store_the_checked_child(self, method: str) -> None:
        """They build their entry from the checker's return, not from the raw protocol-typed child."""
        for grammar, rule, class_name, labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name, method=method)
            label_expr = "checked_label" if labeled else "None"
            stored = (
                f"self.children.insert(idx, ({label_expr}, checked_child))"
                if method == "insert"
                else f"self.children[norm] = ({label_expr}, checked_child)"
            )
            assert "checked_child = self._check_child_type_for_mutators(child)" in src, src
            assert stored in src, src
            assert "typing.Any" not in src, src

    def test_per_label_mutators_supply_the_member_and_check_the_child(self) -> None:
        span_labeled = self._method_source(_make_labeled_grammar(), "bar", "Bar", method="append_name")
        assert "self.children.append((Bar.Label.NAME, self._check_child_type_for_mutators(child)))" in span_labeled, (
            span_labeled
        )
        assert "typing.Any" not in span_labeled, span_labeled

        rule_ref = self._method_source(_rule_ref_grammar(labeled=True), "baz", "Baz", method="append_inner")
        assert "self.children.append((Baz.Label.INNER, self._check_child_type_for_mutators(child)))" in rule_ref, (
            rule_ref
        )
        assert "typing.Any" not in rule_ref, rule_ref

    def test_extend_children_narrows_other_before_reading_its_children(self) -> None:
        """`other: _cstp.Foo` is the protocol class, so without the guard `other.children` is a
        Sequence of protocol entries and the emitted extend is a pyright error in every generated
        module — a failure that only surfaces in the repo-wide gate over committed artifacts after
        a full `make gencode`.  The guard is load-bearing statically as well as at runtime.
        """
        for grammar, rule, class_name, _labeled in self._GRAMMARS:
            src = self._method_source(grammar, rule, class_name, method="extend_children")
            assert f"if not isinstance(other, {class_name}):" in src, src
            assert "self.children.extend(other.children)" in src, src
            assert "typing.Any" not in src, src


class TestChildCheckerShape:
    """``_check_child_type_for_mutators`` proves the concrete type and says so, isinstance first."""

    @staticmethod
    def _checker_source(grammar: gsm.Grammar, rule_name: str, class_name: str) -> ast.FunctionDef:
        gen = _make_generator(grammar)
        klass = _get_class_def(gen.py_class_for_model(class_name, gen.rule_models[rule_name], rule_name), class_name)
        fn = _find_function(klass, "_check_child_type_for_mutators")
        assert fn is not None, f"_check_child_type_for_mutators not found on {class_name}"
        return fn

    def test_the_return_type_is_the_concrete_child_union(self) -> None:
        """The isinstance guard proves membership in the concrete classes; the annotation says so.

        A protocol-typed return would push a `typing.Any` escape hatch into every entry every
        mutator builds, leaving the label slot, the tuple arity and the element type unchecked in
        every generated module.
        """
        fn = self._checker_source(_rule_ref_grammar(labeled=True), "baz", "Baz")
        ret = _annotation_source(fn.returns)
        assert gsm2tree_mod.PROTOCOL_MODULE_ALIAS not in ret, ret
        assert "Foo" in ret, ret

    def test_the_native_span_probe_is_off_the_success_path(self) -> None:
        """A resolvable child returns from the first isinstance; nothing else runs on that path.

        The checker is on the generated parser's construction path (every `append_<label>`), so the
        lazy `fltk._native` lookup must sit on the miss branch, not ahead of the isinstance.
        """
        fn = self._checker_source(_make_zero_label_grammar(), "foo", "Foo")
        src = ast.unparse(fn)
        first = ast.unparse(fn.body[0])
        assert first.startswith("if isinstance(child, "), first
        assert "return child" in first, first
        assert src.index("_get_native_span_type()") > src.index("return child"), src


class TestLabelCheckerShape:
    """``_check_label_type_for_mutators`` resolves a label to this node's own member.

    A label carries no backend-specific storage — its identity is the canonical name, already the
    cross-backend ``__eq__``/``__hash__`` key — so the checker matches by that name and returns the
    node's own member.  The fast path stays a bare isinstance: it is on the generated parser's
    construction path through every generic ``append``.
    """

    @staticmethod
    def _class_def(grammar: gsm.Grammar, rule_name: str, class_name: str) -> ast.ClassDef:
        gen = _make_generator(grammar)
        return _get_class_def(gen.py_class_for_model(class_name, gen.rule_models[rule_name], rule_name), class_name)

    def _checker(self, grammar: gsm.Grammar, rule_name: str, class_name: str) -> ast.FunctionDef:
        fn = _find_function(self._class_def(grammar, rule_name, class_name), "_check_label_type_for_mutators")
        assert fn is not None, f"_check_label_type_for_mutators not found on {class_name}"
        return fn

    def test_the_return_type_is_this_nodes_own_label(self) -> None:
        """A protocol-typed return would hatch the label slot of every mutator's entry."""
        fn = self._checker(_make_labeled_grammar(), "bar", "Bar")
        ret = _annotation_source(fn.returns)
        assert ret == "typing.Optional[Bar.Label]", ret

    def test_a_label_free_node_still_returns_none(self) -> None:
        fn = self._checker(_make_zero_label_grammar(), "foo", "Foo")
        assert _annotation_source(fn.returns) == "None"

    def test_the_canonical_name_lookup_is_off_the_success_path(self) -> None:
        """Own member and None return from the first branch; nothing else runs on that path."""
        fn = self._checker(_make_labeled_grammar(), "bar", "Bar")
        src = ast.unparse(fn)
        first = ast.unparse(fn.body[0])
        assert first.startswith("if label is None or isinstance(label, Bar.Label):"), first
        assert "return label" in first, first
        assert src.index("_fltk_canonical_name") > src.index("return label"), src

    def test_the_mapping_is_class_scoped_and_keyed_on_the_canonical_name(self) -> None:
        """Cross-class resolution is impossible by construction: each class carries its own map.

        Pinned on a three-label rule: a one-label rule cannot tell a correct name→member pairing
        from one that collapses every name onto the first member, and a mispairing silently
        relabels children on every multi-label node.
        """
        src = ast.unparse(self._class_def(_make_multi_label_grammar(), "bar", "Bar"))
        expected = (
            "_LABELS_BY_CANONICAL_NAME = types.MappingProxyType("
            "{'Bar.Label.NAME': Label.NAME, 'Bar.Label.TAIL': Label.TAIL, 'Bar.Label.VALUE': Label.VALUE})"
        )
        assert expected in src, src
        assert "Bar._LABELS_BY_CANONICAL_NAME.get(_canonical)" in src, src

    def test_the_lookup_only_accepts_a_string_canonical_name(self) -> None:
        """A dict lookup hashes anything; the Rust twin only ever extracts a `String`.

        Without the guard an unhashable canonical name raises `unhashable type` on this backend
        where the other backend raises the pinned TypeError.
        """
        fn = self._checker(_make_labeled_grammar(), "bar", "Bar")
        src = ast.unparse(fn)
        assert "if isinstance(_canonical, str):" in src, src
        assert src.index("isinstance(_canonical, str)") < src.index("_LABELS_BY_CANONICAL_NAME.get"), src
