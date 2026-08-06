"""Python AST emitter: turns an ``AstModel`` into a self-contained ``<base>_ast.py``.

Emission is direct source-text generation rather than IIR: the AST module needs no type
registry.  Generated source is normalised by the usual regen -> ``make fix`` -> commit flow.

The emitted module holds one dataclass per product, terminal-only and enum-shaped rule,
payload dataclasses plus a union alias per sum rule, a chain-link dataclass plus a union
alias per fold rule, union aliases for labels carrying more than one type, and the
converters in both directions: ``from_cst``/``to_cst`` members on every class plus
module-level ``<rule>_from_cst`` / ``<rule>_to_cst`` for every rule.  A ``parse`` and an
``unparse`` convenience appear when a parser and an unparser module are named.

What each converter does is decided by ``ast_model``; this module only spells the decisions
as Python.  Anything here that reasons about grammar shape rather than about Python source
belongs in the model, where the Rust emitter reads it too.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence
from typing import TypeAlias

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import grammar_shape as gshape
from fltk.fegen import naming

_MODULE_DOCSTRING = '''"""Generated AST node classes and CST converters.  Do not edit.

Every class carries a ``span`` locating it in the source.  Spans never take part in
equality, so two values converted from identical text at different offsets — or in
different files — compare equal.  Node classes are plain mutable dataclasses: build them by
hand, mutate them in place, compare them by value.
"""'''

_SPAN_TYPE = "fltk.fegen.pyrt.span_protocol.SpanProtocol"

# ``LabelCount`` bounds saturate at 2, so a maximum of 2 means "unbounded".
_SATURATED_COUNT = 2

# The width of a Python ``float``: a coercion declaring anything narrower needs its values kept
# rounded to what the Rust field of that width holds.
_NATIVE_FLOAT_BITS = 64


def _python_path(path: str | None, rule_name: str, statement: str, entry: str) -> str:
    """A sidecar entry's Python path, checked for what the generated module needs of it.

    The module names the whole path and imports everything before its last component, so an
    entry that is missing or names a bare identifier cannot be emitted at all.
    """
    if path is None:
        msg = (
            f"rule '{rule_name}': `{statement}` names no `{entry}:` type, so the Python AST "
            f"module has nothing to reference"
        )
        raise ValueError(msg)
    if "." not in path:
        msg = (
            f"rule '{rule_name}': `{statement}` entry {entry} = {path!r} must be a dotted path "
            f"so the generated module can import the type's module"
        )
        raise ValueError(msg)
    return path


def _tuple_literal(members: Sequence[str]) -> str:
    return f"({', '.join(members)},)" if members else "()"


def _frozenset_literal(names: Iterable[str]) -> str:
    members = ", ".join(f'"{name}"' for name in sorted(names))
    return f"frozenset({{{members}}})" if members else "frozenset()"


def _type_tuple(members: Sequence[str]) -> str:
    """One class, or a tuple of them — either spelling is a usable ``isinstance`` argument."""
    return members[0] if len(members) == 1 else f"({', '.join(members)})"


def _count(bound: float) -> str:
    """A synthesis bound, as the cursor's own spelling of it."""
    return "astrt.UNBOUNDED" if bound == math.inf else str(int(bound))


_SCALAR_CLASS = {
    am.ScalarKind.TEXT: "str",
    am.ScalarKind.BOOL: "bool",
    am.ScalarKind.SPAN: "terminalsrc.Span",
}

_Values: TypeAlias = Callable[[am.Field], str]
"""Where a converter body reads one field's value from."""


def _member_values(field: am.Field) -> str:
    return f"self.{field.name}"


def _parameter_values(_field: am.Field) -> str:
    """An erased rule's helper takes its one payload as a parameter, not off a node."""
    return "value"


def _hoisted_values(field: am.Field) -> str:
    """A flattened wrapper's helper takes each hoisted field as its own parameter.

    The names are prefixed so that a field called ``astrt`` or ``cst`` cannot shadow anything
    the generated body references.
    """
    return f"_f_{field.name}"


class AstGenerator:
    """Emits the Python AST module for one grammar's model."""

    def __init__(
        self,
        model: am.AstModel,
        cst_module_name: str,
        parser_module_name: str | None = None,
        unparser_module_name: str | None = None,
        goal_rule: str | None = None,
    ) -> None:
        self.model = model
        self.cst_module_name = cst_module_name
        self.parser_module_name = parser_module_name
        self.unparser_module_name = unparser_module_name
        self.goal_rule = am.resolve_goal_rule(model, goal_rule)
        self.rule_of_type = model.rule_of_type
        self.lines: list[str] = []

    def emit(self, *lines: str) -> None:
        self.lines.extend(lines)

    def separate(self) -> None:
        """Open a new top-level definition."""
        self.lines.extend(("", ""))

    def cst_class(self, rule_name: str) -> str:
        """The CST node class for a rule, as the CST emitter names it."""
        return naming.snake_to_upper_camel(rule_name)

    def node_kind(self, rule_name: str) -> str:
        """The ``cst.NodeKind`` member expression for a rule."""
        return f"cst.NodeKind.{self.cst_class(rule_name).upper()}"

    def converter_name(self, rule_name: str) -> str:
        return am.converter_names(rule_name)[0]

    def reverse_name(self, rule_name: str) -> str:
        return am.converter_names(rule_name)[1]

    def erased_forward(self, rule_name: str) -> str:
        return am.erased_converter_names(rule_name)[0]

    def erased_reverse(self, rule_name: str) -> str:
        return am.erased_converter_names(rule_name)[1]

    def flat_forward(self, rule_name: str) -> str:
        return am.flat_converter_names(rule_name)[0]

    def flat_reverse(self, rule_name: str) -> str:
        return am.flat_converter_names(rule_name)[1]

    @staticmethod
    def hoist_variable(label: str) -> str:
        """The local holding one hoisted wrapper's fields, as the tuple its helper returned."""
        return f"_h_{label}"

    def terminal_constant(self, rule_name: str) -> str:
        return am.terminal_constant_name(rule_name)

    def payload_constant(self, rule_name: str) -> str:
        return am.payload_constant_name(rule_name)

    def signature_constant(self, rule_name: str) -> str:
        """The name of the module constant holding a sum rule's alternative signatures."""
        return am.signature_constant_name(rule_name)

    def instance_types(self, rule_name: str) -> str:
        """An expression naming the classes a value of ``rule_name``'s AST type can have."""
        custom = self.model.custom_types.get(rule_name)
        if custom is not None:
            return self.custom_path(custom)
        if rule_name in self.model.transparent_types:
            return _type_tuple(self.instance_members(rule_name))
        node = self.model.nodes[rule_name]
        if isinstance(node, am.SumNode | am.FoldNode):
            return self.payload_constant(rule_name)
        return node.name

    def instance_members(self, rule_name: str) -> list[str]:
        """Every concrete class a value of ``rule_name``'s AST type can be.

        The model resolves which types those are — a sum alias and a field-enum alias are
        quoted ``TypeAlias`` strings, plain ``str`` at runtime, so neither is usable as an
        ``isinstance`` argument and both have to be expanded.  Here they are only spelled, and
        two elements spelling the same class collapse into one member.
        """
        return self.class_names(am.instance_elements(self.model, rule_name))

    def class_names(self, elements: Sequence[am.ElementType]) -> list[str]:
        members: list[str] = []
        for element in elements:
            member = self.instance_class(element)
            if member not in members:
                members.append(member)
        return members

    def instance_class(self, element: am.ElementType) -> str:
        """The class an ``isinstance`` test against one element type names."""
        if isinstance(element, am.CustomType):
            return self.custom_path(element)
        if isinstance(element, am.TransparentType):
            return self.element_annotation(element)
        if isinstance(element, am.NodeType):
            return element.name
        return _SCALAR_CLASS[element.kind]

    def custom_path(self, custom: am.CustomType) -> str:
        """The dotted path of a ``custom(...)`` rule's Python type."""
        return _python_path(custom.python, custom.rule_name, "custom(...)", "python")

    def coercion_path(self, coercion: am.CustomCoercion, entry: str) -> str:
        """The dotted path of one Python entry of a ``type: custom(...)`` coercion."""
        path = getattr(coercion, f"python_{entry}")
        return _python_path(path, coercion.rule_name, "type: custom(...)", f"py_{entry}")

    def imported_modules(self) -> list[str]:
        """The modules behind the paths the generated module names.

        A builtin coercion's annotation is itself a dotted path (``uuid.UUID``) or a bare
        builtin (``int``), so both kinds of reference reduce to the same question: is there
        anything before the last component to import?
        """
        paths = [self.custom_path(custom) for custom in self.model.custom_types.values()]
        for coercion in am.coercions(self.model):
            paths.append(self.scalar_annotation(coercion))
            if isinstance(coercion, am.CustomCoercion):
                paths.extend(self.coercion_path(coercion, entry) for entry in ("parse", "unparse"))
        return sorted({module for path in paths if (module := path.rpartition(".")[0])})

    def scalar_annotation(self, coercion: am.Coercion) -> str:
        """The Python type a ``type:`` coercion's ``value`` member carries."""
        if isinstance(coercion, am.CustomCoercion):
            return self.coercion_path(coercion, "type")
        return am.PYTHON_SCALAR_TYPES[coercion.name]

    def from_cst_call(self, rule_name: str, argument: str) -> str:
        """The expression converting a CST node of ``rule_name`` to its AST value."""
        custom = self.model.custom_types.get(rule_name)
        if custom is not None:
            return f"{self.custom_path(custom)}.from_cst({argument})"
        if rule_name in self.model.transparent_types:
            return f"{self.erased_forward(rule_name)}({argument})"
        return f"{self.converter_name(rule_name)}({argument})"

    def to_cst_call(self, rule_name: str, argument: str) -> str:
        """The expression synthesising a CST node of ``rule_name`` from an AST value."""
        if rule_name in self.model.custom_types:
            return f"{argument}.to_cst()"
        if rule_name in self.model.transparent_types:
            return f"{self.erased_reverse(rule_name)}({argument})"
        return f"{self.reverse_name(rule_name)}({argument})"

    def field_enum_converter(self, enum_name: str) -> str:
        return am.field_enum_converter_name(enum_name)

    def element_annotation(self, element: am.ElementType) -> str:
        if isinstance(element, am.NodeType):
            return element.name
        if isinstance(element, am.CustomType):
            return self.custom_path(element)
        if isinstance(element, am.TransparentType):
            if element.coercion is not None:
                return self.scalar_annotation(element.coercion)
            return self.element_annotation(element.payload)
        return {am.ScalarKind.TEXT: "str", am.ScalarKind.SPAN: _SPAN_TYPE, am.ScalarKind.BOOL: "bool"}[element.kind]

    def field_annotation(self, field_type: am.FieldType) -> str:
        inner = self.element_annotation(field_type.element)
        if field_type.container is am.Container.OPTIONAL:
            return f"{inner} | None"
        if field_type.container is am.Container.COLLECTION:
            return f"list[{inner}]"
        if field_type.container is am.Container.MAP:
            assert field_type.key is not None
            return f"dict[{self.element_annotation(field_type.key.element)}, {inner}]"
        return inner

    def generate(self) -> str:
        """Return the complete module source."""
        self.emit_preamble()
        for rule_name, node in self.model.nodes.items():
            self.emit_node(rule_name, node)
        self.emit_aliases()
        self.emit_constants()
        self.emit_sum_converters()
        self.emit_fold_converters()
        self.emit_field_enum_converters()
        self.emit_module_converters()
        self.emit_conveniences()
        return "\n".join(self.lines) + "\n"

    def emit_preamble(self) -> None:
        has_classes = bool(self.model.payload_classes) or any(
            not isinstance(node, am.SumNode)
            and rule_name not in self.model.transparent_types
            and rule_name not in self.model.flattened_rules
            for rule_name, node in self.model.nodes.items()
        )
        self.emit(_MODULE_DOCSTRING, "", "from __future__ import annotations", "")
        if has_classes:
            self.emit("import dataclasses")
        if self.model.value_enums:
            self.emit("import enum")
        self.emit("import typing", "")
        self.emit(f"import {self.cst_module_name} as cst")
        if self.parser_module_name:
            self.emit(f"import {self.parser_module_name} as _parser")
        if self.unparser_module_name:
            self.emit(f"import {self.unparser_module_name} as _unparser")
        # User types are referenced by their full dotted path, so importing the module cannot
        # shadow a generated class name.
        self.emit(*(f"import {module}" for module in self.imported_modules()))
        self.emit(
            "from fltk.fegen.pyrt import astrt, terminalsrc",
            "",
            "if typing.TYPE_CHECKING:",
            "    import fltk.fegen.pyrt.span_protocol",
        )
        if self.unparser_module_name:
            self.emit("    import fltk.unparse.renderer")

    def emit_node(self, rule_name: str, node: am.RuleNode) -> None:
        plans = self.model.plans[rule_name].alternatives
        if rule_name in self.model.flattened_rules:
            self.emit_flattened(rule_name, node, plans)
            return
        if rule_name in self.model.transparent_types:
            if isinstance(node, am.EnumNode) and node.bool_truthy is None:
                # The value enum *is* the payload, so it is still a public type.
                self.emit_value_enum(node.value_enum)
            self.emit_erased(rule_name, node, plans)
            return
        if isinstance(node, am.EnumNode):
            if node.bool_truthy is None:
                self.emit_value_enum(node.value_enum)
            self.emit_enum_class(rule_name, node)
        elif isinstance(node, am.TerminalNode):
            self.emit_terminal_node(rule_name, node)
        elif isinstance(node, am.ProductNode):
            self.emit_dataclass(
                node.name,
                rule_name,
                node.fields,
                f"AST node for rule ``{rule_name}``.",
                plans,
                hoists=node.hoists,
            )
        elif isinstance(node, am.FoldNode):
            self.emit_fold_class(rule_name, node)
        else:
            for variant in node.variants:
                payload = am.generated_payload(self.model, variant)
                if payload is not None:
                    self.emit_dataclass(
                        payload.name,
                        rule_name,
                        payload.fields,
                        f"The ``{variant.name}`` alternative of rule ``{rule_name}``.",
                        (plans[payload.alternative_index],),
                        hoists=payload.hoists,
                    )

    def emit_dataclass(
        self,
        class_name: str,
        rule_name: str,
        fields: Sequence[am.Field],
        docstring: str,
        plans: Sequence[am.AltPlan],
        *,
        hoists: Sequence[am.Hoist] = (),
    ) -> None:
        self.separate()
        self.emit("@dataclasses.dataclass", f"class {class_name}:", f'    """{docstring}"""', "")
        for field in fields:
            annotation = self.field_annotation(field.type)
            if field.type.element == am.SPAN:
                # A literal's text is a grammar constant, so the field carries position only.
                self.emit(f"    {field.name}: {annotation} = dataclasses.field(compare=False)")
            else:
                self.emit(f"    {field.name}: {annotation}")
        self.emit(self.span_field(), *self.backpointer_field(rule_name))
        self.emit(*self.narrowing_method(self.narrowed_members(fields)), "")
        self.emit_from_cst(class_name, rule_name, fields, hoists)
        self.emit_to_cst(rule_name, fields, plans, hoists)

    @staticmethod
    def span_field() -> str:
        return f"    span: {_SPAN_TYPE} = dataclasses.field(default=terminalsrc.UnknownSpan, compare=False)"

    def backpointer_field(self, rule_name: str) -> list[str]:
        """The ``cst`` member, when ``option cst = true;`` asked every node to carry one.

        Hand-built and mutated values have none, so it is optional and out of both equality and
        repr; the AST fields stay authoritative and the reverse direction ignores it.
        """
        if not self.model.cst_backpointers:
            return []
        annotation = f"cst.{self.cst_class(rule_name)} | None"
        return [f"    {am.CST_FIELD_NAME}: {annotation} = dataclasses.field(default=None, compare=False, repr=False)"]

    @staticmethod
    def narrowed_members(fields: Sequence[am.Field]) -> list[tuple[str, int]]:
        """The fields whose float width is narrower than the Python ``float`` holding them."""
        widths = ((field.name, am.element_float_bits(field.type.element)) for field in fields)
        return [(name, bits) for name, bits in widths if bits is not None and bits < _NATIVE_FLOAT_BITS]

    @staticmethod
    def narrowed_value(member: str, coercion: am.Coercion | None) -> list[tuple[str, int]]:
        """A coerced node's own ``value`` member, when its width is narrower than a float."""
        bits = am.coercion_float_bits(coercion)
        return [(member, bits)] if bits is not None and bits < _NATIVE_FLOAT_BITS else []

    @staticmethod
    def narrowing_method(members: Sequence[tuple[str, int]]) -> list[str]:
        """A ``__post_init__`` rounding every narrow float member to the width Rust declares.

        A hand-built ``f32`` field would otherwise hold digits the Rust field cannot, so the same
        literal would give unequal values on the two backends and re-reading its rendering would
        change it.  Escape paths remain — mutating a field in place, or a float reached only
        through a union — and are normalised by the renderer when the value is serialised.
        """
        if not members:
            return []
        lines = [
            "",
            "    def __post_init__(self) -> None:",
            '        """Round the narrow float members to the width the Rust field holds."""',
        ]
        lines.extend(f"        self.{name} = astrt.narrowed(self.{name}, {bits})" for name, bits in members)
        return lines

    def backpointer_argument(self) -> str:
        """The back-pointer keyword argument a converter passes, if there is one."""
        return f", {am.CST_FIELD_NAME}=node" if self.model.cst_backpointers else ""

    def emit_from_cst(
        self, class_name: str, rule_name: str, fields: Sequence[am.Field], hoists: Sequence[am.Hoist] = ()
    ) -> None:
        self.emit(
            "    @classmethod",
            f"    def from_cst(cls, node: cst.{self.cst_class(rule_name)}) -> {class_name}:",
            f'        """Convert a ``{rule_name}`` CST node."""',
        )
        if not fields:
            self.emit(f"        return cls(span=node.span{self.backpointer_argument()})")
            return
        self.emit("        buckets = astrt.bucket_children(node.children)")
        prelude, values = self.forward_body(rule_name, fields, hoists)
        self.emit(*(f"        {line}" for line in prelude))
        self.emit("        return cls(")
        self.emit(*(f"            {name}={expression}," for name, expression in values))
        if self.model.cst_backpointers:
            self.emit(f"            {am.CST_FIELD_NAME}=node,")
        self.emit("            span=node.span,", "        )")

    def forward_body(
        self, rule_name: str, fields: Sequence[am.Field], hoists: Sequence[am.Hoist]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Statements to run over ``buckets``, and each field's name paired with its value.

        A hoisted field's value is one element of the tuple its wrapper's helper returned, so the
        wrapper is read once however many fields came out of it.
        """
        prelude: list[str] = []
        for hoist in hoists:
            prelude.extend(self.hoist_forward_lines(rule_name, hoist))
        indices = {(hoist.label, field.name): index for hoist in hoists for index, field in enumerate(hoist.fields)}
        values: list[tuple[str, str]] = []
        for field in fields:
            if field.hoist is not None:
                index = indices[(field.hoist, field.name)]
                values.append((field.name, f"{self.hoist_variable(field.hoist)}[{index}]"))
                continue
            lines, expression = self.field_code(rule_name, field)
            prelude.extend(lines)
            values.append((field.name, expression))
        return prelude, values

    def hoist_forward_lines(self, rule_name: str, hoist: am.Hoist) -> list[str]:
        """Statements reading a flattened wrapper's child and unpacking the fields it carries."""
        if not hoist.fields:
            # A wrapper with no fields records nothing, so there is nothing to read back.
            return []
        arguments = f'buckets, "{hoist.label.upper()}", "{rule_name}", "{hoist.label}", node.span'
        call = self.flat_forward(hoist.rule_name)
        variable = self.hoist_variable(hoist.label)
        if not hoist.optional:
            guarded = self.checked_node(f"astrt.one({arguments})", hoist.rule_name, rule_name, hoist.label)
            return [f"{variable} = {call}({guarded})"]
        child = f"_w_{hoist.label}"
        absent = _tuple_literal([self.absent_default(field.type) for field in hoist.fields])
        guarded = self.checked_node(child, hoist.rule_name, rule_name, hoist.label)
        return [
            f"{child} = astrt.optional({arguments})",
            f"{variable} = {absent} if {child} is None else {call}({guarded})",
        ]

    @staticmethod
    def absent_default(field_type: am.FieldType) -> str:
        """What a hoisted field holds when its optional wrapper was not there."""
        if field_type.element == am.BOOL:
            return "False"
        if field_type.container is am.Container.COLLECTION:
            return "[]"
        if field_type.container is am.Container.MAP:
            return "{}"
        return "None"

    def field_code(self, rule_name: str, field: am.Field) -> tuple[list[str], str]:
        """Statements to run before the constructor call, and the field's value expression."""
        key = field.label.upper()
        arguments = f'buckets, "{key}", "{rule_name}", "{field.label}", node.span'
        field_type = field.type

        if field_type.element == am.BOOL:
            return [], f"astrt.presence({arguments})"

        if field_type.container is am.Container.MAP:
            map_key = field_type.key
            assert map_key is not None
            converted = self.convert("_child", field_type.element, rule_name, field.label)
            elements = f'[{converted} for _child in buckets.get("{key}", ())]'
            return [], f'astrt.keyed({elements}, "{map_key.field_name}", "{map_key.rule_name}")'

        if field_type.container is am.Container.COLLECTION:
            converted = self.convert("_child", field_type.element, rule_name, field.label)
            if converted == "_child":
                return [], f'list(buckets.get("{key}", ()))'
            return [], f'[{converted} for _child in buckets.get("{key}", ())]'

        variable = f"_{field.name}"
        converted = self.convert(variable, field_type.element, rule_name, field.label)
        if field_type.container is am.Container.SINGLE:
            return [f"{variable} = astrt.one({arguments})"], converted
        return (
            [f"{variable} = astrt.optional({arguments})"],
            f"None if {variable} is None else {converted}",
        )

    def convert(self, expression: str, element: am.ElementType, rule_name: str, label: str) -> str:
        """The expression converting one CST child to a field element.

        Every position that reads a child of a known kind checks that kind first, so a
        hand-built CST carrying the wrong one is refused with the same diagnostic the Rust
        converters give it rather than failing incidentally inside the wrong rule's converter.
        A field enum needs no check here: its own converter dispatches on the kind and reports
        the one it cannot hold.
        """
        if isinstance(element, am.CustomType | am.TransparentType):
            return self.from_cst_call(
                element.rule_name, self.checked_node(expression, element.rule_name, rule_name, label)
            )
        if isinstance(element, am.NodeType):
            if element.name in self.model.field_enums:
                return f"{self.field_enum_converter(element.name)}({expression}, node.span)"
            referenced = self.rule_of_type[element.name]
            return f"{self.converter_name(referenced)}({self.checked_node(expression, referenced, rule_name, label)})"
        if element.kind is am.ScalarKind.TEXT:
            return f'astrt.text({expression}, "{rule_name}", "{label}", node.span)'
        return f'astrt.span_child({expression}, "{rule_name}", "{label}", node.span)'

    def checked_node(self, expression: str, referenced: str, rule_name: str, label: str) -> str:
        """One child expression, guarded by the ``NodeKind`` the label's term references."""
        return f'astrt.node_child({expression}, {self.node_kind(referenced)}, "{rule_name}", "{label}", node.span)'

    def emit_to_cst(
        self,
        rule_name: str,
        fields: Sequence[am.Field],
        plans: Sequence[am.AltPlan],
        hoists: Sequence[am.Hoist] = (),
    ) -> None:
        cst_class = self.cst_class(rule_name)
        self.emit(
            "",
            f"    def to_cst(self) -> cst.{cst_class}:",
            f'        """Synthesise a ``{rule_name}`` CST node from this value."""',
        )
        values = _member_values
        if len(plans) == 1:
            body = self.alternative_body(rule_name, fields, plans[0], values, hoists)
            self.emit(*(f"        {line}" for line in body))
            return

        trial = self.trial_lines(
            rule_name,
            fields,
            plans,
            values,
            span="self.span",
            call=lambda index: f"self._to_cst_alt{index}()",
            hoists=hoists,
        )
        self.emit(*(f"        {line}" for line in trial))
        for plan in plans:
            self.emit("", f"    def _to_cst_alt{plan.index}(self) -> cst.{cst_class}:")
            body = self.alternative_body(rule_name, fields, plan, values, hoists)
            self.emit(*(f"        {line}" for line in body))

    def trial_lines(
        self,
        rule_name: str,
        fields: Sequence[am.Field],
        plans: Sequence[am.AltPlan],
        values: _Values,
        *,
        span: str,
        call: Callable[[int], str],
        hoists: Sequence[am.Hoist] = (),
    ) -> list[str]:
        """Statements picking the first alternative the populated fields fit, then delegating.

        A hoisted group counts as its wrapper's own label, which is the label the alternatives
        are written in terms of: the group is populated exactly when the wrapper would be built.

        Which labels are populated is half the question; a label carrying several types leaves
        the alternatives that accept different ones of them indistinguishable by name, so an
        alternative accepting fewer kinds than the field holds carries a kind test as well.
        """
        by_label = {field.label: field for field in fields if field.hoist is None}
        entries = [
            f'"{field.label}": {self.populated_expression(field, values)}' for field in fields if field.hoist is None
        ]
        entries.extend(f'"{hoist.label}": {self.hoist_present(hoist, values)}' for hoist in hoists)
        populated = ", ".join(entries)
        lines = [f"_present = astrt.populated({{{populated}}})"]
        for plan in plans:
            fits = f"{_frozenset_literal(plan.required_labels)}, {_frozenset_literal(plan.labels)}"
            conditions = [f"astrt.alternative_fits(_present, {fits})"]
            conditions.extend(
                self.kind_condition(by_label[guard.label], guard, values)
                for guard in am.selection_guards(self.model, fields, plan)
            )
            lines.append(f"if {' and '.join(conditions)}:")
            lines.append(f"    return {call(plan.index)}")
        lines.append(f'msg = "rule {rule_name!r}: no alternative fits the populated fields"')
        lines.append(f"raise astrt.AstError(msg, {span})")
        return lines

    def kind_condition(self, field: am.Field, guard: am.SelectionGuard, values: _Values) -> str:
        """The test that every value one field holds is a kind this alternative accepts.

        The value is untagged, so what the kinds are told apart by is the same guard a rival
        item position would test them with: a class, a text type, or the erased rule's own
        converter where its payload is a bare scalar.
        """
        guards = _tuple_literal([self.guard_expression(kind.guard) for kind in guard.accepted])
        return f"astrt.field_fits({values(field)}, {guards})"

    def alternative_body(
        self,
        rule_name: str,
        fields: Sequence[am.Field],
        plan: am.AltPlan,
        values: _Values,
        hoists: Sequence[am.Hoist] = (),
    ) -> list[str]:
        """Statements building the CST node for one alternative.

        ``values`` names where each field's value comes from — a member of the node class, the
        single parameter of an erased rule's private helper, or one parameter per field of a
        flattened wrapper's.  A hoisted field is not distributed over this rule's item positions:
        its wrapper occupies one position, and the wrapper's own helper places the fields inside.
        """
        own = [field for field in fields if field.hoist is None]
        by_label = {field.label: field for field in own}
        by_hoist = {hoist.label: hoist for hoist in hoists}
        checks = am.group_checks(plan, fields, hoists)
        lines = self.group_check_lines(rule_name, checks, values, by_label, by_hoist)
        lines.append(f"_node = cst.{self.cst_class(rule_name)}()")
        lines.extend(f"_c_{field.name} = {self.cursor_expression(field, values(field))}" for field in own)
        for run in am.synthesis_runs(self.model, plan):
            hoist = by_hoist.get(run.label or "")
            if hoist is not None:
                lines.extend(self.hoist_reverse_lines(rule_name, hoist, values))
            elif run.dispatched:
                lines.extend(self.dispatch_lines(rule_name, run, by_label))
            else:
                lines.extend(self.slot_lines(rule_name, run, by_label))
        if own:
            entries = ", ".join(f'("{field.label}", _c_{field.name})' for field in own)
            lines.append(f'astrt.check_consumed("{rule_name}", ({entries},))')
        lines.append("return _node")
        return lines

    def group_check_lines(
        self,
        rule_name: str,
        checks: Sequence[am.GroupCheck],
        values: _Values,
        by_label: dict[str, am.Field],
        by_hoist: dict[str, am.Hoist],
    ) -> list[str]:
        """Statements checking that each sub-expression alternation's values suit one branch."""
        lines: list[str] = []
        for check in checks:
            entries = ", ".join(
                f'"{label}": {self.label_populated(label, values, by_label, by_hoist)}' for label in check.labels
            )
            branch_literal = _tuple_literal([_frozenset_literal(labels) for labels in check.branches])
            lines.append(
                f'astrt.check_group("{rule_name}", astrt.populated({{{entries}}}), {branch_literal}, '
                f"{_frozenset_literal(check.exclusive)}, demanded={check.demanded})"
            )
        return lines

    def label_populated(
        self,
        label: str,
        values: _Values,
        by_label: dict[str, am.Field],
        by_hoist: dict[str, am.Hoist],
    ) -> str:
        """Where one label of an alternation group reads its populated state from."""
        field = by_label.get(label)
        if field is not None:
            return self.populated_expression(field, values)
        return self.hoist_present(by_hoist[label], values)

    def hoist_reverse_lines(self, rule_name: str, hoist: am.Hoist, values: _Values) -> list[str]:
        """Statements re-materialising a flattened wrapper from the fields hoisted out of it.

        An optional wrapper is rebuilt only when something it carries is populated, so a value
        whose hoisted fields are all at their absent defaults renders without the wrapper — the
        same collapse an absent wrapper produces.
        """
        label = f"cst.{self.cst_class(rule_name)}.Label.{hoist.label.upper()}"
        arguments = ", ".join(self.hoist_argument(hoist, field, values) for field in hoist.fields)
        append = f"_node.append({self.flat_reverse(hoist.rule_name)}({arguments}), {label})"
        if not hoist.optional:
            return [append]
        return [f"if {self.wrapper_needed(hoist, values)}:", f"    {append}"]

    def wrapper_needed(self, hoist: am.Hoist, values: _Values) -> str:
        """The test deciding whether an optional flattened wrapper has to be rebuilt."""
        states = [self.populated_expression(field, values) for field in hoist.fields]
        return f"astrt.wrapper_needed({_tuple_literal(states)})"

    def populated_expression(self, field: am.Field, values: _Values) -> str:
        """Whether a field carries something, for alternative and branch selection."""
        value = values(field)
        if am.populated_directly(field):
            return value
        return f"astrt.holds({value})"

    def hoist_present(self, hoist: am.Hoist, values: _Values) -> str:
        """Whether a hoisted group counts as populated, for alternative and branch selection."""
        if am.hoist_always_present(hoist):
            return "True"
        return self.wrapper_needed(hoist, values)

    def hoist_argument(self, hoist: am.Hoist, field: am.Field, values: _Values) -> str:
        """One argument of a wrapper's reverse helper.

        A field the wrapper requires was degraded to optional at an optional use site, so it has
        to be checked: a half-populated wrapper is the user's data, not a CST the formatter can
        report on.
        """
        value = values(field)
        if not hoist.optional or field.name not in hoist.required:
            return value
        return f'astrt.hoisted({value}, "{hoist.rule_name}", "{field.name}")'

    def cursor_expression(self, field: am.Field, value: str) -> str:
        if field.type.element == am.BOOL:
            return f"astrt.flag_cursor({value})"
        return f"astrt.cursor({value})"

    def dispatch_lines(self, rule_name: str, run: am.SlotRun, by_label: dict[str, am.Field]) -> list[str]:
        """Statements handing one label's values to whichever branch of a run accepts each."""
        field = by_label.get(run.label or "")
        if field is None:
            return []
        label = f"cst.{self.cst_class(rule_name)}.Label.{(run.label or '').upper()}"
        taken = f"_c_{field.name}.take({_count(run.maximum)}, {run.reserve})"
        lines = [f"for _child in {self.at_least(taken, run, rule_name)}:"]
        for index, placement in enumerate(run.placements):
            keyword = "if" if index == 0 else "elif"
            lines.append(f"    {keyword} astrt.accepts({self.guard_expression(placement.guard)}, _child):")
            lines.append(f"        _node.append({self.child_expression(rule_name, placement.slot)}, {label})")
        lines.append("    else:")
        lines.append(f'        astrt.unplaceable(_child, "{rule_name}", "{run.label}")')
        return lines

    def at_least(self, taken: str, run: am.SlotRun, rule_name: str) -> str:
        """``taken``, wrapped in the check that the run's lower bound was met."""
        if run.minimum < 1:
            return taken
        return f'astrt.filled({taken}, {run.minimum}, "{rule_name}", "{run.label or ""}")'

    def guard_expression(self, guard: am.Guard) -> str:
        """The runtime guard object one item position tests a value against."""
        if guard.kind is am.GuardKind.NONE:
            return "None"
        if guard.kind is am.GuardKind.NODE:
            return self.instance_types(guard.rule_name or "")
        if guard.kind is am.GuardKind.CONVERTIBLE:
            return f"astrt.Convertible({self.erased_reverse(guard.rule_name or '')})"
        if guard.kind is am.GuardKind.TEXT:
            return "str"
        if guard.kind is am.GuardKind.PATTERN:
            return f"astrt.Pattern({guard.pattern!r})"
        return f"astrt.LiteralText({guard.literal!r})"

    def slot_lines(self, rule_name: str, run: am.SlotRun, by_label: dict[str, am.Field]) -> list[str]:
        """Statements appending the children one item position contributes."""
        slot = run.slots[0]
        if slot.kind is am.SlotKind.UNLABELED:
            # The occurrence count is not recorded, so the grammar minimum is what comes back.
            return ["_node.append(terminalsrc.UnknownSpan)"] * slot.minimum
        field = by_label.get(slot.label or "")
        if field is None:
            return []
        label = f"cst.{self.cst_class(rule_name)}.Label.{(slot.label or '').upper()}"
        guard = self.guard_expression(run.placements[0].guard)
        taken = f"_c_{field.name}.take({_count(run.maximum)}, {run.reserve}, {guard})"
        return [
            f"for _child in {self.at_least(taken, run, rule_name)}:",
            f"    _node.append({self.child_expression(rule_name, slot)}, {label})",
        ]

    def child_expression(self, rule_name: str, slot: am.Slot, value: str = "_child") -> str:
        """The CST child one value of a slot becomes."""
        if slot.kind is am.SlotKind.NODE:
            return self.to_cst_call(slot.rule_name or "", value)
        if slot.kind is am.SlotKind.TEXT:
            return f'astrt.text_span({value}, {slot.pattern!r}, "{rule_name}", "{slot.label}")'
        # A literal's text comes back from the grammar, so the span carries position only.
        return "terminalsrc.UnknownSpan"

    def emit_terminal_node(self, rule_name: str, node: am.TerminalNode) -> None:
        cst_class = self.cst_class(rule_name)
        member = "text" if node.coercion is None else "value"
        annotation = "str" if node.coercion is None else self.scalar_annotation(node.coercion)
        source = "its own span" if node.text_from is None else f"the ``{node.text_from}`` child"
        self.separate()
        self.emit(
            "@dataclasses.dataclass",
            f"class {node.name}:",
            f'    """AST node for terminal-only rule ``{rule_name}``, over the text of {source}."""',
            "",
            f"    {member}: {annotation}",
            self.span_field(),
            *self.backpointer_field(rule_name),
            *self.narrowing_method(self.narrowed_value(member, node.coercion)),
            "",
            "    @classmethod",
            f"    def from_cst(cls, node: cst.{cst_class}) -> {node.name}:",
            f'        """Convert a ``{rule_name}`` CST node."""',
        )
        prelude, text = self.terminal_text_code(rule_name, node)
        value = self.parse_expression(rule_name, node.coercion, text)
        self.emit(*(f"        {line}" for line in prelude))
        self.emit(f"        return cls({member}={value}, span=node.span{self.backpointer_argument()})")
        self.emit(
            "",
            f"    def to_cst(self) -> cst.{cst_class}:",
            f'        """Synthesise a ``{rule_name}`` CST node from the text of ``{member}``."""',
            f"        return {self.terminal_to_cst_call(rule_name, node, f'self.{member}', 'self.span')}",
        )

    def terminal_text_code(self, rule_name: str, node: am.TerminalNode) -> tuple[list[str], str]:
        """Statements to run first, and the expression for the text a terminal-only rule carries."""
        if node.text_from is None:
            return [], f'astrt.node_text(node.span, "{rule_name}")'
        label = node.text_from
        return (
            [
                "buckets = astrt.bucket_children(node.children)",
                f'_child = astrt.one(buckets, "{label.upper()}", "{rule_name}", "{label}", node.span)',
            ],
            f'astrt.text(_child, "{rule_name}", "{label}", node.span)',
        )

    def terminal_to_cst_call(self, rule_name: str, node: am.TerminalNode, value: str, span: str) -> str:
        """The call splitting a terminal-only rule's text back across the grammar's items."""
        redirected = ", redirected=True" if node.text_from is not None else ""
        rendered = self.render_expression(rule_name, node, value, span)
        return (
            f"astrt.terminal_to_cst(cst.{self.cst_class(rule_name)}, {rendered}, "
            f'{self.terminal_constant(rule_name)}, "{rule_name}"{redirected})'
        )

    def parse_expression(self, rule_name: str, coercion: am.Coercion | None, text: str) -> str:
        """The expression coercing a terminal's text to the node's ``value``, if it is coerced."""
        if coercion is None:
            return text
        context = f'"{rule_name}", node.span'
        if isinstance(coercion, am.CustomCoercion):
            return f"astrt.parse_custom({self.coercion_path(coercion, 'parse')}, {text}, {context})"
        if coercion.is_integer:
            return f"astrt.parse_int({text}, {coercion.bits}, {context}, signed={coercion.signed})"
        if coercion.is_float:
            return f"astrt.parse_float({text}, {coercion.bits}, {context})"
        return f"astrt.parse_{coercion.name}({text}, {context})"

    def render_expression(self, rule_name: str, node: am.TerminalNode, value: str, span: str) -> str:
        """The expression rendering ``value`` back to the text the grammar accepts."""
        coercion = node.coercion
        if coercion is None:
            return value
        if isinstance(coercion, am.CustomCoercion):
            return f"{self.coercion_path(coercion, 'unparse')}({value})"
        context = f'"{rule_name}", {span}'
        if coercion.is_integer:
            return f"astrt.render_int({value}, {coercion.bits}, {context}, signed={coercion.signed})"
        if coercion.is_float:
            return f"astrt.render_float({value}, {coercion.bits}, {context})"
        return f"astrt.render_{coercion.name}({value}, {context})"

    def emit_value_enum(self, value_enum: am.ValueEnum) -> None:
        self.separate()
        self.emit(
            f"class {value_enum.name}(astrt.CrossBackendEnumMixin, enum.Enum):",
            f'    """Which alternative of rule ``{value_enum.rule_name}`` matched."""',
            "",
        )
        for variant in value_enum.variants:
            self.emit(f"    {variant.member} = enum.auto()")
        self.separate()
        for variant in value_enum.variants:
            member = variant.member
            self.emit(f'{value_enum.name}.{member}._fltk_canonical_name = "{value_enum.name}.{member}"')

    def enum_value(self, node: am.EnumNode, variant: am.ValueVariant) -> str:
        """The value one alternative of an enum-shaped rule maps to."""
        if node.bool_truthy is not None:
            return str(variant.label == node.bool_truthy)
        return f"{node.value_enum.name}.{variant.member}"

    def enum_from_lines(self, rule_name: str, node: am.EnumNode, result: Callable[[str], str]) -> list[str]:
        """Statements picking the value from whichever alternative label the CST node carries."""
        lines = ["buckets = astrt.bucket_children(node.children)"]
        for variant in node.value_enum.variants:
            lines.append(f'if "{variant.label.upper()}" in buckets:')
            lines.append(f"    {result(self.enum_value(node, variant))}")
        lines.append(f'msg = "rule {rule_name!r}: no alternative label is present"')
        lines.append("raise astrt.AstError(msg, node.span)")
        return lines

    def enum_to_lines(self, rule_name: str, node: am.EnumNode, value: str, span: str) -> list[str]:
        """Statements building the CST node for the alternative ``value`` names."""
        cst_class = self.cst_class(rule_name)
        boolean = node.bool_truthy is not None
        lines = [f"_node = cst.{cst_class}()"]
        for variant in node.value_enum.variants:
            label = f"cst.{cst_class}.Label.{variant.label.upper()}"
            test = "is" if boolean else "=="
            lines.append(f"if {value} {test} {self.enum_value(node, variant)}:")
            lines.append(f"    _node.append(terminalsrc.UnknownSpan, {label})")
            lines.append("    return _node")
        complaint = (
            f'"rule {rule_name!r}: value is " + repr({value}) + ", not a boolean"'
            if boolean
            else f'"rule {rule_name!r}: unknown value " + repr({value})'
        )
        lines.append(f"msg = {complaint}")
        lines.append(f"raise astrt.AstError(msg, {span})")
        return lines

    def emit_enum_class(self, rule_name: str, node: am.EnumNode) -> None:
        """The node class of an enum-shaped rule: its value plus a span."""
        cst_class = self.cst_class(rule_name)
        boolean = node.bool_truthy is not None
        annotation = "bool" if boolean else node.value_enum.name
        carries = "which of its two literals matched" if boolean else "which literal alternative matched"
        self.separate()
        self.emit(
            "@dataclasses.dataclass",
            f"class {node.name}:",
            f'    """AST node for rule ``{rule_name}``: {carries}."""',
            "",
            f"    value: {annotation}",
            self.span_field(),
            *self.backpointer_field(rule_name),
            "",
            "    @classmethod",
            f"    def from_cst(cls, node: cst.{cst_class}) -> {node.name}:",
            f'        """Convert a ``{rule_name}`` CST node."""',
        )
        backpointer = self.backpointer_argument()
        forward = self.enum_from_lines(
            rule_name, node, lambda value: f"return cls(value={value}, span=node.span{backpointer})"
        )
        self.emit(*(f"        {line}" for line in forward))
        self.emit(
            "",
            f"    def to_cst(self) -> cst.{cst_class}:",
            f'        """Synthesise a ``{rule_name}`` CST node for the alternative ``value`` names."""',
        )
        self.emit(*(f"        {line}" for line in self.enum_to_lines(rule_name, node, "self.value", "self.span")))

    def emit_erased(self, rule_name: str, node: am.RuleNode, plans: Sequence[am.AltPlan]) -> None:
        """The private converter pair of a ``transparent;`` rule, which emits no class.

        Both halves are module-level functions taking or returning the payload directly, so a
        use site of the erased rule looks exactly like a use site of a plain scalar.
        """
        transparent = self.model.transparent_types[rule_name]
        annotation = self.element_annotation(transparent)
        cst_class = self.cst_class(rule_name)
        self.separate()
        self.emit(
            f"def {self.erased_forward(rule_name)}(node: cst.{cst_class}) -> {annotation}:",
            f'    """Convert a ``{rule_name}`` CST node to the payload its type erases to."""',
        )
        self.emit(*(f"    {line}" for line in self.erased_forward_lines(rule_name, node)))
        self.separate()
        self.emit(
            f"def {self.erased_reverse(rule_name)}(value: {annotation}) -> cst.{cst_class}:",
            f'    """Synthesise a ``{rule_name}`` CST node from the payload its type erases to."""',
        )
        self.emit(*(f"    {line}" for line in self.erased_reverse_lines(rule_name, node, plans)))
        if isinstance(node, am.ProductNode) and len(plans) > 1:
            for plan in plans:
                self.separate()
                signature = f"(value: {annotation}) -> cst.{cst_class}:"
                self.emit(f"def {am.erased_alt_converter_name(rule_name, plan.index)}{signature}")
                body = self.alternative_body(rule_name, node.fields, plan, _parameter_values)
                self.emit(*(f"    {line}" for line in body))

    def emit_flattened(self, rule_name: str, node: am.RuleNode, plans: Sequence[am.AltPlan]) -> None:
        """The private helper pair of a ``flatten;`` wrapper, which emits no class of its own.

        The forward half hands back the wrapper's fields as a tuple in declared order; the reverse
        half takes them as parameters and rebuilds the wrapper node.  Both are what a use site
        calls in place of the converter a public type would have carried.
        """
        assert isinstance(node, am.ProductNode)
        cst_class = self.cst_class(rule_name)
        fields = node.fields
        if fields:
            annotation = f"tuple[{', '.join(self.field_annotation(field.type) for field in fields)}]"
            self.separate()
            self.emit(
                f"def {self.flat_forward(rule_name)}(node: cst.{cst_class}) -> {annotation}:",
                f'    """Convert a ``{rule_name}`` CST node to the fields it is flattened into."""',
                "    buckets = astrt.bucket_children(node.children)",
            )
            prelude, values = self.forward_body(rule_name, fields, node.hoists)
            self.emit(*(f"    {line}" for line in prelude))
            self.emit(f"    return {_tuple_literal([expression for _name, expression in values])}")

        parameters = ", ".join(f"{_hoisted_values(field)}: {self.field_annotation(field.type)}" for field in fields)
        self.separate()
        self.emit(
            f"def {self.flat_reverse(rule_name)}({parameters}) -> cst.{cst_class}:",
            f'    """Synthesise a ``{rule_name}`` CST node from the fields flattened out of it."""',
        )
        if len(plans) == 1:
            body = self.alternative_body(rule_name, fields, plans[0], _hoisted_values, node.hoists)
            self.emit(*(f"    {line}" for line in body))
            return

        arguments = ", ".join(_hoisted_values(field) for field in fields)
        trial = self.trial_lines(
            rule_name,
            fields,
            plans,
            _hoisted_values,
            span="terminalsrc.UnknownSpan",
            call=lambda index: f"{am.flat_alt_converter_name(rule_name, index)}({arguments})",
            hoists=node.hoists,
        )
        self.emit(*(f"    {line}" for line in trial))
        for plan in plans:
            self.separate()
            self.emit(f"def {am.flat_alt_converter_name(rule_name, plan.index)}({parameters}) -> cst.{cst_class}:")
            body = self.alternative_body(rule_name, fields, plan, _hoisted_values, node.hoists)
            self.emit(*(f"    {line}" for line in body))

    def erased_forward_lines(self, rule_name: str, node: am.RuleNode) -> list[str]:
        if isinstance(node, am.TerminalNode):
            prelude, text = self.terminal_text_code(rule_name, node)
            return [*prelude, f"return {self.parse_expression(rule_name, node.coercion, text)}"]
        if isinstance(node, am.EnumNode):
            return self.enum_from_lines(rule_name, node, lambda value: f"return {value}")
        assert isinstance(node, am.ProductNode)
        (field,) = node.fields
        prelude, expression = self.field_code(rule_name, field)
        return ["buckets = astrt.bucket_children(node.children)", *prelude, f"return {expression}"]

    def erased_reverse_lines(self, rule_name: str, node: am.RuleNode, plans: Sequence[am.AltPlan]) -> list[str]:
        if isinstance(node, am.TerminalNode):
            return [f"return {self.terminal_to_cst_call(rule_name, node, 'value', 'terminalsrc.UnknownSpan')}"]
        if isinstance(node, am.EnumNode):
            return self.enum_to_lines(rule_name, node, "value", "terminalsrc.UnknownSpan")
        assert isinstance(node, am.ProductNode)
        if len(plans) == 1:
            return self.alternative_body(rule_name, node.fields, plans[0], _parameter_values)
        return self.trial_lines(
            rule_name,
            node.fields,
            plans,
            _parameter_values,
            span="terminalsrc.UnknownSpan",
            call=lambda index: f"{am.erased_alt_converter_name(rule_name, index)}(value)",
        )

    # --- Fold rules ----------------------------------------------------------------------

    def emit_fold_class(self, rule_name: str, node: am.FoldNode) -> None:
        """The chain-link class of a fold rule; the rule's own type is the union alias.

        The declared field order is what ``astrt``'s fold builders construct positionally.
        """
        binary = node.binary
        nesting = "left" if node.direction is ac.FoldDirection.LEFT else "right"
        op_line = f"    {binary.op.name}: {self.field_annotation(binary.op.type)}"
        if binary.op.type.element == am.SPAN:
            op_line += " = dataclasses.field(compare=False)"
        self.separate()
        self.emit(
            "@dataclasses.dataclass",
            f"class {binary.name}:",
            f'    """One link of the {nesting}-nested chain rule ``{rule_name}`` folds into.',
            "",
            f"    ``span`` covers everything below the link; ``{am.FOLD_LHS}``/``{am.FOLD_RHS}`` hold "
            f"either an operand or a deeper link.  Comparing two long chains recurses as deep as "
            f"they are, as comparing any deep Python structure does.",
            '    """',
            "",
            op_line,
            f"    {am.FOLD_LHS}: {node.name}",
            f"    {am.FOLD_RHS}: {node.name}",
            self.span_field(),
            *self.backpointer_field(rule_name),
            # The operands are the chain's leaves, reached through the union alias rather than a
            # field of a class, so only the operator member is narrowed here.
            *self.narrowing_method(self.narrowed_members((binary.op,))),
            "",
            f"    def to_cst(self) -> cst.{self.cst_class(rule_name)}:",
            f'        """Synthesise a ``{rule_name}`` CST node by unfolding this chain."""',
            f"        return {self.reverse_name(rule_name)}(self)",
        )

    def emit_fold_converters(self) -> None:
        for rule_name, node in self.model.nodes.items():
            if isinstance(node, am.FoldNode):
                self.emit_fold_forward(rule_name, node)
                self.emit_fold_reverse(rule_name, node)

    def emit_fold_forward(self, rule_name: str, node: am.FoldNode) -> None:
        """The converter bucketing operands and operators, then folding them into a chain."""
        builder = "fold_left" if node.direction is ac.FoldDirection.LEFT else "fold_right"
        self.separate()
        self.emit(
            f"def {self.converter_name(rule_name)}(node: cst.{self.cst_class(rule_name)}) -> {node.name}:",
            f'    """Convert a ``{rule_name}`` CST node, folding its operands into a chain."""',
            "    buckets = astrt.bucket_children(node.children)",
            f'    _operands = buckets.get("{node.operand.label.upper()}", ())',
            f'    _operators = buckets.get("{node.operators.label.upper()}", ())',
            f'    astrt.check_fold_arity(len(_operands), len(_operators), "{rule_name}", node.span)',
            f"    _values = {self.fold_conversion(rule_name, node.operand, '_operands')}",
            "    _spans = [astrt.child_span(_child) for _child in _operands]",
            f"    _ops = {self.fold_conversion(rule_name, node.operators, '_operators')}",
            f'    return astrt.{builder}({node.binary.name}, _values, _spans, _ops, "{rule_name}")',
        )

    def fold_conversion(self, rule_name: str, field: am.Field, children: str) -> str:
        """The list of converted values one fold label's children become."""
        converted = self.convert("_child", field.type.element, rule_name, field.label)
        if converted == "_child":
            return f"list({children})"
        return f"[{converted} for _child in {children}]"

    def emit_fold_reverse(self, rule_name: str, node: am.FoldNode) -> None:
        """The converter unfolding a chain back into the grammar's alternating item positions.

        The items are walked by hand rather than through the cursor machinery: a fold's
        repetition interleaves operator and operand, which a flat pass over the item positions
        in grammar order cannot produce.
        """
        unfolder = "unfold_left" if node.direction is ac.FoldDirection.LEFT else "unfold_right"
        cst_class = self.cst_class(rule_name)
        plan = self.model.plans[rule_name].alternatives[0]
        operand_slot = next(slot for slot in plan.slots if slot.label == node.operand.label)
        op_slot = next(slot for slot in plan.slots if slot.label == node.operators.label)
        operand_label = f"cst.{cst_class}.Label.{node.operand.label.upper()}"
        op_label = f"cst.{cst_class}.Label.{node.operators.label.upper()}"
        self.separate()
        self.emit(
            f"def {self.reverse_name(rule_name)}(value: {node.name}) -> cst.{cst_class}:",
            f'    """Synthesise a ``{rule_name}`` CST node by unfolding ``value``\'s chain."""',
            f"    _operands, _operators = astrt.{unfolder}("
            f'value, {node.binary.name}, "{node.binary.op.name}", "{rule_name}")',
            f"    _node = cst.{cst_class}()",
            f"    _node.append({self.child_expression(rule_name, operand_slot, '_operands[0]')}, {operand_label})",
            "    for _op, _operand in zip(_operators, _operands[1:], strict=True):",
            f"        _node.append({self.child_expression(rule_name, op_slot, '_op')}, {op_label})",
            f"        _node.append({self.child_expression(rule_name, operand_slot, '_operand')}, {operand_label})",
            "    return _node",
        )

    def emit_aliases(self) -> None:
        """Emit union aliases with quoted values (forward references handle mutual recursion)."""
        aliases: list[tuple[str, Iterable[str]]] = [
            (node.name, [self.element_annotation(variant.payload) for variant in node.variants])
            for node in self.model.nodes.values()
            if isinstance(node, am.SumNode)
        ]
        aliases.extend(
            (node.name, [self.element_annotation(node.operand.type.element), node.binary.name])
            for node in self.model.nodes.values()
            if isinstance(node, am.FoldNode)
        )
        aliases.extend(
            (field_enum.name, [self.element_annotation(variant.element) for variant in field_enum.variants])
            for field_enum in self.model.field_enums.values()
        )
        if not aliases:
            return
        self.separate()
        for name, members in aliases:
            union = " | ".join(members)
            self.emit(f'{name}: typing.TypeAlias = "{union}"')

    def emit_constants(self) -> None:
        """Per-rule tables the converters read: sum and fold payload classes, terminal plans."""
        for rule_name, node in self.model.nodes.items():
            if isinstance(node, am.SumNode | am.FoldNode):
                self.separate()
                self.emit(f"{self.payload_constant(rule_name)} = {_tuple_literal(self.instance_members(rule_name))}")
            elif isinstance(node, am.TerminalNode):
                self.separate()
                self.emit(f"{self.terminal_constant(rule_name)} = (")
                for plan in self.model.plans[rule_name].terminals:
                    pieces = [
                        f"({'None' if piece.label is None else repr(piece.label.upper())}, {piece.group!r})"
                        for piece in plan.pieces
                    ]
                    self.emit(f"    astrt.TerminalAlt({plan.pattern!r}, {_tuple_literal(pieces)}),")
                self.emit(")")

    def emit_sum_converters(self) -> None:
        for rule_name, node in self.model.nodes.items():
            if isinstance(node, am.SumNode):
                self.emit_sum_converter(rule_name, node)
                self.emit_sum_reverse(rule_name, node)

    def emit_sum_reverse(self, rule_name: str, node: am.SumNode) -> None:
        cst_class = self.cst_class(rule_name)
        self.separate()
        self.emit(
            f"def {self.reverse_name(rule_name)}(value: {node.name}) -> cst.{cst_class}:",
            f'    """Synthesise a ``{rule_name}`` CST node for whichever variant ``value`` is."""',
        )
        # Tested in payload-precedence order rather than grammar order: a boolean payload has to
        # be offered the value before an integer one, which would take a ``True`` as the number 1.
        for variant in am.variant_test_order(self.model, node):
            payload = am.generated_payload(self.model, variant)
            if payload is not None:
                self.emit(f"    if isinstance(value, {payload.name}):", "        return value.to_cst()")
                continue
            plan = self.model.plans[rule_name].alternatives[variant.alternative_index]
            slot = next(one for one in plan.slots if one.kind is am.SlotKind.NODE)
            payload_rule = variant.payload_rule or ""
            member = (slot.label or "").upper()
            self.emit(
                f"    if isinstance(value, {self.instance_types(payload_rule)}):",
                f"        _node = cst.{cst_class}()",
                f"        _node.append({self.to_cst_call(payload_rule, 'value')}, cst.{cst_class}.Label.{member})",
                "        return _node",
            )
        self.emit(
            f'    msg = "rule {rule_name!r}: cannot synthesise from a " + type(value).__name__',
            "    raise astrt.AstError(msg, terminalsrc.UnknownSpan)",
        )

    def emit_sum_converter(self, rule_name: str, node: am.SumNode) -> None:
        constant = self.signature_constant(rule_name)
        self.separate()
        self.emit(f"{constant} = (")
        for variant in node.variants:
            self.emit("    astrt.AltSignature(", "        {")
            for label, signature in variant.signature.labels.items():
                kinds = ", ".join(sorted(self.kind_expression(kind) for kind in signature.kinds))
                maximum = "astrt.UNBOUNDED" if signature.count.max >= _SATURATED_COUNT else str(signature.count.max)
                self.emit(
                    f'            "{label.upper()}": '
                    f"astrt.LabelSignature({signature.count.min}, {maximum}, frozenset({{{kinds}}})),"
                )
            self.emit("        }", "    ),")
        self.emit(")")
        self.separate()
        self.emit(
            f"def {self.converter_name(rule_name)}(node: cst.{self.cst_class(rule_name)}) -> {node.name}:",
            f'    """Convert a ``{rule_name}`` CST node, dispatching on the alternative that matched."""',
            "    buckets = astrt.bucket_children(node.children)",
        )
        for index, variant in enumerate(node.variants):
            self.emit(f"    if {constant}[{index}].accepts(buckets):")
            self.emit(*(f"        {line}" for line in self.variant_conversion(rule_name, variant)))
        self.emit(
            f'    msg = "rule {rule_name!r}: no alternative matches the node\'s labeled children"',
            "    raise astrt.AstError(msg, node.span)",
        )

    def variant_conversion(self, rule_name: str, variant: am.SumVariant) -> list[str]:
        """The body converting one matched alternative."""
        payload = am.generated_payload(self.model, variant)
        if payload is not None:
            return [f"return {payload.name}.from_cst(node)"]
        label = next(iter(variant.signature.labels))
        arguments = f'buckets, "{label.upper()}", "{rule_name}", "{label}", node.span'
        return [
            f"_child = astrt.one({arguments})",
            f"return {self.from_cst_call(variant.payload_rule or '', '_child')}",
        ]

    def kind_expression(self, kind: str) -> str:
        return "astrt.TEXT" if kind == gshape.TEXT_KIND else self.node_kind(kind)

    def emit_field_enum_converters(self) -> None:
        for field_enum in self.model.field_enums.values():
            self.separate()
            signature = f"(child: typing.Any, span: {_SPAN_TYPE}) -> {field_enum.name}:"
            self.emit(
                f"def {self.field_enum_converter(field_enum.name)}{signature}",
                f'    """Convert a ``{field_enum.label}`` child of rule ``{field_enum.rule_name}``."""',
                "    kind = astrt.child_kind(child)",
            )
            for variant in field_enum.variants:
                if isinstance(variant.element, am.CustomType | am.TransparentType):
                    rule = variant.element.rule_name
                    self.emit(
                        f"    if kind == {self.node_kind(rule)}:",
                        f"        return {self.from_cst_call(rule, 'child')}",
                    )
                elif isinstance(variant.element, am.NodeType):
                    rule = self.rule_of_type[variant.element.name]
                    self.emit(
                        f"    if kind == {self.node_kind(rule)}:",
                        f"        return {self.converter_name(rule)}(child)",
                    )
                else:
                    self.emit(
                        "    if kind is astrt.TEXT:",
                        f'        return astrt.text(child, "{field_enum.rule_name}", "{field_enum.label}", span)',
                    )
            self.emit(
                f'    raise astrt.unexpected_child("{field_enum.rule_name}", "{field_enum.label}", span)',
            )

    def emit_module_converters(self) -> None:
        """A converter pair per rule; sums, folds, erased and flattened rules have their own."""
        for rule_name, node in self.model.nodes.items():
            if isinstance(node, am.SumNode | am.FoldNode):
                continue
            if rule_name in self.model.transparent_types or rule_name in self.model.flattened_rules:
                continue
            self.separate()
            self.emit(
                f"def {self.converter_name(rule_name)}(node: cst.{self.cst_class(rule_name)}) -> {node.name}:",
                f'    """Convert a ``{rule_name}`` CST node to its AST node."""',
                f"    return {node.name}.from_cst(node)",
            )
            self.separate()
            self.emit(
                f"def {self.reverse_name(rule_name)}(value: {node.name}) -> cst.{self.cst_class(rule_name)}:",
                f'    """Synthesise a ``{rule_name}`` CST node from its AST node."""',
                "    return value.to_cst()",
            )

    def goal_annotation(self, goal: str) -> str:
        """The type the conveniences take and return: a user type or payload where erased."""
        custom = self.model.custom_types.get(goal)
        if custom is not None:
            return self.custom_path(custom)
        transparent = self.model.transparent_types.get(goal)
        if transparent is not None:
            return self.element_annotation(transparent)
        return self.model.nodes[goal].name

    def emit_conveniences(self) -> None:
        """The one-call entry points, emitted only when the modules behind them are named."""
        goal = self.goal_rule
        goal_type = self.goal_annotation(goal)
        if self.parser_module_name:
            parsed = f'astrt.parse_cst(_parser.Parser, "{goal}", source, filename)'
            self.separate()
            self.emit(
                f"def parse(source: str, filename: str | None = None) -> {goal_type}:",
                f'    """Parse ``source`` as ``{goal}`` and convert the result to its AST."""',
                f"    return {self.from_cst_call(goal, parsed)}",
            )
        if self.unparser_module_name:
            self.separate()
            self.emit(
                f"def unparse(value: {goal_type}, "
                f"renderer_config: fltk.unparse.renderer.RendererConfig | None = None) -> str:",
                '    """Render ``value`` back to source text through the generated formatter."""',
                f"    return astrt.unparse_cst("
                f'_unparser.Unparser, "{goal}", {self.to_cst_call(goal, "value")}, renderer_config)',
            )


def generate_ast_module(
    model: am.AstModel,
    cst_module_name: str,
    parser_module_name: str | None = None,
    unparser_module_name: str | None = None,
    goal_rule: str | None = None,
) -> str:
    """Return the source of the Python AST module for ``model``.

    ``cst_module_name`` is the importable name of the grammar's generated CST module.
    Naming a parser module adds ``parse()``; naming an unparser module adds ``unparse()``.
    ``goal_rule`` defaults to the grammar's first rule.
    """
    return AstGenerator(model, cst_module_name, parser_module_name, unparser_module_name, goal_rule).generate()
