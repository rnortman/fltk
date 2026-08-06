"""Config model for ``.fltkast`` files, the CST-to-model transform, and validation.

Three layers, in order:

* the pre-validation model — plain dataclasses mirroring the sidecar's statements one for
  one, in source order.  Statements are kept as a list rather than folded into per-rule
  fields because duplicates and conflicts (two ``type:`` statements, ``sum;`` beside
  ``product;``) are diagnosed with the span of each offending statement.
* a small grammar index — the rule, label and shape surface validation matches statements
  against.  Shape classification comes from :mod:`fltk.fegen.grammar_shape`, which the AST
  model classifies with too, so an annotation is accepted exactly when the model will emit
  the shape it applies to.
* :class:`ResolvedAstConfig` — one frozen record per configured rule, the shape the AST
  model consumes.  Building it validates: every offense is collected and the whole set is
  raised together.
"""

from __future__ import annotations

import dataclasses
import enum
import keyword
import typing

from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import fltkast_cst as cst
from fltk.fegen import grammar_shape as gshape
from fltk.fegen import gsm
from fltk.fegen.fltkast_parser import Parser
from fltk.fegen.pyrt import error_formatter, errors, terminalsrc

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    from fltk.fegen.pyrt import span_protocol


class AstConfigError(ValueError):
    """Raised when ``.fltkast`` text fails to parse or map.

    The message renders every offense with a ``file:line:col`` caret annotation, so a
    single raise can report more than one.
    """


# --- The parsed statement model --------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CustomArg:
    """One ``key: "value"`` entry of a ``custom(...)`` argument list."""

    key: str
    value: str
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class BuiltinTypeSpec:
    """``type: i64;`` — a named builtin scalar coercion."""

    name: str
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class CustomTypeSpec:
    """``type: custom(...);`` — user-supplied type and parse/unparse function paths."""

    args: tuple[CustomArg, ...]
    span: span_protocol.SpanProtocol


TypeSpec: typing.TypeAlias = BuiltinTypeSpec | CustomTypeSpec


@dataclasses.dataclass(frozen=True)
class TypeStmt:
    """``type: <spec>;`` — a type coercion, builtin or custom."""

    spec: TypeSpec
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class BoolStmt:
    """``bool: <label>;`` — the alternative label that maps to ``true``."""

    truthy_label: str
    label_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class TransparentStmt:
    """``transparent;`` — the rule produces no AST node of its own."""

    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class TextFromStmt:
    """``text_from: <label>;`` — the label whose span text becomes the rule's ``text``."""

    label: str
    label_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class KeyStmt:
    """``key: <label>;`` — the field keying this rule's collection use sites."""

    label: str
    label_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


class FoldDirection(enum.Enum):
    """Left or right direction for binary-chain fold statements."""

    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class FoldStmt:
    """``fold_left: <op>;`` / ``fold_right: <op>;`` — binary-chain folding."""

    direction: FoldDirection
    op_label: str
    op_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class FlattenStmt:
    """``flatten;`` — inline list children into the parent."""

    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class CustomStmt:
    """``custom(rust: "...", python: "...");`` — the whole-rule escape hatch."""

    args: tuple[CustomArg, ...]
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class NameStmt:
    """``name: <ident>;`` — renames the enclosing rule's type or field."""

    new_name: str
    name_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class VariantStmt:
    """``variant <computed>: <NewName>;`` — renames one sum or fold variant."""

    selector: str
    selector_span: span_protocol.SpanProtocol
    new_name: str
    name_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class FieldStmt:
    """``field <label> { ... }`` — per-field statements for one label."""

    label: str
    label_span: span_protocol.SpanProtocol
    statements: tuple[NameStmt, ...]
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class SumStmt:
    """``sum;`` — force sum-type treatment."""

    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class ProductStmt:
    """``product;`` — force product-type treatment."""

    span: span_protocol.SpanProtocol


RuleStatement: typing.TypeAlias = (
    TypeStmt
    | BoolStmt
    | TransparentStmt
    | TextFromStmt
    | KeyStmt
    | FoldStmt
    | FlattenStmt
    | CustomStmt
    | NameStmt
    | VariantStmt
    | FieldStmt
    | SumStmt
    | ProductStmt
)


@dataclasses.dataclass(frozen=True)
class RuleBlock:
    """One ``rule <name> { ... }`` block, statements in source order."""

    rule_name: str
    rule_name_span: span_protocol.SpanProtocol
    statements: tuple[RuleStatement, ...]
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class OptionStmt:
    """One ``option <key> = <value>;`` statement; ``value`` is a bool or a string."""

    key: str
    key_span: span_protocol.SpanProtocol
    value: bool | str
    value_span: span_protocol.SpanProtocol
    span: span_protocol.SpanProtocol


@dataclasses.dataclass(frozen=True)
class AstConfig:
    """A parsed ``.fltkast`` sidecar: its global options and its rule blocks, in order."""

    options: tuple[OptionStmt, ...]
    rule_blocks: tuple[RuleBlock, ...]


# --- CST to model ----------------------------------------------------------------------

# The escapes a ``.fltkast`` string literal recognises.  The grammar's terminal admits a
# backslash before any character; anything outside this table is an error rather than a
# silent identity, so a typo in a type path is reported where it is written.
_STRING_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}


# TODO(lsp-cst-text-helpers): fourth copy of the span-text helper; consolidate with
# lsp_config, fmt_config, and unparse.pyrt.
def _span_text(span: span_protocol.SpanProtocol, terminal_src: terminalsrc.TerminalSource) -> str:
    text = span.text()
    if text is not None:
        return text
    return terminal_src.terminals[span.start : span.end]


def _render_offense(span: span_protocol.SpanProtocol, terminals: terminalsrc.TerminalSource, message: str) -> str:
    """Format one offense with a caret line.

    Spans may carry no source text, so source is re-attached from ``terminals``.
    """
    source_span = terminalsrc.Span.with_source(
        span.start, span.end, terminalsrc.SourceText(terminals.terminals, terminals.filename)
    )
    return error_formatter.format_source_line(source_span, message)


def raise_offenses(
    offenses: list[tuple[span_protocol.SpanProtocol, str]], terminals: terminalsrc.TerminalSource
) -> typing.NoReturn:
    """Raise one :class:`AstConfigError` rendering every collected offense in source order."""
    offenses.sort(key=lambda offense: (offense[0].start, offense[0].end))
    header = f"{len(offenses)} error(s) in .fltkast config:"
    body = "".join(_render_offense(span, terminals, message) for span, message in offenses)
    raise AstConfigError(header + body)


@dataclasses.dataclass
class _Mapper:
    """The CST-to-model pass: the source it reads from and the offenses it collects.

    A malformed string literal is recorded rather than raised on the spot and its raw text
    is passed through, so one bad escape does not hide the rest of the file's.
    """

    terminal_src: terminalsrc.TerminalSource
    offenses: list[tuple[span_protocol.SpanProtocol, str]] = dataclasses.field(default_factory=list)

    def error(self, span: span_protocol.SpanProtocol, message: str) -> None:
        self.offenses.append((span, message))


def _identifier(identifier: cst.Identifier, mapper: _Mapper) -> str:
    return _span_text(identifier.child_name(), mapper.terminal_src)


def _string_value(string: cst.String, mapper: _Mapper) -> str:
    """The text of a string literal with its quotes stripped and its escapes applied.

    An unrecognised escape is reported against its own two characters and passed through
    verbatim so the pass can continue.
    """
    value_span = string.child_value()
    quoted = _span_text(value_span, mapper.terminal_src)
    body = quoted[1:-1]
    out: list[str] = []
    index = 0
    while index < len(body):
        char = body[index]
        if char != "\\":
            out.append(char)
            index += 1
            continue
        escaped = body[index + 1 : index + 2]
        replacement = _STRING_ESCAPES.get(escaped)
        if replacement is None:
            # The body starts one character past the opening quote.
            start = value_span.start + 1 + index
            mapper.error(
                terminalsrc.Span(start, start + 1 + len(escaped)),
                f"unknown escape '\\{escaped}' in string literal",
            )
            out.append(char + escaped)
        else:
            out.append(replacement)
        index += 2
    return "".join(out)


def _custom_args(args: Iterable[cst.CustomArg], mapper: _Mapper) -> tuple[CustomArg, ...]:
    return tuple(
        CustomArg(
            key=_identifier(arg.child_key(), mapper),
            value=_string_value(arg.child_value(), mapper),
            span=arg.span,
        )
        for arg in args
    )


def _type_spec(spec: cst.TypeSpec, mapper: _Mapper) -> TypeSpec:
    custom = spec.maybe_custom()
    if custom is not None:
        return CustomTypeSpec(args=_custom_args(custom.children_arg(), mapper), span=custom.span)
    return BuiltinTypeSpec(name=_identifier(spec.child_builtin(), mapper), span=spec.span)


def _name_stmt(name_stmt: cst.NameStmt, mapper: _Mapper) -> NameStmt:
    new_name = name_stmt.child_new_name()
    return NameStmt(
        new_name=_identifier(new_name, mapper),
        name_span=new_name.span,
        span=name_stmt.span,
    )


def _field_stmt(field_stmt: cst.FieldStmt, mapper: _Mapper) -> FieldStmt:
    label = field_stmt.child_label()
    return FieldStmt(
        label=_identifier(label, mapper),
        label_span=label.span,
        statements=tuple(
            _name_stmt(statement.child_name_stmt(), mapper) for statement in field_stmt.children_field_statement()
        ),
        span=field_stmt.span,
    )


def _rule_statement(rule_statement: cst.RuleStatement, mapper: _Mapper) -> RuleStatement:
    if (type_stmt := rule_statement.maybe_type_stmt()) is not None:
        return TypeStmt(spec=_type_spec(type_stmt.child_spec(), mapper), span=type_stmt.span)
    if (bool_stmt := rule_statement.maybe_bool_stmt()) is not None:
        truthy = bool_stmt.child_truthy()
        return BoolStmt(truthy_label=_identifier(truthy, mapper), label_span=truthy.span, span=bool_stmt.span)
    if (transparent_stmt := rule_statement.maybe_transparent_stmt()) is not None:
        return TransparentStmt(span=transparent_stmt.span)
    if (text_from_stmt := rule_statement.maybe_text_from_stmt()) is not None:
        label = text_from_stmt.child_label()
        return TextFromStmt(label=_identifier(label, mapper), label_span=label.span, span=text_from_stmt.span)
    if (key_stmt := rule_statement.maybe_key_stmt()) is not None:
        label = key_stmt.child_label()
        return KeyStmt(label=_identifier(label, mapper), label_span=label.span, span=key_stmt.span)
    if (fold_stmt := rule_statement.maybe_fold_stmt()) is not None:
        op = fold_stmt.child_op()
        direction = FoldDirection.LEFT if fold_stmt.child_dir().maybe_left() is not None else FoldDirection.RIGHT
        return FoldStmt(
            direction=direction,
            op_label=_identifier(op, mapper),
            op_span=op.span,
            span=fold_stmt.span,
        )
    if (flatten_stmt := rule_statement.maybe_flatten_stmt()) is not None:
        return FlattenStmt(span=flatten_stmt.span)
    if (custom_stmt := rule_statement.maybe_custom_stmt()) is not None:
        return CustomStmt(args=_custom_args(custom_stmt.children_arg(), mapper), span=custom_stmt.span)
    if (name_stmt := rule_statement.maybe_name_stmt()) is not None:
        return _name_stmt(name_stmt, mapper)
    if (variant_stmt := rule_statement.maybe_variant_stmt()) is not None:
        selector = variant_stmt.child_selector()
        new_name = variant_stmt.child_new_name()
        return VariantStmt(
            selector=_identifier(selector, mapper),
            selector_span=selector.span,
            new_name=_identifier(new_name, mapper),
            name_span=new_name.span,
            span=variant_stmt.span,
        )
    if (field_stmt := rule_statement.maybe_field_stmt()) is not None:
        return _field_stmt(field_stmt, mapper)
    if (sum_stmt := rule_statement.maybe_sum_stmt()) is not None:
        return SumStmt(span=sum_stmt.span)
    if (product_stmt := rule_statement.maybe_product_stmt()) is not None:
        return ProductStmt(span=product_stmt.span)
    msg = f"unhandled rule_statement CST node: {rule_statement!r}"
    raise AssertionError(msg)


def _rule_block(rule_config: cst.RuleConfig, mapper: _Mapper) -> RuleBlock:
    rule_name = rule_config.child_rule_name()
    return RuleBlock(
        rule_name=_identifier(rule_name, mapper),
        rule_name_span=rule_name.span,
        statements=tuple(_rule_statement(statement, mapper) for statement in rule_config.children_rule_statement()),
        span=rule_config.span,
    )


def _option_stmt(option_stmt: cst.OptionStmt, mapper: _Mapper) -> OptionStmt:
    key = option_stmt.child_key()
    option_value = option_stmt.child_value()
    value: bool | str
    if option_value.maybe_true() is not None:
        value = True
    elif option_value.maybe_false() is not None:
        value = False
    else:
        value = _string_value(option_value.child_string(), mapper)
    return OptionStmt(
        key=_identifier(key, mapper),
        key_span=key.span,
        value=value,
        value_span=option_value.span,
        span=option_stmt.span,
    )


def ast_cst_to_config(ast_spec: cst.AstSpec, terminal_src: terminalsrc.TerminalSource) -> AstConfig:
    """Transform a parsed ``.fltkast`` CST into the pre-validation :class:`AstConfig` model.

    Every mapping problem is collected and the whole set is raised together as one
    :class:`AstConfigError`.
    """
    mapper = _Mapper(terminal_src=terminal_src)
    options: list[OptionStmt] = []
    rule_blocks: list[RuleBlock] = []

    for statement in ast_spec.children_statement():
        if (option_stmt := statement.maybe_option_stmt()) is not None:
            options.append(_option_stmt(option_stmt, mapper))
        elif (rule_config := statement.maybe_rule_config()) is not None:
            rule_blocks.append(_rule_block(rule_config, mapper))
        else:
            msg = f"unhandled statement CST node: {statement!r}"
            raise AssertionError(msg)

    if mapper.offenses:
        raise_offenses(mapper.offenses, terminal_src)
    return AstConfig(options=tuple(options), rule_blocks=tuple(rule_blocks))


def _parse_config(config_text: str) -> tuple[AstConfig, terminalsrc.TerminalSource]:
    """Parse non-empty ``.fltkast`` text, returning the model and the source it was read from.

    The source comes back because offense rendering re-attaches it to the stored spans.
    """
    terminals = terminalsrc.TerminalSource(config_text)
    parser = Parser(terminals)
    result = parser.apply__parse_ast_spec(0)
    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f".fltkast config parse failed:\n{error_msg}"
        raise AstConfigError(msg)

    return ast_cst_to_config(result.result, terminals), terminals


def parse_ast_config_text(config_text: str) -> AstConfig:
    """Parse ``.fltkast`` text into the pre-validation :class:`AstConfig` model.

    Empty or whitespace-only text yields an empty config — a sidecar that shapes nothing is
    the same as no sidecar at all.  A parse failure raises :class:`AstConfigError`.
    """
    if not config_text.strip():
        return AstConfig(options=(), rule_blocks=())
    return _parse_config(config_text)[0]


# --- The grammar surface validation matches against -------------------------------------


# The child kinds a label can carry.  A rule reference contributes the rule's name; the two
# terminal forms are distinguished because a labeled literal becomes a position or a
# presence flag rather than text, which several annotations care about.
TEXT_KIND = gshape.TEXT_KIND
LITERAL_KIND = "#literal"


@dataclasses.dataclass(frozen=True)
class LabelIndex:
    """One INCLUDE label's whole-rule multiplicity and the child kinds it can carry."""

    label: str
    count: ce.LabelCount
    kinds: frozenset[str]

    @property
    def arity(self) -> ce.ArityClass:
        return self.count.arity_class

    @property
    def rule_kinds(self) -> frozenset[str]:
        """The referenced rule names, dropping the two terminal sentinels."""
        return self.kinds - {TEXT_KIND, LITERAL_KIND}


@dataclasses.dataclass(frozen=True)
class RuleIndex:
    """The surface of one grammar rule that a sidecar statement can name."""

    name: str
    is_trivia: bool
    labels: frozenset[str]
    """Every ``Item.label`` of the rule, sub-expressions included."""

    shape: gshape.RuleShape
    """The node form the rule classifies as before any ``sum;``/``product;`` override."""

    alternative_count: int
    label_index: Mapping[str, LabelIndex]
    """Whole-rule view of the labels that become fields; suppressed labels are absent."""

    alternative_arities: tuple[Mapping[str, ce.LabelCount], ...]
    """Per-alternative label counts, in grammar order."""


@dataclasses.dataclass(frozen=True)
class UseSite:
    """One place a rule is referenced from, and the arity of the field it lands in."""

    rule_name: str
    label: str
    arity: ce.ArityClass


@dataclasses.dataclass(frozen=True)
class GrammarIndex:
    """Per-rule surfaces, keyed by rule name, plus where each rule is referenced from."""

    rules: Mapping[str, RuleIndex]
    use_sites: Mapping[str, tuple[UseSite, ...]]


def _term_kind(term: gsm.Term) -> str:
    if isinstance(term, gsm.Identifier):
        return term.value
    return LITERAL_KIND if isinstance(term, gsm.Literal) else TEXT_KIND


def _label_index(rule: gsm.Rule, arities: Sequence[Mapping[str, ce.LabelCount]]) -> dict[str, LabelIndex]:
    """Whole-rule counts and child kinds for every label that becomes a field."""
    counts = ce.combine_alternatives(arities)
    kinds: dict[str, set[str]] = {}
    for alternative in rule.alternatives:
        for label, terms in gshape.label_terms(alternative).items():
            kinds.setdefault(label, set()).update(_term_kind(term) for term in terms)
    return {
        label: LabelIndex(label=label, count=counts[label], kinds=frozenset(label_kinds))
        for label, label_kinds in kinds.items()
    }


def _build_rule_index(rule: gsm.Rule) -> RuleIndex:
    labels: set[str] = set()

    def visit(_idx: int, item: gsm.Item) -> None:
        if item.label is not None:
            labels.add(item.label)

    for alternative in rule.alternatives:
        gsm.for_each_item(alternative, visit)

    if rule.is_trivia_rule:
        # Trivia rules get no AST type, so a block naming one is rejected before any shape
        # question is asked; the analysis below would only waste a walk.
        return RuleIndex(
            name=rule.name,
            is_trivia=True,
            labels=frozenset(labels),
            shape=gshape.RuleShape.PRODUCT,
            alternative_count=len(rule.alternatives),
            label_index={},
            alternative_arities=(),
        )

    # One arity walk feeds the classification, the whole-rule label view and the
    # per-alternative view, so the three cannot drift apart.
    arities = gshape.rule_arities(rule)
    return RuleIndex(
        name=rule.name,
        is_trivia=False,
        labels=frozenset(labels),
        shape=gshape.classify_rule(rule, arities),
        alternative_count=len(rule.alternatives),
        label_index=_label_index(rule, arities),
        alternative_arities=tuple(arities),
    )


def build_grammar_index(grammar: gsm.Grammar) -> GrammarIndex:
    """Index ``grammar``'s rules for sidecar validation.

    ``grammar`` should be the one the AST model is built from — INLINE-expanded and
    trivia-classified — so that a block naming a trivia rule is diagnosed as such and the
    labels, shapes and arities are the ones the model will see.
    """
    rules = {rule.name: _build_rule_index(rule) for rule in grammar.rules}

    use_sites: dict[str, list[UseSite]] = {}
    for rule_index in rules.values():
        for info in rule_index.label_index.values():
            for referenced in sorted(info.rule_kinds):
                use_sites.setdefault(referenced, []).append(
                    UseSite(rule_name=rule_index.name, label=info.label, arity=info.arity)
                )
    return GrammarIndex(rules=rules, use_sites={name: tuple(sites) for name, sites in use_sites.items()})


# --- The resolved config ----------------------------------------------------------------


class Backend(enum.Enum):
    """A code-generation target.  Some sidecar entries are required per generated backend."""

    PYTHON = "python"
    RUST = "rust"


ALL_BACKENDS: frozenset[Backend] = frozenset(Backend)

# Scalar coercions with a fixed cross-backend mapping.  ``uuid`` and ``decimal`` need an
# opt-in cargo feature on the Rust side; the Python side needs only the stdlib.
INTEGER_SCALAR_TYPES: frozenset[str] = frozenset({"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64"})

FLOAT_SCALAR_TYPES: frozenset[str] = frozenset({"f32", "f64"})

WIDE_SCALAR_TYPES: frozenset[str] = frozenset({"uuid", "decimal"})
"""Builtins with no width: the two whose Rust support sits behind a cargo feature."""

# Every builtin is spelled in exactly one of the three sets above, so a new width added to one
# of them reaches the width-checked parse helpers and the per-backend type tables at once.
BUILTIN_SCALAR_TYPES: frozenset[str] = INTEGER_SCALAR_TYPES | FLOAT_SCALAR_TYPES | WIDE_SCALAR_TYPES

CST_OPTION = "cst"

# Members a generated node can carry, so no field may be renamed to one.  ``value`` and
# ``cst`` appear only on some node forms, but a rename is checked against the whole union:
# one rule to teach, and no dependence on a shape the sidecar can itself change.
RESERVED_MEMBER_NAMES: frozenset[str] = frozenset({"span", "text", "value", CST_OPTION, "from_cst", "to_cst"})

_CUSTOM_TYPE_KEYS: Mapping[Backend, tuple[str, ...]] = {
    Backend.RUST: ("rust_type", "rust_parse", "rust_unparse"),
    Backend.PYTHON: ("py_type", "py_parse", "py_unparse"),
}

_CUSTOM_RULE_KEYS: Mapping[Backend, tuple[str, ...]] = {
    Backend.RUST: ("rust",),
    Backend.PYTHON: ("python",),
}


@dataclasses.dataclass(frozen=True)
class BuiltinScalar:
    """``type: i64;`` — a coercion with a fixed mapping on both backends."""

    name: str


@dataclasses.dataclass(frozen=True)
class CustomScalar:
    """``type: custom(...);`` — user-supplied type and parse/unparse paths, per backend.

    An entry is ``None`` when the sidecar omits it, which validation permits only for a
    backend that is not being generated.
    """

    entries: Mapping[str, str]

    def entry(self, key: str) -> str | None:
        return self.entries.get(key)


ScalarCoercion: typing.TypeAlias = BuiltinScalar | CustomScalar


@dataclasses.dataclass(frozen=True)
class CustomRule:
    """``custom(rust: "...", python: "...");`` — the whole-rule escape hatch's target types."""

    entries: Mapping[str, str]

    def entry(self, key: str) -> str | None:
        return self.entries.get(key)


@dataclasses.dataclass(frozen=True)
class Fold:
    """A resolved ``fold_left:`` / ``fold_right:`` statement."""

    direction: FoldDirection
    op_label: str


class Shape(enum.Enum):
    """A forced multi-alternative classification."""

    SUM = "sum"
    PRODUCT = "product"


@dataclasses.dataclass(frozen=True)
class ResolvedRule:
    """Everything one ``rule`` block says, in the form the AST model consumes."""

    rule_name: str
    coercion: ScalarCoercion | None = None
    bool_truthy: str | None = None
    transparent: bool = False
    text_from: str | None = None
    key: str | None = None
    fold: Fold | None = None
    flatten: bool = False
    custom: CustomRule | None = None
    type_name: str | None = None
    """The ``name:`` override for the rule's generated type."""

    variant_names: Mapping[str, str] = dataclasses.field(default_factory=dict)
    """Computed variant name -> replacement."""

    field_names: Mapping[str, str] = dataclasses.field(default_factory=dict)
    """Label -> field-name replacement."""

    shape: Shape | None = None


@dataclasses.dataclass(frozen=True)
class ResolvedAstConfig:
    """A validated sidecar: the configured rules plus the global options."""

    rules: Mapping[str, ResolvedRule] = dataclasses.field(default_factory=dict)
    cst_backpointers: bool = False
    """``option cst = true;`` — every node gains a CST back-pointer field."""

    def for_rule(self, rule_name: str) -> ResolvedRule:
        """The rule's config, or an all-default one when the sidecar does not mention it."""
        configured = self.rules.get(rule_name)
        return configured if configured is not None else ResolvedRule(rule_name=rule_name)


# --- Validation and resolution ----------------------------------------------------------

# Statement forms a rule block may carry at most once.  ``VariantStmt`` and ``FieldStmt``
# are excluded: they repeat, keyed by selector and by label.
_SINGULAR_STATEMENTS: Mapping[type, str] = {
    TypeStmt: "type:",
    BoolStmt: "bool:",
    TransparentStmt: "transparent;",
    TextFromStmt: "text_from:",
    KeyStmt: "key:",
    FoldStmt: "fold_left:/fold_right:",
    FlattenStmt: "flatten;",
    CustomStmt: "custom(...);",
    NameStmt: "name:",
    SumStmt: "sum;",
    ProductStmt: "product;",
}

# Pairs that cannot both appear in one rule block.  ``custom(...)`` replaces the rule
# outright, so it is checked separately against everything else.
_CONFLICTING_STATEMENTS: tuple[tuple[type, type], ...] = (
    (TypeStmt, BoolStmt),
    (TypeStmt, FoldStmt),
    (TypeStmt, FlattenStmt),
    (TransparentStmt, FlattenStmt),
    # An erased rule's use sites carry its payload, so a keyed collection of it would hold
    # values with no key field to index them by.
    (TransparentStmt, KeyStmt),
    # A `key:` acts only at a collection use site, and `flatten;` refuses every one of those,
    # so the two together leave a `key:` that keys nothing anywhere.
    (FlattenStmt, KeyStmt),
    (SumStmt, ProductStmt),
)


_Statement = typing.TypeVar("_Statement", bound="RuleStatement")


def _statement_of(statements: Mapping[type, RuleStatement], kind: type[_Statement]) -> _Statement | None:
    """The block's statement of ``kind``, typed as that form."""
    statement = statements.get(kind)
    if statement is None:
        return None
    assert isinstance(statement, kind)
    return statement


def _statement_span(block: RuleBlock, kind: type) -> span_protocol.SpanProtocol:
    """The span of ``block``'s first statement of ``kind``, or the block's own span."""
    for statement in block.statements:
        if type(statement) is kind:
            return statement.span
    return block.span


def _find_cycle(adjacency: Mapping[str, frozenset[str]]) -> list[str] | None:
    """Any cycle in ``adjacency``, as the rules around it with the entry rule repeated."""
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = _VISITING
        path.append(node)
        for target in sorted(adjacency.get(node, frozenset())):
            if state.get(target) == _VISITING:
                return [*path[path.index(target) :], target]
            if target in adjacency and target not in state:
                found = visit(target)
                if found is not None:
                    return found
        path.pop()
        state[node] = _VISITED
        return None

    for node in adjacency:
        if node not in state:
            found = visit(node)
            if found is not None:
                return found
    return None


_VISITING = 1
_VISITED = 2

# A `bool:` rule maps one variant to true and one to false; a fold rule carries an operator
# label and an operand label; a shape override needs something to choose between.
_BOOLEAN_VARIANTS = 2
_FOLD_LABELS = 2
_MIN_ALTERNATIVES = gshape.MIN_ALTERNATIVES

# Sentinels for what a `key:` field resolves to, none of which a builtin name can collide
# with.  A node-typed field is ``None``: it is the one case a `transparent;` hint fixes.
_TEXT_KEY = "#text"
_LITERAL_KEY = "#literal-position"
_CUSTOM_KEY = "#custom-type"

# A Python path needs at least a module and an attribute for the generated module to import.
_MIN_PATH_PARTS = 2

# The ``custom(...)`` entries holding a Python dotted path; the Rust entries use ``::``.
_PYTHON_PATH_KEYS: frozenset[str] = frozenset({"python", "py_type", "py_parse", "py_unparse"})


def name_problem(name: str) -> str | None:
    """Why ``name`` cannot be a generated identifier on both backends, or ``None``.

    The single statement of the rules: the sidecar validator checks a rename against them
    and the AST model checks a grammar label, so the two cannot accept different names.
    """
    if name.startswith("__"):
        return "names starting with '__' are subject to Python private name mangling"
    if keyword.iskeyword(name):
        return "it is a Python keyword"
    if name in ce.RUST_UNRAWABLE_KEYWORDS:
        return "it is a Rust keyword that cannot be written as a raw identifier"
    return None


def _python_path_problem(path: str) -> str | None:
    """Why ``path`` cannot be the dotted path of a Python type or function, or ``None``.

    The generated module imports everything before the last component and names the whole
    path, so the path needs a module part and every component must be an identifier.  A
    path into a nested class is indistinguishable here and fails at import instead.
    """
    parts = path.split(".")
    if len(parts) < _MIN_PATH_PARTS:
        return "it must name a module and an attribute, as in 'pkg.module.Name', so the module can be imported"
    if not all(part.isidentifier() and not keyword.iskeyword(part) for part in parts):
        return "every dot-separated component must be a Python identifier"
    return None


class _Resolver:
    """Validates one parsed sidecar against a grammar index and resolves it.

    Every problem is appended to ``offenses`` and resolution carries on, so one run reports
    everything wrong with the sidecar rather than the first thing.
    """

    def __init__(self, config: AstConfig, index: GrammarIndex, backends: Collection[Backend]) -> None:
        self.config = config
        self.index = index
        self.backends = tuple(backends)
        self.offenses: list[tuple[span_protocol.SpanProtocol, str]] = []

    def error(self, span: span_protocol.SpanProtocol, message: str) -> None:
        self.offenses.append((span, message))

    def resolve(self) -> ResolvedAstConfig:
        cst_backpointers = self.resolve_options()
        rules: dict[str, ResolvedRule] = {}
        blocks: dict[str, RuleBlock] = {}
        for block in self.config.rule_blocks:
            if block.rule_name in rules:
                self.error(block.rule_name_span, f"duplicate `rule {block.rule_name}` block")
                continue
            rule_index = self.index.rules.get(block.rule_name)
            if rule_index is None:
                self.error(block.rule_name_span, f"unknown grammar rule {block.rule_name!r}")
                continue
            if rule_index.is_trivia:
                self.error(
                    block.rule_name_span,
                    f"rule {block.rule_name!r} is a trivia rule, which gets no AST type to shape",
                )
                continue
            rules[block.rule_name] = self.resolve_block(block, rule_index)
            blocks[block.rule_name] = block
        resolved = ResolvedAstConfig(rules=rules, cst_backpointers=cst_backpointers)
        self.check_across_rules(resolved, blocks)
        return resolved

    def resolve_options(self) -> bool:
        cst_backpointers = False
        seen: set[str] = set()
        for option in self.config.options:
            if option.key in seen:
                self.error(option.key_span, f"duplicate `option {option.key}` statement")
                continue
            seen.add(option.key)
            if option.key != CST_OPTION:
                self.error(
                    option.key_span,
                    f"unknown option {option.key!r}; the only option is `option {CST_OPTION} = true|false;`",
                )
                continue
            if not isinstance(option.value, bool):
                self.error(option.value_span, f"option {CST_OPTION!r} takes `true` or `false`, not a string")
                continue
            cst_backpointers = option.value
        return cst_backpointers

    def resolve_block(self, block: RuleBlock, rule_index: RuleIndex) -> ResolvedRule:
        statements = self.singular_statements(block)
        self.check_conflicts(block, statements)

        type_stmt = _statement_of(statements, TypeStmt)
        custom_stmt = _statement_of(statements, CustomStmt)
        bool_stmt = _statement_of(statements, BoolStmt)
        text_from_stmt = _statement_of(statements, TextFromStmt)
        key_stmt = _statement_of(statements, KeyStmt)
        fold_stmt = _statement_of(statements, FoldStmt)
        name_stmt = _statement_of(statements, NameStmt)

        if bool_stmt is not None:
            self.check_label(block, rule_index, bool_stmt.truthy_label, bool_stmt.label_span, "bool:")
        if text_from_stmt is not None:
            self.check_label(block, rule_index, text_from_stmt.label, text_from_stmt.label_span, "text_from:")
        if key_stmt is not None:
            self.check_label(block, rule_index, key_stmt.label, key_stmt.label_span, "key:")
        if fold_stmt is not None:
            self.check_label(block, rule_index, fold_stmt.op_label, fold_stmt.op_span, "the fold operator")
        if name_stmt is not None:
            self.check_name(name_stmt.new_name, name_stmt.name_span, "type name")

        self.check_shapes(block, rule_index, statements)

        return ResolvedRule(
            rule_name=block.rule_name,
            coercion=None if type_stmt is None else self.resolve_type_spec(block, type_stmt.spec),
            bool_truthy=None if bool_stmt is None else bool_stmt.truthy_label,
            transparent=TransparentStmt in statements,
            text_from=None if text_from_stmt is None else text_from_stmt.label,
            key=None if key_stmt is None else key_stmt.label,
            fold=None if fold_stmt is None else Fold(direction=fold_stmt.direction, op_label=fold_stmt.op_label),
            flatten=FlattenStmt in statements,
            custom=None if custom_stmt is None else self.resolve_custom_rule(block, custom_stmt),
            type_name=None if name_stmt is None else name_stmt.new_name,
            variant_names=self.resolve_variants(block),
            field_names=self.resolve_fields(block, rule_index),
            shape=self.resolve_shape(statements),
        )

    def singular_statements(self, block: RuleBlock) -> dict[type, RuleStatement]:
        """The at-most-once statements of ``block``, keeping the first of any duplicate set."""
        first: dict[type, RuleStatement] = {}
        for statement in block.statements:
            kind = _SINGULAR_STATEMENTS.get(type(statement))
            if kind is None:
                continue
            if type(statement) in first:
                self.error(statement.span, f"duplicate `{kind}` statement in `rule {block.rule_name}`")
                continue
            first[type(statement)] = statement
        return first

    def check_conflicts(self, block: RuleBlock, statements: Mapping[type, RuleStatement]) -> None:
        if CustomStmt in statements:
            for statement, spelling in self.other_statements(block, statements):
                self.error(
                    statement.span,
                    f"`{spelling}` conflicts with `custom(...)` in `rule {block.rule_name}`: a custom "
                    f"rule gets no generated type to shape",
                )
        for left, right in _CONFLICTING_STATEMENTS:
            if left in statements and right in statements:
                self.error(
                    statements[right].span,
                    f"`{_SINGULAR_STATEMENTS[right]}` conflicts with `{_SINGULAR_STATEMENTS[left]}` in "
                    f"`rule {block.rule_name}`",
                )

    @staticmethod
    def other_statements(block: RuleBlock, statements: Mapping[type, RuleStatement]) -> list[tuple[RuleStatement, str]]:
        """Every statement of ``block`` but ``custom(...)``, each with how it is spelled.

        The repeatable ``variant``/``field`` forms are absent from the singular map, so they
        are collected from the block itself rather than left without a diagnostic.
        """
        collected: list[tuple[RuleStatement, str]] = [
            (statement, _SINGULAR_STATEMENTS[kind]) for kind, statement in statements.items() if kind is not CustomStmt
        ]
        for statement in block.statements:
            if isinstance(statement, VariantStmt):
                collected.append((statement, f"variant {statement.selector}:"))
            elif isinstance(statement, FieldStmt):
                collected.append((statement, f"field {statement.label}"))
        return collected

    def check_label(
        self, block: RuleBlock, rule_index: RuleIndex, label: str, span: span_protocol.SpanProtocol, statement: str
    ) -> bool:
        if label in rule_index.labels:
            return True
        self.error(span, f"`{statement}` names {label!r}, but rule {block.rule_name!r} has no item with that label")
        return False

    def check_name(self, name: str, span: span_protocol.SpanProtocol, description: str) -> None:
        problem = name_problem(name)
        if problem is not None:
            self.error(span, f"{name!r} cannot be a generated {description} because {problem}")

    def resolve_type_spec(self, block: RuleBlock, spec: TypeSpec) -> ScalarCoercion | None:
        if isinstance(spec, BuiltinTypeSpec):
            if spec.name in BUILTIN_SCALAR_TYPES:
                return BuiltinScalar(name=spec.name)
            known = ", ".join(sorted(BUILTIN_SCALAR_TYPES))
            self.error(spec.span, f"unknown builtin type {spec.name!r}; known builtins are: {known}")
            return None
        entries = self.resolve_args(block, spec.args, _CUSTOM_TYPE_KEYS, spec.span, "type: custom(...)")
        return CustomScalar(entries=entries)

    def resolve_custom_rule(self, block: RuleBlock, statement: CustomStmt) -> CustomRule:
        entries = self.resolve_args(block, statement.args, _CUSTOM_RULE_KEYS, statement.span, "custom(...)")
        return CustomRule(entries=entries)

    def resolve_args(
        self,
        block: RuleBlock,
        args: Iterable[CustomArg],
        keys_by_backend: Mapping[Backend, tuple[str, ...]],
        span: span_protocol.SpanProtocol,
        statement: str,
    ) -> dict[str, str]:
        """Collect a ``custom(...)`` argument list, checking its keys and its completeness."""
        known = {key for keys in keys_by_backend.values() for key in keys}
        entries: dict[str, str] = {}
        for arg in args:
            if arg.key not in known:
                self.error(
                    arg.span,
                    f"unknown `{statement}` entry {arg.key!r} in `rule {block.rule_name}`; "
                    f"known entries are: {', '.join(sorted(known))}",
                )
                continue
            if arg.key in entries:
                self.error(arg.span, f"duplicate `{statement}` entry {arg.key!r} in `rule {block.rule_name}`")
                continue
            if arg.key in _PYTHON_PATH_KEYS and (problem := _python_path_problem(arg.value)) is not None:
                # Recorded anyway: the entry is present, so the completeness check below must
                # not pile a "missing entry" complaint onto the same typo.
                self.error(
                    arg.span,
                    f"`{statement}` entry {arg.key!r} in `rule {block.rule_name}` is not a usable "
                    f"Python path: {problem}",
                )
            entries[arg.key] = arg.value

        for backend in self.backends:
            missing = [key for key in keys_by_backend[backend] if key not in entries]
            if missing:
                self.error(
                    span,
                    f"`{statement}` in `rule {block.rule_name}` is missing the {backend.value} "
                    f"entries {', '.join(missing)}, which generating that backend requires",
                )
        return entries

    def resolve_variants(self, block: RuleBlock) -> dict[str, str]:
        renames: dict[str, str] = {}
        for statement in block.statements:
            if not isinstance(statement, VariantStmt):
                continue
            if statement.selector in renames:
                self.error(
                    statement.selector_span,
                    f"duplicate `variant {statement.selector}:` statement in `rule {block.rule_name}`",
                )
                continue
            self.check_name(statement.new_name, statement.name_span, "variant name")
            renames[statement.selector] = statement.new_name
        return renames

    def resolve_fields(self, block: RuleBlock, rule_index: RuleIndex) -> dict[str, str]:
        renames: dict[str, str] = {}
        seen: set[str] = set()
        for statement in block.statements:
            if not isinstance(statement, FieldStmt):
                continue
            if statement.label in seen:
                self.error(
                    statement.label_span, f"duplicate `field {statement.label}` block in `rule {block.rule_name}`"
                )
                continue
            seen.add(statement.label)
            self.check_label(block, rule_index, statement.label, statement.label_span, "field")
            for index, rename in enumerate(statement.statements):
                if index > 0:
                    self.error(
                        rename.span,
                        f"duplicate `name:` statement in `field {statement.label}` of `rule {block.rule_name}`",
                    )
                    continue
                self.check_field_name(rename.new_name, rename.name_span)
                renames[statement.label] = rename.new_name
        return renames

    def check_field_name(self, name: str, span: span_protocol.SpanProtocol) -> None:
        if name in RESERVED_MEMBER_NAMES:
            self.error(span, f"{name!r} cannot be a generated field name because generated nodes carry that member")
            return
        self.check_name(name, span, "field name")

    def resolve_shape(self, statements: Mapping[type, RuleStatement]) -> Shape | None:
        if SumStmt in statements:
            return Shape.SUM
        if ProductStmt in statements:
            return Shape.PRODUCT
        return None

    # --- Shape compatibility ------------------------------------------------------------

    def check_shapes(self, block: RuleBlock, rule_index: RuleIndex, statements: Mapping[type, RuleStatement]) -> None:
        """Reject every annotation that does not apply to the shape its rule classifies as."""
        if CustomStmt in statements:
            # A custom rule gets no generated type, so nothing else in the block applies; the
            # conflict is already reported against each statement.
            return

        form = self.effective_shape(rule_index, self.resolve_shape(statements))
        self.check_shape_override(block, rule_index, statements)
        self.check_rename_placement(block, form, statements)

        if (type_stmt := _statement_of(statements, TypeStmt)) is not None:
            self.require_terminal_only(block, rule_index, type_stmt.span, "type:")
        if (text_from_stmt := _statement_of(statements, TextFromStmt)) is not None:
            self.check_text_from(block, rule_index, text_from_stmt)
        if (bool_stmt := _statement_of(statements, BoolStmt)) is not None:
            self.check_bool(block, rule_index, bool_stmt)
        if (transparent_stmt := _statement_of(statements, TransparentStmt)) is not None:
            self.check_transparent(block, rule_index, form, transparent_stmt, fold=FoldStmt in statements)
        if (key_stmt := _statement_of(statements, KeyStmt)) is not None:
            self.check_key(block, rule_index, form, key_stmt)
        if (fold_stmt := _statement_of(statements, FoldStmt)) is not None:
            self.check_fold(block, rule_index, fold_stmt)
        if (flatten_stmt := _statement_of(statements, FlattenStmt)) is not None:
            self.check_flatten(block, form, flatten_stmt)

    def effective_shape(self, rule_index: RuleIndex, shape: Shape | None) -> gshape.RuleShape:
        """The rule's node form, with a ``sum;``/``product;`` override applied where it applies.

        The override only chooses between the two multi-alternative forms: enum-shaped and
        terminal-only rules classify ahead of that choice and are unaffected.
        """
        multi = (gshape.RuleShape.SUM, gshape.RuleShape.PRODUCT)
        if shape is None or rule_index.shape not in multi:
            return rule_index.shape
        return gshape.RuleShape.SUM if shape is Shape.SUM else gshape.RuleShape.PRODUCT

    def require_terminal_only(
        self, block: RuleBlock, rule_index: RuleIndex, span: span_protocol.SpanProtocol, statement: str
    ) -> bool:
        if rule_index.shape is gshape.RuleShape.TERMINAL:
            return True
        self.error(
            span,
            f"`{statement}` applies only to a terminal-only rule (one whose children are all "
            f"terminals), but rule {block.rule_name!r} is {rule_index.shape.value}",
        )
        return False

    def field_label(
        self, block: RuleBlock, rule_index: RuleIndex, label: str, span: span_protocol.SpanProtocol, statement: str
    ) -> LabelIndex | None:
        """The label's field information, or ``None`` with the reason reported."""
        info = rule_index.label_index.get(label)
        if info is not None:
            return info
        if label in rule_index.labels:
            self.error(
                span,
                f"`{statement}` names {label!r}, which is suppressed in rule {block.rule_name!r} "
                f"and so contributes no child to read",
            )
        return None

    def check_text_from(self, block: RuleBlock, rule_index: RuleIndex, statement: TextFromStmt) -> None:
        if not self.require_terminal_only(block, rule_index, statement.span, "text_from:"):
            return
        info = self.field_label(block, rule_index, statement.label, statement.label_span, "text_from:")
        if info is None or info.arity is ce.ArityClass.REQUIRED_SINGLE:
            return
        self.error(
            statement.label_span,
            f"`text_from:` needs a label that occurs exactly once, but {statement.label!r} in rule "
            f"{block.rule_name!r} is {info.arity.value}",
        )

    def check_bool(self, block: RuleBlock, rule_index: RuleIndex, statement: BoolStmt) -> None:
        if rule_index.shape is not gshape.RuleShape.ENUM:
            self.error(
                statement.span,
                f"`bool:` applies only to an enum-shaped rule (every alternative a single labeled "
                f"literal), but rule {block.rule_name!r} is {rule_index.shape.value}",
            )
        elif len(rule_index.labels) != _BOOLEAN_VARIANTS:
            # Labels, not alternatives: alternatives of an enum-shaped rule sharing a label are
            # equivalent spellings of one variant, so `yes:"yes" | yes:"y" | no:"no"` is the
            # two-valued rule `bool:` wants and `t:"true" | t:"yes"` is a one-valued one.
            self.error(
                statement.span,
                f"`bool:` needs a rule with exactly two variants — one true, one false — but rule "
                f"{block.rule_name!r} has {len(rule_index.labels)} "
                f"({', '.join(sorted(rule_index.labels))})",
            )

    def check_transparent(
        self,
        block: RuleBlock,
        rule_index: RuleIndex,
        form: gshape.RuleShape,
        statement: TransparentStmt,
        *,
        fold: bool,
    ) -> None:
        if fold:
            self.error(
                statement.span,
                f"`transparent;` cannot apply to the fold rule {block.rule_name!r}: a fold produces "
                f"an operand/binary pair, which has no single payload to erase to",
            )
            return
        if form in (gshape.RuleShape.TERMINAL, gshape.RuleShape.ENUM):
            return
        if form is gshape.RuleShape.SUM:
            self.error(
                statement.span,
                f"`transparent;` applies to terminal-only, enum-shaped and single-field product "
                f"rules, but rule {block.rule_name!r} is a sum, whose variants have no common payload",
            )
            return
        fields = sorted(rule_index.label_index)
        if len(fields) != 1:
            self.error(
                statement.span,
                f"`transparent;` needs a product rule with exactly one field, but rule "
                f"{block.rule_name!r} has {len(fields)}: {', '.join(fields) or '(none)'}",
            )

    def check_key(self, block: RuleBlock, rule_index: RuleIndex, form: gshape.RuleShape, statement: KeyStmt) -> None:
        if form is not gshape.RuleShape.PRODUCT:
            self.error(
                statement.span,
                f"`key:` applies only to a product rule (the only form with named fields), but rule "
                f"{block.rule_name!r} is {form.value}",
            )
            return
        info = self.field_label(block, rule_index, statement.label, statement.label_span, "key:")
        if info is None or info.arity is ce.ArityClass.REQUIRED_SINGLE:
            return
        self.error(
            statement.label_span,
            f"`key:` needs a field that occurs exactly once, but {statement.label!r} in rule "
            f"{block.rule_name!r} is {info.arity.value}",
        )

    def check_fold(self, block: RuleBlock, rule_index: RuleIndex, statement: FoldStmt) -> None:
        if rule_index.alternative_count != 1:
            self.error(
                statement.span,
                f"`fold_left:`/`fold_right:` needs a single-alternative rule of the form "
                f"`operand , (op , operand)*`, but rule {block.rule_name!r} has "
                f"{rule_index.alternative_count} alternatives",
            )
            return
        counts = rule_index.alternative_arities[0]
        if statement.op_label not in counts:
            self.field_label(block, rule_index, statement.op_label, statement.op_span, "the fold operator")
            return
        if len(counts) != _FOLD_LABELS:
            self.error(
                statement.span,
                f"a fold rule carries exactly two labels — the operator and the operand — but rule "
                f"{block.rule_name!r} carries {len(counts)}: {', '.join(sorted(counts))}",
            )
            return
        (operand_label,) = (label for label in counts if label != statement.op_label)
        if counts[statement.op_label].arity_class is not ce.ArityClass.COLLECTION:
            self.error(
                statement.op_span,
                f"the fold operator {statement.op_label!r} must be repeatable, as in "
                f"`operand , ({statement.op_label}:op , operand)*`, but it occurs at most once in rule "
                f"{block.rule_name!r}",
            )
        operand = counts[operand_label]
        if operand.min < 1 or operand.arity_class is not ce.ArityClass.COLLECTION:
            self.error(
                statement.span,
                f"the fold operand {operand_label!r} must occur one or more times, as in "
                f"`{operand_label}:operand , ({statement.op_label}:op , {operand_label}:operand)*`, "
                f"but it is {operand.arity_class.value} in rule {block.rule_name!r}",
            )

    def check_flatten(self, block: RuleBlock, form: gshape.RuleShape, statement: FlattenStmt) -> None:
        if form is not gshape.RuleShape.PRODUCT:
            self.error(
                statement.span,
                f"`flatten;` applies only to a product rule whose fields can be hoisted into its "
                f"parent, but rule {block.rule_name!r} is {form.value}",
            )
            return
        for site in self.index.use_sites.get(block.rule_name, ()):
            if site.arity is ce.ArityClass.COLLECTION:
                self.error(
                    statement.span,
                    f"`flatten;` cannot apply to rule {block.rule_name!r}: it is used as a collection "
                    f"at label {site.label!r} of rule {site.rule_name!r}, and repeated hoisted fields "
                    f"have nowhere to go",
                )
                return

    def check_rename_placement(
        self, block: RuleBlock, form: gshape.RuleShape, statements: Mapping[type, RuleStatement]
    ) -> None:
        """Reject a ``variant``/``field`` rename on a shape that has nothing of that kind.

        Only sums, enum-shaped rules and folds have variants; only products and the payload
        classes of sums have fields.  Anywhere else the rename would apply to nothing, and a
        statement that validates but does nothing is the failure mode this layer exists to
        prevent.  A ``bool:`` rule is the enum-shaped exception: its value is a plain boolean,
        so its alternatives produce no variant to name.
        """
        variant_forms = (gshape.RuleShape.SUM, gshape.RuleShape.ENUM)
        fieldless_forms = (gshape.RuleShape.TERMINAL, gshape.RuleShape.ENUM)
        is_fold = FoldStmt in statements
        is_bool = BoolStmt in statements
        for statement in block.statements:
            if isinstance(statement, VariantStmt) and not is_fold and (is_bool or form not in variant_forms):
                described = "a `bool:` rule, whose value is a plain boolean" if is_bool else form.value
                self.error(
                    statement.selector_span,
                    f"`variant {statement.selector}:` renames a variant of a sum, an enum-shaped rule "
                    f"or a fold, but rule {block.rule_name!r} is {described}",
                )
            elif isinstance(statement, FieldStmt) and form in fieldless_forms:
                self.error(
                    statement.label_span,
                    f"`field {statement.label}` renames a field, but rule {block.rule_name!r} is "
                    f"{form.value} and has no fields to rename",
                )

    def check_shape_override(
        self, block: RuleBlock, rule_index: RuleIndex, statements: Mapping[type, RuleStatement]
    ) -> None:
        statement = statements.get(SumStmt) or statements.get(ProductStmt)
        if statement is None:
            return
        spelling = "sum;" if isinstance(statement, SumStmt) else "product;"
        if rule_index.alternative_count < _MIN_ALTERNATIVES:
            self.error(
                statement.span,
                f"`{spelling}` chooses between the two multi-alternative forms, but rule "
                f"{block.rule_name!r} has a single alternative",
            )
        elif rule_index.shape is gshape.RuleShape.ENUM:
            self.error(
                statement.span,
                f"`{spelling}` cannot apply to enum-shaped rule {block.rule_name!r}, whose "
                f"alternatives are all single literals",
            )

    # --- Checks that span more than one rule ---------------------------------------------

    def check_across_rules(self, resolved: ResolvedAstConfig, blocks: Mapping[str, RuleBlock]) -> None:
        for rule_name, block in blocks.items():
            if resolved.rules[rule_name].key is not None:
                self.check_key_type(rule_name, block, resolved)
        self.check_cycles(resolved, blocks, TransparentStmt, "transparent;", transparent=True)
        self.check_cycles(resolved, blocks, FlattenStmt, "flatten;", transparent=False)

    def check_key_type(self, rule_name: str, block: RuleBlock, resolved: ResolvedAstConfig) -> None:
        """A map key must come out as a string or an integer once the element rule is resolved."""
        label = resolved.rules[rule_name].key
        assert label is not None
        info = self.index.rules[rule_name].label_index.get(label)
        if info is None:
            return
        statement = _statement_span(block, KeyStmt)
        allowed = f"a map key must be a string or one of {', '.join(sorted(INTEGER_SCALAR_TYPES))}"
        key_type = self.key_type(info, resolved, set())
        if key_type == _TEXT_KEY or key_type in INTEGER_SCALAR_TYPES:
            return
        if key_type == _LITERAL_KEY:
            self.error(
                statement,
                f"the `key:` field {label!r} of rule {rule_name!r} carries a literal's position "
                f"rather than text — a literal's text is a grammar constant, so every element "
                f"would share one key; key on a labeled regex or on a rule that resolves to a "
                f"string or an integer",
            )
            return
        if key_type == _CUSTOM_KEY:
            self.error(
                statement,
                f"the `key:` field {label!r} of rule {rule_name!r} resolves to a `type: custom(...)` "
                f"type, which cannot key a map; {allowed}",
            )
            return
        if key_type is None:
            self.error(
                statement,
                f"the `key:` field {label!r} of rule {rule_name!r} has a node type, which cannot key "
                f"a map; mark the referenced rule `transparent;` (optionally with a `type:` coercion) "
                f"so the key resolves to a string or an integer",
            )
            return
        self.error(
            statement,
            f"the `key:` field {label!r} of rule {rule_name!r} resolves to {key_type!r}; {allowed}",
        )

    def key_type(self, info: LabelIndex, resolved: ResolvedAstConfig, seen: set[str]) -> str | None:
        """What a field resolves to: a sentinel, a builtin name, or ``None`` for a node type."""
        if info.kinds == frozenset({LITERAL_KIND}):
            return _LITERAL_KEY
        if info.kinds <= {TEXT_KIND, LITERAL_KIND}:
            # A label mixing a literal with a regex carries text: the literal's own text is
            # recoverable from its span, so the field is a string either way.
            return _TEXT_KEY
        referenced = info.rule_kinds
        if len(referenced) != 1 or len(info.kinds) != 1:
            return None
        (rule_name,) = referenced
        if rule_name in seen or rule_name not in self.index.rules:
            return None
        seen.add(rule_name)

        rule = resolved.for_rule(rule_name)
        if isinstance(rule.coercion, BuiltinScalar):
            return rule.coercion.name if rule.transparent else None
        if isinstance(rule.coercion, CustomScalar):
            return _CUSTOM_KEY if rule.transparent else None
        if not rule.transparent:
            return None

        rule_index = self.index.rules[rule_name]
        if rule_index.shape is gshape.RuleShape.TERMINAL:
            return _TEXT_KEY
        if rule_index.shape is not gshape.RuleShape.PRODUCT or len(rule_index.label_index) != 1:
            return None
        (payload,) = rule_index.label_index.values()
        return self.key_type(payload, resolved, seen)

    def check_cycles(
        self,
        resolved: ResolvedAstConfig,
        blocks: Mapping[str, RuleBlock],
        statement_type: type,
        spelling: str,
        *,
        transparent: bool,
    ) -> None:
        """Reject an erasure that never bottoms out: a rule reachable from itself through it.

        Members keep the sidecar's own block order so the cycle a diagnostic names is the
        same one on every run.
        """
        members = [
            name
            for name, rule in resolved.rules.items()
            if (rule.transparent if transparent else rule.flatten) and name in self.index.rules
        ]
        erased = frozenset(members)
        adjacency = {
            name: frozenset(
                target
                for info in self.index.rules[name].label_index.values()
                for target in info.rule_kinds
                if target in erased
            )
            for name in members
        }
        cycle = _find_cycle(adjacency)
        if cycle is None:
            return
        head = cycle[0]
        self.error(
            _statement_span(blocks[head], statement_type),
            f"`{spelling}` forms a cycle: {' -> '.join(cycle)}; at least one rule in the cycle must "
            f"keep a type of its own",
        )


def resolve_ast_config(
    config: AstConfig,
    index: GrammarIndex,
    terminals: terminalsrc.TerminalSource,
    backends: Collection[Backend] = ALL_BACKENDS,
) -> ResolvedAstConfig:
    """Validate a parsed :class:`AstConfig` against ``index`` and resolve it.

    ``backends`` names the code-generation targets: a ``custom(...)`` list must carry the
    entries of every backend being generated, and may omit the others.  Every offense is
    collected and raised together as one :class:`AstConfigError`.
    """
    resolver = _Resolver(config, index, backends)
    resolved = resolver.resolve()
    if resolver.offenses:
        raise_offenses(resolver.offenses, terminals)
    return resolved


def load_ast_config(
    config_text: str,
    grammar: gsm.Grammar,
    backends: Collection[Backend] = ALL_BACKENDS,
) -> ResolvedAstConfig:
    """Parse, map, validate and resolve ``.fltkast`` text against ``grammar`` in one call.

    Empty or whitespace-only text short-circuits to an empty resolved config — a sidecar
    that shapes nothing is the same as no sidecar.  A parse failure or any validation
    offense raises :class:`AstConfigError`.
    """
    if not config_text.strip():
        return ResolvedAstConfig()

    config, terminals = _parse_config(config_text)
    return resolve_ast_config(config, build_grammar_index(grammar), terminals, backends)
