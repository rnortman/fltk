"""Labeled literals in the unparse subsystem: text-aware trial matching and its generation check.

A label is a statement about semantic content, so a labeled literal's spellings are the label's
own vocabulary:

- Trial matching accepts a labeled literal's span child only when the child's text is one of the
  label's spellings.  A rival regex under the same label then wins the trial for text no spelling
  matches, instead of the parsed text being replaced by the literal.
- Rendering is unchanged: the grammar's literal text is emitted, so several spellings under one
  label canonicalize to the first — which is the keyword-evolution mechanism.
- One shape is refused at generation time: a label that is always present, carries only literals,
  and covers more than one spelling records a bare position while its author almost certainly
  expected the written word to survive.

Both unparser generators are checked; the Python one behaviorally (its output is executable
here), the Rust one at the emitted-source level (compilation lives in the fixture crate).
"""

from __future__ import annotations

import functools
from typing import Any

import pytest

from fltk import plumbing
from fltk.fegen.pyrt import terminalsrc
from fltk.plumbing_types import ParserResult, UnparserResult
from fltk.unparse.gsm2unparser_rs import RustUnparserGenerator
from fltk.unparse.renderer import RendererConfig

# `( x:"null" | x:/[0-9]+/ )`: a keyword-or-value idiom. The label carries both a literal and a
# regex, so the literal position must decline a child whose text it cannot spell.
RIVAL_GRAMMAR = 'val := ( x:"null" | x:/[0-9]+/ ) . u:word ;\nword := c:/[a-z]+/ ;\n'

# The sequential spelling of the same idiom: an optional literal ahead of the rival regex.
SEQUENCE_GRAMMAR = 'val := x:"null"? . x:/[0-9]+/ . u:word ;\nword := c:/[a-z]+/ ;\n'

# Equivalent spellings under one label, in a rule where the label is not always present: `grey`
# parses, `gray` renders. The keyword-evolution shape, and the correct idiom for synonyms.
SYNONYM_GRAMMAR = 'doc := c:colour ;\ncolour := red:"red" | blue:"blue" | gray:"gray" | gray:"grey" ;\n'

# Equivalent spellings with no label at all: nothing is recorded, so the first spelling renders.
KEYWORD_EVOLUTION_GRAMMAR = 'doc := ( "import" | "use" ) : n:word ;\nword := c:/[a-z]+/ ;\n'

# The refused shape: `v` is always present, carries only literals, and covers two spellings.
ALWAYS_PRESENT_GRAMMAR = 'entry := ( v:"yes" | v:"no" ) : r:word . ";" ;\nword := c:/[a-z]+/ ;\n'

# Two spellings under a label that can be absent: presence is the datum, so this has to keep
# working end to end, not merely generate.
OPTIONAL_SPELLINGS_GRAMMAR = 'entry := ( v:"gray" | v:"grey" )? . n:word ;\nword := c:/[a-z]+/ ;\n'

# A labeled sub-expression: `cst_ergonomics` computes no per-label arity for such a rule, so the
# check has no count to judge and skips it. The offending rule is a *different* one, which is what
# pins the skip as per-rule rather than per-grammar.
SKIPPED_RULE_GRAMMAR = (
    'sub := g:( "a" . "b" ) . ";" ;\nentry := ( v:"yes" | v:"no" ) : r:word . ";" ;\nword := c:/[a-z]+/ ;\n'
)

# The whole grammar's only offending label sits inside a labeled sub-expression, so nothing is
# refused -- the deliberate escape, since judging that shape would newly reject a grammar that
# unparses today.
SKIPPED_OFFENDER_GRAMMAR = 'entry := g:( v:"yes" | v:"no" ) . ";" ;\n'


@functools.cache
def _pipeline(grammar_text: str) -> tuple[ParserResult, UnparserResult]:
    """A parser and an unparser for one grammar, generated once however many tests want them.

    The grammars below repeat across tests, and both generators run codegen plus an ``exec``;
    a generation that *fails* — which is what the refusal tests assert — caches nothing and so
    raises again on every call.
    """
    parser_result = plumbing.generate_parser(plumbing.parse_grammar(grammar_text), capture_trivia=True)
    return parser_result, plumbing.generate_unparser(parser_result.grammar, parser_result.cst_module_name)


def _format(grammar_text: str, text: str, rule: str) -> str:
    """Parse ``text`` and format it back through the generated Python unparser."""
    parser_result, unparser_result = _pipeline(grammar_text)
    parse_result = plumbing.parse_text(parser_result, text, rule)
    assert parse_result.success, parse_result.error_message
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, text, rule)
    return plumbing.render_doc(doc, RendererConfig(max_width=80, indent_width=2))


@functools.cache
def _python_source(grammar_text: str) -> str:
    """The generated Python unparser's own source, where a test reads the emitted check."""
    return plumbing.generate_unparser_source(_pipeline(grammar_text)[0].grammar, "unused_cst_module")


@functools.cache
def _rust_source(grammar_text: str) -> str:
    return RustUnparserGenerator(plumbing.parse_grammar(grammar_text)).generate()


def _python_source_without_a_cst(grammar_text: str) -> str:
    """The Python unparser's source, generated straight from the parsed grammar.

    A labeled sub-expression — the shape whose per-label arity ``cst_ergonomics`` refuses, and so
    the shape the check skips — has no CST at all (``gsm2tree`` asserts on it), so the generation
    check has to be reached without one. It is the same shared predicate either way.
    """
    return plumbing.generate_unparser_source(plumbing.parse_grammar(grammar_text), "unused_cst_module")


class TestRivalLiteralAndRegex:
    """A label carrying both a literal and a regex: the text decides which position takes it."""

    def test_the_regex_branch_renders_its_own_text(self) -> None:
        """Before the text check this rendered ``"nullu"`` — silent data corruption."""
        assert _format(RIVAL_GRAMMAR, "42u", "val") == "42u"

    def test_the_literal_branch_still_renders_the_literal(self) -> None:
        assert _format(RIVAL_GRAMMAR, "nullu", "val") == "nullu"

    def test_the_sequential_spelling_renders_the_regex_alone(self) -> None:
        """Before the text check the optional literal took the child and the unparse failed."""
        assert _format(SEQUENCE_GRAMMAR, "42u", "val") == "42u"

    def test_the_sequential_spelling_renders_both_positions(self) -> None:
        assert _format(SEQUENCE_GRAMMAR, "null42u", "val") == "null42u"

    def test_the_python_backend_checks_the_span_text(self) -> None:
        assert "fltk.unparse.pyrt.literal_span_matches(child, ['null'])" in _python_source(RIVAL_GRAMMAR)

    def test_the_rust_backend_checks_the_span_text(self) -> None:
        assert 'if span.text_str().is_some_and(|t| !matches!(t, "null")) {' in _rust_source(RIVAL_GRAMMAR)


class TestEquivalentSpellings:
    """Several spellings under one label are equivalent: any parses, the first renders."""

    @pytest.mark.parametrize("text", ["gray", "grey"])
    def test_either_spelling_renders_the_canonical_one(self, text: str) -> None:
        assert _format(SYNONYM_GRAMMAR, text, "doc") == "gray"

    def test_an_unrelated_variant_is_untouched(self) -> None:
        assert _format(SYNONYM_GRAMMAR, "blue", "doc") == "blue"

    @pytest.mark.parametrize("text", ["import x", "use x"])
    def test_an_unlabeled_alternation_canonicalizes_too(self, text: str) -> None:
        """Keyword evolution: put the new keyword first, accept both, format existing code to it."""
        assert _format(KEYWORD_EVOLUTION_GRAMMAR, text, "doc") == "import x"

    def test_both_spellings_of_the_label_are_accepted_by_each_position(self) -> None:
        source = _python_source(SYNONYM_GRAMMAR)
        assert source.count("fltk.unparse.pyrt.literal_span_matches(child, ['gray', 'grey'])") == 2

    def test_the_rust_backend_accepts_both_spellings(self) -> None:
        assert _rust_source(SYNONYM_GRAMMAR).count('!matches!(t, "gray" | "grey")') == 2


class TestHandBuiltText:
    """Text no position can spell fails loudly rather than rendering as something else."""

    GRAMMAR = 'entry := v:"null" . u:word ;\nword := c:/[a-z]+/ ;\n'

    def _with_literal_child(self, span: terminalsrc.Span) -> tuple[UnparserResult, Any]:
        """Parse ``"nullu"``, then put ``span`` in the labeled literal's child position."""
        parser_result, unparser_result = _pipeline(self.GRAMMAR)
        parse_result = plumbing.parse_text(parser_result, "nullu", "entry")
        assert parse_result.success, parse_result.error_message
        cst = parse_result.cst
        assert cst is not None
        label, _child = cst.children[0]
        cst.replace_at(0, span, label)
        return unparser_result, cst

    def test_a_span_no_position_accepts_fails_the_unparse(self) -> None:
        """Such a CST used to render as the literal — the wrong text, silently."""
        unparser_result, cst = self._with_literal_child(terminalsrc.Span.with_source(0, 4, "oops"))
        with pytest.raises(ValueError, match="Unparsing failed"):
            plumbing.unparse_cst(unparser_result, cst, "nullu", "entry")

    def test_a_synthesized_sourceless_span_renders_the_literal(self) -> None:
        """The AST's ``to_cst`` path: a literal child carries position only, so text cannot decide."""
        unparser_result, cst = self._with_literal_child(terminalsrc.Span(0, 4))
        doc = plumbing.unparse_cst(unparser_result, cst, "nullu", "entry")
        assert plumbing.render_doc(doc, RendererConfig(max_width=80, indent_width=2)) == "nullu"


class TestAlwaysPresentLiteralLabel:
    """The one refused shape, and everything adjacent to it that stays legal."""

    MESSAGE = "is always present, is carried only by literals, and covers more than one spelling"

    def _generate_python(self, grammar_text: str) -> None:
        _pipeline(grammar_text)

    def test_the_python_backend_refuses_it(self) -> None:
        with pytest.raises(RuntimeError, match=self.MESSAGE) as exc_info:
            self._generate_python(ALWAYS_PRESENT_GRAMMAR)
        message = str(exc_info.value)
        assert "rule 'entry'" in message
        assert "label 'v'" in message
        assert "'yes', 'no'" in message
        assert "remove the label" in message
        assert 'yes:"yes" | no:"no"' in message

    def test_the_rust_backend_refuses_it_with_the_same_message(self) -> None:
        with pytest.raises(RuntimeError, match=self.MESSAGE):
            _rust_source(ALWAYS_PRESENT_GRAMMAR)

    def test_a_label_that_can_be_absent_is_allowed(self) -> None:
        """Presence is the datum there, so several spellings are legitimate."""
        self._generate_python(OPTIONAL_SPELLINGS_GRAMMAR)

    @pytest.mark.parametrize(("text", "expected"), [("greyx", "grayx"), ("grayx", "grayx"), ("x", "x")])
    def test_the_permitted_shape_round_trips(self, text: str, expected: str) -> None:
        """The carve-out has to work, not just generate: either spelling parses, the first renders.

        The optional group is where the allowed set and the zero-occurrence path meet — a wrong
        allowed set for a min-0 group, or the group declining a legitimate child, shows up here
        and nowhere else.
        """
        assert _format(OPTIONAL_SPELLINGS_GRAMMAR, text, "entry") == expected

    def test_a_rule_with_no_per_label_arity_is_skipped_one_rule_at_a_time(self) -> None:
        """A labeled sub-expression exempts *its* rule, never the rest of the grammar."""
        with pytest.raises(RuntimeError, match=self.MESSAGE):
            _python_source_without_a_cst(SKIPPED_RULE_GRAMMAR)

    def test_an_offending_label_inside_a_labeled_sub_expression_is_the_deliberate_escape(self) -> None:
        """No count exists for the label, so the shape cannot be judged and generation proceeds."""
        assert _python_source_without_a_cst(SKIPPED_OFFENDER_GRAMMAR)

    def test_a_label_absent_from_some_alternative_is_allowed(self) -> None:
        self._generate_python(SYNONYM_GRAMMAR)

    def test_one_spelling_is_allowed(self) -> None:
        self._generate_python('entry := v:"yes" . ";" ;\n')

    def test_distinct_labels_are_allowed(self) -> None:
        """The enum-shaped idiom: each value carries its own label."""
        self._generate_python('entry := ( yes:"yes" | no:"no" ) . ";" ;\n')

    def test_unlabeled_spellings_are_allowed(self) -> None:
        self._generate_python(KEYWORD_EVOLUTION_GRAMMAR)

    def test_a_label_mixing_a_literal_with_a_regex_is_allowed(self) -> None:
        self._generate_python(RIVAL_GRAMMAR)

    def test_a_repeated_label_of_one_spelling_is_allowed(self) -> None:
        self._generate_python('entry := v:"," . n:word . v:"," ;\nword := c:/[a-z]+/ ;\n')
