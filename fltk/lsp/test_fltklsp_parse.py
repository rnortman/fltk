"""Parse tests for the .fltklsp grammar via its committed generated parser."""

from fltk.fegen.pyrt import errors, terminalsrc
from fltk.lsp.fltklsp_parser import Parser


def _parse(text: str):
    """Parse text against the top rule; assert full consumption, return the CST."""
    terminals = terminalsrc.TerminalSource(text)
    parser = Parser(terminals)
    result = parser.apply__parse_lsp_spec(0)
    if not result or result.pos != len(terminals.terminals):
        formatted = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"parse failed:\n{formatted}"
        raise AssertionError(msg)
    return result.result


def _parse_fails(text: str) -> bool:
    """Return True iff text does not parse to full consumption against the top rule."""
    terminals = terminalsrc.TerminalSource(text)
    parser = Parser(terminals)
    result = parser.apply__parse_lsp_spec(0)
    return not result or result.pos != len(terminals.terminals)


# The worked clockwork example, verbatim from fltklsp-spec.md §4.
WORKED_EXAMPLE = """// clockwork.fltklsp
scope doc: comment;

scope typespec, config_type, signal_type, input_type, output_type, state_type: type;
scope boolean, unit_identifier: constant;
scope string_literal: string;                    // default gets this; explicit for clarity
scope nonnegative_integer, integer, number: number;

rule condition_spec {
    scope "time_since_last_exec", "any_message", "new_message": function.builtin;
}
rule channel_option_publishers {
    scope "single", "multiple", "diagnostics", "bridge_status", "c2c_bridge_status": enumMember;
}
rule clk_generate_target { scope cpp, proto, go_proto, py, nanobind: macro; }

// --- phase 2 ---
rule cog        { def identifier: type.cog;      namespace; }
rule python_cog { def identifier: type.cog;      namespace; }
rule schema     { def identifier: type.schema;   namespace; }
rule enum       { def identifier: type.enum;     namespace; }
rule strong_type{ def identifier: type; }
rule tag        { def identifier: type.tag; }
rule channel    { def identifier: variable.channel; }
rule box        { def identifier: type.box;      namespace; }
rule schema_field { def name: field; }
rule enum_value   { def name: enumMember; }
rule new_stmt     { def identifier: variable; }
rule use_alias    { def alias: type; }

rule expr             { ref identifier: *; }
rule signal_reference { ref identifier: variable.signal; }
"""


def test_worked_clockwork_example_parses():
    cst = _parse(WORKED_EXAMPLE)
    assert cst is not None


def test_empty_file_parses():
    assert _parse("") is not None


def test_whitespace_only_parses():
    assert _parse("\n  \n\t\n") is not None


def test_comments_only_parses():
    cst = _parse("// just a comment\n// another one\n")
    assert cst is not None


# --- individual statement forms ---


def test_global_scope_stmt_parses():
    assert _parse("scope foo: keyword;\n") is not None


def test_global_scope_stmt_multiple_anchors_parses():
    assert _parse("scope foo, bar, baz: type;\n") is not None


def test_global_scope_stmt_literal_anchor_parses():
    assert _parse('scope "single", "multiple": enumMember;\n') is not None


def test_global_scope_stmt_qualified_anchor_parses():
    assert _parse("scope label:mylabel, rule:myrule: keyword;\n") is not None


def test_scope_token_dotted_name_parses():
    assert _parse("scope foo: function.builtin;\n") is not None


def test_scope_token_none_parses():
    assert _parse("scope foo: none;\n") is not None


def test_rule_config_with_scope_parses():
    assert _parse("rule bar {\n  scope baz: type;\n}\n") is not None


def test_rule_config_empty_body_parses():
    assert _parse("rule bar {\n}\n") is not None


def test_def_stmt_parses():
    assert _parse("rule bar {\n  def x: type.cog;\n}\n") is not None


def test_ref_stmt_kinds_parses():
    assert _parse("rule bar {\n  ref x: variable.signal, type;\n}\n") is not None


def test_ref_stmt_wildcard_parses():
    assert _parse("rule bar {\n  ref x: *;\n}\n") is not None


def test_namespace_stmt_parses():
    assert _parse("rule bar {\n  namespace;\n}\n") is not None


# --- grammar-level error cases ---


def test_missing_semicolon_fails():
    assert _parse_fails("scope foo: keyword\n")


def test_missing_scope_token_fails():
    assert _parse_fails("scope foo;\n")


def test_rule_inside_rule_fails():
    assert _parse_fails("rule a {\n  rule b { scope x: type; }\n}\n")


def test_unclosed_rule_body_fails():
    assert _parse_fails("rule bar {\n  scope baz: type;\n")


# --- the label/rule-named-anchor flush-against-colon quirk (design §4.1) ---
#
# An anchor whose *name* is literally `label` or `rule`, written flush against the
# scope-token colon, misparses: the optional qualifier group commits on `label:` and
# does not backtrack (PEG e? success is not undone), so the statement fails shortly
# after. Inserting whitespace before the colon forbids the qualifier group from
# matching (its `.` separators reject whitespace), disambiguating to a plain anchor.


def test_flush_label_named_anchor_fails():
    assert _parse_fails("scope label:comment;\n")


def test_flush_rule_named_anchor_fails():
    assert _parse_fails("scope rule:comment;\n")


def test_spaced_label_named_anchor_parses():
    assert _parse("scope label : comment;\n") is not None


def test_spaced_rule_named_anchor_parses():
    assert _parse("scope rule : comment;\n") is not None
