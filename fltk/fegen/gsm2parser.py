from dataclasses import dataclass
import itertools
from typing import Final, Iterable, Optional, Sequence

from fltk.iir import model as iir
from fltk.iir.py import reg as pyreg
from fltk.fegen import gsm, gsm2tree

ApplyResultType: Final = iir.Type.make(
    cname="ApplyResultType", params=dict(pos_type=iir.TYPE, result_type=iir.TYPE)
)
pyreg.register_type(
    pyreg.TypeInfo(
        typ=ApplyResultType,
        module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        name="ApplyResult",
    )
)

TerminalSpanType: Final = iir.Type.make(cname="TerminalSpan")
pyreg.register_type(
    pyreg.TypeInfo(
        typ=TerminalSpanType,
        module=pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
        name="Span",
    )
)

MemoEntryType: Final = iir.Type.make(
    cname="MemoEntry",
    params=dict(RuleId=iir.TYPE, PosType=iir.TYPE, ResultType=iir.TYPE),
)
pyreg.register_type(
    pyreg.TypeInfo(
        typ=MemoEntryType,
        module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        name="MemoEntry",
    )
)

ErrorTrackerType: Final = iir.Type.make(
    cname="ErrorTracker",
    params=dict(RuleId=iir.TYPE),
)
pyreg.register_type(
    pyreg.TypeInfo(
        typ=ErrorTrackerType,
        module=pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        name="ErrorTracker",
    )
)


class ParserGenerator:
    @dataclass
    class ParserFn:
        name: str
        apply_name: str
        cache_name: Optional[str]
        result_type: iir.Type
        rule_id: Optional[int]

    def __init__(self, grammar: gsm.Grammar, cstgen: gsm2tree.CstGenerator):
        self.grammar: Final = grammar
        self.cstgen = cstgen
        if not self.grammar.vars:
            self.pos_type: Final = iir.SignedIndexInt
        else:
            raise NotImplementedError("Grammar vars not implemented")

        self.parser_class = iir.ClassType.make(
            cname="Parser",
            doc="Parser",
            defined_in=iir.Module.make(name="TODO(module)"),
        )

        packrat_type = iir.Type.make(cname="Packrat")
        pyreg.register_type(
            pyreg.TypeInfo(
                typ=packrat_type,
                module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
                name="Packrat",
            )
        )

        self.parser_class.def_field(
            name="packrat", typ=packrat_type, init=iir.Construct.make(packrat_type)
        )

        terminalsrc_type = iir.Type.make(cname="TerminalSource")
        pyreg.register_type(
            pyreg.TypeInfo(
                typ=terminalsrc_type,
                module=pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
                name="TerminalSource",
            )
        )
        terminalsrc_fld = self.parser_class.def_field(
            name="terminalsrc", typ=terminalsrc_type, init=None
        )

        ErrorTracker = ErrorTrackerType.instantiate(RuleId=iir.IndexInt)
        self.parser_class.def_field(
            name="error_tracker",
            typ=ErrorTracker,
            init=iir.Construct.make(ErrorTracker),
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

        span_result_type = ApplyResultType.instantiate(
            pos_type=self.pos_type, result_type=TerminalSpanType
        )
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
        span_var = iir.Var(
            name="span", typ=TerminalSpanType, ref_type=iir.RefType.VALUE, mutable=False
        )
        consume_literal.block.if_(
            condition=iir.SelfExpr().fld.terminalsrc.method.consume_literal.call(
                pos=consume_literal.get_param("pos").load(),
                literal=consume_literal.get_param("literal").load(),
            ),
            let=span_var,
        ).block.return_(
            iir.Success(
                span_result_type,
                iir.Construct.make(
                    span_result_type, pos=span_var.fld.end, result=span_var.load()
                ),
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
        span_var = iir.Var(
            name="span", typ=TerminalSpanType, ref_type=iir.RefType.VALUE, mutable=False
        )
        consume_regex.block.if_(
            condition=iir.SelfExpr().fld.terminalsrc.method.consume_regex.call(
                pos=consume_regex.get_param("pos").load(),
                regex=consume_regex.get_param("regex").load(),
            ),
            let=span_var,
        ).block.return_(
            iir.Success(
                span_result_type,
                iir.Construct.make(
                    span_result_type, pos=span_var.fld.end, result=span_var.load()
                ),
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

        self.item_keys: dict[gsm.Item, str] = dict()
        self.key_items: dict[str, gsm.Item] = dict()

        self.parsers: dict[tuple[str, ...], ParserGenerator.ParserFn] = dict()
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
            )

    def _memo_type(self, result_type: iir.Type) -> iir.Type:
        return MemoEntryType.instantiate(
            RuleId=iir.IndexInt, PosType=self.pos_type, ResultType=result_type
        )

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

    def _gen_consume_term_expr(
        self,
        path: tuple[str, ...],
        node_type: iir.Type,
        term: gsm.Term,
    ) -> tuple[iir.Expr, iir.Type]:
        if isinstance(term, gsm.Identifier):
            parser_fn = self.parsers[(term.value,)]
            return (
                iir.SelfExpr()
                .method[parser_fn.apply_name]
                .call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load()
                ),
                parser_fn.result_type,
            )
        if isinstance(term, gsm.Literal):
            return (
                iir.SelfExpr().method.consume_literal.call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load(),
                    literal=iir.LiteralString(term.value),
                ),
                TerminalSpanType,
            )
        if isinstance(term, gsm.Regex):
            # TODO pre-compile regexes
            return (
                iir.SelfExpr().method.consume_regex.call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load(),
                    regex=iir.LiteralString(term.value),
                ),
                TerminalSpanType,
            )
        if isinstance(term, Sequence):
            parser_fn = self.gen_alternatives_parser(
                path=path + ("alts",), node_type=node_type, alternatives=term
            )
            return (
                iir.SelfExpr()
                .method[parser_fn.apply_name]
                .call(
                    pos=iir.VarByName(
                        name="pos",
                        typ=self.pos_type,
                        ref_type=iir.RefType.BORROW,
                        mutable=False,
                    ).load()
                ),
                parser_fn.result_type,
            )

        raise NotImplementedError(f"Term type {term}")

    def _apply_rule_method_name(self, rule_name: str) -> str:
        return f"apply__{rule_name}"

    def _make_parser_info(
        self, path: tuple[str, ...], result_type: iir.Type, memoize: bool = False
    ) -> ParserFn:
        base_name = f"parse_{'__'.join(path)}"
        parser_info = ParserGenerator.ParserFn(
            name=base_name,
            apply_name=self._apply_rule_method_name(base_name)
            if memoize
            else base_name,
            cache_name=f"_cache__{base_name}" if memoize else None,
            result_type=result_type,
            rule_id=next(self.rule_id_seq) if memoize else None,
        )
        assert path not in self.parsers
        self.parsers[path] = parser_info
        return parser_info

    def _cache_parser_info(
        self, path: tuple[str, ...], result_type: iir.Type, memoize: bool = False
    ) -> ParserFn:
        try:
            return self.parsers[path]
        except KeyError:
            pass
        return self._make_parser_info(path, result_type, memoize)

    def _gen_parser_callable(
        self,
        path: tuple[str, ...],
        result_type: iir.Type,
        mutable_pos: bool = False,
        memoize: bool = False,
    ) -> tuple[iir.Method, ParserFn]:
        parser_info = self._cache_parser_info(path, result_type, memoize)
        return_type = iir.Maybe.instantiate(
            value_type=ApplyResultType.instantiate(
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
            assert parser_info.rule_id is not None
            assert parser_info.cache_name is not None
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
                init=iir.Construct.make(typ=cache_type),
            )
        return rule_callable, parser_info

    def gen_item_parser(
        self, path: tuple[str, ...], node_type: iir.Type, item: gsm.Item
    ) -> ParserFn:
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
        consume_term_expr, term_result_type = self._gen_consume_term_expr(
            path=path, node_type=node_type, term=item.term
        )
        result, parser_info = self._gen_parser_callable(
            path=path,
            result_type=term_result_type,
        )
        result.block.return_(consume_term_expr)
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
        consume_term_expr, term_result_type = self._gen_consume_term_expr(
            path=path, node_type=node_type, term=item.term
        )
        result_type = node_type
        return_type = ApplyResultType.instantiate(
            pos_type=self.pos_type, result_type=result_type
        )

        result, parser_info = self._gen_parser_callable(
            path=path,
            result_type=result_type,
            mutable_pos=True,
        )
        result_var = result.block.var(
            name="result",
            typ=result_type,
            ref_type=iir.RefType.VALUE,
            init=iir.Construct.make(
                result_type,
                span=iir.Construct.make(
                    TerminalSpanType,
                    start=result.get_param("pos").load(),
                    end=iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
            ),
        )
        loop = result.block.while_(
            condition=consume_term_expr,
            let=iir.Var(
                name="one_result",
                typ=iir.Auto,
                ref_type=iir.RefType.VALUE,
                mutable=True,
            ),
        )
        loop.block.assign(
            target=result.get_param("pos").store(),
            expr=loop.block.get_leaf_scope()
            .lookup_as("one_result", iir.Var)
            .load_mut()
            .fld.pos.move(),
        )
        if term_result_type is node_type:
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
                    child=loop.block.get_leaf_scope()
                    .lookup_as("one_result", iir.Var)
                    .load_mut()
                    .fld.result.move()
                )
            )
        if item.quantifier.min() != gsm.Arity.ZERO:
            loop.block.if_(iir.IsEmpty(result_var.fld.children)).block.return_(
                iir.Failure(result_type)
            )

        result.block.assign(
            result_var.fld.span,
            iir.Construct.make(
                TerminalSpanType,
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
        path: tuple[str, ...],
        node_type: iir.Type,
        alternatives: Sequence[gsm.Items],
        memoize: bool = False,
    ) -> ParserFn:
        alternatives_parser, parser_info = self._gen_parser_callable(
            path=path,
            result_type=node_type,
            mutable_pos=False,
            memoize=memoize,
        )
        alternatives_pos_var = alternatives_parser.get_param("pos")
        return_type = ApplyResultType.instantiate(
            pos_type=self.pos_type, result_type=node_type
        )

        # Try each alternative in order, returning the first one that succeeds.
        for alt_idx, alternative in enumerate(alternatives):
            # Create a parser function for this alternative
            alt_name = f"alt{alt_idx}"
            alt_path = path + (alt_name,)
            alt_parser_info = self.gen_alternative_parser(
                alt_path, node_type, alternative
            )
            # Call the alternative parser function
            alt_result_var = iir.Var(
                name=alt_name, typ=return_type, ref_type=iir.RefType.VALUE, mutable=True
            )
            alt_if = alternatives_parser.block.if_(
                condition=iir.SelfExpr()
                .method[alt_parser_info.apply_name]
                .call(pos=alternatives_pos_var.load()),
                let=alt_result_var,
            ).block.return_(iir.Success(return_type, alt_result_var))

        # If none succeeded, return failure.
        alternatives_parser.block.return_(iir.Failure(return_type))

        return parser_info

    def gen_alternative_parser(
        self, path: tuple[str, ...], node_type: iir.Type, alternative: gsm.Items
    ) -> ParserFn:
        alt_parser, alt_parser_info = self._gen_parser_callable(
            path=path, result_type=node_type, mutable_pos=True
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
                    TerminalSpanType,
                    start=alt_parser.get_param("pos").load(),
                    end=iir.LiteralInt(iir.SignedIndexInt, -1),
                ),
            ),
        )

        return_type = ApplyResultType.instantiate(
            pos_type=self.pos_type, result_type=node_type
        )

        # Process each item in the alternative in order by calling item parser functions.
        # Successful item parses are appended to alt_result_var.
        # Failed parses of non-optional items result in early Failure return.
        for item_idx, item in enumerate(alternative.items):
            if item.disposition == gsm.Disposition.INLINE:
                raise NotImplementedError("Inline items not yet supported: {item}")
            # Create an item parser
            item_name = item.label if item.label else f"item{item_idx}"
            item_parser = self.gen_item_parser(path + (item_name,), node_type, item)
            item_result_var = iir.Var(
                name=item_name,
                typ=ApplyResultType.instantiate(
                    pos_type=self.pos_type, result_type=item_parser.result_type
                ),
                ref_type=iir.RefType.VALUE,
                mutable=True,
            )
            # Call the item parser
            item_if = alt_parser.block.if_(
                condition=iir.SelfExpr()
                .method[item_parser.apply_name]
                .call(pos=alt_pos_var.load()),
                let=item_result_var,
                orelse=item.quantifier.is_required(),
            )
            # Handle item success
            item_if.block.assign(alt_pos_var.store(), item_result_var.fld.pos.move())
            if item.disposition != gsm.Disposition.SUPPRESS:
                if item_parser.result_type is node_type:
                    item_if.block.expr_stmt(
                        alt_result_var.fld.children.method.extend.call(
                            item_result_var.fld.result.fld.children.move()
                        )
                    )
                else:
                    method_name = "append"
                    if item.label:
                        method_name += f"_{item.label}"
                    item_if.block.expr_stmt(
                        alt_result_var.method[method_name].call(
                            child=item_result_var.fld.result.move()
                        )
                    )

            # Handle item failure
            if item.quantifier.is_required():
                assert isinstance(item_if.orelse, iir.Block)
                item_if.orelse.return_(iir.Failure(return_type))

            if alternative.ws_after[item_idx]:
                item_ws_var = iir.Var(
                    name=f"ws_after__{item_name}",
                    typ=ApplyResultType.instantiate(
                        pos_type=self.pos_type,
                        result_type=TerminalSpanType,
                    ),
                    ref_type=iir.RefType.VALUE,
                    mutable=True,
                )
                alt_parser.block.if_(
                    condition=iir.SelfExpr().method.consume_regex.call(
                        pos=alt_pos_var.load(), regex=iir.LiteralString(r"\s+")
                    ),
                    let=item_ws_var,
                ).block.assign(alt_pos_var.store(), item_ws_var.fld.pos.move())

        # If we did not return early, then we succeeded.
        alt_parser.block.assign(
            alt_result_var.fld.span,
            iir.Construct.make(
                TerminalSpanType,
                start=alt_result_var.fld.span.fld.start,
                end=alt_parser.get_param("pos").load(),
            ),
        )
        alt_parser.block.return_(
            iir.Success(
                return_type,
                iir.Construct.make(
                    return_type, pos=alt_pos_var.move(), result=alt_result_var.move()
                ),
            )
        )
        return alt_parser_info
