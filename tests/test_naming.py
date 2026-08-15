"""Tests for fltk.fegen.naming and call-site delegation."""

import pytest

from fltk.fegen.naming import protocol_module_name, protocol_module_path, snake_to_upper_camel


def test_basic_two_segments():
    assert snake_to_upper_camel("no_ws") == "NoWs"


def test_basic_three_segments():
    assert snake_to_upper_camel("foo_bar_baz") == "FooBarBaz"


def test_single_segment():
    assert snake_to_upper_camel("foo") == "Foo"


def test_consecutive_underscores_collapse():
    assert snake_to_upper_camel("a__b") == "AB"


def test_leading_underscore_collapses():
    assert snake_to_upper_camel("_foo_bar") == "FooBar"


def test_trailing_underscore_collapses():
    assert snake_to_upper_camel("foo_") == "Foo"


def test_digit_mid_segment():
    assert snake_to_upper_camel("rule1_test") == "Rule1Test"


def test_digit_mid_segment_not_split():
    assert snake_to_upper_camel("a1b2c3") == "A1b2c3"


def test_digit_leading_segment():
    # capitalize() does not uppercase a digit; documented contract.
    assert snake_to_upper_camel("1starts") == "1starts"


def test_lower_normalizes_mixed_case_input():
    # Grammar identifiers are always lowercase; this covers programmatic callers.
    # .lower() is applied before splitting, so mid-segment uppercase is folded.
    assert snake_to_upper_camel("MixedLabel") == "Mixedlabel"
    assert snake_to_upper_camel("UPPER_CASE") == "UpperCase"


def test_empty_string():
    assert snake_to_upper_camel("") == ""


# ---------------------------------------------------------------------------
# Call-site delegation: UnparserGenerator.class_name_for_rule_node
# ---------------------------------------------------------------------------


def test_unparser_generator_class_name_delegates_to_snake_to_upper_camel():
    """UnparserGenerator.class_name_for_rule_node must delegate to naming.snake_to_upper_camel."""
    from fltk.fegen import gsm  # noqa: PLC0415
    from fltk.iir.context import create_default_context  # noqa: PLC0415
    from fltk.unparse.gsm2unparser import UnparserGenerator  # noqa: PLC0415

    dummy_rule = gsm.Rule(
        name="foo_bar",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="x",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"x"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    dummy_grammar = gsm.Grammar(rules=(dummy_rule,), identifiers={"foo_bar": dummy_rule})
    gen = UnparserGenerator(grammar=dummy_grammar, context=create_default_context(), cst_module="dummy.cst")
    assert gen.class_name_for_rule_node("foo_bar") == "FooBar"
    assert gen.class_name_for_rule_node("no_ws") == "NoWs"


def test_protocol_module_name_appends_the_committed_suffix():
    """The layout every generated pair uses: X_cst beside X_cst_protocol."""
    assert protocol_module_name("mylang.mylang_cst") == "mylang.mylang_cst_protocol"


def test_protocol_module_name_matches_the_committed_fegen_pair():
    """The convention is not hypothetical: the committed modules are named this way."""
    assert protocol_module_name("fltk.fegen.fltk_cst") == "fltk.fegen.fltk_cst_protocol"


def test_protocol_module_path_is_the_sibling_file():
    """The bootstrap writers derive the protocol file they must write beside the CST file."""
    assert protocol_module_path("fltk/fegen/bootstrap_cst.py") == "fltk/fegen/bootstrap_cst_protocol.py"


def test_protocol_module_path_requires_a_py_file():
    """A path without the suffix would silently produce a file nothing imports."""
    with pytest.raises(ValueError, match="does not end in"):
        protocol_module_path("fltk/fegen/bootstrap_cst")
