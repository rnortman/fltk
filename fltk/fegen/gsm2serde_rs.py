"""Rust serde emitter: turns an ``AstModel`` into a ``de.rs`` describing its tree.

A generated ``de.rs`` is not a Deserializer.  The Deserializer — the data-model mapping, the
error positions, the map/seq duality, the keyed identity rule — lives once in
``fltk-serde-core``; what a grammar contributes is a *description* of its own tree, because a
CST's node types, labels and children are per-rule generated types nothing in a runtime crate
can name.  So this module emits, per rule: one ``static`` :rust:`Shape` saying how that rule's
nodes are served, one ``NodeShape`` impl handing the runtime the node's span and its labeled
children, and one entry point deserializing a target from one of those nodes.  Naming a parser
module adds ``from_str``, which parses and then deserializes in one call; naming an AST module
adds a ``Deserialize`` impl per generated AST type, each one call over that type's ``from_cst``,
so an expression sub-language is a field of a hand-written target like anything else.

Everything the descriptions say comes from :mod:`fltk.fegen.ast_model`: field names and order,
containers, map keys, hoist paths, variant names, sum dispatch, fold layout.  Nothing is
re-derived here — an analysis the model does not publish belongs in the model, not in an
emitter, so that the AST types and the serde data model describe one tree by construction.
Rust fragments the AST emitter also writes (the dispatch table, the ``UNBOUNDED`` spelling) come
from :mod:`fltk.fegen.rust_emit`, so one model fact has one rendering.

Runtime types are named by absolute path (``::fltk_serde_core::Field``), as in
:mod:`fltk.fegen.gsm2ast_rs`, so a rule name cannot shadow them.
"""

from __future__ import annotations

from collections.abc import Sequence

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import naming, rust_emit
from fltk.fegen.gsm2parser_rs import cst_module_import, module_import, rust_str_lit
from fltk.fegen.gsm2tree_rs import RustCstGenerator

RUNTIME = "::fltk_serde_core"
_CST_RUNTIME = "::fltk_cst_core"
_SERDE = "::serde"

_PARSER_ALIAS = "parser"
"""What the optional parser module behind ``from_str`` is imported as."""

_AST_ALIAS = "ast"
"""What the optional AST module whose types get ``Deserialize`` impls is imported as."""

_TARGET = f"T: {_SERDE}::de::DeserializeOwned"
"""The bound every entry point takes its target under: owned values, no borrowed lifetime."""

_MODULE_DOC = (
    "//!",
    "//! One shape description per rule, and the entry points that run the runtime's",
    "//! Deserializer over one. The target type drives interpretation: a consumer's own",
    "//! `#[derive(Deserialize)]` structs decide what the tree means, and errors serde raises",
    "//! about them are positioned by the CST spans behind them.",
    "//!",
    "//! Requires crates: `serde`, `fltk-serde-core`.",
)

_KEY_KINDS = {
    "text": "Text",
    "i8": "I8",
    "i16": "I16",
    "i32": "I32",
    "i64": "I64",
    "u8": "U8",
    "u16": "U16",
    "u32": "U32",
    "u64": "U64",
}
"""What each key type the sidecar admits is spelled as in the runtime's ``KeyKind``.

Written out rather than derived by upper-casing the model's name: the variant inventory belongs
to the runtime, so a key type with no spelling here is a ``KeyError`` at generation time rather
than a compile error in a consumer's build.
"""

_indent = rust_emit.indent
"""Every line moved right by the given number of columns."""

_string = rust_emit.string
"""One Rust string literal."""

_member_lines = rust_emit.member_lines
"""One ``name: value,`` entry of a struct literal, whose value may run over several lines."""


def _option(text: str | None) -> str:
    """One optional label, as the runtime holds it."""
    return "None" if text is None else f"Some({_string(text)})"


_FLAGS = {True: "true", False: "false"}
"""One model flag, as the Rust literal the description carries it as."""


def _slice_lines(entries: Sequence[Sequence[str]]) -> list[str]:
    """One Rust slice literal over values that may each run over several lines."""
    if not entries:
        return ["&[]"]
    lines = ["&["]
    for entry in entries:
        lines.extend(_indent([*entry[:-1], f"{entry[-1]},"], 4))
    lines.append("]")
    return lines


class RustSerdeGenerator:
    """Emits the Rust serde description module for one grammar's model."""

    def __init__(
        self,
        model: am.AstModel,
        cst_mod_path: str = "super::cst",
        source_name: str | None = None,
        *,
        parser_mod_path: str | None = None,
        goal_rule: str | None = None,
        ast_mod_path: str | None = None,
    ) -> None:
        self.model = model
        self.cst_mod_path = cst_mod_path
        self.source_name = source_name
        self.parser_mod_path = parser_mod_path
        self.ast_mod_path = ast_mod_path
        self.rules = am.serde_rules(model)
        # The rules a `Deserialize` impl is written for; empty until an AST module is named, and
        # empty even then for a grammar whose every rule is erased or handed to a custom type.
        self.ast_rules = am.serde_ast_rules(model) if ast_mod_path is not None else ()
        # Resolved only where something needs it: a module emitting no `from_str` names no
        # goal rule, and an explicitly named one is still checked.
        self.goal_rule = (
            am.resolve_serde_goal(model, goal_rule) if goal_rule is not None or parser_mod_path is not None else None
        )
        # Called for the raise: a collision is refused before anything is emitted, because these
        # names are load-bearing and a second claimant would silently win in the consumer's
        # module namespace.  The table itself is the emitted module's inventory, which
        # `tests/test_gsm2serde_rs.py` sweeps the generated source against.
        am.serde_claims(model)
        # Class, label-enum and child-enum spellings come from the CST generator, so a
        # description cannot name a type the CST module does not emit.
        self.cst = RustCstGenerator(model.grammar)
        self.trivia_classes = frozenset(
            self.cst.class_name_for_rule(rule.name) for rule in model.grammar.rules if rule.is_trivia_rule
        )
        self.lines: list[str] = []
        self._generated: str | None = None

    def cst_node_type(self, rule_name: str) -> str:
        return f"cst::{self.cst.class_name_for_rule(rule_name)}"

    def label_variant(self, rule_name: str, label: str) -> str:
        """The CST label enum member one label is spelled as."""
        class_name = self.cst.class_name_for_rule(rule_name)
        return f"cst::{self.cst.label_enum_name(class_name)}::{naming.snake_to_upper_camel(label)}"

    def child_variant(self, rule_name: str, variant: str) -> str:
        """One member of a rule's CST child enum, by the variant's own spelling."""
        class_name = self.cst.class_name_for_rule(rule_name)
        return f"cst::{self.cst.child_enum_name(class_name)}::{variant}"

    def emit(self, *lines: str) -> None:
        self.lines.extend(lines)

    def separate(self) -> None:
        """Open a new top-level item."""
        self.lines.append("")

    def generate(self) -> str:
        """Return the complete ``de.rs`` source.

        Idempotent: a second call returns the first call's result.
        """
        if self._generated is not None:
            return self._generated
        self.emit_header()
        for rule_name in self.rules:
            self.emit_rule(rule_name)
        for rule_name in self.ast_rules:
            self.emit_ast_impl(rule_name)
        for rule_name in self.rules:
            self.emit_entry_point(rule_name)
        if self.parser_mod_path is not None:
            self.emit_from_str()
        self._generated = "\n".join(self.lines) + "\n"
        return self._generated

    def emit_header(self) -> None:
        origin = "" if self.source_name is None else f" from `{rust_str_lit(self.source_name)}`"
        self.emit(f"//! Generated by fltk gen-rust-serde{origin}. Do not edit.", *_MODULE_DOC)
        # Every shape impl names a CST node type, so the import is always used.
        self.emit("", cst_module_import(self.cst_mod_path))
        if self.parser_mod_path is not None:
            self.emit(module_import(self.parser_mod_path, _PARSER_ALIAS))
        # Only where something names it: an import nothing uses is a warning, and a warning is a
        # hard build failure in a consumer denying them.
        if self.ast_rules:
            assert self.ast_mod_path is not None, "a rule gets an impl only where an AST module is named"
            self.emit(module_import(self.ast_mod_path, _AST_ALIAS))

    def emit_rule(self, rule_name: str) -> None:
        """One rule's supporting statics, its shape, and the impl handing the runtime its nodes."""
        self.emit_supporting(rule_name)
        self.separate()
        self.emit(
            f"/// How rule `{rule_name}`'s nodes are served.",
            f"static {am.serde_shape_name(rule_name)}: {RUNTIME}::Shape = {RUNTIME}::Shape {{",
            f"    rule: {_string(rule_name)},",
        )
        self.emit(*_indent(_member_lines("form", self.form_lines(rule_name)), 4))
        self.emit("};")
        self.emit_node_shape(rule_name)

    # --- Shapes --------------------------------------------------------------------------

    def emit_supporting(self, rule_name: str) -> None:
        """The statics a rule's form points at: a sum's dispatch table and alternatives, a
        fold's chain description."""
        node = self.model.nodes.get(rule_name)
        if isinstance(node, am.SumNode):
            self.separate()
            self.emit(
                *rust_emit.dispatch_table_lines(
                    am.signature_constant_name(rule_name), rule_name, am.sum_dispatch(node), RUNTIME
                )
            )
            self.separate()
            self.emit(
                f"/// What each alternative of rule `{rule_name}` is served as, in grammar order.",
                f"static {am.serde_alternatives_name(rule_name)}: [{RUNTIME}::Alternative; {len(node.variants)}] = [",
            )
            for variant in node.variants:
                entry = self.alternative_lines(variant)
                self.emit(*_indent([*entry[:-1], f"{entry[-1]},"], 4))
            self.emit("];")
        elif isinstance(node, am.FoldNode):
            self.separate()
            self.emit(*self.fold_lines(rule_name, node))

    def alternative_lines(self, variant: am.SumVariant) -> list[str]:
        """One sum alternative: the name serde sees, and what the variant carries."""
        payload = am.generated_payload(self.model, variant)
        if payload is not None:
            content = [
                f"{RUNTIME}::Content::Fields {{",
                *_indent(
                    _member_lines("fields", _slice_lines([self.field_lines(field) for field in payload.fields])), 4
                ),
                "}",
            ]
        else:
            # A direct payload names exactly one label, which is the child the variant carries.
            label = next(iter(variant.signature.labels))
            content = [f"{RUNTIME}::Content::Child {{ label: {_string(label)} }}"]
        return [
            f"{RUNTIME}::Alternative {{",
            f"    name: {_string(variant.name)},",
            *_indent(_member_lines("payload", content), 4),
            "}",
        ]

    def fold_lines(self, rule_name: str, node: am.FoldNode) -> list[str]:
        """The chain a fold rule's flat run of children nests into."""
        direction = "Left" if node.direction is ac.FoldDirection.LEFT else "Right"
        return [
            f"/// The chain rule `{rule_name}` folds its operands into.",
            f"static {am.serde_fold_name(rule_name)}: {RUNTIME}::Fold = {RUNTIME}::Fold {{",
            f"    direction: {RUNTIME}::Direction::{direction},",
            f"    operand_label: {_string(node.operand.label)},",
            f"    operator_label: {_string(node.operators.label)},",
            f"    operand_variant: {_string(node.operand_variant)},",
            f"    binary_variant: {_string(node.binary_variant)},",
            f"    op: {_string(node.binary.op.name)},",
            f"    lhs: {_string(am.FOLD_LHS)},",
            f"    rhs: {_string(am.FOLD_RHS)},",
            "};",
        ]

    def form_lines(self, rule_name: str) -> list[str]:
        """The serde data model one rule's nodes take."""
        node = self.model.nodes.get(rule_name)
        if node is None:
            # A `custom(...)` rule has no model node: the AST layer hands it to a user type, and
            # the serde path has no target of its own to hand it to.  Its nodes are served as
            # their own source text — so a self-parsing target (a Uuid, a date) works exactly as
            # it does under serde_json, and a target wanting a map is refused, loudly, by kind.
            return [f"{RUNTIME}::Form::Terminal {{ text_from: {_option(None)} }}"]
        if isinstance(node, am.TerminalNode):
            return [f"{RUNTIME}::Form::Terminal {{ text_from: {_option(node.text_from)} }}"]
        if isinstance(node, am.EnumNode):
            return self.enum_form_lines(node)
        if isinstance(node, am.SumNode):
            return [
                f"{RUNTIME}::Form::Sum {{",
                f"    table: &{am.signature_constant_name(rule_name)},",
                f"    alternatives: &{am.serde_alternatives_name(rule_name)},",
                "}",
            ]
        if isinstance(node, am.FoldNode):
            return [f"{RUNTIME}::Form::Fold(&{am.serde_fold_name(rule_name)})"]
        assert isinstance(node, am.ProductNode)
        if rule_name in self.model.transparent_types:
            # An erased product carries exactly one field, and its use sites carry that field's
            # value with no map around it.
            (field,) = node.fields
            return [
                f"{RUNTIME}::Form::Transparent {{",
                *_indent(_member_lines("field", self.field_lines(field)), 4),
                "}",
            ]
        return [
            f"{RUNTIME}::Form::Product {{",
            *_indent(_member_lines("fields", _slice_lines([self.field_lines(field) for field in node.fields])), 4),
            "}",
        ]

    def enum_form_lines(self, node: am.EnumNode) -> list[str]:
        """A rule that is a choice between literal alternatives, and the one that is `true`."""
        variants = [
            [f"{RUNTIME}::Variant {{ name: {_string(variant.name)}, label: {_string(variant.label)} }}"]
            for variant in node.value_enum.variants
        ]
        return [
            f"{RUNTIME}::Form::Enum {{",
            *_indent(_member_lines("variants", _slice_lines(variants)), 4),
            f"    truthy: {_option(node.bool_truthy)},",
            "}",
        ]

    def field_lines(self, field: am.Field) -> list[str]:
        """One field of a product: what it is served under, and what its children add up to."""
        return [
            f"{RUNTIME}::Field {{",
            f"    name: {_string(field.name)},",
            f"    label: {_string(field.label)},",
            *_indent(_member_lines("container", self.container_lines(field.type)), 4),
            f"    hoist: {self.hoist_text(field.hoist)},",
            "}",
        ]

    def container_lines(self, field_type: am.FieldType) -> list[str]:
        """What a field's children add up to: an arity, a presence flag, or a keyed collection."""
        if field_type.element == am.BOOL:
            return [f"{RUNTIME}::Container::Presence"]
        if field_type.container is am.Container.MAP:
            key = field_type.key
            assert key is not None
            kind = _KEY_KINDS[am.map_key_scalar(key.element)]
            return [
                f"{RUNTIME}::Container::Map({RUNTIME}::Key {{",
                f"    name: {_string(key.field_name)},",
                f"    label: {_string(key.label)},",
                f"    kind: {RUNTIME}::KeyKind::{kind},",
                f"    multi: {_FLAGS[key.multi]},",
                "})",
            ]
        arity = {
            am.Container.SINGLE: "Single",
            am.Container.OPTIONAL: "Optional",
            am.Container.COLLECTION: "Collection",
        }[field_type.container]
        return [f"{RUNTIME}::Container::{arity}"]

    def hoist_text(self, hoist: Sequence[am.Wrapper]) -> str:
        """The ``flatten;`` wrappers between a node and one field's children, outermost first."""
        if not hoist:
            return "&[]"
        steps = ", ".join(
            f"{RUNTIME}::Wrapper {{ label: {_string(step.label)}, optional: {_FLAGS[step.optional]} }}"
            for step in hoist
        )
        return f"&[{steps}]"

    def emit_node_shape(self, rule_name: str) -> None:
        """``NodeShape`` for one rule: its shape, its span, and its children as the runtime reads
        them.

        Labels and child kinds are per-rule generated enums, so translating them into the
        description's strings and erased handles is the one thing that has to be emitted.
        """
        self.separate()
        self.emit(
            f"impl {RUNTIME}::NodeShape for {self.cst_node_type(rule_name)} {{",
            f"    fn shape() -> &'static {RUNTIME}::Shape {{",
            f"        &{am.serde_shape_name(rule_name)}",
            "    }",
            "",
            f"    fn node_span(&self) -> {_CST_RUNTIME}::Span {{",
            "        self.span().clone()",
            "    }",
            "",
            f"    fn labeled_children(&self) -> Vec<(Option<&'static str>, {RUNTIME}::Child)> {{",
        )
        self.emit(*_indent(self.children_body(rule_name), 8))
        self.emit("    }", "}")

    def children_body(self, rule_name: str) -> list[str]:
        """The node's children, in source order, each with the label it carries as a string.

        Unlabeled children — trivia and ``$``-included literals — keep their place with no label:
        the Deserializer skips them, but a *labeled* child is never dropped, because a label no
        alternative carries is what a sum rule's dispatch refuses a hand-built node for.  A
        trivia child is the one exception: it carries no label by construction and its rule has
        no shape to reach it through, so it is left out entirely.
        """
        arms = self.child_arms(rule_name)
        if not arms:
            # Every child of this rule is trivia, so nothing it holds is ever served.
            return ["Vec::new()"]
        labels = self.cst.label_names_for_rule(rule_name)
        binding = "label" if labels else "_label"
        lines = [
            "let mut children = Vec::with_capacity(self.children().len());",
            f"for ({binding}, child) in self.children() {{",
        ]
        if labels:
            lines.extend(_indent(self.label_lines(rule_name, labels), 4))
        else:
            lines.append("    let label: Option<&'static str> = None;")
        lines.extend(_indent(arms, 4))
        lines.extend(("    children.push((label, child));", "}", "children"))
        return lines

    def label_lines(self, rule_name: str, labels: Sequence[str]) -> list[str]:
        """The label one child carries, as the description names it.

        Through ``map`` rather than a ``match`` over the whole ``Option``: the unlabeled arm is
        the same either way, and a rule with one label would spell that ``match`` as
        ``clippy::manual_map`` — a hard build failure in every consumer under ``-D warnings``.
        """
        lines = ["let label = label.as_ref().map(|label| match label {"]
        lines.extend(f"    {self.label_variant(rule_name, label)} => {_string(label)}," for label in labels)
        lines.append("});")
        return lines

    def child_arms(self, rule_name: str) -> list[str]:
        """The child one CST child enum member holds, as the runtime reads it."""
        arms: list[str] = []
        if self.cst.has_span_child(rule_name):
            arms.append(f"    {self.child_variant(rule_name, 'Span')}(span) => {RUNTIME}::Child::Text(span.clone()),")
        for class_name in self.cst.child_class_names_for_rule(rule_name):
            variant = self.child_variant(rule_name, class_name)
            if class_name in self.trivia_classes:
                arms.append(f"    {variant}(_) => continue,")
                continue
            arms.append(f"    {variant}(node) => {RUNTIME}::Child::Node({RUNTIME}::Node::new(node.clone())),")
        if all(arm.endswith("=> continue,") for arm in arms):
            return []
        return ["let child = match child {", *arms, "};"]

    # --- AST types as targets --------------------------------------------------------------

    def emit_ast_impl(self, rule_name: str) -> None:
        """``Deserialize`` for one rule's generated AST type.

        A field declared as an AST type (``body: ast::Expr``) is then spelled like every other
        serde field, and what it means is that rule's ``from_cst`` — so folds, transparent chains
        and coercions come along by construction rather than being described a second time here.
        The impl hands the conversion to the runtime, which runs it over whichever node the
        position holds; a node of another rule is a deserialize-time error naming both.
        """
        type_name = f"{_AST_ALIAS}::{self.model.nodes[rule_name].name}"
        constant = am.serde_ast_constant_name(rule_name)
        self.separate()
        self.emit(
            f"/// The newtype-struct name `{type_name}` is deserialized under.",
            f"const {constant}: &str = {_string(am.serde_ast_name(rule_name))};",
            "",
            f"impl<'de> {_SERDE}::Deserialize<'de> for {type_name} {{",
            f"    fn deserialize<D: {_SERDE}::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {{",
            f"        {RUNTIME}::deserialize_ast(deserializer, {constant}, {type_name}::from_cst)",
            "    }",
            "}",
        )

    # --- Entry points --------------------------------------------------------------------

    def emit_entry_point(self, rule_name: str) -> None:
        """``from_<rule>_cst``: a target deserialized from one node, wherever the caller got it.

        One per rule, which is what makes a held `Raw<cst::T>` useful and lets a caller who
        already has a CST start anywhere in it.
        """
        self.separate()
        self.emit(
            f"/// Deserialize `T` from a `{rule_name}` CST node.",
            f"pub fn {am.serde_entry_name(rule_name)}<{_TARGET}>(",
            f"    node: &{_CST_RUNTIME}::Shared<{self.cst_node_type(rule_name)}>,",
            f") -> Result<T, {RUNTIME}::DeserializeError> {{",
            f"    {RUNTIME}::from_node({RUNTIME}::Node::new(node.clone()))",
            "}",
        )

    def emit_from_str(self) -> None:
        """``from_str``: source text to the caller's own type, in one call."""
        goal = self.goal_rule
        assert goal is not None, "the goal rule is resolved whenever a parser module is named"
        error = f"{RUNTIME}::ParseToTargetError"
        failed = f"return Err({error}::Parse(parser.error_message()));"
        self.separate()
        self.emit(
            f"/// Parse `src` as `{goal}` and deserialize `T` from the result.",
            "///",
            "/// `filename` names the source in the parser's diagnostics. Trivia is not captured:",
            "/// unlabeled children are skipped, so there is nothing to capture it for.",
            f"pub fn {am.SERDE_FROM_STR}<{_TARGET}>(src: &str, filename: Option<&str>) -> Result<T, {error}> {{",
            *_indent(
                rust_emit.parse_skeleton_lines(
                    goal, _PARSER_ALIAS, failed, f"{am.serde_entry_name(goal)}(&parsed.result)?"
                ),
                4,
            ),
            "}",
        )


def generate_de_rs(
    model: am.AstModel,
    cst_mod_path: str = "super::cst",
    source_name: str | None = None,
    *,
    parser_mod_path: str | None = None,
    goal_rule: str | None = None,
    ast_mod_path: str | None = None,
) -> str:
    """Return the source of the Rust serde description module for ``model``.

    ``cst_mod_path`` is the path of the grammar's generated Rust CST module, imported as ``cst``.
    ``source_name`` names the grammar in the header comment when it is known.  Naming a parser
    module adds ``from_str``; ``goal_rule`` is what it targets, defaulting to the grammar's first
    rule.  Naming an AST module adds a ``Deserialize`` impl per generated AST type, so a target
    can declare one as a field type.
    """
    return RustSerdeGenerator(
        model,
        cst_mod_path,
        source_name,
        parser_mod_path=parser_mod_path,
        goal_rule=goal_rule,
        ast_mod_path=ast_mod_path,
    ).generate()
