"""Tests for the Python AST emitter: generate a module, exec it, convert real CSTs."""

from __future__ import annotations

import decimal
import pathlib
import re
import sys
import types
import typing
import uuid

import pytest

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import gsm2ast
from fltk.fegen.ast_test_grammars import (
    CONFIG_GRAMMAR,
    CONFIG_SIDECAR,
    CONFIG_TEXT,
    FOLD_GRAMMAR,
    FOLD_SIDECAR,
    KEYED_SIDECAR,
    TASK_GRAMMAR,
    TASK_SIDECAR,
)
from fltk.fegen.pyrt import astrt, terminalsrc
from fltk.plumbing import generate_parser, generate_unparser, parse_format_config, parse_grammar, parse_text
from fltk.plumbing_types import ParserResult
from fltk.unparse.renderer import RendererConfig


class Generated(typing.NamedTuple):
    """A generated parser plus the AST module built from the same grammar."""

    parser: ParserResult
    ast: types.ModuleType
    source: str

    def convert(self, text: str, rule: str) -> typing.Any:
        result = parse_text(self.parser, text, rule)
        assert result.success, result.error_message
        return getattr(self.ast, f"{rule}_from_cst")(result.cst)


def build(grammar_text: str, *, capture_trivia: bool = False) -> Generated:
    return ast_module_for(generate_parser(parse_grammar(grammar_text), capture_trivia=capture_trivia))


def ast_module_for(
    parser_result: ParserResult,
    parser_module: str | None = None,
    unparser_module: str | None = None,
    goal: str | None = None,
    config: ac.ResolvedAstConfig | None = None,
) -> Generated:
    model = am.build_ast_model(parser_result.grammar, config)
    source = gsm2ast.generate_ast_module(model, parser_result.cst_module_name, parser_module, unparser_module, goal)
    module_name = f"generated_ast_{id(parser_result)}_{id(source)}"
    module = types.ModuleType(module_name)
    module.__dict__["__name__"] = module_name
    # dataclasses resolves a class's module out of sys.modules while building fields.
    sys.modules[module_name] = module
    exec(compile(source, "<generated_ast>", "exec"), module.__dict__)  # noqa: S102
    return Generated(parser=parser_result, ast=module, source=source)


def _register(name: str, **members: typing.Any) -> str:
    module = types.ModuleType(name)
    module.__dict__.update(members)
    sys.modules[name] = module
    return name


def build_configured(grammar_text: str, config_text: str, *, capture_trivia: bool = False) -> Generated:
    """A generated AST module shaped by a ``.fltkast`` sidecar."""
    parser_result = generate_parser(parse_grammar(grammar_text), capture_trivia=capture_trivia)
    config = ac.load_ast_config(config_text, parser_result.grammar, {ac.Backend.PYTHON})
    return ast_module_for(parser_result, config=config)


def build_roundtrip(
    grammar_text: str,
    goal: str | None,
    format_config: str | None = None,
    config_text: str | None = None,
) -> Generated:
    """A generated AST module wired to a parser and the grammar's formatter."""
    parser_result = generate_parser(parse_grammar(grammar_text), capture_trivia=True)
    unparser_result = generate_unparser(
        parser_result.grammar,
        parser_result.cst_module_name,
        parse_format_config(format_config) if format_config else None,
    )
    token = f"{id(parser_result)}_{id(unparser_result)}"
    config = (
        ac.load_ast_config(config_text, parser_result.grammar, {ac.Backend.PYTHON}) if config_text is not None else None
    )
    return ast_module_for(
        parser_result,
        _register(f"generated_parser_{token}", Parser=parser_result.parser_class),
        _register(f"generated_unparser_{token}", Unparser=unparser_result.unparser_class),
        goal,
        config,
    )


@pytest.fixture(scope="module")
def config() -> Generated:
    return build(CONFIG_GRAMMAR)


class TestConfigGrammar:
    """Tier-0 conversion of the worked config-language example, end to end."""

    def test_top_level_collection(self, config: Generated) -> None:
        cfg = config.convert(CONFIG_TEXT, "config")
        assert [type(stanza).__name__ for stanza in cfg.stanza] == ["ServerDef", "MetricDef"]

    def test_product_fields(self, config: Generated) -> None:
        server = config.convert(CONFIG_TEXT, "config").stanza[0]
        assert server.name.text == "web"
        assert [setting.key.text for setting in server.setting] == ["host", "port", "debug", "tags"]

    def test_sum_dispatch_selects_the_payload_type(self, config: Generated) -> None:
        settings = config.convert(CONFIG_TEXT, "config").stanza[0].setting
        values = {setting.key.text: setting.value for setting in settings}
        assert type(values["host"]).__name__ == "StringLiteral"
        assert values["host"].text == '"localhost"'
        assert type(values["port"]).__name__ == "Number"
        assert values["port"].text == "8080"
        assert type(values["debug"]).__name__ == "Boolean"

    def test_enum_shaped_rule_carries_a_value(self, config: Generated) -> None:
        settings = config.convert(CONFIG_TEXT, "config").stanza[0].setting
        debug = next(setting for setting in settings if setting.key.text == "debug")
        assert debug.value.value is config.ast.BooleanValue.TRUE

    def test_nested_collection(self, config: Generated) -> None:
        settings = config.convert(CONFIG_TEXT, "config").stanza[0].setting
        tags = next(setting for setting in settings if setting.key.text == "tags")
        assert [element.text for element in tags.value.value] == ["1", "2"]

    def test_optional_field_present(self, config: Generated) -> None:
        metric = config.convert(CONFIG_TEXT, "config").stanza[1]
        assert metric.name.text == "hits"
        assert metric.type.value is config.ast.MetricTypeValue.COUNTER
        assert metric.interval is not None
        assert metric.interval.text == "30"

    def test_optional_field_absent(self, config: Generated) -> None:
        cfg = config.convert("metric hits : gauge ;\n", "config")
        assert cfg.stanza[0].interval is None

    def test_value_enum_members_carry_canonical_names(self, config: Generated) -> None:
        assert config.ast.MetricTypeValue.GAUGE._fltk_canonical_name == "MetricTypeValue.GAUGE"

    def test_value_enum_compares_across_backends(self, config: Generated) -> None:
        """A foreign member carrying the same canonical name is the same variant."""

        class Mirror:
            _fltk_canonical_name = "MetricTypeValue.GAUGE"

        gauge = config.ast.MetricTypeValue.GAUGE
        assert gauge == Mirror()
        assert Mirror() != config.ast.MetricTypeValue.COUNTER
        assert hash(gauge) == hash("MetricTypeValue.GAUGE")
        assert gauge != config.ast.MetricTypeValue.COUNTER
        assert gauge != "MetricTypeValue.GAUGE"
        assert len({gauge, config.ast.MetricTypeValue.COUNTER}) == 2

    def test_spans_locate_the_node(self, config: Generated) -> None:
        server = config.convert(CONFIG_TEXT, "config").stanza[0]
        assert server.name.span.text() == "web"


class TestEquality:
    """Equality is semantic value-equality; source position never participates."""

    def test_same_text_at_different_offsets_compares_equal(self, config: Generated) -> None:
        one = config.convert("server a {\n  x = 1;\n}\n", "config")
        other = config.convert("\n\n\nserver a {\n  x = 1;\n}\n", "config")
        assert one.stanza[0].span.start != other.stanza[0].span.start
        assert one == other

    def test_different_values_compare_unequal(self, config: Generated) -> None:
        one = config.convert("server a {\n  x = 1;\n}\n", "config")
        other = config.convert("server a {\n  x = 2;\n}\n", "config")
        assert one != other


class TestTriviaIndependence:
    """The converter skips unlabeled children, so trivia capture cannot change the AST."""

    def test_both_parser_flavours_convert_identically(self) -> None:
        grammar = parse_grammar(CONFIG_GRAMMAR)
        without = generate_parser(grammar, capture_trivia=False)
        with_trivia = generate_parser(grammar, capture_trivia=True)
        generated = ast_module_for(without)

        plain = parse_text(without, CONFIG_TEXT, "config")
        captured = parse_text(with_trivia, CONFIG_TEXT, "config")
        assert plain.success
        assert captured.success
        # One AST module converts CSTs from either parser: the dispatch signatures name
        # NodeKind members, which compare equal across the two CST modules.
        assert generated.ast.config_from_cst(plain.cst) == generated.ast.config_from_cst(captured.cst)


PRESENCE_GRAMMAR = """
decl := pub:"pub"? , name:word . ";" ;
word := chars:/[a-z]+/ ;
"""


class TestPresenceBool:
    def test_present_and_absent_literal(self) -> None:
        generated = build(PRESENCE_GRAMMAR)
        assert generated.convert("pub foo;", "decl").pub is True
        assert generated.convert("foo;", "decl").pub is False


FIELD_ENUM_GRAMMAR = """
entry := ( val:number | val:word ) . ";" ;
number := digits:/[0-9]+/ ;
word := chars:/[a-z]+/ ;
"""


class TestFieldEnum:
    """A label carrying more than one type becomes a union whose converter dispatches on kind."""

    def test_each_member_type_converts(self) -> None:
        generated = build(FIELD_ENUM_GRAMMAR)
        assert type(generated.convert("12;", "entry").val).__name__ == "Number"
        assert type(generated.convert("ab;", "entry").val).__name__ == "Word"

    def test_alias_is_emitted(self) -> None:
        generated = build(FIELD_ENUM_GRAMMAR)
        assert 'EntryVal: typing.TypeAlias = "Number | Word"' in generated.source


MERGED_GRAMMAR = """
import_stmt := "import" : name:word : "as" : alias:word | "import" : name:word ;
word := chars:/[a-z]+/ ;
"""


class TestMergedProduct:
    """Subset-shaped alternatives merge into one shape with optional parts."""

    def test_short_and_long_forms_share_a_type(self) -> None:
        generated = build(MERGED_GRAMMAR)
        short = generated.convert("import foo", "import_stmt")
        long = generated.convert("import foo as bar", "import_stmt")
        assert type(short) is type(long)
        assert short.alias is None
        assert long.alias is not None
        assert long.alias.text == "bar"


SPAN_FIELD_GRAMMAR = """
tagged := , mark:"!" , name:word , dot:"."* ;
word := chars:/[a-z]+/ ;
"""


class TestLabeledLiteralFields:
    """A labeled literal carries position only; its text is a grammar constant."""

    def test_required_literal_is_a_span_and_repeats_collect(self) -> None:
        generated = build(SPAN_FIELD_GRAMMAR)
        tagged = generated.convert("! foo ..", "tagged")
        assert tagged.mark.text() == "!"
        assert len(tagged.dot) == 2

    def test_positions_and_occurrence_counts_stay_out_of_equality(self) -> None:
        generated = build(SPAN_FIELD_GRAMMAR)
        assert generated.convert("!foo..", "tagged") == generated.convert("  !foo.", "tagged")


class TestInTreeGrammar:
    def test_fegen_grammar_generates_an_importable_module(self) -> None:
        """The grammar FLTK is written in models cleanly under Tier 0 and execs."""
        text = (pathlib.Path(__file__).parent / "fegen.fltkg").read_text()
        generated = build(text)
        assert "def grammar_from_cst(" in generated.source


OPTIONAL_GRAMMAR = """
opt := name:word , extra:word? ;
word := c:/[a-z]+/ ;
"""


def source_node(node_class: typing.Any, text: str) -> typing.Any:
    """A hand-built terminal-only CST node whose span carries ``text``."""
    return node_class(span=terminalsrc.Span.with_source(0, len(text), text))


class TestConversionErrors:
    """Arity violations are only reachable from hand-built CSTs, and are span-bearing."""

    def test_missing_required_child(self, config: Generated) -> None:
        node = config.parser.cst_module.Setting()
        with pytest.raises(astrt.AstError, match="expected exactly one 'key' child, found 0"):
            config.ast.setting_from_cst(node)

    def test_sum_with_no_matching_alternative(self, config: Generated) -> None:
        node = config.parser.cst_module.Value()
        with pytest.raises(astrt.AstError, match="no alternative matches"):
            config.ast.value_from_cst(node)

    def test_optional_label_with_two_children(self) -> None:
        generated = build(OPTIONAL_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Opt()
        node.append(source_node(cst.Word, "a"), cst.Opt.Label.NAME)
        for text in ("b", "c"):
            node.append(source_node(cst.Word, text), cst.Opt.Label.EXTRA)
        with pytest.raises(astrt.AstError, match="expected at most one 'extra' child, found 2"):
            generated.ast.opt_from_cst(node)

    def test_presence_label_with_two_children(self) -> None:
        generated = build(PRESENCE_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Decl()
        node.append(source_node(cst.Word, "a"), cst.Decl.Label.NAME)
        for _ in range(2):
            node.append(terminalsrc.UnknownSpan, cst.Decl.Label.PUB)
        with pytest.raises(astrt.AstError, match="expected at most one 'pub' child, found 2"):
            generated.ast.decl_from_cst(node)

    def test_node_span_without_source_text(self, config: Generated) -> None:
        """A terminal-only rule's ``text`` is its own span, so a sourceless one is fatal."""
        with pytest.raises(astrt.AstError, match="rule 'number': node span carries no source text"):
            config.ast.number_from_cst(config.parser.cst_module.Number())

    def test_labeled_span_child_without_source_text(self) -> None:
        generated = build(PAIR_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Pair()
        node.append(terminalsrc.UnknownSpan, cst.Pair.Label.KEY)
        node.append(source_node(cst.Number, "1"), cst.Pair.Label.VALUE)
        with pytest.raises(astrt.AstError, match="the 'key' span carries no source text"):
            generated.ast.pair_from_cst(node)

    def test_enum_shaped_node_with_no_alternative_label(self, config: Generated) -> None:
        with pytest.raises(astrt.AstError, match="rule 'metric_type': no alternative label is present"):
            config.ast.metric_type_from_cst(config.parser.cst_module.MetricType())

    def test_field_enum_child_of_an_unexpected_kind(self) -> None:
        generated = build(FIELD_ENUM_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Entry()
        node.append(terminalsrc.Span.with_source(0, 1, "x"), cst.Entry.Label.VAL)
        with pytest.raises(astrt.AstError, match="label 'val' has a child of unexpected kind"):
            generated.ast.entry_from_cst(node)

    def test_a_span_where_a_node_belongs_is_refused(self) -> None:
        """The wrong-kind diagnostic at an ordinary single-kind label.

        Without the check the span goes straight into the referenced rule's converter and the
        failure surfaces as an incidental ``AttributeError`` from inside it, with no span, no rule
        and no label — where the Rust converter refuses it by name.
        """
        generated = build(OPTIONAL_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Opt()
        node.append(terminalsrc.Span.with_source(0, 1, "a"), cst.Opt.Label.NAME)
        with pytest.raises(astrt.AstError, match="rule 'opt': label 'name' has a child of unexpected kind"):
            generated.ast.opt_from_cst(node)

    def test_a_node_where_a_span_belongs_is_refused(self) -> None:
        generated = build(PAIR_GRAMMAR)
        cst = generated.parser.cst_module
        node = cst.Pair()
        node.append(source_node(cst.Number, "1"), cst.Pair.Label.KEY)
        node.append(source_node(cst.Number, "1"), cst.Pair.Label.VALUE)
        with pytest.raises(astrt.AstError, match="rule 'pair': label 'key' has a child of unexpected kind"):
            generated.ast.pair_from_cst(node)

    def test_a_node_where_a_labeled_literal_belongs_is_refused(self) -> None:
        generated = build('marks := bang:"!" , name:word ;\nword := c:/[a-z]+/ ;\n')
        cst = generated.parser.cst_module
        node = cst.Marks()
        node.append(source_node(cst.Word, "a"), cst.Marks.Label.BANG)
        node.append(source_node(cst.Word, "b"), cst.Marks.Label.NAME)
        with pytest.raises(astrt.AstError, match="rule 'marks': label 'bang' has a child of unexpected kind"):
            generated.ast.marks_from_cst(node)

    def test_error_omits_position_when_the_span_has_no_source(self, config: Generated) -> None:
        node = config.parser.cst_module.Setting()
        error = astrt.AstError("boom", node.span)
        assert str(error) == "boom"

    def test_error_reports_a_one_based_line_and_column(self) -> None:
        """Spans count from zero and diagnostics from one; the offsets must not be swapped."""
        span = terminalsrc.Span.with_source(6, 9, "abc\nde f\nghi")
        assert str(astrt.AstError("boom", span)) == "boom at line 2, column 3"


PAIR_GRAMMAR = """
pair := key:/[a-z]+/ . "=" . value:number ;
number := digits:/[0-9]+/ ;
"""


@pytest.fixture(scope="module")
def trip() -> Generated:
    return build_roundtrip(CONFIG_GRAMMAR, "config")


class TestRoundTrip:
    """``from_cst(parse(unparse(a))) == a``: the law the serialize direction owes."""

    def test_parsed_value_survives_a_round_trip(self, trip: Generated) -> None:
        value = trip.ast.parse(CONFIG_TEXT)
        assert trip.ast.parse(trip.ast.unparse(value)) == value

    def test_mutated_value_survives_a_round_trip(self, trip: Generated) -> None:
        value = trip.ast.parse(CONFIG_TEXT)
        value.stanza[0].setting[1].value = trip.ast.Number(text="9001")
        rendered = trip.ast.unparse(value)
        assert "9001" in rendered
        assert trip.ast.parse(rendered) == value

    def test_hand_built_value_survives_a_round_trip(self, trip: Generated) -> None:
        ast = trip.ast
        value = ast.Config(
            stanza=[
                ast.ServerDef(
                    name=ast.Identifier(text="db"),
                    setting=[ast.Setting(key=ast.Identifier(text="port"), value=ast.Number(text="5432"))],
                )
            ]
        )
        assert ast.parse(ast.unparse(value)) == value

    def test_optional_field_left_absent(self, trip: Generated) -> None:
        ast = trip.ast
        value = ast.Config(
            stanza=[
                ast.MetricDef(
                    name=ast.Identifier(text="hits"),
                    type=ast.MetricType(value=ast.MetricTypeValue.GAUGE),
                    interval=None,
                )
            ]
        )
        rendered = ast.unparse(value)
        assert "interval" not in rendered
        assert ast.parse(rendered) == value

    def test_nested_collection_round_trips(self, trip: Generated) -> None:
        ast = trip.ast
        value = ast.List(value=[ast.Number(text="1"), ast.Number(text="2"), ast.Number(text="3")])
        node = ast.list_to_cst(value)
        assert ast.list_from_cst(node) == value

    def test_empty_collection_round_trips(self, trip: Generated) -> None:
        ast = trip.ast
        value = ast.List(value=[])
        assert ast.list_from_cst(ast.list_to_cst(value)) == value

    def test_sum_dispatches_on_the_payload_class(self, trip: Generated) -> None:
        ast = trip.ast
        node = ast.value_to_cst(ast.Boolean(value=ast.BooleanValue.FALSE))
        assert ast.value_from_cst(node) == ast.Boolean(value=ast.BooleanValue.FALSE)

    def test_terminal_text_is_split_across_the_grammar_items(self, trip: Generated) -> None:
        node = trip.ast.StringLiteral(text='"hi"').to_cst()
        assert [child.text() for _label, child in node.children] == ["hi"]

    def test_parse_reports_a_syntax_error(self, trip: Generated) -> None:
        with pytest.raises(astrt.ParseError) as caught:
            trip.ast.parse("server {")
        assert caught.value.position > 0


REPEATED_TERMINAL_GRAMMAR = """
holder := word:word , ";" ;
word := c:/[a-z]/+ ;
"""

MIXED_TERMINAL_GRAMMAR = """
holder := val:mixed , ";" ;
mixed := p:/[a-z]/* | w:/[0-9]+/ ;
"""
"""One alternative a repeated item leaves unrebuildable, one that a single regex spells."""


class TestSerializeErrors:
    """Everything ``to_cst`` refuses, and why."""

    def test_field_text_that_the_terminal_cannot_match(self) -> None:
        generated = build_roundtrip(PAIR_GRAMMAR, "pair")
        with pytest.raises(astrt.AstError, match="does not match the terminal"):
            generated.ast.Pair(key="NOPE", value=generated.ast.Number(text="1")).to_cst()

    def test_terminal_only_text_that_the_rule_cannot_match(self, trip: Generated) -> None:
        with pytest.raises(astrt.AstError, match="not something the rule could have matched"):
            trip.ast.StringLiteral(text="unquoted").to_cst()

    def test_terminal_only_rule_whose_shape_cannot_be_split(self) -> None:
        """A repeated included item leaves no determined split."""
        generated = build(REPEATED_TERMINAL_GRAMMAR)
        value = generated.convert("abc;", "holder").word
        assert value.text == "abc"
        with pytest.raises(astrt.AstError, match="rule 'word': the rule's shape cannot be rebuilt from text"):
            value.to_cst()

    def test_a_rule_only_some_of_whose_alternatives_can_be_split(self) -> None:
        """The rebuildable alternative still serves the texts it matches."""
        generated = build(MIXED_TERMINAL_GRAMMAR)
        node = generated.ast.Mixed(text="42").to_cst()
        assert [child.text() for _label, child in node.children] == ["42"]

    def test_text_only_an_unrebuildable_alternative_could_have_matched(self) -> None:
        """The rule as a whole can be rebuilt, so the text is what the diagnostic names."""
        generated = build(MIXED_TERMINAL_GRAMMAR)
        with pytest.raises(astrt.AstError, match="rule 'mixed': text 'abc' is not something"):
            generated.ast.Mixed(text="abc").to_cst()

    def test_more_values_than_the_grammar_has_positions_for(self) -> None:
        generated = build_roundtrip(PAIR_GRAMMAR, "pair")
        value = generated.ast.Pair(key=["a", "b"], value=generated.ast.Number(text="1"))
        with pytest.raises(astrt.AstError, match="no place for 1 more 'key' value"):
            value.to_cst()

    def test_a_value_no_alternation_branch_accepts(self) -> None:
        generated = build_roundtrip(FIELD_ENUM_GRAMMAR, "entry")
        with pytest.raises(astrt.AstError, match="no item position accepts a str value for 'val'"):
            generated.ast.Entry(val="raw string").to_cst()

    def test_enum_shaped_node_with_an_unknown_value(self, trip: Generated) -> None:
        with pytest.raises(astrt.AstError, match="rule 'boolean': unknown value"):
            trip.ast.Boolean(value=None).to_cst()

    def test_no_alternative_fits_the_populated_fields(self) -> None:
        generated = build_roundtrip(MERGED_GRAMMAR, "import_stmt")
        value = generated.convert("import foo", "import_stmt")
        value.name = None
        with pytest.raises(astrt.AstError, match="no alternative fits"):
            value.to_cst()

    def test_a_value_the_sum_has_no_variant_for(self, trip: Generated) -> None:
        with pytest.raises(astrt.AstError, match="cannot synthesise from a"):
            trip.ast.value_to_cst(trip.ast.Identifier(text="oops"))


class TestInlineTerminalFields:
    """A labeled regex inside a product carries its own single-token source."""

    def test_text_fields_round_trip(self) -> None:
        generated = build_roundtrip(PAIR_GRAMMAR, "pair")
        value = generated.ast.Pair(key="port", value=generated.ast.Number(text="8080"))
        assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestMergedProductSerialize:
    """A merged product picks the first alternative its populated fields fit."""

    def test_short_and_long_forms_each_round_trip(self) -> None:
        generated = build_roundtrip(MERGED_GRAMMAR, "import_stmt")
        for text in ("import foo", "import foo as bar"):
            value = generated.convert(text, "import_stmt")
            assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestPresenceBoolSerialize:
    def test_flag_decides_whether_the_literal_is_emitted(self) -> None:
        generated = build_roundtrip(PRESENCE_GRAMMAR, "decl")
        for text in ("pub foo;", "foo;"):
            value = generated.convert(text, "decl")
            assert generated.ast.parse(generated.ast.unparse(value)) == value
        assert "pub" in generated.ast.unparse(generated.convert("pub foo;", "decl"))


class TestFieldEnumSerialize:
    """Rival slots for one label take only the values whose type they accept."""

    def test_each_member_type_round_trips(self) -> None:
        generated = build_roundtrip(FIELD_ENUM_GRAMMAR, "entry")
        for text in ("12;", "ab;"):
            value = generated.convert(text, "entry")
            assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestLabeledLiteralSerialize:
    """Labeled literals come back from the grammar; only their occurrence count is kept."""

    def test_repeats_are_re_emitted(self) -> None:
        generated = build_roundtrip(SPAN_FIELD_GRAMMAR, "tagged")
        value = generated.convert("!foo..", "tagged")
        rendered = generated.ast.unparse(value)
        assert rendered.count(".") == 2
        assert generated.ast.parse(rendered) == value


PAYLOAD_GRAMMAR = """
pick := x:num : a:num | x:word . "/" . a:word? ;
num := d:/[0-9]+/ ;
word := c:/[a-z]+/ ;
"""


class TestSumPayloadClasses:
    """A sum whose alternatives are multi-item gets a generated payload class per variant."""

    @staticmethod
    def payloads() -> Generated:
        return build_roundtrip(PAYLOAD_GRAMMAR, "pick")

    def test_the_model_generates_a_payload_class_per_alternative(self) -> None:
        model = am.build_ast_model(self.payloads().parser.grammar)
        assert sorted(model.payload_classes) == ["PickAlt1", "PickAlt2"]

    def test_kind_dispatch_picks_the_variant(self) -> None:
        """Both alternatives carry the same labels, so only the child kinds separate them."""
        generated = self.payloads()
        assert type(generated.convert("12 34", "pick")).__name__ == "PickAlt1"
        assert type(generated.convert("ab/cd", "pick")).__name__ == "PickAlt2"

    def test_payload_fields_are_populated(self) -> None:
        generated = self.payloads()
        value = generated.convert("12 34", "pick")
        assert value.x.text == "12"
        assert value.a.text == "34"

    def test_per_alternative_arity_keeps_the_optional_label_optional(self) -> None:
        """``a`` is required in the first alternative and optional in the second."""
        generated = self.payloads()
        assert generated.convert("ab/", "pick").a is None

    @pytest.mark.parametrize("text", ["12 34", "ab/cd", "ab/"])
    def test_each_variant_round_trips(self, text: str) -> None:
        generated = self.payloads()
        value = generated.convert(text, "pick")
        assert generated.ast.parse(generated.ast.unparse(value)) == value


NESTED_SUM_GRAMMAR = """
top := t:outer | u:num ;
outer := i:inner | b:word ;
inner := x:num . "!" ;
num := d:/[0-9]+/ ;
word := c:/[a-z]+/ ;
"""


class TestNestedSums:
    """A sum whose variant payload is another sum: the union alias is a string at runtime."""

    def test_the_payload_tuple_holds_only_concrete_classes(self) -> None:
        generated = build(NESTED_SUM_GRAMMAR)
        assert "_TOP_PAYLOADS = (Inner, Word, Num,)" in generated.source
        assert "_OUTER_PAYLOADS = (Inner, Word,)" in generated.source

    @pytest.mark.parametrize("text", ["12!", "abc", "34"])
    def test_every_member_serialises_through_the_outer_sum(self, text: str) -> None:
        generated = build_roundtrip(NESTED_SUM_GRAMMAR, "top")
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_class_reachable_twice_gets_payload_classes(self) -> None:
        """``Num`` sits in both variants' unions; a bare one could not say which variant it is,
        so both fall back to generated payload classes and each names its own alternative."""
        generated = build(
            "top := t:outer | u:num ;\nouter := i:word | b:num ;\nnum := d:/[0-9]+/ ;\nword := c:/[a-z]+/ ;\n"
        )
        assert 'Top: typing.TypeAlias = "TopT | TopU"' in generated.source
        assert type(generated.convert("12", "top")).__name__ == "TopT"
        node = generated.ast.top_to_cst(generated.ast.TopU(u=generated.ast.Num(text="12")))
        assert [label.name for label, _child in node.children] == ["U"]


LITERAL_RIVAL_GRAMMAR = """
val := ( x:"null" | x:/[0-9]+/ ) . u:word ;
word := c:/[a-z]+/ ;
"""

LITERAL_SEQUENCE_GRAMMAR = """
val := x:"null"? . x:/[0-9]+/ . u:word ;
word := c:/[a-z]+/ ;
"""


class TestLiteralRivalSlots:
    """A label mixing a literal with a regex carries text, so the literal position needs a
    content guard: taking a value it cannot render would replace it with the literal."""

    def test_the_literal_position_only_takes_the_literal(self) -> None:
        generated = build(LITERAL_RIVAL_GRAMMAR)
        node = generated.ast.Val(x="42", u=generated.ast.Word(text="u")).to_cst()
        assert [child.text() for _label, child in node.children] == ["42", "u"]

    def test_the_literal_position_still_takes_the_literal(self) -> None:
        generated = build(LITERAL_RIVAL_GRAMMAR)
        node = generated.ast.Val(x="null", u=generated.ast.Word(text="u")).to_cst()
        # A literal renders from the grammar, so its span carries position only.
        assert [child.text() for _label, child in node.children] == [None, "u"]

    def test_text_no_position_can_carry_is_an_error(self) -> None:
        generated = build(LITERAL_RIVAL_GRAMMAR)
        with pytest.raises(astrt.AstError, match="no item position accepts a str value for 'x'"):
            generated.ast.Val(x="oops", u=generated.ast.Word(text="u")).to_cst()

    def test_a_sequential_literal_position_does_not_steal_the_regex_value(self) -> None:
        generated = build(LITERAL_SEQUENCE_GRAMMAR)
        node = generated.ast.Val(x=["42"], u=generated.ast.Word(text="u")).to_cst()
        assert [child.text() for _label, child in node.children] == ["42", "u"]
        assert generated.ast.val_from_cst(node).x == ["42"]

    def test_a_sequential_literal_position_takes_the_literal_when_it_is_there(self) -> None:
        generated = build(LITERAL_SEQUENCE_GRAMMAR)
        node = generated.ast.Val(x=["null", "42"], u=generated.ast.Word(text="u")).to_cst()
        assert [child.text() for _label, child in node.children] == [None, "42", "u"]

    @pytest.mark.parametrize("text", ["42u", "nullu"])
    def test_the_rival_shape_round_trips_through_unparse(self, text: str) -> None:
        """The formatter's trial reads a labeled literal's text, so the regex branch keeps its
        own value instead of being re-rendered as the literal."""
        generated = build_roundtrip(LITERAL_RIVAL_GRAMMAR, "val")
        value = generated.convert(text, "val")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    @pytest.mark.parametrize("text", ["42u", "null42u"])
    def test_the_sequential_shape_round_trips_through_unparse(self, text: str) -> None:
        generated = build_roundtrip(LITERAL_SEQUENCE_GRAMMAR, "val")
        value = generated.convert(text, "val")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_rival_value_round_trips(self) -> None:
        generated = build_roundtrip(LITERAL_RIVAL_GRAMMAR, "val")
        value = generated.ast.Val(x="42", u=generated.ast.Word(text="u"))
        assert generated.ast.unparse(value) == "42u"
        assert generated.ast.parse(generated.ast.unparse(value)) == value


SHORTFALL_GRAMMAR = """
pair := a:num . "," . a:num ;
num := d:/[0-9]+/ ;
"""


class TestRequiredPositionShortfall:
    """A field short of what the grammar's positions demand is the user's data error, not a
    CST the formatter gets to reject on its own."""

    def test_too_few_values_for_two_required_positions(self) -> None:
        generated = build(SHORTFALL_GRAMMAR)
        value = generated.ast.Pair(a=[generated.ast.Num(text="1")])
        with pytest.raises(astrt.AstError, match=r"needs 1 'a' value\(s\) at this position, but 0 were available"):
            value.to_cst()

    def test_enough_values_synthesise_both_children(self) -> None:
        generated = build(SHORTFALL_GRAMMAR)
        value = generated.ast.Pair(a=[generated.ast.Num(text="1"), generated.ast.Num(text="2")])
        assert generated.ast.pair_from_cst(value.to_cst()) == value

    def test_a_required_alternation_branch_needs_one_value(self) -> None:
        generated = build(FIELD_ENUM_GRAMMAR)
        with pytest.raises(astrt.AstError, match=r"needs one of \['val'\] at this position"):
            generated.ast.Entry(val=None).to_cst()


BRANCH_FLAG_GRAMMAR = """
decl := ( mut:"mut" | const:"const" ) : name:word . ";" ;
word := chars:/[a-z]+/ ;
"""

BRANCH_RULE_GRAMMAR = """
entry := ( a:num | b:word ) . ";" ;
num := digits:/[0-9]+/ ;
word := chars:/[a-z]+/ ;
"""

BRANCH_SUPPRESSED_GRAMMAR = """
entry := ( a:num | %"none" ) . ";" ;
num := digits:/[0-9]+/ ;
"""


class TestAlternationDistinctLabels:
    """Branches carrying different labels: only one label is ever populated, so no position
    inside the alternation may insist on a value of its own."""

    @pytest.mark.parametrize("text", ["mut x;", "const x;"])
    def test_the_flag_flavor_round_trips(self, text: str) -> None:
        generated = build_roundtrip(BRANCH_FLAG_GRAMMAR, "decl")
        value = generated.convert(text, "decl")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    @pytest.mark.parametrize("text", ["7;", "ab;"])
    def test_the_rule_reference_flavor_round_trips(self, text: str) -> None:
        generated = build_roundtrip(BRANCH_RULE_GRAMMAR, "entry")
        value = generated.convert(text, "entry")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_branch_of_suppressed_literals_needs_nothing_populated(self) -> None:
        generated = build_roundtrip(BRANCH_SUPPRESSED_GRAMMAR, "entry")
        value = generated.convert("none;", "entry")
        assert value.a is None
        assert generated.ast.unparse(value) == "none;"

    def test_two_branches_at_once_is_an_error(self) -> None:
        generated = build(BRANCH_FLAG_GRAMMAR)
        value = generated.ast.Decl(mut=True, const=True, name=generated.ast.Word(text="x"))
        with pytest.raises(astrt.AstError, match=r"\['const', 'mut'\] cannot come from one branch"):
            value.to_cst()

    def test_no_branch_at_all_is_an_error(self) -> None:
        generated = build(BRANCH_FLAG_GRAMMAR)
        value = generated.ast.Decl(mut=False, const=False, name=generated.ast.Word(text="x"))
        with pytest.raises(astrt.AstError, match=r"needs one of \['const', 'mut'\] at this position"):
            value.to_cst()

    def test_a_label_the_alternative_also_uses_outside_the_group_is_not_checked(self) -> None:
        """The value may have come from the outer position, so the group cannot judge it."""
        generated = build("""
        entry := ( a:num | b:word ) . "," . a:num ;
        num := digits:/[0-9]+/ ;
        word := chars:/[a-z]+/ ;
        """)
        value = generated.ast.Entry(a=[generated.ast.Num(text="1")], b=generated.ast.Word(text="x"))
        assert [child.text() for _label, child in value.to_cst().children] == ["x", "1"]


BRANCH_TEXT_GRAMMAR = """
entry := ( v:/[0-9]+/ | v:/[a-z]+/ ) : r:word . ";" ;
word := chars:/[a-z]+/ ;
"""

# A bad idiom: `v` is always present and carries two different literal texts, so the grammar
# declares the two spellings equivalent while an author writing it almost certainly meant to
# record which word was written.  Distinct values take distinct labels (`yes:"yes" | no:"no"`,
# which generates a value enum); a literal with no discriminatory effect takes no label at all.
# Unparser generation refuses the shape, so an AST built from it has no `unparse` convenience.
BRANCH_LITERAL_GRAMMAR = """
entry := ( v:"yes" | v:"no" ) : r:word . ";" ;
word := chars:/[a-z]+/ ;
"""


class TestSameKindBranchDispatch:
    """Branches sharing a label and a kind are told apart by what their terminals match, so
    they stay one dispatch run rather than collapsing into rival positions."""

    @pytest.mark.parametrize("text", ["7 ab;", "cd ab;"])
    def test_two_regex_branches_round_trip(self, text: str) -> None:
        generated = build_roundtrip(BRANCH_TEXT_GRAMMAR, "entry")
        value = generated.convert(text, "entry")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_each_regex_branch_takes_its_own_text(self) -> None:
        generated = build(BRANCH_TEXT_GRAMMAR)
        node = generated.ast.Entry(v="cd", r=generated.ast.Word(text="ab")).to_cst()
        assert [child.text() for _label, child in node.children] == ["cd", "ab"]

    def test_text_neither_branch_matches_is_an_error(self) -> None:
        generated = build(BRANCH_TEXT_GRAMMAR)
        with pytest.raises(astrt.AstError, match="no item position accepts a str value for 'v'"):
            generated.ast.Entry(v="1a", r=generated.ast.Word(text="ab")).to_cst()

    def test_two_literal_branches_have_no_formatter_at_all(self) -> None:
        """``BRANCH_LITERAL_GRAMMAR`` is refused at unparser generation, so the AST's text
        conveniences are unavailable — the same posture as a grammar with a required suppressed
        regex.  Both spellings still convert; the field is a bare position either way."""
        with pytest.raises(RuntimeError, match="covers more than one spelling"):
            build_roundtrip(BRANCH_LITERAL_GRAMMAR, "entry")
        generated = build(BRANCH_LITERAL_GRAMMAR)
        assert generated.convert("yes ab;", "entry") == generated.convert("no ab;", "entry")


ERASED_BRANCH_GRAMMAR = """
atom := ( v:name | v:number ) . ";" ;
name   := t:/[a-z]+/ ;
number := d:/[0-9]+/ ;
"""

SCALAR_BRANCH_GRAMMAR = """
entry := ( v:num | v:flag ) . ";" ;
num  := d:/[0-9]+/ ;
flag := yes:"true" | no:"false" ;
"""


class TestErasedBranchDispatch:
    """Branches whose rules ``transparent;`` erases to one Python type carry nothing to test by,
    so each branch is guarded by its own converter instead."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(
            ERASED_BRANCH_GRAMMAR, "atom", config_text="rule name { transparent; }\nrule number { transparent; }\n"
        )

    @pytest.mark.parametrize(("text", "value"), [("abc;", "abc"), ("42;", "42")])
    def test_each_erased_branch_round_trips(self, text: str, value: str) -> None:
        generated = self.generated()
        parsed = generated.ast.parse(text)
        assert parsed.v == value
        assert generated.ast.unparse(parsed) == text
        assert generated.ast.parse(generated.ast.unparse(parsed)) == parsed

    def test_the_branch_is_chosen_by_what_its_terminal_matches(self) -> None:
        """Both branches carry ``str``, so a type test would route every value to the first."""
        generated = self.generated()
        assert "astrt.Convertible(_erased_number_to_cst)" in generated.source
        node = generated.ast.Atom(v="42").to_cst()
        assert [child.kind.name for _label, child in node.children] == ["NUMBER"]

    def test_text_no_branch_can_carry_is_an_error(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError, match="no item position accepts a str value for 'v'"):
            generated.ast.Atom(v="1a").to_cst()


class Money:
    """A hand-written stand-in for the Python type of a ``type: custom(...)`` coercion.

    ``render_money`` reads ``amount`` off the value, which is all its contract asks of it: the
    unparse hook is declared for one type.  Handed a sibling branch's ``str`` it raises a bare
    ``AttributeError``, so a dispatch guard that ran it as a probe would let that escape.
    """

    def __init__(self, amount: int) -> None:
        self.amount = amount

    def __repr__(self) -> str:
        return f"Money({self.amount!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Money) and other.amount == self.amount

    def __hash__(self) -> int:
        return hash(self.amount)


def _parse_money(text: str) -> Money:
    return Money(int(text[1:]))


def _render_money(value: Money) -> str:
    return f"${value.amount}"


MONEY_MODULE = _register(
    "generated_ast_money_custom",
    Money=Money,
    parse_money=_parse_money,
    render_money=_render_money,
)

MONEY_BRANCH_GRAMMAR = r"""
holding := ( v:money | v:name ) . ";" ;
money := digits:/\$[0-9]+/ ;
name  := t:/[a-z]+/ ;
"""

MONEY_BRANCH_CONFIG = (
    f'rule money {{ type: custom(py_type: "{MONEY_MODULE}.Money", '
    f'py_parse: "{MONEY_MODULE}.parse_money", py_unparse: "{MONEY_MODULE}.render_money"); transparent; }}\n'
    "rule name { transparent; }\n"
)


class TestCustomCoercedBranchDispatch:
    """A branch erased to a ``type: custom(...)`` value is told apart by its declared class.

    The class is concrete and the coercion's unparse hook is contracted for it alone, so the
    class test is both safe and sufficient — running the converter as a probe would hand user
    code a value of the sibling branch's type.
    """

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(MONEY_BRANCH_GRAMMAR, "holding", config_text=MONEY_BRANCH_CONFIG)

    @pytest.mark.parametrize(("text", "value"), [("$5;", Money(5)), ("abc;", "abc")])
    def test_each_branch_round_trips(self, text: str, value: object) -> None:
        generated = self.generated()
        parsed = generated.ast.parse(text)
        assert parsed.v == value
        assert generated.ast.unparse(parsed) == text
        assert generated.ast.parse(generated.ast.unparse(parsed)) == parsed

    def test_the_custom_branch_is_guarded_by_its_class_and_the_plain_one_by_its_converter(self) -> None:
        generated = self.generated()
        assert "astrt.Convertible(_erased_money_to_cst)" not in generated.source
        assert "astrt.Convertible(_erased_name_to_cst)" in generated.source

    def test_a_sibling_value_serialises_without_reaching_the_custom_hook(self) -> None:
        generated = self.generated()
        node = generated.ast.Holding(v="abc").to_cst()
        assert [child.kind.name for _label, child in node.children] == ["NAME"]

    def test_the_custom_value_serialises_through_its_own_branch(self) -> None:
        generated = self.generated()
        node = generated.ast.Holding(v=Money(12)).to_cst()
        assert [child.kind.name for _label, child in node.children] == ["MONEY"]


class TestScalarBranchPrecedence:
    """A boolean payload is offered a value before an integer one: ``bool`` is an ``int``."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(
            SCALAR_BRANCH_GRAMMAR,
            "entry",
            config_text="rule num { type: i64; transparent; }\nrule flag { bool: yes; transparent; }\n",
        )

    @pytest.mark.parametrize(("text", "value"), [("true;", True), ("false;", False), ("7;", 7)])
    def test_each_payload_round_trips(self, text: str, value: object) -> None:
        generated = self.generated()
        parsed = generated.ast.parse(text)
        assert parsed.v is value or parsed.v == value
        assert generated.ast.parse(generated.ast.unparse(parsed)) == parsed

    def test_a_boolean_renders_through_the_flag_position(self) -> None:
        """Without the precedence sort ``True`` reaches the integer position, which cannot spell it."""
        generated = self.generated()
        assert generated.ast.unparse(generated.ast.Entry(v=True)) == "true;"
        assert generated.ast.unparse(generated.ast.Entry(v=1)) == "1;"


WRAPPED_SCALAR_GRAMMAR = r"""
doc  := ( a:wrap | a:big ) . ";" ;
wrap := "(" . v:small . ")" ;
small := s:/[0-9][0-9]/ ;
big  := b:/[0-9]+/ ;
"""

WRAPPED_SCALAR_CONFIG = (
    "rule wrap { transparent; }\nrule small { transparent; type: i32; }\nrule big { transparent; type: i64; }\n"
)


class TestErasedWrapperBranchDispatch:
    """A branch erased through a wrapper still guards on what its terminal accepts."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(WRAPPED_SCALAR_GRAMMAR, "doc", config_text=WRAPPED_SCALAR_CONFIG)

    @pytest.mark.parametrize(("text", "value"), [("(42);", 42), ("1234;", 1234)])
    def test_each_branch_round_trips(self, text: str, value: int) -> None:
        """``wrap``'s payload is ``small``'s two-digit integer; only ``big`` can carry 1234."""
        generated = self.generated()
        parsed = generated.ast.parse(text)
        assert parsed.a == value
        assert generated.ast.unparse(parsed) == text
        assert generated.ast.parse(generated.ast.unparse(parsed)) == parsed

    def test_the_wrapper_branch_is_guarded_by_its_own_converter(self) -> None:
        """A plain ``int`` test on the wrapper would accept 1234 and then refuse to render it."""
        generated = self.generated()
        assert "astrt.Convertible(_erased_wrap_to_cst)" in generated.source

    def test_a_value_neither_terminal_accepts_is_an_error(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError, match="no item position accepts a int value for 'a'"):
            generated.ast.Doc(a=-1).to_cst()


EQUIVALENT_BOOLEAN_GRAMMAR = """
doc  := f:flag . ";" ;
flag := t:"true" | t:"yes" | f:"false" ;
"""


class TestEquivalentBooleanSpellings:
    """``bool:`` counts variants, so an equivalent spelling of the true value is allowed."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(EQUIVALENT_BOOLEAN_GRAMMAR, "doc", config_text="rule flag { bool: t; }\n")

    @pytest.mark.parametrize(("text", "value"), [("true;", True), ("yes;", True), ("false;", False)])
    def test_both_spellings_of_true_convert(self, text: str, value: bool) -> None:  # noqa: FBT001
        assert self.generated().convert(text, "doc").f.value is value

    def test_the_true_value_renders_through_the_first_spelling(self) -> None:
        generated = self.generated()
        assert generated.ast.unparse(generated.ast.Doc(f=generated.ast.Flag(value=True))) == "true;"

    def test_the_false_value_still_has_an_alternative_to_render_through(self) -> None:
        """With the count taken over alternatives this rule generated a ``False`` nothing spelled."""
        generated = self.generated()
        assert generated.ast.unparse(generated.ast.Doc(f=generated.ast.Flag(value=False))) == "false;"


# The repeated item sits *inside* branch 0, so its unbounded maximum is not the group's.
GROUP_STAR_GRAMMAR = """
top := "<" , ( ( , a:word)+ | b:num ) , ">" ;
word := c:/[a-z]+/ ;
num  := d:/[0-9]+/ ;
"""


class TestGroupWithARepeatedItemInsideOneBranch:
    """A starred item inside a branch is not the group repeating, so the branches stay exclusive."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(GROUP_STAR_GRAMMAR, "top", SPACED_FORMAT)

    @pytest.mark.parametrize("text", ["< a b >", "< 7 >"])
    def test_each_branch_round_trips(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_filling_both_branches_at_once_is_an_error(self) -> None:
        generated = self.generated()
        value = generated.ast.Top(a=[generated.ast.Word(text="x")], b=generated.ast.Num(text="1"))
        with pytest.raises(astrt.AstError, match=r"\['a', 'b'\] cannot come from one branch"):
            value.to_cst()


ALTERNATION_GRAMMAR = """
seq := ( a:num | a:name )* . ";" ;
num := d:/[0-9]+/ ;
name := c:/[a-z]+/ ;
"""


class TestAlternationBranchSerialize:
    """One label shared by an alternation's branches keeps its source order."""

    @pytest.mark.parametrize("text", ["1;", "x;", "1x2;", "x1;", "ab12cd;", ";"])
    def test_any_interleaving_round_trips(self, text: str) -> None:
        generated = build_roundtrip(ALTERNATION_GRAMMAR, "seq")
        value = generated.convert(text, "seq")
        assert generated.ast.unparse(value) == text
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_values_are_appended_in_field_order(self) -> None:
        """Position order follows the values, not the branch layout: `name` may come first."""
        generated = build_roundtrip(ALTERNATION_GRAMMAR, "seq")
        value = generated.ast.Seq(a=[generated.ast.Name(text="x"), generated.ast.Num(text="1")])
        node = value.to_cst()
        assert [child.text() for _label, child in node.children] == ["x", "1"]

    def test_a_value_of_no_branch_type_is_an_error(self) -> None:
        generated = build_roundtrip(ALTERNATION_GRAMMAR, "seq")
        with pytest.raises(astrt.AstError, match="no item position accepts a str value for 'a'"):
            generated.ast.Seq(a=["oops"]).to_cst()


RESERVE_GRAMMAR = """
mix := head:/[a-z]+/+ . "-" . head:/[0-9]+/ , tail:word ;
word := c:/[a-z]+/ ;
"""


class TestTrailingRequiredPosition:
    """A repeated position leaves behind what a later required position for the label needs."""

    def test_values_are_split_across_the_two_positions(self) -> None:
        generated = build(RESERVE_GRAMMAR)
        value = generated.ast.Mix(head=["ab", "cd", "12"], tail=generated.ast.Word(text="z"))

        node = value.to_cst()

        # The trailing "12" was held back for the /[0-9]+/ position: had the repeated
        # /[a-z]+/ position swallowed it, its terminal validation would have refused it.
        assert [child.text() for _label, child in node.children] == ["ab", "cd", "12", "z"]
        assert generated.ast.mix_from_cst(node).head == ["ab", "cd", "12"]

    def test_the_reserved_value_is_validated_against_the_trailing_terminal(self) -> None:
        generated = build(RESERVE_GRAMMAR)
        value = generated.ast.Mix(head=["ab", "cd"], tail=generated.ast.Word(text="z"))
        with pytest.raises(astrt.AstError, match=r"the 'head' text 'cd' does not match the terminal /\[0-9\]\+/"):
            value.to_cst()


WRAPPED_GRAMMAR = """
seq := "[" , item:word , ( "," , item:word )* , "]" ;
word := c:/[a-z]+/ ;
"""

WRAPPED_FORMAT = """
ws_allowed: bsp;

rule seq
{
    group;
    nest from after "[" to before "]";
}
"""


class TestRendererConfig:
    """``unparse``'s renderer_config reaches the renderer that lays the output out."""

    def test_width_and_indent_change_the_rendering(self) -> None:
        generated = build_roundtrip(WRAPPED_GRAMMAR, "seq", WRAPPED_FORMAT)
        value = generated.convert("[aaaa, bbbb, cccc]", "seq")

        default = generated.ast.unparse(value)
        narrow = generated.ast.unparse(value, RendererConfig(max_width=10))
        deep = generated.ast.unparse(value, RendererConfig(max_width=10, indent_width=8))

        assert "\n" not in default
        assert "\n    aaaa" in narrow
        assert "\n        aaaa" in deep
        assert generated.ast.parse(narrow) == value


SIDECAR_GRAMMAR = r"""
doc   := , entry* ;
entry := key:word , "=" , flavour:flavour , ";" , ;
flavour := very_hot:"vh" | cold:"cold" ;
word  := w:/[a-z]+/ ;
"""

SIDECAR_TEXT = "alpha = vh; beta = cold;"


class TestNamingOverrides:
    """`name:`, `variant` and `field { name: }` reach the emitted module."""

    @staticmethod
    def sidecar(config_text: str) -> Generated:
        return build_configured(SIDECAR_GRAMMAR, config_text)

    def test_renamed_rule_type_is_what_the_module_defines(self) -> None:
        generated = self.sidecar("rule doc { name: Document; }")
        assert not hasattr(generated.ast, "Doc")
        value = generated.convert(SIDECAR_TEXT, "doc")
        assert isinstance(value, generated.ast.Document)

    def test_renamed_value_enum_follows_its_rule(self) -> None:
        generated = self.sidecar("rule flavour { name: Taste; }")
        value = generated.convert(SIDECAR_TEXT, "doc")
        assert value.entry[0].flavour.value is generated.ast.TasteValue.VERY_HOT

    def test_default_value_enum_member_is_upper_snake(self) -> None:
        generated = self.sidecar("")
        assert [member.name for member in generated.ast.FlavourValue] == ["VERY_HOT", "COLD"]

    def test_renamed_value_enum_variant(self) -> None:
        generated = self.sidecar("rule flavour { variant VeryHot: Blazing; }")
        value = generated.convert(SIDECAR_TEXT, "doc")
        assert value.entry[0].flavour.value is generated.ast.FlavourValue.BLAZING
        assert generated.ast.FlavourValue.BLAZING._fltk_canonical_name == "FlavourValue.BLAZING"

    def test_renamed_field_keeps_reading_its_label(self) -> None:
        generated = self.sidecar("rule doc { field entry { name: entries; } }")
        value = generated.convert(SIDECAR_TEXT, "doc")
        assert [entry.key.text for entry in value.entries] == ["alpha", "beta"]

    def test_renamed_sum_variant_payload_class(self) -> None:
        generated = build_configured(
            "target := a:item . b:item | c:item ;\nitem := n:/[a-z]+/ ;\n",
            "rule target { variant Alt1: Pair; }",
        )
        assert hasattr(generated.ast, "TargetPair")
        assert not hasattr(generated.ast, "TargetAlt1")


class TestShapeOverridesEndToEnd:
    def test_forced_product_merges_the_alternatives(self) -> None:
        generated = build_configured(
            "target := a:item | b:item ;\nitem := n:/[a-z]+/ ;\n",
            "rule target { product; }",
        )
        value = generated.convert("xy", "target")
        assert isinstance(value, generated.ast.Target)
        assert value.a is not None
        assert value.b is None

    def test_forced_sum_dispatches_on_the_required_extra(self) -> None:
        generated = build_configured(
            "target := a:item , b:item | a:item ;\nitem := n:/[a-z]+/ ;\n",
            "rule target { sum; }",
        )
        assert generated.convert("xy", "target") == generated.ast.Item("xy")
        assert isinstance(generated.convert("xy zz", "target"), generated.ast.TargetAlt1)


class Flipped:
    """A hand-written stand-in for a ``custom(...)`` rule's type.

    Reverses the lexeme in both directions, so a test can tell the hook ran rather than the
    generated terminal-only converter.  Each instance carries the CST class it synthesises
    with — ``from_cst`` reads it off the node it converts — so two grammars' modules can never
    share one, and equality ignores it so a hand-built value compares to a converted one.
    """

    def __init__(self, text: str, cst_class: typing.Any = None) -> None:
        self.text = text
        self.cst_class = cst_class

    def __repr__(self) -> str:
        return f"Flipped({self.text!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Flipped) and other.text == self.text

    def __hash__(self) -> int:
        return hash(self.text)

    @classmethod
    def from_cst(cls, node: typing.Any) -> Flipped:
        return cls(astrt.node_text(node.span, "word")[::-1], type(node))

    def to_cst(self) -> typing.Any:
        if self.cst_class is None:
            msg = "this Flipped was built without a CST class, so it cannot synthesise one"
            raise astrt.AstError(msg, terminalsrc.UnknownSpan)
        lexeme = self.text[::-1]
        node = self.cst_class(span=astrt.source_span(lexeme))
        node.append(astrt.text_span(lexeme, "[a-z]+", "word", "w"), self.cst_class.Label.W)
        return node


CUSTOM_MODULE = _register("fltk_test_ast_custom_types", Flipped=Flipped)
CUSTOM_WORD = f'rule word {{ custom(python: "{CUSTOM_MODULE}.Flipped"); }}'


SUM_OVER_CUSTOM_GRAMMAR = """
wrap := v:target , ";" ;
target := a:word | b:num ;
word := w:/[a-z]+/ ;
num := n:/[0-9]+/ ;
"""


class TestCustomRules:
    """A ``custom(...)`` rule gets no generated type; the named class does both directions."""

    @staticmethod
    def sidecar(config_text: str) -> Generated:
        return build_roundtrip(SIDECAR_GRAMMAR, "doc", config_text=config_text)

    def test_no_type_is_generated_for_the_rule(self) -> None:
        generated = self.sidecar(CUSTOM_WORD)
        assert not hasattr(generated.ast, "Word")
        assert not hasattr(generated.ast, "word_from_cst")
        assert f"import {CUSTOM_MODULE}" in generated.source

    def test_the_custom_class_converts_the_field(self) -> None:
        generated = self.sidecar(CUSTOM_WORD)
        value = generated.ast.parse(SIDECAR_TEXT)
        assert [entry.key for entry in value.entry] == [Flipped("ahpla"), Flipped("ateb")]

    def test_round_trip_goes_back_through_the_custom_class(self) -> None:
        generated = self.sidecar(CUSTOM_WORD)
        value = generated.ast.parse(SIDECAR_TEXT)
        value.entry[0].key = Flipped("ammag", generated.parser.cst_module.Word)
        assert generated.ast.parse(generated.ast.unparse(value)) == value
        assert "gamma" in generated.ast.unparse(value)

    def test_custom_rule_as_a_direct_sum_payload(self) -> None:
        generated = build_configured(
            "target := a:word | b:num ;\nword := w:/[a-z]+/ ;\nnum := n:/[0-9]+/ ;\n",
            CUSTOM_WORD,
        )
        assert "Flipped | Num" in generated.source
        assert generated.convert("abc", "target") == Flipped("cba")

    def test_a_sum_over_a_custom_payload_serialises_through_the_custom_class(self) -> None:
        """``target_to_cst`` must reach ``value.to_cst()``, not a converter the rule never got."""
        generated = build_roundtrip(SUM_OVER_CUSTOM_GRAMMAR, "wrap", config_text=CUSTOM_WORD)
        value = generated.ast.parse("abc;")
        assert value == generated.ast.Wrap(v=Flipped("cba"))
        rendered = generated.ast.unparse(value)
        # The reversal is what makes the hook visible: the generated converter would emit 'cba'.
        assert "abc" in rendered
        assert generated.ast.parse(rendered) == value

    def test_a_custom_rule_can_be_the_goal_rule(self) -> None:
        parser_result = generate_parser(parse_grammar(SIDECAR_GRAMMAR), capture_trivia=True)
        unparser_result = generate_unparser(parser_result.grammar, parser_result.cst_module_name, None)
        token = f"custom_goal_{id(parser_result)}"
        generated = ast_module_for(
            parser_result,
            _register(f"generated_parser_{token}", Parser=parser_result.parser_class),
            _register(f"generated_unparser_{token}", Unparser=unparser_result.unparser_class),
            "word",
            ac.load_ast_config(CUSTOM_WORD, parser_result.grammar, {ac.Backend.PYTHON}),
        )
        assert generated.ast.parse("abc") == Flipped("cba")
        assert generated.ast.unparse(Flipped("cba", parser_result.cst_module.Word)) == "abc"

    def test_the_unknown_goal_message_lists_custom_rules(self) -> None:
        parser_result = generate_parser(parse_grammar(SIDECAR_GRAMMAR), capture_trivia=False)
        config = ac.load_ast_config(CUSTOM_WORD, parser_result.grammar, {ac.Backend.PYTHON})
        model = am.build_ast_model(parser_result.grammar, config)
        with pytest.raises(ValueError, match="goal rule 'nope' has no AST node") as caught:
            am.resolve_goal_rule(model, "nope")
        assert "word" in str(caught.value)

    def test_the_default_goal_is_the_first_rule_even_when_it_is_custom(self) -> None:
        """Marking a rule custom must not move the goal to whatever comes after it."""
        parser_result = generate_parser(parse_grammar("top := v:num ;\nnum := d:/[0-9]+/ ;\n"), capture_trivia=False)
        config = ac.load_ast_config(
            'rule top { custom(python: "pkg.mod.Top"); }', parser_result.grammar, {ac.Backend.PYTHON}
        )
        model = am.build_ast_model(parser_result.grammar, config)
        assert am.resolve_goal_rule(model, None) == "top"

    def test_a_field_enum_variant_may_be_a_custom_rule(self) -> None:
        """The label mixes a coerced leaf with a generated one; both branches must convert."""
        generated = build_roundtrip(
            "target := a:word , a:num ;\nword := w:/[a-z]+/ ;\nnum := n:/[0-9]+/ ;\n",
            "target",
            config_text=CUSTOM_WORD,
        )
        value = generated.ast.parse("ab 12")
        assert value.a == [Flipped("ba"), generated.ast.Num(text="12")]
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_missing_python_entry_is_a_generation_error(self) -> None:
        parser_result = generate_parser(parse_grammar(SIDECAR_GRAMMAR), capture_trivia=False)
        config = ac.load_ast_config(
            'rule word { custom(rust: "myapp::Word"); }',
            parser_result.grammar,
            {ac.Backend.RUST},
        )
        model = am.build_ast_model(parser_result.grammar, config)
        with pytest.raises(ValueError, match="names no `python:` type"):
            gsm2ast.generate_ast_module(model, parser_result.cst_module_name)

    def test_two_custom_rules_on_one_class_get_payload_classes(self) -> None:
        """A union listing one class twice could not dispatch; both variants fall back."""
        generated = build_configured(
            "target := a:word | b:tag ;\nword := w:/[a-z]+/ ;\ntag := t:/[0-9]+/ ;\n",
            f'rule word {{ custom(python: "{CUSTOM_MODULE}.Flipped"); }}\n'
            f'rule tag {{ custom(python: "{CUSTOM_MODULE}.Flipped"); }}\n',
        )
        assert "Flipped | " not in generated.source
        assert generated.convert("abc", "target") == generated.ast.TargetA(a=Flipped("cba"))
        assert generated.convert("12", "target") == generated.ast.TargetB(b=Flipped("21"))

    def test_undotted_python_path_is_a_sidecar_error(self) -> None:
        """The path shape is checked where the span is, not left to emission."""
        parser_result = generate_parser(parse_grammar(SIDECAR_GRAMMAR), capture_trivia=False)
        with pytest.raises(ac.AstConfigError, match="is not a usable Python path"):
            ac.load_ast_config('rule word { custom(python: "Word"); }', parser_result.grammar, {ac.Backend.PYTHON})

    def test_emission_still_guards_an_undotted_path(self) -> None:
        """A hand-built config skips the validator, so the emitter keeps its own guard."""
        parser_result = generate_parser(parse_grammar(SIDECAR_GRAMMAR), capture_trivia=False)
        config = ac.ResolvedAstConfig(
            rules={"word": ac.ResolvedRule(rule_name="word", custom=ac.CustomRule(entries={"python": "Word"}))}
        )
        model = am.build_ast_model(parser_result.grammar, config)
        with pytest.raises(ValueError, match="must be a dotted path"):
            gsm2ast.generate_ast_module(model, parser_result.cst_module_name)


def coerced(pattern: str, statements: str, *, extra: str = "") -> Generated:
    """A one-field grammar whose single terminal-only rule carries ``statements``."""
    grammar = f"doc := , v:val , ;\nval := t:/{pattern}/ ;\n"
    return build_roundtrip(grammar, "doc", config_text=f"rule val {{ {statements} }}\n{extra}")


def _parse_grouped(text: str) -> int:
    if text.endswith("_"):
        msg = "a digit group separator cannot be last"
        raise ValueError(msg)
    return int(text.replace("_", ""))


SCALAR_MODULE = _register(
    "generated_ast_scalar_custom",
    parse_grouped=_parse_grouped,
    render_grouped=str,
)

GROUPED_INT = (
    'type: custom(py_type: "builtins.int", '
    f'py_parse: "{SCALAR_MODULE}.parse_grouped", py_unparse: "{SCALAR_MODULE}.render_grouped");'
)


class TestScalarCoercion:
    """``type:`` on a terminal-only rule: the node carries a parsed value, both directions."""

    def test_integer(self) -> None:
        generated = coerced("-?[0-9]+", "type: i64;")
        assert generated.ast.parse("-42").v.value == -42

    def test_integer_round_trip(self) -> None:
        generated = coerced("-?[0-9]+", "type: i64;")
        value = generated.ast.parse("7")
        value.v.value = 1234
        assert generated.ast.unparse(value).strip() == "1234"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_integer_out_of_range(self) -> None:
        generated = coerced("[0-9]+", "type: u8;")
        with pytest.raises(astrt.AstError, match="in range for u8"):
            generated.ast.parse("300")

    def test_negative_value_in_an_unsigned_field(self) -> None:
        generated = coerced("-?[0-9]+", "type: u16;")
        with pytest.raises(astrt.AstError, match="in range for u16"):
            generated.ast.parse("-1")

    def test_float(self) -> None:
        generated = coerced(r"[0-9eE.+-]+", "type: f64;")
        assert generated.ast.parse("1.5e2").v.value == 150.0

    def test_float_renders_the_shortest_round_trip_spelling(self) -> None:
        generated = coerced(r"[0-9eE.+-]+", "type: f64;")
        value = generated.ast.parse("1.50")
        assert generated.ast.unparse(value).strip() == "1.5"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_float_gate_rejects_what_only_one_backend_would_accept(self) -> None:
        """Python's ``float`` and Rust's ``f64::from_str`` both take these; the gate does not."""
        generated = coerced(r"[a-zA-Z0-9eE.+-]+", "type: f64;")
        for text in ("inf", "infinity", "NaN", "1e", "1.0f"):
            with pytest.raises(astrt.AstError, match="not a valid f64"):
                generated.ast.parse(text)

    def test_f32_holds_the_value_the_rust_backend_would(self) -> None:
        generated = coerced(r"[0-9eE.+-]+", "type: f32;")
        assert generated.ast.parse("0.1").v.value == 0.10000000149011612

    def test_f32_out_of_range(self) -> None:
        generated = coerced(r"[0-9eE.+-]+", "type: f32;")
        with pytest.raises(astrt.AstError, match="in range for f32"):
            generated.ast.parse("1e39")

    def test_uuid(self) -> None:
        generated = coerced("[0-9a-fA-F-]+", "type: uuid;")
        text = "6BA7B810-9DAD-11D1-80B4-00C04FD430C8"
        assert generated.ast.parse(text).v.value == uuid.UUID(text)

    def test_uuid_renders_lowercase_hyphenated(self) -> None:
        generated = coerced("[0-9a-fA-F-]+", "type: uuid;")
        value = generated.ast.parse("6BA7B810-9DAD-11D1-80B4-00C04FD430C8")
        assert generated.ast.unparse(value).strip() == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_uuid_gate_rejects_the_spellings_python_alone_would_take(self) -> None:
        generated = coerced("[0-9a-zA-Z:{}-]+", "type: uuid;")
        for text in ("{6ba7b810-9dad-11d1-80b4-00c04fd430c8}", "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8"):
            with pytest.raises(astrt.AstError, match="not a canonical"):
                generated.ast.parse(text)

    def test_decimal(self) -> None:
        generated = coerced(r"[0-9.+-]+", "type: decimal;")
        assert generated.ast.parse("1.50").v.value == decimal.Decimal("1.50")

    def test_decimal_renders_in_plain_notation_keeping_its_scale(self) -> None:
        generated = coerced(r"[0-9.+-]+", "type: decimal;")
        value = generated.ast.parse("1.50")
        assert generated.ast.unparse(value).strip() == "1.50"
        value.v.value = decimal.Decimal("0.000001")
        assert generated.ast.unparse(value).strip() == "0.000001"

    def test_the_decimal_gate_rejects_exponent_forms(self) -> None:
        generated = coerced(r"[0-9eE.+-]+", "type: decimal;")
        with pytest.raises(astrt.AstError, match="not a plain decimal"):
            generated.ast.parse("1e3")

    def test_a_decimal_the_rust_backend_could_not_hold_is_refused(self) -> None:
        generated = coerced(r"[0-9.+-]+", "type: decimal;")
        with pytest.raises(astrt.AstError, match="at most 28 fractional digits"):
            generated.ast.parse("1.00000000000000000000000000000001")

    @pytest.mark.parametrize(
        ("text", "held"),
        [
            # 2^96 - 1 fits the mantissa; one more does not.
            ("79228162514264337593543950335", True),
            ("79228162514264337593543950336", False),
            # 28 fractional digits are the most a scale can hold; a 29th is not.
            ("0.0000000000000000000000000001", True),
            ("0.00000000000000000000000000001", False),
            # Trailing zeros count toward both bounds, being part of the scale and the mantissa.
            ("1.0000000000000000000000000000", True),
            ("7922816251426433759354395033.5", True),
        ],
    )
    def test_the_edges_of_the_decimal_domain(self, text: str, held: bool) -> None:  # noqa: FBT001
        generated = coerced(r"[0-9.+-]+", "type: decimal;")
        if held:
            assert generated.ast.parse(text).v.value == decimal.Decimal(text)
        else:
            with pytest.raises(astrt.AstError, match="96 bits of mantissa"):
                generated.ast.parse(text)

    def test_custom_parse_and_unparse(self) -> None:
        generated = coerced("[0-9_]+", GROUPED_INT)
        value = generated.ast.parse("1_000")
        assert value.v.value == 1000
        assert generated.ast.unparse(value).strip() == "1000"

    def test_a_custom_parse_failure_becomes_an_ast_error(self) -> None:
        generated = coerced("[0-9_]+", GROUPED_INT)
        with pytest.raises(astrt.AstError, match="separator cannot be last"):
            generated.ast.parse("1_")

    def test_a_coercion_error_carries_the_terminal_position(self) -> None:
        generated = coerced("[0-9]+", "type: u8;")
        with pytest.raises(astrt.AstError) as caught:
            generated.ast.parse("\n  300")
        assert "line 2, column 3" in str(caught.value)

    def test_a_hand_built_value_serialises(self) -> None:
        generated = coerced("-?[0-9]+", "type: i64;")
        value = generated.ast.Doc(v=generated.ast.Val(value=-8))
        assert generated.ast.unparse(value).strip() == "-8"

    def test_a_value_of_the_wrong_type_is_a_serialise_error(self) -> None:
        generated = coerced("-?[0-9]+", "type: i64;")
        value = generated.ast.Doc(v=generated.ast.Val(value="nine"))
        with pytest.raises(astrt.AstError, match="not an integer"):
            generated.ast.unparse(value)

    def test_a_rendering_the_terminal_rejects_is_a_serialise_error(self) -> None:
        """The canonical rendering still has to be something the grammar could have matched."""
        generated = coerced("[0-9]+", "type: f64;")
        value = generated.ast.Doc(v=generated.ast.Val(value=1.5))
        with pytest.raises(astrt.AstError, match="not something the rule could have matched"):
            generated.ast.unparse(value)

    def test_the_node_keeps_no_text_member(self) -> None:
        generated = coerced("-?[0-9]+", "type: i64;")
        assert not hasattr(generated.ast.parse("1").v, "text")


class TestCanonicalRendering:
    """The renderers guard what the parse half guards, so the round-trip law stays honest."""

    @staticmethod
    def hand_built(pattern: str, statements: str, value: typing.Any) -> tuple[Generated, typing.Any]:
        """A generated module plus a hand-built document holding ``value`` in its coerced field."""
        generated = coerced(pattern, statements)
        return generated, generated.ast.Doc(v=generated.ast.Val(value=value))

    @pytest.mark.parametrize(
        ("statements", "value", "expected"),
        [
            ("type: i64;", True, "not an integer"),
            ("type: i8;", 300, "in range for i8"),
            ("type: u8;", -1, "in range for u8"),
            ("type: f64;", float("inf"), "not a finite float"),
            ("type: f64;", float("nan"), "not a finite float"),
            ("type: f64;", 3, "not a finite float"),
            ("type: f32;", 1e39, "in range for f32"),
            ("type: decimal;", decimal.Decimal("NaN"), "not a finite Decimal"),
            ("type: decimal;", 1.5, "not a finite Decimal"),
            ("type: uuid;", "6ba7b810-9dad-11d1-80b4-00c04fd430c8", "not a UUID"),
        ],
    )
    def test_a_value_the_width_or_the_type_cannot_hold_is_named(
        self, statements: str, value: typing.Any, expected: str
    ) -> None:
        generated, document = self.hand_built(r"[0-9a-fA-F.eE+-]+", statements, value)
        with pytest.raises(astrt.AstError, match=re.escape(expected)):
            generated.ast.unparse(document)

    def test_an_out_of_range_integer_would_otherwise_re_parse_as_an_error(self) -> None:
        """The rendered text matches the terminal, so only the width check catches it."""
        generated, document = self.hand_built("[0-9]+", "type: u8;", 300)
        with pytest.raises(astrt.AstError, match="in range for u8"):
            generated.ast.unparse(document)
        assert generated.ast.parse("7").v.value == 7

    @pytest.mark.parametrize(
        "value",
        [
            decimal.Decimal("1.00000000000000000000000000001"),
            decimal.Decimal("79228162514264337593543950336"),
        ],
    )
    def test_a_decimal_wider_than_the_shared_domain_is_refused_on_the_way_out(self, value: object) -> None:
        """Python's decimal is unbounded, so only the renderer stops a hand-built one here."""
        generated, document = self.hand_built(r"[0-9.+-]+", "type: decimal;", value)
        with pytest.raises(astrt.AstError, match="96 bits of mantissa"):
            generated.ast.unparse(document)

    @pytest.mark.parametrize(("value", "expected"), [("-0", "0"), ("-0.0", "0.0"), ("-0.00", "0.00")])
    def test_a_negative_zero_decimal_renders_unsigned(self, value: str, expected: str) -> None:
        """The sign carries no value; both backends must emit the same unsigned bytes."""
        generated, document = self.hand_built(r"[0-9.+-]+", "type: decimal;", decimal.Decimal(value))
        assert generated.ast.unparse(document).strip() == expected

    def test_a_representable_f32_still_round_trips(self) -> None:
        generated, document = self.hand_built(r"[0-9.eE+-]+", "type: f32;", 0.5)
        assert generated.ast.unparse(document).strip() == "0.5"
        assert generated.ast.parse(generated.ast.unparse(document)) == document

    def test_the_widest_values_of_each_family_render(self) -> None:
        for statements, value in (("type: i8;", -128), ("type: u8;", 255), ("type: i64;", 2**63 - 1)):
            generated, document = self.hand_built("-?[0-9]+", statements, value)
            assert generated.ast.parse(generated.ast.unparse(document)) == document


FLOAT_PATTERN = r"[0-9.eE+-]+"

# What an f32 holds for 0.1 and 3.14, spelled in full: the value the Rust field holds, and the
# value the Python field is kept rounded to.
F32_TENTH = 0.10000000149011612
F32_PI = 3.140000104904175

# A value no float width holds exactly, so its f64 and f32 spellings differ in length: the pair
# is what makes the rounding step of a rendering observable.
A_THIRD = 0.3333333333333333
F32_THIRD = 0.3333333432674408


class TestFloatWidths:
    """``type: f32;`` emulates the 32-bit value: rounded on the way in, short on the way out."""

    @staticmethod
    def generated(statements: str = "type: f32;") -> Generated:
        return coerced(FLOAT_PATTERN, statements)

    def test_a_parsed_f32_renders_the_spelling_it_was_written_as(self) -> None:
        """The value is the 32-bit one, but its canonical text is still ``3.14``."""
        generated = self.generated()
        value = generated.ast.parse("3.14")
        assert value.v.value == F32_PI
        assert generated.ast.unparse(value).strip() == "3.14"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_seventeen_digit_input_renders_short_under_f32(self) -> None:
        generated = self.generated()
        value = generated.ast.parse(repr(F32_TENTH))
        assert generated.ast.unparse(value).strip() == "0.1"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_an_f64_field_keeps_repr_behaviour(self) -> None:
        """Nothing changes for the native width: ``repr`` already is the shortest spelling."""
        generated = self.generated("type: f64;")
        for text in ("0.1", repr(F32_TENTH), "1e+20"):
            value = generated.ast.parse(text)
            assert generated.ast.unparse(value).strip() == repr(float(text))
            assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_f32_is_rounded_at_construction(self) -> None:
        """The field holds what ``Ratio { value: 3.14f32 }`` holds, so the law needs no round trip."""
        generated = self.generated()
        node = generated.ast.Val(value=3.14)
        assert node.value == F32_PI
        document = generated.ast.Doc(v=node)
        assert generated.ast.unparse(document).strip() == "3.14"
        assert generated.ast.parse(generated.ast.unparse(document)) == document

    def test_a_magnitude_the_width_cannot_hold_survives_construction_to_be_named(self) -> None:
        """Rounding an overflow to infinity would hide the value the diagnostic has to name."""
        generated = self.generated()
        document = generated.ast.Doc(v=generated.ast.Val(value=1e39))
        assert document.v.value == 1e39
        with pytest.raises(astrt.AstError, match="in range for f32"):
            generated.ast.unparse(document)

    def test_an_erased_f32_field_is_rounded_on_its_owner(self) -> None:
        """``transparent;`` puts the float on the parent, which is where the rounding goes."""
        generated = self.generated("type: f32; transparent;")
        document = generated.ast.Doc(v=0.1)
        assert document.v == F32_TENTH
        assert generated.ast.unparse(document).strip() == "0.1"
        assert generated.ast.parse(generated.ast.unparse(document)) == document

    def test_the_elements_of_a_collection_are_rounded_too(self) -> None:
        grammar = f'doc := , v:val , ( "," , v:val )* , ;\nval := t:/{FLOAT_PATTERN}/ ;\n'
        generated = build_roundtrip(grammar, "doc", config_text="rule val { type: f32; transparent; }")
        document = generated.ast.Doc(v=[0.1, 0.5])
        assert document.v == [F32_TENTH, 0.5]
        assert generated.ast.unparse(document).replace(" ", "") == "0.1,0.5"
        assert generated.ast.parse(generated.ast.unparse(document)) == document

    def test_a_value_of_the_wrong_type_reaches_the_renderer_unchanged(self) -> None:
        generated = self.generated()
        document = generated.ast.Doc(v=generated.ast.Val(value="0.1"))
        with pytest.raises(astrt.AstError, match="not a finite float"):
            generated.ast.unparse(document)

    def test_a_field_mutated_past_construction_is_rounded_by_the_renderer(self) -> None:
        """Assigning to the field runs no ``__post_init__``, so the rounding falls to render time.

        A seventeen-digit f64 is what the width cannot hold: rendering it without rounding first
        spells every digit, which is the readability the short spelling exists to protect.
        """
        generated = self.generated()
        document = generated.ast.Doc(v=generated.ast.Val(value=0.5))
        document.v.value = A_THIRD
        assert document.v.value == A_THIRD
        assert generated.ast.unparse(document).strip() == "0.33333334"

    def test_a_mutated_field_compares_unequal_until_it_has_been_through_one_round_trip(self) -> None:
        """The documented consequence of the escape path: the field holds what no f32 holds."""
        generated = self.generated()
        document = generated.ast.Doc(v=generated.ast.Val(value=0.5))
        document.v.value = A_THIRD
        once = generated.ast.parse(generated.ast.unparse(document))
        assert once != document
        assert once.v.value == F32_THIRD
        assert generated.ast.parse(generated.ast.unparse(once)) == once

    def test_a_float_reached_only_through_a_union_is_rounded_by_the_renderer(self) -> None:
        """The union arm has no owning dataclass, so nothing rounds it at construction."""
        grammar = f"doc := , ( v:val | v:word ) , ;\nval := t:/{FLOAT_PATTERN}/ ;\nword := w:/[a-z]+/ ;\n"
        generated = build_roundtrip(
            grammar, "doc", config_text="rule val { type: f32; transparent; }\nrule word { transparent; }\n"
        )
        document = generated.ast.Doc(v=A_THIRD)
        assert document.v == A_THIRD
        assert generated.ast.unparse(document).strip() == "0.33333334"

    def test_a_fold_operator_of_a_narrow_width_is_rounded_at_construction(self) -> None:
        """A fold link owns its operator member, so that one *is* reached by ``__post_init__``."""
        grammar = f"sum := t:word , ( , op:val , t:word)* ;\nword := w:/[a-z]+/ ;\nval := d:/{FLOAT_PATTERN}/ ;\n"
        generated = build_roundtrip(
            grammar, "sum", config_text="rule sum { fold_left: op; }\nrule val { type: f32; transparent; }\n"
        )
        word = generated.ast.Word(text="a")
        link = generated.ast.SumBinary(op=0.1, lhs=word, rhs=word)
        assert link.op == F32_TENTH


# The two canonical float tables, spelled once. `crates/fltk-ast-core/src/scalar.rs` asserts
# the same value/text pairs against its own renderers: byte-identical unparse across the two
# backends is what makes an AST portable, and two independently written expectation tables
# would let a threshold row drift apart unnoticed.
F64_RENDERINGS = [
    (0.0, "0.0"),
    (-0.0, "-0.0"),
    (1.0, "1.0"),
    (3.14, "3.14"),
    (0.1, "0.1"),
    (-2.75, "-2.75"),
    (123456.789, "123456.789"),
    (1e15, "1000000000000000.0"),
    (1e16, "1e+16"),
    (1e17, "1e+17"),
    (1e22, "1e+22"),
    (1e-4, "0.0001"),
    (1e-5, "1e-05"),
    (1.5e300, "1.5e+300"),
    (2.5e-300, "2.5e-300"),
    (5e-324, "5e-324"),
    (1.7976931348623157e308, "1.7976931348623157e+308"),
]

F32_RENDERINGS = [
    (0.0, "0.0"),
    (1.0, "1.0"),
    (3.14, "3.14"),
    (0.1, "0.1"),
    (1e15, "1000000000000000.0"),
    (1e16, "1e+16"),
    (1e-5, "1e-05"),
    (123456.789, "123456.79"),
    (16777216.0, "16777216.0"),
    (3.4028235e38, "3.4028235e+38"),
    (1.1754944e-38, "1.1754944e-38"),
]


class TestCanonicalFloatText:
    """The renderings both backends have to agree on, row for row."""

    @pytest.mark.parametrize(("value", "expected"), F64_RENDERINGS)
    def test_f64_is_cpython_repr(self, value: float, expected: str) -> None:
        assert astrt.render_float(value, 64, "r", terminalsrc.UnknownSpan) == expected

    @pytest.mark.parametrize(("value", "expected"), F32_RENDERINGS)
    def test_f32_is_the_shortest_spelling_at_thirty_two_bits(self, value: float, expected: str) -> None:
        held = astrt.narrowed(value, 32)
        assert astrt.render_float(held, 32, "r", terminalsrc.UnknownSpan) == expected


class TestTextFrom:
    """``text_from:`` reads and writes one child's span instead of the node's own."""

    QUOTED = 'doc := , v:quoted , ;\nquoted := "\\"" . content:/[^"]*/ . "\\"" ;\n'
    NUMERIC = 'doc := , v:quoted , ;\nquoted := "\\"" . content:/[0-9]+/ . "\\"" ;\n'

    def test_the_quotes_are_stripped(self) -> None:
        generated = build_roundtrip(self.QUOTED, "doc", config_text="rule quoted { text_from: content; }")
        assert generated.ast.parse('"hello"').v.text == "hello"

    def test_the_quotes_come_back_from_the_grammar(self) -> None:
        generated = build_roundtrip(self.QUOTED, "doc", config_text="rule quoted { text_from: content; }")
        value = generated.ast.parse('"hello"')
        value.v.text = "world"
        assert generated.ast.unparse(value).strip() == '"world"'
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_value_serialises(self) -> None:
        generated = build_roundtrip(self.QUOTED, "doc", config_text="rule quoted { text_from: content; }")
        value = generated.ast.Doc(v=generated.ast.Quoted(text="hi"))
        assert generated.ast.unparse(value).strip() == '"hi"'

    def test_text_the_terminal_could_not_match_is_a_serialise_error(self) -> None:
        generated = build_roundtrip(self.QUOTED, "doc", config_text="rule quoted { text_from: content; }")
        value = generated.ast.Doc(v=generated.ast.Quoted(text='say "hi"'))
        with pytest.raises(astrt.AstError, match="not something the rule could have matched"):
            generated.ast.unparse(value)

    def test_a_coercion_applies_to_the_redirected_text(self) -> None:
        generated = build_roundtrip(self.NUMERIC, "doc", config_text="rule quoted { text_from: content; type: i64; }")
        value = generated.ast.parse('"12"')
        assert value.v.value == 12
        value.v.value = 34
        assert generated.ast.unparse(value).strip() == '"34"'

    def test_the_whitespace_separator_a_redirect_fixes(self) -> None:
        """The rule is refused without the redirect, so this pins the fix, not just the shape."""
        grammar = 'doc := , v:spaced , ;\nspaced := "(" , content:/[a-z]+/ , ")" ;\n'
        generated = build_roundtrip(grammar, "doc", config_text="rule spaced { text_from: content; }")
        value = generated.ast.parse("(  abc  )")
        assert value.v.text == "abc"
        assert generated.ast.parse(generated.ast.unparse(value)) == value


@pytest.fixture(scope="module")
def plain() -> Generated:
    return build_roundtrip(CONFIG_GRAMMAR, "config", config_text=CONFIG_SIDECAR)


class TestTransparentConfigLanguage:
    """The serde-competitive shape: one sidecar turns every leaf node into a plain value."""

    def test_fields_carry_bare_python_values(self, plain: Generated) -> None:
        server = plain.ast.parse(CONFIG_TEXT).stanzas[0]
        assert server.name == "web"
        assert {setting.key: setting.value for setting in server.settings} == {
            "host": "localhost",
            "port": 8080,
            "debug": True,
            "tags": plain.ast.List(value=[1, 2]),
        }

    def test_an_enum_shaped_field_is_the_value_enum_itself(self, plain: Generated) -> None:
        metric = plain.ast.parse(CONFIG_TEXT).stanzas[1]
        assert metric.metric_kind is plain.ast.MetricTypeValue.COUNTER
        assert metric.interval == 30

    def test_the_sum_union_lists_the_erased_payloads(self, plain: Generated) -> None:
        assert 'Value: typing.TypeAlias = "str | int | bool | List"' in plain.source

    def test_a_boolean_payload_is_tested_before_an_integer_one(self, plain: Generated) -> None:
        """``bool`` is an ``int`` subclass, so grammar order would render ``True`` as a number."""
        node = plain.ast.value_to_cst(True)
        assert [label.name for label, _child in node.children] == ["FLAG"]

    def test_the_whole_document_round_trips(self, plain: Generated) -> None:
        value = plain.ast.parse(CONFIG_TEXT)
        assert plain.ast.parse(plain.ast.unparse(value)) == value

    def test_a_hand_built_document_round_trips(self, plain: Generated) -> None:
        ast = plain.ast
        value = ast.Config(
            stanzas=[
                ast.ServerDef(name="db", settings=[ast.Setting(key="port", value=5432)]),
                ast.MetricDef(name="hits", metric_kind=ast.MetricTypeValue.GAUGE, interval=None),
            ]
        )
        rendered = ast.unparse(value)
        assert "5432" in rendered
        assert ast.parse(rendered) == value

    def test_a_mutated_scalar_round_trips(self, plain: Generated) -> None:
        value = plain.ast.parse(CONFIG_TEXT)
        value.stanzas[0].settings[0].value = "elsewhere"
        rendered = plain.ast.unparse(value)
        assert '"elsewhere"' in rendered
        assert plain.ast.parse(rendered) == value

    def test_no_type_or_module_converter_survives_for_an_erased_rule(self, plain: Generated) -> None:
        for name in ("Identifier", "Number", "StringLiteral", "Boolean", "MetricType"):
            assert not hasattr(plain.ast, name)
        for name in ("identifier_from_cst", "number_to_cst", "boolean_from_cst"):
            assert not hasattr(plain.ast, name)

    def test_the_value_enum_of_an_erased_rule_is_still_public(self, plain: Generated) -> None:
        """It *is* the payload, so it is the one type the erased rule still contributes."""
        assert [member.name for member in plain.ast.MetricTypeValue] == ["COUNTER", "GAUGE", "HISTOGRAM"]


WRAPPER_GRAMMAR = """
doc  := , w:wrap , ;
wrap := "(" , only:word , ")" ;
word := c:/[a-z]+/ ;
"""

CHOICE_WRAPPER_GRAMMAR = """
doc  := , w:wrap , ;
wrap := "(" , only:word , ")" | "[" , only:word , "]" ;
word := c:/[a-z]+/ ;
"""


class TestTransparentWrapper:
    """A single-field product erases to its one field; the wrapper never appears."""

    def test_the_field_holds_the_inner_node(self) -> None:
        generated = build_roundtrip(WRAPPER_GRAMMAR, "doc", config_text="rule wrap { transparent; }")
        value = generated.ast.parse("( abc )")
        assert value.w == generated.ast.Word(text="abc")
        assert not hasattr(generated.ast, "Wrap")

    def test_the_wrapper_comes_back_from_the_grammar(self) -> None:
        generated = build_roundtrip(WRAPPER_GRAMMAR, "doc", config_text="rule wrap { transparent; }")
        value = generated.ast.Doc(w=generated.ast.Word(text="xyz"))
        assert generated.ast.unparse(value).strip() == "(xyz)"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_transitive_erasure_reaches_the_scalar(self) -> None:
        generated = build_roundtrip(
            WRAPPER_GRAMMAR, "doc", config_text="rule wrap { transparent; }\nrule word { transparent; }"
        )
        value = generated.ast.parse("( abc )")
        assert value.w == "abc"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_merged_wrapper_picks_an_alternative_by_trial(self) -> None:
        """Two alternatives differing only in suppressed literals: the first fitting one renders."""
        generated = build_roundtrip(CHOICE_WRAPPER_GRAMMAR, "doc", config_text="rule wrap { transparent; }")
        assert generated.ast.parse("[ abc ]").w == generated.ast.Word(text="abc")
        value = generated.ast.Doc(w=generated.ast.Word(text="abc"))
        assert generated.ast.unparse(value).strip() == "(abc)"

    def test_the_erased_rule_can_be_the_goal(self) -> None:
        generated = build_roundtrip(WRAPPER_GRAMMAR, "wrap", config_text="rule wrap { transparent; }")
        assert generated.ast.parse("( abc )") == generated.ast.Word(text="abc")
        assert generated.ast.unparse(generated.ast.Word(text="abc")).strip() == "(abc)"


SUM_OF_WRAPPERS_GRAMMAR = """
top   := v:pick , ";" ;
pick  := p:paren | q:tag ;
paren := "(" , c:choice , ")" ;
choice := a:word | b:num ;
tag   := "#" . t:word ;
word  := c:/[a-z]+/ ;
num   := d:/[0-9]+/ ;
"""


class TestTransparentSumPayload:
    """An erased rule whose payload is itself a union expands to the classes behind it."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(SUM_OF_WRAPPERS_GRAMMAR, "top", config_text="rule paren { transparent; }")

    def test_the_guard_names_every_class_the_payload_can_be(self) -> None:
        assert "isinstance(value, (Word, Num))" in self.generated().source

    @pytest.mark.parametrize("text", ["(ab);", "(12);", "#ab;"])
    def test_every_variant_round_trips(self, text: str) -> None:
        generated = self.generated()
        value = generated.ast.parse(text)
        assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestTransparentFieldEnumMember:
    """A label mixing an erased rule with a generated one converts through both branches."""

    def test_both_members_convert_and_round_trip(self) -> None:
        generated = build_roundtrip(
            "target := a:word , a:num ;\nword := w:/[a-z]+/ ;\nnum := n:/[0-9]+/ ;\n",
            "target",
            config_text="rule word { transparent; }",
        )
        value = generated.ast.parse("ab 12")
        assert value.a == ["ab", generated.ast.Num(text="12")]
        assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestBoolMapping:
    """``bool:`` on a two-alternative enum-shaped rule: the value is a plain boolean."""

    GRAMMAR = 'doc := , v:flag , ;\nflag := yes:"yes" | no:"no" ;\n'
    CONFIG = "rule flag { bool: yes; }"

    def test_both_alternatives_map(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "doc", config_text=self.CONFIG)
        assert generated.ast.parse("yes").v.value is True
        assert generated.ast.parse("no").v.value is False

    def test_no_value_enum_is_emitted(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "doc", config_text=self.CONFIG)
        assert not hasattr(generated.ast, "FlagValue")

    def test_round_trip(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "doc", config_text=self.CONFIG)
        value = generated.ast.parse("yes")
        assert generated.ast.unparse(value).strip() == "yes"
        value.v.value = False
        assert generated.ast.unparse(value).strip() == "no"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_non_boolean_value_is_a_serialise_error(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "doc", config_text=self.CONFIG)
        value = generated.ast.Doc(v=generated.ast.Flag(value="yes"))
        with pytest.raises(astrt.AstError, match="not a boolean"):
            generated.ast.unparse(value)

    def test_equality_is_by_value(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "doc", config_text=self.CONFIG)
        assert generated.ast.parse("yes") == generated.ast.parse("  yes  ")
        assert generated.ast.parse("yes") != generated.ast.parse("no")


class TestEquivalentLiteralSpellings:
    """Alternatives sharing a label are one variant, canonicalised to the first spelling."""

    GRAMMAR = 'doc := , c:colour , ;\ncolour := red:"red" | blue:"blue" | gray:"gray" | gray:"grey" ;\n'

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(TestEquivalentLiteralSpellings.GRAMMAR, "doc")

    def test_both_spellings_convert_to_the_merged_variant(self) -> None:
        """Dispatch is by child label; the text is never read, so neither spelling is special."""
        generated = self.generated()
        assert generated.ast.parse("gray").c.value is generated.ast.ColourValue.GRAY
        assert generated.ast.parse("grey").c.value is generated.ast.ColourValue.GRAY
        assert generated.ast.parse("blue").c.value is generated.ast.ColourValue.BLUE

    def test_the_two_spellings_compare_equal(self) -> None:
        generated = self.generated()
        assert generated.ast.parse("grey") == generated.ast.parse("gray")
        assert generated.ast.parse("grey") != generated.ast.parse("blue")

    def test_unparse_canonicalises_to_the_first_spelling(self) -> None:
        """This is the keyword-evolution mechanism: accept both, format to the first."""
        generated = self.generated()
        value = generated.ast.parse("grey")
        assert generated.ast.unparse(value).strip() == "gray"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_value_renders_the_canonical_spelling(self) -> None:
        generated = self.generated()
        value = generated.ast.Doc(c=generated.ast.Colour(value=generated.ast.ColourValue.GRAY))
        assert generated.ast.unparse(value).strip() == "gray"


LITERAL_ONLY_GRAMMAR = """
doc    := , m:marker , f:flag , ;
marker := "begin" , "end" ;
flag   := on:"on" . off:"off" ;
"""


class TestLiteralOnlyRules:
    """A rule of literals alone carries no text: a marker product, or one of bare positions."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(LITERAL_ONLY_GRAMMAR, "doc")

    def test_the_label_free_rule_carries_only_a_span(self) -> None:
        generated = self.generated()
        value = generated.ast.parse("begin end onoff")
        assert value.m == generated.ast.Marker()
        assert not hasattr(value.m, "text")
        assert value.m.span.text() == "begin end"

    def test_the_labeled_rule_carries_the_literals_positions(self) -> None:
        generated = self.generated()
        flag = generated.ast.parse("begin end onoff").f
        assert flag.on.text() == "on"
        assert flag.off.text() == "off"

    def test_positions_stay_out_of_equality(self) -> None:
        """A literal's text is a grammar constant, so only its position is recorded."""
        generated = self.generated()
        assert generated.ast.parse("begin end onoff") == generated.ast.parse("  begin  end  onoff")

    def test_round_trip_from_a_parse(self) -> None:
        generated = self.generated()
        value = generated.ast.parse("begin end onoff")
        assert generated.ast.unparse(value).replace(" ", "") == "beginendonoff"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_round_trip_from_a_hand_built_value(self) -> None:
        """Both nodes' contents come back from the grammar, so neither needs a span."""
        generated = self.generated()
        value = generated.ast.Doc(
            m=generated.ast.Marker(),
            f=generated.ast.Flag(on=terminalsrc.UnknownSpan, off=terminalsrc.UnknownSpan),
        )
        assert generated.ast.parse(generated.ast.unparse(value)) == value


KEYED_GRAMMAR = """
top   := , entry* , ;
entry := name:word , "=" , v:num , ";" , ;
word  := w:/[a-z]+/ ;
num   := d:/[0-9]+/ ;
"""

KEYED_CONFIG = "rule word { transparent; }\nrule num { type: i64; transparent; }\nrule entry { key: name; }\n"


@pytest.fixture(scope="module")
def keyed() -> Generated:
    return build_roundtrip(CONFIG_GRAMMAR, "config", config_text=KEYED_SIDECAR)


class TestKeyedCollections:
    """``key:`` on an element rule: its collection use sites are insertion-ordered maps."""

    def test_the_collection_is_a_map_keyed_by_the_field(self, keyed: Generated) -> None:
        server = keyed.ast.parse(CONFIG_TEXT).stanzas[0]
        assert list(server.settings) == ["host", "port", "debug", "tags"]
        assert server.settings["port"].value == 8080

    def test_the_annotation_names_the_key_type(self, keyed: Generated) -> None:
        assert "settings: dict[str, Setting]" in keyed.source

    def test_the_key_stays_a_field_of_the_element(self, keyed: Generated) -> None:
        server = keyed.ast.parse(CONFIG_TEXT).stanzas[0]
        assert server.settings["host"].key == "host"

    def test_an_empty_collection_is_an_empty_map(self, keyed: Generated) -> None:
        value = keyed.ast.parse("server web { }")
        assert value.stanzas[0].settings == {}
        assert keyed.ast.parse(keyed.ast.unparse(value)) == value

    def test_the_document_round_trips(self, keyed: Generated) -> None:
        value = keyed.ast.parse(CONFIG_TEXT)
        assert keyed.ast.parse(keyed.ast.unparse(value)) == value

    def test_a_mutated_map_round_trips(self, keyed: Generated) -> None:
        value = keyed.ast.parse(CONFIG_TEXT)
        del value.stanzas[0].settings["debug"]
        value.stanzas[0].settings["retries"] = keyed.ast.Setting(key="retries", value=3)
        rendered = keyed.ast.unparse(value)
        assert "retries=3" in rendered.replace(" ", "")
        assert "debug" not in rendered
        assert keyed.ast.parse(rendered) == value

    def test_a_hand_built_map_round_trips(self, keyed: Generated) -> None:
        ast = keyed.ast
        value = ast.Config(stanzas=[ast.ServerDef(name="db", settings={"port": ast.Setting(key="port", value=5432)})])
        assert ast.parse(ast.unparse(value)) == value

    def test_the_element_field_is_authoritative_not_the_map_key(self) -> None:
        """They can only disagree after hand mutation; the field is what renders."""
        generated = build_roundtrip(KEYED_GRAMMAR, "top", config_text=KEYED_CONFIG)
        value = generated.ast.Top(entry={"stale": generated.ast.Entry(name="fresh", v=1)})
        assert generated.ast.unparse(value).replace(" ", "").strip() == "fresh=1;"

    def test_a_duplicate_key_names_both_locations(self) -> None:
        generated = build_roundtrip(KEYED_GRAMMAR, "top", config_text=KEYED_CONFIG)
        with pytest.raises(astrt.AstError) as exc:
            generated.ast.parse("a = 1; a = 2;")
        assert exc.value.message == "duplicate entry key 'a'"
        assert exc.value.span.start == len("a = 1; ")
        ((message, related),) = exc.value.related
        assert message == "previously defined here"
        assert related.start == 0

    def test_an_integer_key(self) -> None:
        generated = build_roundtrip(
            'top := , entry* , ;\nentry := code:num , "=" , v:word , ";" , ;\n'
            "word := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n",
            "top",
            config_text="rule word { transparent; }\nrule num { type: i64; transparent; }\nrule entry { key: code; }\n",
        )
        value = generated.ast.parse("7 = seven; 8 = eight;")
        assert list(value.entry) == [7, 8]
        assert "entry: dict[int, Entry]" in generated.source
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_map_takes_part_in_equality(self) -> None:
        generated = build_roundtrip(KEYED_GRAMMAR, "top", config_text=KEYED_CONFIG)
        assert generated.ast.parse("a = 1;") == generated.ast.parse("  a = 1;  ")
        assert generated.ast.parse("a = 1;") != generated.ast.parse("a = 2;")


# A product, a sum with both a generated payload class and direct payloads, an enum-shaped
# rule and a terminal-only rule — every node form that carries a back-pointer.
BACKPOINTER_GRAMMAR = """
top   := , v:value , ";" , ;
value := a:word , b:word | flag:flag | one:word ;
flag  := yes:"yes" | no:"no" ;
word  := w:/[a-z]+/ ;
"""


class TestCstBackpointers:
    """``option cst = true;`` gives every node class the CST node it was converted from."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(BACKPOINTER_GRAMMAR, "top", config_text="option cst = true;")

    def test_every_node_form_carries_its_own_node(self) -> None:
        value = self.generated().ast.parse("ab cd;")
        assert type(value.cst).__name__ == "Top"
        assert type(value.v).__name__ == "ValueAlt1"
        # A sum is a union, so the payload class carries the sum rule's own CST node.
        assert type(value.v.cst).__name__ == "Value"
        assert type(value.v.a.cst).__name__ == "Word"

    def test_an_enum_shaped_node_carries_one_too(self) -> None:
        value = self.generated().ast.parse("yes;")
        assert type(value.v.cst).__name__ == "Flag"

    def test_the_back_pointer_carries_the_source_text(self) -> None:
        value = self.generated().ast.parse("ab cd;")
        assert value.v.a.cst.span.text() == "ab"

    def test_it_is_absent_on_a_hand_built_value(self) -> None:
        assert self.generated().ast.Word(text="ab").cst is None

    def test_it_stays_out_of_equality_and_repr(self) -> None:
        ast = self.generated().ast
        parsed = ast.parse("ab;")
        assert parsed.v == ast.Word(text="ab")
        assert "cst=" not in repr(parsed)

    def test_the_reverse_direction_ignores_a_stale_back_pointer(self) -> None:
        """The AST fields are authoritative: a mutated value renders as mutated."""
        generated = self.generated()
        value = generated.ast.parse("ab;")
        value.v.text = "zz"
        assert value.v.cst is not None
        assert generated.ast.unparse(value).strip() == "zz;"

    def test_no_back_pointer_without_the_option(self) -> None:
        assert not hasattr(build_roundtrip(BACKPOINTER_GRAMMAR, "top").ast.Word(text="ab"), "cst")

    def test_a_synthesised_fold_link_has_none_while_its_operands_do_not(self) -> None:
        """The link is not a node of the CST, so there is nothing for it to point at."""
        generated = build_roundtrip(SUM_GRAMMAR, "sum", config_text="option cst = true;\nrule sum { fold_left: op; }\n")
        value = generated.ast.parse("a + b")
        assert value.cst is None
        assert value.lhs.cst is not None
        assert value.rhs.cst is not None
        assert value.op.cst is not None

    def test_a_flattened_wrapper_leaves_its_parents_pointer_alone(self) -> None:
        """The wrapper emits no class, so the only back-pointer is the parent's own CST node."""
        generated = build_roundtrip(TASK_GRAMMAR, "task_def", SPACED_FORMAT, "option cst = true;\n" + TASK_SIDECAR)
        value = generated.ast.parse("task t every 5m { a = 1; }")
        assert value.cst is not None
        assert value.cst.span.text() == "task t every 5m { a = 1; }"
        assert value.settings[0].cst is not None


# Each repetition carries a leading separator, which is what lets a second operator follow
# whitespace.
# One fold rule on its own, with a span-bearing operand and operator.
SUM_GRAMMAR = """
sum  := word , ( , op:sign , word)* ;
sign := plus:"+" | minus:"-" ;
word := w:/[a-z]+/ ;
"""


@pytest.fixture(scope="module")
def folded() -> Generated:
    return build_roundtrip(FOLD_GRAMMAR, "expr", config_text=FOLD_SIDECAR)


class TestFoldLeft:
    """``fold_left:`` on the shared expression grammar, in both directions."""

    def test_a_single_operand_is_the_operand_itself(self, folded: Generated) -> None:
        assert folded.ast.parse("42") == 42

    def test_the_chain_nests_to_the_left(self, folded: Generated) -> None:
        value = folded.ast.parse("1 - 2 - 3")
        assert value.op is folded.ast.AddOpValue.MINUS
        assert value.rhs == 3
        assert (value.lhs.op, value.lhs.lhs, value.lhs.rhs) == (folded.ast.AddOpValue.MINUS, 1, 2)

    def test_precedence_levels_nest_as_separate_chains(self, folded: Generated) -> None:
        value = folded.ast.parse("1 + 2 * 3")
        assert value.lhs == 1
        assert type(value.rhs).__name__ == "TermBinary"
        assert (value.rhs.lhs, value.rhs.rhs) == (2, 3)

    def test_a_synthesised_link_carries_the_merged_span(self, folded: Generated) -> None:
        value = folded.ast.parse("1 + 2 * 3")
        assert value.span.text() == "1 + 2 * 3"
        assert value.rhs.span.text() == "2 * 3"

    def test_the_link_class_is_a_union_member(self, folded: Generated) -> None:
        assert 'Expr: typing.TypeAlias = "Term | ExprBinary"' in folded.source
        assert 'Term: typing.TypeAlias = "Factor | TermBinary"' in folded.source

    def test_spans_stay_out_of_equality(self, folded: Generated) -> None:
        assert folded.ast.parse("1 + 2") == folded.ast.parse("1+2")
        assert folded.ast.parse("1 + 2") != folded.ast.parse("1 - 2")

    @pytest.mark.parametrize("text", ["7", "1 + 2", "1 + 2 * 3 - 4", "(1 + 2) * 3", "((4))"])
    def test_the_round_trip_law_holds(self, folded: Generated, text: str) -> None:
        value = folded.ast.parse(text)
        assert folded.ast.parse(folded.ast.unparse(value)) == value

    def test_a_mutated_chain_round_trips(self, folded: Generated) -> None:
        value = folded.ast.parse("1 + 2")
        value.op = folded.ast.AddOpValue.MINUS
        value.rhs = 9
        assert folded.ast.unparse(value).replace(" ", "") == "1-9"
        assert folded.ast.parse(folded.ast.unparse(value)) == value

    def test_a_hand_built_chain_round_trips(self, folded: Generated) -> None:
        ast = folded.ast
        value = ast.ExprBinary(ast.AddOpValue.PLUS, ast.TermBinary(ast.MulOpValue.TIMES, 2, 3), 4)
        assert ast.unparse(value).replace(" ", "") == "2*3+4"
        assert ast.parse(ast.unparse(value)) == value

    def test_a_link_converts_itself(self, folded: Generated) -> None:
        """``to_cst`` on the link class is the same node the module-level converter builds."""
        value = folded.ast.parse("1 + 2")
        assert [label for label, _ in value.to_cst().children] == [
            label for label, _ in folded.ast.expr_to_cst(value).children
        ]

    def test_a_deeper_chain_on_the_right_is_not_representable(self, folded: Generated) -> None:
        ast = folded.ast
        against = ast.ExprBinary(ast.AddOpValue.PLUS, 1, ast.ExprBinary(ast.AddOpValue.PLUS, 2, 3))
        with pytest.raises(astrt.AstError) as exc:
            ast.unparse(against)
        assert "this fold nests the other way" in exc.value.message
        assert "the right operand" in exc.value.message


class TestFoldRight:
    """``fold_right:`` mirrors the nesting and the refusal."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(SUM_GRAMMAR, "sum", config_text="rule sum { fold_right: op; }\n")

    def test_the_chain_nests_to_the_right(self) -> None:
        value = self.generated().ast.parse("a - b - c")
        assert value.lhs.text == "a"
        assert value.rhs.lhs.text == "b"
        assert value.rhs.rhs.text == "c"

    def test_the_merged_span_covers_the_sub_chain(self) -> None:
        value = self.generated().ast.parse("a - b - c")
        assert value.span.text() == "a - b - c"
        assert value.rhs.span.text() == "b - c"

    def test_the_round_trip_law_holds(self) -> None:
        generated = self.generated()
        for text in ("a", "a + b", "a + b - c"):
            value = generated.ast.parse(text)
            assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_operator_keeps_its_own_span_bearing_node(self) -> None:
        ast = self.generated().ast
        value = ast.parse("a + b")
        assert value.op.value is ast.SignValue.PLUS
        assert value.op.span.text() == "+"

    def test_a_deeper_chain_on_the_left_is_not_representable(self) -> None:
        generated = self.generated()
        ast = generated.ast
        leaf = ast.Word(text="a")
        against = ast.SumBinary(
            ast.Sign(ast.SignValue.PLUS), ast.SumBinary(ast.Sign(ast.SignValue.PLUS), leaf, leaf), leaf
        )
        with pytest.raises(astrt.AstError) as exc:
            ast.unparse(against)
        assert "the left operand" in exc.value.message


class TestFoldErrors:
    """The arity contract a hand-built or mutated CST can break, in either direction."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(SUM_GRAMMAR, "sum", config_text="rule sum { fold_left: op; }\n")

    def test_a_missing_operator_is_reported(self) -> None:
        generated = self.generated()
        node = generated.parser.cst_module.Sum()
        for text in ("a", "b"):
            node.append(generated.ast.word_to_cst(generated.ast.Word(text=text)), node.Label.WORD)
        with pytest.raises(astrt.AstError) as exc:
            generated.ast.sum_from_cst(node)
        assert "a fold over 2 operand(s) needs 1 operator(s), but the node has 0" in exc.value.message

    def test_a_literal_operator_carries_position_only(self) -> None:
        """Its text is a grammar constant, so the member is a span and stays out of equality."""
        generated = build_roundtrip(
            'sum := word , ( , op:"+" , word)* ;\nword := w:/[a-z]+/ ;\n',
            "sum",
            config_text="rule sum { fold_left: op; }\nrule word { transparent; }\n",
        )
        value = generated.ast.parse("a + b")
        assert (value.lhs, value.rhs) == ("a", "b")
        assert value.op.text() == "+"
        assert value == generated.ast.SumBinary(terminalsrc.UnknownSpan, "a", "b")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_runtime_fold_refuses_a_run_the_interleaving_does_not_fit(self) -> None:
        """The helpers are self-validating, so a caller of the runtime gets the same diagnostic.

        Nothing is dropped to make the two runs meet: a chain missing an operand — or an
        operator — is not the value the caller handed over.
        """
        spans = [terminalsrc.Span.with_source(0, 1, "a"), terminalsrc.Span.with_source(1, 2, "b")]

        def link(*_arguments: object) -> object:
            message = "the arity check runs before any link is built"
            raise AssertionError(message)

        for fold in (astrt.fold_left, astrt.fold_right):
            with pytest.raises(astrt.AstError) as exc:
                fold(link, [1, 2], spans, ["+", "-"], "sum")
            assert "a fold over 2 operand(s) needs 1 operator(s), but the node has 2" in exc.value.message
            with pytest.raises(astrt.AstError) as exc:
                fold(link, [1, 2], spans, [], "sum")
            assert "a fold over 2 operand(s) needs 1 operator(s), but the node has 0" in exc.value.message
            with pytest.raises(astrt.AstError) as exc:
                fold(link, [], [], ["+"], "sum")
            assert "a fold needs at least one operand" in exc.value.message

    def test_an_operandless_node_is_reported(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError) as exc:
            generated.ast.sum_from_cst(generated.parser.cst_module.Sum())
        assert "a fold needs at least one operand" in exc.value.message

    def test_operands_from_two_sources_cannot_merge_their_spans(self) -> None:
        """Each synthesised ``Word`` span carries its own single-token source, so a chain built
        out of them mixes sources the way only a hand-built CST can."""
        generated = self.generated()
        cst = generated.parser.cst_module
        node = cst.Sum()
        node.append(generated.ast.word_to_cst(generated.ast.Word(text="a")), node.Label.WORD)
        node.append(generated.ast.sign_to_cst(generated.ast.Sign(generated.ast.SignValue.PLUS)), node.Label.OP)
        node.append(generated.ast.word_to_cst(generated.ast.Word(text="b")), node.Label.WORD)
        with pytest.raises(astrt.AstError) as exc:
            generated.ast.sum_from_cst(node)
        assert "rule 'sum': the operands of a fold come from different sources" in exc.value.message


# The most compact fold a user can write: both the operand and the operator are labeled regexes.
TERMINAL_FOLD_GRAMMAR = """
expr := t:/[a-z]+/ , ( , op:/[+-]/ , t:/[a-z]+/)* ;
"""


class TestFoldOverTerminals:
    """A directly labeled regex operand and operator, in both directions."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(TERMINAL_FOLD_GRAMMAR, "expr", SPACED_FORMAT, "rule expr { fold_left: op; }\n")

    def test_the_chain_leaves_are_plain_text(self) -> None:
        generated = self.generated()
        value = generated.ast.parse("a + b - c")
        assert (value.lhs.lhs, value.lhs.rhs, value.rhs) == ("a", "b", "c")
        assert (value.lhs.op, value.op) == ("+", "-")

    @pytest.mark.parametrize("text", ["a", "a + b", "a + b - c"])
    def test_the_round_trip_law_holds(self, text: str) -> None:
        generated = self.generated()
        value = generated.ast.parse(text)
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_chain_round_trips(self) -> None:
        generated = self.generated()
        value = generated.ast.ExprBinary("-", "x", "y")
        assert generated.ast.unparse(value).replace(" ", "") == "x-y"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_an_operand_the_terminal_cannot_match_is_a_serialise_error(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError, match=re.escape("does not match the terminal /[a-z]+/")):
            generated.ast.unparse(generated.ast.ExprBinary("+", "1", "y"))

    def test_an_operator_the_terminal_cannot_match_is_a_serialise_error(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError, match=re.escape("does not match the terminal /[+-]/")):
            generated.ast.unparse(generated.ast.ExprBinary("*", "x", "y"))


class TestFoldNaming:
    """``name:``, ``variant`` and ``field`` renames reach the generated fold surface."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(
            SUM_GRAMMAR,
            "sum",
            config_text=(
                "rule sum { fold_left: op; name: Total; variant Binary: Chain; "
                "field op { name: operator; } }\nrule word { transparent; }\n"
            ),
        )

    def test_the_renamed_link_class_carries_the_renamed_member(self) -> None:
        generated = self.generated()
        value = generated.ast.parse("a + b")
        assert type(value).__name__ == "TotalChain"
        assert value.operator.value is generated.ast.SignValue.PLUS
        assert 'Total: typing.TypeAlias = "str | TotalChain"' in generated.source

    def test_the_renamed_surface_round_trips(self) -> None:
        generated = self.generated()
        value = generated.ast.TotalChain(generated.ast.Sign(generated.ast.SignValue.MINUS), "x", "y")
        assert generated.ast.unparse(value).replace(" ", "") == "x-y"
        assert generated.ast.parse(generated.ast.unparse(value)) == value


# Two adjacent word terminals need a space between them to re-parse, and a synthesised CST
# carries no trivia, so the round trips below need the default spacing of `,` to render one.
SPACED_FORMAT = "ws_allowed: bsp;"


@pytest.fixture(scope="module")
def task() -> Generated:
    return build_roundtrip(TASK_GRAMMAR, "task_def", SPACED_FORMAT, config_text=TASK_SIDECAR)


class TestFlatten:
    """``flatten;`` hoists a wrapper's fields into its parent, in both directions."""

    def test_the_hoisted_fields_sit_on_the_parent(self, task: Generated) -> None:
        value = task.ast.parse("task t every 5m { }")
        assert (value.name, value.interval, value.unit) == ("t", 5, task.ast.TimeUnitValue.MIN)
        assert not hasattr(task.ast, "Schedule")
        assert not hasattr(task.ast, "schedule_from_cst")

    def test_an_absent_wrapper_leaves_the_hoisted_fields_at_their_defaults(self, task: Generated) -> None:
        value = task.ast.parse("task build { retries = 3; }")
        assert (value.interval, value.unit) == (None, None)
        assert value.settings == [task.ast.Setting(key="retries", value=3)]

    def test_a_mutated_wrapper_is_re_materialised(self, task: Generated) -> None:
        value = task.ast.parse("task build { retries = 3; }")
        value.interval = 30
        value.unit = task.ast.TimeUnitValue.SEC
        rendered = task.ast.unparse(value)
        assert "task build every 30s" in rendered
        assert task.ast.parse(rendered) == value

    @pytest.mark.parametrize("text", ["task t every 5m { }", "task t { a = 1; b = 2; }"])
    def test_the_round_trip_law_holds(self, task: Generated, text: str) -> None:
        value = task.ast.parse(text)
        assert task.ast.parse(task.ast.unparse(value)) == value

    def test_a_hand_built_value_without_the_wrapper_round_trips(self, task: Generated) -> None:
        value = task.ast.TaskDef(name="db", interval=None, unit=None, settings=[])
        assert "every" not in task.ast.unparse(value)
        assert task.ast.parse(task.ast.unparse(value)) == value

    def test_a_partially_populated_wrapper_is_an_error(self, task: Generated) -> None:
        value = task.ast.TaskDef(name="db", interval=30, unit=None, settings=[])
        with pytest.raises(astrt.AstError) as exc:
            task.ast.unparse(value)
        assert "the flattened wrapper needs a 'unit' value" in exc.value.message

    def test_the_wrapper_is_read_through_one_private_helper_pair(self, task: Generated) -> None:
        assert "def _flat_schedule_from_cst(node: cst.Schedule) -> tuple[int, TimeUnitValue]:" in task.source
        assert "def _flat_schedule_to_cst(_f_interval: int, _f_unit: TimeUnitValue) -> cst.Schedule:" in task.source


REQUIRED_WRAPPER_GRAMMAR = """
top   := "<" , w:pair , ">" ;
pair  := k:word . "=" . v:word , flags:mark* ;
mark  := m:"!" ;
word  := c:/[a-z]+/ ;
"""


class TestFlattenRequiredSite:
    """A required wrapper site keeps the wrapper's own field types and is always rebuilt."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(REQUIRED_WRAPPER_GRAMMAR, "top", config_text="rule pair { flatten; }")

    def test_the_fields_are_not_degraded(self) -> None:
        generated = self.generated()
        value = generated.ast.parse("<a=b !>")
        assert value.k == generated.ast.Word(text="a")
        assert value.v == generated.ast.Word(text="b")
        # `mark := m:"!"` carries literals only, so its one field is the literal's position;
        # positions are out of equality, so the constructed node compares equal to the parsed one.
        assert value.flags == [generated.ast.Mark(m=terminalsrc.UnknownSpan)]

    def test_the_wrapper_comes_back_unconditionally(self) -> None:
        generated = self.generated()
        value = generated.ast.Top(k=generated.ast.Word(text="x"), v=generated.ast.Word(text="y"), flags=[])
        assert generated.ast.unparse(value).replace(" ", "") == "<x=y>"
        assert generated.ast.parse(generated.ast.unparse(value)) == value


NESTED_WRAPPER_GRAMMAR = """
top    := "<" , w:outer , ">" ;
outer  := i:inner , tail:word ;
inner  := k:word . "=" . v:word ;
word   := c:/[a-z]+/ ;
"""


class TestFlattenTransitive:
    """A flattened wrapper may itself hoist a flattened wrapper."""

    def test_both_layers_reach_the_outermost_node(self) -> None:
        generated = build_roundtrip(
            NESTED_WRAPPER_GRAMMAR, "top", SPACED_FORMAT, "rule outer { flatten; }\nrule inner { flatten; }\n"
        )
        value = generated.ast.parse("<a=b c>")
        assert [value.k.text, value.v.text, value.tail.text] == ["a", "b", "c"]
        assert generated.ast.parse(generated.ast.unparse(value)) == value
        for name in ("Outer", "Inner"):
            assert not hasattr(generated.ast, name)


MERGED_WRAPPER_GRAMMAR = """
top   := "<" , w:pair? , ">" ;
pair  := k:word . "=" . v:word | j:word ;
word  := c:/[a-z]+/ ;
"""


class TestFlattenMergedWrapper:
    """A wrapper whose alternatives merge into one product picks one by trial when rebuilt."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(MERGED_WRAPPER_GRAMMAR, "top", config_text="rule pair { flatten; product; }")

    def test_each_alternative_converts(self) -> None:
        generated = self.generated()
        assert (generated.ast.parse("<a=b>").v, generated.ast.parse("<a=b>").j) == (
            generated.ast.Word(text="b"),
            None,
        )
        assert generated.ast.parse("<c>").j == generated.ast.Word(text="c")

    def test_the_populated_fields_choose_the_alternative(self) -> None:
        generated = self.generated()
        word = generated.ast.Word
        pair = generated.ast.Top(k=word(text="a"), v=word(text="b"), j=None)
        assert generated.ast.unparse(pair).strip() == "<a=b>"
        lone = generated.ast.Top(k=None, v=None, j=word(text="c"))
        assert generated.ast.unparse(lone).strip() == "<c>"
        assert generated.ast.parse(generated.ast.unparse(pair)) == pair

    def test_an_empty_wrapper_collapses(self) -> None:
        generated = self.generated()
        assert generated.ast.unparse(generated.ast.Top(k=None, v=None, j=None)).strip() == "<>"


# A wrapper required by both alternatives of a merged product, whose own field is optional: the
# alternative trial has to count the wrapper as there whatever the hoisted field holds.
MERGED_PARENT_GRAMMAR = """
top  := "<" , pair , x:word , ">" | "<" , pair , y:num , ">" ;
pair := "(" , k:word? , ")" ;
word := c:/[a-z]+/ ;
num  := d:/[0-9]+/ ;
"""

# The same wrapper reached through one branch of a sub-expression alternation.
BRANCH_PARENT_GRAMMAR = """
top  := "<" , ( w:pair | j:word ) , ">" ;
pair := k:word . "=" . v:word ;
word := c:/[a-z]+/ ;
num  := d:/[0-9]+/ ;
"""


class TestFlattenInAMultiAlternativeParent:
    """A hoisted group counts as its wrapper's label when an alternative or a branch is chosen."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(
            MERGED_PARENT_GRAMMAR, "top", SPACED_FORMAT, "rule pair { flatten; }\nrule top { product; }\n"
        )

    @pytest.mark.parametrize("text", ["< ( a ) b >", "< ( ) b >", "< ( a ) 7 >", "< ( ) 7 >"])
    def test_each_alternative_round_trips(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_required_wrapper_with_nothing_in_it_still_fits_an_alternative(self) -> None:
        """Reading the wrapper's presence off its hoisted fields would leave no alternative fitting."""
        generated = self.generated()
        value = generated.ast.Top(k=None, x=generated.ast.Word(text="b"), y=None)
        assert generated.ast.unparse(value).replace(" ", "") == "<()b>"
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_no_alternative_fits_a_value_populating_both(self) -> None:
        generated = self.generated()
        value = generated.ast.Top(k=None, x=generated.ast.Word(text="b"), y=generated.ast.Num(text="7"))
        with pytest.raises(astrt.AstError, match="no alternative fits the populated fields"):
            value.to_cst()


class TestFlattenInsideAnAlternation:
    """The wrapper's label is one branch of an alternation, so the group check reads it too."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(BRANCH_PARENT_GRAMMAR, "top", SPACED_FORMAT, "rule pair { flatten; }\n")

    @pytest.mark.parametrize("text", ["< a=b >", "< c >"])
    def test_each_branch_round_trips(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_populating_the_wrapper_and_the_sibling_branch_is_an_error(self) -> None:
        generated = self.generated()
        word = generated.ast.Word
        value = generated.ast.Top(k=word(text="a"), v=word(text="b"), j=word(text="c"))
        with pytest.raises(astrt.AstError, match=r"\['j', 'w'\] cannot come from one branch"):
            value.to_cst()

    def test_populating_neither_branch_is_an_error(self) -> None:
        generated = self.generated()
        with pytest.raises(astrt.AstError, match=r"needs one of \['j', 'w'\] at this position"):
            generated.ast.Top(k=None, v=None, j=None).to_cst()


# A keyed collection inside an optional wrapper: the hoisted field's absent default is an empty
# map, not the empty list or ``None`` every other optional hoist takes.
KEYED_WRAPPER_GRAMMAR = """
top   := "<" , w:bag? , ">" ;
bag   := "(" , entries:entry* , ")" ;
entry := name:word , "=" , v:num , ";" , ;
word  := c:/[a-z]+/ ;
num   := d:/[0-9]+/ ;
"""

KEYED_WRAPPER_SIDECAR = """
rule bag   { flatten; }
rule word  { transparent; }
rule num   { type: i64; transparent; }
rule entry { key: name; }
"""


class TestFlattenAKeyedCollection:
    """``key:`` inside a flattened wrapper: the hoisted field is a map at either use site."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(KEYED_WRAPPER_GRAMMAR, "top", SPACED_FORMAT, KEYED_WRAPPER_SIDECAR)

    def test_the_hoisted_field_is_a_map_on_the_parent(self) -> None:
        generated = self.generated()
        assert "entries: dict[str, Entry]" in generated.source
        value = generated.ast.parse("< ( a = 1 ; b = 2 ; ) >")
        assert list(value.entries) == ["a", "b"]

    def test_an_absent_wrapper_leaves_an_empty_map(self) -> None:
        """A list or a ``None`` here would sit in a ``dict``-annotated field with nothing raising."""
        value = self.generated().ast.parse("< >")
        assert value.entries == {}

    @pytest.mark.parametrize("text", ["< >", "< ( a = 1 ; ) >"])
    def test_the_round_trip_law_holds(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value


class TestFlattenIntoSumPayload:
    """A sum variant over a flattened wrapper carries the hoisted fields in its payload class."""

    GRAMMAR = (
        "top := s:choice , ';' ;\nchoice := a:wrap | b:word ;\nwrap := '(' . k:word . ')' ;\nword := c:/[a-z]+/ ;\n"
    )

    def test_the_payload_class_holds_the_hoisted_fields(self) -> None:
        generated = build_roundtrip(self.GRAMMAR, "top", config_text="rule wrap { flatten; }")
        value = generated.ast.parse("(ab);")
        assert value.s == generated.ast.ChoiceA(k=generated.ast.Word(text="ab"))
        assert generated.ast.parse(generated.ast.unparse(value)) == value
        assert generated.ast.parse(generated.ast.unparse(generated.ast.parse("ab;"))).s == generated.ast.Word(text="ab")


class TestFlattenGoalRule:
    """A flattened rule has no type, so it cannot be what the conveniences take and return."""

    def test_a_flattened_goal_is_refused(self) -> None:
        parser_result = generate_parser(parse_grammar(NESTED_WRAPPER_GRAMMAR))
        config = ac.load_ast_config("rule inner { flatten; }", parser_result.grammar, {ac.Backend.PYTHON})
        with pytest.raises(ValueError, match="flattened into its use sites"):
            ast_module_for(parser_result, goal="inner", config=config)

    GOAL_GRAMMAR = "wrap := k:word ;\ntop := '<' , w:wrap , '>' ;\nword := c:/[a-z]+/ ;\n"

    def test_a_flattened_first_rule_is_skipped_by_the_default(self) -> None:
        """Without the sidecar the default is ``wrap``; flattening it moves the default on."""
        parser_result = generate_parser(parse_grammar(self.GOAL_GRAMMAR))
        config = ac.load_ast_config("rule wrap { flatten; }", parser_result.grammar, {ac.Backend.PYTHON})
        plain = am.build_ast_model(parser_result.grammar)
        flattened = am.build_ast_model(parser_result.grammar, config)
        assert am.resolve_goal_rule(plain, None) == "wrap"
        assert am.resolve_goal_rule(flattened, None) == "top"

    def test_the_conveniences_target_the_rule_the_default_landed_on(self) -> None:
        generated = build_roundtrip(self.GOAL_GRAMMAR, None, config_text="rule wrap { flatten; }")
        assert type(generated.ast.parse("<ab>")).__name__ == "Top"


# One label carrying three types, one per alternative: the shape whose alternatives share a label
# signature, so their populated names are identical and only the value's kind tells them apart.
UNION_LABEL_GRAMMAR = """
val  := item:num | item:word | item:/[!@#]+/ ;
num  := d:/[0-9]+/ ;
word := c:/[a-z]+/ ;
"""

# The same union label beside a second one an alternative demands, so a value can populate names
# one alternative carries while holding a kind only the other accepts.
UNION_MISFIT_GRAMMAR = """
top  := x:num , y:word | x:word ;
num  := d:/[0-9]+/ ;
word := c:/[a-z]+/ ;
"""


class TestUnionLabelSelection:
    """A field several kinds share: which alternative can render a value is the value's own kind."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(UNION_LABEL_GRAMMAR, "val", config_text="rule val { product; }\n")

    @pytest.mark.parametrize("text", ["123", "abc", "!@#"])
    def test_every_alternatives_kind_round_trips(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "val")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_a_hand_built_value_of_any_kind_synthesises_a_cst_of_that_kind(self) -> None:
        """Name-only selection would place a wrong-kind child under the label silently."""
        generated = self.generated()
        items = [generated.ast.Num(text="1"), generated.ast.Word(text="a"), "!@#"]
        for item in items:
            value = generated.ast.Val(item=item)
            node = value.to_cst()
            assert generated.ast.Val.from_cst(node) == value
        assert [type(generated.ast.Val(item=item).to_cst().children[0][1]).__name__ for item in items] == [
            "Num",
            "Word",
            "Span",
        ]

    def test_a_kind_the_fitting_alternative_cannot_accept_leaves_none_fitting(self) -> None:
        generated = build_roundtrip(UNION_MISFIT_GRAMMAR, "top", SPACED_FORMAT, "rule top { product; }\n")
        word = generated.ast.Word
        value = generated.ast.Top(x=word(text="a"), y=word(text="b"))
        with pytest.raises(astrt.AstError, match="no alternative fits the populated fields"):
            value.to_cst()

    def test_every_alternative_carries_the_kind_test_of_its_own_position(self) -> None:
        """One alternative's guard tuple on all three is the defect this selection closes."""
        names = 'astrt.alternative_fits(_present, frozenset({"item"}), frozenset({"item"}))'
        source = self.generated().source
        start = source.index("    def to_cst(self) -> cst.Val:")
        assert source[start : source.index("\n\n", start)] == (
            "    def to_cst(self) -> cst.Val:\n"
            '        """Synthesise a ``val`` CST node from this value."""\n'
            '        _present = astrt.populated({"item": astrt.holds(self.item)})\n'
            f"        if {names} and astrt.field_fits(self.item, (Num,)):\n"
            "            return self._to_cst_alt0()\n"
            f"        if {names} and astrt.field_fits(self.item, (Word,)):\n"
            "            return self._to_cst_alt1()\n"
            f"        if {names} and astrt.field_fits(self.item, (str,)):\n"
            "            return self._to_cst_alt2()\n"
            "        msg = \"rule 'val': no alternative fits the populated fields\"\n"
            "        raise astrt.AstError(msg, self.span)"
        )

    def test_a_field_of_one_kind_carries_no_kind_test(self) -> None:
        """The merged product is already discriminated by names alone."""
        assert "field_fits" not in build(MERGED_GRAMMAR).source

    def test_alternatives_accepting_the_same_kind_carry_no_kind_test(self) -> None:
        """Two spellings of one value: first-fit canonicalisation needs no kind information."""
        grammar = "wrapped := v:word | '(' . v:word . ')' ;\nword := c:/[a-z]+/ ;\n"
        assert "field_fits" not in build_roundtrip(grammar, "wrapped").source


# A union label in a container: the kind half has to look through the list, and an absent
# optional constrains nothing.
UNION_CONTAINER_GRAMMAR = """
rep  := x:num* , y:word | x:word* ;
opt  := x:num? , y:word | x:word? ;
num  := d:/[0-9]+/ ;
word := c:/[a-z]+/ ;
"""

# Two spellings of a bare string: an erased rule's own text beside a rival terminal's, which
# nothing but the erased rule's converter can tell apart.
ERASED_UNION_GRAMMAR = """
top  := x:word | x:/[!@#]+/ ;
word := c:/[a-z]+/ ;
"""


class TestUnionLabelContainers:
    """A union label a container holds: every value it carries has to be an accepted kind."""

    @staticmethod
    def generated(goal: str) -> Generated:
        return build_roundtrip(
            UNION_CONTAINER_GRAMMAR, goal, SPACED_FORMAT, "rule rep { product; }\nrule opt { product; }\n"
        )

    def test_a_repeated_field_whose_values_are_all_accepted_selects_that_alternative(self) -> None:
        generated = self.generated("rep")
        value = generated.ast.Rep(x=[generated.ast.Word(text="a"), generated.ast.Word(text="b")], y=None)
        assert generated.ast.Rep.from_cst(value.to_cst()) == value

    @pytest.mark.parametrize("first", [True, False])
    def test_one_value_of_a_repeated_field_no_alternative_accepts_leaves_none_fitting(self, first: bool) -> None:  # noqa: FBT001
        """Every value is asked, not just the one at the head: a list whose tail an alternative
        cannot place would otherwise be half rendered under it."""
        generated = self.generated("rep")
        values = [generated.ast.Num(text="1"), generated.ast.Word(text="a")]
        value = generated.ast.Rep(x=values if first else values[::-1], y=None)
        with pytest.raises(astrt.AstError, match="no alternative fits the populated fields"):
            value.to_cst()

    def test_an_absent_optional_field_constrains_nothing(self) -> None:
        """The name half decides a label the value does not carry; the kind half has nothing to say."""
        generated = self.generated("opt")
        value = generated.ast.Opt(x=None, y=generated.ast.Word(text="q"))
        assert generated.ast.Opt.from_cst(value.to_cst()) == value


class TestErasedUnionLabelSelection:
    """Two kinds that are both a bare string: the erased rule's converter is the only test."""

    @staticmethod
    def generated() -> Generated:
        return build_roundtrip(
            ERASED_UNION_GRAMMAR, "top", config_text="rule top { product; }\nrule word { transparent; }\n"
        )

    @pytest.mark.parametrize("text", ["abc", "!@#"])
    def test_both_spellings_round_trip(self, text: str) -> None:
        generated = self.generated()
        value = generated.convert(text, "top")
        assert generated.ast.parse(generated.ast.unparse(value)) == value

    def test_the_erased_rules_kind_is_tested_by_running_its_converter(self) -> None:
        """Its values are a bare string, so a type test would take the rival terminal's too."""
        assert "astrt.field_fits(self.x, (astrt.Convertible(_erased_word_to_cst),))" in self.generated().source

    def test_the_text_a_converter_declines_reaches_the_alternative_that_spells_it(self) -> None:
        generated = self.generated()
        assert [type(generated.ast.Top(x=text).to_cst().children[0][1]).__name__ for text in ("abc", "!@#")] == [
            "Word",
            "Span",
        ]
