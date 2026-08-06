"""Unit tests for the FLTK plumbing module."""

import sys
import types
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst
from fltk.fegen import fltk_parser as _fltk_parser
from fltk.fegen.ast_config import AstConfigError, Backend
from fltk.fegen.fltk2gsm import Cst2Gsm
from fltk.fegen.pyrt import terminalsrc as _terminalsrc
from fltk.plumbing import (
    generate_ast,
    generate_ast_source,
    generate_parser,
    generate_unparser,
    generate_unparser_source,
    parse_ast_config,
    parse_ast_config_file,
    parse_format_config,
    parse_grammar,
    parse_text,
    render_doc,
    unparse_cst,
)
from fltk.plumbing_types import UnparserResult
from fltk.unparse.combinators import HARDLINE, LINE, NBSP, NIL, SOFTLINE, Concat, Line, Nbsp, Text
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig
from fltk.unparse.renderer import RendererConfig


class TestGrammarParsing:
    """Test grammar parsing functions."""

    def test_parse_simple_grammar(self):
        """Test parsing a simple grammar."""
        grammar_text = """
        expr := term , ("+" , term)*;
        term := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)

        assert grammar is not None
        assert len(grammar.rules) == 3
        assert grammar.rules[0].name == "expr"
        assert grammar.rules[1].name == "term"
        assert grammar.rules[2].name == "number"

    def test_parse_invalid_grammar(self):
        """Test parsing invalid grammar raises error."""
        with pytest.raises(ValueError, match="Grammar parse failed"):
            parse_grammar("this is not valid grammar syntax")

    def test_parse_empty_grammar(self):
        """Test parsing empty grammar raises error."""
        with pytest.raises(ValueError, match="Grammar parse failed"):
            parse_grammar("")


class TestParserGeneration:
    """Test parser generation functions."""

    def test_generate_parser_with_trivia(self):
        """Test generating parser with trivia capture."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        assert parser_result.parser_class is not None
        assert parser_result.cst_module is not None
        assert parser_result.cst_module_name in sys.modules
        assert parser_result.capture_trivia is True
        assert hasattr(parser_result.cst_module, "Expr")
        assert hasattr(parser_result.cst_module, "Number")

    def test_generate_parser_without_trivia(self):
        """Test generating parser without trivia capture."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=False)

        assert parser_result.parser_class is not None
        assert parser_result.capture_trivia is False

    def test_parser_module_cleanup(self):
        """Test that generated modules are properly registered."""
        grammar = parse_grammar('test := value:"hello";')  # Include item to avoid empty model
        parser_result = generate_parser(grammar)

        # Module should be in sys.modules
        assert parser_result.cst_module_name in sys.modules
        assert sys.modules[parser_result.cst_module_name] is parser_result.cst_module

    def test_each_generated_cst_module_gets_its_own_name(self):
        """Names come from a monotonic counter, so regenerating one grammar clobbers nothing."""
        grammar = parse_grammar('test := value:"hello";')

        first = generate_parser(grammar)
        second = generate_parser(grammar)

        assert first.cst_module_name != second.cst_module_name
        assert sys.modules[first.cst_module_name] is first.cst_module
        assert sys.modules[second.cst_module_name] is second.cst_module


class TestParsing:
    """Test text parsing functions."""

    def test_parse_simple_expression(self):
        """Test parsing a simple expression."""
        grammar_text = """
        expr := number , ("+" , number)*;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "123+456", "expr")

        assert parse_result.success is True
        assert parse_result.cst is not None
        assert parse_result.error_message is None

    def test_parse_with_auto_rule(self):
        """Test parsing with auto-detected start rule."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        # Should use "expr" as first rule
        parse_result = parse_text(parser_result, "123")

        assert parse_result.success is True
        assert parse_result.cst is not None

    def test_parse_failure(self):
        """Test parsing failure returns error message."""
        grammar_text = """
        expr := value:"hello";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "goodbye", "expr")

        assert parse_result.success is False
        assert parse_result.cst is None
        assert parse_result.error_message is not None
        assert "hello" in parse_result.error_message

    def test_parse_invalid_rule(self):
        """Test parsing with invalid rule name."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar)

        parse_result = parse_text(parser_result, "test", "nonexistent")

        assert parse_result.success is False
        assert parse_result.error_message is not None
        assert "No parse method for rule 'nonexistent'" in parse_result.error_message


class TestFormatConfig:
    """Test format configuration parsing."""

    def test_parse_empty_config(self):
        """Test parsing empty format config."""
        config = parse_format_config("")
        assert isinstance(config.global_ws_allowed, type(NIL))
        assert isinstance(config.global_ws_required, type(LINE))
        assert len(config.rule_configs) == 0

    def test_parse_global_config(self):
        """Test parsing global format config."""
        config_text = """
        ws_allowed: nbsp;
        ws_required: hard;
        """
        config = parse_format_config(config_text)

        assert isinstance(config.global_ws_allowed, type(NBSP))
        assert isinstance(config.global_ws_required, type(HARDLINE))

    def test_parse_rule_config(self):
        """Test parsing rule-specific format config."""
        config_text = """
        rule expr {
            ws_allowed: soft;
            ws_required: bsp;
        }
        """
        config = parse_format_config(config_text)

        assert "expr" in config.rule_configs
        assert isinstance(config.rule_configs["expr"].ws_allowed_spacing, type(SOFTLINE))
        assert isinstance(config.rule_configs["expr"].ws_required_spacing, type(LINE))

    def test_parse_invalid_config(self):
        """Test parsing invalid format config raises error."""
        with pytest.raises(ValueError, match="Format config parse failed"):
            parse_format_config("this is not valid format syntax")


class TestUnparserGeneration:
    """Test unparser generation functions."""

    def test_generate_basic_unparser(self):
        """Test generating basic unparser."""
        grammar_text = """
        expr := value:"hello";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        assert unparser_result.unparser_class is not None
        assert hasattr(unparser_result.unparser_class, "__init__")
        assert hasattr(unparser_result.unparser_class, "unparse_expr")

    def test_generate_unparser_with_formatter(self):
        """Test generating unparser with formatter config."""
        grammar = parse_grammar('expr := a:"a" , b:"b";')
        parser_result = generate_parser(grammar, capture_trivia=True)

        formatter_config = FormatterConfig()
        formatter_config.global_ws_allowed = Nbsp()

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        assert unparser_result.formatter_config is formatter_config

    def test_generate_unparser_with_trivia_config(self):
        """Test generating unparser with trivia config."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar, capture_trivia=True)

        trivia_config = TriviaConfig(preserve_node_names={"LineComment"})
        formatter_config = FormatterConfig()
        formatter_config.trivia_config = trivia_config

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        assert unparser_result.trivia_config is trivia_config


class TestUnparserSource:
    """Test the source-returning unparser helper (single-sources the assembly pipeline)."""

    def test_source_defines_unparser_class_when_exec(self):
        """generate_unparser_source returns source that, exec'd, defines an Unparser class."""
        grammar = parse_grammar('expr := value:"hello";')
        parser_result = generate_parser(grammar, capture_trivia=True)

        source = generate_unparser_source(grammar, parser_result.cst_module_name)

        assert isinstance(source, str)
        exec_globals: dict = {}
        exec(source, exec_globals)  # noqa: S102
        assert "Unparser" in exec_globals
        assert hasattr(exec_globals["Unparser"], "unparse_expr")

    def test_generate_unparser_matches_source_output(self):
        """generate_unparser execs exactly what generate_unparser_source returns.

        Cross-checks both public entry points on the same inputs: the unparser exec'd
        from generate_unparser_source's string must render identically to the one
        generate_unparser produces. This pins the single-source contract — if
        generate_unparser stopped routing through _assemble_unparser_module (or the two
        entry points diverged), this test would catch it.
        """
        grammar_text = """
        expr := hello:"hello" , world:"world";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "helloworld", "expr")

        # Exec path (generate_unparser).
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
        expected = render_doc(unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr"))

        # Source path (generate_unparser_source): exec the returned string and drive the same CST.
        source = generate_unparser_source(grammar, parser_result.cst_module_name)
        exec_globals: dict = {}
        exec(source, exec_globals)  # noqa: S102
        source_result = UnparserResult(
            unparser_class=exec_globals["Unparser"],
            grammar=unparser_result.grammar,
            formatter_config=unparser_result.formatter_config,
            trivia_config=unparser_result.trivia_config,
        )
        actual = render_doc(unparse_cst(source_result, parse_result.cst, parse_result.terminals, "expr"))

        assert actual == expected == "helloworld"

    def test_source_reflects_formatter_config(self):
        """A non-default formatter_config is threaded through into the emitted source."""
        grammar = parse_grammar('expr := a:"a" , b:"b";')
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "ab", "expr")

        formatter_config = FormatterConfig()
        formatter_config.global_ws_allowed = Nbsp()

        source = generate_unparser_source(grammar, parser_result.cst_module_name, formatter_config=formatter_config)
        exec_globals: dict = {}
        exec(source, exec_globals)  # noqa: S102
        source_result = UnparserResult(
            unparser_class=exec_globals["Unparser"],
            grammar=parser_result.grammar,
            formatter_config=formatter_config,
            trivia_config=TriviaConfig(),
        )
        # With ws_allowed=Nbsp the "," separator renders as a space; default (NIL) would render "ab".
        rendered = render_doc(unparse_cst(source_result, parse_result.cst, parse_result.terminals, "expr"))
        assert rendered == "a b"


_AST_GRAMMAR = """
config := , entry* ;
entry := key:identifier , "=" , value:number , ";" , ;
identifier := name:/[a-z_][a-z0-9_]*/ ;
number := val:/-?[0-9]+/ ;
"""


class TestAstGeneration:
    """Test AST module generation."""

    @staticmethod
    def _generate(goal_rule=None, parser_module_name=None, unparser_module_name=None):
        """Return (parser_result, ast_result) for the small config grammar above."""
        parser_result = generate_parser(parse_grammar(_AST_GRAMMAR), capture_trivia=False)
        ast_result = generate_ast(
            parser_result.grammar,
            parser_result.cst_module_name,
            parser_module_name,
            unparser_module_name,
            goal_rule,
        )
        return parser_result, ast_result

    def test_generate_ast_defines_node_classes(self):
        """Every non-trivia rule gets a class carrying the converters in both directions."""
        _parser_result, ast_result = self._generate()

        for class_name in ("Config", "Entry", "Identifier", "Number"):
            node_class = getattr(ast_result.ast_module, class_name)
            assert hasattr(node_class, "from_cst")
            assert hasattr(node_class, "to_cst")
        assert hasattr(ast_result.ast_module, "config_from_cst")
        assert hasattr(ast_result.ast_module, "config_to_cst")
        assert set(ast_result.model.nodes) == {"config", "entry", "identifier", "number"}

    def test_returned_grammar_carries_the_trivia_processing(self):
        """AstResult.grammar is the processed grammar, ready to feed a second generator."""
        parser_result, ast_result = self._generate()

        assert "_trivia" in ast_result.grammar.identifiers
        assert any(rule.is_trivia_rule for rule in ast_result.grammar.rules)
        # Feeding it back is the use the field exists for; the pipeline is idempotent.
        again = generate_ast(ast_result.grammar, parser_result.cst_module_name)
        assert set(again.model.nodes) == set(ast_result.model.nodes)

    def test_generate_ast_converts_a_parsed_cst(self):
        """The generated converters run against a CST from the paired parser."""
        parser_result, ast_result = self._generate()
        parse_result = parse_text(parser_result, "port = 8080;\n", "config")
        assert parse_result.success, parse_result.error_message

        config = ast_result.ast_module.config_from_cst(parse_result.cst)

        assert [entry.key.text for entry in config.entry] == ["port"]
        assert [entry.value.text for entry in config.entry] == ["8080"]
        # Synthesising a CST needs no unparser module.
        assert ast_result.ast_module.config_to_cst(config) is not None

    def test_generate_ast_accepts_a_raw_grammar(self):
        """A grammar straight from parse_grammar works: trivia processing is applied and idempotent."""
        raw_grammar = parse_grammar(_AST_GRAMMAR)
        parser_result = generate_parser(raw_grammar, capture_trivia=False)

        ast_result = generate_ast(raw_grammar, parser_result.cst_module_name)

        parse_result = parse_text(parser_result, "a = 1;", "config")
        config = ast_result.ast_module.config_from_cst(parse_result.cst)
        assert [entry.key.text for entry in config.entry] == ["a"]

    def test_goal_rule_defaults_to_first_rule(self):
        """With no goal_rule the grammar's first rule is recorded, matching parse_text's default."""
        _parser_result, ast_result = self._generate()

        assert ast_result.goal_rule == "config"

    def test_explicit_goal_rule_is_recorded(self):
        """An explicit goal_rule is reported back on the result."""
        _parser_result, ast_result = self._generate(goal_rule="entry")

        assert ast_result.goal_rule == "entry"

    def test_unknown_goal_rule_is_an_error(self):
        """A goal rule with no AST node fails with the available rules listed."""
        parser_result = generate_parser(parse_grammar(_AST_GRAMMAR), capture_trivia=False)

        with pytest.raises(ValueError, match="goal rule 'nope' has no AST node"):
            generate_ast(parser_result.grammar, parser_result.cst_module_name, goal_rule="nope")

    def test_conveniences_are_gated_on_module_names(self):
        """parse()/unparse() appear only when a parser/unparser module is named."""
        parser_result = generate_parser(parse_grammar(_AST_GRAMMAR), capture_trivia=False)

        bare = generate_ast_source(parser_result.grammar, parser_result.cst_module_name)
        wired = generate_ast_source(
            parser_result.grammar, parser_result.cst_module_name, "some.parser_mod", "some.unparser_mod"
        )

        assert "def parse(" not in bare
        assert "def unparse(" not in bare
        assert "def parse(" in wired
        assert "def unparse(" in wired
        assert "import some.parser_mod as _parser" in wired
        assert "import some.unparser_mod as _unparser" in wired

    def test_generate_ast_matches_source_output(self):
        """generate_ast execs exactly what generate_ast_source returns.

        Both entry points route through _assemble_ast_module; converting the same CST through
        each must give equal AST values (equality is by value, so the two module instances'
        distinct classes are compared field-by-field via their reprs).
        """
        parser_result, ast_result = self._generate()
        parse_result = parse_text(parser_result, "x = 5;", "config")

        source = generate_ast_source(parser_result.grammar, parser_result.cst_module_name)
        module_name = "fltk_ast_source_path_test"
        module = types.ModuleType(module_name)
        # dataclasses resolves a class's defining module out of sys.modules while building fields.
        sys.modules[module_name] = module
        try:
            exec(compile(source, "<ast_source>", "exec"), module.__dict__)  # noqa: S102
        finally:
            del sys.modules[module_name]

        from_source = module.config_from_cst(parse_result.cst)
        from_exec = ast_result.ast_module.config_from_cst(parse_result.cst)
        assert repr(from_source) == repr(from_exec)

    def test_ast_module_is_importable_by_name(self):
        """The exec'd module is registered in sys.modules under its reported name."""
        _parser_result, ast_result = self._generate()

        assert sys.modules[ast_result.ast_module_name] is ast_result.ast_module

    def test_each_generated_module_gets_its_own_name(self):
        """Names come from a monotonic counter, so no result can clobber another's entry."""
        _first_parser, first = self._generate()
        _second_parser, second = self._generate()

        assert first.ast_module_name != second.ast_module_name
        assert sys.modules[first.ast_module_name] is first.ast_module
        assert sys.modules[second.ast_module_name] is second.ast_module


_AST_SIDECAR = """
// shape the small config grammar above
rule config { field entry { name: entries; } }
rule entry  { name: Setting; }
"""


class TestAstConfig:
    """The .fltkast sidecar entry points and the shaping they hand to generate_ast."""

    def test_parse_ast_config_resolves_against_the_grammar(self):
        """A raw grammar works: the entry point applies the same trivia processing the model does."""
        config = parse_ast_config(_AST_SIDECAR, parse_grammar(_AST_GRAMMAR))

        assert config.for_rule("entry").type_name == "Setting"
        assert config.for_rule("config").field_names == {"entry": "entries"}
        assert config.for_rule("number").type_name is None

    def test_empty_text_is_an_empty_config(self):
        assert parse_ast_config("", parse_grammar(_AST_GRAMMAR)).rules == {}

    def test_unknown_rule_is_reported(self):
        with pytest.raises(AstConfigError, match="unknown grammar rule 'nope'"):
            parse_ast_config("rule nope { transparent; }", parse_grammar(_AST_GRAMMAR))

    def test_backends_gate_the_custom_entries(self):
        """Generating Python alone does not require the Rust entries of a custom(...) list."""
        sidecar = 'rule number { custom(python: "pkg.mod.Number"); }'

        config = parse_ast_config(sidecar, parse_grammar(_AST_GRAMMAR), {Backend.PYTHON})
        assert config.for_rule("number").custom is not None

        with pytest.raises(AstConfigError, match="missing the rust entries"):
            parse_ast_config(sidecar, parse_grammar(_AST_GRAMMAR), {Backend.RUST})

    def test_parse_ast_config_file(self, tmp_path):
        config_path = tmp_path / "grammar.fltkast"
        config_path.write_text(_AST_SIDECAR)

        config = parse_ast_config_file(config_path, parse_grammar(_AST_GRAMMAR))

        assert config.for_rule("entry").type_name == "Setting"

    def test_missing_config_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="AST config file not found"):
            parse_ast_config_file(tmp_path / "absent.fltkast", parse_grammar(_AST_GRAMMAR))

    def test_generate_ast_applies_the_config(self):
        """The resolved config reaches the model and the emitted module."""
        parser_result = generate_parser(parse_grammar(_AST_GRAMMAR), capture_trivia=False)
        config = parse_ast_config(_AST_SIDECAR, parser_result.grammar)

        ast_result = generate_ast(parser_result.grammar, parser_result.cst_module_name, ast_config=config)

        parse_result = parse_text(parser_result, "port = 8080;\n", "config")
        value = ast_result.ast_module.config_from_cst(parse_result.cst)
        assert [setting.key.text for setting in value.entries] == ["port"]
        assert type(value.entries[0]).__name__ == "Setting"

    def test_generate_ast_without_a_config_is_tier_zero(self):
        parser_result = generate_parser(parse_grammar(_AST_GRAMMAR), capture_trivia=False)

        source = generate_ast_source(parser_result.grammar, parser_result.cst_module_name)

        assert "class Entry:" in source
        assert "class Setting:" not in source


class TestUnparsing:
    """Test unparsing functions."""

    def test_unparse_simple_expression(self):
        """Test unparsing a simple expression."""
        grammar_text = """
        expr := hello:"hello" , world:"world";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "helloworld", "expr")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        assert doc is not None
        # Should be Concat([Text("hello"), Text("world")])
        assert isinstance(doc, Concat)
        assert len(doc.docs) == 2
        assert isinstance(doc.docs[0], Text)
        assert doc.docs[0].content == "hello"
        assert isinstance(doc.docs[1], Text)
        assert doc.docs[1].content == "world"

    def test_unparse_with_auto_rule(self):
        """Test unparsing with auto-detected rule."""
        grammar_text = """
        expr := value:"test";
        """
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "test")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals)

        assert doc is not None
        assert isinstance(doc, Text)
        assert doc.content == "test"

    def test_unparse_invalid_rule(self):
        """Test unparsing with invalid rule name."""
        grammar = parse_grammar('expr := value:"test";')
        parser_result = generate_parser(grammar, capture_trivia=True)
        parse_result = parse_text(parser_result, "test")

        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        with pytest.raises(ValueError, match="No unparse method for rule 'nonexistent'"):
            unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "nonexistent")


class TestRendering:
    """Test rendering functions."""

    def test_render_simple_doc(self):
        """Test rendering a simple doc."""
        doc = Text("hello world")
        output = render_doc(doc)
        assert output == "hello world"

    def test_render_concat_doc(self):
        """Test rendering concatenated docs."""
        doc = Concat([Text("hello"), Line(), Text("world")])
        output = render_doc(doc)
        assert output == "hello world"

    def test_render_with_config(self):
        """Test rendering with custom config."""
        doc = Concat([Text("hello"), Line(), Text("world")])
        config = RendererConfig(indent_width=2, max_width=5)
        output = render_doc(doc, config)
        # Should break due to max_width
        assert output == "hello\nworld"


class TestIntegration:
    """Test full pipeline integration."""

    def test_full_pipeline(self):
        """Test complete parse->unparse->render pipeline."""
        # Define grammar
        grammar_text = """
        expr := term , ("+" , term)*;
        term := number;
        number := value:/[0-9]+/;
        """

        # Parse grammar and generate parser
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse input
        parse_result = parse_text(parser_result, "1+2+3", "expr")
        assert parse_result.success

        # Generate unparser
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name)

        # Unparse to doc
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        # Render
        output = render_doc(doc)
        assert output == "1+2+3"

    def test_pipeline_with_formatting(self):
        """Test pipeline with custom formatting."""
        grammar_text = """
        expr := a:"a" , b:"b" : c:"c";
        """

        # Parse grammar and generate parser
        grammar = parse_grammar(grammar_text)
        parser_result = generate_parser(grammar, capture_trivia=True)

        # Parse with whitespace
        parse_result = parse_text(parser_result, "a b c", "expr")
        assert parse_result.success

        # Create formatter config
        formatter_config = FormatterConfig()
        formatter_config.global_ws_allowed = Nbsp()
        formatter_config.global_ws_required = Line()

        # Generate unparser with formatter
        unparser_result = generate_unparser(grammar, parser_result.cst_module_name, formatter_config=formatter_config)

        # Unparse to doc
        doc = unparse_cst(unparser_result, parse_result.cst, parse_result.terminals, "expr")

        # Render - should have nbsp and line
        output = render_doc(doc)
        assert output == "a b c"  # Nbsp renders as space, Line renders as space in flat mode


class TestCst2GsmNoSelfCst:
    """Verify Cst2Gsm has no self.cst after AC10 removal, and produces correct output."""

    _GRAMMAR_SRC = """\
expr := term , ("+" , term)* ;
term := value:/[0-9]+/ ;
"""

    def test_no_cst_attribute(self):
        """Cst2Gsm instance has no self.cst attribute after removal."""
        terminals = _terminalsrc.TerminalSource(self._GRAMMAR_SRC)
        cst2gsm = Cst2Gsm(terminals.terminals)
        assert not hasattr(cst2gsm, "cst"), "self.cst should be absent from Cst2Gsm after AC10 removal"

    def test_produces_correct_grammar(self):
        """Cst2Gsm(terminals) produces the same gsm.Grammar as the baseline parse_grammar call."""
        # Build the CST via the Python parser.
        terminals = _terminalsrc.TerminalSource(self._GRAMMAR_SRC)
        parser = _fltk_parser.Parser(terminalsrc=terminals)
        result = parser.apply__parse_grammar(0)
        assert result is not None and result.result is not None

        cst2gsm_default = Cst2Gsm(terminals.terminals)
        # result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation.
        grammar_default = cst2gsm_default.visit_grammar(cast("cst.Grammar", result.result))

        # Compare to the baseline produced by parse_grammar (also Python default).
        grammar_baseline = parse_grammar(self._GRAMMAR_SRC)

        assert grammar_default is not None
        assert grammar_default == grammar_baseline


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
