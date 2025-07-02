from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Sequence

from fltk.fegen import gsm, gsm2tree
from fltk.iir import model as iir
from fltk.iir.context import get_parser_types
from fltk.iir.py import reg as pyreg

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext


class ParserGenerator:
    @dataclass
    class ParserFn:
        name: str
        apply_name: str
        cache_name: str | None
        result_type: iir.Type
        rule_id: int | None
        inline_to_parent: bool

    def __init__(
        self,
        grammar: gsm.Grammar,
        cstgen: gsm2tree.CstGenerator,
        context: CompilerContext,
    ):
        grammar = gsm.classify_trivia_rules(grammar)

        self.grammar: Final = grammar
        self.cstgen = cstgen
        self.context = context
        self.pos_type: Final = iir.SignedIndexInt

        self.ApplyResultType, self.TerminalSpanType, self.MemoEntryType, self.ErrorTrackerType = get_parser_types()

        self.parser_class = iir.ClassType.make(
            cname="Parser",
            doc="Parser",
            defined_in=iir.Module.make(name="TODO(module)"),
        )

        packrat_type = iir.Type.make(cname="Packrat", params={"RuleId": iir.TYPE, "PosType": iir.TYPE})
        type_info = pyreg.TypeInfo(
            typ=packrat_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
            name="Packrat",
        )
        self.context.python_type_registry.register_type(type_info)

        concrete_packrat_type = packrat_type.instantiate(RuleId=iir.IndexInt, PosType=iir.IndexInt)
        self.parser_class.def_field(
            name="packrat", typ=concrete_packrat_type, init=iir.Construct.make(concrete_packrat_type)
        )

        terminalsrc_type = iir.Type.make(cname="TerminalSource")
        type_info = pyreg.TypeInfo(
            typ=terminalsrc_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
            name="TerminalSource",
        )
        self.context.python_type_registry.register_type(type_info)
        terminalsrc_fld = self.parser_class.def_field(name="terminalsrc", typ=terminalsrc_type, init=None)

        if "trivia" not in self.grammar.identifiers:
            msg = "Expected trivia rule to exist for parsing"
            raise RuntimeError(msg)
        self.TriviaNodeType = self.cstgen.iir_type_for_rule("trivia")

        error_tracker_type = self.ErrorTrackerType.instantiate(RuleId=iir.IndexInt)
        self.parser_class.def_field(
            name="error_tracker",
            typ=error_tracker_type,
            init=iir.Construct.make(error_tracker_type),
        )

        self.parser_class.def_field(
            name="rule_names",
            typ=iir.GenericImmutableSequence.instantiate(value_type=iir.String),
            init=iir.LiteralSequence([iir.LiteralString(rule.name) for rule in self.grammar.rules]),
        )

        self.parser_class.def_constructor(
            params=[
                iir.Param(
                    name="terminalsrc",
                    typ=terminalsrc_type,
                    ref_type=iir.RefType.OWNING,
                    mutable=False,
                )
            ],
            init_list=[(terminalsrc_fld, iir.INIT_FROM_PARAM)],
        )

        span_result_type = self.ApplyResultType.instantiate(pos_type=self.pos_type, result_type=self.TerminalSpanType)
        consume_literal = self.parser_class.def_method(
            name="consume_literal",
            return_type=iir.Maybe.instantiate(value_type=span_result_type),
            params=[
                iir.Param(
                    name="pos",
                    typ=self.pos_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
                iir.Param(
                    name="literal",
                    typ=iir.String,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
            ],
            mutable_self=False,
        )
        span_var = iir.Var(name="span", typ=self.TerminalSpanType, ref_type=iir.RefType.VALUE, mutable=False)
        consume_literal.block.if_(
            condition=iir.SelfExpr().fld.terminalsrc.method.consume_literal.call(
                pos=consume_literal.get_param("pos").load(),
                literal=consume_literal.get_param("literal").load(),
            ),
            let=span_var,
        ).block.return_(
            iir.Success(
                span_result_type,
                iir.Construct.make(span_result_type, pos=span_var.fld.end, result=span_var.load()),
            )
        )
        consume_literal.block.expr_stmt(
            iir.SelfExpr().fld.error_tracker.method.fail_literal.call(
                pos=consume_literal.get_param("pos").load(),
                rule_id=iir.Subscript(
                    iir.SelfExpr().fld.packrat.fld.invocation_stack,
                    iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
                literal=consume_literal.get_param("literal").load(),
            )
        )
        consume_literal.block.return_(iir.Failure(span_result_type))

        consume_regex = self.parser_class.def_method(
            name="consume_regex",
            return_type=iir.Maybe.instantiate(value_type=span_result_type),
            params=[
                iir.Param(
                    name="pos",
                    typ=self.pos_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
                iir.Param(
                    name="regex",
                    typ=iir.String,
                    ref_type=iir.RefType.BORROW,
                    mutable=False,
                ),
            ],
            mutable_self=False,
        )
        span_var = iir.Var(name="span", typ=self.TerminalSpanType, ref_type=iir.RefType.VALUE, mutable=False)
        consume_regex.block.if_(
            condition=iir.SelfExpr().fld.terminalsrc.method.consume_regex.call(
                pos=consume_regex.get_param("pos").load(),
                regex=consume_regex.get_param("regex").load(),
            ),
            let=span_var,
        ).block.return_(
            iir.Success(
                span_result_type,
                iir.Construct.make(span_result_type, pos=span_var.fld.end, result=span_var.load()),
            )
        )

        consume_regex.block.expr_stmt(
            iir.SelfExpr().fld.error_tracker.method.fail_regex.call(
                pos=consume_regex.get_param("pos").load(),
                rule_id=iir.Subscript(
                    iir.SelfExpr().fld.packrat.fld.invocation_stack,
                    iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
                regex=consume_regex.get_param("regex").load(),
            )
        )
        consume_regex.block.return_(iir.Failure(span_result_type))

        self.item_keys: dict[gsm.Item, str] = {}
        self.key_items: dict[str, gsm.Item] = {}

        self.parsers: dict[tuple[str, ...], ParserGenerator.ParserFn] = {}
        self.rule_id_seq = itertools.count()
        for rule in self.grammar.rules:
            self._make_parser_info(
                path=(rule.name,),
                result_type=self.cstgen.iir_type_for_rule(rule.name),
                memoize=True,
            )
        for rule in self.grammar.rules:
            path = (rule.name,)
            parser_fn = self.parsers[path]
            self.gen_alternatives_parser(
                path=path,
                node_type=parser_fn.result_type,
                memoize=True,
                alternatives=rule.alternatives,
                current_rule=rule,
            )

    def _memo_type(self, result_type: iir.Type) -> iir.Type:
        return self.MemoEntryType.instantiate(RuleId=iir.IndexInt, PosType=self.pos_type, ResultType=result_type)

    def _get_trivia_regex_pattern(self, current_rule: gsm.Rule | None) -> str:
        """Get the appropriate trivia regex pattern based on rule classification."""
        if current_rule and current_rule.is_trivia_rule:
            # Trivia rules use only basic whitespace to prevent recursion
            return r"\s+"
        else:
            # Non-trivia rules use full trivia parsing (when grammar-defined trivia exists)
            # For now, default to basic whitespace - this will be enhanced when we implement
            # grammar-based trivia parsing in trivia rules
            return r"\s+"

    def get_item_key(self, item: gsm.Item) -> str:
        try:
            return self.item_keys[item]
        except KeyError:
            pass
        label = item.label or "anonitem"
        try:
            for i in itertools.count():
                key = f"{label}_{i}"
                self.key_items[key]
        except KeyError:
            pass
        self.key_items[key] = item
        self.item_keys[item] = key
        return key

    @dataclass(slots=True, frozen=True)
    class ConsumeTermInfo:
        expr: iir.Expr
        result_type: iir.Type
        inline_to_parent: bool

    def _gen_consume_term_expr(
        self,
        path: tuple[str, ...],
        node_type: iir.Type,
        term: gsm.Term,
    ) -> ConsumeTermInfo:
        if isinstance(term, gsm.Identifier):
            parser_fn = self.parsers[(term.value,)]
            return ParserGenerator.ConsumeTermInfo(
                expr=iir.SelfExpr()
                .method[parser_fn.apply_name]
                .call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load()
                ),
                result_type=parser_fn.result_type,
                inline_to_parent=False,
            )
        if isinstance(term, gsm.Literal):
            return ParserGenerator.ConsumeTermInfo(
                expr=iir.SelfExpr().method.consume_literal.call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load(),
                    literal=iir.LiteralString(term.value),
                ),
                result_type=self.TerminalSpanType,
                inline_to_parent=False,
            )
        if isinstance(term, gsm.Regex):
            # TODO pre-compile regexes
            return ParserGenerator.ConsumeTermInfo(
                expr=iir.SelfExpr().method.consume_regex.call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load(),
                    regex=iir.LiteralString(term.value),
                ),
                result_type=self.TerminalSpanType,
                inline_to_parent=False,
            )
        if isinstance(term, Sequence):
            parser_fn = self.gen_alternatives_parser(path=(*path, "alts"), node_type=node_type, alternatives=term)
            return ParserGenerator.ConsumeTermInfo(
                expr=iir.SelfExpr()
                .method[parser_fn.apply_name]
                .call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load()
                ),
                result_type=parser_fn.result_type,
                inline_to_parent=True,
            )

        msg = f"Term type {term}"
        raise NotImplementedError(msg)

    def _apply_rule_method_name(self, rule_name: str) -> str:
        return f"apply__{rule_name}"

    def _make_parser_info(
        self, *, path: tuple[str, ...], result_type: iir.Type, memoize: bool = False, inline_to_parent: bool = False
    ) -> ParserFn:
        base_name = f"parse_{'__'.join(path)}"
        parser_info = ParserGenerator.ParserFn(
            name=base_name,
            apply_name=self._apply_rule_method_name(base_name) if memoize else base_name,
            cache_name=f"_cache__{base_name}" if memoize else None,
            result_type=result_type,
            rule_id=next(self.rule_id_seq) if memoize else None,
            inline_to_parent=inline_to_parent,
        )
        assert path not in self.parsers  # noqa: S101
        self.parsers[path] = parser_info
        return parser_info

    def _cache_parser_info(
        self, *, path: tuple[str, ...], result_type: iir.Type, memoize: bool = False, inline_to_parent: bool = False
    ) -> ParserFn:
        try:
            return self.parsers[path]
        except KeyError:
            pass
        return self._make_parser_info(
            path=path, result_type=result_type, memoize=memoize, inline_to_parent=inline_to_parent
        )

    def _gen_parser_callable(
        self,
        *,
        path: tuple[str, ...],
        result_type: iir.Type,
        mutable_pos: bool = False,
        memoize: bool = False,
        inline_to_parent: bool = False,
    ) -> tuple[iir.Method, ParserFn]:
        parser_info = self._cache_parser_info(
            path=path, result_type=result_type, memoize=memoize, inline_to_parent=inline_to_parent
        )
        return_type = iir.Maybe.instantiate(
            value_type=self.ApplyResultType.instantiate(
                pos_type=self.pos_type,
                result_type=result_type,
            )
        )
        rule_callable = self.parser_class.def_method(
            name=parser_info.name,
            return_type=return_type,
            params=[
                iir.Param(
                    name="pos",
                    typ=self.pos_type,
                    ref_type=iir.RefType.BORROW,
                    mutable=mutable_pos,
                )
            ],
            mutable_self=False,
        )
        if memoize:
            assert parser_info.rule_id is not None  # noqa: S101
            assert parser_info.cache_name is not None  # noqa: S101
            memoizer = self.parser_class.def_method(
                name=parser_info.apply_name,
                return_type=return_type,
                params=[
                    iir.Param(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    )
                ],
                mutable_self=False,
            )
            memoizer.block.return_(
                iir.SelfExpr()
                .fld.packrat.load()
                .method.apply.call(
                    rule_callable=iir.SelfExpr().method[parser_info.name].bind(),
                    rule_id=iir.LiteralInt(typ=iir.IndexInt, value=parser_info.rule_id),
                    rule_cache=iir.SelfExpr().fld[parser_info.cache_name].load(),
                    pos=memoizer.get_param("pos").load(),
                )
            )
            cache_type = iir.GenericMutableHashmap.instantiate(
                key_type=self.pos_type,
                value_type=self._memo_type(result_type=result_type),
            )
            self.parser_class.def_field(
                name=parser_info.cache_name,
                typ=cache_type,
                init=iir.LiteralMapping(key_values=[]),
            )
        return rule_callable, parser_info

    def gen_item_parser(self, path: tuple[str, ...], node_type: iir.Type, item: gsm.Item) -> ParserFn:
        if item.quantifier.is_multiple():
            return self.gen_item_parser_multiple(path, node_type, item)
        else:
            return self.gen_item_parser_single_or_optional(path, node_type, item)

    def gen_item_parser_single_or_optional(
        self,
        path: tuple[str, ...],
        node_type: iir.Type,
        item: gsm.Item,
    ) -> ParserFn:
        """
        def item_parser_single_or_optional(self, pos):
            return <consume_term_expr>
        """
        consume_term = self._gen_consume_term_expr(path=path, node_type=node_type, term=item.term)
        result, parser_info = self._gen_parser_callable(
            path=path,
            result_type=consume_term.result_type,
            inline_to_parent=consume_term.inline_to_parent,
        )
        result.block.return_(consume_term.expr)
        return parser_info

    def gen_item_parser_multiple(
        self,
        path: tuple[str, ...],
        node_type: iir.Type,
        item: gsm.Item,
    ) -> ParserFn:
        """
        def item_parser_multiple(self, pos):
            result = node_type()
            while (one_result := <consume_term_expr>) is not None:
                pos = result.pos
                result.append_<label>(one_result.result)
            if constexpr item.quantifier.min() > gsm.Arity.ZERO:
                if not results:
                    return None
            return memo.ApplyResult(pos, results)
        """
        consume_term = self._gen_consume_term_expr(path=path, node_type=node_type, term=item.term)
        result_type = node_type
        return_type = self.ApplyResultType.instantiate(pos_type=self.pos_type, result_type=result_type)

        result, parser_info = self._gen_parser_callable(
            path=path,
            result_type=result_type,
            mutable_pos=True,
            inline_to_parent=True,
        )
        result_var = result.block.var(
            name="result",
            typ=result_type,
            ref_type=iir.RefType.VALUE,
            init=iir.Construct.make(
                result_type,
                span=iir.Construct.make(
                    self.TerminalSpanType,
                    start=result.get_param("pos").load(),
                    end=iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
            ),
        )
        loop = result.block.while_(
            condition=consume_term.expr,
            let=iir.Var(
                name="one_result",
                typ=iir.Auto,
                ref_type=iir.RefType.VALUE,
                mutable=True,
            ),
        )
        loop.block.assign(
            target=result.get_param("pos").store(),
            expr=loop.block.get_leaf_scope().lookup_as("one_result", iir.Var).load_mut().fld.pos.move(),
        )
        if consume_term.inline_to_parent:
            loop.block.expr_stmt(
                result_var.fld.children.method.extend.call(
                    loop.block.get_leaf_scope()
                    .lookup_as("one_result", iir.Var)
                    .load_mut()
                    .fld.result.fld.children.move()
                )
            )
        else:
            method = f"append_{item.label}" if item.label else "append"
            loop.block.expr_stmt(
                result_var.method[method].call(
                    child=loop.block.get_leaf_scope().lookup_as("one_result", iir.Var).load_mut().fld.result.move()
                )
            )
        if item.quantifier.min() != gsm.Arity.ZERO:
            result.block.if_(iir.IsEmpty(result_var.fld.children)).block.return_(iir.Failure(result_type))

        result.block.assign(
            result_var.fld.span,
            iir.Construct.make(
                self.TerminalSpanType,
                start=result_var.fld.span.fld.start,
                end=result.get_param("pos").load(),
            ),
        )
        result.block.return_(
            expr=iir.Success(
                return_type,
                iir.Construct.make(
                    return_type,
                    pos=result.get_param("pos").move(),
                    result=result_var.move(),
                ),
            )
        )
        return parser_info

    def gen_alternatives_parser(
        self,
        *,
        path: tuple[str, ...],
        node_type: iir.Type,
        alternatives: Sequence[gsm.Items],
        memoize: bool = False,
        current_rule: gsm.Rule | None = None,
    ) -> ParserFn:
        alternatives_parser, parser_info = self._gen_parser_callable(
            path=path,
            result_type=node_type,
            mutable_pos=False,
            memoize=memoize,
            inline_to_parent=True,
        )
        alternatives_pos_var = alternatives_parser.get_param("pos")
        return_type = self.ApplyResultType.instantiate(pos_type=self.pos_type, result_type=node_type)

        # Try each alternative in order, returning the first one that succeeds.
        for alt_idx, alternative in enumerate(alternatives):
            # Create a parser function for this alternative
            alt_name = f"alt{alt_idx}"
            alt_path = (*path, alt_name)
            alt_parser_info = self.gen_alternative_parser(alt_path, node_type, alternative, current_rule)
            # Call the alternative parser function
            alt_result_var = iir.Var(name=alt_name, typ=return_type, ref_type=iir.RefType.VALUE, mutable=True)
            alternatives_parser.block.if_(
                condition=iir.SelfExpr().method[alt_parser_info.apply_name].call(pos=alternatives_pos_var.load()),
                let=alt_result_var,
            ).block.return_(iir.Success(return_type, alt_result_var))

        # If none succeeded, return failure.
        alternatives_parser.block.return_(iir.Failure(return_type))

        return parser_info

    def gen_alternative_parser(
        self, path: tuple[str, ...], node_type: iir.Type, alternative: gsm.Items, current_rule: gsm.Rule | None = None
    ) -> ParserFn:
        alt_parser, alt_parser_info = self._gen_parser_callable(
            path=path, result_type=node_type, mutable_pos=True, inline_to_parent=True
        )
        alt_pos_var = alt_parser.get_param("pos")
        alt_result_var = alt_parser.block.var(
            name="result",
            typ=node_type,
            ref_type=iir.RefType.VALUE,
            mutable=True,
            init=iir.Construct.make(
                node_type,
                span=iir.Construct.make(
                    self.TerminalSpanType,
                    start=alt_parser.get_param("pos").load(),
                    end=iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
            ),
        )

        return_type = self.ApplyResultType.instantiate(pos_type=self.pos_type, result_type=node_type)

        # Process each item in the alternative in order by calling item parser functions.
        # Successful item parses are appended to alt_result_var.
        # Failed parses of non-optional items result in early Failure return.
        for item_idx, item in enumerate(alternative.items):
            if item.disposition == gsm.Disposition.INLINE:
                msg = "Inline items not yet supported: {item}"
                raise NotImplementedError(msg)
            # Create an item parser
            item_name = f"item{item_idx}"
            item_parser = self.gen_item_parser((*path, item_name), node_type, item)
            item_result_var = iir.Var(
                name=item_name,
                typ=self.ApplyResultType.instantiate(pos_type=self.pos_type, result_type=item_parser.result_type),
                ref_type=iir.RefType.VALUE,
                mutable=True,
            )
            # Call the item parser
            item_if = alt_parser.block.if_(
                condition=iir.SelfExpr().method[item_parser.apply_name].call(pos=alt_pos_var.load()),
                let=item_result_var,
                orelse=item.quantifier.is_required(),
            )
            # Handle item success
            item_if.block.assign(alt_pos_var.store(), item_result_var.fld.pos.move())
            if item.disposition != gsm.Disposition.SUPPRESS:
                if item_parser.inline_to_parent:
                    item_if.block.expr_stmt(
                        alt_result_var.fld.children.method.extend.call(item_result_var.fld.result.fld.children.move())
                    )
                else:
                    method_name = "append"
                    if item.label:
                        method_name += f"_{item.label}"
                    item_if.block.expr_stmt(
                        alt_result_var.method[method_name].call(child=item_result_var.fld.result.move())
                    )

            # Handle item failure
            if item.quantifier.is_required():
                assert isinstance(item_if.orelse, iir.Block)  # noqa: S101
                item_if.orelse.return_(iir.Failure(return_type))

            if (sep := alternative.sep_after[item_idx]) != gsm.Separator.NO_WS:
                item_ws_var = iir.Var(
                    name=f"ws_after__{item_name}",
                    typ=self.ApplyResultType.instantiate(
                        pos_type=self.pos_type,
                        result_type=self.TerminalSpanType,
                    ),
                    ref_type=iir.RefType.VALUE,
                    mutable=True,
                )
                # Choose trivia parsing strategy based on current rule
                if current_rule and current_rule.is_trivia_rule:
                    # For trivia rules, use basic regex to avoid recursion
                    trivia_pattern = r"\s+"
                    sep_if = alt_parser.block.if_(
                        condition=iir.SelfExpr().method.consume_regex.call(
                            pos=alt_pos_var.load(), regex=iir.LiteralString(trivia_pattern)
                        ),
                        let=item_ws_var,
                        orelse=(sep == gsm.Separator.WS_REQUIRED),
                    )
                    sep_if.block.assign(alt_pos_var.store(), item_ws_var.fld.pos.move())

                    # Conditionally create trivia node if capture_trivia is enabled
                    if self.context.capture_trivia:
                        trivia_construct = iir.Construct.make(
                            self.TriviaNodeType,
                            span=item_ws_var.fld.result.move(),
                        )
                        sep_if.block.expr_stmt(
                            alt_result_var.method.append.call(
                                child=trivia_construct,
                                label=iir.LiteralNull(),
                            )
                        )
                else:
                    # For non-trivia rules, use grammar-based trivia parsing
                    trivia_parser_info = self._cache_parser_info(
                        path=("trivia",),
                        result_type=self.TriviaNodeType,
                        memoize=True,
                    )
                    sep_if = alt_parser.block.if_(
                        condition=iir.SelfExpr().method[trivia_parser_info.apply_name].call(pos=alt_pos_var.load()),
                        let=item_ws_var,
                        orelse=(sep == gsm.Separator.WS_REQUIRED),
                    )
                    sep_if.block.assign(alt_pos_var.store(), item_ws_var.fld.pos.move())

                    # Conditionally add trivia node if capture_trivia is enabled
                    if self.context.capture_trivia:
                        sep_if.block.expr_stmt(
                            alt_result_var.method.append.call(
                                child=item_ws_var.fld.result.move(),
                                label=iir.LiteralNull(),
                            )
                        )

                if sep == gsm.Separator.WS_REQUIRED and isinstance(sep_if.orelse, iir.Block):
                    sep_if.orelse.return_(iir.Failure(return_type))

        # If we did not return early, then we succeeded.
        alt_parser.block.assign(
            alt_result_var.fld.span,
            iir.Construct.make(
                self.TerminalSpanType,
                start=alt_result_var.fld.span.fld.start,
                end=alt_parser.get_param("pos").load(),
            ),
        )
        alt_parser.block.return_(
            iir.Success(
                return_type,
                iir.Construct.make(return_type, pos=alt_pos_var.move(), result=alt_result_var.move()),
            )
        )
        return alt_parser_info
