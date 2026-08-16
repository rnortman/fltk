"""One generated Python AST module converting both backends' CSTs.

The forward direction (`<rule>_from_cst` and the generated `from_cst` methods) is annotated and
keyed against the CST protocol, so the AST module that a Python-backend consumer generates also
takes nodes produced by the Rust extension.  These tests execute that claim over the richest
committed grammar/sidecar pair — `rust_parser_fixture`, which covers sums, products, folds,
coercions, transparent rules, keyed collections and inline splices — by converting the same source
text through both backends with the *same* AST module and comparing the results.

Requires rust_parser_fixture to be built: run 'make build-rust-parser-fixture' first.
A CI lane where every test here is skipped is a failure signal.
"""

from __future__ import annotations

import dataclasses
import typing

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)

from fltk import plumbing  # noqa: E402
from fltk.fegen.pyrt import astrt  # noqa: E402
from tests import fixture_ast_layer  # noqa: E402
from tests.parser_parity import parse_rust_cst  # noqa: E402

if typing.TYPE_CHECKING:
    import types

    from fltk.plumbing_types import ParserResult


class Layer(typing.NamedTuple):
    """A Python parser and the AST module built from the same grammar, plus the Rust parser."""

    parser: ParserResult
    ast: types.ModuleType
    capture_trivia: bool
    converted: dict[tuple[str, str], tuple[typing.Any, typing.Any]]

    def py_cst(self, rule: str, text: str) -> typing.Any:
        result = plumbing.parse_text(self.parser, text, rule)
        assert result.success, result.error_message
        return result.cst

    def rust_cst(self, rule: str, text: str) -> typing.Any:
        return parse_rust_cst(rust_parser_fixture.parser, rule, text, capture_trivia=self.capture_trivia)

    def convert(self, rule: str, node: typing.Any) -> typing.Any:
        return getattr(self.ast, f"{rule}_from_cst")(node)

    def convert_both(self, rule: str, text: str) -> tuple[typing.Any, typing.Any]:
        """The AST value the same text converts to through each backend.

        Memoised per (rule, text): several tests read the same pair, and the callers below only
        read the values.  Anything that mutates a node parses it separately.
        """
        key = (rule, text)
        if key not in self.converted:
            self.converted[key] = (
                self.convert(rule, self.py_cst(rule, text)),
                self.convert(rule, self.rust_cst(rule, text)),
            )
        return self.converted[key]


def _build_layer(*, capture_trivia: bool, config_prefix: str = "") -> Layer:
    base = fixture_ast_layer.build(capture_trivia=capture_trivia, config_prefix=config_prefix)
    return Layer(parser=base.parser, ast=base.ast, capture_trivia=capture_trivia, converted={})


@pytest.fixture(scope="module", params=[False, True], ids=["no_trivia", "trivia"])
def layer(request: pytest.FixtureRequest) -> Layer:
    """The AST layer over the fixture grammar, once with trivia capture and once without.

    Trivia capture changes the shape of every node's children (Trivia nodes appear between the
    labeled ones), so it is the other half of the forward direction's bucketing behaviour.
    """
    return _build_layer(capture_trivia=request.param)


@pytest.fixture(scope="module")
def backpointer_layer() -> Layer:
    """The same layer with ``option cst = true;``, so every AST value keeps its source node."""
    return _build_layer(capture_trivia=False, config_prefix="option cst = true;\n")


# Covers every AST shape the sidecar produces and every grammar construct that reaches
# the forward converters by a distinct path.
_SNIPPETS = [
    # Terminals and scalars
    ("num", "42"),
    ("name", "abc"),
    ("digit_seq", "907"),
    ("word_seq", "a_1"),
    ("three_to_five_digits", "1234"),
    ("escaped_metas", ".*+"),
    ("nc_group_alt", "abcd"),
    ("case_insensitive", "abc"),
    ("anchored_word", "abc"),
    ("latin_word", "ÀÁÂ"),
    ("arrow", "→abc"),
    # Sums (alternative signatures)
    ("atom", "42"),
    ("atom", "abc"),
    ("val", "42"),
    ("val", "hello"),
    ("val", "!@#$"),
    ("colour", "gray"),
    ("colour", "grey"),
    ("colour", "black"),
    # Products, quantifiers, sub-expressions
    ("paren_expr", "(42)"),
    ("stmt", "x = y"),
    ("items", "12"),
    ("opt_item", ""),
    ("zero_items", ""),
    ("zero_items", "1"),
    ("grouped", "(x)"),
    ("tagged", "tagword"),
    ("leading_ws", "7"),
    ("kw_labels", "abc#3"),
    ("quoted", "'ab5'"),
    ("mixed_opt", "ab3"),
    # Recursion
    ("expr", "1+2+3"),
    ("lval", "x"),
    ("rval", "1"),
    ("nest", "((7))"),
    ("nest_sum", "1+2"),
    ("rec_via_sub", "1xy+ab"),
    # Inline splices
    ("pair", "x=1"),
    ("wrapper", "[x=1]"),
    ("opt_wrapper", "<x=1>"),
    ("opt_wrapper", "<>"),
    ("rep_wrapper", "{x=1;y=2;}"),
    # Coercions
    ("uuid_val", "12345678-1234-1234-1234-123456789abc"),
    ("decimal_val", "-1.25"),
    # Fold
    ("sum_chain", "1+2+3"),
    ("sum_chain", "7"),
    # Keyed collections (the key rule itself is transparent, so it has no converter of its own)
    ("entry", "a = 1 ;"),
    ("entries", "{a=1;b=2;}"),
    ("multi_entry", "a = 1 ;"),
    ("multi_entries", "{a=1;a=2;b=3;}"),
]

_SNIPPET_IDS = [f"{rule}-{text or 'empty'}" for rule, text in _SNIPPETS]


def _spans(
    value: typing.Any, path: str = "", found: list[tuple[str, int, int]] | None = None
) -> list[tuple[str, int, int]]:
    """Every span reachable from an AST value, as (path, start, end).

    Spans are excluded from AST equality (`compare=False`), because a Python span and a native
    one are never `==`.  That is what makes the cross-backend equality assertions possible at
    all — and it means the offsets have to be compared separately or they are never compared.
    """
    if found is None:
        found = []
    if hasattr(value, "start") and hasattr(value, "end"):
        found.append((path, value.start, value.end))
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            _spans(getattr(value, field.name), f"{path}.{field.name}", found)
    elif isinstance(value, list | tuple):
        for index, element in enumerate(value):
            _spans(element, f"{path}[{index}]", found)
    elif isinstance(value, dict):
        for key, element in value.items():
            _spans(element, f"{path}[{key!r}]", found)
    return found


@pytest.mark.parametrize(("rule", "text"), _SNIPPETS, ids=_SNIPPET_IDS)
def test_both_backends_convert_to_equal_ast_values(layer: Layer, rule: str, text: str) -> None:
    """The headline claim: same source, same AST module, either backend, equal values."""
    from_python, from_rust = layer.convert_both(rule, text)
    assert from_python == from_rust


@pytest.mark.parametrize(("rule", "text"), _SNIPPETS, ids=_SNIPPET_IDS)
def test_the_spans_the_two_backends_record_agree(layer: Layer, rule: str, text: str) -> None:
    """Equality skips spans, so the offsets are checked here — including span-typed fields."""
    from_python, from_rust = layer.convert_both(rule, text)
    python_spans = _spans(from_python)
    # A walker that stopped recognising spans would compare [] with [] for every snippet.
    assert python_spans, "no spans found; the walker no longer reaches this value's spans"
    assert python_spans == _spans(from_rust)


def test_equal_ast_values_are_not_the_only_thing_conversion_can_produce(layer: Layer) -> None:
    """The control for the equality sweep: AST `==` can report unequal, so the sweep has teeth."""
    assert layer.convert("num", layer.py_cst("num", "42")) != layer.convert("num", layer.py_cst("num", "43"))
    assert layer.convert("num", layer.py_cst("num", "42")) != layer.convert("num", layer.rust_cst("num", "43"))


@pytest.mark.parametrize(
    ("rule", "empty_value"),
    [("opt_item", None), ("zero_items", [])],
    ids=["opt_item", "zero_items"],
)
def test_an_absent_quantified_child_converts_to_the_empty_shape(
    layer: Layer, rule: str, empty_value: typing.Any
) -> None:
    """The two empty snippets' only compared field is the quantified one, so pin its value.

    Without this, dataclass equality on the empty sources reduces to "same class" and a dropped
    label on either backend would satisfy the sweep above on both sides at once.
    """
    for value in layer.convert_both(rule, ""):
        assert value.item == empty_value
    for value in layer.convert_both(rule, "1"):
        assert value.item != empty_value


def test_the_spans_are_the_backends_own_span_objects(layer: Layer) -> None:
    """Each value keeps the span type its own backend produced; neither is converted."""
    from_python, from_rust = layer.convert_both("num", "42")
    assert type(from_python.span) is not type(from_rust.span)
    assert from_python.span != from_rust.span
    assert from_python.span.text() == from_rust.span.text() == "42"


def test_a_nested_values_span_carries_its_own_backends_span(layer: Layer) -> None:
    """Spans do not stop at the root: each converted child keeps its own backend's span too."""
    from_python, from_rust = layer.convert_both("mixed_opt", "ab3")
    assert from_python.key == from_rust.key == "ab"
    assert (from_python.node.span.start, from_python.node.span.end) == (2, 3)
    assert (from_rust.node.span.start, from_rust.node.span.end) == (2, 3)
    assert type(from_python.node.span) is not type(from_rust.node.span)


class TestWrongShapedNodes:
    """The error paths are backend-independent: same constructor, same message, same span.

    The wrong-shape cases are reachable only from a hand-built or mutated CST — the parser never
    puts a child of the wrong kind under a label — so each mutates a parsed node through the
    backend's own mutators.  The duplicate-key case is the one a parse alone reaches.
    """

    @staticmethod
    def _swap_child(node: typing.Any, index: int, child: typing.Any) -> typing.Any:
        """Replace one child in place, keeping the label already on it."""
        label = node.children[index][0]
        node.replace_at(index, child, label)
        return node

    def _raises(self, layer: Layer, rule: str, node: typing.Any) -> astrt.AstError:
        with pytest.raises(astrt.AstError) as excinfo:
            layer.convert(rule, node)
        return excinfo.value

    def test_a_sum_whose_child_matches_no_alternative(self, layer: Layer) -> None:
        """`atom` accepts a Num or a Name; a Name under the `num` label matches neither arm."""
        from_python = self._raises(
            layer, "atom", self._swap_child(layer.py_cst("atom", "42"), 0, layer.py_cst("name", "zz"))
        )
        from_rust = self._raises(
            layer, "atom", self._swap_child(layer.rust_cst("atom", "42"), 0, layer.rust_cst("name", "zz"))
        )
        assert str(from_python) == str(from_rust)
        assert "no alternative matches" in str(from_python)

    def test_a_product_whose_label_holds_a_child_of_the_wrong_kind(self, layer: Layer) -> None:
        """`entry`'s `key` label carries an EntryKey; an Atom there is the wrong-kind error."""
        from_python = self._raises(
            layer, "entry", self._swap_child(layer.py_cst("entry", "a = 1 ;"), 0, layer.py_cst("atom", "9"))
        )
        from_rust = self._raises(
            layer, "entry", self._swap_child(layer.rust_cst("entry", "a = 1 ;"), 0, layer.rust_cst("atom", "9"))
        )
        assert str(from_python) == str(from_rust)
        assert "unexpected kind" in str(from_python)

    def test_a_missing_required_child(self, layer: Layer) -> None:
        """An emptied node fails the same way whichever backend emptied it."""
        python_node = layer.py_cst("stmt", "x = y")
        python_node.clear()
        rust_node = layer.rust_cst("stmt", "x = y")
        rust_node.clear()
        from_python = self._raises(layer, "stmt", python_node)
        from_rust = self._raises(layer, "stmt", rust_node)
        assert str(from_python) == str(from_rust)
        assert "expected exactly one 'lhs' child, found 0" in str(from_python)

    def test_a_duplicate_key_in_a_keyed_collection(self, layer: Layer) -> None:
        """The one forward error a parser-produced tree reaches, and the one with a related span.

        The error message includes the offending element's span and a note citing an earlier one, so
        this is also where a native span must resolve to the same line and column as a Python one.
        """
        from_python = self._raises(layer, "entries", layer.py_cst("entries", "{a=1;a=2;}"))
        from_rust = self._raises(layer, "entries", layer.rust_cst("entries", "{a=1;a=2;}"))
        assert str(from_python) == str(from_rust)
        assert "duplicate entry key 'a'" in str(from_python)
        assert "line 1, column 6" in str(from_python)


class TestBackpointer:
    """`option cst = true;`: the value keeps the node it came from, whichever backend made it."""

    def test_a_python_node_is_kept_by_identity(self, backpointer_layer: Layer) -> None:
        node = backpointer_layer.py_cst("quoted", "'ab5'")
        assert backpointer_layer.convert("quoted", node).cst is node

    def test_a_rust_node_is_kept_by_identity(self, backpointer_layer: Layer) -> None:
        node = backpointer_layer.rust_cst("quoted", "'ab5'")
        assert backpointer_layer.convert("quoted", node).cst is node

    def test_the_backpointer_does_not_break_cross_backend_equality(self, backpointer_layer: Layer) -> None:
        """The field is `compare=False`, so two backends' values still compare equal."""
        from_python, from_rust = backpointer_layer.convert_both("stmt", "x = y")
        assert from_python == from_rust
        assert from_python.cst is not from_rust.cst

    def test_a_nested_value_keeps_its_own_backends_node(self, backpointer_layer: Layer) -> None:
        """Every converted node records its own source node by identity, not just the root.

        Identity rather than kind: kinds compare equal across backends by design, so a kind
        assertion would also hold for a node the field must never carry.
        """
        rust_root = backpointer_layer.rust_cst("entries", "{a=1;}")
        value = backpointer_layer.convert("entries", rust_root)
        assert value.cst is rust_root
        entry = next(iter(value.entry.values()))
        assert entry.cst is rust_root.children[0][1]


def test_the_reverse_direction_builds_python_nodes_from_a_rust_derived_value(layer: Layer) -> None:
    """`to_cst` is Python-backend-only by design, whatever backend the value was converted from.

    The AST is backend-neutral data, but reverse construction needs span synthesis, which only the
    Python backend offers.  A value converted from a Rust CST therefore round-trips back into a
    Python CST — and that node is the one the Python unparser takes.
    """
    from_rust = layer.convert("stmt", layer.rust_cst("stmt", "x = y"))
    rebuilt = from_rust.to_cst()
    assert isinstance(rebuilt, layer.parser.cst_module.Stmt)
    assert rebuilt.kind == layer.rust_cst("stmt", "x = y").kind
    assert layer.convert("stmt", rebuilt) == from_rust
