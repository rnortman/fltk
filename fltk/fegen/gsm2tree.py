from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fltk import pygen
from fltk.fegen import gsm
from fltk.iir import model as iir
from fltk.iir import typemodel
from fltk.iir.py import compiler as pycompiler
from fltk.iir.py import reg as pyreg

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext

ModelType = str | typemodel.TypeKey


@dataclass()
class ItemsModel:
    labels: MutableMapping[str, set[ModelType]] = field(default_factory=lambda: defaultdict(set))
    types: set[ModelType] = field(default_factory=set)

    def incorporate(self, other: ItemsModel):
        for label, models in other.labels.items():
            self.labels[label] |= models
        self.types |= other.types


class CstGenerator:
    def __init__(self, grammar: gsm.Grammar, py_module: pyreg.Module, context: CompilerContext):
        self.grammar = grammar
        self.py_module = py_module
        self.context = context
        self.rule_models: dict[str, ItemsModel] = {}
        self.iir_types: dict[str, iir.Type] = {}

        self.Span = iir.Type.make(cname="Span")

        for rule in self.grammar.rules:
            self.rule_models[rule.name] = self.model_for_rule(rule, [])

    def class_name_for_rule_node(self, rule_name: str) -> str:
        return "".join(part.capitalize() for part in rule_name.lower().split("_"))

    def rule_has_whitespace_separators(self, rule: gsm.Rule) -> bool:
        """Check if a rule has any whitespace separators that would allow trivia."""
        return self._check_items_for_whitespace_separators(rule.alternatives)

    def _check_items_for_whitespace_separators(self, alternatives_list: Sequence[gsm.Items]) -> bool:
        """Recursively check Items for whitespace separators, including in sub-expressions."""
        for alternatives in alternatives_list:
            if alternatives.initial_sep in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
                return True

            for separator in alternatives.sep_after:
                if separator in (gsm.Separator.WS_REQUIRED, gsm.Separator.WS_ALLOWED):
                    return True

            for item in alternatives.items:
                if isinstance(item.term, list):  # Sub-expression is a list of Items
                    if self._check_items_for_whitespace_separators(item.term):
                        return True
        return False

    def iir_type_for_rule(self, rule_name: str) -> iir.Type:
        try:
            return self.iir_types[rule_name]
        except KeyError:
            pass
        name = self.class_name_for_rule_node(rule_name)
        typ = iir.Type.make(cname=name)
        self.context.python_type_registry.register_type(pyreg.TypeInfo(typ=typ, module=self.py_module, name=name))
        self.iir_types[rule_name] = typ
        return typ

    def iir_type_for_model_type(self, model_type: ModelType) -> iir.Type:
        if isinstance(model_type, str):
            return self.iir_type_for_rule(model_type)
        return typemodel.lookup_type(model_type)

    def py_annotation_for_model_types(self, *, model_types: Iterable[ModelType], in_module: bool = False) -> str:
        iir_types = [self.iir_type_for_model_type(model_type) for model_type in model_types]
        assert len(iir_types) > 0  # noqa: S101
        py_types = sorted(pycompiler.iir_type_to_py_annotation(typ, self.context) for typ in iir_types)
        if in_module:
            py_types = sorted(f'"{typ.removeprefix(".".join(self.py_module.import_path) + ".")}"' for typ in py_types)
        if len(py_types) > 1:
            return f"typing.Union[{', '.join(py_types)}]"
        return py_types[0]

    def gen_py_module(self) -> ast.Module:
        imports = [
            pyreg.Module(("dataclasses",)),
            pyreg.Module(("enum",)),
            pyreg.Module(("typing",)),
            pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
        ]
        module = pygen.module(module.import_path for module in imports)

        for rule, model in self.rule_models.items():
            module.body.append(self.py_class_for_model(self.class_name_for_rule_node(rule), model))

        return module

    def py_class_for_model(self, class_name: str, model: ItemsModel) -> ast.ClassDef:
        klass = pygen.dataclass(class_name)

        label_enum = pygen.klass(name="Label", bases=["enum.Enum"])
        labels = sorted(model.labels.keys())
        for label in labels:
            label_enum.body.append(pygen.stmt(f"{label.upper()} = enum.auto()"))
        klass.body.append(label_enum)
        if not model.types:
            msg = (
                f"Model class `{class_name}` "
                "would have no members; ensure there is at least one term included in the model."
            )
            raise RuntimeError(msg)
        child_annotation = self.py_annotation_for_model_types(model_types=model.types, in_module=True)
        klass.body.extend(
            [
                pygen.stmt("span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan"),
                pygen.stmt(
                    f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"
                    " = dataclasses.field(default_factory=list)"
                ),
            ]
        )

        child_annotation_by_labels = {
            label: self.py_annotation_for_model_types(model_types=types, in_module=True)
            for label, types in model.labels.items()
        }
        append_fn = pygen.function(
            "append",
            f"self, child: {child_annotation}, label: typing.Optional[Label] = None",
            "None",
        )
        append_fn.body.append(pygen.stmt("self.children.append((label, child))"))
        klass.body.append(append_fn)

        extend_fn = pygen.function(
            "extend",
            f"self, children: typing.Iterable[{child_annotation}], label: typing.Optional[Label] = None",
            "None",
        )
        extend_fn.body.append(pygen.stmt("self.children.extend((label, child) for child in children)"))
        klass.body.append(extend_fn)

        child_fn = pygen.function("child", "self", f"tuple[typing.Optional[Label], {child_annotation}]")
        child_fn.body.extend(
            [
                pygen.if_(
                    pygen.expr("(n := len(self.children)) != 1"),
                    [
                        pygen.stmt('msg = f"Expected one child but have {n}"'),
                        pygen.stmt("raise ValueError(msg)"),
                    ],
                    (),
                ),
                pygen.stmt("return self.children[0]"),
            ]
        )
        klass.body.append(child_fn)

        for label in labels:
            append_fn = pygen.function(
                f"append_{label}",
                f"self, child: {child_annotation_by_labels[label]}",
                "None",
            )
            append_fn.body.append(pygen.stmt(f"self.children.append(({class_name}.Label.{label.upper()}, child))"))
            klass.body.append(append_fn)

            extend_fn = pygen.function(
                f"extend_{label}",
                f"self, children: typing.Iterable[{child_annotation_by_labels[label]}]",
                "None",
            )
            extend_fn.body.append(
                pygen.stmt(f"self.children.extend(({class_name}.Label.{label.upper()}, child) for child in children)")
            )
            klass.body.append(extend_fn)

            children_fn = pygen.function(
                f"children_{label}",
                "self",
                f"typing.Iterator[{child_annotation_by_labels[label]}]",
            )
            if len(model.types) > 1:
                child_expr = f"typing.cast({child_annotation_by_labels[label]}, child)"
            else:
                child_expr = "child"
            children_fn.body.append(
                pygen.stmt(
                    f"return ({child_expr} for label, child in self.children"
                    f" if label == {class_name}.Label.{label.upper()})"
                )
            )
            klass.body.append(children_fn)

            child_fn = pygen.function(f"child_{label}", "self", f"{child_annotation_by_labels[label]}")
            child_fn.body.extend(
                [
                    pygen.stmt(f"children = list(self.children_{label}())"),
                    pygen.if_(
                        pygen.expr("(n := len(children)) != 1"),
                        [
                            pygen.stmt(f'msg = f"Expected one {label} child but have {{n}}"'),
                            pygen.stmt("raise ValueError(msg)"),
                        ],
                        (),
                    ),
                    pygen.stmt("return children[0]"),
                ]
            )
            klass.body.append(child_fn)

            maybe_fn = pygen.function(
                f"maybe_{label}",
                "self",
                f"typing.Optional[{child_annotation_by_labels[label]}]",
            )
            maybe_fn.body.extend(
                [
                    pygen.stmt(f"children = list(self.children_{label}())"),
                    pygen.if_(
                        pygen.expr("(n := len(children)) > 1"),
                        [
                            pygen.stmt(f'msg = f"Expected at most one {label} child but have {{n}}"'),
                            pygen.stmt("raise ValueError(msg)"),
                        ],
                        (),
                    ),
                    pygen.stmt("return children[0] if children else None"),
                ]
            )
            klass.body.append(maybe_fn)

        return klass

    def model_for_item(self, item: gsm.Item, inline_stack: list[str]) -> ItemsModel:
        if isinstance(item.term, gsm.Identifier):
            if item.term.value not in self.grammar.identifiers:
                msg = f"Identifier {item.term.value} not in grammar"
                raise ValueError(msg)
            return ItemsModel(types={item.term.value})
        if isinstance(item.term, gsm.Literal | gsm.Regex):
            return ItemsModel(types={self.Span.key})
        if isinstance(item.term, Sequence):
            return self.model_for_alternatives(item.term, inline_stack)
        msg = f"Term type {item.term}"
        raise NotImplementedError(msg)

    def model_for_items(self, items: gsm.Items, inline_stack: list[str]) -> ItemsModel:
        model = ItemsModel()
        for item in items.items:
            if item.disposition == gsm.Disposition.SUPPRESS:
                assert not isinstance(item.term, Sequence)  # noqa: S101
                continue
            if item.disposition == gsm.Disposition.INLINE:
                assert isinstance(item.term, gsm.Identifier)  # noqa: S101
                inline_rule = self.grammar.identifiers[item.term.value]
                assert isinstance(inline_rule, gsm.Rule)  # noqa: S101
                inline_model = self.model_for_rule(inline_rule, inline_stack)
                model.incorporate(inline_model)
            else:
                item_model = self.model_for_item(item, inline_stack)
                model.incorporate(item_model)
                if item.label:
                    assert not isinstance(item.term, Sequence)  # noqa: S101
                    model.labels[item.label] |= item_model.types
        return model

    def model_for_alternatives(self, alternatives: Iterable[gsm.Items], inline_stack: list[str]) -> ItemsModel:
        model = ItemsModel()
        for alternative in alternatives:
            model.incorporate(self.model_for_items(alternative, inline_stack))
        return model

    def model_for_rule(self, rule: gsm.Rule, inline_stack: list[str]) -> ItemsModel:
        if rule.name in inline_stack:
            msg = f"Recursive cycle of inlined rules: {[*inline_stack, rule.name]}"
            raise ValueError(msg)
        inline_stack.append(rule.name)
        try:
            return self.rule_models[rule.name]
        except KeyError:
            pass
        model = self.model_for_alternatives(rule.alternatives, inline_stack)

        if self.rule_has_whitespace_separators(rule):
            if rule.is_trivia_rule:
                model.incorporate(ItemsModel(types={self.Span.key}))
            else:
                model.incorporate(ItemsModel(types={"_trivia"}))

        self.rule_models[rule.name] = model
        return self.rule_models[rule.name]
