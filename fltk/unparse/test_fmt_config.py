"""Tests for formatter configuration."""

from fltk.fegen import gsm
from fltk.plumbing import parse_format_config
from fltk.unparse.combinators import (
    HARDLINE,
    LINE,
    NBSP,
    NIL,
    SOFTLINE,
    Concat,
    Group,
    HardLine,
    Join,
    Nest,
    Text,
)
from fltk.unparse.fmt_config import (
    OMIT,
    AnchorConfig,
    FormatterConfig,
    ItemSelector,
    Normal,
    Omit,
    OperationType,
    RenderAs,
    RuleConfig,
)


class TestFormatterConfigAPI:
    """Test the FormatterConfig API directly."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FormatterConfig()

        assert config.global_ws_allowed == NIL
        assert config.global_ws_required == LINE
        assert len(config.rule_configs) == 0

    def test_no_ws_separator(self):
        """Test NO_WS separator always returns NIL."""
        config = FormatterConfig()

        # Should always return NIL regardless of rule or config
        assert config.get_spacing_for_separator("any_rule", gsm.Separator.NO_WS) == NIL

        # Even with custom config
        config.rule_configs["test"] = RuleConfig(ws_allowed_spacing=NBSP)
        assert config.get_spacing_for_separator("test", gsm.Separator.NO_WS) == NIL

    def test_global_defaults(self):
        """Test global default spacing."""
        config = FormatterConfig()

        assert config.get_spacing_for_separator("any_rule", gsm.Separator.WS_ALLOWED) == NIL
        assert config.get_spacing_for_separator("any_rule", gsm.Separator.WS_REQUIRED) == LINE

        # Change global defaults
        config.global_ws_allowed = NBSP
        config.global_ws_required = HARDLINE

        assert config.get_spacing_for_separator("any_rule", gsm.Separator.WS_ALLOWED) == NBSP
        assert config.get_spacing_for_separator("any_rule", gsm.Separator.WS_REQUIRED) == HARDLINE

    def test_rule_specific_config(self):
        """Test rule-specific configuration overrides."""
        config = FormatterConfig()

        # Add rule-specific config
        config.rule_configs["expr"] = RuleConfig(ws_allowed_spacing=NBSP, ws_required_spacing=HARDLINE)

        # Test rule-specific
        assert config.get_spacing_for_separator("expr", gsm.Separator.WS_ALLOWED) == NBSP
        assert config.get_spacing_for_separator("expr", gsm.Separator.WS_REQUIRED) == HARDLINE

        # Test other rules still use defaults
        assert config.get_spacing_for_separator("stmt", gsm.Separator.WS_ALLOWED) == NIL
        assert config.get_spacing_for_separator("stmt", gsm.Separator.WS_REQUIRED) == LINE

    def test_partial_rule_config(self):
        """Test partial rule configuration with fallback."""
        config = FormatterConfig()
        config.global_ws_required = HARDLINE

        # Rule with only ws_allowed specified
        config.rule_configs["partial"] = RuleConfig(ws_allowed_spacing=NIL)

        assert config.get_spacing_for_separator("partial", gsm.Separator.WS_ALLOWED) == NIL
        # Should fall back to global for ws_required
        assert config.get_spacing_for_separator("partial", gsm.Separator.WS_REQUIRED) == HARDLINE

    def test_all_separator_types(self):
        """Test handling of all separator types."""
        config = FormatterConfig()
        config.global_ws_allowed = NBSP
        config.global_ws_required = HARDLINE

        # Test all separator types
        assert config.get_spacing_for_separator("test", gsm.Separator.NO_WS) == NIL
        assert config.get_spacing_for_separator("test", gsm.Separator.WS_ALLOWED) == NBSP
        assert config.get_spacing_for_separator("test", gsm.Separator.WS_REQUIRED) == HARDLINE

    def test_multiple_rules(self):
        """Test multiple rules with different configurations."""
        config = FormatterConfig()

        # Set up different configs for different rules
        config.rule_configs["rule1"] = RuleConfig(ws_allowed_spacing=NIL, ws_required_spacing=HARDLINE)
        config.rule_configs["rule2"] = RuleConfig(ws_allowed_spacing=NBSP, ws_required_spacing=SOFTLINE)
        config.rule_configs["rule3"] = RuleConfig(ws_allowed_spacing=LINE)  # Partial config

        # Test each rule
        assert config.get_spacing_for_separator("rule1", gsm.Separator.WS_ALLOWED) == NIL
        assert config.get_spacing_for_separator("rule1", gsm.Separator.WS_REQUIRED) == HARDLINE

        assert config.get_spacing_for_separator("rule2", gsm.Separator.WS_ALLOWED) == NBSP
        assert config.get_spacing_for_separator("rule2", gsm.Separator.WS_REQUIRED) == SOFTLINE

        assert config.get_spacing_for_separator("rule3", gsm.Separator.WS_ALLOWED) == LINE
        assert config.get_spacing_for_separator("rule3", gsm.Separator.WS_REQUIRED) == LINE  # Global default

        # Test unknown rule falls back to global
        assert config.get_spacing_for_separator("unknown", gsm.Separator.WS_ALLOWED) == NIL
        assert config.get_spacing_for_separator("unknown", gsm.Separator.WS_REQUIRED) == LINE


class TestFormatterConfigWithCST:
    """Test CST transformation with real parser."""

    def test_empty_config(self):
        """Test parsing empty formatter config."""
        fmt_text = ""
        config = parse_format_config(fmt_text)

        # Should get default config
        assert config.global_ws_allowed == NIL
        assert config.global_ws_required == LINE
        assert len(config.rule_configs) == 0

    def test_global_defaults_only(self):
        """Test parsing global defaults."""
        fmt_text = "ws_allowed: nbsp;"
        config = parse_format_config(fmt_text)

        assert config.global_ws_allowed == NBSP
        assert config.global_ws_required == LINE  # Should remain default
        assert len(config.rule_configs) == 0

    def test_single_rule_config(self):
        """Test parsing single rule configuration."""
        fmt_text = """rule expr {
    ws_allowed: nil;
    ws_required: soft;
}"""
        config = parse_format_config(fmt_text)

        # Global defaults unchanged
        assert config.global_ws_allowed == NIL
        assert config.global_ws_required == LINE

        # Rule specific config
        assert "expr" in config.rule_configs
        assert config.rule_configs["expr"].ws_allowed_spacing == NIL
        assert config.rule_configs["expr"].ws_required_spacing == SOFTLINE

    def test_global_and_rule_configs(self):
        """Test parsing both global and rule-specific configs."""
        fmt_text = """
ws_allowed: nbsp;
ws_required: hard;

rule stmt {
    ws_allowed: bsp;
}

rule expr {
    ws_required: soft;
}
"""
        config = parse_format_config(fmt_text)

        # Global config
        assert config.global_ws_allowed == NBSP
        assert config.global_ws_required == HARDLINE

        # Rule configs
        assert "stmt" in config.rule_configs
        assert config.rule_configs["stmt"].ws_allowed_spacing == LINE
        assert config.rule_configs["stmt"].ws_required_spacing is None

        assert "expr" in config.rule_configs
        assert config.rule_configs["expr"].ws_allowed_spacing is None
        assert config.rule_configs["expr"].ws_required_spacing == SOFTLINE

    def test_all_spacing_types(self):
        """Test all spacing types are parsed correctly."""
        fmt_text = """
rule test1 {
    ws_allowed: nil;
}
rule test2 {
    ws_allowed: nbsp;
}
rule test3 {
    ws_allowed: bsp;
}
rule test4 {
    ws_allowed: soft;
}
rule test5 {
    ws_allowed: hard;
}
rule test6 {
    ws_allowed: blank;
}
"""
        config = parse_format_config(fmt_text)

        assert config.rule_configs["test1"].ws_allowed_spacing == NIL
        assert config.rule_configs["test2"].ws_allowed_spacing == NBSP
        assert config.rule_configs["test3"].ws_allowed_spacing == LINE
        assert config.rule_configs["test4"].ws_allowed_spacing == SOFTLINE
        assert config.rule_configs["test5"].ws_allowed_spacing == HARDLINE
        # blank defaults to HardLine with 1 blank line
        assert isinstance(config.rule_configs["test6"].ws_allowed_spacing, HardLine)
        assert config.rule_configs["test6"].ws_allowed_spacing.blank_lines == 1

    def test_blank_spacing_with_parameters(self):
        """Test blank spacing with different blank line counts."""
        fmt_text = """
rule test1 {
    ws_allowed: blank(2);
}
rule test2 {
    ws_required: blank(3);
}
after ";" { blank(5); };
before "{" { blank; };
render newline as blank(4);
"""
        config = parse_format_config(fmt_text)

        # Rule-specific blank spacing with parameters
        assert isinstance(config.rule_configs["test1"].ws_allowed_spacing, HardLine)
        assert config.rule_configs["test1"].ws_allowed_spacing.blank_lines == 2

        assert isinstance(config.rule_configs["test2"].ws_required_spacing, HardLine)
        assert config.rule_configs["test2"].ws_required_spacing.blank_lines == 3

        # After statement with blank(5)
        assert "after:literal:;" in config.anchor_configs
        after_semi = config.anchor_configs["after:literal:;"]
        assert len(after_semi.operations) == 1
        assert after_semi.operations[0].operation_type == OperationType.SPACING
        assert isinstance(after_semi.operations[0].spacing, HardLine)
        assert after_semi.operations[0].spacing.blank_lines == 5

        # Before statement with default blank (1 line)
        assert "before:literal:{" in config.anchor_configs
        before_brace = config.anchor_configs["before:literal:{"]
        assert len(before_brace.operations) == 1
        assert before_brace.operations[0].operation_type == OperationType.SPACING
        assert isinstance(before_brace.operations[0].spacing, HardLine)
        assert before_brace.operations[0].spacing.blank_lines == 1

        # Render statement with blank(4)
        assert "before:label:newline" in config.anchor_configs
        render_newline = config.anchor_configs["before:label:newline"]
        assert isinstance(render_newline.disposition, RenderAs)
        assert isinstance(render_newline.disposition.spacing, HardLine)
        assert render_newline.disposition.spacing.blank_lines == 4

    def test_comments_handled(self):
        """Test that comments are handled correctly."""
        fmt_text = """
// Global defaults
ws_allowed: soft;  // Default soft line

// Rule specific configs
rule expr {
    // Expression formatting
    ws_allowed: nbsp;
    ws_required: hard;
}
"""
        config = parse_format_config(fmt_text)

        # Comments should not affect parsing
        assert config.global_ws_allowed == SOFTLINE
        assert config.global_ws_required == LINE  # Default
        assert config.rule_configs["expr"].ws_allowed_spacing == NBSP
        assert config.rule_configs["expr"].ws_required_spacing == HARDLINE

    def test_api_integration(self):
        """Test full API integration with parsed config."""
        fmt_text = """
ws_allowed: nbsp;
ws_required: hard;

rule expr {
    ws_allowed: nil;
}
"""
        config = parse_format_config(fmt_text)

        # Test API methods with parsed config
        assert config.get_spacing_for_separator("expr", gsm.Separator.NO_WS) == NIL
        assert config.get_spacing_for_separator("expr", gsm.Separator.WS_ALLOWED) == NIL
        assert config.get_spacing_for_separator("expr", gsm.Separator.WS_REQUIRED) == HARDLINE  # Global default

        assert config.get_spacing_for_separator("other", gsm.Separator.NO_WS) == NIL
        assert config.get_spacing_for_separator("other", gsm.Separator.WS_ALLOWED) == NBSP
        assert config.get_spacing_for_separator("other", gsm.Separator.WS_REQUIRED) == HARDLINE

    def test_group_config(self):
        """Test parsing group configuration."""
        fmt_text = """rule expr {
    group;
}"""
        config = parse_format_config(fmt_text)

        # Check that group operations were created at rule start/end
        assert "expr" in config.rule_configs
        rule_config = config.rule_configs["expr"]

        # Should have GROUP_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        assert len(start_anchor.operations) == 1
        assert start_anchor.operations[0].operation_type == OperationType.GROUP_BEGIN

        # Should have GROUP_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        assert len(end_anchor.operations) == 1
        assert end_anchor.operations[0].operation_type == OperationType.GROUP_END

    def test_group_config_with_from(self):
        """Test parsing group configuration with from anchor."""
        fmt_text = """rule expr {
    group from op_token;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have GROUP_BEGIN before op_token
        assert "before:label:op_token" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:op_token"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in from_anchor.operations)

        # Should have GROUP_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        assert any(op.operation_type == OperationType.GROUP_END for op in end_anchor.operations)

    def test_group_config_with_to(self):
        """Test parsing group configuration with to anchor."""
        fmt_text = """rule expr {
    group to "end";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have GROUP_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in start_anchor.operations)

        # Should have GROUP_END after "end"
        assert "after:literal:end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:literal:end"]
        assert any(op.operation_type == OperationType.GROUP_END for op in to_anchor.operations)

    def test_group_config_with_from_and_to(self):
        """Test parsing group configuration with both from and to anchors."""
        fmt_text = """rule expr {
    group from start_token to "end";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have GROUP_BEGIN before start_token
        assert "before:label:start_token" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:start_token"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in from_anchor.operations)

        # Should have GROUP_END after "end"
        assert "after:literal:end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:literal:end"]
        assert any(op.operation_type == OperationType.GROUP_END for op in to_anchor.operations)

    def test_rule_with_group_and_other_statements(self):
        """Test parsing rule with group and other statements."""
        fmt_text = """rule stmt {
    ws_allowed: nbsp;
    group from "if" to ";";
    after condition { hard; };
}"""
        config = parse_format_config(fmt_text)

        # Check all configurations are present
        rule_config = config.rule_configs["stmt"]
        assert rule_config.ws_allowed_spacing == NBSP

        # Check group operations
        assert "before:literal:if" in rule_config.anchor_configs
        assert "after:literal:;" in rule_config.anchor_configs

        # Check after spacing for condition
        assert "after:label:condition" in rule_config.anchor_configs
        condition_anchor = rule_config.anchor_configs["after:label:condition"]
        spacing_ops = [op for op in condition_anchor.operations if op.operation_type == OperationType.SPACING]
        assert len(spacing_ops) == 1
        assert spacing_ops[0].spacing == HARDLINE

    def test_after_before_with_anchor_syntax(self):
        """Test that after/before work with anchor syntax."""
        fmt_text = """
after ";" { hard; };
before operator { nbsp; };

rule expr {
    after value { soft; };
    before "(" { nil; };
}
"""
        config = parse_format_config(fmt_text)

        # Check global configs
        assert "after:literal:;" in config.anchor_configs
        global_after = config.anchor_configs["after:literal:;"]
        assert len(global_after.operations) == 1
        assert global_after.operations[0].operation_type == OperationType.SPACING
        assert global_after.operations[0].spacing == HARDLINE

        assert "before:label:operator" in config.anchor_configs
        global_before = config.anchor_configs["before:label:operator"]
        assert len(global_before.operations) == 1
        assert global_before.operations[0].operation_type == OperationType.SPACING
        assert global_before.operations[0].spacing == NBSP

        # Check rule-specific configs
        rule_config = config.rule_configs["expr"]
        assert "after:label:value" in rule_config.anchor_configs
        rule_after = rule_config.anchor_configs["after:label:value"]
        assert len(rule_after.operations) == 1
        assert rule_after.operations[0].operation_type == OperationType.SPACING
        assert rule_after.operations[0].spacing == SOFTLINE

        assert "before:literal:(" in rule_config.anchor_configs
        rule_before = rule_config.anchor_configs["before:literal:("]
        assert len(rule_before.operations) == 1
        assert rule_before.operations[0].operation_type == OperationType.SPACING
        assert rule_before.operations[0].spacing == NIL

    def test_nest_config(self):
        """Test parsing nest configuration."""
        fmt_text = """rule expr {
    nest;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        nest_begin_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_begin_ops) == 1
        assert nest_begin_ops[0].indent == 1  # default indent

        # Should have NEST_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        nest_end_ops = [op for op in end_anchor.operations if op.operation_type == OperationType.NEST_END]
        assert len(nest_end_ops) == 1

    def test_nest_config_with_indent(self):
        """Test parsing nest configuration with custom indent."""
        fmt_text = """rule expr {
    nest 2;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Check indent value
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        nest_begin_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_begin_ops) == 1
        assert nest_begin_ops[0].indent == 2

    def test_multiple_groups_and_nests(self):
        """Test multiple groups and nests with ordering."""
        fmt_text = """rule expr {
    group from "(" to ")";
    group from "[" to "]";
    nest from "{" to "}";
    after "{" { hard; };
    before "}" { hard; };
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Check operations at "{" anchor
        # NEST_BEGIN should be before "{" (inclusive)
        assert "before:literal:{" in rule_config.anchor_configs
        brace_before = rule_config.anchor_configs["before:literal:{"]
        assert len(brace_before.operations) == 1
        assert brace_before.operations[0].operation_type == OperationType.NEST_BEGIN

        # Spacing should be after "{"
        assert "after:literal:{" in rule_config.anchor_configs
        brace_after = rule_config.anchor_configs["after:literal:{"]
        assert len(brace_after.operations) == 1
        assert brace_after.operations[0].operation_type == OperationType.SPACING
        assert brace_after.operations[0].spacing == HARDLINE

        # Check operations at "}" anchor
        # Spacing should be before "}"
        assert "before:literal:}" in rule_config.anchor_configs
        brace_before_2 = rule_config.anchor_configs["before:literal:}"]
        assert len(brace_before_2.operations) == 1
        assert brace_before_2.operations[0].operation_type == OperationType.SPACING
        assert brace_before_2.operations[0].spacing == HARDLINE

        # NEST_END should be after "}" (inclusive)
        assert "after:literal:}" in rule_config.anchor_configs
        brace_after_2 = rule_config.anchor_configs["after:literal:}"]
        assert len(brace_after_2.operations) == 1
        assert brace_after_2.operations[0].operation_type == OperationType.NEST_END

        # Check first group
        assert "before:literal:(" in rule_config.anchor_configs
        paren_before = rule_config.anchor_configs["before:literal:("]
        assert len(paren_before.operations) == 1
        assert paren_before.operations[0].operation_type == OperationType.GROUP_BEGIN

        # Check second group
        assert "before:literal:[" in rule_config.anchor_configs
        bracket_before = rule_config.anchor_configs["before:literal:["]
        assert len(bracket_before.operations) == 1
        assert bracket_before.operations[0].operation_type == OperationType.GROUP_BEGIN

    def test_global_and_rule_operations_merged(self):
        """Test that global and rule operations at the same anchor are merged."""
        fmt_text = """
after ";" { hard; };

rule expr {
    group to ";";
}"""
        config = parse_format_config(fmt_text)

        # Check global operation
        assert "after:literal:;" in config.anchor_configs
        global_anchor = config.anchor_configs["after:literal:;"]
        assert len(global_anchor.operations) == 1
        assert global_anchor.operations[0].operation_type == OperationType.SPACING
        assert global_anchor.operations[0].spacing == HARDLINE

        # Check rule operation
        rule_config = config.rule_configs["expr"]
        assert "after:literal:;" in rule_config.anchor_configs
        rule_anchor = rule_config.anchor_configs["after:literal:;"]
        # GROUP_END should be inserted at beginning
        assert len(rule_anchor.operations) == 1
        assert rule_anchor.operations[0].operation_type == OperationType.GROUP_END

        # Now test the merged behavior
        anchor_config = config.get_anchor_config("expr", "after", ItemSelector.LITERAL, ";")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 2
        # Global operations come first (SPACING), then rule operations (GROUP_END)
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == HARDLINE
        assert anchor_config.operations[1].operation_type == OperationType.GROUP_END

    def test_rule_spacing_overrides_global(self):
        """Test that rule spacing operations completely override global spacing."""
        fmt_text = """
after ";" { hard; };

rule expr {
    after ";" { soft; };
    group to ";";
}"""
        config = parse_format_config(fmt_text)

        # Now test the merged behavior - rule spacing should override global
        anchor_config = config.get_anchor_config("expr", "after", ItemSelector.LITERAL, ";")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 2

        # Should have rule spacing (not global) and group end
        spacing_ops = [op for op in anchor_config.operations if op.operation_type == OperationType.SPACING]
        assert len(spacing_ops) == 1
        assert spacing_ops[0].spacing == SOFTLINE  # Rule override, not global HARDLINE

        group_ops = [op for op in anchor_config.operations if op.operation_type == OperationType.GROUP_END]
        assert len(group_ops) == 1

    def test_global_spacing_and_rule_group_merge(self):
        """Test that global spacing and rule group/nest operations merge correctly."""
        fmt_text = """
before "(" { nbsp; };
after ")" { hard; };

rule expr {
    group from "(" to ")";
    nest 2 from "(" to ")";
}"""
        config = parse_format_config(fmt_text)

        # Test at "(" anchor - should have global spacing followed by rule group/nest begins
        anchor_config = config.get_anchor_config("expr", "before", ItemSelector.LITERAL, "(")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 3
        # Global spacing first
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == NBSP
        # Then rule group/nest operations
        assert anchor_config.operations[1].operation_type == OperationType.GROUP_BEGIN
        assert anchor_config.operations[2].operation_type == OperationType.NEST_BEGIN
        assert anchor_config.operations[2].indent == 2

        # Test at ")" anchor - should have global spacing and rule group/nest ends
        anchor_config = config.get_anchor_config("expr", "after", ItemSelector.LITERAL, ")")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 3
        # Global spacing first
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == HARDLINE
        # Then rule operations (which were inserted at beginning, so NEST_END before GROUP_END)
        assert anchor_config.operations[1].operation_type == OperationType.NEST_END
        assert anchor_config.operations[2].operation_type == OperationType.GROUP_END

    def test_operation_ordering_preserved(self):
        """Test that operations at an anchor preserve their definition order."""
        fmt_text = """rule expr {
    group from "(" to ")";
    nest from "(" to ")";
    after "(" { hard; };
    before ")" { soft; };
    group from ")" to "]";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Check operations at "(" anchor
        # Before "(": GROUP_BEGIN, NEST_BEGIN
        assert "before:literal:(" in rule_config.anchor_configs
        paren_before = rule_config.anchor_configs["before:literal:("]
        assert len(paren_before.operations) == 2
        assert paren_before.operations[0].operation_type == OperationType.GROUP_BEGIN
        assert paren_before.operations[1].operation_type == OperationType.NEST_BEGIN

        # After "(": SPACING
        assert "after:literal:(" in rule_config.anchor_configs
        paren_after = rule_config.anchor_configs["after:literal:("]
        assert len(paren_after.operations) == 1
        assert paren_after.operations[0].operation_type == OperationType.SPACING
        assert paren_after.operations[0].spacing == HARDLINE

        # Check operations at ")" anchor
        # Before ")": SPACING, GROUP_BEGIN (for second group)
        assert "before:literal:)" in rule_config.anchor_configs
        paren_before_2 = rule_config.anchor_configs["before:literal:)"]
        assert len(paren_before_2.operations) == 2
        assert paren_before_2.operations[0].operation_type == OperationType.SPACING
        assert paren_before_2.operations[0].spacing == SOFTLINE
        assert paren_before_2.operations[1].operation_type == OperationType.GROUP_BEGIN

        # After ")": GROUP_END, NEST_END
        assert "after:literal:)" in rule_config.anchor_configs
        paren_after_2 = rule_config.anchor_configs["after:literal:)"]
        assert len(paren_after_2.operations) == 2
        # Operations should be in reverse order for proper unwinding
        assert paren_after_2.operations[0].operation_type == OperationType.NEST_END
        assert paren_after_2.operations[1].operation_type == OperationType.GROUP_END

    def test_omit_global(self):
        """Test parsing global omit statement."""
        fmt_text = """omit semicolon;"""
        config = parse_format_config(fmt_text)

        # Check that global omit is configured
        assert "before:label:semicolon" in config.anchor_configs
        anchor_config = config.anchor_configs["before:label:semicolon"]
        assert anchor_config.disposition is OMIT

    def test_omit_literal(self):
        """Test parsing omit statement with literal."""
        fmt_text = """omit ";";"""
        config = parse_format_config(fmt_text)

        # Check that literal omit is configured
        assert "before:literal:;" in config.anchor_configs
        anchor_config = config.anchor_configs["before:literal:;"]
        assert anchor_config.disposition is OMIT

    def test_omit_in_rule(self):
        """Test parsing omit statement inside rule configuration."""
        fmt_text = """rule stmt {
    omit semicolon;
    omit ",";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["stmt"]

        # Check label omit
        assert "before:label:semicolon" in rule_config.anchor_configs
        anchor_config = rule_config.anchor_configs["before:label:semicolon"]
        assert anchor_config.disposition is OMIT

        # Check literal omit
        assert "before:literal:," in rule_config.anchor_configs
        anchor_config = rule_config.anchor_configs["before:literal:,"]
        assert anchor_config.disposition is OMIT

    def test_get_item_disposition_api(self):
        """Test the get_item_disposition API method."""
        config = FormatterConfig()

        # Create a test item with a label
        literal = gsm.Literal(value=";")
        item_with_label = gsm.Item(
            term=literal, label="semicolon", disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED
        )
        item_without_label = gsm.Item(
            term=literal, label=None, disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED
        )

        # Initially everything should be Normal
        assert isinstance(config.get_item_disposition("test_rule", item_with_label), Normal)
        assert isinstance(config.get_item_disposition("test_rule", item_without_label), Normal)

        # Add global omit for label
        anchor_config = AnchorConfig(
            selector_type=ItemSelector.LABEL,
            selector_value="semicolon",
            disposition=OMIT,
        )
        config.anchor_configs["before:label:semicolon"] = anchor_config

        # Now labeled item should be Omit
        assert isinstance(config.get_item_disposition("test_rule", item_with_label), Omit)
        assert isinstance(config.get_item_disposition("test_rule", item_without_label), Normal)

        # Add global omit for literal
        anchor_config2 = AnchorConfig(selector_type=ItemSelector.LITERAL, selector_value=";", disposition=OMIT)
        config.anchor_configs["before:literal:;"] = anchor_config2

        # Now both should be Omit
        assert isinstance(config.get_item_disposition("test_rule", item_with_label), Omit)
        assert isinstance(config.get_item_disposition("test_rule", item_without_label), Omit)

    def test_omit_with_mixed_operations(self):
        """Test omit mixed with other operations at the same anchor."""
        fmt_text = """
after semicolon { hard; };
rule stmt {
    omit semicolon;
    group to semicolon;
}"""
        config = parse_format_config(fmt_text)

        # Check global after config
        assert "after:label:semicolon" in config.anchor_configs
        global_after = config.anchor_configs["after:label:semicolon"]
        assert len(global_after.operations) == 1
        assert global_after.operations[0].operation_type == OperationType.SPACING

        # Check rule omit config
        rule_config = config.rule_configs["stmt"]
        assert "before:label:semicolon" in rule_config.anchor_configs
        rule_before = rule_config.anchor_configs["before:label:semicolon"]
        assert rule_before.disposition is OMIT

        # Check rule group end config
        assert "after:label:semicolon" in rule_config.anchor_configs
        rule_after = rule_config.anchor_configs["after:label:semicolon"]
        assert len(rule_after.operations) == 1
        assert rule_after.operations[0].operation_type == OperationType.GROUP_END

        # Test merged behavior with API
        literal = gsm.Literal(value=";")
        item = gsm.Item(term=literal, label="semicolon", disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED)
        assert isinstance(config.get_item_disposition("stmt", item), Omit)

    def test_render_global(self):
        """Test parsing global render statement."""
        fmt_text = """render semicolon as nbsp;"""
        config = parse_format_config(fmt_text)

        # Check that global render is configured
        assert "before:label:semicolon" in config.anchor_configs
        anchor_config = config.anchor_configs["before:label:semicolon"]
        assert isinstance(anchor_config.disposition, RenderAs)
        assert anchor_config.disposition.spacing is NBSP

    def test_render_literal(self):
        """Test parsing render statement with literal."""
        fmt_text = """render ";" as hard;"""
        config = parse_format_config(fmt_text)

        # Check that literal render is configured
        assert "before:literal:;" in config.anchor_configs
        anchor_config = config.anchor_configs["before:literal:;"]
        assert isinstance(anchor_config.disposition, RenderAs)
        assert anchor_config.disposition.spacing is HARDLINE

    def test_render_in_rule(self):
        """Test parsing render statement inside rule configuration."""
        fmt_text = """rule stmt {
    render semicolon as soft;
    render "," as nil;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["stmt"]

        # Check label render
        assert "before:label:semicolon" in rule_config.anchor_configs
        anchor_config = rule_config.anchor_configs["before:label:semicolon"]
        assert isinstance(anchor_config.disposition, RenderAs)
        assert anchor_config.disposition.spacing is SOFTLINE

        # Check literal render
        assert "before:literal:," in rule_config.anchor_configs
        anchor_config = rule_config.anchor_configs["before:literal:,"]
        assert isinstance(anchor_config.disposition, RenderAs)
        assert anchor_config.disposition.spacing is NIL

    def test_render_api(self):
        """Test the get_item_disposition API method with render."""
        config = FormatterConfig()

        # Create a test item with a label
        literal = gsm.Literal(value=";")
        item_with_label = gsm.Item(
            term=literal, label="semicolon", disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED
        )
        item_without_label = gsm.Item(
            term=literal, label=None, disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED
        )

        # Add global render for label
        anchor_config = AnchorConfig(
            selector_type=ItemSelector.LABEL, selector_value="semicolon", disposition=RenderAs(spacing=NBSP)
        )
        config.anchor_configs["before:label:semicolon"] = anchor_config

        # Now labeled item should be Render with NBSP
        disposition = config.get_item_disposition("test_rule", item_with_label)
        assert isinstance(disposition, RenderAs)
        assert disposition.spacing == NBSP
        assert isinstance(config.get_item_disposition("test_rule", item_without_label), Normal)

        # Add global render for literal
        anchor_config2 = AnchorConfig(
            selector_type=ItemSelector.LITERAL,
            selector_value=";",
            disposition=RenderAs(spacing=HARDLINE),
        )
        config.anchor_configs["before:literal:;"] = anchor_config2

        # Now both should be Render (label takes precedence)
        disposition = config.get_item_disposition("test_rule", item_with_label)
        assert isinstance(disposition, RenderAs)
        assert disposition.spacing == NBSP  # Label render takes precedence

        disposition2 = config.get_item_disposition("test_rule", item_without_label)
        assert isinstance(disposition2, RenderAs)
        assert disposition2.spacing == HARDLINE

    def test_render_with_mixed_operations(self):
        """Test render mixed with other operations at the same anchor."""
        fmt_text = """
after semicolon { hard; };
rule stmt {
    render semicolon as soft;
    group to semicolon;
}"""
        config = parse_format_config(fmt_text)

        # Check global after config
        assert "after:label:semicolon" in config.anchor_configs
        global_after = config.anchor_configs["after:label:semicolon"]
        assert len(global_after.operations) == 1
        assert global_after.operations[0].operation_type == OperationType.SPACING

        # Check rule render config
        rule_config = config.rule_configs["stmt"]
        assert "before:label:semicolon" in rule_config.anchor_configs
        rule_before = rule_config.anchor_configs["before:label:semicolon"]
        assert isinstance(rule_before.disposition, RenderAs)
        assert rule_before.disposition.spacing is SOFTLINE

        # Check rule group end config
        assert "after:label:semicolon" in rule_config.anchor_configs
        rule_after = rule_config.anchor_configs["after:label:semicolon"]
        assert len(rule_after.operations) == 1
        assert rule_after.operations[0].operation_type == OperationType.GROUP_END

        # Test merged behavior with API
        literal = gsm.Literal(value=";")
        item = gsm.Item(term=literal, label="semicolon", disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED)
        disposition = config.get_item_disposition("stmt", item)
        assert isinstance(disposition, RenderAs)
        assert disposition.spacing == SOFTLINE

    def test_omit_vs_render_precedence(self):
        """Test that omit and render at the same anchor are handled correctly."""
        fmt_text = """
omit semicolon;
rule stmt {
    render semicolon as hard;
}"""
        config = parse_format_config(fmt_text)

        # In rule "stmt", render should override global omit
        literal = gsm.Literal(value=";")
        item = gsm.Item(term=literal, label="semicolon", disposition=gsm.Disposition.INCLUDE, quantifier=gsm.REQUIRED)

        # For stmt rule, should get Render
        disposition = config.get_item_disposition("stmt", item)
        assert isinstance(disposition, RenderAs)
        assert disposition.spacing == HARDLINE

        # For other rules, should get Omit
        disposition = config.get_item_disposition("other_rule", item)
        assert isinstance(disposition, Omit)

    def test_get_anchor_config_fallback_to_global(self):
        """Test that get_anchor_config returns global config when rule has no specific config."""
        fmt_text = """
after ";" { hard; };
before "(" { nbsp; };
group from "{" to "}";

rule expr {
    // This rule has some config but not for the anchors we'll test
    ws_allowed: soft;
}

rule stmt {
    // This rule has no anchor configs at all
    ws_required: bsp;
}
"""
        config = parse_format_config(fmt_text)

        # Test that expr rule (which has no anchor configs) gets global configs
        anchor_config = config.get_anchor_config("expr", "after", ItemSelector.LITERAL, ";")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == HARDLINE

        anchor_config = config.get_anchor_config("expr", "before", ItemSelector.LITERAL, "(")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == NBSP

        # Test that stmt rule (which also has no anchor configs) gets global configs
        anchor_config = config.get_anchor_config("stmt", "after", ItemSelector.LITERAL, ";")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == HARDLINE

        # Test global group operations
        anchor_config = config.get_anchor_config("stmt", "before", ItemSelector.LITERAL, "{")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.GROUP_BEGIN

        anchor_config = config.get_anchor_config("stmt", "after", ItemSelector.LITERAL, "}")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.GROUP_END

        # Test that a rule that doesn't exist in config also gets global configs
        anchor_config = config.get_anchor_config("nonexistent_rule", "before", ItemSelector.LITERAL, "{")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.GROUP_BEGIN

        anchor_config = config.get_anchor_config("nonexistent_rule", "after", ItemSelector.LITERAL, "}")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.GROUP_END

        anchor_config = config.get_anchor_config("nonexistent_rule", "after", ItemSelector.LITERAL, ";")
        assert anchor_config is not None
        assert len(anchor_config.operations) == 1
        assert anchor_config.operations[0].operation_type == OperationType.SPACING
        assert anchor_config.operations[0].spacing == HARDLINE

        # Test that when no global config exists, we get None
        anchor_config = config.get_anchor_config("expr", "after", ItemSelector.LITERAL, "nonexistent")
        assert anchor_config is None

    def test_group_with_from_after(self):
        """Test parsing group configuration with 'from after' (non-inclusive start)."""
        fmt_text = """rule expr {
    group from after "(" to ")";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # GROUP_BEGIN should be AFTER "(" (non-inclusive)
        assert "after:literal:(" in rule_config.anchor_configs
        after_paren = rule_config.anchor_configs["after:literal:("]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in after_paren.operations)

        # GROUP_END should still be AFTER ")" (inclusive)
        assert "after:literal:)" in rule_config.anchor_configs
        after_close = rule_config.anchor_configs["after:literal:)"]
        assert any(op.operation_type == OperationType.GROUP_END for op in after_close.operations)

    def test_group_with_to_before(self):
        """Test parsing group configuration with 'to before' (non-inclusive end)."""
        fmt_text = """rule expr {
    group from "{" to before "}";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # GROUP_BEGIN should be BEFORE "{" (inclusive)
        assert "before:literal:{" in rule_config.anchor_configs
        before_brace = rule_config.anchor_configs["before:literal:{"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in before_brace.operations)

        # GROUP_END should be BEFORE "}" (non-inclusive)
        assert "before:literal:}" in rule_config.anchor_configs
        before_close = rule_config.anchor_configs["before:literal:}"]
        assert any(op.operation_type == OperationType.GROUP_END for op in before_close.operations)

    def test_group_with_both_modifiers(self):
        """Test parsing group configuration with both 'from after' and 'to before'."""
        fmt_text = """rule stmt {
    group from after keyword to before semicolon;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["stmt"]

        # GROUP_BEGIN should be AFTER keyword (non-inclusive)
        assert "after:label:keyword" in rule_config.anchor_configs
        after_keyword = rule_config.anchor_configs["after:label:keyword"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in after_keyword.operations)

        # GROUP_END should be BEFORE semicolon (non-inclusive)
        assert "before:label:semicolon" in rule_config.anchor_configs
        before_semi = rule_config.anchor_configs["before:label:semicolon"]
        assert any(op.operation_type == OperationType.GROUP_END for op in before_semi.operations)

    def test_nest_with_from_after(self):
        """Test parsing nest configuration with 'from after' (non-inclusive start)."""
        fmt_text = """rule expr {
    nest 2 from after "[" to "]";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # NEST_BEGIN should be AFTER "[" (non-inclusive)
        assert "after:literal:[" in rule_config.anchor_configs
        after_bracket = rule_config.anchor_configs["after:literal:["]
        nest_ops = [op for op in after_bracket.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 2

        # NEST_END should still be AFTER "]" (inclusive)
        assert "after:literal:]" in rule_config.anchor_configs
        after_close = rule_config.anchor_configs["after:literal:]"]
        assert any(op.operation_type == OperationType.NEST_END for op in after_close.operations)

    def test_nest_with_to_before(self):
        """Test parsing nest configuration with 'to before' (non-inclusive end)."""
        fmt_text = """rule expr {
    nest from "begin" to before "end";
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # NEST_BEGIN should be BEFORE "begin" (inclusive)
        assert "before:literal:begin" in rule_config.anchor_configs
        before_begin = rule_config.anchor_configs["before:literal:begin"]
        nest_ops = [op for op in before_begin.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 1  # default indent

        # NEST_END should be BEFORE "end" (non-inclusive)
        assert "before:literal:end" in rule_config.anchor_configs
        before_end = rule_config.anchor_configs["before:literal:end"]
        assert any(op.operation_type == OperationType.NEST_END for op in before_end.operations)

    def test_nest_with_both_modifiers_and_indent(self):
        """Test parsing nest configuration with both modifiers and custom indent."""
        fmt_text = """rule block {
    nest 3 from after open_brace to before close_brace;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["block"]

        # NEST_BEGIN should be AFTER open_brace (non-inclusive)
        assert "after:label:open_brace" in rule_config.anchor_configs
        after_open = rule_config.anchor_configs["after:label:open_brace"]
        nest_ops = [op for op in after_open.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 3

        # NEST_END should be BEFORE close_brace (non-inclusive)
        assert "before:label:close_brace" in rule_config.anchor_configs
        before_close = rule_config.anchor_configs["before:label:close_brace"]
        assert any(op.operation_type == OperationType.NEST_END for op in before_close.operations)

    def test_mixed_inclusive_noninclusive(self):
        """Test mixing inclusive and non-inclusive endpoints in different statements."""
        fmt_text = """rule complex {
    group from "[" to before "]";
    nest from after "{" to "}";
    after "[" { hard; };
    before "]" { soft; };
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["complex"]

        # Group: inclusive start at "[", non-inclusive end before "]"
        assert "before:literal:[" in rule_config.anchor_configs
        before_bracket = rule_config.anchor_configs["before:literal:["]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in before_bracket.operations)

        assert "before:literal:]" in rule_config.anchor_configs
        before_bracket_close = rule_config.anchor_configs["before:literal:]"]
        # Should have both GROUP_END and spacing
        assert any(op.operation_type == OperationType.GROUP_END for op in before_bracket_close.operations)
        assert any(
            op.operation_type == OperationType.SPACING and op.spacing == SOFTLINE
            for op in before_bracket_close.operations
        )

        # Nest: non-inclusive start after "{", inclusive end at "}"
        assert "after:literal:{" in rule_config.anchor_configs
        after_brace = rule_config.anchor_configs["after:literal:{"]
        assert any(op.operation_type == OperationType.NEST_BEGIN for op in after_brace.operations)

        assert "after:literal:}" in rule_config.anchor_configs
        after_brace_close = rule_config.anchor_configs["after:literal:}"]
        assert any(op.operation_type == OperationType.NEST_END for op in after_brace_close.operations)

        # Spacing after "["
        assert "after:literal:[" in rule_config.anchor_configs
        after_bracket = rule_config.anchor_configs["after:literal:["]
        assert any(
            op.operation_type == OperationType.SPACING and op.spacing == HARDLINE for op in after_bracket.operations
        )

    def test_global_group_with_modifiers(self):
        """Test global group configuration with from/to modifiers."""
        fmt_text = """
group from after "START" to before "END";

rule test {
    ws_allowed: nbsp;
}"""
        config = parse_format_config(fmt_text)

        # Check global group operations
        assert "after:literal:START" in config.anchor_configs
        after_start = config.anchor_configs["after:literal:START"]
        assert any(op.operation_type == OperationType.GROUP_BEGIN for op in after_start.operations)

        assert "before:literal:END" in config.anchor_configs
        before_end = config.anchor_configs["before:literal:END"]
        assert any(op.operation_type == OperationType.GROUP_END for op in before_end.operations)

    def test_global_nest_with_modifiers(self):
        """Test global nest configuration with from/to modifiers."""
        fmt_text = """
nest 4 from after open to before close;

rule test {
    ws_required: hard;
}"""
        config = parse_format_config(fmt_text)

        # Check global nest operations
        assert "after:label:open" in config.anchor_configs
        after_open = config.anchor_configs["after:label:open"]
        nest_ops = [op for op in after_open.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 4

        assert "before:label:close" in config.anchor_configs
        before_close = config.anchor_configs["before:label:close"]
        assert any(op.operation_type == OperationType.NEST_END for op in before_close.operations)

    def test_join_config(self):
        """Test parsing join configuration."""
        fmt_text = """rule expr {
    join soft;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have JOIN_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_begin_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_begin_ops) == 1
        assert join_begin_ops[0].separator == SOFTLINE

        # Should have JOIN_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        join_end_ops = [op for op in end_anchor.operations if op.operation_type == OperationType.JOIN_END]
        assert len(join_end_ops) == 1

    def test_join_config_with_complex_separator(self):
        """Test parsing join configuration with complex separator."""
        fmt_text = """rule list {
    join concat([hard, nbsp, nbsp]);
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["list"]

        # Check separator is parsed correctly
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_begin_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_begin_ops) == 1

        separator = join_begin_ops[0].separator
        assert isinstance(separator, Concat)
        assert len(separator.docs) == 3
        assert separator.docs[0] == HARDLINE
        assert separator.docs[1] == NBSP
        assert separator.docs[2] == NBSP

    def test_join_config_with_from(self):
        """Test parsing join configuration with from anchor."""
        fmt_text = """rule expr {
    join from list_start bsp;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have JOIN_BEGIN before list_start
        assert "before:label:list_start" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:list_start"]
        join_ops = [op for op in from_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == LINE

        # Should have JOIN_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        assert any(op.operation_type == OperationType.JOIN_END for op in end_anchor.operations)

    def test_join_config_with_to(self):
        """Test parsing join configuration with to anchor."""
        fmt_text = """rule expr {
    join to "end" hard;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have JOIN_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == HARDLINE

        # Should have JOIN_END after "end"
        assert "after:literal:end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:literal:end"]
        assert any(op.operation_type == OperationType.JOIN_END for op in to_anchor.operations)

    def test_join_config_with_from_and_to(self):
        """Test parsing join configuration with both from and to anchors."""
        fmt_text = """rule expr {
    join from items_start to items_end nil;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Should have JOIN_BEGIN before items_start
        assert "before:label:items_start" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:items_start"]
        join_ops = [op for op in from_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == NIL

        # Should have JOIN_END after items_end
        assert "after:label:items_end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:label:items_end"]
        assert any(op.operation_type == OperationType.JOIN_END for op in to_anchor.operations)

    def test_join_with_from_after(self):
        """Test parsing join configuration with 'from after' (non-inclusive start)."""
        fmt_text = """rule list {
    join from after "[" to "]" nbsp;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["list"]

        # JOIN_BEGIN should be AFTER "[" (non-inclusive)
        assert "after:literal:[" in rule_config.anchor_configs
        after_bracket = rule_config.anchor_configs["after:literal:["]
        join_ops = [op for op in after_bracket.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == NBSP

        # JOIN_END should still be AFTER "]" (inclusive)
        assert "after:literal:]" in rule_config.anchor_configs
        after_close = rule_config.anchor_configs["after:literal:]"]
        assert any(op.operation_type == OperationType.JOIN_END for op in after_close.operations)

    def test_join_with_to_before(self):
        """Test parsing join configuration with 'to before' (non-inclusive end)."""
        fmt_text = """rule list {
    join from "{" to before "}" soft;
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["list"]

        # JOIN_BEGIN should be BEFORE "{" (inclusive)
        assert "before:literal:{" in rule_config.anchor_configs
        before_brace = rule_config.anchor_configs["before:literal:{"]
        join_ops = [op for op in before_brace.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == SOFTLINE

        # JOIN_END should be BEFORE "}" (non-inclusive)
        assert "before:literal:}" in rule_config.anchor_configs
        before_close = rule_config.anchor_configs["before:literal:}"]
        assert any(op.operation_type == OperationType.JOIN_END for op in before_close.operations)

    def test_join_with_both_modifiers(self):
        """Test parsing join configuration with both 'from after' and 'to before'."""
        fmt_text = """rule items {
    join from after start_marker to before end_marker concat([bsp, text("-"), bsp]);
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["items"]

        # JOIN_BEGIN should be AFTER start_marker (non-inclusive)
        assert "after:label:start_marker" in rule_config.anchor_configs
        after_start = rule_config.anchor_configs["after:label:start_marker"]
        join_ops = [op for op in after_start.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1

        separator = join_ops[0].separator
        assert isinstance(separator, Concat)
        assert len(separator.docs) == 3
        assert separator.docs[0] == LINE
        assert isinstance(separator.docs[1], Text)
        assert separator.docs[1].content == "-"
        assert separator.docs[2] == LINE

        # JOIN_END should be BEFORE end_marker (non-inclusive)
        assert "before:label:end_marker" in rule_config.anchor_configs
        before_end = rule_config.anchor_configs["before:label:end_marker"]
        assert any(op.operation_type == OperationType.JOIN_END for op in before_end.operations)

    def test_global_join_config(self):
        """Test global join configuration."""
        fmt_text = """
join hard;

rule test {
    ws_allowed: nbsp;
}"""
        config = parse_format_config(fmt_text)

        # Check global join operations
        assert "before:rule_start:" in config.anchor_configs
        start_anchor = config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == HARDLINE

        assert "after:rule_end:" in config.anchor_configs
        end_anchor = config.anchor_configs["after:rule_end:"]
        assert any(op.operation_type == OperationType.JOIN_END for op in end_anchor.operations)

    def test_global_join_with_modifiers(self):
        """Test global join configuration with from/to modifiers."""
        fmt_text = """
join from after "BEGIN" to before "END" soft;

rule test {
    ws_required: hard;
}"""
        config = parse_format_config(fmt_text)

        # Check global join operations
        assert "after:literal:BEGIN" in config.anchor_configs
        after_begin = config.anchor_configs["after:literal:BEGIN"]
        join_ops = [op for op in after_begin.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == SOFTLINE

        assert "before:literal:END" in config.anchor_configs
        before_end = config.anchor_configs["before:literal:END"]
        assert any(op.operation_type == OperationType.JOIN_END for op in before_end.operations)

    def test_multiple_operations_with_join(self):
        """Test multiple operations including join with proper ordering."""
        fmt_text = """rule expr {
    group from "(" to ")";
    nest 2 from "{" to "}";
    join from "[" to "]" nbsp;
    after "{" { hard; };
    before "}" { hard; };
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["expr"]

        # Check join operations at "[" anchor
        assert "before:literal:[" in rule_config.anchor_configs
        bracket_before = rule_config.anchor_configs["before:literal:["]
        join_ops = [op for op in bracket_before.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == NBSP

        # Check join end at "]" anchor
        assert "after:literal:]" in rule_config.anchor_configs
        bracket_after = rule_config.anchor_configs["after:literal:]"]
        assert any(op.operation_type == OperationType.JOIN_END for op in bracket_after.operations)

        # Verify other operations still work
        assert "before:literal:(" in rule_config.anchor_configs
        assert "before:literal:{" in rule_config.anchor_configs

    def test_join_with_group_combinator_separator(self):
        """Test join with group combinator as separator."""
        fmt_text = """rule items {
    join group(concat([soft, text("|"), soft]));
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["items"]

        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1

        separator = join_ops[0].separator
        assert isinstance(separator, Group)
        assert isinstance(separator.content, Concat)
        assert len(separator.content.docs) == 3
        assert separator.content.docs[0] == SOFTLINE
        assert isinstance(separator.content.docs[1], Text)
        assert separator.content.docs[1].content == "|"
        assert separator.content.docs[2] == SOFTLINE

    def test_join_with_nested_combinator_separator(self):
        """Test join with nest combinator as separator."""
        fmt_text = """rule block {
    join nest(concat([hard, hard]));
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["block"]

        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1

        separator = join_ops[0].separator
        assert isinstance(separator, Nest)
        assert separator.indent == 1  # default indent
        assert isinstance(separator.content, Concat)
        assert len(separator.content.docs) == 2
        assert separator.content.docs[0] == HARDLINE
        assert separator.content.docs[1] == HARDLINE

    def test_join_with_join_literal_separator(self):
        """Test join with another join as separator (nested joins)."""
        fmt_text = """rule complex {
    join join(nbsp, [hard, hard]);
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["complex"]

        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1

        separator = join_ops[0].separator
        assert isinstance(separator, Join)
        assert separator.separator == NBSP
        assert len(separator.docs) == 2
        assert separator.docs[0] == HARDLINE
        assert separator.docs[1] == HARDLINE

    def test_rule_with_all_operations(self):
        """Test rule with group, nest, and join operations combined."""
        fmt_text = """rule complex {
    ws_allowed: nbsp;
    group from "(" to ")";
    nest 2 from "{" to "}";
    join from "[" to "]" soft;
    after "(" { bsp; };
    before ")" { bsp; };
}"""
        config = parse_format_config(fmt_text)

        # Check all configurations are present
        rule_config = config.rule_configs["complex"]
        assert rule_config.ws_allowed_spacing == NBSP

        # Check group operations
        assert "before:literal:(" in rule_config.anchor_configs
        assert "after:literal:)" in rule_config.anchor_configs

        # Check nest operations
        assert "before:literal:{" in rule_config.anchor_configs
        assert "after:literal:}" in rule_config.anchor_configs

        # Check join operations
        assert "before:literal:[" in rule_config.anchor_configs
        bracket_anchor = rule_config.anchor_configs["before:literal:["]
        join_ops = [op for op in bracket_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1
        assert join_ops[0].separator == SOFTLINE

        assert "after:literal:]" in rule_config.anchor_configs
        bracket_end = rule_config.anchor_configs["after:literal:]"]
        assert any(op.operation_type == OperationType.JOIN_END for op in bracket_end.operations)

    def test_join_separator_with_blank_spacing(self):
        """Test join with blank spacing separator."""
        fmt_text = """rule spaced {
    join blank(2);
}"""
        config = parse_format_config(fmt_text)

        rule_config = config.rule_configs["spaced"]

        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        join_ops = [op for op in start_anchor.operations if op.operation_type == OperationType.JOIN_BEGIN]
        assert len(join_ops) == 1

        separator = join_ops[0].separator
        assert isinstance(separator, HardLine)
        assert separator.blank_lines == 2

    def test_global_nest_with_rule_join_overlapping_anchors(self):
        """Test global nest and rule join with overlapping from/to anchors."""
        fmt_text = """
nest from after "{" to before "}";
rule foo {
    join from after "{" to before "}" bsp;
}"""
        config = parse_format_config(fmt_text)

        # Check global nest operations
        assert "after:literal:{" in config.anchor_configs
        global_after_brace = config.anchor_configs["after:literal:{"]
        assert len(global_after_brace.operations) == 1
        assert global_after_brace.operations[0].operation_type == OperationType.NEST_BEGIN
        assert global_after_brace.operations[0].indent == 1

        assert "before:literal:}" in config.anchor_configs
        global_before_brace = config.anchor_configs["before:literal:}"]
        assert len(global_before_brace.operations) == 1
        assert global_before_brace.operations[0].operation_type == OperationType.NEST_END

        # Check rule join operations
        rule_config = config.rule_configs["foo"]
        assert "after:literal:{" in rule_config.anchor_configs
        rule_after_brace = rule_config.anchor_configs["after:literal:{"]
        assert len(rule_after_brace.operations) == 1
        assert rule_after_brace.operations[0].operation_type == OperationType.JOIN_BEGIN
        assert rule_after_brace.operations[0].separator == LINE

        assert "before:literal:}" in rule_config.anchor_configs
        rule_before_brace = rule_config.anchor_configs["before:literal:}"]
        assert len(rule_before_brace.operations) == 1
        assert rule_before_brace.operations[0].operation_type == OperationType.JOIN_END

        # Test merged behavior - should have global nest operations followed by rule join operations
        merged_after = config.get_anchor_config("foo", "after", ItemSelector.LITERAL, "{")
        assert merged_after is not None
        assert len(merged_after.operations) == 2
        # Global NEST_BEGIN first, then rule JOIN_BEGIN
        assert merged_after.operations[0].operation_type == OperationType.NEST_BEGIN
        assert merged_after.operations[1].operation_type == OperationType.JOIN_BEGIN

        merged_before = config.get_anchor_config("foo", "before", ItemSelector.LITERAL, "}")
        assert merged_before is not None
        assert len(merged_before.operations) == 2
        # Operations should be in proper unwinding order: JOIN_END first, then NEST_END
        assert merged_before.operations[0].operation_type == OperationType.JOIN_END
        assert merged_before.operations[1].operation_type == OperationType.NEST_END
