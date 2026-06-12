"""Tests for validate_no_underscore_only_names (GSM-layer name validation).

All tests marked 'failing-first' demonstrate the before/after behavior:
- Before: cryptic error (IndentationError, malformed Rust output, or silent success)
- After: ValueError naming the offender and the cause, raised at classify_trivia_rules time.
"""

import pytest

from fltk import plumbing
from fltk.fegen import gsm
from fltk.fegen.gsm2tree_rs import RustCstGenerator


def _make_simple_grammar(rule_name: str, label: str | None = None) -> gsm.Grammar:
    """Build a minimal Grammar with one rule (and optional label) for testing."""
    rule = gsm.Rule(
        name=rule_name,
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=label,
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    return gsm.Grammar(rules=[rule], identifiers={rule_name: rule})


# ---------------------------------------------------------------------------
# Failing-first tests: rule name rejection
# ---------------------------------------------------------------------------


def test_rule_named_single_underscore_raises():
    """Rule named '_' must raise ValueError naming the rule and mentioning underscore.

    Before fix: raises IndentationError from pygen.stmt(' = enum.auto()')
    After fix: raises ValueError with friendly message.
    """
    grammar = _make_simple_grammar("_")
    with pytest.raises(ValueError, match=r"'_'") as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    assert "underscore" in str(exc_info.value).lower()


def test_rule_named_double_underscore_raises():
    """Rule named '__' must raise ValueError.

    Before fix: raises IndentationError.
    After fix: raises ValueError with friendly message.
    """
    grammar = _make_simple_grammar("__")
    with pytest.raises(ValueError, match=r"'__'") as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    assert "underscore" in str(exc_info.value).lower()


def test_rule_named_triple_underscore_raises():
    """Rule named '___' must raise ValueError."""
    grammar = _make_simple_grammar("___")
    with pytest.raises(ValueError):
        gsm.validate_no_underscore_only_names(grammar)


def test_rule_named_empty_string_raises():
    """Rule named '' (empty string from programmatic GSM) must raise ValueError.

    naming.snake_to_upper_camel('') == '' (same predicate as underscore-only names).
    Pins that any future defensive change to snake_to_upper_camel for empty input
    does not silently drop the rejection.
    """
    grammar = _make_simple_grammar("")
    with pytest.raises(ValueError) as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    assert "underscore" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Failing-first tests: label rejection
# ---------------------------------------------------------------------------


def test_top_level_label_underscore_raises():
    """Label '_' in rule 'x' must raise ValueError naming both rule and label.

    Before fix: generates successfully (Python backend produces Label._, child__()).
    After fix: raises ValueError.
    """
    grammar = _make_simple_grammar("x", label="_")
    with pytest.raises(ValueError) as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    msg = str(exc_info.value)
    assert "'_'" in msg
    assert "x" in msg
    assert "label" in msg.lower()
    assert "underscore" in msg.lower()


def test_nested_label_underscore_raises():
    """Label '_' nested inside a parenthesized sub-expression must raise ValueError.

    Grammar: x := (a:/[a-z]+/ | _:/[0-9]+/)
    Before fix: generates successfully.
    After fix: raises ValueError.
    """
    inner_items_a = gsm.Items(
        items=[
            gsm.Item(
                label="a",
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"[a-z]+"),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    inner_items_bad = gsm.Items(
        items=[
            gsm.Item(
                label="_",  # problematic label in nested alternative
                disposition=gsm.Disposition.INCLUDE,
                term=gsm.Regex(r"[0-9]+"),
                quantifier=gsm.REQUIRED,
            )
        ],
        sep_after=[gsm.Separator.NO_WS],
    )
    rule = gsm.Rule(
        name="x",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label=None,
                        disposition=gsm.Disposition.INCLUDE,
                        term=[inner_items_a, inner_items_bad],  # sub-expression
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(rules=[rule], identifiers={"x": rule})
    with pytest.raises(ValueError) as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    msg = str(exc_info.value)
    assert "'_'" in msg
    assert "x" in msg
    assert "label" in msg.lower()
    assert "underscore" in msg.lower()


def test_rust_path_raises_at_init():
    """RustCstGenerator.__init__ for grammar with rule '_' raises ValueError (not silent).

    Before fix: __init__ succeeds, generate() emits 'pub struct  {' (malformed Rust).
    After fix: ValueError from classify_trivia_rules inside __init__.
    """
    grammar = _make_simple_grammar("_")
    with pytest.raises(ValueError) as exc_info:
        RustCstGenerator(grammar)
    assert "underscore" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Failing-first tests: trivia-less grammar still checked
# ---------------------------------------------------------------------------


def test_trivia_less_grammar_still_validates():
    """Grammar without _trivia: validate_no_underscore_only_names and classify_trivia_rules
    both raise ValueError — the check fires before the early-return in classify_trivia_rules.
    """
    grammar = _make_simple_grammar("_")  # no _trivia rule

    # Direct function call raises
    with pytest.raises(ValueError):
        gsm.validate_no_underscore_only_names(grammar)

    # classify_trivia_rules also raises (before the early-return)
    with pytest.raises(ValueError):
        gsm.classify_trivia_rules(grammar)


# ---------------------------------------------------------------------------
# Failing-first tests: multiple violations reported together
# ---------------------------------------------------------------------------


def test_multiple_violations_reported_in_one_error():
    """Rule '_' plus label '__' in another rule: both violations in one ValueError."""
    rule_bad_name = gsm.Rule(
        name="_",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="val",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    rule_bad_label = gsm.Rule(
        name="good_rule",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="__",  # bad label
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[0-9]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(
        rules=[rule_bad_name, rule_bad_label],
        identifiers={"_": rule_bad_name, "good_rule": rule_bad_label},
    )
    with pytest.raises(ValueError) as exc_info:
        gsm.validate_no_underscore_only_names(grammar)
    msg = str(exc_info.value)
    # Both violations mentioned
    assert "'_'" in msg
    assert "'__'" in msg


# ---------------------------------------------------------------------------
# Regression guards: valid names must still pass
# ---------------------------------------------------------------------------


def test_rule_foo_with_leading_underscore_passes():
    """Rule '_foo' derives non-empty CN 'Foo'; must pass validation.

    Regression: '_trivia', '_foo', etc. must not be affected.
    """
    grammar = _make_simple_grammar("_foo")
    gsm.validate_no_underscore_only_names(grammar)  # must not raise


def test_label_foo_with_leading_underscore_passes():
    """Label '_foo' derives non-empty CN 'Foo'; must pass validation."""
    grammar = _make_simple_grammar("x", label="_foo")
    gsm.validate_no_underscore_only_names(grammar)  # must not raise


def test_classify_trivia_rules_with_trivia_passes():
    """Full classify_trivia_rules with a real _trivia rule succeeds.

    Exercises the auto-added _trivia rule (label 'content') through the validator.
    """
    content_rule = gsm.Rule(
        name="word",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="val",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"[a-z]+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    trivia_rule = gsm.Rule(
        name="_trivia",
        alternatives=[
            gsm.Items(
                items=[
                    gsm.Item(
                        label="content",
                        disposition=gsm.Disposition.INCLUDE,
                        term=gsm.Regex(r"\s+"),
                        quantifier=gsm.REQUIRED,
                    )
                ],
                sep_after=[gsm.Separator.NO_WS],
            )
        ],
    )
    grammar = gsm.Grammar(
        rules=[content_rule, trivia_rule],
        identifiers={"word": content_rule, "_trivia": trivia_rule},
    )
    result = gsm.classify_trivia_rules(grammar)
    assert result is not None


def test_plumbing_generate_parser_with_underscore_foo_rule():
    """Grammar with rule '_foo' generates and parses successfully via plumbing pipeline."""
    grammar_text = """
_foo := val:/[a-z]+/ ;
root := _foo ;
"""
    try:
        result = plumbing.parse_grammar(grammar_text)
        parser_result = plumbing.generate_parser(result)
        parse_result = plumbing.parse_text(parser_result, "hello", rule_name="root")
        assert parse_result.success, f"Parse failed: {parse_result.error_message}"
    except (ValueError, IndentationError) as exc:
        pytest.fail(f"Expected success for '_foo' grammar, got: {exc}")


# ---------------------------------------------------------------------------
# Plumbing integration tests: pipeline-level rejection (design tests 1-2)
# ---------------------------------------------------------------------------


def test_plumbing_rejects_rule_named_single_underscore():
    """plumbing.generate_parser raises ValueError for rule '_', not IndentationError.

    Locks the plumbing integration: the validator fires inside classify_trivia_rules
    which is called by generate_parser, so any bypass path would leave this test failing.
    Before fix: raises IndentationError from pygen.stmt(' = enum.auto()')
    After fix: raises ValueError with friendly message.
    """
    grammar_text = "_ := val:/[a-z]+/ ;"
    grammar = plumbing.parse_grammar(grammar_text)
    with pytest.raises(ValueError, match=r"underscore"):
        plumbing.generate_parser(grammar)


def test_plumbing_rejects_rule_named_double_underscore():
    """plumbing.generate_parser raises ValueError for rule '__'.

    Before fix: raises IndentationError.
    After fix: raises ValueError with friendly message.
    """
    grammar_text = "__ := val:/[a-z]+/ ;"
    grammar = plumbing.parse_grammar(grammar_text)
    with pytest.raises(ValueError, match=r"underscore"):
        plumbing.generate_parser(grammar)


def test_plumbing_rejects_label_underscore():
    """plumbing.generate_parser raises ValueError for a label '_' (formerly worked on Python backend).

    Locks the plumbing integration for the label case: classify_trivia_rules fires for label
    violations too, so any future bypass would leave this test failing.
    Before fix: generate_parser succeeds (produces Label._, child__()).
    After fix: raises ValueError.
    """
    grammar_text = "x := _:/[a-z]+/ ;"
    grammar = plumbing.parse_grammar(grammar_text)
    with pytest.raises(ValueError, match=r"underscore"):
        plumbing.generate_parser(grammar)


# ---------------------------------------------------------------------------
# Regression guard: capture_trivia=True pipeline passes (design test 9)
# ---------------------------------------------------------------------------


def test_plumbing_capture_trivia_pipeline_passes():
    """Full plumbing.generate_parser with capture_trivia=True succeeds.

    Locks that the auto-added _trivia rule (label 'content') passes through
    validate_no_underscore_only_names without raising.  If the validator were
    mistakenly tightened to reject _trivia or the 'content' label, this test
    would catch it.
    """
    grammar_text = "word := val:/[a-z]+/ ;"
    grammar = plumbing.parse_grammar(grammar_text)
    # Must not raise — _trivia + its 'content' label are auto-added and must pass validation
    plumbing.generate_parser(grammar, capture_trivia=True)
