"""Refactored unparser generator for FLTK grammars."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from fltk.fegen import gsm
from fltk.iir import model as iir
from fltk.iir.py import reg as pyreg
from fltk.unparse.combinators import (
    HARDLINE,
    LINE,
    NBSP,
    NIL,
    SOFTLINE,
    Concat,
    Doc,
    HardLine,
    Text,
)
from fltk.unparse.fmt_config import FormatterConfig, ItemSelector, Normal, Omit, OperationType, RenderAs

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext


class UnparserGenerator:
    """Generator for creating unparsers from FLTK grammars."""

    @dataclass
    class UnparserFn:
        name: str
        result_type: iir.Type

    def __init__(
        self,
        grammar: gsm.Grammar,
        context: CompilerContext,
        cst_module: str,
        formatter_config: FormatterConfig | None = None,
    ):
        self.grammar: Final = grammar
        self.context = context
        self.cst_module = cst_module
        self.formatter_config = formatter_config or FormatterConfig()

        self._setup_type_system()

        self.unparser_class = iir.ClassType.make(
            cname="Unparser",
            doc="Generated unparser for grammar",
            defined_in=iir.Module.make(name="TODO(module)"),
        )

        self._setup_unparser_class()

        # Track unparsers by path
        self.unparsers: dict[tuple[str, ...], UnparserGenerator.UnparserFn] = {}

        for rule in grammar.rules:
            rule_name = rule.name
            self._make_unparser_info(path=(rule_name,), result_type=self.maybe_unparse_result_type)

        self._gen_has_preservable_trivia_method()

        for rule in grammar.rules:
            self._generate_rule_unparser(rule)

    def _setup_type_system(self):
        """Set up all the types needed for unparsing."""
        doc_type = iir.Type.make(cname="Doc")
        type_info = pyreg.TypeInfo(
            typ=doc_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="Doc",
        )
        self.context.python_type_registry.register_type(type_info)
        self.doc_type = doc_type

        self.span_type = iir.Type.make(cname="Span")
        span_type_info = pyreg.TypeInfo(
            typ=self.span_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
            name="Span",
        )
        self.context.python_type_registry.register_type(span_type_info)

        self.unparse_result_type = iir.Type.make(cname="UnparseResult")
        unparse_result_type_info = pyreg.TypeInfo(
            typ=self.unparse_result_type,
            module=pyreg.Module(("fltk", "unparse", "pyrt")),
            name="UnparseResult",
        )
        self.context.python_type_registry.register_type(unparse_result_type_info)
        self.maybe_unparse_result_type = iir.Maybe.instantiate(value_type=self.unparse_result_type)

        self.doc_list_type = iir.GenericMutableSequence.instantiate(value_type=self.doc_type)
        doc_list_type_info = pyreg.TypeInfo(
            typ=self.doc_list_type,
            module=pyreg.Module(("collections", "abc")),
            name="MutableSequence",
        )
        self.context.python_type_registry.register_type(doc_list_type_info)

        self.doc_accumulator_type = iir.Type.make(cname="DocAccumulator")
        doc_accumulator_type_info = pyreg.TypeInfo(
            typ=self.doc_accumulator_type,
            module=pyreg.Module(("fltk", "unparse", "accumulator")),
            name="DocAccumulator",
        )
        self.context.python_type_registry.register_type(doc_accumulator_type_info)

        self.after_spec_type = iir.Type.make(cname="AfterSpec")
        after_spec_type_info = pyreg.TypeInfo(
            typ=self.after_spec_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="AfterSpec",
        )
        self.context.python_type_registry.register_type(after_spec_type_info)

        self.before_spec_type = iir.Type.make(cname="BeforeSpec")
        before_spec_type_info = pyreg.TypeInfo(
            typ=self.before_spec_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="BeforeSpec",
        )
        self.context.python_type_registry.register_type(before_spec_type_info)

        self.separator_spec_type = iir.Type.make(cname="SeparatorSpec")
        separator_spec_type_info = pyreg.TypeInfo(
            typ=self.separator_spec_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="SeparatorSpec",
        )
        self.context.python_type_registry.register_type(separator_spec_type_info)

        self.group_type = iir.Type.make(cname="Group")
        group_type_info = pyreg.TypeInfo(
            typ=self.group_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="Group",
        )
        self.context.python_type_registry.register_type(group_type_info)

        self.nest_type = iir.Type.make(cname="Nest")
        nest_type_info = pyreg.TypeInfo(
            typ=self.nest_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="Nest",
        )
        self.context.python_type_registry.register_type(nest_type_info)

        self.join_type = iir.Type.make(cname="Join")
        join_type_info = pyreg.TypeInfo(
            typ=self.join_type,
            module=pyreg.Module(("fltk", "unparse", "combinators")),
            name="Join",
        )
        self.context.python_type_registry.register_type(join_type_info)

        self.cst_node_types: dict[str, iir.Type] = {}
        cst_module_parts = tuple(self.cst_module.split("."))
        for rule in self.grammar.rules:
            rule_name = rule.name
            class_name = self.class_name_for_rule_node(rule_name)
            node_type = iir.Type.make(cname=f"_rule_{class_name}")
            node_type_info = pyreg.TypeInfo(
                typ=node_type,
                module=pyreg.Module(cst_module_parts),
                name=class_name,
            )
            self.context.python_type_registry.register_type(node_type_info)
            self.cst_node_types[rule_name] = node_type

    def _setup_unparser_class(self):
        """Set up the unparser class with constructor and fields."""
        terminals_field = self.unparser_class.def_field(name="terminals", typ=iir.String, init=None)
        terminals_param = iir.Param(
            name="terminals",
            typ=iir.String,
            ref_type=iir.RefType.BORROW,
            mutable=False,
        )
        self.unparser_class.def_constructor(
            params=[terminals_param],
            init_list=[(terminals_field, iir.INIT_FROM_PARAM)],
        )

    def _generate_rule_unparser(self, rule: gsm.Rule):
        """Generate the unparser method for a grammar rule."""
        rule_name = rule.name
        path = (rule_name,)
        alternatives = rule.alternatives

        unparser_info = self.unparsers[path]
        node_type = self.get_node_type_for_rule(rule_name)
        method = self.unparser_class.def_method(
            name=unparser_info.name,
            return_type=self.maybe_unparse_result_type,
            params=[
                iir.Param(
                    name="node",
                    typ=node_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
            ],
            mutable_self=False,
        )

        # Create initial accumulator for rule
        accumulator_module = self._get_accumulator_module()
        initial_accumulator = method.block.var(
            name="accumulator",
            typ=self.doc_accumulator_type,
            ref_type=iir.RefType.VALUE,
            mutable=True,
            init=accumulator_module.method.DocAccumulator.call(),
        )

        start_anchor = self.formatter_config.get_anchor_config(rule_name, "before", ItemSelector.RULE_START, "")
        if start_anchor:
            for op in start_anchor.operations:
                if op.operation_type == OperationType.GROUP_BEGIN:
                    method.block.assign(
                        initial_accumulator.store(), initial_accumulator.load().method.push_group.call()
                    )
                elif op.operation_type == OperationType.NEST_BEGIN:
                    method.block.assign(
                        initial_accumulator.store(),
                        initial_accumulator.load().method.push_nest.call(
                            iir.LiteralInt(typ=iir.IndexInt, value=op.indent or 1)
                        ),
                    )
                elif op.operation_type == OperationType.JOIN_BEGIN:
                    if op.separator is None:
                        msg = "JOIN_BEGIN operation missing required separator"
                        raise RuntimeError(msg)
                    separator_expr = self._doc_to_combinator_expr(op.separator)
                    method.block.assign(
                        initial_accumulator.store(), initial_accumulator.load().method.push_join.call(separator_expr)
                    )

        self.gen_alternatives_unparser(
            path=path,
            alternatives=alternatives,
            rule_name=rule_name,
            method=method,
            unparser_info=unparser_info,
            accumulator_var=initial_accumulator,
        )

    def _extract_and_validate_nonsequence_child(
        self,
        method: iir.Method,
        node_var: iir.Var,
        pos_var: iir.Var | iir.Expr,
        item: gsm.Item,
        rule_name: str,
        child_name: str = "child",
    ) -> iir.Var:
        """Generate code to extract a non-sequence child and validate its label and type.

        Returns the validated child variable.
        """
        if item.disposition != gsm.Disposition.INCLUDE:
            error_msg = (
                f"_extract_and_validate_child called on non-included item with disposition {item.disposition}. "
                "This is an internal error - this method should only be called for INCLUDE items."
            )
            raise RuntimeError(error_msg)

        # Bounds check
        children_count = self._get_children_count(node_var)
        pos_expr = pos_var.load() if isinstance(pos_var, iir.Var) else pos_var
        bounds_check = iir.BinOp(
            lhs=pos_expr,
            op=">=",
            rhs=children_count,
        )
        if_out_of_bounds = method.block.if_(bounds_check)
        if_out_of_bounds.block.return_(iir.LiteralNull())

        # Get child tuple at position
        child_tuple = iir.Subscript(
            target=node_var.load().fld.children.load(),
            index=pos_expr,
        )

        # Check label if present
        if item.label:
            child_label = iir.Subscript(
                target=child_tuple,
                index=iir.LiteralInt(typ=iir.IndexInt, value=0),
            )
            expected_label = item.label
            class_name = self.class_name_for_rule_node(rule_name)
            expected_label_enum = iir.VarByName(
                name=f"{class_name}.Label.{expected_label.upper()}",
                typ=iir.Type.make(cname="enum.Enum"),
                ref_type=iir.RefType.BORROW,
                mutable=False,
            )
            label_check = iir.BinOp(
                lhs=child_label,
                op="!=",
                rhs=expected_label_enum.load(),
            )
            if_wrong_label = method.block.if_(label_check)
            if_wrong_label.block.return_(iir.LiteralNull())

        # Extract child
        child_expr = iir.Subscript(
            target=child_tuple,
            index=iir.LiteralInt(typ=iir.IndexInt, value=1),
        )

        child_var = method.block.var(
            name=child_name,
            typ=iir.Auto,
            ref_type=iir.RefType.VALUE,
            mutable=False,
            init=child_expr,
        )

        expected_type = self._get_node_type_for_nonsequence_term(item.term)
        isinstance_check = iir.IsInstance(expr=child_var.load(), typ=expected_type)
        type_check_condition = iir.LogicalNegation(operand=isinstance_check)
        if_wrong_type = method.block.if_(type_check_condition)
        if_wrong_type.block.return_(iir.LiteralNull())

        return child_var

    def _check_unparse_result(self, method: iir.Method, result_var: iir.Var):
        """Check if unparse result is None and return early if needed."""
        if_failed = method.block.if_(iir.LogicalNegation(operand=result_var.load()))
        if_failed.block.return_(iir.LiteralNull())

    def _extract_result_accumulator(self, result_var: iir.Var) -> iir.Expr:
        """Extract the accumulator from an UnparseResult (assumes it's not None)."""
        return result_var.load().fld.accumulator.load()

    def _extract_result_pos(self, result_var: iir.Var) -> iir.Expr:
        """Extract the new_pos from an UnparseResult (assumes it's not None)."""
        return result_var.load().fld.new_pos.load()

    def _make_unparse_result(self, accumulator: iir.Expr, new_pos: iir.Expr) -> iir.Construct:
        """Create an UnparseResult construct."""
        return iir.Construct.make(
            self.unparse_result_type,
            accumulator=accumulator,
            new_pos=new_pos,
        )

    def _get_combinators_module(self) -> iir.VarByName:
        """Get the combinators module variable."""
        return iir.VarByName(
            name="fltk.unparse.combinators",
            typ=iir.Type.make(cname="module"),
            ref_type=iir.RefType.BORROW,
            mutable=False,
        )

    def _get_accumulator_module(self) -> iir.VarByName:
        """Get the accumulator module variable."""
        return iir.VarByName(
            name="fltk.unparse.accumulator",
            typ=iir.Type.make(cname="module"),
            ref_type=iir.RefType.BORROW,
            mutable=False,
        )

    def _doc_to_combinator_expr(self, doc: Doc) -> iir.Expr:
        """Convert a Doc combinator to an IIR expression."""
        combinators = self._get_combinators_module()

        doc_to_field = {
            NIL: "NIL",
            NBSP: "NBSP",
            LINE: "LINE",
            SOFTLINE: "SOFTLINE",
            HARDLINE: "HARDLINE",
        }

        field_name = doc_to_field.get(doc)
        if field_name:
            return combinators.fld[field_name].load()
        elif isinstance(doc, HardLine):
            if doc.blank_lines == 0:
                return combinators.fld["HARDLINE"].load()
            elif doc.blank_lines == 1:
                return combinators.fld["HARDLINE_BLANK"].load()
            else:
                return combinators.method.hardline.call(iir.LiteralInt(typ=iir.IndexInt, value=doc.blank_lines))
        elif isinstance(doc, Text):
            return combinators.method.text.call(iir.LiteralString(doc.content))
        elif isinstance(doc, Concat):
            doc_exprs = [self._doc_to_combinator_expr(d) for d in doc.docs]
            list_expr = iir.LiteralSequence(values=doc_exprs)
            return combinators.method.concat.call(list_expr)
        else:
            msg = f"Unknown Doc type: {doc}"
            raise ValueError(msg)

    def _create_after_spec(self, spacing: Doc) -> iir.Expr:
        """Create an AfterSpec control node."""
        self._get_combinators_module()
        spacing_expr = self._doc_to_combinator_expr(spacing)
        return iir.Construct.make(
            self.after_spec_type,
            spacing=spacing_expr,
        )

    def _create_before_spec(self, spacing: Doc) -> iir.Expr:
        """Create a BeforeSpec control node."""
        self._get_combinators_module()
        spacing_expr = self._doc_to_combinator_expr(spacing)
        return iir.Construct.make(
            self.before_spec_type,
            spacing=spacing_expr,
        )

    def _create_separator_spec(
        self, *, spacing: Doc | None, preserved_trivia: iir.Expr | None, required: bool
    ) -> iir.Expr:
        """Create a SeparatorSpec control node."""
        spacing_expr = iir.LiteralNull() if spacing is None else self._doc_to_combinator_expr(spacing)
        trivia_expr = preserved_trivia if preserved_trivia is not None else iir.LiteralNull()

        return iir.Construct.make(
            self.separator_spec_type,
            spacing=spacing_expr,
            preserved_trivia=trivia_expr,
            required=iir.TrueBool if required else iir.FalseBool,
        )

    def gen_item_unparser(self, path: tuple[str, ...], item: gsm.Item, rule_name: str) -> UnparserFn:
        """Generate unparser for an Item."""
        if item.disposition == gsm.Disposition.SUPPRESS:
            # For suppressed quantified items, we need to generate the minimum required occurrences
            # since they're not in the CST but still needed for the grammar to parse
            node_type = self.get_node_type_for_rule(rule_name)
            method, unparser_info = self._gen_unparser_callable(
                path=path, result_type=self.maybe_unparse_result_type, node_type=node_type
            )
            self._gen_suppressed_quantified_item_body(method, item)
            return unparser_info
        elif item.quantifier.is_multiple():
            # Quantified items need their own method for loop logic
            node_type = self.get_node_type_for_rule(rule_name)
            method, unparser_info = self._gen_unparser_callable(
                path=path, result_type=self.maybe_unparse_result_type, node_type=node_type
            )
            node_var = method.get_param("node")
            pos_var = method.get_param("pos")
            self._gen_quantified_item_body(method, node_var, pos_var, path, item, rule_name)
            return unparser_info
        else:
            # Single items can just use the term unparser directly
            return self.gen_term_unparser(path, item, rule_name)

    def _gen_suppressed_quantified_item_body(
        self,
        method: iir.Method,
        item: gsm.Item,
    ):
        """Generate body for suppressed quantified items that are not in the CST.

        For suppressed items, we generate the minimum required by the grammar:
        - ? (optional): 0 occurrences
        - * (zero or more): 0 occurrences
        - + (one or more): 1 occurrence
        """
        pos_var = method.get_param("pos")
        accumulator_param = method.get_param("accumulator")
        combinators = self._get_combinators_module()

        if item.quantifier.is_optional():
            # Optional suppressed items: generate nothing - just return the passed accumulator
            empty_result = self._make_unparse_result(accumulator_param.load(), pos_var.load())
            method.block.return_(empty_result)
        # Required suppressed items: validate that we can actually generate them
        elif isinstance(item.term, gsm.Literal):
            # Literals can be regenerated exactly
            literal_text = item.term.value
            text_call = combinators.method.text.call(iir.LiteralString(literal_text))

            result_accumulator = accumulator_param.load().method.add_non_trivia.call(text_call)
            result = self._make_unparse_result(result_accumulator, pos_var.load())
            method.block.return_(result)
        elif isinstance(item.term, gsm.Regex):
            msg = (
                f"Cannot generate unparser: required suppressed regex '{item.term.value}' "
                "cannot be recreated from CST. Consider adding a label to include it."
            )
            raise RuntimeError(msg)
        elif isinstance(item.term, gsm.Identifier):
            msg = (
                f"Cannot generate unparser: required suppressed rule reference '{item.term.value}' "
                "cannot be recreated from CST. Consider removing the suppression."
            )
            raise RuntimeError(msg)
        else:
            msg = (
                f"Cannot generate unparser: required suppressed term of type {type(item.term).__name__} "
                "cannot be recreated from CST. Consider adding a lable or removing the suppression."
            )
            raise RuntimeError(msg)

    def _gen_quantified_item_body(
        self,
        method: iir.Method,
        node_var: iir.Var,
        pos_var: iir.Var,
        path: tuple[str, ...],
        item: gsm.Item,
        rule_name: str,
    ):
        """Generate the body for a quantified (+ or *) item using a unified approach."""
        accumulator_param = method.get_param("accumulator")

        # First, generate the inner unparser that processes one occurrence
        inner_unparser_info = self.gen_term_unparser((*path, "inner"), item, rule_name)

        current_pos_var = method.block.var(
            name="current_pos",
            typ=iir.IndexInt,
            ref_type=iir.RefType.VALUE,
            mutable=True,
            init=pos_var.load(),
        )

        # Loop to process multiple occurrences
        children_count = self._get_children_count(node_var)
        loop_condition = iir.BinOp(
            lhs=current_pos_var.load(),
            op="<",
            rhs=children_count,
        )

        # For + quantifier, track if we matched at least once
        match_count_var = None
        if item.quantifier.min() == gsm.Arity.ONE:
            match_count_var = method.block.var(
                name="match_count",
                typ=iir.IndexInt,
                ref_type=iir.RefType.VALUE,
                mutable=True,
                init=iir.LiteralInt(typ=iir.IndexInt, value=0),
            )

        while_loop = method.block.while_(loop_condition)

        # Call inner unparser with current accumulator
        inner_call = (
            iir.SelfExpr()
            .method[inner_unparser_info.name]
            .call(node_var.load(), current_pos_var.load(), accumulator_param.load())
        )
        result_var = while_loop.block.var(
            name="inner_result",
            typ=self.maybe_unparse_result_type,
            ref_type=iir.RefType.VALUE,
            mutable=False,
            init=inner_call,
        )

        # Handle success - update accumulator and position
        if_success = while_loop.block.if_(result_var.load())
        if_success.block.assign(accumulator_param.store(), self._extract_result_accumulator(result_var))
        if_success.block.assign(current_pos_var.store(), self._extract_result_pos(result_var))

        if item.quantifier.min() == gsm.Arity.ONE and match_count_var is not None:
            if_success.block.assign(
                match_count_var.store(),
                iir.BinOp(
                    lhs=match_count_var.load(),
                    op="+",
                    rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
                ),
            )

        # On failure, exit loop
        if_failed = while_loop.block.if_(iir.LogicalNegation(operand=result_var.load()))
        if_failed.block.body.append(iir.Break(parent_block=if_failed.block))

        # Check minimum requirements for + quantifier
        if item.quantifier.min() == gsm.Arity.ONE and match_count_var is not None:
            no_matches = iir.BinOp(
                lhs=match_count_var.load(),
                op="==",
                rhs=iir.LiteralInt(typ=iir.IndexInt, value=0),
            )
            if_no_matches = method.block.if_(no_matches)
            if_no_matches.block.return_(iir.LiteralNull())

        # Return the accumulated result
        result = self._make_unparse_result(accumulator_param.load(), current_pos_var.load())
        method.block.return_(result)

    def _get_children_count(self, node_var: iir.Var) -> iir.Expr:
        """Get the count of children for a node."""
        return iir.MethodCall(
            bound_method=iir.MethodAccess(
                member_name="__call__",
                bound_to=iir.VarByName(
                    name="len",
                    typ=iir.Type.make(cname="function"),
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ).load(),
            ),
            args=[node_var.load().fld.children.load()],
            kwargs={},
        )

    def _get_len(self, expr: iir.Expr) -> iir.Expr:
        """Get the length of a sequence."""
        return iir.MethodCall(
            bound_method=iir.MethodAccess(
                member_name="__call__",
                bound_to=iir.VarByName(
                    name="len",
                    typ=iir.Type.make(cname="function"),
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ).load(),
            ),
            args=[expr],
            kwargs={},
        )

    def class_name_for_rule_node(self, rule_name: str) -> str:
        return "".join(part.capitalize() for part in rule_name.lower().split("_"))

    def get_node_type_for_rule(self, rule_name: str) -> iir.Type:
        return self.cst_node_types[rule_name]

    def _get_node_type_for_nonsequence_term(self, term: gsm.Term) -> iir.Type:
        if isinstance(term, gsm.Identifier):
            rule_name = term.value
            return self.get_node_type_for_rule(rule_name)
        elif isinstance(term, gsm.Literal | gsm.Regex):
            return self.span_type
        else:
            msg = f"Internal error: Unexpected term {term}"
            raise RuntimeError(msg)

    def _make_unparser_info(self, *, path: tuple[str, ...], result_type: iir.Type) -> UnparserFn:
        base_name = f"unparse_{'__'.join(path)}"
        unparser_info = UnparserGenerator.UnparserFn(
            name=base_name,
            result_type=result_type,
        )
        assert path not in self.unparsers  # noqa: S101
        self.unparsers[path] = unparser_info
        return unparser_info

    def _cache_unparser_info(self, *, path: tuple[str, ...], result_type: iir.Type) -> UnparserFn:
        try:
            return self.unparsers[path]
        except KeyError:
            pass
        return self._make_unparser_info(path=path, result_type=result_type)

    def _gen_unparser_callable(
        self, *, path: tuple[str, ...], result_type: iir.Type, node_type: iir.Type
    ) -> tuple[iir.Method, UnparserFn]:
        unparser_info = self._cache_unparser_info(path=path, result_type=result_type)

        method = self.unparser_class.def_method(
            name=unparser_info.name,
            return_type=result_type,
            params=[
                iir.Param(
                    name="node",
                    typ=node_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
                iir.Param(
                    name="pos",
                    typ=iir.IndexInt,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
                iir.Param(
                    name="accumulator",
                    typ=self.doc_accumulator_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
            ],
            mutable_self=False,
        )
        return method, unparser_info

    def gen_alternatives_unparser(
        self,
        *,
        path: tuple[str, ...],
        alternatives: Sequence[gsm.Items],
        rule_name: str,
        method: iir.Method,
        unparser_info: UnparserFn,
        accumulator_var: iir.Var,
        is_rule_unparser: bool = True,
    ) -> UnparserFn:
        # Generate methods for each alternative first
        alt_methods = []
        for alt_idx, items in enumerate(alternatives):
            alt_path = (*path, f"alt{alt_idx}")
            alt_unparser_info = self.gen_alternative_unparser(alt_path, items, rule_name)
            alt_methods.append(alt_unparser_info)

        node_var = method.get_param("node")

        if is_rule_unparser:
            # Rule unparsers start at position 0
            pos_expr = iir.LiteralInt(typ=iir.IndexInt, value=0)
        else:
            # Nested alternatives use the passed position
            pos_var = method.get_param("pos")
            pos_expr = pos_var.load()

        # Try each alternative in order
        for alt_info in alt_methods:
            alt_call = iir.SelfExpr().method[alt_info.name].call(node_var.load(), pos_expr, accumulator_var.load())

            result_var = method.block.var(
                name=f"result_{alt_info.name.split('__')[-1]}",
                typ=self.maybe_unparse_result_type,
                ref_type=iir.RefType.VALUE,
                mutable=False,
                init=alt_call,
            )

            if_stmt = method.block.if_(result_var.load())

            if is_rule_unparser:
                final_accumulator = self._extract_result_accumulator(result_var)
                needs_modification = False

                end_anchor = self.formatter_config.get_anchor_config(rule_name, "after", ItemSelector.RULE_END, "")
                if end_anchor:
                    # Operations are already in correct order for unwinding
                    for op in end_anchor.operations:
                        if op.operation_type == OperationType.NEST_END:
                            final_accumulator = final_accumulator.method.pop_nest.call()
                            needs_modification = True
                        elif op.operation_type == OperationType.GROUP_END:
                            final_accumulator = final_accumulator.method.pop_group.call()
                            needs_modification = True
                        elif op.operation_type == OperationType.JOIN_END:
                            final_accumulator = final_accumulator.method.pop_join.call()
                            needs_modification = True

                if needs_modification:
                    final_result = self._make_unparse_result(final_accumulator, self._extract_result_pos(result_var))
                    if_stmt.block.return_(final_result)
                else:
                    if_stmt.block.return_(result_var.load())
            else:
                if_stmt.block.return_(result_var.load())

        method.block.return_(iir.LiteralNull())
        return unparser_info

    def _get_trivia_type(self) -> iir.Type:
        """Get the Trivia type."""
        if not hasattr(self, "_trivia_type"):
            self._trivia_type = iir.Type.make(cname="Trivia")
            trivia_type_info = pyreg.TypeInfo(
                typ=self._trivia_type,
                module=pyreg.Module(tuple(self.cst_module.split("."))),
                name="Trivia",
            )
            self.context.python_type_registry.register_type(trivia_type_info)
        return self._trivia_type

    def _gen_after_item_spacing(
        self,
        target_block: iir.Block,
        accumulator_var: iir.Var,
        item: gsm.Item,
        rule_name: str,
    ) -> None:
        """Generate code to emit AfterSpec control node for a specific item.

        Args:
            target_block: The block to add the spacing code to
            accumulator_var: The accumulator to add spacing to
            item: The grammar item to check for after configuration
            rule_name: The name of the rule containing the item
        """
        after_spacing = self.formatter_config.get_after_spacing(rule_name, item)
        if after_spacing:
            after_spec_expr = self._create_after_spec(after_spacing)
            new_accumulator = accumulator_var.load().method.add_non_trivia.call(after_spec_expr)
            target_block.assign(accumulator_var.store(), new_accumulator)

    def _gen_before_item_spacing(
        self,
        target_block: iir.Block,
        accumulator_var: iir.Var,
        item: gsm.Item,
        rule_name: str,
    ) -> None:
        """Generate code to emit BeforeSpec control node for a specific item.

        Args:
            target_block: The block to add the spacing code to
            accumulator_var: The accumulator to add spacing to
            item: The grammar item to check for before configuration
            rule_name: The name of the rule containing the item
        """
        before_spacing = self.formatter_config.get_before_spacing(rule_name, item)
        if before_spacing:
            before_spec_expr = self._create_before_spec(before_spacing)
            new_accumulator = accumulator_var.load().method.add_non_trivia.call(before_spec_expr)
            target_block.assign(accumulator_var.store(), new_accumulator)

    def _gen_has_preservable_trivia_method(self) -> iir.Method:
        """Generate a method that checks if a trivia node has any preservable content."""
        method = self.unparser_class.def_method(
            name="_has_preservable_trivia",
            return_type=iir.Bool,
            params=[
                iir.Param(
                    name="trivia_node",
                    typ=self._get_trivia_type(),
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
            ],
            mutable_self=False,
        )

        # If preserve_node_names is None, preserve everything
        if self.formatter_config.trivia_config and self.formatter_config.trivia_config.preserve_node_names is None:
            method.block.return_(iir.TrueBool)
            return method

        # If preserve_node_names is empty set, preserve nothing
        if not self.formatter_config.trivia_config or not self.formatter_config.trivia_config.preserve_node_names:
            method.block.return_(iir.FalseBool)
            return method

        # Otherwise, check each child
        trivia_node_var = method.get_param("trivia_node")
        children_var = method.block.var(
            name="children",
            typ=iir.Auto,
            ref_type=iir.RefType.VALUE,
            mutable=False,
            init=trivia_node_var.load().fld.children.load(),
        )

        # Loop through children
        idx_var = method.block.var(
            name="idx",
            typ=iir.IndexInt,
            ref_type=iir.RefType.VALUE,
            mutable=True,
            init=iir.LiteralInt(typ=iir.IndexInt, value=0),
        )

        children_count = self._get_len(children_var.load())
        loop_condition = iir.BinOp(
            lhs=idx_var.load(),
            op="<",
            rhs=children_count,
        )

        while_loop = method.block.while_(loop_condition)

        # Get child node
        child_tuple = iir.Subscript(
            target=children_var.load(),
            index=idx_var.load(),
        )
        child_node = iir.Subscript(
            target=child_tuple,
            index=iir.LiteralInt(typ=iir.IndexInt, value=1),
        )

        # Check each preservable type
        for node_name in self.formatter_config.trivia_config.preserve_node_names:
            node_type = self._get_trivia_child_type(node_name)
            is_type_check = iir.IsInstance(expr=child_node, typ=node_type)
            if_matches = while_loop.block.if_(is_type_check)
            if_matches.block.return_(iir.TrueBool)

        # Increment index
        while_loop.block.assign(
            idx_var.store(),
            iir.BinOp(
                lhs=idx_var.load(),
                op="+",
                rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
            ),
        )

        # No preservable content found
        method.block.return_(iir.FalseBool)
        return method

    def _get_trivia_child_type(self, node_name: str) -> iir.Type:
        """Get the type for a trivia child node by name."""
        # Cache trivia child types
        if not hasattr(self, "_trivia_child_types"):
            self._trivia_child_types = {}

        if node_name not in self._trivia_child_types:
            node_type = iir.Type.make(cname=node_name)
            type_info = pyreg.TypeInfo(
                typ=node_type,
                module=pyreg.Module(tuple(self.cst_module.split("."))),
                name=node_name,
            )
            self.context.python_type_registry.register_type(type_info)
            self._trivia_child_types[node_name] = node_type

        return self._trivia_child_types[node_name]

    def _gen_trivia_processing(
        self,
        method: iir.Method,
        current_pos_var: iir.Var,
        node_var: iir.Var,
        accumulator_var: iir.Var,
        separator: gsm.Separator,
        rule_name: str,
    ) -> None:
        """Generate code to process a Trivia node using the generated unparse__trivia method.

        Args:
            separator: The separator type that determines whitespace handling
        """
        if separator not in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
            return

        # Check if this is a trivia rule - if so, handle whitespace Span children
        rule = self.grammar.identifiers.get(rule_name)
        if rule and rule.is_trivia_rule:
            # For trivia rules, we need to consume unlabeled Span children that represent whitespace
            # Check if we're within bounds
            children_count = self._get_children_count(node_var)
            bounds_check = iir.BinOp(
                lhs=current_pos_var.load(),
                op="<",
                rhs=children_count,
            )

            if_in_bounds = method.block.if_(bounds_check, orelse=(separator == gsm.Separator.WS_REQUIRED))

            # Get current child
            child_tuple = iir.Subscript(
                target=node_var.load().fld.children.load(),
                index=current_pos_var.load(),
            )
            child_label = iir.Subscript(
                target=child_tuple,
                index=iir.LiteralInt(typ=iir.IndexInt, value=0),
            )
            child_value = iir.Subscript(
                target=child_tuple,
                index=iir.LiteralInt(typ=iir.IndexInt, value=1),
            )

            # Check if it's an unlabeled Span (label should be None)
            is_unlabeled = iir.BinOp(
                lhs=child_label,
                op="is",
                rhs=iir.LiteralNull(),
            )

            # Check if child is a Span
            span_type = iir.Type.make(cname="Span")
            is_span_check = iir.IsInstance(expr=child_value, typ=span_type)

            is_whitespace_span = iir.LogicalAnd(lhs=is_unlabeled, rhs=is_span_check)

            if_whitespace = if_in_bounds.block.if_(is_whitespace_span, orelse=(separator == gsm.Separator.WS_REQUIRED))

            # Consume the whitespace span
            if_whitespace.block.assign(
                current_pos_var.store(),
                iir.BinOp(
                    lhs=current_pos_var.load(),
                    op="+",
                    rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
                ),
            )

            # For WS_REQUIRED, check if we found whitespace and fail if not
            if separator == gsm.Separator.WS_REQUIRED:
                assert isinstance(if_in_bounds.orelse, iir.Block)  # noqa: S101
                if_in_bounds.orelse.return_(iir.LiteralNull())
                assert isinstance(if_whitespace.orelse, iir.Block)  # noqa: S101
                if_whitespace.orelse.return_(iir.LiteralNull())

            # Always add the configured spacing
            self._add_default_separator_spec(
                method.block,
                accumulator_var,
                rule_name,
                separator,
            )

            return

        # First check if last item was trivia - if so, skip processing
        if_not_last_trivia = method.block.if_(
            iir.LogicalNegation(operand=accumulator_var.load().fld.last_was_trivia.load())
        )

        # Check if current child is Trivia (only if last wasn't trivia)
        children_count = self._get_children_count(node_var)
        bounds_check = iir.BinOp(
            lhs=current_pos_var.load(),
            op="<",
            rhs=children_count,
        )

        if_in_bounds = if_not_last_trivia.block.if_(bounds_check, orelse=True)

        # Get current child
        child_tuple = iir.Subscript(
            target=node_var.load().fld.children.load(),
            index=current_pos_var.load(),
        )
        child_value = iir.Subscript(
            target=child_tuple,
            index=iir.LiteralInt(typ=iir.IndexInt, value=1),
        )

        # Check if it's a Trivia node
        trivia_type = self._get_trivia_type()
        is_trivia_check = iir.IsInstance(expr=child_value, typ=trivia_type)

        if_trivia = if_in_bounds.block.if_(is_trivia_check, orelse=True)

        # Store the trivia node in a variable
        trivia_var = if_trivia.block.var(
            name="trivia_node",
            typ=trivia_type,
            ref_type=iir.RefType.VALUE,
            mutable=False,
            init=child_value,
        )

        # Check if this trivia has preservable content
        has_preservable_call = iir.SelfExpr().method._has_preservable_trivia.call(trivia_var.load())
        if_has_preservable = if_trivia.block.if_(has_preservable_call, orelse=True)

        # Call the generated unparse__trivia method
        trivia_unparser_call = iir.SelfExpr().method.unparse__trivia.call(trivia_var.load())

        trivia_result_var = if_has_preservable.block.var(
            name="trivia_result",
            typ=self.maybe_unparse_result_type,
            ref_type=iir.RefType.VALUE,
            mutable=False,
            init=trivia_unparser_call,
        )

        # If trivia unparsing succeeded, use it
        if_trivia_success = if_has_preservable.block.if_(trivia_result_var.load())

        # Extract the accumulated doc from trivia result
        trivia_accumulator = self._extract_result_accumulator(trivia_result_var)
        trivia_doc = trivia_accumulator.fld.doc.load()

        # Wrap in a SeparatorSpec control node with preserved trivia
        self._add_separator_spec(
            if_trivia_success.block,
            accumulator_var,
            spacing=None,
            preserved_trivia=trivia_doc,
            required=(separator == gsm.Separator.WS_REQUIRED),
        )

        # Else: no preservable content, add configured spacing
        assert isinstance(if_has_preservable.orelse, iir.Block)  # noqa: S101
        self._add_default_separator_spec(
            if_has_preservable.orelse,
            accumulator_var,
            rule_name,
            separator,
        )

        # Always advance position past the trivia node
        if_trivia.block.assign(
            current_pos_var.store(),
            iir.BinOp(
                lhs=current_pos_var.load(),
                op="+",
                rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
            ),
        )

        # Else: child is not trivia, add default spacing
        assert isinstance(if_trivia.orelse, iir.Block)  # noqa: S101
        self._add_default_separator_spec(
            if_trivia.orelse,
            accumulator_var,
            rule_name,
            separator,
        )

        # Also handle out of bounds case - add default spacing
        assert isinstance(if_in_bounds.orelse, iir.Block)  # noqa: S101
        self._add_default_separator_spec(
            if_in_bounds.orelse,
            accumulator_var,
            rule_name,
            separator,
        )

    def _add_separator_spec(
        self,
        block: iir.Block,
        accumulator_var: iir.Var,
        spacing: Doc | None,
        preserved_trivia: iir.Expr | None,
        *,
        required: bool,
    ) -> None:
        """Add a SeparatorSpec to the accumulator."""
        separator_spec_expr = self._create_separator_spec(
            spacing=spacing,
            preserved_trivia=preserved_trivia or iir.LiteralNull(),
            required=required,
        )
        new_accumulator = accumulator_var.load().method.add_trivia.call(separator_spec_expr)
        block.assign(accumulator_var.store(), new_accumulator)

    def _add_default_separator_spec(
        self,
        block: iir.Block,
        accumulator_var: iir.Var,
        rule_name: str,
        separator: gsm.Separator,
    ) -> None:
        """Add a default SeparatorSpec based on formatter config."""
        spacing_doc = self.formatter_config.get_spacing_for_separator(rule_name, separator)
        self._add_separator_spec(
            block,
            accumulator_var,
            spacing=spacing_doc,
            preserved_trivia=None,
            required=(separator == gsm.Separator.WS_REQUIRED),
        )

    def _item_matches_anchor(self, item: gsm.Item, selector_type: ItemSelector, selector_value: str) -> bool:
        """Check if an item matches an anchor specification."""
        if selector_type == ItemSelector.LABEL:
            return item.label == selector_value
        elif selector_type == ItemSelector.LITERAL:
            return isinstance(item.term, gsm.Literal) and item.term.value == selector_value
        return False

    def _gen_anchor_operations_before_item(
        self,
        block: iir.Block,
        accumulator_var: iir.Var,
        item: gsm.Item,
        rule_name: str,
    ) -> None:
        """Generate operations that should occur before an item."""
        anchor_config = None
        if item.label:
            anchor_config = self.formatter_config.get_anchor_config(rule_name, "before", ItemSelector.LABEL, item.label)
        if anchor_config is None and isinstance(item.term, gsm.Literal):
            anchor_config = self.formatter_config.get_anchor_config(
                rule_name, "before", ItemSelector.LITERAL, item.term.value
            )
        if anchor_config is None:
            return

        if anchor_config:
            for op in anchor_config.operations:
                if op.operation_type == OperationType.SPACING:
                    # Already handled by _gen_before_item_spacing
                    continue
                elif op.operation_type == OperationType.GROUP_BEGIN:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.push_group.call())
                elif op.operation_type == OperationType.NEST_BEGIN:
                    block.assign(
                        accumulator_var.store(),
                        accumulator_var.load().method.push_nest.call(
                            iir.LiteralInt(typ=iir.IndexInt, value=op.indent or 1)
                        ),
                    )
                elif op.operation_type == OperationType.GROUP_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_group.call())
                elif op.operation_type == OperationType.NEST_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_nest.call())
                elif op.operation_type == OperationType.JOIN_BEGIN:
                    if op.separator is None:
                        msg = "JOIN_BEGIN operation missing required separator"
                        raise RuntimeError(msg)
                    separator_expr = self._doc_to_combinator_expr(op.separator)
                    block.assign(accumulator_var.store(), accumulator_var.load().method.push_join.call(separator_expr))
                elif op.operation_type == OperationType.JOIN_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_join.call())

    def _gen_anchor_operations_after_item(
        self,
        block: iir.Block,
        accumulator_var: iir.Var,
        item: gsm.Item,
        rule_name: str,
    ) -> None:
        """Generate operations that should occur after an item."""
        if item.label:
            anchor_config = self.formatter_config.get_anchor_config(rule_name, "after", ItemSelector.LABEL, item.label)
        elif isinstance(item.term, gsm.Literal):
            anchor_config = self.formatter_config.get_anchor_config(
                rule_name, "after", ItemSelector.LITERAL, item.term.value
            )
        else:
            return

        if anchor_config:
            for op in anchor_config.operations:
                if op.operation_type == OperationType.SPACING:
                    # Already handled by _gen_after_item_spacing
                    continue
                elif op.operation_type == OperationType.GROUP_BEGIN:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.push_group.call())
                elif op.operation_type == OperationType.NEST_BEGIN:
                    block.assign(
                        accumulator_var.store(),
                        accumulator_var.load().method.push_nest.call(
                            iir.LiteralInt(typ=iir.IndexInt, value=op.indent or 1)
                        ),
                    )
                elif op.operation_type == OperationType.GROUP_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_group.call())
                elif op.operation_type == OperationType.NEST_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_nest.call())
                elif op.operation_type == OperationType.JOIN_BEGIN:
                    if op.separator is None:
                        msg = "JOIN_BEGIN operation missing required separator"
                        raise RuntimeError(msg)
                    separator_expr = self._doc_to_combinator_expr(op.separator)
                    block.assign(accumulator_var.store(), accumulator_var.load().method.push_join.call(separator_expr))
                elif op.operation_type == OperationType.JOIN_END:
                    block.assign(accumulator_var.store(), accumulator_var.load().method.pop_join.call())

    def gen_alternative_unparser(self, path: tuple[str, ...], items: gsm.Items, rule_name: str) -> UnparserFn:
        """Generate unparser for a single alternative using incremental result building."""
        node_type = self.get_node_type_for_rule(rule_name)
        method, unparser_info = self._gen_unparser_callable(
            path=path, result_type=self.maybe_unparse_result_type, node_type=node_type
        )

        # Generate methods for each item
        item_methods = []
        for item_idx, item in enumerate(items.items):
            item_path = (*path, f"item{item_idx}")
            item_unparser_info = self.gen_item_unparser(item_path, item, rule_name)
            item_methods.append(item_unparser_info)

        node_var = method.get_param("node")
        pos_var = method.get_param("pos")
        accumulator_var = method.get_param("accumulator")

        current_pos_var = method.block.var(
            name="current_pos",
            typ=iir.IndexInt,
            ref_type=iir.RefType.VALUE,
            mutable=True,
            init=pos_var.load(),
        )

        # Handle initial separator before processing items
        self._gen_trivia_processing(
            method,
            current_pos_var,
            node_var,
            accumulator_var,
            items.initial_sep,
            rule_name,
        )

        for item_idx, item_info in enumerate(item_methods):
            grammar_item = items.items[item_idx]

            item_disposition = self.formatter_config.get_item_disposition(rule_name, grammar_item)

            self._gen_anchor_operations_before_item(method.block, accumulator_var, grammar_item, rule_name)

            if not isinstance(item_disposition, Omit | RenderAs):
                self._gen_before_item_spacing(method.block, accumulator_var, grammar_item, rule_name)

            item_call = (
                iir.SelfExpr()
                .method[item_info.name]
                .call(node_var.load(), current_pos_var.load(), accumulator_var.load())
            )

            unparse_result_var = method.block.var(
                name=f"unparse_result_{item_idx}",
                typ=self.maybe_unparse_result_type,
                ref_type=iir.RefType.VALUE,
                mutable=False,
                init=item_call,
            )

            is_required = not grammar_item.quantifier.is_optional()

            if is_required:
                self._check_unparse_result(method, unparse_result_var)

                method.block.assign(current_pos_var.store(), self._extract_result_pos(unparse_result_var))

                if isinstance(item_disposition, RenderAs):
                    # For Render, we discard the item's output and use the specified spacing
                    spacing_value = self._doc_to_combinator_expr(item_disposition.spacing)
                    new_accumulator = accumulator_var.load().method.add_non_trivia.call(spacing_value)
                    method.block.assign(accumulator_var.store(), new_accumulator)
                elif not isinstance(item_disposition, Omit):
                    assert isinstance(item_disposition, Normal)  # noqa: S101
                    result_accumulator = self._extract_result_accumulator(unparse_result_var)
                    method.block.assign(accumulator_var.store(), result_accumulator)
                    self._gen_after_item_spacing(method.block, accumulator_var, grammar_item, rule_name)
            else:
                # Optional item - handle None case
                if_not_none = method.block.if_(unparse_result_var.load())

                if_not_none.block.assign(current_pos_var.store(), self._extract_result_pos(unparse_result_var))

                if isinstance(item_disposition, RenderAs):
                    # For Render, we discard the item's output and use the specified spacing
                    spacing_value = self._doc_to_combinator_expr(item_disposition.spacing)
                    new_accumulator = accumulator_var.load().method.add_non_trivia.call(spacing_value)
                    if_not_none.block.assign(accumulator_var.store(), new_accumulator)
                elif not isinstance(item_disposition, Omit):
                    assert isinstance(item_disposition, Normal)  # noqa: S101
                    result_accumulator = self._extract_result_accumulator(unparse_result_var)
                    if_not_none.block.assign(accumulator_var.store(), result_accumulator)

                    self._gen_after_item_spacing(if_not_none.block, accumulator_var, grammar_item, rule_name)

            self._gen_anchor_operations_after_item(method.block, accumulator_var, grammar_item, rule_name)

            # Add separator after item
            if item_idx < len(items.items) and item_idx < len(items.sep_after):
                separator = items.sep_after[item_idx]

                self._gen_trivia_processing(method, current_pos_var, node_var, accumulator_var, separator, rule_name)

        result = self._make_unparse_result(accumulator_var.load(), current_pos_var.load())
        method.block.return_(result)

        return unparser_info

    def gen_term_unparser(self, path: tuple[str, ...], item: gsm.Item, rule_name: str) -> UnparserFn:
        """Generate unparser method for any grammar term type."""
        term = item.term
        disposition = item.disposition

        node_type = self.get_node_type_for_rule(rule_name)

        method, unparser_info = self._gen_unparser_callable(
            path=path, result_type=self.maybe_unparse_result_type, node_type=node_type
        )

        if isinstance(term, gsm.Identifier):
            # Extract child and call the unparser for the referenced rule
            ref_rule_name = term.value
            node_var = method.get_param("node")
            pos_var = method.get_param("pos")
            accumulator_param = method.get_param("accumulator")

            child_var = self._extract_and_validate_nonsequence_child(method, node_var, pos_var, item, rule_name)

            rule_path = (ref_rule_name,)
            rule_unparser_info = self.unparsers[rule_path]
            rule_call = iir.SelfExpr().method[rule_unparser_info.name].call(child_var.load())

            # Create a variable to hold the result from the child unparser
            child_result_var = method.block.var(
                name="child_result",
                typ=self.maybe_unparse_result_type,
                ref_type=iir.RefType.VALUE,
                mutable=False,
                init=rule_call,
            )

            # Check if child unparser failed
            if_failed = method.block.if_(iir.LogicalNegation(operand=child_result_var.load()))
            if_failed.block.return_(iir.LiteralNull())

            # Extract accumulator from child result and merge with ours
            child_accumulator = self._extract_result_accumulator(child_result_var)
            new_accumulator = accumulator_param.load().method.add_accumulator.call(child_accumulator)

            new_pos = iir.BinOp(
                lhs=pos_var.load(),
                op="+",
                rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
            )

            result = self._make_unparse_result(new_accumulator, new_pos)
            method.block.return_(result)

        elif isinstance(term, gsm.Literal):
            literal_text = term.value
            node_var = method.get_param("node")
            pos_var = method.get_param("pos")
            accumulator_param = method.get_param("accumulator")

            if disposition == gsm.Disposition.INCLUDE:
                self._extract_and_validate_nonsequence_child(method, node_var, pos_var, item, rule_name)

            combinators = self._get_combinators_module()
            text_call = combinators.method.text.call(iir.LiteralString(literal_text))

            result_accumulator = method.block.var(
                name="result_accumulator",
                typ=self.doc_accumulator_type,
                ref_type=iir.RefType.VALUE,
                mutable=False,
                init=accumulator_param.load().method.add_non_trivia.call(text_call),
            )

            new_pos = pos_var.load()
            if disposition == gsm.Disposition.INCLUDE:
                new_pos = iir.BinOp(
                    lhs=pos_var.load(),
                    op="+",
                    rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
                )

            result = self._make_unparse_result(result_accumulator.load(), new_pos)
            method.block.return_(result)

        elif isinstance(term, gsm.Regex):
            # Extract child Span node and get its text
            node_var = method.get_param("node")
            pos_var = method.get_param("pos")
            accumulator_param = method.get_param("accumulator")

            child_var = self._extract_and_validate_nonsequence_child(method, node_var, pos_var, item, rule_name)

            pyrt_module = iir.VarByName(
                name="fltk.unparse.pyrt",
                typ=iir.Type.make(cname="module"),
                ref_type=iir.RefType.BORROW,
                mutable=False,
            )
            span_text = pyrt_module.method.extract_span_text.call(
                child_var.load(),
                iir.SelfExpr().fld.terminals.load(),
            )

            combinators = self._get_combinators_module()
            text_call = combinators.method.text.call(span_text)

            result_accumulator = method.block.var(
                name="result_accumulator",
                typ=self.doc_accumulator_type,
                ref_type=iir.RefType.VALUE,
                mutable=False,
                init=accumulator_param.load().method.add_non_trivia.call(text_call),
            )

            new_pos = pos_var.load()
            if disposition == gsm.Disposition.INCLUDE:
                new_pos = iir.BinOp(
                    lhs=pos_var.load(),
                    op="+",
                    rhs=iir.LiteralInt(typ=iir.IndexInt, value=1),
                )

            result = self._make_unparse_result(result_accumulator.load(), new_pos)
            method.block.return_(result)

        elif isinstance(term, list):
            # Handle nested alternatives
            nested_path = (*path, "alts")
            node_type = self.get_node_type_for_rule(rule_name)
            nested_method, nested_unparser_info = self._gen_unparser_callable(
                path=nested_path, result_type=self.maybe_unparse_result_type, node_type=node_type
            )

            nested_accumulator_param = nested_method.get_param("accumulator")

            self.gen_alternatives_unparser(
                path=nested_path,
                alternatives=term,
                rule_name=rule_name,
                method=nested_method,
                unparser_info=nested_unparser_info,
                accumulator_var=nested_accumulator_param,
                is_rule_unparser=False,
            )

            node_var = method.get_param("node")
            pos_var = method.get_param("pos")
            accumulator_param = method.get_param("accumulator")
            nested_call = (
                iir.SelfExpr()
                .method[nested_unparser_info.name]
                .call(node_var.load(), pos_var.load(), accumulator_param.load())
            )
            method.block.return_(nested_call)
        else:
            msg = f"Internal error: Unrecognized term type {term}"
            raise ValueError(msg)

        return unparser_info


def generate_unparser(
    grammar: gsm.Grammar,
    context: CompilerContext,
    cst_module: str,
    formatter_config: FormatterConfig | None = None,
) -> tuple[iir.ClassType, list]:
    """Generate complete unparser class and imports for a grammar."""
    generator = UnparserGenerator(grammar, context, cst_module, formatter_config)

    imports: list[ast.ImportFrom | ast.Import] = [
        ast.Import(names=[ast.alias(name="typing", asname=None)]),
        ast.Import(names=[ast.alias(name="fltk.unparse.combinators", asname=None)]),
        ast.Import(names=[ast.alias(name="fltk.unparse.pyrt", asname=None)]),
        ast.Import(names=[ast.alias(name="fltk.unparse.accumulator", asname=None)]),
        ast.Import(names=[ast.alias(name="fltk.unparse.resolve_specs", asname=None)]),
        ast.Import(names=[ast.alias(name=cst_module, asname=None)]),
        ast.Import(names=[ast.alias(name="collections.abc", asname=None)]),
        ast.Import(names=[ast.alias(name="fltk.fegen.pyrt.terminalsrc", asname=None)]),
    ]

    rule_names = [rule.name for rule in grammar.rules if isinstance(rule, gsm.Rule)]
    class_names = ["".join(part.capitalize() for part in rule_name.lower().split("_")) for rule_name in rule_names]
    cst_import = ast.ImportFrom(
        module=cst_module, names=[ast.alias(name=class_name, asname=None) for class_name in class_names], level=0
    )
    imports.append(cst_import)

    return generator.unparser_class, imports
