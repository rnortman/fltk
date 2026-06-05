"""Unit tests for the FLTK plumbing module."""

import importlib
import inspect
import sys
import types
from typing import TYPE_CHECKING, cast
from unittest import mock

import pytest

import fltk.plumbing as fltk_plumbing_mod
from fltk.fegen import fltk_cst as _fltk_cst

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cstp
from fltk.fegen import fltk_parser as _fltk_parser
from fltk.fegen.fltk2gsm import Cst2Gsm
from fltk.fegen.pyrt import terminalsrc as _terminalsrc
from fltk.plumbing import (
    RustBackendUnavailableError,
    _load_rust_cst_classes,
    generate_parser,
    generate_unparser,
    parse_format_config,
    parse_grammar,
    parse_grammar_file,
    parse_text,
    render_doc,
    unparse_cst,
)
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


class TestRustBackendUnavailableError:
    """Test RustBackendUnavailableError construction and message."""

    def test_message_without_detail(self):
        err = RustBackendUnavailableError("mypkg.mygrammar_cst")
        assert "mypkg.mygrammar_cst" in str(err)
        assert "unavailable" in str(err)
        assert err.module_name == "mypkg.mygrammar_cst"

    def test_message_with_detail(self):
        err = RustBackendUnavailableError("mypkg.mygrammar_cst", detail="module loaded but exposes no CST classes")
        assert "mypkg.mygrammar_cst" in str(err)
        assert "exposes no CST classes" in str(err)

    def test_is_runtime_error(self):
        err = RustBackendUnavailableError("x")
        assert isinstance(err, RuntimeError)


class TestLoadRustCstClasses:
    """Test _load_rust_cst_classes helper."""

    def test_missing_module_raises_unavailable_error(self):
        """A non-existent module name raises RustBackendUnavailableError."""
        with pytest.raises(RustBackendUnavailableError) as exc_info:
            _load_rust_cst_classes("does_not_exist_pkg_xyz_abc.nope")
        assert "does_not_exist_pkg_xyz_abc.nope" in str(exc_info.value)

    def test_missing_module_chained_from_import_error(self):
        """RustBackendUnavailableError chains the original ImportError."""
        with pytest.raises(RustBackendUnavailableError) as exc_info:
            _load_rust_cst_classes("does_not_exist_pkg_xyz_abc.nope")
        assert isinstance(exc_info.value.__cause__, ImportError)

    def test_module_with_no_classes_raises_unavailable_error(self):
        """A module that loads but exposes no public type attributes raises error."""
        fake_module = types.ModuleType("fake_empty_cst")
        fake_module.some_string = "not a class"  # type: ignore[attr-defined]
        fake_module.some_int = 42  # type: ignore[attr-defined]

        with mock.patch.object(importlib, "import_module", return_value=fake_module):
            with pytest.raises(RustBackendUnavailableError) as exc_info:
                _load_rust_cst_classes("fake_empty_cst")
        assert "exposes no CST classes" in str(exc_info.value)

    def test_module_with_classes_returns_class_dict(self):
        """A module with type attributes returns only those types."""

        class NodeClass:
            pass

        fake_module = types.ModuleType("fake_cst")
        fake_module.NodeClass = NodeClass  # type: ignore[attr-defined]
        fake_module.some_string = "not a class"  # type: ignore[attr-defined]
        fake_module._private = object()  # type: ignore[attr-defined]

        with mock.patch.object(importlib, "import_module", return_value=fake_module):
            result = _load_rust_cst_classes("fake_cst")

        assert "NodeClass" in result
        assert result["NodeClass"] is NodeClass
        # Private names excluded
        assert "_private" not in result
        # Non-type attributes excluded
        assert "some_string" not in result


class TestGenerateParserRustBackend:
    """Tests for generate_parser rust_cst_module parameter (Tier 1 — no real Rust artifact)."""

    def test_python_backend_default_unchanged(self):
        """No rust_cst_module argument → Python backend is used; parser and cst_module are populated as usual."""
        grammar_text = """
        expr := number;
        number := value:/[0-9]+/;
        """
        grammar = parse_grammar(grammar_text)
        pr = generate_parser(grammar)
        assert pr.parser_class is not None
        assert pr.cst_module is not None
        assert pr.cst_module_name in sys.modules
        assert hasattr(pr.cst_module, "Expr")
        assert hasattr(pr.cst_module, "Number")

    def test_rust_backend_missing_module_hard_errors(self):
        """AC4: rust_cst_module missing → RustBackendUnavailableError, no sys.modules pollution."""
        grammar = parse_grammar('test := value:"hello";')
        module_name = f"fltk_grammar_{id(grammar)}"
        # Ensure not already in sys.modules from a prior run
        sys.modules.pop(module_name, None)

        with pytest.raises(RustBackendUnavailableError):
            generate_parser(grammar, rust_cst_module="does_not_exist_pkg_xyz_abc.nope")

        # The per-call CST module must NOT have been registered on failure
        assert module_name not in sys.modules

    def test_rust_backend_empty_module_hard_errors(self):
        """AC4 variant: module loads but exposes no classes → RustBackendUnavailableError."""
        grammar = parse_grammar('test := value:"hello";')
        module_name = f"fltk_grammar_{id(grammar)}"
        sys.modules.pop(module_name, None)

        fake_module = types.ModuleType("fake_empty_cst")
        fake_module.not_a_class = "string"  # type: ignore[attr-defined]

        with mock.patch.object(importlib, "import_module", return_value=fake_module):
            with pytest.raises(RustBackendUnavailableError) as exc_info:
                generate_parser(grammar, rust_cst_module="fake_empty_cst")

        assert "exposes no CST classes" in str(exc_info.value)
        assert module_name not in sys.modules

    def test_rust_backend_uses_provided_classes(self):
        """With a mocked Rust module, generate_parser populates cst_module with the module's classes."""

        class FakeNode:
            pass

        fake_module = types.ModuleType("fake_cst")
        fake_module.FakeNode = FakeNode  # type: ignore[attr-defined]

        grammar = parse_grammar('fake_node := value:"hello";')
        module_name = f"fltk_grammar_{id(grammar)}"
        sys.modules.pop(module_name, None)

        with mock.patch.object(importlib, "import_module", return_value=fake_module):
            pr = generate_parser(grammar, rust_cst_module="fake_cst")

        assert pr.parser_class is not None
        assert pr.cst_module_name in sys.modules
        assert hasattr(pr.cst_module, "FakeNode")
        assert pr.cst_module.FakeNode is FakeNode  # type: ignore[attr-defined]


class TestParseGrammarRustBackend:
    """Tier 1 tests for parse_grammar / parse_grammar_file rust_fegen_cst_module parameter."""

    def test_parse_grammar_python_default_unchanged(self):
        """No rust_fegen_cst_module → Python path, behavior identical to before."""
        grammar = parse_grammar('expr := value:"hello";')
        assert grammar is not None
        assert len(grammar.rules) >= 1

    def test_parse_grammar_rust_missing_module_hard_errors(self):
        """AC4: missing rust_fegen_cst_module → RustBackendUnavailableError, no fallback."""
        grammar_text = 'expr := value:"hello";'
        with pytest.raises(RustBackendUnavailableError) as exc_info:
            parse_grammar(grammar_text, rust_fegen_cst_module="does_not_exist_pkg_xyz.nope")
        assert "does_not_exist_pkg_xyz.nope" in str(exc_info.value)

    def test_parse_grammar_rust_missing_module_no_fallback(self):
        """AC4: on Rust backend failure, the function raises RustBackendUnavailableError."""
        grammar_text = 'expr := value:"hello";'
        with pytest.raises(RustBackendUnavailableError):
            parse_grammar(grammar_text, rust_fegen_cst_module="does_not_exist_xyz.nope")

    def test_parse_grammar_file_rust_missing_module_hard_errors(self, tmp_path):
        """AC4: parse_grammar_file with missing rust_fegen_cst_module raises RustBackendUnavailableError."""
        grammar_file = tmp_path / "test.fltkg"
        grammar_file.write_text('expr := value:"hello";')
        with pytest.raises(RustBackendUnavailableError) as exc_info:
            parse_grammar_file(grammar_file, rust_fegen_cst_module="does_not_exist_pkg_xyz.nope")
        assert "does_not_exist_pkg_xyz.nope" in str(exc_info.value)


class TestCst2GsmDefaultNamespace:
    """Guard the DI refactor's backward-compatibility guarantee for Cst2Gsm.

    Cst2Gsm(terminals) with no cst= argument must use fltk_cst as its namespace
    and produce the same gsm.Grammar output as the pre-DI baseline.
    """

    _GRAMMAR_SRC = """\
expr := term , ("+" , term)* ;
term := value:/[0-9]+/ ;
"""

    def test_default_cst_is_fltk_cst(self):
        """Cst2Gsm() with no cst= uses fltk_cst as the namespace object."""
        terminals = _terminalsrc.TerminalSource(self._GRAMMAR_SRC)
        cst2gsm = Cst2Gsm(terminals.terminals)
        assert cst2gsm.cst is _fltk_cst

    def test_default_namespace_produces_correct_grammar(self):
        """Cst2Gsm(terminals) with no cst= produces the same gsm.Grammar as the baseline parse_grammar call."""
        # Build the CST via the Python parser.
        terminals = _terminalsrc.TerminalSource(self._GRAMMAR_SRC)
        parser = _fltk_parser.Parser(terminalsrc=terminals)
        result = parser.apply__parse_grammar(0)
        assert result is not None and result.result is not None

        cst2gsm_default = Cst2Gsm(terminals.terminals)
        # result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation.
        # TODO(parse-result-typed): make ParseResult generic so callers don't need individual casts.
        grammar_default = cst2gsm_default.visit_grammar(cast("cstp.GrammarNode", result.result))

        # Compare to the baseline produced by parse_grammar (also Python default).
        grammar_baseline = parse_grammar(self._GRAMMAR_SRC)

        assert grammar_default is not None
        assert len(grammar_default.rules) == len(grammar_baseline.rules)
        for r_default, r_baseline in zip(grammar_default.rules, grammar_baseline.rules, strict=True):
            assert r_default.name == r_baseline.name


class TestNoRuntimeCompilation:
    """Constraint: plumbing.py must not invoke cargo/maturin/rustc at runtime."""

    def test_plumbing_imports_no_subprocess_or_build_tools(self):
        """plumbing.py must not invoke build tools in _load_rust_cst_classes."""
        # The constraint is that _load_rust_cst_classes ONLY uses importlib.import_module,
        # not subprocess/cargo/maturin/rustc.
        src = inspect.getsource(fltk_plumbing_mod._load_rust_cst_classes)
        assert "subprocess" not in src
        assert "cargo" not in src
        assert "maturin" not in src
        assert "rustc" not in src
        assert "importlib.import_module" in src


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
