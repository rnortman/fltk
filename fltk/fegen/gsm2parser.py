from dataclasses import dataclass
import itertools
from typing import Final, Iterable

from fltk.iir import model as iir
from fltk.iir.py import reg as pyreg
from fltk.fegen import gsm

ApplyResultType: Final = iir.Type.make(cname="ApplyResultType", params=dict(pos_type=iir.TYPE, result_type=iir.TYPE))
pyreg.register_type(pyreg.TypeInfo(typ=ApplyResultType, module=pyreg.Builtins, name="ApplyResultType"))

TerminalSpanType: Final = iir.Type.make(cname="TerminalSpan")
pyreg.register_type(pyreg.TypeInfo(typ=TerminalSpanType, module=pyreg.Builtins, name="Span"))


class ParserGenerator:
    def __init__(self, grammar: gsm.Grammar):
        self.grammar: Final = grammar
        if not self.grammar.vars:
            self.pos_type: Final = iir.UInt64
        else:
            raise NotImplementedError("Grammar vars not implemented")
        self.parser_class = iir.ClassType.make(
            cname="Parser",
            doc="Parser",
            defined_in=iir.Module.make(name="TODO(module)")
        )
        self.item_keys: dict[gsm.Item, str] = dict()
        self.key_items: dict[str, gsm.Item] = dict()

    def get_item_key(self, item: gsm.Item) -> str:
        try:
            return self.item_keys[item]
        except KeyError:
            pass
        label = item.label or "anonitem"
        try:
            for i in itertools.count():
                key = f"{label}{i}"
                self.key_items[key]
        except KeyError:
            pass
        self.key_items[key] = item
        self.item_keys[item] = key
        return key

    def gen_consume_term_expr(
        self,
        term: gsm.Term,
        pos_expr: iir.Expr,
        terminalsrc_expr: iir.Expr,
    ) -> tuple[iir.Expr,
               iir.Type]:
        if isinstance(term, gsm.Literal):
            return (
                terminalsrc_expr.method.consume_literal.call(
                    pos=pos_expr,
                    literal=iir.LiteralString(term.value),
                ),
                TerminalSpanType
            )
        raise NotImplementedError(f"Term type {term}")

    def gen_item_parser(self, item: gsm.Item) -> Iterable[iir.Method]:
        base_name: Final = f"parse_item__{self.get_item_key(item)}"
        pos_param = iir.Param(name="pos", typ=self.pos_type, ref_type=iir.RefType.BORROW, mutable=False)
        consume_term_expr, term_result_type = self.gen_consume_term_expr(
            term=item.term,
            pos_expr=pos_param.load(),
            terminalsrc_expr=iir.SelfExpr().fld.pos.load(),
        )
        if item.quantifier.max() == gsm.Arity.MULTIPLE:
            yield from self.gen_item_parser_multiple(item, base_name, pos_param, consume_term_expr, term_result_type)
        else:
            yield from self.gen_item_parser_single_or_optional(
                item,
                base_name,
                pos_param,
                consume_term_expr,
                term_result_type
            )

    def gen_item_parser_single_or_optional(
        self,
        item: gsm.Item,
        base_name: str,
        pos_param: iir.Param,
        consume_term_expr: iir.Expr,
        term_result_type: iir.Type
    ) -> Iterable[iir.Method]:
        """
        def item_parser_single_or_optional(self, pos):
            return self.consume_term(pos) # Customized to be the correct term type
        """
        if item.quantifier.min() == gsm.Arity.ZERO:
            term_result_type = iir.Maybe.instantiate(value_type=term_result_type)
        result = self.parser_class.def_method(
            name=base_name,
            return_type=ApplyResultType.instantiate(
                pos_type=self.pos_type,
                result_type=term_result_type,
            ),
            params=(pos_param,
                   ),
            mutable_self=False,
        )
        result.block.return_(expr=consume_term_expr)
        return (result, )

    def gen_item_parser_multiple(
        self,
        item: gsm.Item,
        base_name: str,
        pos_param: iir.Param,
        consume_term_expr: iir.Expr,
        term_result_type: iir.Type
    ) -> Iterable[iir.Method]:
        """
        def item_parser_multiple(self, pos):
            results = []
            while (result := self.consume_term(pos)) is not None:
                pos = result.pos
                results.append(result.result)
            if constexpr item.quantifier.min() > gsm.Arity.ZERO:
                if not results:
                    return None
            return memo.ApplyResult(pos, results)
        """
        result_type = iir.GenericImmutableSequence.instantiate(value_type=term_result_type)
        result = self.parser_class.def_method(
            name=base_name,
            return_type=ApplyResultType.instantiate(
                pos_type=self.pos_type,
                result_type=result_type,
            ),
            params=(iir.Param(name="pos",
                              typ=self.pos_type,
                              ref_type=iir.RefType.BORROW,
                              mutable=False),
                   ),
            mutable_self=False,
        )
        results_var = result.block.var(
            name="results",
            typ=result_type,
            ref_type=iir.RefType.VALUE,
            init=iir.Construct.make(result_type),
        )
        loop = result.block.while_(
            iir.CheckAndExtractResult(
                result=consume_term_expr,
                var=iir.Var(name='result',
                            typ=iir.Auto,
                            ref_type=iir.RefType.VALUE,
                            mutable=True)
            )
        )
        loop.block.assign(
            target=result.get_param("pos").store(),
            expr=loop.block.get_leaf_scope().lookup_as('result',
                                                       iir.Var).load_mut().fld.pos.move()
        )
        loop.block.expr_stmt(
            results_var.load().method.append.call(
                loop.block.get_leaf_scope().lookup_as('result',
                                                      iir.Var).load_mut().fld.result.move()
            )
        )
        if item.quantifier.min() != gsm.Arity.ZERO:
            loop.block.if_(iir.IsEmpty(results_var)).block.return_(iir.Failure(result_type))

        result.block.return_(
            expr=iir.Success(
                result_type,
                iir.Construct.make(result_type,
                                   pos=result.get_param("pos").move(),
                                   value=results_var.move())
            )
        )
        yield result
        return
