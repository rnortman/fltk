"""Rust AST emitter: turns an ``AstModel`` into a self-contained ``ast.rs``.

Emission is direct source-text generation, like every other Rust backend
(:mod:`fltk.fegen.gsm2tree_rs`, :mod:`fltk.unparse.gsm2unparser_rs`); the emitted file is
normalised by the usual regen -> ``make fix`` -> commit flow.

The emitted module holds the same shapes the Python emitter produces, under the same names: one
struct per product, terminal-only and enum-shaped rule, a payload struct plus an enum per sum
rule, a chain-link struct plus an enum per fold rule, a fieldless value enum per enum-shaped
rule, and an enum per label carrying more than one type.  Where the Python module reaches its
children through references, this one owns them by value, so an edge that can reach its own owner
again is indirected; which edges those are is the model's answer, not this module's.

Equality is written out rather than derived, because it is over semantic data: every span-typed
member and any CST back-pointer is skipped, so two values converted from identical text at
different offsets compare equal.  A type whose values can nest to a depth nothing in the grammar
bounds compares through a worklist instead of by recursion, which is again the model's answer
about which types those are.

Runtime types are named by absolute path (``::fltk_cst_core::Span``,
``::fltk_ast_core::IndexMap``) rather than imported, so a rule named ``span`` — whose type is
``Span`` — cannot collide with a preamble.  What each type looks like is decided by
``ast_model``; this module only spells the decisions as Rust.
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TypeAlias

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import grammar_shape as gshape
from fltk.fegen import naming
from fltk.fegen.gsm2parser_rs import cst_module_import, module_import, rust_str_lit
from fltk.fegen.gsm2tree_rs import RustCstGenerator

_SPAN_TYPE = "::fltk_cst_core::Span"
_SHARED_TYPE = "::fltk_cst_core::Shared"
_INDEX_MAP_TYPE = "::fltk_ast_core::IndexMap"
_AST_ERROR = "::fltk_ast_core::AstError"
_RUNTIME = "::fltk_ast_core"
_UNPARSER_RUNTIME = "::fltk_unparser_core"

_PARSER_ALIAS = "parser"
_UNPARSER_ALIAS = "unparser"
"""What the two optional modules behind the conveniences are imported as."""

_SCALAR_TYPES = {
    am.ScalarKind.TEXT: "String",
    am.ScalarKind.BOOL: "bool",
    am.ScalarKind.SPAN: _SPAN_TYPE,
}

_SCALAR_WITNESSES = {
    am.ScalarKind.TEXT: "String::new()",
    am.ScalarKind.BOOL: "false",
    am.ScalarKind.SPAN: f"{_SPAN_TYPE}::unknown()",
}
"""The cheapest value of each scalar, for the sentinel an iterative teardown writes back."""

_EMPTY_CONTAINERS = {
    am.Container.OPTIONAL: "None",
    am.Container.COLLECTION: "Vec::new()",
    am.Container.MAP: f"{_INDEX_MAP_TYPE}::new()",
}
"""The empty value of each container, for the same sentinel."""

_WIDE_SCALAR_WITNESSES = {"uuid": "::fltk_ast_core::Uuid::nil()", "decimal": "::fltk_ast_core::Decimal::ZERO"}
"""The zero value of the two builtins whose type comes from the runtime's re-exports."""

_WIDE_SCALAR_TYPES = {"uuid": "::fltk_ast_core::Uuid", "decimal": "::fltk_ast_core::Decimal"}
"""The two builtins whose value is a third-party type, named through the runtime's re-export."""

_MODULE_DOC = (
    "//!",
    "//! Every type carries a `span` locating it in the source. Spans never take part in equality,",
    "//! so two values converted from identical text at different offsets — or in different files —",
    "//! compare equal. The types are plain owned data: build them by hand, mutate them in place,",
    "//! compare them by value.",
)

# TODO(ast-deep-clone-debug): both derives recurse per fold link, so a very deep chain overflows.
_NODE_DERIVES = "#[derive(Debug, Clone)]"
"""What a node type derives.

No ``Eq``/``Hash``: a float coercion rules both out, and one uniform surface across every rule is
worth more than either.  ``PartialEq`` is written out rather than derived, because equality skips
every span-typed member.
"""

_VALUE_ENUM_DERIVES = "#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]"
"""What a value enum derives: it is a bare discriminant, so it is match and map material."""

_FEATURE_BUILTINS = ("uuid", "decimal")
"""The ``type:`` builtins whose value type sits behind a ``fltk-ast-core`` feature."""

_EQ_MODULE = am.EQ_SUPPORT_MODULE
"""The private module holding the bounded-stack equality walk.

A Rust module and a Rust type share one namespace, so a rule renamed to this spelling would
collide; the model claims it.
"""

_MAX_LINE = 116
"""Where a chain of comparisons is broken across lines instead of run onto one."""

_ITEM = "item"
"""The local a run's loop binds each of a field's values to."""

_INNER = "inner"
"""The local holding what a field enum's variant wraps."""

_TEXT = "text"
"""The binding a content test reads a value's text through."""

_PAYLOAD = "payload"
"""The local a sum's reverse converter binds its variant's payload to."""

_OPERAND, _OPERANDS = "operand", "operands"
_OPERATOR, _OPERATORS = "operator", "operators"
"""What an unfolded chain's two runs are called."""

_ALT_METHOD = "to_cst_alt"
"""The private method a merged product delegates one alternative to."""

_ALT_SUFFIX = am.ALT_SUFFIX
"""What a private reverse helper's per-alternative halves are suffixed with."""

_HOISTED_PREFIX = "v"
"""A flattened wrapper's reverse helper takes its fields positionally, as `v0`, `v1`, ..."""

_TERMINAL_PREFIX = "TERMINAL_"
"""The function-scoped `static` a text position's terminal is declared as."""

_BORROWED_TYPES = {"String": "str"}
"""What a private helper takes a value of each owning type as; a `&String` parameter is a lint."""

_PUSH_COLUMNS = 12
"""How far in a synthesised ``push_child`` sits: a converter body, one alternative deep."""


def _indent(lines: Iterable[str], columns: int) -> list[str]:
    return [" " * columns + line for line in lines]


def _chain(parts: Sequence[str], operator: str, columns: int) -> list[str]:
    """One boolean chain, on a single line where it fits and one operand per line where it does not."""
    single = f" {operator} ".join(parts)
    if columns + len(single) <= _MAX_LINE:
        return [single]
    return [parts[0], *(f"    {operator} {part}" for part in parts[1:])]


def _resolved_element(element: am.ElementType) -> am.ElementType:
    """What a member actually holds, with ``transparent;`` erasure applied.

    A coerced erasure stops the walk: the member holds the coercion's own value type, which is
    neither a generated node nor a span.
    """
    while isinstance(element, am.TransparentType):
        if element.coercion is not None:
            return element
        element = element.payload
    return element


@dataclasses.dataclass(frozen=True, slots=True)
class _EqMember:
    """One member that takes part in equality.

    ``deep`` names the type the member holds whose comparison must not recurse, and is ``None``
    for every member that can be compared with ``==`` on the spot.
    """

    name: str
    container: am.Container
    deep: str | None


def _string(text: str) -> str:
    """One Rust string literal."""
    return f'"{rust_str_lit(text)}"'


def _message(text: str) -> str:
    """One diagnostic message, as a Rust string literal."""
    return _string(text)


def _tuple_text(members: Sequence[str]) -> str:
    """A Rust tuple; a one-element tuple keeps the trailing comma that makes it one."""
    return f"({members[0]},)" if len(members) == 1 else f"({', '.join(members)})"


def _block(lines: Sequence[str], expression: str) -> list[str]:
    """One value: the bare expression, or a block of the statements it needs, ending in it."""
    if not lines:
        return [expression]
    return ["{", *_indent([*lines, expression], 4), "}"]


def _member_lines(name: str, value: Sequence[str]) -> list[str]:
    """One ``name: value,`` entry of a struct literal, whose value may run over several lines."""
    if len(value) == 1:
        return [f"{name}: {value[0]},"]
    return [f"{name}: {value[0]}", *value[1:-1], f"{value[-1]},"]


@dataclasses.dataclass(frozen=True, slots=True)
class _Value:
    """One generated value expression, and whether reading it can fail.

    ``code`` never carries the trailing ``?``; the two spellings a context needs are derived from
    ``fallible``, which the producer of the expression knows, rather than recovered afterwards by
    inspecting the rendered text.
    """

    code: str
    fallible: bool = False

    @property
    def expression(self) -> str:
        """The value where the surrounding function propagates a failure of its own."""
        return f"{self.code}?" if self.fallible else self.code

    @property
    def result(self) -> str:
        """The value as the function's own ``Result``: a fallible expression already is one."""
        return self.code if self.fallible else f"Ok({self.code})"


def _str_slice(names: Sequence[str]) -> str:
    """One Rust slice of string literals, which is how a set of labels reaches the runtime."""
    return f"&[{', '.join(_string(name) for name in names)}]"


def _count(bound: float) -> str:
    """One item position's upper bound, as the cursor's own spelling of it."""
    return f"{_RUNTIME}::UNBOUNDED" if bound == math.inf else str(int(bound))


@dataclasses.dataclass(frozen=True, slots=True)
class _Held:
    """The value a terminal-only or enum-shaped rule renders, in the spellings a body needs.

    ``place`` is what a method call or a ``match`` reads, ``reference`` an ``&T`` argument,
    ``copied`` the value itself where it is ``Copy``, ``text`` the value as a ``&str``, and
    ``span`` where a failure is reported.
    """

    place: str
    reference: str
    copied: str
    text: str
    span: str


@dataclasses.dataclass(frozen=True, slots=True)
class _Place:
    """One field's value inside a reverse converter, in the spellings a body needs.

    ``cursor`` is the values its item positions draw from and ``populated`` whether it carries
    anything; the rest are how it is handed to a flattened wrapper's helper.
    """

    cursor: str
    populated: str
    reference: str
    optional: str
    value: str
    container: str


_Values: TypeAlias = Callable[[am.Field], _Place]
"""Where a reverse converter body reads one field's value from."""


@dataclasses.dataclass(frozen=True, slots=True)
class _Body:
    """One reverse converter body: whose rule it synthesises, and where its values come from.

    ``owner`` is the type holding the fields, which is what decides whether a value is reached
    through a ``Box``; a private helper has no owning type at all.
    """

    rule_name: str
    owner: str | None
    values: _Values


def _binding(target: str, body: Sequence[str]) -> list[str]:
    """``let <target> = { ... };`` over a body whose last lines are its value."""
    return [f"let {target} = {{", *_indent(body, 4), "};"]


def _if_chain(clauses: Sequence[tuple[str, Sequence[str]]], otherwise: Sequence[str] | None = None) -> list[str]:
    """One ``if`` / ``else if`` chain, with an optional trailing ``else``."""
    lines: list[str] = []
    for index, (condition, body) in enumerate(clauses):
        keyword = "if" if index == 0 else "} else if"
        lines.append(f"{keyword} {condition} {{")
        lines.extend(_indent(body, 4))
    if otherwise is not None:
        lines.append("} else {")
        lines.extend(_indent(otherwise, 4))
    lines.append("}")
    return lines


def _if_block(conditions: Sequence[str], body: Sequence[str], columns: int) -> list[str]:
    """One ``if`` whose condition is a ``&&`` chain, broken across lines when it is long."""
    parts = _chain(list(conditions), "&&", columns + len("if "))
    lines = [f"if {parts[0]}"] if len(parts) > 1 else [f"if {parts[0]} {{"]
    if len(parts) > 1:
        lines.extend(parts[1:])
        lines.append("{")
    lines.extend(_indent(body, 4))
    lines.append("}")
    return lines


def _rust_path(path: str | None, rule_name: str, statement: str, entry: str) -> str:
    """A sidecar entry's Rust path, or the reason the module cannot be emitted without it."""
    if path is None:
        msg = (
            f"rule '{rule_name}': `{statement}` names no `{entry}:` type, so the Rust AST module "
            f"has nothing to reference"
        )
        raise ValueError(msg)
    return path


class RustAstGenerator:
    """Emits the Rust AST module for one grammar's model."""

    def __init__(
        self,
        model: am.AstModel,
        cst_mod_path: str = "super::cst",
        source_name: str | None = None,
        *,
        parser_mod_path: str | None = None,
        unparser_mod_path: str | None = None,
        goal_rule: str | None = None,
    ) -> None:
        self.model = model
        self.cst_mod_path = cst_mod_path
        self.source_name = source_name
        self.parser_mod_path = parser_mod_path
        self.unparser_mod_path = unparser_mod_path
        # Resolved only where something needs it: a module emitting neither entry point names no
        # goal rule, and an explicitly named one is still checked so the option cannot be ignored.
        self.goal_rule = (
            am.resolve_goal_rule(model, goal_rule)
            if goal_rule is not None or parser_mod_path is not None or unparser_mod_path is not None
            else None
        )
        # Child-enum naming and variant counts delegate to the CST generator.
        self.cst = RustCstGenerator(model.grammar)
        self.recursion = am.recursion(model)
        self.span_bearing = am.span_bearing(model)
        # The sentinel a fold link's iterative teardown writes into a side it has taken the child
        # out of; a fold whose operands bottom out in a `custom(...)` type has none.
        self.witnesses = am.fold_witnesses(model)
        # The types whose span is reached through a method rather than a member: an enum carries
        # no member of its own, so it delegates to whichever payload it holds.
        self.span_methods = frozenset(
            node.name
            for rule_name, node in model.nodes.items()
            if isinstance(node, am.SumNode | am.FoldNode)
            and node.name in self.span_bearing
            and rule_name not in model.transparent_types
        ) | frozenset(name for name in model.field_enums if name in self.span_bearing)
        self.lines: list[str] = []
        # The terminals the body being emitted validates text against, in first-ask order; each
        # body declares its own as `static` items and starts again from empty.
        self.terminals: dict[str, str] = {}
        # The deep types in emission order, which is the order their walk items are declared in.
        self._walked: list[str] = []
        self._generated: str | None = None

    # --- Names and types -----------------------------------------------------------------

    @staticmethod
    def cst_class(rule_name: str) -> str:
        """The CST node type for a rule, as the Rust CST emitter names it."""
        return naming.snake_to_upper_camel(rule_name)

    def cst_node_type(self, rule_name: str) -> str:
        return f"cst::{self.cst_class(rule_name)}"

    def child_enum_type(self, rule_name: str) -> str:
        """The CST child enum of a rule, which is what its children slice holds."""
        return f"cst::{self.cst.child_enum_name(self.cst_class(rule_name))}"

    def label_variant(self, rule_name: str, label: str) -> str:
        """The CST label enum member one label is spelled as."""
        return f"cst::{self.cst.label_enum_name(self.cst_class(rule_name))}::{naming.snake_to_upper_camel(label)}"

    def child_variant(self, rule_name: str, kind: str) -> str:
        """The child enum member one child kind occupies: a referenced rule, or a span."""
        variant = "Span" if kind == gshape.TEXT_KIND else self.cst_class(kind)
        return f"{self.child_enum_type(rule_name)}::{variant}"

    def child_variant_count(self, rule_name: str) -> int:
        """How many kinds of child a rule's nodes can hold; one means it needs no test."""
        return self.cst.num_child_variants(rule_name)

    def element_rule(self, element: am.ElementType) -> str:
        """The rule whose CST node a reference to ``element`` carries."""
        rule_name = am.element_rule(self.model, element)
        assert rule_name is not None, f"no rule carries values of {element!r}"
        return rule_name

    @staticmethod
    def member_name(name: str) -> str:
        """A field name spelled as a usable Rust identifier: a keyword becomes a raw one."""
        return ce.rust_method_ident(name)

    def custom_path(self, custom: am.CustomType) -> str:
        """The path of a ``custom(...)`` rule's Rust type."""
        return _rust_path(custom.rust, custom.rule_name, "custom(...)", "rust")

    def coercion_type(self, coercion: am.Coercion) -> str:
        """The Rust type a ``type:`` coercion's value has."""
        if isinstance(coercion, am.CustomCoercion):
            return _rust_path(coercion.rust_type, coercion.rule_name, "type: custom(...)", "rust_type")
        return _WIDE_SCALAR_TYPES.get(coercion.name, coercion.name)

    def element_type(self, element: am.ElementType) -> str:
        """The Rust type one field element has, before its container and any indirection."""
        if isinstance(element, am.NodeType):
            return element.name
        if isinstance(element, am.CustomType):
            return self.custom_path(element)
        if isinstance(element, am.TransparentType):
            if element.coercion is not None:
                return self.coercion_type(element.coercion)
            return self.element_type(element.payload)
        return _SCALAR_TYPES[element.kind]

    def is_boxed_element(self, owner: str | None, element: am.ElementType) -> bool:
        """Whether ``owner`` reaches ``element`` through an edge that closes a cycle.

        ``owner`` is ``None`` where there is no owning type at all — a ``flatten;`` wrapper's
        helper hands its fields to whichever type references it, and the indirection each of
        those needs is that type's own answer.
        """
        if owner is None:
            return False
        return any(self.recursion.is_boxed(owner, target) for target in am.embedded_types(element))

    def embedded_type(self, owner: str | None, element: am.ElementType) -> str:
        """One element held by value in ``owner``, boxed where that edge closes a cycle."""
        inner = self.element_type(element)
        return f"Box<{inner}>" if self.is_boxed_element(owner, element) else inner

    def boxed(self, value: _Value, owner: str | None, element: am.ElementType) -> _Value:
        """One converted value, indirected where the owning type holds it through a ``Box``.

        The indirection consumes the propagation, so what comes back is infallible.
        """
        if not self.is_boxed_element(owner, element):
            return value
        return _Value(f"Box::new({value.expression})")

    def deep_type(self, element: am.ElementType) -> str | None:
        """The type this element holds whose comparison must not recurse, if it holds one."""
        resolved = _resolved_element(element)
        if isinstance(resolved, am.NodeType) and resolved.name in self.recursion.deep:
            return resolved.name
        return None

    @staticmethod
    def is_position_only(element: am.ElementType) -> bool:
        """Whether a member holding this element carries position and nothing else."""
        resolved = _resolved_element(element)
        return isinstance(resolved, am.ScalarType) and resolved.kind is am.ScalarKind.SPAN

    def eq_members(self, fields: Sequence[am.Field]) -> list[_EqMember]:
        """The fields of a struct that take part in equality, in declaration order.

        A labeled literal's ``Span`` / ``Vec<Span>`` is dropped along with the node's own ``span``
        and any CST back-pointer: a literal's text is a grammar constant, so such a member records
        position only and two values converted from identical text must compare equal.
        """
        return [
            _EqMember(self.member_name(field.name), field.type.container, self.deep_type(field.type.element))
            for field in fields
            if not self.is_position_only(field.type.element)
        ]

    def field_type(self, owner: str | None, field: am.Field) -> str:
        """The Rust type of one field of ``owner``."""
        container = field.type.container
        if container is am.Container.COLLECTION:
            return f"Vec<{self.element_type(field.type.element)}>"
        if container is am.Container.MAP:
            assert field.type.key is not None
            key = self.element_type(field.type.key.element)
            return f"{_INDEX_MAP_TYPE}<{key}, {self.element_type(field.type.element)}>"
        inner = self.embedded_type(owner, field.type.element)
        return f"Option<{inner}>" if container is am.Container.OPTIONAL else inner

    # --- Emission ------------------------------------------------------------------------

    def emit(self, *lines: str) -> None:
        self.lines.extend(lines)

    def separate(self) -> None:
        """Open a new top-level item."""
        self.lines.append("")

    def generate(self) -> str:
        """Return the complete ``ast.rs`` source.

        Idempotent: a second call hands back the first call's result, matching the other Rust
        generators, which are memoized so a caller cannot double-emit into one file.
        """
        if self._generated is not None:
            return self._generated
        self.emit_header()
        for rule_name, node in self.model.nodes.items():
            self.emit_node(rule_name, node)
        self.emit_field_enums()
        self.emit_converters()
        self.emit_reverse_converters()
        self.emit_conveniences()
        self.emit_eq_module()
        self._generated = "\n".join(self.lines) + "\n"
        return self._generated

    def map_fields(self) -> bool:
        """Whether any generated type holds a keyed collection, which the container feature gates."""
        products: list[Sequence[am.Field]] = [
            node.fields for node in self.model.nodes.values() if isinstance(node, am.ProductNode)
        ]
        products.extend(payload.fields for payload in self.model.payload_classes.values())
        return any(field.type.container is am.Container.MAP for fields in products for field in fields)

    def required_features(self) -> list[str]:
        """The ``fltk-ast-core`` features the emitted module needs enabled to compile."""
        features = ["indexmap"] if self.map_fields() else []
        builtins = {coercion.name for coercion in am.coercions(self.model) if isinstance(coercion, am.BuiltinCoercion)}
        features.extend(name for name in _FEATURE_BUILTINS if name in builtins)
        return features

    def emit_header(self) -> None:
        origin = "" if self.source_name is None else f" from `{rust_str_lit(self.source_name)}`"
        self.emit(f"//! Generated by fltk gen-rust-ast{origin}. Do not edit.", *_MODULE_DOC)
        features = self.required_features()
        if features:
            self.emit("//!", f"//! Requires these `fltk-ast-core` features: {', '.join(features)}.")
        # Every converter's signature names a CST node type, so the import is always used.
        self.emit("", cst_module_import(self.cst_mod_path))
        if self.parser_mod_path is not None:
            self.emit(module_import(self.parser_mod_path, _PARSER_ALIAS))
        if self.unparser_mod_path is not None:
            self.emit(module_import(self.unparser_mod_path, _UNPARSER_ALIAS))

    def emit_node(self, rule_name: str, node: am.RuleNode) -> None:
        if rule_name in self.model.flattened_rules:
            # A flattened wrapper's fields live on the types referencing it, so it has no type.
            return
        if isinstance(node, am.EnumNode) and node.value_enum.name in self.model.value_enums:
            # Under `bool:` the node carries a plain `bool` and the enum is not a type at all.
            self.emit_value_enum(node.value_enum)
        if rule_name in self.model.transparent_types:
            # An erased rule's use sites carry its payload, which is the only type it leaves.
            return
        if isinstance(node, am.ProductNode):
            self.emit_struct(node.name, rule_name, node.fields, f"AST node for rule `{rule_name}`.")
        elif isinstance(node, am.TerminalNode):
            self.emit_terminal_struct(rule_name, node)
        elif isinstance(node, am.EnumNode):
            self.emit_enum_struct(rule_name, node)
        elif isinstance(node, am.SumNode):
            self.emit_sum(rule_name, node)
        else:
            self.emit_fold(rule_name, node)

    def emit_struct(self, type_name: str, rule_name: str, fields: Sequence[am.Field], doc: str) -> None:
        """A struct with one member per field, plus ``span`` and any CST back-pointer."""
        members = [(self.member_name(field.name), self.field_type(type_name, field)) for field in fields]
        self.emit_struct_lines(type_name, rule_name, doc, members, self.eq_members(fields))

    def emit_struct_lines(
        self,
        type_name: str,
        rule_name: str,
        doc: str,
        members: Sequence[tuple[str, str]],
        equality: Sequence[_EqMember],
        *,
        notes: Sequence[str] = (),
    ) -> None:
        self.separate()
        self.emit(f"/// {doc}")
        for note in notes:
            self.emit("///", f"/// {note}")
        self.emit(_NODE_DERIVES, f"pub struct {type_name} {{")
        for name, member_type in members:
            self.emit(f"    pub {name}: {member_type},")
        self.emit(f"    pub span: {_SPAN_TYPE},")
        self.emit(*self.backpointer_member(rule_name))
        self.emit("}")
        self.emit_struct_eq(type_name, equality)

    def backpointer_member(self, rule_name: str) -> list[str]:
        """The ``cst`` member ``option cst = true;`` asks every type to carry.

        Hand-built and synthesized values have none, so it is optional; the AST members stay
        authoritative and the reverse direction ignores it.
        """
        if not self.model.cst_backpointers:
            return []
        return [
            "    /// The CST node this value was converted from; `None` on a hand-built value.",
            f"    pub {am.CST_FIELD_NAME}: Option<{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>>,",
        ]

    def emit_terminal_struct(self, rule_name: str, node: am.TerminalNode) -> None:
        source = "its own span" if node.text_from is None else f"its `{node.text_from}` child"
        member = ("text", "String") if node.coercion is None else ("value", self.coercion_type(node.coercion))
        self.emit_struct_lines(
            node.name,
            rule_name,
            f"AST node for terminal-only rule `{rule_name}`, over the text of {source}.",
            (member,),
            (_EqMember(member[0], am.Container.SINGLE, None),),
        )

    def emit_enum_struct(self, rule_name: str, node: am.EnumNode) -> None:
        boolean = node.bool_truthy is not None
        member_type = "bool" if boolean else node.value_enum.name
        carries = "which of its two literals matched" if boolean else "which literal alternative matched"
        self.emit_struct_lines(
            node.name,
            rule_name,
            f"AST node for rule `{rule_name}`: {carries}.",
            (("value", member_type),),
            (_EqMember("value", am.Container.SINGLE, None),),
        )

    def emit_value_enum(self, value_enum: am.ValueEnum) -> None:
        self.separate()
        self.emit(
            f"/// Which alternative of rule `{value_enum.rule_name}` matched.",
            _VALUE_ENUM_DERIVES,
            f"pub enum {value_enum.name} {{",
        )
        self.emit(*(f"    {variant.name}," for variant in value_enum.variants))
        self.emit("}")

    def emit_sum(self, rule_name: str, node: am.SumNode) -> None:
        """The payload structs of a sum rule's generated variants, then the enum over them."""
        for variant in node.variants:
            payload = am.generated_payload(self.model, variant)
            if payload is not None:
                self.emit_struct(
                    payload.name,
                    rule_name,
                    payload.fields,
                    f"The `{variant.name}` alternative of rule `{rule_name}`.",
                )
        payloads = [(variant.name, variant.payload) for variant in node.variants]
        self.emit_payload_enum(node.name, f"AST node for rule `{rule_name}`: whichever alternative matched.", payloads)

    def emit_fold(self, rule_name: str, node: am.FoldNode) -> None:
        """The chain link of a fold rule, then the enum choosing between an operand and a link."""
        nesting = "left" if node.direction is ac.FoldDirection.LEFT else "right"
        binary = node.binary
        witness = self.witnesses.get(rule_name)
        residual = (
            "Teardown recurses once per link: this rule's operands reach a type the generator "
            "cannot construct a value of, so it has no sentinel to tear the chain down with. "
            "Dropping a chain of many tens of thousands of links overflows the stack."
        )
        notes: tuple[str, ...] = () if witness is not None else (residual,)
        self.emit_struct_lines(
            binary.name,
            rule_name,
            f"One link of the {nesting}-nested chain rule `{rule_name}` folds into. "
            f"`span` covers everything below the link.",
            (
                (self.member_name(binary.op.name), self.field_type(binary.name, binary.op)),
                # The chain's own indirections, which the recursion analysis therefore ignores.
                (am.FOLD_LHS, f"Box<{node.name}>"),
                (am.FOLD_RHS, f"Box<{node.name}>"),
            ),
            (
                *self.eq_members((binary.op,)),
                # Both sides are the chain, which is what the equality walk exists for.
                *(
                    _EqMember(side, am.Container.SINGLE, self.deep_type(am.NodeType(node.name)))
                    for side in (am.FOLD_LHS, am.FOLD_RHS)
                ),
            ),
            notes=notes,
        )
        payloads = [
            (node.operand_variant, node.operand.type.element),
            (node.binary_variant, am.NodeType(binary.name)),
        ]
        self.emit_payload_enum(
            node.name,
            f"AST node for fold rule `{rule_name}`: a bare operand, or one link of the chain.",
            payloads,
        )
        if witness is not None:
            self.emit_drop_witness(rule_name, node, witness)
            self.emit_iterative_drop(rule_name, node)

    # --- Iterative teardown --------------------------------------------------------------

    def witness_expression(self, witness: am.Witness) -> str:
        """One witness plan, as the Rust expression constructing it."""
        if isinstance(witness, am.ScalarWitness):
            return self.witness_scalar(witness.element)
        if isinstance(witness, am.EmptyWitness):
            return _EMPTY_CONTAINERS[witness.container]
        if isinstance(witness, am.UnitWitness):
            return f"{witness.type_name}::{witness.variant}"
        if isinstance(witness, am.VariantWitness):
            payload = self.witness_member(witness.type_name, witness.element, witness.payload)
            return f"{witness.type_name}::{witness.variant}({payload})"
        members = [
            f"{self.member_name(member.name)}: {self.witness_member(witness.type_name, member.element, member.value)}"
            for member in witness.members
        ]
        members.append(f"span: {_SPAN_TYPE}::unknown()")
        if self.model.cst_backpointers:
            members.append(f"{am.CST_FIELD_NAME}: None")
        return f"{witness.type_name} {{ {', '.join(members)} }}"

    def witness_member(self, owner: str, element: am.ElementType, witness: am.Witness) -> str:
        """One member of a witness, indirected where the owning type holds it through a ``Box``.

        A container is an indirection already, so only a required-single member can be boxed.
        """
        value = self.witness_expression(witness)
        if isinstance(witness, am.EmptyWitness) or not self.is_boxed_element(owner, element):
            return value
        return f"Box::new({value})"

    def witness_scalar(self, element: am.ElementType) -> str:
        """The cheapest value of one scalar element, which is what a sentinel is made of."""
        if isinstance(element, am.ScalarType):
            return _SCALAR_WITNESSES[element.kind]
        assert isinstance(element, am.TransparentType)
        coercion = element.coercion
        assert isinstance(coercion, am.BuiltinCoercion)
        wide = _WIDE_SCALAR_WITNESSES.get(coercion.name)
        if wide is not None:
            return wide
        return "0.0" if coercion.is_float else "0"

    def emit_drop_witness(self, rule_name: str, node: am.FoldNode, witness: am.Witness) -> None:
        """The function building the sentinel a link's teardown writes back into an emptied side."""
        self.separate()
        self.emit(
            f"/// A cheap `{node.name}` for a chain link to leave behind where it took a child out.",
            f"fn {am.drop_witness_name(rule_name)}() -> {node.name} {{",
            f"    {self.witness_expression(witness)}",
            "}",
        )

    def emit_iterative_drop(self, rule_name: str, node: am.FoldNode) -> None:
        """``Drop`` for a chain link, taking the chain below it apart through a worklist.

        A chain is as long as the source repeated the operator, so derived drop glue would recurse
        once per link and abort the process on a long one.  Only the link struct carries this: the
        enum stays destructurable by value, which is how consumers match it.
        """
        witness = f"{am.drop_witness_name(rule_name)}()"
        link = f"{node.name}::{node.binary_variant}"
        replace = "::std::mem::replace"
        self.separate()
        self.emit(
            f"impl Drop for {node.binary.name} {{",
            "    /// Take the chain below this link apart through a worklist rather than by recursion.",
            "    fn drop(&mut self) {",
            "        // A link holding two bare operands tears down by ordinary glue: their depth is the",
            "        // parse's own. This is also what ends the nested drops the loop below triggers.",
            f"        if !matches!(&*self.{am.FOLD_LHS}, {link}(_)) && !matches!(&*self.{am.FOLD_RHS}, {link}(_)) {{",
            "            return;",
            "        }",
            f"        let mut stack: Vec<{node.name}> = vec![",
            f"            {replace}(&mut *self.{am.FOLD_LHS}, {witness}),",
            f"            {replace}(&mut *self.{am.FOLD_RHS}, {witness}),",
            "        ];",
            "        while let Some(below) = stack.pop() {",
            f"            if let {link}(mut link) = below {{",
            f"                stack.push({replace}(&mut *link.{am.FOLD_LHS}, {witness}));",
            f"                stack.push({replace}(&mut *link.{am.FOLD_RHS}, {witness}));",
            "            }",
            "            // The popped value drops here holding witnesses or bare operands, so its own",
            "            // teardown takes the fast path above.",
            "        }",
            "    }",
            "}",
        )

    def emit_payload_enum(self, type_name: str, doc: str, payloads: Sequence[tuple[str, am.ElementType]]) -> None:
        """An enum over payload element types, plus the ``span()`` accessor when it has one."""
        self.emit_enum(type_name, doc, payloads)
        self.emit_span_method(type_name, payloads)

    def emit_enum(self, type_name: str, doc: str, variants: Sequence[tuple[str, am.ElementType]]) -> None:
        self.separate()
        self.emit(f"/// {doc}", _NODE_DERIVES, f"pub enum {type_name} {{")
        self.emit(*(f"    {name}({self.embedded_type(type_name, element)})," for name, element in variants))
        self.emit("}")
        self.emit_enum_eq(type_name, variants)

    def emit_span_method(self, type_name: str, payloads: Sequence[tuple[str, am.ElementType]]) -> None:
        """``span()`` on an enum, emitted only when every payload it can hold carries one.

        An erased payload — a plain ``i64``, a value enum — has none, and the honest consequence is
        that the enum has no accessor rather than one returning a span nothing stands behind.
        """
        if type_name not in self.span_methods:
            return
        self.separate()
        self.emit(
            f"impl {type_name} {{",
            "    /// The span of whichever payload this value holds.",
            f"    pub fn span(&self) -> &{_SPAN_TYPE} {{",
            "        match self {",
        )
        for variant, element in payloads:
            self.emit(f"            Self::{variant}(payload) => {self.span_expression(element)},")
        self.emit("        }", "    }", "}")

    def span_expression(self, element: am.ElementType) -> str:
        """Where the span of one payload is read: a member, or the payload's own accessor."""
        resolved = element
        while isinstance(resolved, am.TransparentType):
            resolved = resolved.payload
        assert isinstance(resolved, am.NodeType)
        return "payload.span()" if resolved.name in self.span_methods else "&payload.span"

    def emit_field_enums(self) -> None:
        """One enum per label carrying more than one type, over the types it can hold."""
        for field_enum in self.model.field_enums.values():
            self.emit_payload_enum(
                field_enum.name,
                f"The `{field_enum.label}` label of rule `{field_enum.rule_name}`, which carries more than one type.",
                [(variant.name, variant.element) for variant in field_enum.variants],
            )

    # --- Equality ------------------------------------------------------------------------

    def walks(self, type_name: str) -> bool:
        """Whether this type compares through the worklist rather than by recursion.

        Recorded on first ask in emission order, which is the order the walk's items are declared
        in, so the item enum lists exactly the types that got an ``eq_shallow``.
        """
        if type_name not in self.recursion.deep:
            return False
        if type_name not in self._walked:
            self._walked.append(type_name)
        return True

    def emit_eq_driver(self, type_name: str) -> None:
        """``PartialEq`` for a type whose values nest to a depth nothing in the grammar bounds."""
        self.separate()
        self.emit(
            f"impl PartialEq for {type_name} {{",
            "    /// Bounded stack: the pending pairs live in a worklist, not in call frames.",
            "    fn eq(&self, other: &Self) -> bool {",
            f"        {_EQ_MODULE}::run({_EQ_MODULE}::Item::{type_name}(self, other))",
            "    }",
            "}",
        )

    def emit_struct_eq(self, type_name: str, members: Sequence[_EqMember]) -> None:
        """``PartialEq`` for one struct, over the members that carry semantic data."""
        if self.walks(type_name):
            self.emit_eq_driver(type_name)
            walked = any(member.deep is not None for member in members)
            self.emit_eq_shallow(type_name, self.struct_shallow_lines(members), walked=walked)
            return
        self.separate()
        if not members:
            self.emit(
                f"impl PartialEq for {type_name} {{",
                "    /// A marker node carries position only, so every value of it is equal to every other.",
                "    fn eq(&self, _other: &Self) -> bool {",
                "        true",
                "    }",
                "}",
            )
            return
        comparisons = _chain([f"self.{member.name} == other.{member.name}" for member in members], "&&", 8)
        self.emit(f"impl PartialEq for {type_name} {{", "    fn eq(&self, other: &Self) -> bool {")
        self.emit(*_indent(comparisons, 8))
        self.emit("    }", "}")

    def emit_enum_eq(self, type_name: str, variants: Sequence[tuple[str, am.ElementType]]) -> None:
        """``PartialEq`` for one enum: the same variant, then its payloads."""
        if self.walks(type_name):
            self.emit_eq_driver(type_name)
            walked = any(self.deep_type(element) is not None for _name, element in variants)
            self.emit_eq_shallow(type_name, self.enum_shallow_lines(variants), walked=walked)
            return
        self.separate()
        self.emit(
            f"impl PartialEq for {type_name} {{",
            "    fn eq(&self, other: &Self) -> bool {",
            "        match (self, other) {",
        )
        for name, _element in variants:
            self.emit(f"            (Self::{name}(a), Self::{name}(b)) => a == b,")
        if len(variants) > 1:
            self.emit("            _ => false,")
        self.emit("        }", "    }", "}")

    def emit_eq_shallow(self, type_name: str, body: Sequence[str], *, walked: bool) -> None:
        """The one level of comparison the walk performs per pending pair."""
        worklist = "worklist" if walked else "_worklist"
        signature = f"fn eq_shallow<'a>(&'a self, other: &'a Self, {worklist}: &mut Vec<{_EQ_MODULE}::Item<'a>>)"
        self.separate()
        self.emit(
            f"impl {type_name} {{",
            "    /// Compare what cannot recurse, enqueueing the pairs that can.",
            f"    {signature} -> bool {{",
        )
        self.emit(*_indent(body, 8))
        self.emit("    }", "}")

    def struct_shallow_lines(self, members: Sequence[_EqMember]) -> list[str]:
        lines: list[str] = []
        direct = [member for member in members if member.deep is None]
        if direct:
            differ = _chain([f"self.{member.name} != other.{member.name}" for member in direct], "||", 12)
            lines.append(f"if {differ[0]}" + (" {" if len(differ) == 1 else ""))
            if len(differ) > 1:
                lines.extend(differ[1:])
                lines.append("{")
            lines.extend(("    return false;", "}"))
        for member in members:
            if member.deep is not None:
                lines.extend(self.eq_walk_lines(member))
        lines.append("true")
        return lines

    def enum_shallow_lines(self, variants: Sequence[tuple[str, am.ElementType]]) -> list[str]:
        lines = ["match (self, other) {"]
        for name, element in variants:
            deep = self.deep_type(element)
            if deep is None:
                lines.append(f"    (Self::{name}(a), Self::{name}(b)) => a == b,")
                continue
            lines.extend(
                (
                    f"    (Self::{name}(a), Self::{name}(b)) => {{",
                    f"        worklist.push({_EQ_MODULE}::Item::{deep}(a, b));",
                    "        true",
                    "    }",
                )
            )
        if len(variants) > 1:
            lines.append("    _ => false,")
        lines.append("}")
        return lines

    def eq_walk_lines(self, member: _EqMember) -> list[str]:
        """Enqueueing one member's pair, or pairs, for the walk.

        A collection compares element by element in order, and a map by key — the same answers
        ``Vec`` and ``IndexMap`` give when their own ``PartialEq`` does the comparing, so a member
        whose element happens to be recursive compares no differently from one whose is not.
        """
        item = f"{_EQ_MODULE}::Item::{member.deep}"
        name = member.name
        if member.container is am.Container.SINGLE:
            return [f"worklist.push({item}(&self.{name}, &other.{name}));"]
        if member.container is am.Container.OPTIONAL:
            return [
                f"match (&self.{name}, &other.{name}) {{",
                f"    (Some(a), Some(b)) => worklist.push({item}(a, b)),",
                "    (None, None) => {}",
                "    _ => return false,",
                "}",
            ]
        lines = [f"if self.{name}.len() != other.{name}.len() {{", "    return false;", "}"]
        if member.container is am.Container.COLLECTION:
            lines.extend(
                (
                    f"for (a, b) in self.{name}.iter().zip(other.{name}.iter()) {{",
                    f"    worklist.push({item}(a, b));",
                    "}",
                )
            )
            return lines
        lines.extend(
            (
                f"for (key, a) in &self.{name} {{",
                f"    let Some(b) = other.{name}.get(key) else {{",
                "        return false;",
                "    };",
                f"    worklist.push({item}(a, b));",
                "}",
            )
        )
        return lines

    def emit_eq_module(self) -> None:
        """The walk itself, emitted only for a grammar whose types can nest without a bound."""
        if not self._walked:
            return
        self.separate()
        self.emit(
            "/// The bounded-stack equality walk over the types whose values nest without a bound.",
            "///",
            "/// A chain is as deep as the source it was parsed from, so comparing one by recursion would",
            "/// exhaust the stack. Each such type's `eq` seeds `run` with its own pair instead, and every",
            "/// pair still to compare waits here rather than in a call frame.",
            f"mod {_EQ_MODULE} {{",
            "    /// One pair still to compare.",
            "    pub(super) enum Item<'a> {",
        )
        self.emit(*(f"        {name}(&'a super::{name}, &'a super::{name})," for name in self._walked))
        self.emit(
            "    }",
            "",
            "    impl<'a> Item<'a> {",
            "        fn compare(self, worklist: &mut Vec<Self>) -> bool {",
            "            match self {",
        )
        self.emit(*(f"                Self::{name}(a, b) => a.eq_shallow(b, worklist)," for name in self._walked))
        self.emit(
            "            }",
            "        }",
            "    }",
            "",
            "    /// Whether the pair at the root of the walk, and everything below it, are equal.",
            "    pub(super) fn run(root: Item<'_>) -> bool {",
            "        let mut worklist = vec![root];",
            "        while let Some(item) = worklist.pop() {",
            "            if !item.compare(&mut worklist) {",
            "                return false;",
            "            }",
            "        }",
            "        true",
            "    }",
            "}",
        )

    # --- Converters: CST -> AST ----------------------------------------------------------

    def emit_converters(self) -> None:
        """The forward direction: one converter per rule, plus one per field enum."""
        for rule_name, node in self.model.nodes.items():
            self.emit_rule_converter(rule_name, node)
        for field_enum in self.model.field_enums.values():
            self.emit_field_enum_converter(field_enum)

    def emit_rule_converter(self, rule_name: str, node: am.RuleNode) -> None:
        if isinstance(node, am.FoldNode):
            self.emit_fold_converter(rule_name, node)
            return
        if rule_name in self.model.flattened_rules:
            self.emit_flat_converter(rule_name, node)
        elif rule_name in self.model.transparent_types:
            self.emit_erased_converter(rule_name, node)
        elif isinstance(node, am.ProductNode):
            self.emit_from_cst(node.name, rule_name, self.product_body(node.name, rule_name, node.fields, node.hoists))
        elif isinstance(node, am.TerminalNode):
            self.emit_from_cst(node.name, rule_name, self.terminal_body(rule_name, node))
        elif isinstance(node, am.EnumNode):
            self.emit_from_cst(node.name, rule_name, self.enum_body(rule_name, node))
        else:
            self.emit_sum_converters(rule_name, node)

    def emit_from_cst(self, type_name: str, rule_name: str, body: Sequence[str], doc: str | None = None) -> None:
        """``from_cst`` on one generated type, over the CST node of ``rule_name``."""
        self.separate()
        self.emit(
            f"impl {type_name} {{",
            f"    /// {doc or f'Convert a `{rule_name}` CST node.'}",
            f"    pub fn from_cst(node: &{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>)"
            f" -> Result<Self, {_AST_ERROR}> {{",
        )
        self.emit(*_indent(body, 8))
        self.emit("    }", "}")

    def backpointer_argument(self) -> list[str]:
        """The ``cst`` member a converter fills, when the sidecar asked for back-pointers."""
        return [f"{am.CST_FIELD_NAME}: Some(node.clone()),"] if self.model.cst_backpointers else []

    def product_body(
        self,
        type_name: str,
        rule_name: str,
        fields: Sequence[am.Field],
        hoists: Sequence[am.Hoist] = (),
    ) -> list[str]:
        """The converter body of a product or a sum's payload: one member per field, then ``span``.

        A field's value is a block of its own inside the struct literal, so the only locals the
        body binds are ``cst_node`` and one per flattened wrapper — nothing named after a label,
        which a grammar chooses and could otherwise shadow what the body reads.
        """
        lines = ["let cst_node = node.read();"]
        lines.extend(self.bucket_lines(rule_name, self.body_labels(fields, hoists)))
        for hoist in hoists:
            lines.extend(self.hoist_lines(type_name, rule_name, hoist))
        positions = {(field.hoist, field.name): index for hoist in hoists for index, field in enumerate(hoist.fields)}
        lines.append("Ok(Self {")
        for field in fields:
            member = self.member_name(field.name)
            if field.hoist is None:
                statements, held = self.field_value(type_name, rule_name, field)
                value = _block(statements, held.expression)
            else:
                value = [f"{self.hoist_variable(field.hoist)}.{positions[field.hoist, field.name]}"]
            lines.extend(_indent(_member_lines(member, value), 4))
        lines.append("    span: cst_node.span().clone(),")
        lines.extend(_indent(self.backpointer_argument(), 4))
        lines.append("})")
        return lines

    @staticmethod
    def bucket_name(label: str) -> str:
        """The local holding the children that carry one label."""
        return f"children_{label}"

    @staticmethod
    def body_labels(fields: Sequence[am.Field], hoists: Sequence[am.Hoist]) -> list[str]:
        """The labels one converter body reads, deduplicated, in the order it binds them.

        A hoisted field is read out of its wrapper's tuple rather than off a child, so it is the
        wrapper's own label that the body reads; a wrapper carrying no fields is never read at all.
        """
        labels = [hoist.label for hoist in hoists if hoist.fields]
        labels.extend(field.label for field in fields if field.hoist is None)
        return list(dict.fromkeys(labels))

    def bucket_lines(self, rule_name: str, labels: Sequence[str]) -> list[str]:
        """Statements binding one local per label to the children carrying it, in source order.

        The children are walked once for the whole conversion, not once per label: the wide
        dimension is the children — a config body holding hundreds of settings — so a scan per
        field would cost a pass and a vector allocation each.

        Unlabeled children — trivia and ``$``-included literals — are dropped, which is what
        makes a converter accept CSTs from the trivia-capturing and non-capturing parsers alike.
        """
        if not labels:
            return []
        if len(labels) == 1:
            return self.collect_lines(rule_name, labels[0], self.bucket_name(labels[0]))
        child_type = self.child_enum_type(rule_name)
        lines = [f"let mut {self.bucket_name(label)}: Vec<&{child_type}> = Vec::new();" for label in labels]
        lines.extend(("for (label, child) in cst_node.children() {", "    match label {"))
        lines.extend(
            f"        Some({self.label_variant(rule_name, label)}) => {self.bucket_name(label)}.push(child),"
            for label in labels
        )
        lines.extend(("        _ => {}", "    }", "}"))
        return lines

    def collect_lines(self, rule_name: str, label: str, target: str) -> list[str]:
        """Statements collecting the children carrying one label, in source order."""
        return [
            f"let {target}: Vec<&{self.child_enum_type(rule_name)}> = cst_node",
            "    .children()",
            "    .iter()",
            f"    .filter(|(label, _)| matches!(label, Some({self.label_variant(rule_name, label)})))",
            "    .map(|(_, child)| child)",
            "    .collect();",
        ]

    def child_pattern_lines(self, rule_name: str, label: str, variant: str, child: str, target: str) -> list[str]:
        """Statements binding ``target`` to what one child of a known kind holds.

        A rule whose nodes can hold only one kind of child needs no test: the destructure is
        irrefutable, and a ``let ... else`` on it would be a warning.
        """
        binding = f"let {variant}({target}) = {child}"
        if self.child_variant_count(rule_name) == 1:
            return [f"{binding};"]
        return [
            f"{binding} else {{",
            f'    return Err({_RUNTIME}::unexpected_child("{rule_name}", "{label}", cst_node.span()));',
            "};",
        ]

    def element_code(self, rule_name: str, label: str, element: am.ElementType, child: str) -> tuple[list[str], _Value]:
        """Statements to run first, and the expression for the element one CST child carries."""
        context = f'"{rule_name}", "{label}", cst_node.span()'
        if isinstance(element, am.NodeType) and element.name in self.model.field_enums:
            converter = am.field_enum_converter_name(element.name)
            return [], _Value(f"{converter}({child}, cst_node.span())", fallible=True)
        if isinstance(element, am.ScalarType):
            lines = self.child_pattern_lines(
                rule_name, label, self.child_variant(rule_name, gshape.TEXT_KIND), child, "span_child"
            )
            if element.kind is am.ScalarKind.SPAN:
                # A literal's text is a grammar constant, so the field records the position only.
                return lines, _Value("span_child.clone()")
            return lines, _Value(f"{_RUNTIME}::text(span_child, {context})", fallible=True)
        lines = self.child_pattern_lines(
            rule_name, label, self.child_variant(rule_name, self.element_rule(element)), child, "child_node"
        )
        return lines, self.convert_call(element, "child_node")

    def convert_call(self, element: am.ElementType, node: str) -> _Value:
        """The expression converting one CST node into the element a field holds."""
        if isinstance(element, am.CustomType):
            cst_type = f"{_SHARED_TYPE}<{self.cst_node_type(element.rule_name)}>"
            # Named through the trait rather than by method call: the user's type may carry an
            # inherent `from_cst` of its own, and this is the one the sidecar asked for.
            call = f"<{self.custom_path(element)} as {_RUNTIME}::FromCst<{cst_type}>>::from_cst({node})"
        elif isinstance(element, am.TransparentType):
            call = f"{am.erased_converter_names(element.rule_name)[0]}({node})"
        else:
            assert isinstance(element, am.NodeType)
            call = f"{element.name}::from_cst({node})"
        return _Value(call, fallible=True)

    def field_value(self, owner: str | None, rule_name: str, field: am.Field) -> tuple[list[str], _Value]:
        """Statements to run first, and the expression for one field's whole value.

        The children carrying the field's label are already bucketed by the body's own prelude
        (:meth:`bucket_lines`), so no statement here walks the child list.
        """
        label = field.label
        bucket = self.bucket_name(label)
        context = f'&{bucket}, "{rule_name}", "{label}", cst_node.span()'
        lines: list[str] = []
        field_type = field.type

        if field_type.element == am.BOOL:
            return lines, _Value(f"{_RUNTIME}::presence({context})", fallible=True)

        pre, value = self.element_code(rule_name, label, field_type.element, "child")
        held = self.boxed(value, owner, field_type.element)
        if field_type.container is am.Container.SINGLE:
            lines.append(f"let child = {_RUNTIME}::one({context})?;")
            lines.extend(pre)
            return lines, held
        if field_type.container is am.Container.OPTIONAL:
            lines.append("let mut value = None;")
            lines.append(f"if let Some(child) = {_RUNTIME}::optional({context})? {{")
            lines.extend(_indent(pre, 4))
            lines.append(f"    value = Some({held.expression});")
            lines.append("}")
            return lines, _Value("value")
        if field_type.container is am.Container.COLLECTION:
            lines.append(f"let mut values = Vec::with_capacity({bucket}.len());")
            lines.append(f"for child in &{bucket} {{")
            lines.extend(_indent(pre, 4))
            lines.append(f"    values.push({value.expression});")
            lines.append("}")
            return lines, _Value("values")
        return lines + self.map_lines(pre, value, field_type, bucket), _Value("keyed")

    def map_lines(self, pre: Sequence[str], value: _Value, field_type: am.FieldType, bucket: str) -> list[str]:
        """Statements building a keyed collection, rejecting a key two elements share.

        The key is read off each element's own field, which is the authoritative one; the map's
        keys are a lookup convenience.
        """
        key = field_type.key
        assert key is not None
        read = f"element.{self.member_name(key.field_name)}"
        # A text key is owned by the element, so the map takes a clone; an integer one is `Copy`.
        owned = self.element_type(key.element) == _SCALAR_TYPES[am.ScalarKind.TEXT]
        # Spelled out rather than inferred: the duplicate-key arm reads a member off a value the
        # map holds, which it cannot do before the map's own type is known.
        annotation = f"{_INDEX_MAP_TYPE}<{self.element_type(key.element)}, {self.element_type(field_type.element)}>"
        lines = [f"let mut keyed: {annotation} = {_INDEX_MAP_TYPE}::new();", f"for child in &{bucket} {{"]
        lines.extend(_indent(pre, 4))
        lines.append(f"    let element = {value.expression};")
        lines.append(f"    let key = {read}.clone();" if owned else f"    let key = {read};")
        lines.append("    if let Some(previous) = keyed.get(&key) {")
        lines.append(
            f'        return Err({_RUNTIME}::duplicate_key("{key.rule_name}", &key, &element.span, &previous.span));'
        )
        lines.append("    }")
        lines.append("    keyed.insert(key, element);")
        lines.append("}")
        return lines

    @staticmethod
    def hoist_variable(label: str) -> str:
        """The local holding one flattened wrapper's fields, as the tuple its helper returned."""
        return f"hoisted_{label}"

    def hoist_lines(self, owner: str | None, rule_name: str, hoist: am.Hoist) -> list[str]:
        """Statements reading a ``flatten;`` wrapper's child and binding the fields it carries.

        The wrapper's helper hands back its own field types; at an optional use site the fields
        were degraded, so a required one arrives as ``Some``, and an absent wrapper leaves every
        one of them at the value that says "not there".
        """
        if not hoist.fields:
            # A wrapper carrying no fields records nothing, so there is nothing to read back.
            return []
        wrapper = self.model.nodes[hoist.rule_name]
        assert isinstance(wrapper, am.ProductNode)
        # Positional locals: the wrapper's own field names are the grammar's, and this tuple is
        # read back by position anyway.
        raw = [f"v{index}" for index in range(len(hoist.fields))]
        variable = self.hoist_variable(hoist.label)
        call = am.flat_converter_names(hoist.rule_name)[0]
        bucket = self.bucket_name(hoist.label)
        context = f'&{bucket}, "{rule_name}", "{hoist.label}", cst_node.span()'
        destructure = self.child_pattern_lines(
            rule_name, hoist.label, self.child_variant(rule_name, hoist.rule_name), "child", "child_node"
        )
        promoted = _tuple_text(
            [
                self.hoisted_value(owner, parent, own, name)
                for parent, own, name in zip(hoist.fields, wrapper.fields, raw, strict=True)
            ]
        )
        if not hoist.optional:
            return _binding(
                variable,
                [
                    f"let child = {_RUNTIME}::one({context})?;",
                    *destructure,
                    f"let {_tuple_text(raw)} = {call}(child_node)?;",
                    promoted,
                ],
            )
        arm = [*destructure, f"let {_tuple_text(raw)} = {call}(child_node)?;", promoted]
        absent = _tuple_text([self.absent_default(field.type) for field in hoist.fields])
        return _binding(
            variable,
            [
                f"match {_RUNTIME}::optional({context})? {{",
                "    Some(child) => {",
                *_indent(arm, 8),
                "    }",
                f"    None => {absent},",
                "}",
            ],
        )

    def hoisted_value(self, owner: str | None, parent: am.Field, own: am.Field, name: str) -> str:
        """One hoisted field as the containing type holds it, given the wrapper's own spelling."""
        boxed = self.is_boxed_element(owner, parent.type.element)
        degraded = own.type.container is am.Container.SINGLE and parent.type.container is am.Container.OPTIONAL
        if degraded:
            return f"Some(Box::new({name}))" if boxed else f"Some({name})"
        if not boxed:
            return name
        if parent.type.container is am.Container.OPTIONAL:
            return f"{name}.map(Box::new)"
        return f"Box::new({name})"

    @staticmethod
    def absent_default(field_type: am.FieldType) -> str:
        """What a hoisted field holds when its optional wrapper was not there."""
        if field_type.element == am.BOOL:
            return "false"
        if field_type.container is am.Container.COLLECTION:
            return "Vec::new()"
        if field_type.container is am.Container.MAP:
            return f"{_INDEX_MAP_TYPE}::new()"
        return "None"

    def emit_flat_converter(self, rule_name: str, node: am.RuleNode) -> None:
        """The forward helper of a ``flatten;`` wrapper, which has no type to hang one on."""
        assert isinstance(node, am.ProductNode)
        if not node.fields:
            return
        result = _tuple_text([self.field_type(None, field) for field in node.fields])
        self.separate()
        self.emit(
            f"/// Convert a `{rule_name}` CST node to the fields it is flattened into.",
            f"fn {am.flat_converter_names(rule_name)[0]}(node: &{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>)"
            f" -> Result<{result}, {_AST_ERROR}> {{",
        )
        body = ["let cst_node = node.read();"]
        body.extend(self.bucket_lines(rule_name, self.body_labels(node.fields, node.hoists)))
        for hoist in node.hoists:
            body.extend(self.hoist_lines(None, rule_name, hoist))
        positions = {
            (field.hoist, field.name): index for hoist in node.hoists for index, field in enumerate(hoist.fields)
        }
        # Positional locals, as in a hoist: what leaves here is read back by position.
        values: list[str] = []
        for index, field in enumerate(node.fields):
            values.append(f"v{index}")
            if field.hoist is not None:
                body.append(f"let v{index} = {self.hoist_variable(field.hoist)}.{positions[field.hoist, field.name]};")
                continue
            lines, value = self.field_value(None, rule_name, field)
            body.extend(
                _binding(f"v{index}", [*lines, value.expression]) if lines else [f"let v{index} = {value.expression};"]
            )
        body.append(f"Ok({_tuple_text(values)})")
        self.emit(*_indent(body, 4))
        self.emit("}")

    def emit_erased_converter(self, rule_name: str, node: am.RuleNode) -> None:
        """The forward helper of a ``transparent;`` rule, which emits no type of its own."""
        payload = self.element_type(self.model.transparent_types[rule_name])
        self.separate()
        self.emit(
            f"/// Convert a `{rule_name}` CST node to the payload its type erases to.",
            f"fn {am.erased_converter_names(rule_name)[0]}(node: &{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>)"
            f" -> Result<{payload}, {_AST_ERROR}> {{",
        )
        self.emit(*_indent(self.erased_body(rule_name, node), 4))
        self.emit("}")

    def erased_body(self, rule_name: str, node: am.RuleNode) -> list[str]:
        if isinstance(node, am.TerminalNode):
            lines, _member, value = self.terminal_value(rule_name, node)
            return ["let cst_node = node.read();", *lines, value.result]
        if isinstance(node, am.EnumNode):
            return [
                "let cst_node = node.read();",
                *self.enum_lines(rule_name, node, lambda value: f"return Ok({value});"),
            ]
        assert isinstance(node, am.ProductNode)
        (field,) = node.fields
        lines, value = self.field_value(None, rule_name, field)
        return [
            "let cst_node = node.read();",
            *self.bucket_lines(rule_name, [field.label]),
            *lines,
            value.result,
        ]

    def terminal_value(self, rule_name: str, node: am.TerminalNode) -> tuple[list[str], str, _Value]:
        """Statements to run first, the member a terminal-only rule carries, and its value."""
        lines: list[str] = []
        if node.text_from is None:
            text = _Value(f'{_RUNTIME}::node_text(cst_node.span(), "{rule_name}")', fallible=True)
        else:
            label = node.text_from
            bucket = self.bucket_name(label)
            lines.extend(self.bucket_lines(rule_name, [label]))
            lines.append(f'let child = {_RUNTIME}::one(&{bucket}, "{rule_name}", "{label}", cst_node.span())?;')
            lines.extend(
                self.child_pattern_lines(
                    rule_name, label, self.child_variant(rule_name, gshape.TEXT_KIND), "child", "span_child"
                )
            )
            text = _Value(f'{_RUNTIME}::text(span_child, "{rule_name}", "{label}", cst_node.span())', fallible=True)
        if node.coercion is None:
            return lines, "text", text
        lines.append(f"let text = {text.expression};")
        return lines, "value", self.parse_expression(rule_name, node.coercion)

    def parse_expression(self, rule_name: str, coercion: am.Coercion) -> _Value:
        """The expression coercing a terminal's text to the value its ``type:`` names."""
        context = f'"{rule_name}", cst_node.span()'
        if isinstance(coercion, am.CustomCoercion):
            parse = _rust_path(coercion.rust_parse, coercion.rule_name, "type: custom(...)", "rust_parse")
            return _Value(f"{_RUNTIME}::scalar::parse_custom({parse}, &text, {context})", fallible=True)
        return _Value(f"{_RUNTIME}::scalar::parse_{coercion.name}(&text, {context})", fallible=True)

    def terminal_body(self, rule_name: str, node: am.TerminalNode) -> list[str]:
        lines, member, value = self.terminal_value(rule_name, node)
        tail = [
            *_member_lines(member, [value.expression]),
            "span: cst_node.span().clone(),",
            *self.backpointer_argument(),
        ]
        return ["let cst_node = node.read();", *lines, "Ok(Self {", *_indent(tail, 4), "})"]

    def enum_value(self, node: am.EnumNode, variant: am.ValueVariant) -> str:
        """The value one alternative of an enum-shaped rule maps to."""
        if node.bool_truthy is not None:
            return "true" if variant.label == node.bool_truthy else "false"
        return f"{node.value_enum.name}::{variant.name}"

    def enum_lines(self, rule_name: str, node: am.EnumNode, result: Callable[[str], str]) -> list[str]:
        """Statements picking the value from whichever alternative label the node carries.

        The label decides, never the literal's text: alternatives of one rule sharing a label
        declare their spellings equivalent, and the parser records no more than the label.
        """
        lines: list[str] = []
        for variant in node.value_enum.variants:
            present = (
                "cst_node.children().iter()"
                f".any(|(label, _)| matches!(label, Some({self.label_variant(rule_name, variant.label)})))"
            )
            lines.extend((f"if {present} {{", f"    {result(self.enum_value(node, variant))}", "}"))
        message = _message(f'rule "{rule_name}": no alternative label is present')
        lines.append(f"Err({_AST_ERROR}::new({message}, cst_node.span().clone()))")
        return lines

    def enum_body(self, rule_name: str, node: am.EnumNode) -> list[str]:
        tail = ["span: cst_node.span().clone()", *(member.rstrip(",") for member in self.backpointer_argument())]

        def result(value: str) -> str:
            members = ", ".join([f"value: {value}", *tail])
            return f"return Ok(Self {{ {members} }});"

        return ["let cst_node = node.read();", *self.enum_lines(rule_name, node, result)]

    # --- Fold chains ---------------------------------------------------------------------

    def emit_fold_converter(self, rule_name: str, node: am.FoldNode) -> None:
        """The converter of a fold rule, whose CST holds the chain flattened."""
        self.emit_from_cst(
            node.name,
            rule_name,
            self.fold_body(rule_name, node),
            doc=f"Convert a `{rule_name}` CST node, folding its operands into a chain.",
        )

    def fold_body(self, rule_name: str, node: am.FoldNode) -> list[str]:
        """Bucket the operands and operators, convert each, and hand both runs to the fold.

        The nesting order, the merged spans and the arity diagnostic all live in the runtime, so
        what is emitted here is the two conversions plus the two closures that name generated
        types — the only part of a fold the runtime cannot spell.
        """
        operand_bucket = self.bucket_name(node.operand.label)
        operator_bucket = self.bucket_name(node.operators.label)
        direction = "fold_left" if node.direction is ac.FoldDirection.LEFT else "fold_right"
        lines = ["let cst_node = node.read();"]
        lines.extend(self.bucket_lines(rule_name, [node.operand.label, node.operators.label]))
        lines.append(
            f"{_RUNTIME}::check_fold_arity("
            f'{operand_bucket}.len(), {operator_bucket}.len(), "{rule_name}", cst_node.span())?;'
        )
        lines.extend(self.fold_operand_lines(rule_name, node))
        lines.extend(self.fold_operator_lines(rule_name, node))
        lines.extend(
            (
                f"{_RUNTIME}::{direction}(",
                f'    "{rule_name}",',
                "    cst_node.span(),",
                "    operands,",
                "    operators,",
                *_indent(self.fold_operand_closure(node), 4),
                *_indent(self.fold_link_closure(node), 4),
                ")",
            )
        )
        return lines

    def fold_operand_lines(self, rule_name: str, node: am.FoldNode) -> list[str]:
        """Statements converting the operands, each with its own span, in source order.

        A link's span is merged out of the operand spans, and those are read off the CST children
        rather than off the converted values: an erased operand — a plain ``i64`` — carries none.
        """
        label = node.operand.label
        element = node.operand.type.element
        statements, value = self.element_code(rule_name, label, element, "child")
        bucket = self.bucket_name(label)
        return [
            f"let mut operands = Vec::with_capacity({bucket}.len());",
            f"for child in &{bucket} {{",
            *_indent(statements, 4),
            f"    let operand_span = {self.child_span(element)};",
            f"    operands.push(({value.expression}, operand_span));",
            "}",
        ]

    def fold_operator_lines(self, rule_name: str, node: am.FoldNode) -> list[str]:
        """Statements converting the operators, in source order: one sits between each pair."""
        label = node.operators.label
        element = node.operators.type.element
        statements, value = self.element_code(rule_name, label, element, "child")
        held = self.boxed(value, node.binary.name, element)
        bucket = self.bucket_name(label)
        return [
            f"let mut operators = Vec::with_capacity({bucket}.len());",
            f"for child in &{bucket} {{",
            *_indent(statements, 4),
            f"    operators.push({held.expression});",
            "}",
        ]

    def child_span(self, element: am.ElementType) -> str:
        """One child's own span, read off whichever binding :meth:`element_code` made for it."""
        assert not (isinstance(element, am.NodeType) and element.name in self.model.field_enums), (
            "a fold operand carrying more than one type has no single item position to render "
            "through, which the model refuses before this runs"
        )
        if isinstance(element, am.ScalarType):
            return "span_child.clone()"
        return "child_node.read().span().clone()"

    def fold_operand_closure(self, node: am.FoldNode) -> list[str]:
        """How one operand becomes a value of the fold rule's own type.

        Where the variant holds the operand directly the constructor is passed as the function it
        already is: wrapping it in a closure that only calls it is a `clippy::redundant_closure`,
        which `-D warnings` turns into a build failure in a consumer's crate.
        """
        payload = self.boxed(_Value("operand"), node.name, node.operand.type.element)
        if payload.code == "operand":
            return [f"Self::{node.operand_variant},"]
        return [f"|operand| Self::{node.operand_variant}({payload.expression}),"]

    def fold_link_closure(self, node: am.FoldNode) -> list[str]:
        """How one operator and two sub-chains become a link of the chain."""
        member = self.member_name(node.binary.op.name)
        # Shorthand where the member is already spelled `operator`: naming it twice is a lint.
        operator = "operator," if member == "operator" else f"{member}: operator,"
        members = [
            operator,
            f"{am.FOLD_LHS}: Box::new(lhs),",
            f"{am.FOLD_RHS}: Box::new(rhs),",
            "span,",
            # A synthesized link stands for no CST node of its own.
            *(["cst: None,"] if self.model.cst_backpointers else []),
        ]
        boxed = self.is_boxed_element(node.name, am.NodeType(node.binary.name))
        held = f"Box::new({node.binary.name} {{" if boxed else f"{node.binary.name} {{"
        return [
            "|operator, lhs, rhs, span| {",
            f"    Self::{node.binary_variant}({held}",
            *_indent(members, 8),
            "    }))" if boxed else "    })",
            "},",
        ]

    # --- Sum dispatch --------------------------------------------------------------------

    @staticmethod
    def dispatch_name(rule_name: str) -> str:
        """The private function recovering which alternative of a sum rule matched."""
        return am.alternative_dispatch_name(rule_name)

    def emit_sum_converters(self, rule_name: str, node: am.SumNode) -> None:
        """The payload converters of a sum rule, its dispatch function, and its own converter."""
        for variant in node.variants:
            payload = am.generated_payload(self.model, variant)
            if payload is not None:
                self.emit_from_cst(
                    payload.name,
                    rule_name,
                    self.product_body(payload.name, rule_name, payload.fields, payload.hoists),
                    doc=f"Convert the `{variant.name}` alternative of a `{rule_name}` CST node.",
                )
        self.emit_dispatch(rule_name, node)
        body = [
            "let (alternative, span) = {",
            "    let cst_node = node.read();",
            f"    ({self.dispatch_name(rule_name)}(&cst_node), cst_node.span().clone())",
            "};",
            "match alternative {",
        ]
        for index, variant in enumerate(node.variants):
            lines = self.variant_lines(rule_name, node, variant)
            if len(lines) == 1:
                body.append(f"    Some({index}) => {lines[0]},")
            else:
                body.extend((f"    Some({index}) => {{", *_indent(lines, 8), "    }"))
        message = _message(f'rule "{rule_name}": no alternative matches the node\'s labeled children')
        body.extend((f"    _ => Err({_AST_ERROR}::new({message}, span)),", "}"))
        self.emit_from_cst(
            node.name, rule_name, body, doc=f"Convert a `{rule_name}` CST node, dispatching on the matched alternative."
        )

    def variant_lines(self, rule_name: str, node: am.SumNode, variant: am.SumVariant) -> list[str]:
        """The body converting one matched alternative into its variant."""
        payload = am.generated_payload(self.model, variant)
        if payload is not None:
            converted = _Value(f"{payload.name}::from_cst(node)", fallible=True)
            held = self.boxed(converted, node.name, variant.payload)
            return [f"Ok(Self::{variant.name}({held.expression}))"]
        label = next(iter(variant.signature.labels))
        bucket = self.bucket_name(label)
        lines = ["let cst_node = node.read();", *self.bucket_lines(rule_name, [label])]
        lines.append(f'let child = {_RUNTIME}::one(&{bucket}, "{rule_name}", "{label}", cst_node.span())?;')
        pre, value = self.element_code(rule_name, label, variant.payload, "child")
        lines.extend(pre)
        held = self.boxed(value, node.name, variant.payload)
        lines.append(f"Ok(Self::{variant.name}({held.expression}))")
        return lines

    def emit_dispatch(self, rule_name: str, node: am.SumNode) -> None:
        """The function counting a node's labeled children and naming the alternative they fit."""
        dispatch = am.sum_dispatch(node)
        self.separate()
        self.emit(
            f"/// Which alternative of rule `{rule_name}` the node's labeled children came from.",
            "///",
            "/// The CST does not record it, so the children are counted per label and kind and the",
            "/// first alternative whose signature accepts those counts wins.",
            f"fn {self.dispatch_name(rule_name)}(node: &{self.cst_node_type(rule_name)}) -> Option<usize> {{",
        )
        self.emit(*_indent(self.dispatch_body(rule_name, dispatch), 4))
        self.emit("}")

    def dispatch_body(self, rule_name: str, dispatch: am.SumDispatch) -> list[str]:
        # A rule whose nodes hold one kind of child needs no kind test anywhere in the loop
        # (:meth:`count_lines`), so no clause reads the child and binding it by name would be an
        # unused variable -- a warning, and a hard build failure under `-D warnings`.
        child = "child" if self.child_variant_count(rule_name) > 1 else "_child"
        lines = [f"let mut counts = [0usize; {len(dispatch.pairs)}];", f"for (label, {child}) in node.children() {{"]
        lines.extend(_indent(self.count_lines(rule_name, dispatch), 4))
        lines.append("}")
        for alternative in dispatch.alternatives:
            conditions = self.dispatch_conditions(alternative)
            accept = [f"return Some({alternative.variant_index});"]
            if not conditions:
                # Unreachable for a rule classified as a sum: an alternative that constrains no
                # count accepts every label freely and forbids none, so no label can tell it apart
                # from a sibling and the rule is a merged product instead. The guard stands so an
                # emitter change that made it reachable would not emit `if  {`.
                lines.extend(accept)
                return lines
            lines.extend(_if_block(conditions, accept, 0))
        lines.append("None")
        return lines

    def count_lines(self, rule_name: str, dispatch: am.SumDispatch) -> list[str]:
        """Statements counting one child into the (label, kind) pair it occupies."""
        clauses: list[tuple[str, Sequence[str]]] = []
        for label in dict.fromkeys(pair.label for pair in dispatch.pairs):
            own = [(index, pair) for index, pair in enumerate(dispatch.pairs) if pair.label == label]
            if len(own) == 1 and self.child_variant_count(rule_name) == 1:
                body: list[str] = [f"counts[{own[0][0]}] += 1;"]
            else:
                kinds = [
                    (f"matches!(child, {self.child_variant(rule_name, pair.kind)}(_))", [f"counts[{index}] += 1;"])
                    for index, pair in own
                ]
                body = _if_chain(kinds, ["return None;"])
            clauses.append((f"matches!(label, Some({self.label_variant(rule_name, label)}))", body))
        # A label no alternative carries tells us nothing fits; an unlabeled child is not ours.
        clauses.append(("label.is_some()", ["return None;"]))
        return _if_chain(clauses)

    @staticmethod
    def dispatch_conditions(alternative: am.AltDispatch) -> list[str]:
        """What one alternative requires of the counts, as Rust comparisons."""
        conditions: list[str] = []
        for bound in alternative.bounds:
            counted = " + ".join(f"counts[{index}]" for index in bound.pairs) or "0"
            if bound.minimum == bound.maximum:
                conditions.append(f"{counted} == {bound.minimum}")
            elif bound.maximum == math.inf:
                conditions.append(f"{counted} >= {bound.minimum}")
            else:
                # `LabelCount` saturates both bounds at two, so a bound's maximum is 0, 1 or
                # infinity: a finite maximum above the minimum is one over a minimum of zero.
                assert bound.minimum == 0, bound
                conditions.append(f"{counted} <= {int(bound.maximum)}")
        conditions.extend(f"counts[{index}] == 0" for index in alternative.forbidden)
        return conditions

    def emit_field_enum_converter(self, field_enum: am.FieldEnum) -> None:
        """The converter of a label carrying more than one type, dispatching on the child's kind."""
        rule_name = field_enum.rule_name
        label = field_enum.label
        arms: list[str] = []
        # The span is the owner's, reported where a child carries no text or no variant at all;
        # a label whose types are all nodes and cover every kind of child never needs it.
        reads_span = len(field_enum.variants) < self.child_variant_count(rule_name)
        for variant in field_enum.variants:
            element = variant.element
            if isinstance(element, am.ScalarType):
                pattern = f"{self.child_variant(rule_name, gshape.TEXT_KIND)}(span_child)"
                value = _Value(f'{_RUNTIME}::text(span_child, "{rule_name}", "{label}", span)', fallible=True)
                reads_span = True
            else:
                pattern = f"{self.child_variant(rule_name, self.element_rule(element))}(child_node)"
                value = self.convert_call(element, "child_node")
            payload = self.boxed(value, field_enum.name, element)
            arms.append(f"        {pattern} => Ok({field_enum.name}::{variant.name}({payload.expression})),")
        if len(field_enum.variants) < self.child_variant_count(rule_name):
            arms.append(f'        _ => Err({_RUNTIME}::unexpected_child("{rule_name}", "{label}", span)),')
        parameter = "span" if reads_span else "_span"
        self.separate()
        self.emit(
            f"/// Convert an `{label}` child of rule `{rule_name}`, whichever of its types it carries.",
            f"fn {am.field_enum_converter_name(field_enum.name)}"
            f"(child: &{self.child_enum_type(rule_name)}, {parameter}: &{_SPAN_TYPE})"
            f" -> Result<{field_enum.name}, {_AST_ERROR}> {{",
            "    match child {",
        )
        self.emit(*arms, "    }", "}")

    # --- Converters: AST -> CST ----------------------------------------------------------

    def emit_reverse_converters(self) -> None:
        """The serialize direction: one converter per rule, plus the private helper halves.

        A terminal-only rule carries the text its children were read from and an enum-shaped one
        carries which alternative matched, so both synthesise their node out of their own value.
        Every other form hands its field values to the item positions that can carry them.
        """
        for rule_name, node in self.model.nodes.items():
            if isinstance(node, am.TerminalNode):
                self.emit_terminal_shape(rule_name)
            if rule_name in self.model.flattened_rules:
                self.emit_flat_reverse(rule_name, node)
            elif rule_name in self.model.transparent_types:
                self.emit_erased_reverse(rule_name, node)
            elif isinstance(node, am.TerminalNode):
                member = "text" if node.coercion is None else "value"
                self.emit_to_cst(
                    node.name,
                    rule_name,
                    self.terminal_to_cst_body(rule_name, node, self.member_held(node)),
                    doc=f"Synthesise a `{rule_name}` CST node from the text of `{member}`.",
                )
            elif isinstance(node, am.EnumNode):
                self.emit_to_cst(
                    node.name,
                    rule_name,
                    self.enum_to_cst_body(rule_name, node, self.member_held(node)),
                    doc=f"Synthesise a `{rule_name}` CST node for the alternative `value` names.",
                )
            elif isinstance(node, am.ProductNode):
                self.emit_product_reverse(
                    rule_name,
                    node.name,
                    node.fields,
                    node.hoists,
                    doc=f"Synthesise a `{rule_name}` CST node from this value's fields.",
                )
            elif isinstance(node, am.SumNode):
                self.emit_sum_reverse(rule_name, node)
            else:
                self.emit_fold_reverse(rule_name, node)

    def emit_to_cst(self, type_name: str, rule_name: str, body: Sequence[str], doc: str) -> None:
        """``to_cst`` on one generated type, over the CST node of ``rule_name``."""
        self.separate()
        self.emit(
            f"impl {type_name} {{",
            f"    /// {doc}",
            f"    pub fn to_cst(&self) -> Result<{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>, {_AST_ERROR}> {{",
        )
        self.emit(*_indent(self.with_terminals(body), 8))
        self.emit("    }", "}")

    def emit_reverse_function(self, name: str, parameters: str, rule_name: str, body: Sequence[str], doc: str) -> None:
        """One private reverse helper: an erased rule's, a flattened wrapper's, or one alternative's."""
        self.separate()
        self.emit(
            f"/// {doc}",
            f"fn {name}({parameters}) -> Result<{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>, {_AST_ERROR}> {{",
        )
        self.emit(*_indent(self.with_terminals(body), 4))
        self.emit("}")

    def with_terminals(self, body: Sequence[str]) -> list[str]:
        """One body, with the terminals its text positions validate against declared above it.

        The declarations are ``static`` items inside the function: they compile on first use, and
        being function-scoped they need no module-level name that could collide with a rule's.
        """
        declarations = [
            f"static {name}: {_RUNTIME}::LazyTerminal = {_RUNTIME}::LazyTerminal::new({_string(pattern)});"
            for pattern, name in self.terminals.items()
        ]
        self.terminals = {}
        return [*declarations, *body]

    def terminal_reference(self, pattern: str) -> str:
        """The compiled terminal one text position validates against, declared on first ask."""
        name = self.terminals.setdefault(pattern, f"{_TERMINAL_PREFIX}{len(self.terminals)}")
        return f"{name}.get()"

    # --- Where a reverse converter reads its values --------------------------------------

    def member_held(self, node: am.TerminalNode | am.EnumNode) -> _Held:
        """The value a terminal-only or enum-shaped node's own ``to_cst`` renders."""
        member = "value" if isinstance(node, am.EnumNode) or node.coercion is not None else "text"
        return _Held(
            place=f"self.{member}",
            reference=f"&self.{member}",
            copied=f"self.{member}",
            text=f"self.{member}.as_str()",
            span="&self.span",
        )

    @staticmethod
    def parameter_held() -> _Held:
        """The value an erased rule's reverse helper renders, which is its payload by reference."""
        return _Held(place="value", reference="value", copied="*value", text="value", span=f"&{_SPAN_TYPE}::unknown()")

    @staticmethod
    def cursor_name(label: str) -> str:
        """The local holding the values one label's item positions draw from."""
        return f"cursor_{label}"

    def member_places(self, owner: str) -> _Values:
        """Where a node's own ``to_cst`` reads each field: off the members of ``self``."""

        def place(field: am.Field) -> _Place:
            member = f"self.{self.member_name(field.name)}"
            # An optional member is handed on as `Option<&T>` over the value itself, so a member
            # holding it through a `Box` — or as a `String` where the helper takes a `&str` — is
            # dereferenced on the way rather than borrowed as it stands.
            element = self.element_type(field.type.element)
            indirect = self.is_boxed_element(owner, field.type.element) or element in _BORROWED_TYPES
            unwrap = "as_deref" if indirect else "as_ref"
            return _Place(
                cursor=self.cursor_values(field, member, reference=f"&{member}", truth=member, owned=True),
                populated=self.populated_test(field, member, truth=member),
                reference=f"&{member}",
                optional=f"{member}.{unwrap}()",
                value=member,
                container=f"&{member}",
            )

        return place

    def parameter_places(self, names: Mapping[str, str]) -> _Values:
        """Where a private helper reads each field: off the parameters it was handed.

        A helper takes each field by reference — an optional one as ``Option<&T>``, a presence flag
        by value — so what it passes on to a wrapper nested inside it needs no adjusting.
        """

        def place(field: am.Field) -> _Place:
            name = names[field.name]
            return _Place(
                cursor=self.cursor_values(field, name, reference=name, truth=name, owned=False),
                populated=self.populated_test(field, name, truth=name),
                reference=name,
                optional=name,
                value=name,
                container=name,
            )

        return place

    @staticmethod
    def cursor_values(field: am.Field, receiver: str, *, reference: str, truth: str, owned: bool) -> str:
        """The values one field's item positions draw from, in the order the field holds them.

        ``owned`` says the field is a member holding its values; a helper's parameter has them by
        reference already, so an optional one is iterated rather than borrowed again.
        """
        if field.type.element == am.BOOL:
            # A presence flag is one occurrence of the literal where it is set, and none otherwise.
            return f"if {truth} {{ vec![{reference}] }} else {{ Vec::new() }}"
        if field.type.container is am.Container.SINGLE:
            return f"vec![{reference}]"
        if field.type.container is am.Container.MAP:
            # Insertion order.  Each element carries its own key field, which is the authoritative
            # one, so the map's keys are never read back.
            return f"{receiver}.values().collect()"
        if field.type.container is am.Container.OPTIONAL and not owned:
            return f"{receiver}.into_iter().collect()"
        return f"{receiver}.iter().collect()"

    @staticmethod
    def populated_test(field: am.Field, receiver: str, *, truth: str) -> str:
        """Whether a field carries something, for alternative and branch selection."""
        if am.populated_directly(field):
            return truth
        if field.type.container is am.Container.OPTIONAL:
            return f"{receiver}.is_some()"
        if field.type.container in (am.Container.COLLECTION, am.Container.MAP):
            return f"!{receiver}.is_empty()"
        return "true"

    def parameter_type(self, field: am.Field) -> str:
        """The type a private helper takes one field as: by reference, and never boxed.

        Boxing is the answer for the type that *owns* a field; a helper's caller is whichever type
        references the rule, and a reference reaches the value through whatever indirection that
        type chose.
        """
        if field.type.element == am.BOOL:
            return "bool"
        element = self.element_type(field.type.element)
        container = field.type.container
        if container is am.Container.COLLECTION:
            return f"&[{element}]"
        if container is am.Container.MAP:
            assert field.type.key is not None
            return f"&{_INDEX_MAP_TYPE}<{self.element_type(field.type.key.element)}, {element}>"
        borrowed = _BORROWED_TYPES.get(element, element)
        if container is am.Container.OPTIONAL:
            return f"Option<&{borrowed}>"
        return f"&{borrowed}"

    # --- One node form at a time ---------------------------------------------------------

    def emit_product_reverse(
        self,
        rule_name: str,
        type_name: str,
        fields: Sequence[am.Field],
        hoists: Sequence[am.Hoist] = (),
        *,
        doc: str,
        plans: Sequence[am.AltPlan] | None = None,
    ) -> None:
        """``to_cst`` on a product or a sum's payload class, over its alternative or a trial of them."""
        if plans is None:
            plans = self.model.plans[rule_name].alternatives
        body = _Body(rule_name=rule_name, owner=type_name, values=self.member_places(type_name))
        if len(plans) == 1:
            self.emit_to_cst(type_name, rule_name, self.alternative_lines(body, fields, plans[0], hoists), doc)
            return
        trial = self.trial_lines(body, fields, plans, hoists, lambda index: f"self.{_ALT_METHOD}{index}()")
        self.emit_to_cst(type_name, rule_name, trial, doc)
        self.separate()
        self.emit(f"impl {type_name} {{")
        for plan in plans:
            self.emit(
                f"    /// Synthesise alternative {plan.index} of rule `{rule_name}`.",
                f"    fn {_ALT_METHOD}{plan.index}(&self)"
                f" -> Result<{_SHARED_TYPE}<{self.cst_node_type(rule_name)}>, {_AST_ERROR}> {{",
            )
            self.emit(*_indent(self.with_terminals(self.alternative_lines(body, fields, plan, hoists)), 8))
            self.emit("    }")
        self.emit("}")

    def emit_sum_reverse(self, rule_name: str, node: am.SumNode) -> None:
        """The payload classes' own ``to_cst``, then the sum's, which matches on the variant.

        No trial and no type test: the variant a value holds *is* the alternative the grammar
        spells, which is what the payload uniqueness condition on direct payloads buys.
        """
        plans = self.model.plans[rule_name].alternatives
        for variant in node.variants:
            payload = am.generated_payload(self.model, variant)
            if payload is not None:
                self.emit_product_reverse(
                    rule_name,
                    payload.name,
                    payload.fields,
                    payload.hoists,
                    doc=f"Synthesise the `{variant.name}` alternative of rule `{rule_name}`.",
                    plans=(plans[payload.alternative_index],),
                )
        lines = ["match self {"]
        for variant in node.variants:
            payload = am.generated_payload(self.model, variant)
            if payload is not None:
                lines.append(f"    Self::{variant.name}({_PAYLOAD}) => {_PAYLOAD}.to_cst(),")
                continue
            body = self.direct_variant_lines(rule_name, variant, plans[variant.alternative_index])
            lines.extend((f"    Self::{variant.name}({_PAYLOAD}) => {{", *_indent(body, 8), "    }"))
        lines.append("}")
        self.emit_to_cst(
            node.name,
            rule_name,
            lines,
            doc=f"Synthesise a `{rule_name}` CST node for whichever alternative this value is.",
        )

    def direct_variant_lines(self, rule_name: str, variant: am.SumVariant, plan: am.AltPlan) -> list[str]:
        """The body of a variant whose payload is the referenced rule's own AST type."""
        slot = next(slot for slot in plan.slots if slot.kind is am.SlotKind.NODE)
        child = f"{self.child_variant(rule_name, slot.rule_name or '')}({self.reverse_call(variant.payload, _PAYLOAD)})"
        return [
            f"let mut cst_node = {self.cst_node_type(rule_name)}::new({_SPAN_TYPE}::unknown());",
            *self.push_lines(self.child_label(rule_name, slot.label or ""), child),
            "Ok(cst_node.into())",
        ]

    def emit_fold_reverse(self, rule_name: str, node: am.FoldNode) -> None:
        """``to_cst`` on a fold rule: unfold the chain back into the alternating item run.

        The items interleave, which the flat pass over item positions cannot produce, so the walk
        is written out here: the operands and operators come off the chain in source order and go
        straight into the node.
        """
        plan = self.model.plans[rule_name].alternatives[0]
        operand_slot = next(slot for slot in plan.slots if slot.label == node.operand.label)
        operator_slot = next(slot for slot in plan.slots if slot.label == node.operators.label)
        body = _Body(rule_name=rule_name, owner=node.name, values=self.member_places(node.name))
        lines = self.unfold_lines(rule_name, node)
        lines.append(f"let mut cst_node = {self.cst_node_type(rule_name)}::new({_SPAN_TYPE}::unknown());")
        lines.extend(self.child_lines(body, node.operand, operand_slot, f"{_OPERANDS}[0]"))
        lines.append(
            f"for ({_OPERATOR}, {_OPERAND}) in {_OPERATORS}.into_iter().zip({_OPERANDS}.into_iter().skip(1)) {{"
        )
        lines.extend(_indent(self.child_lines(body, node.operators, operator_slot, _OPERATOR), 4))
        lines.extend(_indent(self.child_lines(body, node.operand, operand_slot, _OPERAND), 4))
        lines.extend(("}", "Ok(cst_node.into())"))
        self.emit_to_cst(
            node.name,
            rule_name,
            lines,
            doc=f"Synthesise a `{rule_name}` CST node by unfolding this chain.",
        )

    def unfold_lines(self, rule_name: str, node: am.FoldNode) -> list[str]:
        """Statements splitting a chain back into its operands and its operators, in source order.

        The chain nests one way, so the walk descends that side and every operand it passes must be
        a bare one: a chain on the other side of a link is a value the grammar has no shape for.
        """
        left = node.direction is ac.FoldDirection.LEFT
        deeper, operand_side = (am.FOLD_LHS, am.FOLD_RHS) if left else (am.FOLD_RHS, am.FOLD_LHS)
        side = "right" if left else "left"
        lines = [
            f"let mut {_OPERANDS} = Vec::new();",
            f"let mut {_OPERATORS} = Vec::new();",
            "let mut chain = self;",
            "loop {",
            "    match chain {",
            f"        Self::{node.operand_variant}({_OPERAND}) => {{",
            f"            {_OPERANDS}.push({_OPERAND});",
            "            break;",
            "        }",
            f"        Self::{node.binary_variant}(link) => {{",
            f"            {_OPERATORS}.push(&link.{self.member_name(node.binary.op.name)});",
            f"            match link.{operand_side}.as_ref() {{",
            f"                Self::{node.operand_variant}({_OPERAND}) => {_OPERANDS}.push({_OPERAND}),",
            f"                Self::{node.binary_variant}(_) => {{",
            f"                    return Err({_RUNTIME}::against_direction({_string(rule_name)}, {_string(side)}));",
            "                }",
            "            }",
            f"            chain = link.{deeper}.as_ref();",
            "        }",
            "    }",
            "}",
        ]
        if left:
            # The walk descended from the outermost link, so it saw the chain back to front.
            lines.extend((f"{_OPERANDS}.reverse();", f"{_OPERATORS}.reverse();"))
        return lines

    def emit_erased_reverse(self, rule_name: str, node: am.RuleNode) -> None:
        """The reverse helper of a ``transparent;`` rule, which takes the payload it erases to."""
        payload = self.element_type(self.model.transparent_types[rule_name])
        name = am.erased_converter_names(rule_name)[1]
        parameters = f"value: &{_BORROWED_TYPES.get(payload, payload)}"
        doc = f"Synthesise a `{rule_name}` CST node from the payload its type erases to."
        if isinstance(node, am.TerminalNode):
            lines = self.terminal_to_cst_body(rule_name, node, self.parameter_held())
        elif isinstance(node, am.EnumNode):
            lines = self.enum_to_cst_body(rule_name, node, self.parameter_held())
        else:
            assert isinstance(node, am.ProductNode)
            (field,) = node.fields
            body = _Body(rule_name=rule_name, owner=None, values=self.parameter_places({field.name: "value"}))
            plans = self.model.plans[rule_name].alternatives
            if len(plans) == 1:
                lines = self.alternative_lines(body, node.fields, plans[0])
            else:
                lines = self.trial_lines(
                    body, node.fields, plans, (), lambda index: f"{name}{_ALT_SUFFIX}{index}(value)"
                )
                for plan in plans:
                    self.emit_reverse_function(
                        f"{name}{_ALT_SUFFIX}{plan.index}",
                        parameters,
                        rule_name,
                        self.alternative_lines(body, node.fields, plan),
                        f"Synthesise alternative {plan.index} of the erased rule `{rule_name}`.",
                    )
        self.emit_reverse_function(name, parameters, rule_name, lines, doc)

    def emit_flat_reverse(self, rule_name: str, node: am.RuleNode) -> None:
        """The reverse helper of a ``flatten;`` wrapper, which rebuilds it from the hoisted fields."""
        assert isinstance(node, am.ProductNode)
        name = am.flat_converter_names(rule_name)[1]
        names = {field.name: f"{_HOISTED_PREFIX}{index}" for index, field in enumerate(node.fields)}
        parameters = ", ".join(f"{names[field.name]}: {self.parameter_type(field)}" for field in node.fields)
        body = _Body(rule_name=rule_name, owner=None, values=self.parameter_places(names))
        plans = self.model.plans[rule_name].alternatives
        doc = f"Synthesise a `{rule_name}` CST node from the fields flattened out of it."
        if len(plans) == 1:
            lines = self.alternative_lines(body, node.fields, plans[0], node.hoists)
        else:
            arguments = ", ".join(names[field.name] for field in node.fields)
            lines = self.trial_lines(
                body,
                node.fields,
                plans,
                node.hoists,
                lambda index: f"{name}{_ALT_SUFFIX}{index}({arguments})",
            )
            for plan in plans:
                self.emit_reverse_function(
                    f"{name}{_ALT_SUFFIX}{plan.index}",
                    parameters,
                    rule_name,
                    self.alternative_lines(body, node.fields, plan, node.hoists),
                    f"Synthesise alternative {plan.index} of the flattened rule `{rule_name}`.",
                )
        self.emit_reverse_function(name, parameters, rule_name, lines, doc)

    # --- One alternative -----------------------------------------------------------------

    def trial_lines(
        self,
        body: _Body,
        fields: Sequence[am.Field],
        plans: Sequence[am.AltPlan],
        hoists: Sequence[am.Hoist],
        call: Callable[[int], str],
    ) -> list[str]:
        """Statements picking the first alternative the populated fields fit, then delegating.

        A hoisted group counts as its wrapper's own label, which is the label the alternatives are
        written in terms of: the group is populated exactly when the wrapper would be built.

        Which labels are populated is half the question; a label carrying several types leaves the
        alternatives that accept different ones of them indistinguishable by name, so an
        alternative accepting fewer kinds than the field holds carries a kind test as well.
        """
        by_label = {field.label: field for field in fields if field.hoist is None}
        entries = [
            f"({_string(field.label)}, {body.values(field).populated})" for field in fields if field.hoist is None
        ]
        entries.extend(f"({_string(hoist.label)}, {self.hoist_present(hoist, body.values)})" for hoist in hoists)
        lines = [f"let present = {_RUNTIME}::populated(&[{', '.join(entries)}]);"]
        for plan in plans:
            conditions = [
                (
                    f"{_RUNTIME}::alternative_fits(&present, {_str_slice(sorted(plan.required_labels))},"
                    f" {_str_slice(sorted(plan.labels))})"
                )
            ]
            conditions.extend(
                self.kind_condition(body, by_label[guard.label], guard)
                for guard in am.selection_guards(self.model, fields, plan)
            )
            lines.extend(_if_block(conditions, [f"return {call(plan.index)};"], 0))
        message = _message(f'rule "{body.rule_name}": no alternative fits the populated fields')
        lines.append(f"Err({_AST_ERROR}::new({message}, {_SPAN_TYPE}::unknown()))")
        return lines

    def kind_condition(self, body: _Body, field: am.Field, guard: am.SelectionGuard) -> str:
        """The test that every value one field holds is a kind this alternative accepts.

        The value carries its own kind as the field enum variant wrapping it, and the variants
        are read off the enum's own declaration, so a test and the type it reads cannot drift
        apart.  A field holding no value passes: what an alternative does with a label it is not
        given is the name test's question.

        A keyed map is not spelled here: a label whose values are keyed carries one element type,
        which is a field of its own type rather than a field enum, and a single-element field is
        never kind-tested at all.
        """
        field_enum = self.field_enum_of(field)
        assert field_enum is not None
        by_element = {variant.element: variant.name for variant in field_enum.variants}
        patterns = " | ".join(f"{field_enum.name}::{by_element[kind.element]}(_)" for kind in guard.accepted)
        place = body.values(field)
        if field.type.container is am.Container.OPTIONAL:
            return f"{place.optional}.into_iter().all(|{_ITEM}| matches!({_ITEM}, {patterns}))"
        if field.type.container is am.Container.COLLECTION:
            return f"{place.value}.iter().all(|{_ITEM}| matches!({_ITEM}, {patterns}))"
        # A pattern that binds nothing reads the value where it lies, so a member held through
        # an indirection is dereferenced rather than moved out of.
        held = f"*{place.value}" if self.is_boxed_element(body.owner, field.type.element) else place.value
        return f"matches!({held}, {patterns})"

    def alternative_lines(
        self,
        body: _Body,
        fields: Sequence[am.Field],
        plan: am.AltPlan,
        hoists: Sequence[am.Hoist] = (),
    ) -> list[str]:
        """Statements building the CST node for one alternative.

        A hoisted field is not distributed over this rule's item positions: its wrapper occupies
        one position, and the wrapper's own helper places the fields inside it.
        """
        own = [field for field in fields if field.hoist is None]
        by_label = {field.label: field for field in own}
        by_hoist = {hoist.label: hoist for hoist in hoists}
        served: set[str] = set()
        walk: list[str] = []
        for run in am.synthesis_runs(self.model, plan):
            hoist = by_hoist.get(run.label or "")
            if hoist is not None:
                walk.extend(self.hoist_reverse_lines(body, hoist))
            elif run.dispatched:
                walk.extend(self.dispatch_lines(body, run, by_label, served))
            else:
                walk.extend(self.slot_lines(body, run, by_label, served))
        lines = self.group_check_lines(body, am.group_checks(plan, fields, hoists), by_label, by_hoist)
        mutable = "mut " if walk else ""
        node_type = self.cst_node_type(body.rule_name)
        lines.append(f"let {mutable}cst_node = {node_type}::new({_SPAN_TYPE}::unknown());")
        for field in own:
            # Only a cursor some position draws from is mutable; the others are read for what they
            # still hold, which is what `check_consumed` reports.
            mutable = "mut " if field.label in served else ""
            values = body.values(field).cursor
            lines.append(f"let {mutable}{self.cursor_name(field.label)} = {_RUNTIME}::Cursor::new({values});")
        lines.extend(walk)
        lines.extend(
            f"{_RUNTIME}::check_consumed({_string(body.rule_name)}, {_string(field.label)},"
            f" {self.cursor_name(field.label)}.remaining())?;"
            for field in own
        )
        lines.append("Ok(cst_node.into())")
        return lines

    def group_check_lines(
        self,
        body: _Body,
        checks: Sequence[am.GroupCheck],
        by_label: Mapping[str, am.Field],
        by_hoist: Mapping[str, am.Hoist],
    ) -> list[str]:
        """Statements checking that each sub-expression alternation's values suit a single branch."""
        lines: list[str] = []
        for check in checks:
            entries = ", ".join(
                f"({_string(label)}, {self.label_populated(label, body.values, by_label, by_hoist)})"
                for label in check.labels
            )
            branches = ", ".join(_str_slice(sorted(labels)) for labels in check.branches)
            lines.extend(
                (
                    f"{_RUNTIME}::check_group(",
                    f"    {_string(body.rule_name)},",
                    f"    &{_RUNTIME}::populated(&[{entries}]),",
                    f"    &[{branches}],",
                    f"    {_str_slice(sorted(check.exclusive))},",
                    f"    {str(check.demanded).lower()},",
                    ")?;",
                )
            )
        return lines

    def label_populated(
        self,
        label: str,
        values: _Values,
        by_label: Mapping[str, am.Field],
        by_hoist: Mapping[str, am.Hoist],
    ) -> str:
        """Where one label of an alternation group reads its populated state from."""
        field = by_label.get(label)
        if field is not None:
            return values(field).populated
        return self.hoist_present(by_hoist[label], values)

    def hoist_present(self, hoist: am.Hoist, values: _Values) -> str:
        """Whether a hoisted group counts as populated, for alternative and branch selection."""
        if am.hoist_always_present(hoist):
            return "true"
        return self.wrapper_needed(hoist, values)

    @staticmethod
    def wrapper_needed(hoist: am.Hoist, values: _Values) -> str:
        """The test deciding whether an optional flattened wrapper has to be rebuilt."""
        states = ", ".join(values(field).populated for field in hoist.fields)
        return f"{_RUNTIME}::wrapper_needed(&[{states}])"

    def hoist_reverse_lines(self, body: _Body, hoist: am.Hoist) -> list[str]:
        """Statements re-materialising a flattened wrapper from the fields hoisted out of it.

        An optional wrapper is rebuilt only when something it carries is populated, so a value
        whose hoisted fields all sit at their absent defaults renders without the wrapper — the
        same collapse an absent wrapper produces.
        """
        wrapper = self.model.nodes[hoist.rule_name]
        assert isinstance(wrapper, am.ProductNode)
        arguments = ", ".join(
            self.hoist_argument(hoist, parent, own, body.values(parent))
            for parent, own in zip(hoist.fields, wrapper.fields, strict=True)
        )
        call = f"{am.flat_converter_names(hoist.rule_name)[1]}({arguments})?"
        push = self.push_lines(
            self.child_label(body.rule_name, hoist.label),
            f"{self.child_variant(body.rule_name, hoist.rule_name)}({call})",
        )
        if not hoist.optional:
            return push
        return _if_block([self.wrapper_needed(hoist, body.values)], push, 0)

    @staticmethod
    def hoist_argument(hoist: am.Hoist, parent: am.Field, own: am.Field, place: _Place) -> str:
        """One argument of a wrapper's reverse helper, given how the containing type holds it.

        A field the wrapper requires was degraded to optional at an optional use site, so it has to
        be checked: a half-populated wrapper is the user's data, not a CST the formatter can report
        on.
        """
        if own.type.element == am.BOOL:
            return place.value
        if own.type.container is am.Container.SINGLE:
            if parent.type.container is am.Container.OPTIONAL:
                return f"{_RUNTIME}::hoisted({place.optional}, {_string(hoist.rule_name)}, {_string(own.name)})?"
            return place.reference
        if own.type.container is am.Container.OPTIONAL:
            return place.optional
        return place.container

    def slot_lines(self, body: _Body, run: am.SlotRun, by_label: Mapping[str, am.Field], served: set[str]) -> list[str]:
        """Statements appending the children one item position contributes."""
        slot = run.slots[0]
        if slot.kind is am.SlotKind.UNLABELED:
            # The occurrence count is not recorded, so the grammar minimum is what comes back.
            child = f"{self.child_variant(body.rule_name, gshape.TEXT_KIND)}({_SPAN_TYPE}::unknown())"
            return [line for _ in range(slot.minimum) for line in self.push_lines("None", child)]
        label = slot.label or ""
        field = by_label.get(label)
        if field is None:
            return []
        served.add(label)
        guard = self.guard_condition(body, run.placements[0], field)
        cursor = self.cursor_name(label)
        bounds = f"{_count(run.maximum)}, {run.reserve}"
        take = f"{cursor}.take({bounds})" if guard is None else f"{cursor}.take_if({bounds}, |{_ITEM}| {guard})"
        lines = [f"let taken = {take};"]
        lines.extend(self.filled_lines(body, run, label))
        placed = self.child_lines(body, field, slot, _ITEM)
        lines.extend((f"for {self.loop_binding(placed)} in taken {{", *_indent(placed, 4), "}"))
        return lines

    def dispatch_lines(
        self, body: _Body, run: am.SlotRun, by_label: Mapping[str, am.Field], served: set[str]
    ) -> list[str]:
        """Statements handing one label's values to whichever branch of a run accepts each.

        The branches of an alternation are mutually exclusive, so the label's values arrive in
        source order and any of them may occupy any branch; which one is decided per value.
        """
        label = run.label or ""
        field = by_label.get(label)
        if field is None:
            return []
        served.add(label)
        clauses = [
            (
                self.guard_condition(body, placement, field) or "true",
                self.child_lines(body, field, placement.slot, _ITEM),
            )
            for placement in run.placements
        ]
        kind = self.element_type(field.type.element)
        otherwise = [f"return Err({self.unplaceable(body.rule_name, label, kind)});"]
        lines = [f"let taken = {self.cursor_name(label)}.take({_count(run.maximum)}, {run.reserve});"]
        lines.extend(self.filled_lines(body, run, label))
        placed = _if_chain(clauses, otherwise)
        lines.extend((f"for {self.loop_binding(placed)} in taken {{", *_indent(placed, 4), "}"))
        return lines

    @staticmethod
    def unplaceable(rule_name: str, label: str, kind: str) -> str:
        """The error for a value no item position of a label can carry."""
        return f"{_RUNTIME}::unplaceable({_string(rule_name)}, {_string(label)}, {_string(kind)})"

    @staticmethod
    def filled_lines(body: _Body, run: am.SlotRun, label: str) -> list[str]:
        """The check that a run of positions the grammar requires values for got them."""
        if run.minimum < 1:
            return []
        return [
            f"{_RUNTIME}::filled(taken.len(), {run.minimum}, {_string(body.rule_name)}, {_string(label)})?;",
        ]

    @staticmethod
    def loop_binding(placed: Sequence[str]) -> str:
        """The name a run's loop binds each value to, underscored where the body never reads it."""
        return _ITEM if any(_ITEM in line for line in placed) else f"_{_ITEM}"

    # --- One value, and the item position it occupies ------------------------------------

    def field_enum_of(self, field: am.Field) -> am.FieldEnum | None:
        """The field enum a label's values are wrapped in, when the label carries several types."""
        element = field.type.element
        if isinstance(element, am.NodeType):
            return self.model.field_enums.get(element.name)
        return None

    def field_enum_variant(self, field_enum: am.FieldEnum, slot: am.Slot) -> am.FieldEnumVariant:
        """Which variant of a field enum wraps the values of one item position.

        A field enum holds at most one scalar variant — a literal contributes text where the
        label carries anything else, and a bare span or presence flag is a label of a single
        type, which is no enum — so a literal and a regex position under one label resolve to
        that one variant, and the resolution never comes back empty.  The ``ValueError`` is
        therefore a report that the model is broken, not a shape a grammar can reach.
        """
        element = am.slot_element(self.model, slot, [variant.element for variant in field_enum.variants])
        for variant in field_enum.variants:
            if variant.element == element:
                return variant
        msg = f"no variant of {field_enum.name} carries the values of {slot!r}"
        raise ValueError(msg)

    def scrutinee(self, body: _Body, field: am.Field, value: str) -> str:
        """One value as a pattern can read it, through whatever indirection its owner holds it by."""
        if self.is_boxed_element(body.owner, field.type.element):
            return f"&**{value}"
        return value

    def guard_condition(self, body: _Body, placement: am.SlotPlacement, field: am.Field) -> str | None:
        """The test one item position applies to a value, or ``None`` where it takes anything.

        Rust types carry most of what the Python backend has to ask at runtime: a label whose
        positions all hold one type needs no test, and a label carrying several is a field enum
        whose variant *is* the test.  What a type cannot say is content — which of two terminals
        accepts this text, which of two erased rules could render it — and that is the rest.
        """
        guard = placement.guard
        if guard.kind is am.GuardKind.NONE:
            return None
        field_enum = self.field_enum_of(field)
        if field_enum is None:
            return self.content_test(guard, _ITEM)
        variant = self.field_enum_variant(field_enum, placement.slot)
        pattern = f"{field_enum.name}::{variant.name}"
        content = self.content_test(guard, _TEXT)
        scrutinee = self.scrutinee(body, field, _ITEM)
        if content is None:
            return f"matches!({scrutinee}, {pattern}(_))"
        return f"matches!({scrutinee}, {pattern}({_TEXT}) if {content})"

    def content_test(self, guard: am.Guard, value: str) -> str | None:
        """What a position tests about a value's content, where its type cannot decide."""
        if guard.kind is am.GuardKind.PATTERN:
            return f"{self.terminal_reference(guard.pattern or '')}.matches({value})"
        if guard.kind is am.GuardKind.LITERAL:
            # A labeled literal renders from the grammar, so a position holding one may take a
            # value only where that value *is* the literal: anything else would come back changed.
            return f"{value} == {_string(guard.literal or '')}"
        if guard.kind is am.GuardKind.CONVERTIBLE:
            # Two rules erased to one type leave nothing on the value to tell their positions
            # apart; what distinguishes them is which terminal accepts the rendering, and that is
            # what the rule's own reverse converter checks.
            return f"{am.erased_converter_names(guard.rule_name or '')[1]}({value}).is_ok()"
        return None

    def child_label(self, rule_name: str, label: str) -> str:
        return f"Some({self.label_variant(rule_name, label)})"

    def child_lines(self, body: _Body, field: am.Field, slot: am.Slot, value: str) -> list[str]:
        """Statements appending the CST child one value of ``slot`` becomes."""
        label = slot.label or ""
        span_child = f"{self.child_variant(body.rule_name, gshape.TEXT_KIND)}"
        if slot.kind is am.SlotKind.LITERAL:
            # A literal's text is a grammar constant, so the child carries position only.
            return self.push_lines(self.child_label(body.rule_name, label), f"{span_child}({_SPAN_TYPE}::unknown())")
        lines: list[str] = []
        element = field.type.element
        field_enum = self.field_enum_of(field)
        if field_enum is not None:
            variant = self.field_enum_variant(field_enum, slot)
            element = variant.element
            refused = self.unplaceable(body.rule_name, label, field_enum.name)
            lines = [
                f"let {field_enum.name}::{variant.name}({_INNER}) = {self.scrutinee(body, field, value)} else {{",
                f"    return Err({refused});",
                "};",
            ]
            value = _INNER
        if slot.kind is am.SlotKind.TEXT:
            pattern = self.terminal_reference(slot.pattern or "")
            span = f"{_RUNTIME}::text_span({value}, {pattern}, {_string(body.rule_name)}, {_string(label)})?"
            child = f"{span_child}({span})"
        else:
            child = f"{self.child_variant(body.rule_name, slot.rule_name or '')}({self.reverse_call(element, value)})"
        return [*lines, *self.push_lines(self.child_label(body.rule_name, label), child)]

    def reverse_call(self, element: am.ElementType, value: str) -> str:
        """The expression synthesising the CST node one element's value stands for."""
        if isinstance(element, am.CustomType):
            cst_type = f"{_SHARED_TYPE}<{self.cst_node_type(element.rule_name)}>"
            # Named through the trait rather than by method call: the user's type may carry an
            # inherent `to_cst` of its own, and the trait impl is what the sidecar asked for.
            return f"<{self.custom_path(element)} as {_RUNTIME}::ToCst<{cst_type}>>::to_cst({value})?"
        if isinstance(element, am.TransparentType):
            return f"{am.erased_converter_names(element.rule_name)[1]}({value})?"
        assert isinstance(element, am.NodeType)
        return f"{value}.to_cst()?"

    # --- Terminal-only and enum-shaped rules ---------------------------------------------

    def emit_terminal_shape(self, rule_name: str) -> None:
        """The table a terminal-only rule's ``to_cst`` splits its text against.

        One ``static`` per rule: the alternatives are patterns, and the regexes behind them are
        compiled on first use, so a rule nothing ever serialises costs nothing at all.
        """
        self.separate()
        self.emit(
            f"/// How each alternative of rule `{rule_name}` splits the node's text back into children.",
            f"static {am.terminal_constant_name(rule_name)}: {_RUNTIME}::TerminalShape =",
            f"    {_RUNTIME}::TerminalShape::new(&[",
        )
        for plan in self.model.plans[rule_name].terminals:
            groups = ", ".join(
                "None" if piece.group is None else f"Some({_string(piece.group)})" for piece in plan.pieces
            )
            self.emit(
                f"        {_RUNTIME}::TerminalAlt {{",
                f"            pattern: {'None' if plan.pattern is None else f'Some({_string(plan.pattern)})'},",
                f"            groups: &[{groups}],",
                "        },",
            )
        self.emit("    ]);")

    def terminal_to_cst_body(self, rule_name: str, node: am.TerminalNode, held: _Held) -> list[str]:
        """Statements splitting a terminal-only rule's text back across the grammar's items."""
        arms = [(plan, self.terminal_arm(rule_name, plan)) for plan in self.model.plans[rule_name].terminals]
        pushes = [(plan, arm) for plan, arm in arms if arm]
        lines, text = self.terminal_text_lines(rule_name, node, held)
        # The split validates the text against the rule's own terminals whether or not any child
        # comes out of it, so it runs even for a rule whose every included item is a literal.
        split = "split" if pushes else "_split"
        lines.append(f'let {split} = {am.terminal_constant_name(rule_name)}.split({text}, "{rule_name}")?;')
        # Under `text_from:` the text belongs to one child, so the node's own span stays unknown;
        # otherwise the node's span is the text, which is where `from_cst` reads it back from.
        span = f"{_SPAN_TYPE}::unknown()" if node.text_from is not None else f"{_RUNTIME}::source_span({text})"
        binding = "let cst_node" if not pushes else "let mut cst_node"
        lines.append(f"{binding} = {self.cst_node_type(rule_name)}::new({span});")
        if len(arms) == 1:
            lines.extend(arms[0][1])
        elif pushes:
            lines.extend(_if_chain([(f"split.alternative == {plan.index}", arm) for plan, arm in pushes]))
        lines.append("Ok(cst_node.into())")
        return lines

    def terminal_text_lines(self, rule_name: str, node: am.TerminalNode, held: _Held) -> tuple[list[str], str]:
        """Statements binding the text a terminal-only rule renders to, and the name they bind."""
        if node.coercion is None:
            return [f"let text = {held.text};"], "text"
        rendered = self.render_expression(rule_name, node.coercion, held)
        return [f"let rendered = {rendered.expression};", "let text = rendered.as_str();"], "text"

    def render_expression(self, rule_name: str, coercion: am.Coercion, held: _Held) -> _Value:
        """The expression rendering a coerced value back to text the grammar accepts."""
        if isinstance(coercion, am.CustomCoercion):
            unparse = _rust_path(coercion.rust_unparse, coercion.rule_name, "type: custom(...)", "rust_unparse")
            return _Value(f"{unparse}({held.reference})")
        if coercion.is_integer:
            # No range check: the member is the width itself, so a value it cannot hold cannot be
            # written.  The Python backend checks because its `int` is unbounded.
            return _Value(f"{held.place}.to_string()")
        if coercion.is_float:
            call = f'{_RUNTIME}::scalar::render_{coercion.name}({held.copied}, "{rule_name}", {held.span})'
            return _Value(call, fallible=True)
        return _Value(f"{_RUNTIME}::scalar::render_{coercion.name}({held.reference})")

    def terminal_arm(self, rule_name: str, plan: am.TerminalPlan) -> list[str]:
        """Statements appending the children one alternative's items take from the split."""
        lines: list[str] = []
        for index, piece in enumerate(plan.pieces):
            label = "None" if piece.label is None else self.child_label(rule_name, piece.label)
            child = f"{self.child_variant(rule_name, gshape.TEXT_KIND)}(split.spans[{index}].clone())"
            lines.extend(self.push_lines(label, child))
        return lines

    def enum_to_cst_body(self, rule_name: str, node: am.EnumNode, held: _Held) -> list[str]:
        """Statements building the CST node for the alternative the value names.

        The label is what the parser recorded; a literal's text comes back from the grammar, so
        the child carries position only.
        """
        lines = self.enum_label_lines(rule_name, node, held)
        lines.append(f"let mut cst_node = {self.cst_node_type(rule_name)}::new({_SPAN_TYPE}::unknown());")
        child = f"{self.child_variant(rule_name, gshape.TEXT_KIND)}({_SPAN_TYPE}::unknown())"
        lines.extend(self.push_lines("Some(label)", child))
        lines.append("Ok(cst_node.into())")
        return lines

    def enum_label_lines(self, rule_name: str, node: am.EnumNode, held: _Held) -> list[str]:
        """Statements binding the CST label of the alternative the value names."""
        variants = node.value_enum.variants
        if node.bool_truthy is not None:
            truthy = next(variant for variant in variants if variant.label == node.bool_truthy)
            falsy = next(variant for variant in variants if variant.label != node.bool_truthy)
            return [
                f"let label = if {held.copied} {{",
                f"    {self.label_variant(rule_name, truthy.label)}",
                "} else {",
                f"    {self.label_variant(rule_name, falsy.label)}",
                "};",
            ]
        lines = [f"let label = match {held.place} {{"]
        lines.extend(
            f"    {node.value_enum.name}::{variant.name} => {self.label_variant(rule_name, variant.label)},"
            for variant in variants
        )
        lines.append("};")
        return lines

    @staticmethod
    def push_lines(label: str, child: str) -> list[str]:
        """One ``push_child`` call, broken across lines where it does not fit on one."""
        single = f"cst_node.push_child({label}, {child});"
        if len(single) + _PUSH_COLUMNS <= _MAX_LINE:
            return [single]
        return ["cst_node.push_child(", f"    {label},", f"    {child},", ");"]

    # --- The one-call entry points --------------------------------------------------------

    def goal_type(self) -> str:
        """The type the conveniences take and return: a user type, or the payload where erased."""
        goal = self.goal_rule or ""
        custom = self.model.custom_types.get(goal)
        if custom is not None:
            return self.custom_path(custom)
        erased = self.model.transparent_types.get(goal)
        if erased is not None:
            return self.element_type(erased)
        return self.model.nodes[goal].name

    def goal_parameter(self) -> str:
        """The goal type as ``unparse_str`` takes it: by reference, and never as a ``&String``."""
        goal_type = self.goal_type()
        return f"&{_BORROWED_TYPES.get(goal_type, goal_type)}"

    def goal_from_cst(self, node: str) -> str:
        """The expression converting the goal rule's CST node, propagating a conversion failure."""
        goal = self.goal_rule or ""
        custom = self.model.custom_types.get(goal)
        if custom is not None:
            return self.convert_call(custom, node).expression
        if goal in self.model.transparent_types:
            return f"{am.erased_converter_names(goal)[0]}({node})?"
        return f"{self.goal_type()}::from_cst({node})?"

    def goal_to_cst(self, value: str) -> str:
        """The expression synthesising the goal rule's CST node, propagating a failure."""
        goal = self.goal_rule or ""
        custom = self.model.custom_types.get(goal)
        if custom is not None:
            return self.reverse_call(custom, value)
        if goal in self.model.transparent_types:
            return f"{am.erased_converter_names(goal)[1]}({value})?"
        return f"{value}.to_cst()?"

    def emit_conveniences(self) -> None:
        """The one-call entry points, each emitted only when the module behind it is named."""
        if self.parser_mod_path is not None:
            self.emit_parse_str()
        if self.unparser_mod_path is not None:
            self.emit_unparse_str()

    def emit_parse_str(self) -> None:
        """``parse_str``: source text to an AST value, in one call."""
        goal = self.goal_rule
        parse_error = f"{_RUNTIME}::ParseToAstError"
        failed = f"return Err({parse_error}::Parse(parser.error_message()));"
        self.separate()
        self.emit(
            f"/// Parse `src` as `{goal}` and convert the result to its AST.",
            "///",
            "/// `filename` names the source in the parser's diagnostics. Trivia is not captured: a",
            "/// converter ignores unlabeled children, so there is nothing to capture it for.",
            f"pub fn {am.PARSE_STR_FUNCTION}(src: &str, filename: Option<&str>)"
            f" -> Result<{self.goal_type()}, {parse_error}> {{",
            f"    let mut parser = {_PARSER_ALIAS}::Parser::new(src, filename, false);",
            f"    let result = parser.apply__parse_{goal}(0);",
            "    // A depth-rejected parse can still come back as `Some` holding a wrong tree.",
            "    if parser.depth_exceeded() {",
            f"        {failed}",
            "    }",
            "    let Some(parsed) = result else {",
            f"        {failed}",
            "    };",
            "    // The whole input has to be consumed; `pos` counts characters, not bytes.",
            "    if parsed.pos != src.chars().count() as i64 {",
            f"        {failed}",
            "    }",
            f"    Ok({self.goal_from_cst('&parsed.result')})",
            "}",
        )

    def emit_unparse_str(self) -> None:
        """``unparse_str``: an AST value back to source text, in one call."""
        goal = self.goal_rule
        self.separate()
        self.emit(
            "/// Render `value` back to source text through the grammar's generated formatter.",
            "///",
            "/// The layout is whatever that formatter was generated with — the grammar's `.fltkfmt`,",
            "/// or the default separator spacing; `max_width` and `indent_width` are the renderer's.",
            f"pub fn {am.UNPARSE_STR_FUNCTION}(value: {self.goal_parameter()},"
            f" max_width: usize, indent_width: usize) -> Result<String, {_AST_ERROR}> {{",
            f"    let node = {self.goal_to_cst('value')};",
            "    let guard = node.read();",
            f"    let Some(unparsed) = {_UNPARSER_ALIAS}::Unparser::new().unparse_{goal}(&guard) else {{",
            f'        return Err({_RUNTIME}::unrenderable("{goal}"));',
            "    };",
            f"    let resolved = {_UNPARSER_RUNTIME}::resolve_spacing_specs(unparsed.doc());",
            f"    let config = {_UNPARSER_RUNTIME}::RendererConfig {{",
            "        indent_width,",
            "        max_width,",
            "    };",
            f"    Ok({_UNPARSER_RUNTIME}::Renderer::new(config).render(&resolved))",
            "}",
        )


def generate_ast_rs(
    model: am.AstModel,
    cst_mod_path: str = "super::cst",
    source_name: str | None = None,
    *,
    parser_mod_path: str | None = None,
    unparser_mod_path: str | None = None,
    goal_rule: str | None = None,
) -> str:
    """Return the source of the Rust AST module for ``model``.

    ``cst_mod_path`` is the path of the grammar's generated Rust CST module, imported as ``cst``.
    ``source_name`` names the grammar in the header comment when it is known.  Naming a parser
    module adds ``parse_str``; naming an unparser module adds ``unparse_str``; ``goal_rule`` is
    what both target, defaulting to the grammar's first rule with an AST type.
    """
    return RustAstGenerator(
        model,
        cst_mod_path,
        source_name,
        parser_mod_path=parser_mod_path,
        unparser_mod_path=unparser_mod_path,
        goal_rule=goal_rule,
    ).generate()
