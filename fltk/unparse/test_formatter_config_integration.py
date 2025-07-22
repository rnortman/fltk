"""Test FormatterConfig integration with actual parsing and unparsing."""

from fltk import plumbing
from fltk.fegen import gsm
from fltk.unparse.combinators import Concat, HardLine, Line, Nbsp, Nil, SoftLine, Text
from fltk.unparse.fmt_config import FormatterConfig, RuleConfig

# Test grammar with WS_ALLOWED and WS_REQUIRED separators
FORMATTER_TEST_GRAMMAR = """
ws_allowed_test := first:"a" , second:"b";
ws_required_test := first:"x" : second:"y";
mixed_test := first:"p" , second:"q" : third:"r";
"""


def create_formatter_unparser_fixture(formatter_config=None):
    """Helper to create parser and unparser with specific FormatterConfig."""
    # Parse the grammar
    grammar = plumbing.parse_grammar(FORMATTER_TEST_GRAMMAR)

    # Generate parser
    parser_result = plumbing.generate_parser(grammar, capture_trivia=True)

    # Generate unparser
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar, parser_result.cst_module_name, formatter_config=formatter_config
    )

    return parser_result, unparser_result


def test_ws_allowed_default_vs_custom():
    """Test that WS_ALLOWED behavior differs between default and custom FormatterConfig."""

    # Create unparser with default config (WS_ALLOWED = NIL)
    default_parser_result, default_unparser_result = create_formatter_unparser_fixture(formatter_config=None)

    # Create unparser with custom config (WS_ALLOWED = SOFTLINE)
    custom_config = FormatterConfig(global_ws_allowed=SoftLine(), global_ws_required=Line())
    custom_parser_result, custom_unparser_result = create_formatter_unparser_fixture(formatter_config=custom_config)

    # Parse the same input with both
    test_input = "a b"  # Input that will trigger WS_ALLOWED separator

    default_parse = plumbing.parse_text(default_parser_result, test_input, "ws_allowed_test")
    custom_parse = plumbing.parse_text(custom_parser_result, test_input, "ws_allowed_test")

    assert default_parse.success, "Failed to parse with default config"
    assert custom_parse.success, "Failed to parse with custom config"

    # Unparse with both configs
    default_doc = plumbing.unparse_cst(default_unparser_result, default_parse.cst, test_input, "ws_allowed_test")
    custom_doc = plumbing.unparse_cst(custom_unparser_result, custom_parse.cst, test_input, "ws_allowed_test")

    # Default should produce: Text("a") + Text("b") (no spacing for WS_ALLOWED with NIL)
    default_expected = Concat((Text("a"), Text("b")))

    # Custom should produce: Text("a") + SoftLine() + Text("b") (SOFTLINE for WS_ALLOWED)
    custom_expected = Concat((Text("a"), SoftLine(), Text("b")))

    assert default_doc == default_expected, f"Default: expected {default_expected}, got {default_doc}"
    assert custom_doc == custom_expected, f"Custom: expected {custom_expected}, got {custom_doc}"

    # Verify they are actually different
    assert default_doc != custom_doc, "Different configs should produce different output"


def test_ws_required_line_vs_hardline():
    """Test that WS_REQUIRED behavior differs between LINE and HARDLINE configs."""

    # Create unparser with LINE for WS_REQUIRED
    line_config = FormatterConfig(global_ws_allowed=Nil(), global_ws_required=Line())
    line_parser_result, line_unparser_result = create_formatter_unparser_fixture(formatter_config=line_config)

    # Create unparser with HARDLINE for WS_REQUIRED
    hardline_config = FormatterConfig(global_ws_allowed=Nil(), global_ws_required=HardLine())
    hardline_parser_result, hardline_unparser_result = create_formatter_unparser_fixture(
        formatter_config=hardline_config
    )

    # Parse the same input with both
    test_input = "x y"  # Input that will trigger WS_REQUIRED separator

    line_parse = plumbing.parse_text(line_parser_result, test_input, "ws_required_test")
    hardline_parse = plumbing.parse_text(hardline_parser_result, test_input, "ws_required_test")

    assert line_parse.success, "Failed to parse with LINE config"
    assert hardline_parse.success, "Failed to parse with HARDLINE config"

    # Unparse with both configs
    line_doc = plumbing.unparse_cst(line_unparser_result, line_parse.cst, test_input, "ws_required_test")
    hardline_doc = plumbing.unparse_cst(hardline_unparser_result, hardline_parse.cst, test_input, "ws_required_test")

    # LINE should produce: Text("x") + Line() + Text("y")
    line_expected = Concat((Text("x"), Line(), Text("y")))

    # HARDLINE should produce: Text("x") + HardLine() + Text("y")
    hardline_expected = Concat((Text("x"), HardLine(), Text("y")))

    assert line_doc == line_expected, f"LINE: expected {line_expected}, got {line_doc}"
    assert hardline_doc == hardline_expected, f"HARDLINE: expected {hardline_expected}, got {hardline_doc}"

    # Verify they are actually different
    assert line_doc != hardline_doc, "Different WS_REQUIRED configs should produce different output"


def test_per_rule_configuration():
    """Test that per-rule configuration overrides global defaults."""

    # Create unparser with global defaults
    global_config = FormatterConfig(global_ws_allowed=SoftLine(), global_ws_required=Line())
    global_parser_result, global_unparser_result = create_formatter_unparser_fixture(formatter_config=global_config)

    # Create unparser with rule-specific override
    rule_config = FormatterConfig(
        global_ws_allowed=SoftLine(),
        global_ws_required=Line(),
        rule_configs={"mixed_test": RuleConfig(ws_allowed_spacing=Nbsp(), ws_required_spacing=HardLine())},
    )
    rule_parser_result, rule_unparser_result = create_formatter_unparser_fixture(formatter_config=rule_config)

    # Parse input that uses both WS_ALLOWED and WS_REQUIRED
    test_input = "p q r"  # mixed_test has: "p" , "q" : "r"

    global_parse = plumbing.parse_text(global_parser_result, test_input, "mixed_test")
    rule_parse = plumbing.parse_text(rule_parser_result, test_input, "mixed_test")

    assert global_parse.success, "Failed to parse with global config"
    assert rule_parse.success, "Failed to parse with rule config"

    # Unparse with both configs
    global_doc = plumbing.unparse_cst(global_unparser_result, global_parse.cst, test_input, "mixed_test")
    rule_doc = plumbing.unparse_cst(rule_unparser_result, rule_parse.cst, test_input, "mixed_test")

    # Global should use: SoftLine for WS_ALLOWED, Line for WS_REQUIRED
    global_expected = Concat((Text("p"), SoftLine(), Text("q"), Line(), Text("r")))

    # Rule override should use: Nbsp for WS_ALLOWED, HardLine for WS_REQUIRED
    rule_expected = Concat((Text("p"), Nbsp(), Text("q"), HardLine(), Text("r")))

    assert global_doc == global_expected, f"Global: expected {global_expected}, got {global_doc}"
    assert rule_doc == rule_expected, f"Rule: expected {rule_expected}, got {rule_doc}"

    # Verify they are actually different
    assert global_doc != rule_doc, "Rule-specific config should override global config"


def test_formatter_config_get_spacing():
    """Test FormatterConfig.get_spacing_for_separator method."""
    config = FormatterConfig(
        global_ws_allowed=SoftLine(),
        global_ws_required=Line(),
        rule_configs={"test_rule": RuleConfig(ws_allowed_spacing=Nil(), ws_required_spacing=HardLine())},
    )

    # Test global defaults
    assert config.get_spacing_for_separator("unknown_rule", gsm.Separator.WS_ALLOWED) == SoftLine()
    assert config.get_spacing_for_separator("unknown_rule", gsm.Separator.WS_REQUIRED) == Line()
    assert config.get_spacing_for_separator("unknown_rule", gsm.Separator.NO_WS) == Nil()

    # Test rule-specific overrides
    assert config.get_spacing_for_separator("test_rule", gsm.Separator.WS_ALLOWED) == Nil()
    assert config.get_spacing_for_separator("test_rule", gsm.Separator.WS_REQUIRED) == HardLine()
    assert config.get_spacing_for_separator("test_rule", gsm.Separator.NO_WS) == Nil()
