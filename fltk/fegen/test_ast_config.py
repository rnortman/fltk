"""Tests for the ``.fltkast`` sidecar grammar, its self-hosted parser, the config model,
and validation against a grammar."""

from __future__ import annotations

import functools

import pytest

from fltk.fegen import ast_config, gsm
from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import fltkast_cst as cst
from fltk.fegen import grammar_shape as gshape
from fltk.fegen.fltkast_parser import Parser
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import create_default_context
from fltk.plumbing import parse_grammar


def _parse(text: str) -> cst.AstSpec:
    terminals = terminalsrc.TerminalSource(text)
    parser = Parser(terminals)
    result = parser.apply__parse_ast_spec(0)
    if not result or result.pos != len(terminals.terminals):
        formatted = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"parse failed:\n{formatted}"
        raise AssertionError(msg)
    assert result.result is not None
    return result.result


def _parse_fails(text: str) -> bool:
    terminals = terminalsrc.TerminalSource(text)
    parser = Parser(terminals)
    result = parser.apply__parse_ast_spec(0)
    return not result or result.pos != len(terminals.terminals)


def _text(span: object) -> str:
    value = span.text()  # type: ignore[attr-defined]
    assert value is not None
    return value


def _identifier(node: cst.Identifier) -> str:
    return _text(node.child_name())


def _only_rule_statement(text: str) -> cst.RuleStatement:
    spec = _parse(text)
    (statement,) = spec.children_statement()
    rule_config = statement.child_rule_config()
    (rule_statement,) = rule_config.children_rule_statement()
    return rule_statement


class TestSpecShape:
    """The statement list and the two top-level statement forms."""

    def test_empty_spec(self) -> None:
        assert list(_parse("").children_statement()) == []

    def test_comments_only(self) -> None:
        assert list(_parse("// a comment\n// another\n").children_statement()) == []

    def test_leading_and_trailing_whitespace(self) -> None:
        spec = _parse("\n\n  rule x { transparent; }\n\n")
        (statement,) = spec.children_statement()
        assert _identifier(statement.child_rule_config().child_rule_name()) == "x"

    def test_multiple_rule_blocks_keep_order(self) -> None:
        spec = _parse("rule a { transparent; }\nrule b { flatten; }\n")
        names = [_identifier(s.child_rule_config().child_rule_name()) for s in spec.children_statement()]
        assert names == ["a", "b"]

    def test_empty_rule_block(self) -> None:
        spec = _parse("rule a { }\n")
        (statement,) = spec.children_statement()
        assert list(statement.child_rule_config().children_rule_statement()) == []

    def test_several_statements_in_one_block(self) -> None:
        spec = _parse("rule number { type: i64; transparent; }\n")
        (statement,) = spec.children_statement()
        rule_statements = list(statement.child_rule_config().children_rule_statement())
        assert len(rule_statements) == 2
        assert rule_statements[0].maybe_type_stmt() is not None
        assert rule_statements[1].maybe_transparent_stmt() is not None

    def test_comment_between_statements(self) -> None:
        spec = _parse("rule a {\n  // why\n  transparent;\n}\n")
        (statement,) = spec.children_statement()
        (rule_statement,) = statement.child_rule_config().children_rule_statement()
        assert rule_statement.maybe_transparent_stmt() is not None

    def test_rule_keyword_needs_whitespace_before_the_name(self) -> None:
        assert _parse_fails("rulex { transparent; }\n")


class TestOptionStatements:
    def test_true_option(self) -> None:
        spec = _parse("option cst = true;\n")
        (statement,) = spec.children_statement()
        option = statement.child_option_stmt()
        assert _identifier(option.child_key()) == "cst"
        assert option.child_value().maybe_true() is not None

    def test_false_option(self) -> None:
        option = next(iter(_parse("option cst = false;\n").children_statement())).child_option_stmt()
        value = option.child_value()
        assert value.maybe_false() is not None
        assert value.maybe_true() is None

    def test_string_option(self) -> None:
        option = next(iter(_parse('option prefix = "app";\n').children_statement())).child_option_stmt()
        string = option.child_value().child_string()
        assert _text(string.child_value()) == '"app"'

    def test_option_keyword_needs_whitespace_before_the_key(self) -> None:
        assert _parse_fails("optioncst = true;\n")


class TestRuleStatements:
    """One case per ``rule_statement`` alternative."""

    def test_builtin_type(self) -> None:
        statement = _only_rule_statement("rule number { type: i64; }\n")
        spec = statement.child_type_stmt().child_spec()
        assert _identifier(spec.child_builtin()) == "i64"
        assert spec.maybe_custom() is None

    def test_custom_type(self) -> None:
        statement = _only_rule_statement(
            'rule money { type: custom(rust_type: "myapp::Money", py_type: "myapp.money.Money"); }\n'
        )
        custom = statement.child_type_stmt().child_spec().child_custom()
        args = [(_identifier(a.child_key()), _text(a.child_value())) for a in custom.children_arg()]
        assert args == [("rust_type", '"myapp::Money"'), ("py_type", '"myapp.money.Money"')]

    def test_custom_type_trailing_comma(self) -> None:
        statement = _only_rule_statement('rule money { type: custom(rust_type: "M",); }\n')
        custom = statement.child_type_stmt().child_spec().child_custom()
        assert [_identifier(a.child_key()) for a in custom.children_arg()] == ["rust_type"]

    def test_custom_type_needs_at_least_one_argument(self) -> None:
        assert _parse_fails("rule money { type: custom(); }\n")

    def test_bool(self) -> None:
        statement = _only_rule_statement("rule boolean { bool: true; }\n")
        assert _identifier(statement.child_bool_stmt().child_truthy()) == "true"

    def test_transparent(self) -> None:
        assert _only_rule_statement("rule identifier { transparent; }\n").maybe_transparent_stmt() is not None

    def test_text_from(self) -> None:
        statement = _only_rule_statement("rule string_literal { text_from: content; }\n")
        assert _identifier(statement.child_text_from_stmt().child_label()) == "content"

    def test_key(self) -> None:
        statement = _only_rule_statement("rule setting { key: key; }\n")
        assert _identifier(statement.child_key_stmt().child_label()) == "key"
        assert statement.child_key_stmt().maybe_multi() is None

    def test_key_multi(self) -> None:
        statement = _only_rule_statement("rule setting { key: key multi; }\n")
        assert _identifier(statement.child_key_stmt().child_label()) == "key"
        assert statement.child_key_stmt().maybe_multi() is not None

    def test_fold_left(self) -> None:
        fold = _only_rule_statement("rule expr { fold_left: op; }\n").child_fold_stmt()
        assert fold.child_dir().maybe_left() is not None
        assert _identifier(fold.child_op()) == "op"

    def test_fold_right(self) -> None:
        fold = _only_rule_statement("rule expr { fold_right: op; }\n").child_fold_stmt()
        assert fold.child_dir().maybe_right() is not None
        assert fold.child_dir().maybe_left() is None

    def test_flatten(self) -> None:
        assert _only_rule_statement("rule schedule { flatten; }\n").maybe_flatten_stmt() is not None

    def test_whole_rule_custom(self) -> None:
        statement = _only_rule_statement('rule blob { custom(rust: "app::Blob", python: "app.Blob"); }\n')
        args = [
            (_identifier(a.child_key()), _text(a.child_value())) for a in statement.child_custom_stmt().children_arg()
        ]
        assert args == [("rust", '"app::Blob"'), ("python", '"app.Blob"')]

    def test_name(self) -> None:
        statement = _only_rule_statement("rule cfg { name: Configuration; }\n")
        assert _identifier(statement.child_name_stmt().child_new_name()) == "Configuration"

    def test_variant(self) -> None:
        variant = _only_rule_statement("rule expr { variant Alt2: Application; }\n").child_variant_stmt()
        assert _identifier(variant.child_selector()) == "Alt2"
        assert _identifier(variant.child_new_name()) == "Application"

    def test_variant_keyword_needs_whitespace_before_the_selector(self) -> None:
        assert _parse_fails("rule expr { variantAlt2: Application; }\n")

    def test_field_rename(self) -> None:
        field = _only_rule_statement("rule server_def { field setting { name: settings; } }\n").child_field_stmt()
        assert _identifier(field.child_label()) == "setting"
        (field_statement,) = field.children_field_statement()
        assert _identifier(field_statement.child_name_stmt().child_new_name()) == "settings"

    def test_empty_field_block(self) -> None:
        field = _only_rule_statement("rule server_def { field setting { } }\n").child_field_stmt()
        assert list(field.children_field_statement()) == []

    def test_field_keyword_needs_whitespace_before_the_label(self) -> None:
        assert _parse_fails("rule r { fieldsetting { name: settings; } }\n")

    def test_sum(self) -> None:
        assert _only_rule_statement("rule entity { sum; }\n").maybe_sum_stmt() is not None

    def test_product(self) -> None:
        assert _only_rule_statement("rule entity { product; }\n").maybe_product_stmt() is not None


@pytest.mark.parametrize(
    "sidecar",
    [
        """
        rule identifier     { transparent; }
        rule number         { type: i64; transparent; }
        rule string_literal { text_from: content; transparent; }
        rule boolean        { bool: true; transparent; }
        rule metric_type    { transparent; }
        rule setting        { key: key; }
        rule server_def     { field setting { name: settings; } }
        rule config         { field stanza  { name: stanzas; } }
        rule metric_def     { field type    { name: metric_kind; } }
        """,
        """
        rule expr       { fold_left: op; }
        rule term       { fold_left: op; }
        rule add_op     { transparent; }
        rule mul_op     { transparent; }
        rule paren_expr { transparent; }
        rule number     { type: i64; transparent; }
        """,
        """
        rule schedule  { flatten; }
        rule time_unit { transparent; }
        rule task_def  { field setting { name: settings; } }
        """,
    ],
)
def test_worked_example_sidecars_parse(sidecar: str) -> None:
    spec = _parse(sidecar)
    assert list(spec.children_statement())


def _config(text: str) -> ast_config.AstConfig:
    return ast_config.parse_ast_config_text(text)


def _block(text: str) -> ast_config.RuleBlock:
    (block,) = _config(text).rule_blocks
    return block


def _statement(text: str) -> ast_config.RuleStatement:
    (statement,) = _block(text).statements
    return statement


class TestConfigShape:
    """The top level of the mapped model: options, rule blocks, and their order."""

    def test_empty_text(self) -> None:
        config = _config("")
        assert config.options == ()
        assert config.rule_blocks == ()

    def test_whitespace_only_text(self) -> None:
        assert _config("\n  \n") == ast_config.AstConfig(options=(), rule_blocks=())

    def test_comments_only(self) -> None:
        assert _config("// nothing to shape\n").rule_blocks == ()

    def test_rule_blocks_keep_source_order(self) -> None:
        config = _config("rule b { transparent; }\nrule a { flatten; }\n")
        assert [block.rule_name for block in config.rule_blocks] == ["b", "a"]

    def test_statements_keep_source_order(self) -> None:
        block = _block("rule number { name: Num; type: i64; transparent; }\n")
        assert [type(statement).__name__ for statement in block.statements] == [
            "NameStmt",
            "TypeStmt",
            "TransparentStmt",
        ]

    def test_repeated_statements_are_all_kept(self) -> None:
        # Duplicates are a validation concern; the model records each one so both can be
        # reported against their own span.
        block = _block("rule x { sum; sum; }\n")
        assert len(block.statements) == 2

    def test_empty_rule_block(self) -> None:
        assert _block("rule x { }\n").statements == ()

    def test_rule_name_span_covers_the_name(self) -> None:
        block = _block("rule server_def { transparent; }\n")
        assert block.rule_name_span.text() == "server_def"

    def test_parse_failure_raises(self) -> None:
        with pytest.raises(ast_config.AstConfigError, match="parse failed"):
            _config("rule x { bogus; }\n")


class TestOptions:
    def test_true_option(self) -> None:
        (option,) = _config("option cst = true;\n").options
        assert (option.key, option.value) == ("cst", True)

    def test_false_option(self) -> None:
        (option,) = _config("option cst = false;\n").options
        assert option.value is False

    def test_string_option(self) -> None:
        (option,) = _config('option prefix = "app";\n').options
        assert option.value == "app"

    def test_options_keep_source_order(self) -> None:
        config = _config("option cst = true;\noption other = false;\n")
        assert [option.key for option in config.options] == ["cst", "other"]

    def test_key_span_covers_the_key(self) -> None:
        (option,) = _config("option cst = true;\n").options
        assert option.key_span.text() == "cst"


class TestStatementMapping:
    """One case per ``rule_statement`` form."""

    def test_builtin_type(self) -> None:
        statement = _statement("rule number { type: i64; }\n")
        assert isinstance(statement, ast_config.TypeStmt)
        spec = statement.spec
        assert isinstance(spec, ast_config.BuiltinTypeSpec)
        assert spec.name == "i64"

    def test_custom_type(self) -> None:
        statement = _statement(
            'rule money { type: custom(rust_type: "myapp::Money", py_parse: "myapp.money.parse"); }\n'
        )
        assert isinstance(statement, ast_config.TypeStmt)
        spec = statement.spec
        assert isinstance(spec, ast_config.CustomTypeSpec)
        assert [(arg.key, arg.value) for arg in spec.args] == [
            ("rust_type", "myapp::Money"),
            ("py_parse", "myapp.money.parse"),
        ]

    def test_custom_type_arg_span_covers_the_entry(self) -> None:
        statement = _statement('rule money { type: custom(rust_type: "M"); }\n')
        assert isinstance(statement, ast_config.TypeStmt)
        spec = statement.spec
        assert isinstance(spec, ast_config.CustomTypeSpec)
        assert spec.args[0].span.text() == 'rust_type: "M"'

    def test_bool(self) -> None:
        statement = _statement("rule boolean { bool: true; }\n")
        assert isinstance(statement, ast_config.BoolStmt)
        assert statement.truthy_label == "true"
        assert statement.label_span.text() == "true"

    def test_transparent(self) -> None:
        assert isinstance(_statement("rule identifier { transparent; }\n"), ast_config.TransparentStmt)

    def test_text_from(self) -> None:
        statement = _statement("rule string_literal { text_from: content; }\n")
        assert isinstance(statement, ast_config.TextFromStmt)
        assert statement.label == "content"

    def test_key(self) -> None:
        statement = _statement("rule setting { key: name; }\n")
        assert isinstance(statement, ast_config.KeyStmt)
        assert statement.label == "name"

    def test_fold_left(self) -> None:
        statement = _statement("rule expr { fold_left: op; }\n")
        assert isinstance(statement, ast_config.FoldStmt)
        assert statement.direction is ast_config.FoldDirection.LEFT
        assert statement.op_label == "op"

    def test_fold_right(self) -> None:
        statement = _statement("rule expr { fold_right: op; }\n")
        assert isinstance(statement, ast_config.FoldStmt)
        assert statement.direction is ast_config.FoldDirection.RIGHT

    def test_flatten(self) -> None:
        assert isinstance(_statement("rule schedule { flatten; }\n"), ast_config.FlattenStmt)

    def test_whole_rule_custom(self) -> None:
        statement = _statement('rule blob { custom(rust: "app::Blob", python: "app.Blob"); }\n')
        assert isinstance(statement, ast_config.CustomStmt)
        assert [(arg.key, arg.value) for arg in statement.args] == [("rust", "app::Blob"), ("python", "app.Blob")]

    def test_name(self) -> None:
        statement = _statement("rule cfg { name: Configuration; }\n")
        assert isinstance(statement, ast_config.NameStmt)
        assert statement.new_name == "Configuration"
        assert statement.name_span.text() == "Configuration"

    def test_variant(self) -> None:
        statement = _statement("rule expr { variant Alt2: Application; }\n")
        assert isinstance(statement, ast_config.VariantStmt)
        assert (statement.selector, statement.new_name) == ("Alt2", "Application")
        assert statement.selector_span.text() == "Alt2"

    def test_field_rename(self) -> None:
        statement = _statement("rule server_def { field setting { name: settings; } }\n")
        assert isinstance(statement, ast_config.FieldStmt)
        assert statement.label == "setting"
        (rename,) = statement.statements
        assert rename.new_name == "settings"

    def test_empty_field_block(self) -> None:
        statement = _statement("rule server_def { field setting { } }\n")
        assert isinstance(statement, ast_config.FieldStmt)
        assert statement.statements == ()

    def test_sum(self) -> None:
        assert isinstance(_statement("rule entity { sum; }\n"), ast_config.SumStmt)

    def test_product(self) -> None:
        assert isinstance(_statement("rule entity { product; }\n"), ast_config.ProductStmt)


class TestStringLiterals:
    def test_quotes_are_stripped(self) -> None:
        (option,) = _config('option prefix = "";\n').options
        assert option.value == ""

    @pytest.mark.parametrize(
        ("literal", "expected"),
        [
            (r"\"", '"'),
            (r"\\", "\\"),
            (r"\n", "\n"),
            (r"\t", "\t"),
            (r"\r", "\r"),
        ],
    )
    def test_escapes(self, literal: str, expected: str) -> None:
        (option,) = _config(f'option prefix = "a{literal}b";\n').options
        assert option.value == f"a{expected}b"

    def test_unknown_escape_is_an_error(self) -> None:
        with pytest.raises(ast_config.AstConfigError) as excinfo:
            _config(r'option prefix = "a\qb";')
        message = str(excinfo.value)
        assert "unknown escape '\\q'" in message
        assert "At line 1, column 19:" in message  # the caret points at the backslash

    def test_every_bad_escape_is_reported_together(self) -> None:
        with pytest.raises(ast_config.AstConfigError) as excinfo:
            _config('rule number { custom(rust: "a\\q", python: "b\\z"); }')
        message = str(excinfo.value)
        assert message.startswith("2 error(s) in .fltkast config:")
        assert "unknown escape '\\q'" in message
        assert "unknown escape '\\z'" in message


class TestWorkedExampleSidecars:
    """Worked example sidecar, mapped end to end."""

    SIDECAR = """
        rule identifier     { transparent; }
        rule number         { type: i64; transparent; }
        rule string_literal { text_from: content; transparent; }
        rule boolean        { bool: true; transparent; }
        rule setting        { key: key; }
        rule server_def     { field setting { name: settings; } }
        """

    def test_every_block_maps(self) -> None:
        config = _config(self.SIDECAR)
        assert [block.rule_name for block in config.rule_blocks] == [
            "identifier",
            "number",
            "string_literal",
            "boolean",
            "setting",
            "server_def",
        ]

    def test_type_and_transparent_share_a_block(self) -> None:
        config = _config(self.SIDECAR)
        number = next(block for block in config.rule_blocks if block.rule_name == "number")
        kinds = [type(statement) for statement in number.statements]
        assert kinds == [ast_config.TypeStmt, ast_config.TransparentStmt]


# --- Validation against a grammar -------------------------------------------------------

GRAMMAR_TEXT = r"""
config      := , stanza* ;
stanza      := server_def | metric_def ;
server_def  := "server" : name:identifier , "{" , setting* , "}" , ;
setting     := key:identifier , "=" , value:number , ";" , ;
metric_def  := "metric" : name:identifier , ":" , type:metric_type , ";" , ;
metric_type := counter:"counter" | gauge:"gauge" ;
tri_state   := yes:"yes" | no:"no" | maybe:"maybe" ;
two_words   := yes:"yes" | yes:"y" | no:"no" ;
one_word    := yes:"yes" | yes:"y" ;
identifier  := name:/[a-z_][a-z0-9_]*/ ;
number      := val:/-?[0-9]+/ ;
padded      := val:/[0-9]+/ . sign:/[+-]/? ;
hidden      := shown:/[a-z]+/ . gone:%/[0-9]+/ ;
entry       := name:/[a-z]+/ , "=" , value:number , ";" , ;
task_def    := "task" : name:identifier , schedule? , "{" , setting* , "}" , ;
schedule    := "every" : interval:number . unit:time_unit ;
time_unit   := sec:"s" | min:"m" ;
expr        := term:number , (op:plus_op , term:number)* ;
plus_op     := plus:"+" ;
lit_key     := k:"@" , v:number ;
marker      := %"(" . %number . %")" ;
alias_a     := "@" . inner:number ;
loop_a      := "a" . inner:loop_b ;
loop_b      := "b" . inner:loop_a ;
"""

TRANSPARENT_IDENTIFIER = "rule identifier { transparent; }"

PY_ONLY = [ast_config.Backend.PYTHON]
RUST_ONLY = [ast_config.Backend.RUST]

CUSTOM_TYPE_ARGS = (
    'rust_type: "app::Money", rust_parse: "app::parse", rust_unparse: "app::render", '
    'py_type: "app.Money", py_parse: "app.parse", py_unparse: "app.render"'
)


@functools.cache
def _grammar() -> gsm.Grammar:
    """The test grammar, processed exactly as the AST model's input is."""
    context = create_default_context()
    return gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(parse_grammar(GRAMMAR_TEXT), context))


def _resolve(text: str, backends: list[ast_config.Backend] | None = None) -> ast_config.ResolvedAstConfig:
    return ast_config.load_ast_config(text, _grammar(), backends if backends is not None else ast_config.ALL_BACKENDS)


def _rule(text: str, rule_name: str = "number") -> ast_config.ResolvedRule:
    return _resolve(text).for_rule(rule_name)


def _errors(text: str, backends: list[ast_config.Backend] | None = None) -> str:
    with pytest.raises(ast_config.AstConfigError) as excinfo:
        _resolve(text, backends)
    return str(excinfo.value)


class TestGrammarIndex:
    def test_rule_labels(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert index.rules["setting"].labels == frozenset({"key", "value"})

    def test_sub_expression_labels_are_included(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert index.rules["expr"].labels == frozenset({"term", "op"})

    def test_unlabeled_invocation_carries_its_rule_name(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert "setting" in index.rules["server_def"].labels

    def test_trivia_rules_are_marked(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert index.rules[gsm.TRIVIA_RULE_NAME].is_trivia
        assert not index.rules["setting"].is_trivia


class TestResolution:
    """A valid sidecar resolves to the per-rule record the AST model consumes."""

    def test_empty_text(self) -> None:
        resolved = _resolve("")
        assert resolved.rules == {}
        assert resolved.cst_backpointers is False

    def test_unconfigured_rule_gets_defaults(self) -> None:
        rule = _resolve("rule number { transparent; }").for_rule("setting")
        assert rule == ast_config.ResolvedRule(rule_name="setting")

    def test_transparent(self) -> None:
        assert _rule("rule number { transparent; }").transparent is True

    def test_builtin_coercion(self) -> None:
        assert _rule("rule number { type: i64; }").coercion == ast_config.BuiltinScalar(name="i64")

    def test_custom_coercion(self) -> None:
        coercion = _rule(f"rule number {{ type: custom({CUSTOM_TYPE_ARGS}); }}").coercion
        assert isinstance(coercion, ast_config.CustomScalar)
        assert coercion.entry("py_parse") == "app.parse"
        assert coercion.entry("rust_type") == "app::Money"

    def test_bool(self) -> None:
        assert _rule("rule metric_type { bool: counter; }", "metric_type").bool_truthy == "counter"

    def test_text_from(self) -> None:
        assert _rule("rule number { text_from: val; }").text_from == "val"

    def test_key(self) -> None:
        assert _rule(
            f"rule setting {{ key: key; }}\n{TRANSPARENT_IDENTIFIER}", "setting"
        ).key == ast_config.ResolvedKey(label="key")

    def test_key_multi(self) -> None:
        """``multi`` is the same statement, accumulating instead of refusing a repeated key."""
        rule = _rule(f"rule setting {{ key: key multi; }}\n{TRANSPARENT_IDENTIFIER}", "setting")
        assert rule.key == ast_config.ResolvedKey(label="key", multi=True)

    def test_fold(self) -> None:
        rule = _rule("rule expr { fold_right: op; }", "expr")
        assert rule.fold == ast_config.Fold(direction=ast_config.FoldDirection.RIGHT, op_label="op")

    def test_flatten(self) -> None:
        assert _rule("rule schedule { flatten; }", "schedule").flatten is True

    def test_whole_rule_custom(self) -> None:
        rule = _rule('rule number { custom(rust: "app::Num", python: "app.Num"); }')
        assert rule.custom is not None
        assert (rule.custom.entry("rust"), rule.custom.entry("python")) == ("app::Num", "app.Num")

    def test_type_rename(self) -> None:
        assert _rule("rule number { name: Numeral; }").type_name == "Numeral"

    def test_variant_renames(self) -> None:
        rule = _rule("rule stanza { variant ServerDef: Server; variant MetricDef: Metric; }", "stanza")
        assert rule.variant_names == {"ServerDef": "Server", "MetricDef": "Metric"}

    def test_field_renames(self) -> None:
        rule = _rule("rule server_def { field setting { name: settings; } }", "server_def")
        assert rule.field_names == {"setting": "settings"}

    def test_field_block_without_a_rename(self) -> None:
        rule = _rule("rule server_def { field setting { } }", "server_def")
        assert rule.field_names == {}

    @pytest.mark.parametrize(
        ("statement", "shape"),
        [("sum;", ast_config.Shape.SUM), ("product;", ast_config.Shape.PRODUCT), ("name: Entity;", None)],
    )
    def test_shape_override(self, statement: str, shape: ast_config.Shape | None) -> None:
        assert _rule(f"rule stanza {{ {statement} }}", "stanza").shape is shape

    def test_several_statements_in_one_block(self) -> None:
        rule = _rule("rule number { type: i64; transparent; name: Numeral; }")
        assert (rule.transparent, rule.type_name) == (True, "Numeral")
        assert rule.coercion == ast_config.BuiltinScalar(name="i64")

    def test_cst_option_on(self) -> None:
        assert _resolve("option cst = true;").cst_backpointers is True

    def test_cst_option_off(self) -> None:
        assert _resolve("option cst = false;").cst_backpointers is False

    def test_cst_option_defaults_off(self) -> None:
        assert _resolve("rule number { transparent; }").cst_backpointers is False

    def test_worked_example_sidecar(self) -> None:
        resolved = _resolve(
            """
            rule identifier  { transparent; }
            rule number      { type: i64; transparent; }
            rule metric_type { transparent; }
            rule setting     { key: key; }
            rule server_def  { field setting { name: settings; } }
            rule config      { field stanza  { name: stanzas; } }
            rule metric_def  { field type    { name: metric_kind; } }
            """
        )
        assert set(resolved.rules) == {
            "identifier",
            "number",
            "metric_type",
            "setting",
            "server_def",
            "config",
            "metric_def",
        }
        assert resolved.for_rule("metric_def").field_names == {"type": "metric_kind"}


class TestRuleBlockErrors:
    def test_unknown_rule(self) -> None:
        assert "unknown grammar rule 'nope'" in _errors("rule nope { transparent; }")

    def test_trivia_rule(self) -> None:
        assert "is a trivia rule" in _errors(f"rule {gsm.TRIVIA_RULE_NAME} {{ transparent; }}")

    def test_duplicate_rule_block(self) -> None:
        assert "duplicate `rule number` block" in _errors("rule number { transparent; }\nrule number { flatten; }")

    def test_offenses_are_reported_together(self) -> None:
        message = _errors("rule nope { transparent; }\nrule alsonope { flatten; }")
        assert message.startswith("2 error(s) in .fltkast config:")

    def test_offense_points_at_the_offending_token(self) -> None:
        assert "At line 1, column 6:" in _errors("rule nope { transparent; }")


class TestStatementErrors:
    @pytest.mark.parametrize(
        "statements",
        ["type: i64; type: u8;", "sum; sum;", "transparent; transparent;", "fold_left: op; fold_right: op;"],
    )
    def test_duplicate_statements(self, statements: str) -> None:
        assert "duplicate `" in _errors(f"rule expr {{ {statements} }}")

    @pytest.mark.parametrize(
        ("statements", "expected"),
        [
            ("type: i64; bool: val;", "`bool:` conflicts with `type:`"),
            ("type: i64; fold_left: val;", "`fold_left:/fold_right:` conflicts with `type:`"),
            ("type: i64; flatten;", "`flatten;` conflicts with `type:`"),
            ("transparent; flatten;", "`flatten;` conflicts with `transparent;`"),
            ("transparent; key: val;", "`key:` conflicts with `transparent;`"),
            # A `key:` only ever acts at a collection use site, which `flatten;` refuses.
            ("flatten; key: val;", "`key:` conflicts with `flatten;`"),
            ("sum; product;", "`product;` conflicts with `sum;`"),
        ],
    )
    def test_conflicting_statements(self, statements: str, expected: str) -> None:
        assert expected in _errors(f"rule number {{ {statements} }}")

    def test_custom_rule_conflicts_with_everything(self) -> None:
        message = _errors('rule number { custom(rust: "a::B", python: "a.B"); transparent; }')
        assert "conflicts with `custom(...)`" in message
        assert "a custom rule gets no generated type to shape" in message

    @pytest.mark.parametrize(
        ("rule_name", "statement"),
        [
            ("number", "bool: nope;"),
            ("number", "text_from: nope;"),
            ("number", "key: nope;"),
            ("expr", "fold_left: nope;"),
            ("number", "field nope { name: other; }"),
        ],
    )
    def test_unknown_label(self, rule_name: str, statement: str) -> None:
        message = _errors(f"rule {rule_name} {{ {statement} }}")
        assert f"names 'nope', but rule {rule_name!r} has no item with that label" in message

    def test_duplicate_field_block(self) -> None:
        message = _errors("rule server_def { field setting { } field setting { name: settings; } }")
        assert "duplicate `field setting` block" in message

    def test_duplicate_rename_in_a_field_block(self) -> None:
        message = _errors("rule server_def { field setting { name: settings; name: other; } }")
        assert "duplicate `name:` statement in `field setting`" in message

    def test_duplicate_variant_selector(self) -> None:
        message = _errors("rule stanza { variant ServerDef: Server; variant ServerDef: Other; }")
        assert "duplicate `variant ServerDef:` statement" in message


class TestTypeStatementErrors:
    def test_unknown_builtin(self) -> None:
        message = _errors("rule number { type: int; }")
        assert "unknown builtin type 'int'" in message
        assert "i64" in message

    @pytest.mark.parametrize("builtin", ["i8", "u64", "f32", "uuid", "decimal"])
    def test_known_builtins(self, builtin: str) -> None:
        assert _rule(f"rule number {{ type: {builtin}; }}").coercion == ast_config.BuiltinScalar(name=builtin)

    def test_unknown_custom_entry(self) -> None:
        message = _errors(f'rule number {{ type: custom({CUSTOM_TYPE_ARGS}, go_type: "x"); }}')
        assert "unknown `type: custom(...)` entry 'go_type'" in message

    def test_duplicate_custom_entry(self) -> None:
        message = _errors(f'rule number {{ type: custom({CUSTOM_TYPE_ARGS}, py_type: "again"); }}')
        assert "duplicate `type: custom(...)` entry 'py_type'" in message

    def test_missing_entries_for_a_generated_backend(self) -> None:
        message = _errors('rule number { type: custom(py_type: "app.Money"); }', PY_ONLY)
        assert "missing the python entries py_parse, py_unparse" in message

    def test_entries_for_an_ungenerated_backend_may_be_omitted(self) -> None:
        text = 'rule number { type: custom(py_type: "app.Money", py_parse: "app.parse", py_unparse: "app.render"); }'
        assert isinstance(_resolve(text, PY_ONLY).for_rule("number").coercion, ast_config.CustomScalar)
        assert "missing the rust entries" in _errors(text, RUST_ONLY)

    def test_whole_rule_custom_missing_entry(self) -> None:
        message = _errors('rule number { custom(python: "app.Num"); }')
        assert "missing the rust entries rust" in message

    def test_whole_rule_custom_unknown_entry(self) -> None:
        message = _errors('rule number { custom(rust: "a::B", python: "a.B", java: "a.B"); }')
        assert "unknown `custom(...)` entry 'java'" in message

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("Money", "it must name a module and an attribute"),
            ("app..Money", "every dot-separated component must be a Python identifier"),
            ("app.class.Money", "every dot-separated component must be a Python identifier"),
            ("app.mo-ney.Money", "every dot-separated component must be a Python identifier"),
        ],
    )
    def test_unusable_python_path(self, path: str, expected: str) -> None:
        message = _errors(f'rule number {{ custom(rust: "a::B", python: "{path}"); }}')
        assert "entry 'python' in `rule number` is not a usable Python path" in message
        assert expected in message

    def test_unusable_python_path_in_a_type_coercion(self) -> None:
        text = 'rule number { type: custom(py_type: "Money", py_parse: "app.parse", py_unparse: "app.render"); }'
        assert "entry 'py_type' in `rule number` is not a usable Python path" in _errors(text, PY_ONLY)

    def test_a_bad_path_is_not_also_reported_as_missing(self) -> None:
        """The entry is there; only its shape is wrong, so one typo yields one error."""
        message = _errors('rule number { custom(python: "Money"); }', PY_ONLY)
        assert message.startswith("1 error(s)")

    def test_rust_paths_are_not_checked_as_python_paths(self) -> None:
        assert _rule('rule number { custom(rust: "a::B", python: "a.B"); }').custom is not None


class TestRenameErrors:
    @pytest.mark.parametrize("name", ["class", "__hidden", "self"])
    def test_unusable_type_name(self, name: str) -> None:
        assert f"{name!r} cannot be a generated type name" in _errors(f"rule number {{ name: {name}; }}")

    def test_unusable_variant_name(self) -> None:
        assert "cannot be a generated variant name" in _errors("rule stanza { variant ServerDef: class; }")

    @pytest.mark.parametrize("name", ["span", "text", "value", "cst", "from_cst", "to_cst"])
    def test_reserved_field_name(self, name: str) -> None:
        message = _errors(f"rule server_def {{ field setting {{ name: {name}; }} }}")
        assert f"{name!r} cannot be a generated field name because generated nodes carry that member" in message

    @pytest.mark.parametrize("name", ["class", "__hidden", "self"])
    def test_unusable_field_name(self, name: str) -> None:
        message = _errors(f"rule server_def {{ field setting {{ name: {name}; }} }}")
        assert f"{name!r} cannot be a generated field name" in message


class TestShapeIndex:
    """The per-rule shape facts the compatibility checks are decided against."""

    @pytest.mark.parametrize(
        ("rule_name", "shape"),
        [
            ("metric_type", gshape.RuleShape.ENUM),
            ("number", gshape.RuleShape.TERMINAL),
            ("padded", gshape.RuleShape.TERMINAL),
            ("stanza", gshape.RuleShape.SUM),
            ("setting", gshape.RuleShape.PRODUCT),
            ("config", gshape.RuleShape.PRODUCT),
        ],
    )
    def test_rule_shape(self, rule_name: str, shape: gshape.RuleShape) -> None:
        assert ast_config.build_grammar_index(_grammar()).rules[rule_name].shape is shape

    def test_label_index_records_arity_and_kinds(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        key = index.rules["setting"].label_index["key"]
        assert key.arity is ce.ArityClass.REQUIRED_SINGLE
        assert key.kinds == frozenset({"identifier"})
        assert key.rule_kinds == frozenset({"identifier"})

    def test_label_index_distinguishes_regex_from_literal(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert index.rules["number"].label_index["val"].kinds == frozenset({ast_config.TEXT_KIND})
        assert index.rules["plus_op"].label_index["plus"].kinds == frozenset({ast_config.LITERAL_KIND})

    def test_collection_label_arity(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        assert index.rules["server_def"].label_index["setting"].arity is ce.ArityClass.COLLECTION

    def test_alternative_arities_are_per_alternative(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        arities = index.rules["stanza"].alternative_arities
        assert [sorted(alternative) for alternative in arities] == [["server_def"], ["metric_def"]]

    def test_use_sites_record_every_reference(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        sites = {(site.rule_name, site.label, site.arity) for site in index.use_sites["setting"]}
        assert ("server_def", "setting", ce.ArityClass.COLLECTION) in sites
        assert ("task_def", "setting", ce.ArityClass.COLLECTION) in sites

    def test_optional_use_site_arity(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        (site,) = index.use_sites["schedule"]
        assert (site.rule_name, site.arity) == ("task_def", ce.ArityClass.OPTIONAL_SINGLE)

    def test_trivia_rules_carry_no_shape_analysis(self) -> None:
        index = ast_config.build_grammar_index(_grammar())
        trivia = index.rules[gsm.TRIVIA_RULE_NAME]
        assert trivia.is_trivia
        assert trivia.label_index == {}


class TestShapeCompatibility:
    """Annotations accepted on the shapes they apply to."""

    @pytest.mark.parametrize("rule_name", ["number", "metric_type", "config"])
    def test_transparent_on_a_legal_shape(self, rule_name: str) -> None:
        assert _rule(f"rule {rule_name} {{ transparent; }}", rule_name).transparent is True

    def test_type_combines_with_text_from(self) -> None:
        """A coercion parses the redirected text, so the two annotations compose."""
        rule = _rule("rule padded { type: i64; text_from: val; }", "padded")
        assert (rule.coercion, rule.text_from) == (ast_config.BuiltinScalar(name="i64"), "val")

    def test_text_from_a_required_single_label(self) -> None:
        assert _rule("rule padded { text_from: val; }", "padded").text_from == "val"

    def test_bool_may_name_either_alternative(self) -> None:
        """The named label maps to ``true``; the other one is ``false``, whichever comes first."""
        assert _rule("rule metric_type { bool: gauge; }", "metric_type").bool_truthy == "gauge"

    def test_key_naming_a_text_field(self) -> None:
        assert _rule("rule entry { key: name; }", "entry").key == ast_config.ResolvedKey(label="name")

    def test_key_through_an_integer_coercion(self) -> None:
        text = "rule setting { key: key; }\nrule identifier { transparent; type: u32; }"
        assert _rule(text, "setting").key == ast_config.ResolvedKey(label="key")

    def test_fold_on_the_precedence_level_shape(self) -> None:
        assert _rule("rule expr { fold_left: op; }", "expr").fold is not None

    def test_flatten_on_a_single_arity_wrapper(self) -> None:
        assert _rule("rule schedule { flatten; }", "schedule").flatten is True

    def test_transparent_chain_that_bottoms_out(self) -> None:
        resolved = _resolve("rule alias_a { transparent; }\nrule number { transparent; }")
        assert resolved.for_rule("alias_a").transparent is True

    def test_shape_override_on_a_multi_alternative_rule(self) -> None:
        assert _rule("rule stanza { product; }", "stanza").shape is ast_config.Shape.PRODUCT

    def test_variant_rename_on_a_sum(self) -> None:
        assert _rule("rule stanza { variant ServerDef: Server; }", "stanza").variant_names

    def test_variant_rename_on_an_enum_shaped_rule(self) -> None:
        assert _rule("rule metric_type { variant Counter: Count; }", "metric_type").variant_names

    def test_variant_rename_on_a_fold_rule(self) -> None:
        """A fold classifies as a product but still has ``Operand``/``Binary`` variants."""
        rule = _rule("rule expr { fold_left: op; variant Operand: Atom; }", "expr")
        assert rule.variant_names == {"Operand": "Atom"}

    def test_field_rename_on_a_product(self) -> None:
        assert _rule("rule setting { field key { name: name; } }", "setting").field_names

    @pytest.mark.parametrize(
        "sidecar",
        [
            f"""
            {TRANSPARENT_IDENTIFIER}
            rule number      {{ type: i64; transparent; }}
            rule metric_type {{ transparent; }}
            rule setting     {{ key: key; }}
            rule server_def  {{ field setting {{ name: settings; }} }}
            rule config      {{ field stanza  {{ name: stanzas; }} }}
            """,
            """
            rule expr    { fold_left: op; }
            rule plus_op { transparent; }
            rule number  { type: i64; transparent; }
            """,
            """
            rule schedule  { flatten; }
            rule time_unit { transparent; }
            rule task_def  { field setting { name: settings; } }
            """,
        ],
    )
    def test_worked_example_sidecars_validate(self, sidecar: str) -> None:
        assert _resolve(sidecar).rules


class TestShapeErrors:
    """Every annotation rejected against the shape it does not apply to."""

    def test_type_needs_a_terminal_only_rule(self) -> None:
        message = _errors("rule setting { type: i64; }")
        assert "`type:` applies only to a terminal-only rule" in message
        assert "rule 'setting' is product" in message

    def test_text_from_needs_a_terminal_only_rule(self) -> None:
        assert "`text_from:` applies only to a terminal-only rule" in _errors("rule setting { text_from: key; }")

    def test_text_from_needs_a_required_single_label(self) -> None:
        message = _errors("rule padded { text_from: sign; }")
        assert "`text_from:` needs a label that occurs exactly once" in message
        assert "'sign' in rule 'padded' is optional_single" in message

    def test_text_from_rejects_a_suppressed_label(self) -> None:
        message = _errors("rule hidden { text_from: gone; }")
        assert "`text_from:` names 'gone', which is suppressed in rule 'hidden'" in message
        assert "contributes no child to read" in message

    def test_bool_needs_an_enum_shaped_rule(self) -> None:
        message = _errors("rule number { bool: val; }")
        assert "`bool:` applies only to an enum-shaped rule" in message
        assert "rule 'number' is terminal-only" in message

    def test_bool_needs_exactly_two_variants(self) -> None:
        message = _errors("rule tri_state { bool: yes; }")
        assert "`bool:` needs a rule with exactly two variants" in message
        assert "has 3 (maybe, no, yes)" in message

    def test_bool_counts_variants_rather_than_alternatives(self) -> None:
        """Alternatives sharing a label are equivalent spellings of one value, so they count once."""
        assert _rule("rule two_words { bool: yes; }", "two_words").bool_truthy == "yes"

    def test_bool_rejects_a_rule_whose_spellings_are_all_one_value(self) -> None:
        """Two alternatives, but only one variant: nothing would ever render ``False``."""
        message = _errors("rule one_word { bool: yes; }")
        assert "`bool:` needs a rule with exactly two variants" in message
        assert "has 1 (yes)" in message

    def test_transparent_rejects_a_sum(self) -> None:
        assert "rule 'stanza' is a sum" in _errors("rule stanza { transparent; }")

    def test_transparent_rejects_a_multi_field_product(self) -> None:
        message = _errors("rule setting { transparent; }")
        assert "needs a product rule with exactly one field" in message
        assert "has 2: key, value" in message

    def test_transparent_rejects_a_label_free_product(self) -> None:
        """Every item suppressed, so there is no payload to erase the marker node to."""
        message = _errors("rule marker { transparent; }")
        assert "needs a product rule with exactly one field" in message
        assert "has 0: (none)" in message

    def test_transparent_rejects_a_fold_rule(self) -> None:
        message = _errors("rule expr { fold_left: op; transparent; }")
        assert "cannot apply to the fold rule 'expr'" in message

    def test_transparent_cycle(self) -> None:
        message = _errors("rule loop_a { transparent; }\nrule loop_b { transparent; }")
        assert "`transparent;` forms a cycle: loop_a -> loop_b -> loop_a" in message

    def test_key_needs_a_product_rule(self) -> None:
        assert "`key:` applies only to a product rule" in _errors("rule number { key: val; }")

    def test_key_needs_a_required_single_field(self) -> None:
        message = _errors("rule server_def { key: setting; }")
        assert "`key:` needs a field that occurs exactly once" in message
        assert "'setting' in rule 'server_def' is collection" in message

    def test_key_multi_needs_a_required_single_field_too(self) -> None:
        """`multi` alters what a key holds, not what may be one, so the arity rule is unchanged."""
        message = _errors("rule server_def { key: setting multi; }")
        assert "`key:` needs a field that occurs exactly once" in message
        assert "'setting' in rule 'server_def' is collection" in message

    def test_key_multi_is_still_a_singular_statement(self) -> None:
        message = _errors("rule setting { key: key multi; key: value multi; }")
        assert "duplicate `key:` statement in `rule setting`" in message

    def test_key_multi_still_conflicts_with_transparent(self) -> None:
        message = _errors("rule setting { transparent; key: key multi; }")
        assert "`key:` conflicts with `transparent;`" in message

    def test_key_rejects_a_node_typed_field(self) -> None:
        message = _errors("rule setting { key: key; }")
        assert "the `key:` field 'key' of rule 'setting' has a node type" in message
        assert "mark the referenced rule `transparent;`" in message

    def test_key_rejects_a_labeled_literal_field(self) -> None:
        """There is no referenced rule to mark transparent: the field is a literal's position."""
        message = _errors("rule lit_key { key: k; }")
        assert "the `key:` field 'k' of rule 'lit_key' carries a literal's position rather than text" in message
        assert "every element would share one key" in message
        assert "transparent" not in message

    def test_key_rejects_a_custom_scalar_field(self) -> None:
        text = f"rule setting {{ key: key; }}\nrule identifier {{ transparent; type: custom({CUSTOM_TYPE_ARGS}); }}"
        message = _errors(text)
        assert "resolves to a `type: custom(...)` type, which cannot key a map" in message

    def test_key_rejects_a_float(self) -> None:
        message = _errors("rule setting { key: key; }\nrule identifier { transparent; type: f64; }")
        assert "resolves to 'f64'" in message
        assert "must be a string or one of" in message

    def test_fold_needs_a_single_alternative_rule(self) -> None:
        message = _errors("rule stanza { fold_left: server_def; }")
        assert "needs a single-alternative rule" in message
        assert "has 2 alternatives" in message

    def test_fold_needs_exactly_two_labels(self) -> None:
        message = _errors("rule task_def { fold_left: name; }")
        assert "a fold rule carries exactly two labels" in message
        assert "carries 3: name, schedule, setting" in message

    def test_fold_operator_must_repeat(self) -> None:
        message = _errors("rule setting { fold_left: key; }")
        assert "the fold operator 'key' must be repeatable" in message
        assert "the fold operand 'value' must occur one or more times" in message

    def test_flatten_needs_a_product_rule(self) -> None:
        message = _errors("rule metric_type { flatten; }")
        assert "`flatten;` applies only to a product rule" in message
        assert "rule 'metric_type' is enum-shaped" in message

    def test_flatten_rejects_a_collection_use_site(self) -> None:
        message = _errors("rule setting { flatten; }")
        assert "it is used as a collection at label 'setting' of rule" in message

    def test_flatten_cycle(self) -> None:
        message = _errors("rule loop_a { flatten; }\nrule loop_b { flatten; }")
        assert "`flatten;` forms a cycle: loop_a -> loop_b -> loop_a" in message

    def test_shape_override_needs_two_alternatives(self) -> None:
        message = _errors("rule setting { sum; }")
        assert "`sum;` chooses between the two multi-alternative forms" in message
        assert "rule 'setting' has a single alternative" in message

    def test_shape_override_rejects_an_enum_shaped_rule(self) -> None:
        assert "`product;` cannot apply to enum-shaped rule 'metric_type'" in _errors("rule metric_type { product; }")

    @pytest.mark.parametrize(
        ("rule_name", "shape"),
        [("setting", "product"), ("number", "terminal-only"), ("config", "product")],
    )
    def test_variant_rename_needs_a_shape_with_variants(self, rule_name: str, shape: str) -> None:
        message = _errors(f"rule {rule_name} {{ variant Alt1: Other; }}")
        assert "`variant Alt1:` renames a variant of a sum, an enum-shaped rule or a fold" in message
        assert f"but rule {rule_name!r} is {shape}" in message

    def test_variant_rename_follows_a_product_override(self) -> None:
        """The override is what the model applies, so it is what placement is judged against."""
        message = _errors("rule stanza { product; variant ServerDef: Server; }")
        assert "`variant ServerDef:` renames a variant" in message
        assert "rule 'stanza' is product" in message

    @pytest.mark.parametrize("rule_name", ["number", "metric_type"])
    def test_field_rename_needs_a_shape_with_fields(self, rule_name: str) -> None:
        message = _errors(f"rule {rule_name} {{ field val {{ name: v; }} }}")
        assert f"`field val` renames a field, but rule {rule_name!r} is" in message
        assert "has no fields to rename" in message

    @pytest.mark.parametrize(
        ("statement", "spelling"),
        [("variant ServerDef: Server;", "variant ServerDef:"), ("field server_def { name: s; }", "field server_def")],
    )
    def test_repeatable_statements_conflict_with_custom(self, statement: str, spelling: str) -> None:
        message = _errors(f'rule stanza {{ custom(rust: "a::B", python: "a.B"); {statement} }}')
        assert f"`{spelling}` conflicts with `custom(...)`" in message

    def test_a_custom_rule_skips_shape_checks(self) -> None:
        # `custom(...)` already conflicts with everything else in the block; the shape checks
        # would only pile duplicate complaints onto a rule that gets no generated type at all.
        message = _errors('rule setting { custom(rust: "a::B", python: "a.B"); type: i64; }')
        assert "conflicts with `custom(...)`" in message
        assert "applies only to a terminal-only rule" not in message


class TestOptionErrors:
    def test_unknown_option(self) -> None:
        message = _errors("option prefix = true;")
        assert "unknown option 'prefix'" in message

    def test_duplicate_option(self) -> None:
        assert "duplicate `option cst` statement" in _errors("option cst = true;\noption cst = false;")

    def test_cst_takes_a_boolean(self) -> None:
        assert "takes `true` or `false`, not a string" in _errors('option cst = "yes";')
