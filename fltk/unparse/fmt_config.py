"""Formatter configuration data structures and transformation from CST."""

from __future__ import annotations

from ast import literal_eval
from dataclasses import dataclass, field
from enum import Enum

from fltk.fegen import gsm
from fltk.fegen.pyrt.terminalsrc import TerminalSource
from fltk.unparse import unparsefmt_cst as fmt_cst
from fltk.unparse.combinators import (
    HARDLINE,
    HARDLINE_BLANK,
    LINE,
    NBSP,
    NIL,
    SOFTLINE,
    Doc,
    HardLine,
    Text,
    concat,
    group,
    join,
    nest,
)


@dataclass
class TriviaConfig:
    """Configuration for selective trivia preservation in unparsing.

    Specifies which types of trivia child nodes should be preserved when unparsing.
    The names refer to the CST class names (e.g., "LineComment", "BlockComment").
    These are the actual node types that appear as children of Trivia nodes.
    """

    # CST class names of trivia children to preserve (e.g., {"LineComment", "BlockComment"})
    # If empty, all trivia is discarded. If None, all trivia is preserved.
    preserve_node_names: set[str] | None = field(default_factory=set)


class ItemSelector(Enum):
    """Type of item selector for anchor points."""

    LABEL = "label"
    LITERAL = "literal"
    RULE_START = "rule_start"
    RULE_END = "rule_end"


@dataclass(frozen=True, slots=True)
class Normal:
    """Item is rendered normally."""

    pass


NORMAL = Normal()


@dataclass(frozen=True, slots=True)
class Omit:
    """Item is completely omitted."""

    pass


OMIT = Omit()


@dataclass(frozen=True, slots=True)
class RenderAs:
    """Item is replaced with specified content."""

    spacing: Doc


class OperationType(Enum):
    """Types of formatting operations that can occur at an anchor point."""

    SPACING = "spacing"
    GROUP_BEGIN = "group_begin"
    GROUP_END = "group_end"
    NEST_BEGIN = "nest_begin"
    NEST_END = "nest_end"
    JOIN_BEGIN = "join_begin"
    JOIN_END = "join_end"


@dataclass
class FormatOperation:
    """A single formatting operation at an anchor point."""

    operation_type: OperationType

    spacing: Doc | None = None

    indent: int | None = None

    separator: Doc | None = None


@dataclass
class AnchorConfig:
    """Configuration for all formatting operations at a specific anchor point.

    Operations are applied in the order they appear in the list.
    This replaces the old AfterConfig/BeforeConfig classes.
    """

    selector_type: ItemSelector
    selector_value: str

    disposition: None | Normal | Omit | RenderAs = None
    # Ordered list of operations to perform at this anchor
    operations: list[FormatOperation] = field(default_factory=list)


@dataclass
class RuleConfig:
    """Configuration for a specific rule."""

    ws_allowed_spacing: Doc | None = None
    ws_required_spacing: Doc | None = None

    # All anchor configurations for this rule
    # Key format: "{position}:{selector_type}:{selector_value}"
    # Examples: "after:label:condition", "before:literal:(", "before:rule_start:"
    anchor_configs: dict[str, AnchorConfig] = field(default_factory=dict)


@dataclass
class FormatterConfig:
    """Complete formatter configuration with global defaults and rule overrides."""

    global_ws_allowed: Doc = field(default=NIL)
    global_ws_required: Doc = field(default=LINE)

    anchor_configs: dict[str, AnchorConfig] = field(default_factory=dict)

    rule_configs: dict[str, RuleConfig] = field(default_factory=dict)

    trivia_config: TriviaConfig | None = None

    def get_anchor_config(
        self, rule_name: str, position: str, selector_type: ItemSelector, selector_value: str
    ) -> AnchorConfig | None:
        """Get merged anchor configuration for a specific position and selector.

        This method returns an AnchorConfig that merges operations from both global
        and rule-specific configurations. Rule-specific operations appear first in
        the operations list (important for proper GROUP_END/NEST_END ordering).

        Args:
            rule_name: Name of the rule
            position: "before" or "after"
            selector_type: Type of selector
            selector_value: Value of selector

        Returns:
            AnchorConfig with merged operations if any exist, None otherwise
        """
        key = f"{position}:{selector_type.value}:{selector_value}"

        # Get both configs
        rule_anchor_config = None
        rule_config = self.rule_configs.get(rule_name)
        if rule_config:
            rule_anchor_config = rule_config.anchor_configs.get(key)

        global_anchor_config = self.anchor_configs.get(key)

        # If neither exists, return None
        if not rule_anchor_config and not global_anchor_config:
            return None

        # If only one exists, return it
        if not rule_anchor_config:
            return global_anchor_config
        if not global_anchor_config:
            return rule_anchor_config

        # Both exist - merge intelligently:
        # 1. Spacing operations: rule completely replaces global
        # 2. Group/Nest operations: merge with globals "outside" locals
        # 3. END operations must maintain proper unwinding order (rule ENDs before global ENDs)

        # Check if rule has any spacing operations
        rule_has_spacing = any(op.operation_type == OperationType.SPACING for op in rule_anchor_config.operations)

        merged_operations = []

        # First pass: Add non-END global operations (but skip spacing if rule has spacing)
        for op in global_anchor_config.operations:
            if op.operation_type == OperationType.SPACING and rule_has_spacing:
                continue  # Skip global spacing, rule overrides
            if not op.operation_type.value.endswith("_end"):
                merged_operations.append(op)

        # Second pass: Add all rule operations
        merged_operations.extend(rule_anchor_config.operations)

        # Third pass: Add END global operations
        for op in global_anchor_config.operations:
            if op.operation_type.value.endswith("_end"):
                merged_operations.append(op)

        return AnchorConfig(
            selector_type=selector_type,
            selector_value=selector_value,
            disposition=(rule_anchor_config.disposition or global_anchor_config.disposition),
            operations=merged_operations,
        )

    def get_spacing_for_separator(self, rule_name: str, separator: gsm.Separator) -> Doc:
        """Get the appropriate spacing Doc for a given rule and separator type.

        Args:
            rule_name: Name of the grammar rule
            separator: The separator type from the grammar

        Returns:
            The appropriate Doc combinator for the spacing
        """
        if separator == gsm.Separator.NO_WS:
            return NIL

        # Check for rule-specific config
        rule_config = self.rule_configs.get(rule_name)
        if rule_config:
            if separator == gsm.Separator.WS_ALLOWED and rule_config.ws_allowed_spacing is not None:
                return rule_config.ws_allowed_spacing
            elif separator == gsm.Separator.WS_REQUIRED and rule_config.ws_required_spacing is not None:
                return rule_config.ws_required_spacing

        # Fall back to global defaults
        if separator == gsm.Separator.WS_ALLOWED:
            return self.global_ws_allowed
        else:  # WS_REQUIRED
            return self.global_ws_required

    def get_after_spacing(self, rule_name: str, item: gsm.Item) -> Doc | None:
        """Get spacing after an item using the new anchor-based system.

        Args:
            rule_name: Name of the grammar rule
            item: The grammar item to check

        Returns:
            The Doc combinator for spacing after the item, or None if no config exists
        """
        return self._get_spacing(rule_name, item, "after")

    def get_before_spacing(self, rule_name: str, item: gsm.Item) -> Doc | None:
        """Get spacing before an item using the new anchor-based system.

        Args:
            rule_name: Name of the grammar rule
            item: The grammar item to check

        Returns:
            The Doc combinator for spacing before the item, or None if no config exists
        """
        return self._get_spacing(rule_name, item, "before")

    def _get_spacing(self, rule_name: str, item: gsm.Item, prefix: str) -> Doc | None:
        anchor_config = None
        if item.label:
            selector_type = ItemSelector.LABEL
            selector_value = item.label
            anchor_config = self.get_anchor_config(rule_name, prefix, selector_type, selector_value)
        if not anchor_config and isinstance(item.term, gsm.Literal):
            selector_type = ItemSelector.LITERAL
            selector_value = item.term.value
            anchor_config = self.get_anchor_config(rule_name, prefix, selector_type, selector_value)

        if not anchor_config:
            return None

        # Find first spacing operation
        for op in anchor_config.operations:
            if op.operation_type == OperationType.SPACING:
                return op.spacing
        return None

    def get_item_disposition(self, rule_name: str, item: gsm.Item) -> Normal | Omit | RenderAs:
        """Get the disposition for an item in the unparsed output.

        Args:
            rule_name: Name of the grammar rule
            item: The grammar item to check

        Returns:
            Normal, Omit, or RenderAs with spacing information
        """
        anchor_config = None
        if item.label:
            selector_type = ItemSelector.LABEL
            selector_value = item.label
            anchor_config = self.get_anchor_config(rule_name, "before", selector_type, selector_value)
        if (not anchor_config or not anchor_config.disposition) and isinstance(item.term, gsm.Literal):
            selector_type = ItemSelector.LITERAL
            selector_value = item.term.value
            anchor_config = self.get_anchor_config(rule_name, "before", selector_type, selector_value)

        if not anchor_config or not anchor_config.disposition:
            return NORMAL

        return anchor_config.disposition


def _spacing_cst_to_doc(spacing: fmt_cst.Spacing, terminal_src: TerminalSource) -> Doc:
    """Convert a Spacing CST node to a Doc combinator."""
    if spacing.maybe_nil():
        return NIL
    elif spacing.maybe_nbsp():
        return NBSP
    elif spacing.maybe_bsp():
        return LINE
    elif spacing.maybe_soft():
        return SOFTLINE
    elif spacing.maybe_hard():
        return HARDLINE
    elif spacing.maybe_blank():
        num_blanks = spacing.maybe_num_blanks()
        if num_blanks:
            num_blanks_span = num_blanks.child_value()
            num_blanks_text = terminal_src.terminals[num_blanks_span.start : num_blanks_span.end]
            return HardLine(blank_lines=int(num_blanks_text))
        else:
            return HARDLINE_BLANK
    else:
        msg = f"Unknown spacing type in CST: {spacing}"
        raise ValueError(msg)


def _doc_list_literal_to_docs(doc_list_literal: fmt_cst.DocListLiteral, terminal_src: TerminalSource) -> list[Doc]:
    """Convert a DocListLiteral CST node to a list of Doc combinators."""
    docs = []
    for child_doc_literal in doc_list_literal.children_doc_literal():
        docs.append(_doc_literal_cst_to_doc(child_doc_literal, terminal_src))
    return docs


def _doc_literal_cst_to_doc(doc_literal: fmt_cst.DocLiteral, terminal_src: TerminalSource) -> Doc:
    """Convert a DocLiteral CST node to a Doc combinator."""
    concat_literal = doc_literal.maybe_concat_literal()
    if concat_literal:
        doc_list_literal = concat_literal.child_doc_list_literal()
        docs = _doc_list_literal_to_docs(doc_list_literal, terminal_src)
        return concat(docs)

    join_literal = doc_literal.maybe_join_literal()
    if join_literal:
        separator_doc_literal = join_literal.child_separator()
        separator = _doc_literal_cst_to_doc(separator_doc_literal, terminal_src)

        doc_list_literal = join_literal.child_doc_list_literal()
        docs = _doc_list_literal_to_docs(doc_list_literal, terminal_src)

        return join(docs, separator)

    compound_literal = doc_literal.maybe_compound_literal()
    if compound_literal:
        inner_doc_literal = compound_literal.child_doc_literal()
        inner_doc = _doc_literal_cst_to_doc(inner_doc_literal, terminal_src)

        if compound_literal.maybe_group():
            return group(inner_doc)
        elif compound_literal.maybe_nest():
            return nest(1, inner_doc)
        else:
            msg = "compound_literal must have group or nest"
            raise ValueError(msg)

    text_literal = doc_literal.maybe_text_literal()
    if text_literal:
        text_value = _extract_literal_text(text_literal.child_text(), terminal_src)
        return Text(text_value)

    spacing = doc_literal.maybe_spacing()
    if spacing:
        return _spacing_cst_to_doc(spacing, terminal_src)

    msg = f"Unknown doc_literal type in CST: {doc_literal}"
    raise ValueError(msg)


def _process_default_statement(
    default: fmt_cst.Default,
    config: FormatterConfig,
    terminal_src: TerminalSource,
    rule_config: RuleConfig | None = None,
) -> None:
    """Process a Default statement and update the appropriate config."""
    spacing_doc = _spacing_cst_to_doc(default.child_spacing(), terminal_src)

    if default.maybe_ws_allowed():
        if rule_config is not None:
            rule_config.ws_allowed_spacing = spacing_doc
        else:
            config.global_ws_allowed = spacing_doc
    elif default.maybe_ws_required():
        if rule_config is not None:
            rule_config.ws_required_spacing = spacing_doc
        else:
            config.global_ws_required = spacing_doc


def _extract_identifier_text(identifier: fmt_cst.Identifier, terminal_src: TerminalSource) -> str:
    """Extract the text content of an identifier from its span."""
    name_span = identifier.child_name()
    return terminal_src.terminals[name_span.start : name_span.end]


def _extract_literal_text(literal: fmt_cst.Literal, terminal_src: TerminalSource) -> str:
    """Extract the text content of a literal from its span, properly unquoting."""
    value_span = literal.child_value()
    quoted_text = terminal_src.terminals[value_span.start : value_span.end]

    return literal_eval(quoted_text)


def _process_trivia_preserve_statement(
    trivia_preserve: fmt_cst.TriviaPreserve, config: FormatterConfig, terminal_src: TerminalSource
) -> None:
    """Process a TriviaPreserve statement and update the config's trivia_config."""

    trivia_node_list = trivia_preserve.child_trivia_node_list()

    node_names = set()
    for identifier in trivia_node_list.children_identifier():
        node_name = _extract_identifier_text(identifier, terminal_src)
        node_names.add(node_name)

    config.trivia_config = TriviaConfig(preserve_node_names=node_names)


def _process_after_statement(
    after: fmt_cst.After, target: FormatterConfig | RuleConfig, terminal_src: TerminalSource
) -> None:
    """Process an After statement and update the target config (global or rule-specific)."""
    anchor = after.child_anchor()

    label = anchor.maybe_label()
    literal = anchor.maybe_literal()

    if label:
        selector_type = ItemSelector.LABEL
        selector_value = _extract_identifier_text(label, terminal_src)
    elif literal:
        selector_type = ItemSelector.LITERAL
        selector_value = _extract_literal_text(literal, terminal_src)
    else:
        msg = "After statement's anchor must have either label or literal"
        raise ValueError(msg)

    # Process position_spec_statement - for now we expect only one spacing
    # TODO: The grammar allows multiple position_spec_statement*, but the current
    # implementation assumes one spacing. We'll take the first one.
    position_spec_cst = after.maybe_position_spec_statement()
    if not position_spec_cst:
        msg = "After statement must have at exactly one position_spec_statement"
        raise ValueError(msg)

    spacing_cst = position_spec_cst.child_spacing()
    spacing_doc = _spacing_cst_to_doc(spacing_cst, terminal_src)

    anchor_key = f"after:{selector_type.value}:{selector_value}"

    anchor_config = target.anchor_configs.get(anchor_key)
    if not anchor_config:
        anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
        target.anchor_configs[anchor_key] = anchor_config

    anchor_config.operations.append(FormatOperation(OperationType.SPACING, spacing=spacing_doc))


def _process_before_statement(
    before: fmt_cst.Before, target: FormatterConfig | RuleConfig, terminal_src: TerminalSource
) -> None:
    """Process a Before statement and update the target config (global or rule-specific)."""
    anchor = before.child_anchor()

    label = anchor.maybe_label()
    literal = anchor.maybe_literal()

    if label:
        selector_type = ItemSelector.LABEL
        selector_value = _extract_identifier_text(label, terminal_src)
    elif literal:
        selector_type = ItemSelector.LITERAL
        selector_value = _extract_literal_text(literal, terminal_src)
    else:
        msg = "Before statement's anchor must have either label or literal"
        raise ValueError(msg)

    # Process position_spec_statement - for now we expect only one spacing
    # TODO: The grammar allows multiple position_spec_statement*, but the current
    # implementation assumes one spacing. We'll take the first one.
    position_spec_cst = before.maybe_position_spec_statement()
    if not position_spec_cst:
        msg = "Before statement must have exactly one position_spec_statement"
        raise ValueError(msg)

    spacing_cst = position_spec_cst.child_spacing()
    spacing_doc = _spacing_cst_to_doc(spacing_cst, terminal_src)

    anchor_key = f"before:{selector_type.value}:{selector_value}"

    anchor_config = target.anchor_configs.get(anchor_key)
    if not anchor_config:
        anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
        target.anchor_configs[anchor_key] = anchor_config

    anchor_config.operations.append(FormatOperation(OperationType.SPACING, spacing=spacing_doc))


def _process_range_operation(
    from_spec: fmt_cst.FromSpec | None,
    to_spec: fmt_cst.ToSpec | None,
    begin_op: FormatOperation,
    end_op_type: OperationType,
    config: RuleConfig | FormatterConfig,
    terminal_src: TerminalSource,
) -> None:
    """Process a range-based operation (group, nest, join) with from/to specs.

    Args:
        from_spec: Optional from specification (where operation begins)
        to_spec: Optional to specification (where operation ends)
        begin_op: The operation to add at the beginning
        end_op_type: The operation type for the end
        config: Configuration to update
        terminal_src: Terminal source for extracting text
    """
    if from_spec:
        from_anchor = from_spec.child_from_anchor()
        label = from_anchor.maybe_label()
        literal = from_anchor.maybe_literal()

        if label:
            selector_type = ItemSelector.LABEL
            selector_value = _extract_identifier_text(label, terminal_src)
        elif literal:
            selector_type = ItemSelector.LITERAL
            selector_value = _extract_literal_text(literal, terminal_src)
        else:
            msg = "from_anchor must have either label or literal"
            raise RuntimeError(msg)

        # Check if "after" modifier is present (non-inclusive start)
        is_after = from_spec.maybe_after() is not None
        position = "after" if is_after else "before"

        # Add BEGIN operation at the appropriate position
        anchor_key = f"{position}:{selector_type.value}:{selector_value}"
        anchor_config = config.anchor_configs.get(anchor_key)
        if not anchor_config:
            anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
            config.anchor_configs[anchor_key] = anchor_config
        anchor_config.operations.append(begin_op)
    else:
        # No from_spec means operation starts at rule beginning
        anchor_key = "before:rule_start:"
        anchor_config = config.anchor_configs.get(anchor_key)
        if not anchor_config:
            anchor_config = AnchorConfig(selector_type=ItemSelector.RULE_START, selector_value="")
            config.anchor_configs[anchor_key] = anchor_config
        anchor_config.operations.append(begin_op)

    if to_spec:
        to_anchor = to_spec.child_to_anchor()
        label = to_anchor.maybe_label()
        literal = to_anchor.maybe_literal()

        if label:
            selector_type = ItemSelector.LABEL
            selector_value = _extract_identifier_text(label, terminal_src)
        elif literal:
            selector_type = ItemSelector.LITERAL
            selector_value = _extract_literal_text(literal, terminal_src)
        else:
            msg = "to_anchor must have either label or literal"
            raise RuntimeError(msg)

        is_before = to_spec.maybe_before() is not None
        position = "before" if is_before else "after"

        # Add END operation at the appropriate position
        anchor_key = f"{position}:{selector_type.value}:{selector_value}"
        anchor_config = config.anchor_configs.get(anchor_key)
        if not anchor_config:
            anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
            config.anchor_configs[anchor_key] = anchor_config
        # Insert at beginning to ensure proper unwinding order
        anchor_config.operations.insert(0, FormatOperation(end_op_type))
    else:
        # No to_spec means operation ends at rule end
        anchor_key = "after:rule_end:"
        anchor_config = config.anchor_configs.get(anchor_key)
        if not anchor_config:
            anchor_config = AnchorConfig(selector_type=ItemSelector.RULE_END, selector_value="")
            config.anchor_configs[anchor_key] = anchor_config
        # Insert at beginning to ensure proper unwinding order
        anchor_config.operations.insert(0, FormatOperation(end_op_type))


def _process_group_statement(
    group: fmt_cst.Group, config: RuleConfig | FormatterConfig, terminal_src: TerminalSource
) -> None:
    """Process a Group statement and update the rule config."""
    _process_range_operation(
        group.maybe_from_spec(),
        group.maybe_to_spec(),
        FormatOperation(OperationType.GROUP_BEGIN),
        OperationType.GROUP_END,
        config,
        terminal_src,
    )


def _process_nest_statement(
    nest: fmt_cst.Nest, config: RuleConfig | FormatterConfig, terminal_src: TerminalSource
) -> None:
    """Process a Nest statement and update the rule config."""
    indent_value = 1
    indent = nest.maybe_indent()
    if indent:
        indent_span = indent.child_value()
        indent_text = terminal_src.terminals[indent_span.start : indent_span.end]
        indent_value = int(indent_text)

    _process_range_operation(
        nest.maybe_from_spec(),
        nest.maybe_to_spec(),
        FormatOperation(OperationType.NEST_BEGIN, indent=indent_value),
        OperationType.NEST_END,
        config,
        terminal_src,
    )


def _process_join_statement(
    join: fmt_cst.Join, config: RuleConfig | FormatterConfig, terminal_src: TerminalSource
) -> None:
    """Process a Join statement and update the rule config."""
    doc_literal = join.child_doc_literal()
    separator = _doc_literal_cst_to_doc(doc_literal, terminal_src)

    _process_range_operation(
        join.maybe_from_spec(),
        join.maybe_to_spec(),
        FormatOperation(OperationType.JOIN_BEGIN, separator=separator),
        OperationType.JOIN_END,
        config,
        terminal_src,
    )


def _process_omit_statement(
    omit: fmt_cst.Omit, target: FormatterConfig | RuleConfig, terminal_src: TerminalSource
) -> None:
    """Process an Omit statement and update the target config (global or rule-specific)."""
    anchor = omit.child_anchor()

    label = anchor.maybe_label()
    literal = anchor.maybe_literal()

    if label:
        selector_type = ItemSelector.LABEL
        selector_value = _extract_identifier_text(label, terminal_src)
    elif literal:
        selector_type = ItemSelector.LITERAL
        selector_value = _extract_literal_text(literal, terminal_src)
    else:
        msg = "Omit statement's anchor must have either label or literal"
        raise ValueError(msg)

    anchor_key = f"before:{selector_type.value}:{selector_value}"

    anchor_config = target.anchor_configs.get(anchor_key)
    if not anchor_config:
        anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
        target.anchor_configs[anchor_key] = anchor_config
    if anchor_config.disposition:
        msg = f"Multiple dispositions for {selector_type.value}:{selector_value}"
        raise ValueError(msg)
    anchor_config.disposition = OMIT


def _process_render_statement(
    render: fmt_cst.Render, target: FormatterConfig | RuleConfig, terminal_src: TerminalSource
) -> None:
    """Process a Render statement and update the target config (global or rule-specific)."""
    anchor = render.child_anchor()

    label = anchor.maybe_label()
    literal = anchor.maybe_literal()

    if label:
        selector_type = ItemSelector.LABEL
        selector_value = _extract_identifier_text(label, terminal_src)
    elif literal:
        selector_type = ItemSelector.LITERAL
        selector_value = _extract_literal_text(literal, terminal_src)
    else:
        msg = "Render statement's anchor must have either label or literal"
        raise ValueError(msg)

    spacing_cst = render.child_spacing()
    spacing_doc = _spacing_cst_to_doc(spacing_cst, terminal_src)

    anchor_key = f"before:{selector_type.value}:{selector_value}"

    anchor_config = target.anchor_configs.get(anchor_key)
    if not anchor_config:
        anchor_config = AnchorConfig(selector_type=selector_type, selector_value=selector_value)
        target.anchor_configs[anchor_key] = anchor_config

    if anchor_config.disposition:
        msg = f"Multiple dispositions for {selector_type.value}:{selector_value}"
        raise ValueError(msg)
    anchor_config.disposition = RenderAs(spacing=spacing_doc)


def fmt_cst_to_config(formatter: fmt_cst.Formatter, terminal_src: TerminalSource) -> FormatterConfig:
    """Transform a formatter CST into a FormatterConfig.

    Args:
        formatter: The parsed formatter CST
        terminal_src: The terminal source for extracting identifier values

    Returns:
        A FormatterConfig with all settings extracted from the CST
    """
    config = FormatterConfig()

    for statement in formatter.children_statement():
        default = statement.maybe_default()
        if default:
            _process_default_statement(default, config, terminal_src)
            continue

        group = statement.maybe_group()
        if group:
            _process_group_statement(group, config, terminal_src)
            continue

        nest = statement.maybe_nest()
        if nest:
            _process_nest_statement(nest, config, terminal_src)
            continue

        join = statement.maybe_join()
        if join:
            _process_join_statement(join, config, terminal_src)
            continue

        after = statement.maybe_after()
        if after:
            _process_after_statement(after, config, terminal_src)
            continue

        before = statement.maybe_before()
        if before:
            _process_before_statement(before, config, terminal_src)
            continue

        trivia_preserve = statement.maybe_trivia_preserve()
        if trivia_preserve:
            _process_trivia_preserve_statement(trivia_preserve, config, terminal_src)
            continue

        omit = statement.maybe_omit()
        if omit:
            _process_omit_statement(omit, config, terminal_src)
            continue

        render = statement.maybe_render()
        if render:
            _process_render_statement(render, config, terminal_src)
            continue

        rule_config_cst = statement.maybe_rule_config()
        if rule_config_cst:
            rule_name = _extract_identifier_text(rule_config_cst.child_rule_name(), terminal_src)

            rule_config = config.rule_configs.setdefault(rule_name, RuleConfig())

            for rule_statement in rule_config_cst.children_rule_statement():
                rule_default = rule_statement.maybe_default()
                if rule_default:
                    _process_default_statement(rule_default, config, terminal_src, rule_config)
                    continue

                rule_after = rule_statement.maybe_after()
                if rule_after:
                    _process_after_statement(rule_after, rule_config, terminal_src)
                    continue

                rule_before = rule_statement.maybe_before()
                if rule_before:
                    _process_before_statement(rule_before, rule_config, terminal_src)
                    continue

                rule_group = rule_statement.maybe_group()
                if rule_group:
                    _process_group_statement(rule_group, rule_config, terminal_src)
                    continue

                rule_nest = rule_statement.maybe_nest()
                if rule_nest:
                    _process_nest_statement(rule_nest, rule_config, terminal_src)
                    continue

                rule_join = rule_statement.maybe_join()
                if rule_join:
                    _process_join_statement(rule_join, rule_config, terminal_src)
                    continue

                rule_omit = rule_statement.maybe_omit()
                if rule_omit:
                    _process_omit_statement(rule_omit, rule_config, terminal_src)
                    continue

                rule_render = rule_statement.maybe_render()
                if rule_render:
                    _process_render_statement(rule_render, rule_config, terminal_src)
                    continue

    return config
