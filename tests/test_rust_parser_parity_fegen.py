"""Cross-backend parity tests: Python fegen parser vs fegen_rust_cst.Parser.

Requires fegen_rust_cst to be built: run 'make build-fegen-rust-cst' first.
A CI lane where every test here is skipped is a failure signal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

import fltk.fegen.fltk_parser as py_parser_mod  # noqa: E402
import fltk.fegen.fltk_trivia_parser as py_trivia_parser_mod  # noqa: E402
from fltk.fegen.pyrt import terminalsrc as tsrc  # noqa: E402
from tests.parser_parity import (  # noqa: E402
    FAIL,
    SUCCESS,
    _assert_messages_equiv,
    assert_cst_equal,
    assert_error_equiv,
    run_parity_corpus_entry,
)

_FEGEN_FLTKG = Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"


def _py_parser(text: str, capture_trivia: bool):  # noqa: FBT001
    ts = tsrc.TerminalSource(text)
    if capture_trivia:
        return py_trivia_parser_mod.Parser(terminalsrc=ts)
    else:
        return py_parser_mod.Parser(terminalsrc=ts)


def _rust_parser(text: str, capture_trivia: bool):  # noqa: FBT001
    return fegen_rust_cst.parser.Parser(text, capture_trivia)


# Corpus: (rule_name, input_text, expected_outcome)
_CORPUS = [
    # Full fegen grammar self-parse
    ("grammar", _FEGEN_FLTKG.read_text(), SUCCESS),
    # Single rule
    ("rule", "word := value:/[a-z]+/ ;", SUCCESS),
    # Multi-alternative rule
    ("rule", "atom := num:num | name:name ;", SUCCESS),
    # Quantifiers
    ("rule", "items := item:atom+ ;", SUCCESS),
    ("rule", "opt := item:atom? ;", SUCCESS),
    ("rule", "zom := item:atom* ;", SUCCESS),
    # Disposition
    ("rule", 'kw := %"hello" ;', SUCCESS),
    # Identifier
    ("identifier", "my_rule", SUCCESS),
    # Line comment (trivia)
    ("rule", "x := a:b ; // comment\n", SUCCESS),
    # Block comment
    ("rule", "x := a:b ; /* comment */ \n", SUCCESS),
    # Raw string
    ("raw_string", '"hello world"', SUCCESS),
    # Multibyte in grammar string literal
    ("raw_string", '"café"', SUCCESS),
    # Multibyte content preceding a syntax error (line/col + caret over multibyte text).
    # Error is at position 12 (the first '*'), after the multibyte 'é' at position 9,
    # so line/col and caret computation must index past a multibyte character.
    ("grammar", 'x := "café" ** ;', FAIL),
    # Non-start rule: identifier
    ("identifier", "some_rule_name", SUCCESS),
    # Trailing-character pinning: grammar text ending in non-whitespace terminal
    ("rule", 'x := "a" ;', SUCCESS),
    # Failure: unterminated rule
    ("grammar", "broken :=", FAIL),
    # Failure: bad token mid-line
    ("grammar", "x := *** ;", FAIL),
    # Multi-line input failing on a later line
    ("grammar", 'ok := "x" ;\nbad :=\n', FAIL),
    # Empty input
    ("grammar", "", FAIL),
]

_CORPUS_IDS = [f"{r}-{i}" for i, (r, _, _) in enumerate(_CORPUS)]


@pytest.mark.parametrize("capture_trivia", [False, True])
@pytest.mark.parametrize("rule,text,expected", _CORPUS, ids=_CORPUS_IDS)
def test_parity(rule, text, expected, capture_trivia):
    py_p = _py_parser(text, capture_trivia)
    rust_p = _rust_parser(text, capture_trivia)
    ts = tsrc.TerminalSource(text)
    run_parity_corpus_entry(py_p, rust_p, ts, rule, text, expected)


# ---------------------------------------------------------------------------
# Comparator self-tests (§4.4)
# ---------------------------------------------------------------------------


def test_assert_cst_equal_passes_for_equal_nodes():
    """Sanity: same parse should pass assert_cst_equal."""
    text = 'x := "a" ;'
    py_p = _py_parser(text, False)
    rust_p = _rust_parser(text, False)
    py_r = py_p.apply__parse_rule(pos=0)
    rust_r = rust_p.apply__parse_rule(0)
    assert py_r is not None and rust_r is not None
    assert_cst_equal(py_r.result, rust_r.result)  # must not raise


def test_assert_cst_equal_fails_for_different_inputs():
    """assert_cst_equal must fail when trees differ (different lengths → different spans)."""
    text1 = 'x := "a" ;'
    text2 = 'longname := "longer_literal" ;'
    py_r1 = _py_parser(text1, False).apply__parse_rule(pos=0)
    rust_r2 = _rust_parser(text2, False).apply__parse_rule(0)
    with pytest.raises(AssertionError):
        assert_cst_equal(py_r1.result, rust_r2.result)


def test_assert_error_equiv_fails_for_different_positions():
    """assert_error_equiv must fail when error positions differ."""
    text1 = "broken :="
    text2 = "x broken"  # fails at different position
    py_p = _py_parser(text1, False)
    py_p.apply__parse_grammar(pos=0)
    rust_p = _rust_parser(text2, False)
    rust_p.apply__parse_grammar(0)
    ts = tsrc.TerminalSource(text1)
    with pytest.raises(AssertionError):
        assert_error_equiv(py_p, rust_p, ts)


# Targeted comparator self-tests (§4.4)


def test_assert_cst_equal_fails_kind_mismatch():
    """assert_cst_equal must fail when node kinds differ."""
    # py: parse an identifier; rust: parse a rule — same text "my_rule" succeeds as identifier
    # but we compare an identifier-result against a different-kind rule-result
    id_text = "my_rule"
    rule_text = 'x := "a" ;'
    py_id = _py_parser(id_text, False).apply__parse_identifier(pos=0)
    rust_rule = _rust_parser(rule_text, False).apply__parse_rule(0)
    assert py_id is not None and rust_rule is not None
    with pytest.raises(AssertionError):
        assert_cst_equal(py_id.result, rust_rule.result)


def test_assert_cst_equal_fails_span_mismatch():
    """assert_cst_equal must fail when node spans differ (same kind, different span)."""
    # Parse two different-length identifiers; both produce IDENTIFIER nodes but with different spans
    py_id = _py_parser("ab", False).apply__parse_identifier(pos=0)
    rust_id = _rust_parser("abc", False).apply__parse_identifier(0)
    assert py_id is not None and rust_id is not None
    with pytest.raises(AssertionError):
        assert_cst_equal(py_id.result, rust_id.result)


def test_assert_cst_equal_fails_child_count_mismatch():
    """assert_cst_equal must fail when child counts differ, even when enclosing spans are equal.

    Uses hand-built nodes so kind, span, and labels all match — only child count differs.
    A comparator that fires on span before reaching the length check would pass this test,
    so both Grammar nodes share the same outer span to force the length check to be the discriminator.
    """
    import fltk.fegen.fltk_cst as py_cst  # noqa: PLC0415
    from fltk.fegen.pyrt.terminalsrc import Span  # noqa: PLC0415

    shared_span = Span(0, 10)
    rule_child = py_cst.Rule(span=Span(0, 10))
    g_one = py_cst.Grammar(span=shared_span, children=[(py_cst.Grammar.Label.RULE, rule_child)])
    g_two = py_cst.Grammar(
        span=shared_span,
        children=[
            (py_cst.Grammar.Label.RULE, rule_child),
            (py_cst.Grammar.Label.RULE, py_cst.Rule(span=Span(0, 10))),
        ],
    )
    with pytest.raises(AssertionError):
        assert_cst_equal(g_one, g_two)


def test_assert_cst_equal_fails_label_mismatch():
    """assert_cst_equal must fail when child labels differ."""
    import fltk.fegen.fltk_cst as py_cst  # noqa: PLC0415

    # Parse a rule to get a real Rust Rule node with proper shape
    rule_text = 'x := "a" ;'
    py_r = _py_parser(rule_text, False).apply__parse_rule(pos=0)
    rust_r = _rust_parser(rule_text, False).apply__parse_rule(0)
    assert py_r is not None and rust_r is not None
    # The rust rule node has a child labelled NAME for the identifier.
    # Construct a Python Rule node that has the same children except with None label
    # (unlabelled) instead of NAME, so the label differs.
    rust_node = rust_r.result
    rust_children = rust_node.children
    # Find a child that has a label; we'll build a Python node with wrong label
    labeled_children = [(lbl, ch) for lbl, ch in rust_children if lbl is not None]
    assert labeled_children, "Expected at least one labeled child in Rule"
    # Build a modified Python Rule node where one labelled child has label=None instead
    py_rule = py_r.result
    py_children_copy = list(py_rule.children)
    # Find first labelled child and strip its label
    first_labeled_idx = next(i for i, (lbl, _) in enumerate(py_children_copy) if lbl is not None)
    lbl, ch = py_children_copy[first_labeled_idx]
    py_children_copy[first_labeled_idx] = (None, ch)  # strip the label
    # Build a modified Python Rule node
    modified_py_rule = py_cst.Rule(
        span=py_rule.span,
        children=py_children_copy,
    )
    with pytest.raises(AssertionError):
        assert_cst_equal(modified_py_rule, rust_node)


def test_assert_cst_equal_fails_deep_child_mismatch():
    """assert_cst_equal must recurse: fail when a deeply nested child differs.

    Uses hand-built nodes so the outer Grammar and Rule spans match — only the
    nested Identifier span differs.  A comparator that stops after checking the
    root span (or even the Rule span) would pass this test without recursing.
    """
    import fltk.fegen.fltk_cst as py_cst  # noqa: PLC0415
    from fltk.fegen.pyrt.terminalsrc import Span  # noqa: PLC0415

    outer_span = Span(0, 25)
    rule_span = Span(0, 25)

    # Both grammars: one rule with one Identifier child, same outer spans everywhere,
    # but the Identifier spans differ (5 vs 6 chars).
    def _make_grammar(id_end: int) -> py_cst.Grammar:
        ident = py_cst.Identifier(span=Span(0, id_end))
        rule = py_cst.Rule(span=rule_span, children=[(py_cst.Rule.Label.NAME, ident)])
        return py_cst.Grammar(span=outer_span, children=[(py_cst.Grammar.Label.RULE, rule)])

    g_a = _make_grammar(5)
    g_b = _make_grammar(6)
    with pytest.raises(AssertionError):
        assert_cst_equal(g_a, g_b)


def test_assert_cst_equal_fails_species_node_vs_span():
    """assert_cst_equal must fail when Python has a node child and Rust has a span child."""
    import fltk.fegen.fltk_cst as py_cst  # noqa: PLC0415
    from fltk.fegen.pyrt.terminalsrc import Span  # noqa: PLC0415

    # Parse an identifier to get a Rust IDENTIFIER node (has a span child for the matched text)
    rust_r = _rust_parser("my_rule", False).apply__parse_identifier(0)
    assert rust_r is not None
    rust_node = rust_r.result

    # Build a Python Identifier node that has a *node* child where the Rust one has a span child.
    # We do this by constructing a Python Identifier whose children list has a Rule child instead of a Span.
    py_r = _py_parser("my_rule", False).apply__parse_identifier(pos=0)
    assert py_r is not None
    py_node = py_r.result
    # Replace first child (a span) with a node (use a fresh Rule with no children)
    # so species mismatches: Rust has span child, Python has node child
    fake_rule = py_cst.Rule(span=Span(0, 0))
    first_lbl = py_node.children[0][0] if py_node.children else None
    modified_py = py_cst.Identifier(
        span=py_node.span,
        children=[(first_lbl, fake_rule)],
    )
    with pytest.raises(AssertionError):
        assert_cst_equal(modified_py, rust_node)


def test_assert_cst_equal_fails_species_span_vs_node():
    """assert_cst_equal must fail when Python has a span child and Rust has a node child.

    Reverse direction of test_assert_cst_equal_fails_species_node_vs_span.
    The comparator discriminates via hasattr(child, 'children'); this direction exercises
    the case where the Python side lacks 'children' (it's a Span) and the Rust side has it
    (it's an Identifier or similar node object).
    """
    import fltk.fegen.fltk_cst as py_cst  # noqa: PLC0415
    from fltk.fegen.pyrt.terminalsrc import Span  # noqa: PLC0415

    # Get a Rust Rule node: its children are (NAME, Identifier) and (ALTERNATIVES, Alternatives) — both nodes.
    rust_r = _rust_parser('x := "a" ;', False).apply__parse_rule(0)
    assert rust_r is not None
    rust_node = rust_r.result  # 2 node children: NAME=Identifier, ALTERNATIVES=Alternatives

    # Build a Python Rule with the same span and 2 children (matching count and labels),
    # but first child is a bare Span instead of an Identifier node.
    # kind, span, child-count, and label all match — only species differs for child[0].
    py_r = _py_parser('x := "a" ;', False).apply__parse_rule(pos=0)
    assert py_r is not None
    py_node = py_r.result

    py_span_child = Span(0, 1)  # span species in place of Identifier node
    modified_py = py_cst.Rule(
        span=rust_node.span,
        children=[
            (py_cst.Rule.Label.NAME, py_span_child),  # span where Rust has node
            py_node.children[1],  # real Alternatives node, same as Rust
        ],
    )
    with pytest.raises(AssertionError):
        assert_cst_equal(modified_py, rust_node)


def test_assert_error_equiv_fails_header_mismatch():
    """_assert_messages_equiv must fail when error message headers differ.

    Uses hand-built parsed messages so the failure fires at the header comparison,
    not at the position check (which is separate in assert_error_equiv).
    """
    # Same position prefix in header lines, but different line/col text to force header inequality
    header_a = ["Syntax error at line 1, col 5:", "foo  x", "    ^"]
    header_b = ["Syntax error at line 1, col 7:", "foo  x", "      ^"]
    rules = {'From rule "r":': {'"x"'}}
    with pytest.raises(AssertionError):
        _assert_messages_equiv(header_a, rules, header_b, rules)


def test_assert_messages_equiv_fails_group_order():
    """_assert_messages_equiv must fail when rule-group order differs."""
    header = ["Syntax error at line 1, col 1:", "x", "^"]
    rules_ab = {'From rule "alpha":': {'"x"'}, 'From rule "beta":': {'"y"'}}
    # dict preserves insertion order in Python 3.7+; reversed order is a different dict ordering
    rules_ba = {'From rule "beta":': {'"y"'}, 'From rule "alpha":': {'"x"'}}
    with pytest.raises(AssertionError):
        _assert_messages_equiv(header, rules_ab, header, rules_ba)


def test_assert_messages_equiv_fails_token_set():
    """_assert_messages_equiv must fail when token sets for a rule differ."""
    header = ["Syntax error at line 1, col 1:", "x", "^"]
    rules_a = {'From rule "r":': {'"x"', '"y"'}}
    rules_b = {'From rule "r":': {'"x"', '"z"'}}
    with pytest.raises(AssertionError):
        _assert_messages_equiv(header, rules_a, header, rules_b)
