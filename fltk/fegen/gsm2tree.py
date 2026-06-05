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

    def protocol_node_name(self, rule_name: str) -> str:
        """Rule name → Protocol class name.

        Protocol classes live in a separate *_cst_protocol.py module from concrete CST classes, so bare
        names (e.g. 'Rule') do not collide with the concrete 'Rule' dataclass — they are always
        module-qualified in annotations (e.g. cstp.Rule).  No suffix is needed.
        """
        return self.class_name_for_rule_node(rule_name)

    # TODO(cst-protocol-generator-refactor): this method mirrors py_annotation_for_model_types (gsm2tree.py:85)
    # and _protocol_class_for_model mirrors py_class_for_model (gsm2tree.py:109).  Unify both pairs with
    # shared skeletons parameterized by annotation resolver / Label body / method bodies / base class.
    def protocol_annotation_for_model_types(self, *, model_types: Iterable[ModelType], class_name: str = "") -> str:
        """Return a Python annotation string for model_types.

        Uses the bare Protocol class name (same as the concrete class name) for rule references, and
        library-type annotations for everything else.

        Quoting asymmetry is intentional: rule references are quoted strings (e.g. '"Rule"') because they are
        forward references to Protocol classes defined later in the same module, while library types (e.g.
        fltk.fegen.pyrt.terminalsrc.Span) are unquoted module paths resolved at import time.  The generated module
        carries `from __future__ import annotations`, which makes all annotations lazy, so the explicit quoting on
        rule refs is redundant there — but kept for clarity and consistency with how fltk_cst.py emits forward refs.
        """
        parts = []
        for model_type in model_types:
            if isinstance(model_type, str):
                # rule reference -> Protocol node name (quoted forward ref)
                parts.append(f'"{self.protocol_node_name(model_type)}"')
            else:
                # library type (Span, etc.) -> use the existing iir-to-annotation path (unquoted)
                iir_type = typemodel.lookup_type(model_type)
                parts.append(pycompiler.iir_type_to_py_annotation(iir_type, self.context))
        # Sort for deterministic output; quoted rule names (starting with '"') sort before unquoted library
        # paths alphabetically by ASCII order, but both categories are distinct and sort is stable within each.
        parts = sorted(set(parts))  # deduplicate then sort for deterministic Union member order
        if not parts:
            rule_ctx = f" for rule {class_name!r}" if class_name else ""
            msg = f"Rule node{rule_ctx} has no child types in its model; cannot generate annotation"
            raise ValueError(msg)
        if len(parts) > 1:
            return f"typing.Union[{', '.join(parts)}]"
        return parts[0]

    def gen_protocol_module(self) -> ast.Module:
        """Generate a *_cst_protocol.py module with Protocol classes describing the CST module surface."""
        module = ast.parse("")
        assert isinstance(module, ast.Module)  # noqa: S101
        module.body.append(pygen.stmt("from __future__ import annotations"))
        module.body.append(pygen.import_(("typing",)))
        module.body.append(pygen.import_(("fltk", "fegen", "pyrt", "terminalsrc")))

        for rule in self.rule_models:
            model = self.rule_models[rule]
            class_name = self.protocol_node_name(rule)
            module.body.append(self._protocol_class_for_model(class_name, model))

        module.body.append(self._cst_module_protocol())

        return module

    def _protocol_class_for_model(self, class_name: str, model: ItemsModel) -> ast.ClassDef:
        """Generate a Protocol class for a single CST node."""
        klass = pygen.klass(name=class_name, bases=["typing.Protocol"])

        labels = sorted(model.labels.keys())

        # Nested Label class (if this node has labels)
        if labels:
            label_class = pygen.klass(name="Label")
            for label in labels:
                # Use ClassVar[object] rather than ClassVar[Label] to avoid the
                # self-referential annotation that pyright flags as reportUndefinedVariable
                # inside the nested class body.  The only guarantee we need is attribute
                # presence (so label == self.cst.Items.Label.NO_WS typechecks); the exact
                # type of the constant is immaterial for Protocol-level checking.
                label_class.body.append(pygen.stmt(f"{label.upper()}: typing.ClassVar[object]"))
            klass.body.append(label_class)

        klass.body.append(pygen.stmt("span: fltk.fegen.pyrt.terminalsrc.Span"))

        child_annotation = self.protocol_annotation_for_model_types(model_types=model.types, class_name=class_name)

        if labels:
            klass.body.append(pygen.stmt(f"children: list[tuple[typing.Optional[Label], {child_annotation}]]"))
        else:
            # TODO(cst-protocol-label-free): label-free nodes use tuple[None, T] rather than
            # tuple[Label | None, T], creating an asymmetry with label-bearing nodes.  Generic
            # consumers iterating children of arbitrary node types must case-split on this.
            # Fix by introducing a vacuous Label class for label-free nodes or a module-level
            # _NoLabel alias so all children share the same tuple shape.
            klass.body.append(pygen.stmt(f"children: list[tuple[None, {child_annotation}]]"))

        label_annotation = "typing.Optional[Label]" if labels else "None"

        append_fn = pygen.function(
            "append", f"self, child: {child_annotation}, label: {label_annotation} = None", "None"
        )
        append_fn.body.append(pygen.stmt("..."))
        klass.body.append(append_fn)

        extend_fn = pygen.function(
            "extend", f"self, children: typing.Iterable[{child_annotation}], label: {label_annotation} = None", "None"
        )
        extend_fn.body.append(pygen.stmt("..."))
        klass.body.append(extend_fn)

        if labels:
            child_ret = f"tuple[typing.Optional[Label], {child_annotation}]"
        else:
            child_ret = f"tuple[None, {child_annotation}]"
        child_fn = pygen.function("child", "self", child_ret)
        child_fn.body.append(pygen.stmt("..."))
        klass.body.append(child_fn)

        for label in labels:
            label_type_annotation = self.protocol_annotation_for_model_types(
                model_types=model.labels[label], class_name=f"{class_name}.{label}"
            )

            # append_<label>
            fn = pygen.function(f"append_{label}", f"self, child: {label_type_annotation}", "None")
            fn.body.append(pygen.stmt("..."))
            klass.body.append(fn)

            # extend_<label>
            fn = pygen.function(f"extend_{label}", f"self, children: typing.Iterable[{label_type_annotation}]", "None")
            fn.body.append(pygen.stmt("..."))
            klass.body.append(fn)

            # children_<label>
            fn = pygen.function(f"children_{label}", "self", f"typing.Iterator[{label_type_annotation}]")
            fn.body.append(pygen.stmt("..."))
            klass.body.append(fn)

            # child_<label>
            fn = pygen.function(f"child_{label}", "self", label_type_annotation)
            fn.body.append(pygen.stmt("..."))
            klass.body.append(fn)

            # maybe_<label>
            fn = pygen.function(f"maybe_{label}", "self", f"typing.Optional[{label_type_annotation}]")
            fn.body.append(pygen.stmt("..."))
            klass.body.append(fn)

        return klass

    def _cst_module_protocol(self) -> ast.ClassDef:
        """Generate the CstModule Protocol describing the module-level surface."""
        klass = pygen.klass(name="CstModule", bases=["typing.Protocol"])
        for rule in self.rule_models:
            node_name = self.protocol_node_name(rule)
            class_name = self.class_name_for_rule_node(rule)
            # @property returning type[<NodeName>] — covariant, satisfies concrete module's class attribute
            prop_fn = pygen.function(class_name, "self", f"type[{node_name}]")
            # Add @property decorator
            prop_fn.decorator_list = [pygen.expr("property")]
            prop_fn.body.append(pygen.stmt("..."))
            klass.body.append(prop_fn)
        return klass

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
