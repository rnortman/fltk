"""Runtime cross-backend parity for the ergonomic CST accessors.

`tests/test_cst_ergonomic_accessors_rs.py` inspects generated Rust *source*; this module
runs the compiled thing. Every case parses the same text with the generated Python backend
and with the `rust_parser_fixture` extension, then asserts the new members return equal
values and raise the same exception type and message.

Two error classes are deliberately asserted per-backend rather than across backends: the
`maybe_` count wording for a duplicated child, and the out-of-range span wording. Both come
from surfaces that predate this module (the quintet pymethods and `Span`), and both already
differ between the backends; each new member is pinned against its own backend's producer.

Requires rust_parser_fixture, which the py_test target takes from //tests/rust_parser_fixture:rust_parser_fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not importable; it is built by //tests/rust_parser_fixture:rust_parser_fixture",
)

from fltk import _native  # noqa: E402
from fltk.fegen.pyrt import terminalsrc  # noqa: E402
from fltk.plumbing import generate_parser, parse_grammar_file, parse_text  # noqa: E402

_FIXTURE_FLTKG = Path(__file__).parent.parent / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg"

_py_parser: Any = None


def _py(rule: str, text: str) -> Any:
    """Parse `text` as `rule` with the generated Python backend, returning the CST root."""
    global _py_parser  # noqa: PLW0603
    if _py_parser is None:
        _py_parser = generate_parser(parse_grammar_file(_FIXTURE_FLTKG), capture_trivia=False)
    result = parse_text(_py_parser, text, rule)
    assert result.success, f"python backend failed to parse {text!r} as {rule}"
    return result.cst


def _rs(rule: str, text: str) -> Any:
    """Parse `text` as `rule` with the compiled Rust backend, returning the CST root."""
    parser = rust_parser_fixture.parser.Parser(text, capture_trivia=False)
    result = getattr(parser, f"apply__parse_{rule}")(0)
    assert result is not None, f"rust backend failed to parse {text!r} as {rule}"
    assert result.pos == len(text), f"rust backend did not consume all of {text!r}"
    return result.result


def _both(rule: str, text: str) -> list[Any]:
    return [_py(rule, text), _rs(rule, text)]


def test_inline_splice_children_match() -> None:
    for node in _both("wrapper", "[a=1]"):
        labels = type(node).Label
        assert len(node.children) == 2
        assert [label for label, _ in node.children] == [labels.KEY, labels.VAL]
        assert node.key().value_text() == "a"
        assert node.val().value_text() == "1"


def test_inline_optional_splice_absent() -> None:
    for node in _both("opt_wrapper", "<>"):
        assert node.key() is None
        assert node.val() is None


def test_inline_repeated_splice_is_a_collection() -> None:
    for node in _both("rep_wrapper", "{a=1;b=2;}"):
        assert [child.value_text() for child in node.key()] == ["a", "b"]
        assert [child.value_text() for child in node.val()] == ["1", "2"]


def test_inlined_rule_still_parses_standalone() -> None:
    for node in _both("pair", "a=1"):
        assert node.key().value_text() == "a"


def test_label_text_and_rule_text() -> None:
    for node in _both("num", "123"):
        assert node.value_text() == "123"
        assert node.text() == "123"


def test_rule_text_covers_suppressed_content() -> None:
    """`text()` reads the node's own span, so the suppressed quotes are included."""
    for node in _both("quoted", "'ab5'"):
        assert node.text() == "'ab5'"
        assert node.value_text() == "ab"
        assert node.tail_text() == "5"


def test_optional_label_text_is_none_when_absent() -> None:
    for node in _both("quoted", "'ab'"):
        assert node.tail_text() is None
        assert node.text() == "'ab'"


def test_no_rule_text_on_a_rule_with_node_children() -> None:
    for node in _both("wrapper", "[a=1]"):
        assert not hasattr(node, "text"), "wrapper has node children, so it gets no rule-level text()"


def test_variant_values_compare_across_backends() -> None:
    py_node, rs_node = _both("atom", "42")
    assert py_node.variant() == rs_node.variant()
    assert py_node.variant().name == "NUM"

    py_name, rs_name = _both("atom", "xy")
    assert py_name.variant() == rs_name.variant()
    assert py_name.variant().name == "NAME"


def test_keyword_labels_keep_their_python_names() -> None:
    for node in _both("kw_labels", "abc#7"):
        assert node.type_text() == "abc"
        assert node.type().text_or_raise() == "abc"
        assert node.match().value_text() == "7"


def _messages(rule: str, text: str, mutate: Any, call: Any) -> list[str]:
    """Apply `mutate` then `call` on both backends' nodes; return the two error messages."""
    messages = []
    for node in _both(rule, text):
        mutate(node)
        with pytest.raises(ValueError) as excinfo:
            call(node)
        messages.append(str(excinfo.value))
    return messages


def test_required_accessor_error_matches_across_backends() -> None:
    py_msg, rs_msg = _messages(
        "pair",
        "a=1",
        lambda node: node.clear(),
        lambda node: node.key(),
    )
    assert py_msg == rs_msg
    assert "key" in py_msg


def test_optional_accessor_error_matches_its_own_quintet_member() -> None:
    """The bare accessor delegates, so its message is the quintet's on that same backend.

    Cross-backend equality is not asserted here: the Python and Rust `maybe_` wordings for
    a duplicated child already differ, and the bare accessor inherits that difference rather
    than papering over it.
    """
    for node in _both("atom", "42"):
        node.append_num(node.child_num())
        with pytest.raises(ValueError) as bare:
            node.num()
        with pytest.raises(ValueError) as quintet:
            node.maybe_num()
        assert str(bare.value) == str(quintet.value)
        assert "num" in str(bare.value)


def test_label_text_error_matches_across_backends() -> None:
    py_msg, rs_msg = _messages(
        "num",
        "123",
        lambda node: node.clear(),
        lambda node: node.value_text(),
    )
    assert py_msg == rs_msg


def test_optional_label_text_error_matches_its_own_quintet_member() -> None:
    """`<label>_text()` reproduces the `maybe_` count message of the backend it runs on."""
    for node in _both("quoted", "'ab5'"):
        node.append_tail(node.child_tail())
        with pytest.raises(ValueError) as text_err:
            node.tail_text()
        with pytest.raises(ValueError) as quintet_err:
            node.maybe_tail()
        assert str(text_err.value) == str(quintet_err.value)
        assert "tail" in str(text_err.value)


def test_wrong_child_type_under_a_span_label_raises_type_error() -> None:
    """Only reachable through the untyped mutators; both backends name class, member and label."""
    messages = []
    for node in _both("kw_labels", "abc#7"):
        num_child = node.child_match()
        node.clear()
        node.append(num_child, type(node).Label.TYPE)
        with pytest.raises(TypeError) as excinfo:
            node.type_text()
        messages.append(str(excinfo.value))

    assert messages[0] == messages[1]
    assert messages[0] == "KwLabels.type_text: child labelled 'type' is not a Span"


def test_wrong_child_type_under_an_optional_span_label_raises_type_error() -> None:
    """The optional arity has its own wrong-variant arm, reached when exactly one child is
    stored under the label; both backends word it like the required arity."""
    messages = []
    for node in _both("mixed_opt", "ab7"):
        num_child = node.child_node()
        node.clear()
        node.append(num_child, type(node).Label.KEY)
        with pytest.raises(TypeError) as excinfo:
            node.key_text()
        messages.append(str(excinfo.value))

    assert messages[0] == messages[1]
    assert messages[0] == "MixedOpt.key_text: child labelled 'key' is not a Span"


def test_optional_span_label_beside_a_node_label() -> None:
    """The happy paths of the same accessor: present, and absent."""
    for node in _both("mixed_opt", "ab7"):
        assert node.key_text() == "ab"
        assert node.node().value_text() == "7"
    for node in _both("mixed_opt", "7"):
        assert node.key_text() is None
        assert node.key() is None


def test_sourceless_span_message_matches_across_backends() -> None:
    py_node = _py("num", "123")
    py_node.clear()
    py_node.append_value(terminalsrc.Span(0, 3))
    rs_node = _rs("num", "123")
    rs_node.clear()
    rs_node.append_value(_native.Span(0, 3))

    messages = []
    for node in (py_node, rs_node):
        with pytest.raises(ValueError) as excinfo:
            node.value_text()
        messages.append(str(excinfo.value))

    assert messages[0] == messages[1] == "Span(0, 3) has no source"


def test_out_of_range_span_message_is_the_backends_own_span_wording() -> None:
    """The two `Span` implementations word an out-of-range span differently; each accessor
    reports its own backend's wording rather than inventing a third."""
    py_node = _py("num", "123")
    py_node.clear()
    py_span = terminalsrc.Span.with_source(0, 9, "abc")
    py_node.append_value(py_span)

    rs_node = _rs("num", "123")
    rs_node.clear()
    rs_span = _native.Span.with_source(0, 9, _native.SourceText("abc"))
    rs_node.append_value(rs_span)

    for node, span in ((py_node, py_span), (rs_node, rs_span)):
        with pytest.raises(ValueError) as accessor_err:
            node.value_text()
        with pytest.raises(ValueError) as span_err:
            span.text_or_raise()
        assert str(accessor_err.value) == str(span_err.value)


def test_variant_without_labeled_child_raises_on_both() -> None:
    py_msg, rs_msg = _messages(
        "atom",
        "42",
        lambda node: node.clear(),
        lambda node: node.variant(),
    )
    assert "variant" in py_msg
    assert "variant" in rs_msg
