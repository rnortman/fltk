"""Tests for nest configuration in formatter."""

from fltk.plumbing import parse_format_config
from fltk.unparse.fmt_config import OperationType


class TestNestConfig:
    """Test Nest configuration parsing and data structures."""

    def test_nest_config(self):
        """Test parsing nest configuration."""
        fmt_text = """rule expr {
    nest;
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created at rule start/end
        assert "expr" in config.rule_configs
        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        assert len(start_anchor.operations) == 1
        assert start_anchor.operations[0].operation_type == OperationType.NEST_BEGIN
        assert start_anchor.operations[0].indent == 1  # Default indent

        # Should have NEST_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        assert len(end_anchor.operations) == 1
        assert end_anchor.operations[0].operation_type == OperationType.NEST_END

    def test_nest_config_with_indent(self):
        """Test parsing nest configuration with custom indent."""
        fmt_text = """rule expr {
    nest 4;
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created with custom indent
        rule_config = config.rule_configs["expr"]

        # Check indent value at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        assert len(start_anchor.operations) == 1
        assert start_anchor.operations[0].operation_type == OperationType.NEST_BEGIN
        assert start_anchor.operations[0].indent == 4

    def test_nest_config_with_from(self):
        """Test parsing nest configuration with from anchor."""
        fmt_text = """rule expr {
    nest from op_token;
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created with from_anchor
        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN before op_token
        assert "before:label:op_token" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:op_token"]
        assert any(op.operation_type == OperationType.NEST_BEGIN for op in from_anchor.operations)

        # Should have NEST_END at rule end
        assert "after:rule_end:" in rule_config.anchor_configs
        end_anchor = rule_config.anchor_configs["after:rule_end:"]
        assert any(op.operation_type == OperationType.NEST_END for op in end_anchor.operations)

    def test_nest_config_with_to(self):
        """Test parsing nest configuration with to anchor."""
        fmt_text = """rule expr {
    nest to "end";
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created with to_anchor
        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN at rule start
        assert "before:rule_start:" in rule_config.anchor_configs
        start_anchor = rule_config.anchor_configs["before:rule_start:"]
        assert any(op.operation_type == OperationType.NEST_BEGIN for op in start_anchor.operations)

        # Should have NEST_END after "end"
        assert "after:literal:end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:literal:end"]
        assert any(op.operation_type == OperationType.NEST_END for op in to_anchor.operations)

    def test_nest_config_with_from_and_to(self):
        """Test parsing nest configuration with both from and to anchors."""
        fmt_text = """rule expr {
    nest from start_token to "end";
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created with both anchors
        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN before start_token
        assert "before:label:start_token" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:label:start_token"]
        assert any(op.operation_type == OperationType.NEST_BEGIN for op in from_anchor.operations)

        # Should have NEST_END after "end"
        assert "after:literal:end" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:literal:end"]
        assert any(op.operation_type == OperationType.NEST_END for op in to_anchor.operations)

    def test_nest_config_with_indent_and_anchors(self):
        """Test parsing nest configuration with indent and anchors."""
        fmt_text = """rule expr {
    nest 4 from "begin" to close_paren;
}"""
        config = parse_format_config(fmt_text)

        # Check that nest operations were created with all parameters
        rule_config = config.rule_configs["expr"]

        # Should have NEST_BEGIN before "begin" with indent 4
        assert "before:literal:begin" in rule_config.anchor_configs
        from_anchor = rule_config.anchor_configs["before:literal:begin"]
        nest_begin_ops = [op for op in from_anchor.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_begin_ops) == 1
        assert nest_begin_ops[0].indent == 4

        # Should have NEST_END after close_paren
        assert "after:label:close_paren" in rule_config.anchor_configs
        to_anchor = rule_config.anchor_configs["after:label:close_paren"]
        assert any(op.operation_type == OperationType.NEST_END for op in to_anchor.operations)

    def test_rule_with_nest_and_group(self):
        """Test parsing rule with both nest and group configurations."""
        fmt_text = """rule stmt {
    ws_allowed: nbsp;
    group from "if" to ";";
    nest 4 from "then";
    after condition { hard; };
}"""
        config = parse_format_config(fmt_text)

        # Check all configurations are present
        rule_config = config.rule_configs["stmt"]
        assert rule_config.ws_allowed_spacing is not None

        # Check group operations
        assert "before:literal:if" in rule_config.anchor_configs
        assert "after:literal:;" in rule_config.anchor_configs

        # Check nest operations starting from "then"
        assert "before:literal:then" in rule_config.anchor_configs
        then_anchor = rule_config.anchor_configs["before:literal:then"]
        nest_begin_ops = [op for op in then_anchor.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_begin_ops) == 1
        assert nest_begin_ops[0].indent == 4

        # Check after spacing for condition
        assert "after:label:condition" in rule_config.anchor_configs

    def test_multiple_rules_with_nest(self):
        """Test multiple rules with different nest configurations."""
        fmt_text = """
rule block {
    nest 4;
}

rule expr {
    nest from "(" to ")";
}

rule list {
    nest 2 from "[" to "]";
}
"""
        config = parse_format_config(fmt_text)

        # Check block rule - nest entire rule with indent 4
        block_config = config.rule_configs["block"]
        assert "before:rule_start:" in block_config.anchor_configs
        block_start = block_config.anchor_configs["before:rule_start:"]
        nest_ops = [op for op in block_start.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 4

        # Check expr rule - nest from "(" to ")"
        expr_config = config.rule_configs["expr"]
        assert "before:literal:(" in expr_config.anchor_configs
        assert "after:literal:)" in expr_config.anchor_configs

        # Check list rule - nest from "[" to "]" with indent 2
        list_config = config.rule_configs["list"]
        assert "before:literal:[" in list_config.anchor_configs
        list_start = list_config.anchor_configs["before:literal:["]
        nest_ops = [op for op in list_start.operations if op.operation_type == OperationType.NEST_BEGIN]
        assert len(nest_ops) == 1
        assert nest_ops[0].indent == 2
        assert "after:literal:]" in list_config.anchor_configs
