"""Tests for resolve_spacing_specs function."""

from collections import deque

import pytest

from fltk.unparse.combinators import (
    HARDLINE,
    LINE,
    NBSP,
    NIL,
    SOFTLINE,
    AfterSpec,
    BeforeSpec,
    Concat,
    Doc,
    Group,
    HardLine,
    Join,
    Nest,
    SeparatorSpec,
    Text,
)
from fltk.unparse.renderer import Renderer, RendererConfig
from fltk.unparse.resolve_specs import (
    _expand_joins,
    _extract_boundary_specs,
    _has_source_trivia,
    _mutate_consecutive_specs,
    resolve_spacing_specs,
)


def test_problematic_sequence():
    """Test the specific sequence of combinators that drives the resolver crazy."""
    # This is the exact sequence from the error report
    doc = Concat(
        [
            Text("rule"),
            Text("+"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            AfterSpec(LINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Text(";"),
        ]
    )

    # This should not crash or loop forever
    resolved = resolve_spacing_specs(doc)

    # The expected result should have:
    # - Text('rule')
    # - Text('+')
    # - Line (from AfterSpec)
    # - Text(';')
    assert resolved == Concat((Text("rule"), Text("+"), LINE, Text(";")))


def test_multiple_consecutive_separator_specs():
    """Test resolution of multiple consecutive SeparatorSpec nodes."""
    doc = Concat(
        [
            Text("a"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Text("b"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Should collapse to just the text nodes
    assert resolved == Concat((Text("a"), Text("b")))


def test_separator_after_separator_after():
    """Test SeparatorSpec following AfterSpec with other SeparatorSpecs."""
    doc = Concat(
        [
            Text("x"),
            AfterSpec(LINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Text("y"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Should get Line from AfterSpec
    assert resolved == Concat((Text("x"), LINE, Text("y")))


def test_extract_boundary_specs_basic():
    """Test basic extraction of boundary specs."""
    # Test with both leading and trailing specs
    docs = [
        BeforeSpec(LINE),
        BeforeSpec(SOFTLINE),
        Text("content"),
        AfterSpec(LINE),
        AfterSpec(SOFTLINE),
    ]
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    assert leading == [BeforeSpec(LINE), BeforeSpec(SOFTLINE)]
    assert remaining == [Text("content")]
    assert trailing == [AfterSpec(LINE), AfterSpec(SOFTLINE)]


def test_extract_boundary_specs_no_specs():
    """Test extraction when there are no specs."""
    docs: list[Doc] = [Text("a"), Text("b"), Text("c")]
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    assert leading == []
    assert remaining == [Text("a"), Text("b"), Text("c")]
    assert trailing == []


def test_extract_boundary_specs_only_leading():
    """Test extraction with only leading specs."""
    docs = [BeforeSpec(LINE), BeforeSpec(SOFTLINE), Text("content")]
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    assert leading == [BeforeSpec(LINE), BeforeSpec(SOFTLINE)]
    assert remaining == [Text("content")]
    assert trailing == []


def test_extract_boundary_specs_only_trailing():
    """Test extraction with only trailing specs."""
    docs = [Text("content"), AfterSpec(LINE), AfterSpec(SOFTLINE)]
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    assert leading == []
    assert remaining == [Text("content")]
    assert trailing == [AfterSpec(LINE), AfterSpec(SOFTLINE)]


def test_extract_boundary_specs_all_specs():
    """Test extraction when all items are specs."""
    docs = [BeforeSpec(LINE), BeforeSpec(SOFTLINE), AfterSpec(LINE)]
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    # BeforeSpecs should be leading, AfterSpec should be trailing
    assert leading == [BeforeSpec(LINE), BeforeSpec(SOFTLINE)]
    assert remaining == []
    assert trailing == [AfterSpec(LINE)]


def test_extract_boundary_specs_empty_list():
    """Test extraction with empty list."""
    docs = []
    leading, remaining, trailing = _extract_boundary_specs(docs.copy())

    assert leading == []
    assert remaining == []
    assert trailing == []


def test_group_with_boundary_specs():
    """Test resolution with specs at Group boundaries."""
    # Specs inside a Group should be extracted and bubble up
    doc = Concat(
        [
            Text("before"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Group(
                Concat(
                    [
                        BeforeSpec(LINE),
                        Text("inside"),
                        AfterSpec(SOFTLINE),
                    ]
                )
            ),
            SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The BeforeSpec from inside the group should combine with the SeparatorSpec
    # The AfterSpec should also combine with the SeparatorSpec
    assert resolved == Concat(
        (
            Text("before"),
            LINE,  # BeforeSpec combined with SeparatorSpec
            Group(Text("inside")),
            SOFTLINE,  # AfterSpec combined with SeparatorSpec
            Text("after"),
        )
    )


def test_nest_with_boundary_specs():
    """Test resolution with specs at Nest boundaries."""
    doc = Concat(
        [
            Text("before"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Nest(
                content=Concat(
                    [
                        BeforeSpec(SOFTLINE),
                        Text("nested"),
                        AfterSpec(LINE),
                    ]
                ),
                indent=1,
            ),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Specs should be extracted from Nest and resolved with separator
    assert resolved == Concat(
        (
            Text("before"),
            SOFTLINE,  # BeforeSpec from inside nest
            Nest(content=Text("nested"), indent=1),
            LINE,  # AfterSpec combined with SeparatorSpec (LINE wins)
            Text("after"),
        )
    )


def test_nested_group_nest_extraction():
    """Test extraction through multiple levels of nesting."""
    # Group containing Nest containing Concat with specs
    doc = Concat(
        [
            Text("outer"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Group(
                Nest(
                    content=Concat(
                        [
                            BeforeSpec(LINE),
                            BeforeSpec(SOFTLINE),
                            Text("deeply"),
                            Text("nested"),
                            AfterSpec(SOFTLINE),
                            AfterSpec(LINE),
                        ]
                    ),
                    indent=2,
                )
            ),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Text("end"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Specs should bubble up through both Group and Nest
    assert resolved == Concat(
        (
            Text("outer"),
            LINE,  # First BeforeSpec
            Group(Nest(content=Concat((Text("deeply"), Text("nested"))), indent=2)),
            LINE,  # Last AfterSpec
            Text("end"),
        )
    )


def test_multiple_nested_groups():
    """Test extraction with multiple nested groups."""
    # Outer group contains inner group with specs
    doc = Group(
        Concat(
            [
                Text("start"),
                SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
                Group(
                    Concat(
                        [
                            BeforeSpec(LINE),
                            Text("inner"),
                            AfterSpec(SOFTLINE),
                        ]
                    )
                ),
                SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True),
                Text("end"),
            ]
        )
    )

    resolved = resolve_spacing_specs(doc)

    # Specs from inner group should be properly extracted and resolved
    assert resolved == Group(
        Concat(
            (
                Text("start"),
                LINE,  # BeforeSpec from inner group
                Group(Text("inner")),
                SOFTLINE,  # AfterSpec from inner group
                Text("end"),
            )
        )
    )


def test_complex_multilevel_extraction():
    """Test complex case with multiple levels and various specs."""
    # This tests the case the user is concerned about - extracting through
    # multiple levels of group/nest/concat
    doc = Concat(
        [
            Text("a"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Group(
                Concat(
                    [
                        BeforeSpec(LINE),
                        Nest(
                            content=Concat(
                                [
                                    BeforeSpec(SOFTLINE),
                                    Group(
                                        Concat(
                                            [
                                                BeforeSpec(NIL),
                                                Text("content"),
                                                AfterSpec(NIL),
                                            ]
                                        )
                                    ),
                                    AfterSpec(SOFTLINE),
                                ]
                            ),
                            indent=1,
                        ),
                        AfterSpec(LINE),
                    ]
                )
            ),
            SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True),
            Text("b"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # All specs should be properly extracted and resolved
    # The outermost BeforeSpec(LINE) and innermost BeforeSpec(NIL) should merge to LINE
    # The outermost AfterSpec(LINE) wins
    assert resolved == Concat(
        (
            Text("a"),
            LINE,  # Outermost BeforeSpec
            Group(Nest(content=Group(Text("content")), indent=1)),
            LINE,  # Outermost AfterSpec
            Text("b"),
        )
    )


def test_empty_group_with_specs():
    """Test Group that contains only specs."""
    doc = Concat(
        [
            Text("before"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Group(
                Concat(
                    [
                        BeforeSpec(LINE),
                        AfterSpec(SOFTLINE),
                    ]
                )
            ),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Empty group should disappear, specs should be resolved
    assert resolved == Concat(
        (
            Text("before"),
            LINE,  # BeforeSpec
            Group(NIL),  # Empty group
            SOFTLINE,  # AfterSpec
            Text("after"),
        )
    )


def test_consecutive_groups_with_specs():
    """Test consecutive groups each with boundary specs."""
    doc = Concat(
        [
            Group(
                Concat(
                    [
                        Text("first"),
                        AfterSpec(LINE),
                    ]
                )
            ),
            SeparatorSpec(spacing=SOFTLINE, preserved_trivia=None, required=True),
            Group(
                Concat(
                    [
                        BeforeSpec(SOFTLINE),
                        Text("second"),
                    ]
                )
            ),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # AfterSpec and BeforeSpec should merge with the separator
    assert resolved == Concat(
        (
            Group(Text("first")),
            LINE,  # AfterSpec(LINE) wins over SeparatorSpec(SOFTLINE)
            Group(Text("second")),
        )
    )


def test_deeply_nested_empty_structures():
    """Test deeply nested structures that become empty after spec extraction."""
    doc = Concat(
        [
            Text("start"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Group(
                Nest(
                    content=Group(
                        Concat(
                            [
                                BeforeSpec(LINE),
                                AfterSpec(LINE),
                            ]
                        )
                    ),
                    indent=1,
                )
            ),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Text("end"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # Nested empty structures should be preserved but specs extracted
    assert resolved == Concat(
        (
            Text("start"),
            LINE,  # BeforeSpec
            Group(Nest(content=Group(NIL), indent=1)),
            LINE,  # AfterSpec
            Text("end"),
        )
    )


def test_nested_separator_spec_with_outer_spec():
    """Test SeparatorSpec nested inside structure that needs to combine with outer specs."""
    doc = Concat(
        [
            Text("{"),
            AfterSpec(spacing=LINE),
            Nest(
                indent=1,
                content=Concat(
                    docs=[
                        SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                        Text("nested"),
                        SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                    ]
                ),
            ),
            BeforeSpec(spacing=SOFTLINE),
            Text("}"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            LINE,
            Nest(content=Text("nested"), indent=1),
            SOFTLINE,
            Text("}"),
        )
    )


def test_deeply_nested_after_spec_with_separator():
    """Test AfterSpec deeply nested inside Group/Nest that needs to combine with following SeparatorSpec."""
    doc = Concat(
        [
            Group(
                Concat(
                    [
                        Text("use"),
                        SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True),
                        Nest(
                            indent=1,
                            content=Concat(
                                docs=[
                                    SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                                    Text("content"),
                                    Text(";"),
                                    AfterSpec(spacing=LINE),
                                ]
                            ),
                        ),
                    ]
                )
            ),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Text("next"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The AfterSpec inside the nested structure should be extracted and combined
    # with the following SeparatorSpec, resulting in LINE spacing after the Group
    assert resolved == Concat(
        (
            Group(
                Concat(
                    (
                        Text("use"),
                        LINE,  # From the required SeparatorSpec
                        Nest(content=Concat((Text("content"), Text(";"))), indent=1),
                    )
                )
            ),
            LINE,  # AfterSpec extracted and combined with following SeparatorSpec
            Text("next"),
        )
    )


def test_consecutive_before_specs():
    """Test that consecutive BeforeSpec nodes are merged properly."""
    doc = Concat(
        [
            Text("before"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            BeforeSpec(spacing=HardLine()),
            BeforeSpec(spacing=HardLine(blank_lines=1)),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The two BeforeSpecs should be merged first, then combined with SeparatorSpec
    assert resolved == Concat(
        (
            Text("before"),
            HardLine(blank_lines=1),  # Merged BeforeSpecs combined with SeparatorSpec
            Text("after"),
        )
    )


def test_consecutive_after_specs():
    """Test that consecutive AfterSpec nodes are merged properly."""
    doc = Concat(
        [
            Text("before"),
            AfterSpec(spacing=HardLine(blank_lines=1)),
            AfterSpec(spacing=HardLine()),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The two AfterSpecs should be merged, with HardLine(blank_lines=1) winning
    assert resolved == Concat(
        (
            Text("before"),
            HardLine(blank_lines=1),  # Merged AfterSpecs
            Text("after"),
        )
    )


def test_mixed_consecutive_specs():
    """Test consecutive BeforeSpec and AfterSpec combinations."""
    doc = Concat(
        [
            Text("a"),
            AfterSpec(spacing=LINE),
            AfterSpec(spacing=SOFTLINE),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=True),
            BeforeSpec(spacing=SOFTLINE),
            BeforeSpec(spacing=LINE),
            Text("b"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # AfterSpecs should merge to LINE (stronger than SOFTLINE)
    # BeforeSpecs should merge to LINE (stronger than SOFTLINE)
    # Final result should be LINE (from merging After(LINE) and Before(LINE))
    assert resolved == Concat(
        (
            Text("a"),
            LINE,  # Merged result
            Text("b"),
        )
    )


def test_consecutive_specs_inside_group():
    """Test that consecutive specs inside a Group are properly merged."""
    doc = Concat(
        [
            Text("before"),
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Group(
                Concat(
                    [
                        BeforeSpec(spacing=HardLine()),
                        BeforeSpec(spacing=HardLine(blank_lines=1)),
                        Text("content"),
                    ]
                )
            ),
            Text("after"),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The consecutive BeforeSpecs inside the Group should be merged
    assert resolved == Concat(
        (
            Text("before"),
            HardLine(blank_lines=1),  # Merged BeforeSpecs extracted from Group
            Group(Text("content")),
            Text("after"),
        )
    )


def test_consecutive_leading_specs_in_group():
    """Test the exact case from the user's example."""
    # This mirrors the user's exact structure - SeparatorSpec at end of first group,
    # consecutive BeforeSpecs at start of second group
    doc = Concat(
        [
            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
            Group(
                Concat(
                    [
                        Text("extern_type"),
                        SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True),
                        Text("CxxState"),
                        SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                        Text(";"),
                        AfterSpec(spacing=HardLine()),
                        SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                    ]
                )
            ),
            Group(
                Concat(
                    [
                        BeforeSpec(spacing=HardLine()),
                        BeforeSpec(spacing=HardLine(blank_lines=1)),
                        Text("//"),
                        Text(" "),
                        Text("Hello, Cog!"),
                    ]
                )
            ),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The consecutive BeforeSpecs should be merged and combined with the separator
    # from the previous group
    assert resolved == Concat(
        (
            Group(
                Concat(
                    (
                        Text("extern_type"),
                        LINE,
                        Text("CxxState"),
                        Text(";"),
                    )
                )
            ),
            HardLine(blank_lines=1),  # Merged BeforeSpecs combined with extracted SeparatorSpec
            Group(
                Concat(
                    (
                        Text("//"),
                        Text(" "),
                        Text("Hello, Cog!"),
                    )
                )
            ),
        )
    )


@pytest.mark.parametrize(
    ("first", "spacing", "expected"),
    [
        pytest.param(HardLine(), LINE, HardLine(), id="plain_spacing_keeps_hardline"),
        pytest.param(HardLine(), HardLine(blank_lines=2), HardLine(blank_lines=2), id="separator_blank_count"),
        pytest.param(HardLine(blank_lines=1), HardLine(), HardLine(blank_lines=1), id="max_keeps_own_blank"),
        pytest.param(HardLine(), NBSP, HardLine(), id="nbsp_spacing_dropped"),
    ],
)
def test_hardline_before_separator_merges(first: HardLine, spacing: Doc, expected: HardLine):
    """A HardLine followed by a spacing separator is one break with the larger blank count."""
    doc = Concat([first, SeparatorSpec(spacing=spacing, preserved_trivia=None, required=True), Text("x")])

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat((expected, Text("x")))


def test_hardline_before_trivia_separator_keeps_trivia():
    """A separator carrying preserved trivia is not merged into a preceding HardLine."""
    trivia = Concat([Text("// c"), HardLine()])
    doc = Concat([HardLine(), SeparatorSpec(spacing=LINE, preserved_trivia=trivia, required=True), Text("x")])

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat((HardLine(), Text("// c"), HardLine(), Text("x")))


def test_text_newline_before_separator_is_not_inspected():
    """A Text whose value is a newline is token content: the separator resolves on its own."""
    doc = Concat([Text("\n"), SeparatorSpec(spacing=LINE, preserved_trivia=None, required=True)])

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat((Text("\n"), LINE))


# Nest boundary trivia: a Nest keeps the preserved source trivia the generator placed in its
# first or last gap, so the comment takes the nest's indent.


def _comment_sep(content: str = "// c", trivia: Doc | None = None) -> SeparatorSpec:
    """A separator carrying an own-line comment as preserved source trivia."""
    if trivia is None:
        trivia = Concat([HARDLINE, Text(content), HARDLINE])
    return SeparatorSpec(spacing=None, preserved_trivia=trivia, required=False)


def _render(doc: Doc) -> str:
    return Renderer(RendererConfig(indent_width=4)).render(doc)


def _braced(nest_content: Doc, *, before: Doc | None = HARDLINE) -> Doc:
    """`{`, AfterSpec(HARDLINE), Nest(1, content), [BeforeSpec(before)], `}`."""
    docs: list[Doc] = [Text("{"), AfterSpec(HARDLINE), Nest(content=nest_content, indent=1)]
    if before is not None:
        docs.append(BeforeSpec(before))
    docs.append(Text("}"))
    return Concat(docs)


def test_nest_keeps_boundary_comments_first_and_last():
    """Comment trivia as first and last child stays inside the nest; the outer specs are gone."""
    doc = _braced(Concat([_comment_sep(), Text("x"), _comment_sep("// d")]))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(
                content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("x"), HARDLINE, Text("// d"), HARDLINE)),
                indent=1,
            ),
            Text("}"),
        )
    )
    assert _render(resolved) == "{\n    // c\n    x\n    // d\n}"


def test_nest_keeps_leading_boundary_comment():
    """Comment trivia as first child only: the trailing side extracts."""
    doc = _braced(Concat([_comment_sep(), Text("x")]))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (Text("{"), Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("x"))), indent=1), Text("}"))
    )
    assert _render(resolved) == "{\n    // c\n    x}"


def test_nest_keeps_trailing_boundary_comment():
    """Comment trivia as last child only: the leading side extracts."""
    doc = _braced(Concat([Text("x"), _comment_sep()]))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (Text("{"), Nest(content=Concat((Text("x"), HARDLINE, Text("// c"), HARDLINE)), indent=1), Text("}"))
    )
    assert _render(resolved) == "{x\n    // c\n}"


def test_nest_boundary_comment_beside_spacing_separator_is_one_break():
    """A spacing-only separator beside the comment adds no second break and no blank line."""
    doc = _braced(
        Concat([SeparatorSpec(spacing=HARDLINE, preserved_trivia=None, required=False), _comment_sep(), Text("x")]),
        before=None,
    )

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (Text("{"), Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("x"))), indent=1), Text("}"))
    )
    assert _render(resolved) == "{\n    // c\n    x}"


def test_nest_boundary_same_line_comment_invents_no_break():
    """Trivia with no leading break renders on the delimiter's line."""
    trivia = Concat([NBSP, Text("// c"), HARDLINE])
    doc = _braced(
        Concat(
            [
                SeparatorSpec(spacing=HARDLINE, preserved_trivia=None, required=False),
                _comment_sep(trivia=trivia),
                Text("x"),
            ]
        ),
        before=None,
    )

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (Text("{"), Nest(content=Concat((NBSP, Text("// c"), HARDLINE, Text("x"))), indent=1), Text("}"))
    )
    assert _render(resolved) == "{ // c\n    x}"


_NIL_SEP = SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False)


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        pytest.param(
            _braced(Concat([_NIL_SEP, Text("x"), _NIL_SEP])),
            Concat((Text("{"), HARDLINE, Nest(content=Text("x"), indent=1), HARDLINE, Text("}"))),
            id="first_and_last",
        ),
        pytest.param(
            _braced(Concat([_NIL_SEP, Text("x")])),
            Concat((Text("{"), HARDLINE, Nest(content=Text("x"), indent=1), Text("}"))),
            id="first",
        ),
        pytest.param(
            _braced(Concat([Text("x"), _NIL_SEP])),
            Concat((Text("{"), Nest(content=Text("x"), indent=1), HARDLINE, Text("}"))),
            id="last",
        ),
        pytest.param(
            _braced(
                Concat([SeparatorSpec(spacing=HARDLINE, preserved_trivia=None, required=False), _NIL_SEP, Text("x")]),
                before=None,
            ),
            Concat((Text("{"), HARDLINE, Nest(content=Text("x"), indent=1), Text("}"))),
            id="spacing_separator_beside_empty_gap",
        ),
        pytest.param(
            Group(
                Concat(
                    [
                        Text("("),
                        AfterSpec(LINE),
                        Nest(content=Concat([Text("x"), _NIL_SEP, AfterSpec(NBSP), _NIL_SEP]), indent=1),
                        BeforeSpec(LINE),
                        Text(")"),
                    ]
                )
            ),
            Group(Concat((Text("("), Nest(content=Text("x"), indent=1), LINE, Text(")")))),
            id="paren_term_tail",
        ),
    ],
)
def test_nest_trivia_free_boundary_runs_extract_as_today(doc: Doc, expected: Doc):
    """With no preserved trivia every run leaves the nest and merges with the outer specs into one break."""
    assert resolve_spacing_specs(doc) == expected


def test_expand_joins_marks_the_synthetic_separator():
    """Join expansion marks its separator; only source trivia counts as source trivia."""
    expanded = _expand_joins(Join((Text("x"), Text("y")), Text("|")))

    assert expanded == Concat(
        (
            Text("x"),
            SeparatorSpec(spacing=None, preserved_trivia=Text("|"), required=False, join_separator=True),
            Text("y"),
        )
    )
    assert isinstance(expanded, Concat)
    assert not _has_source_trivia([expanded.docs[1]])
    assert _has_source_trivia([_comment_sep()])


def test_nest_join_separator_before_boundary_comment():
    """A Join separator between the content and a comment stays inside with the comment."""
    doc = _braced(Join((Text("x"), _comment_sep()), Text("|")))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(content=Concat((Text("x"), Text("|"), HARDLINE, Text("// c"), HARDLINE)), indent=1),
            Text("}"),
        )
    )


def test_nest_join_separator_alone_extracts_as_today():
    """A Join's synthetic separator in a boundary run is not source trivia and extracts."""
    doc = _braced(Join((NIL, Text("x")), Text("|")))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat((Text("{"), Text("|"), Nest(content=Text("x"), indent=1), Text("}")))


def test_nest_join_separator_beyond_boundary_comment_is_kept():
    """The cut is at the outermost trivia-bearing separator: a Join separator beyond a comment stays."""
    doc = _braced(Join((Text("x"), _comment_sep(), NIL), Text("|")))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(
                content=Concat((Text("x"), Text("|"), HARDLINE, Text("// c"), HARDLINE, Text("|"))),
                indent=1,
            ),
            Text("}"),
        )
    )
    assert _render(resolved) == "{x|\n    // c\n    |}"


def test_nest_join_separator_ahead_of_leading_boundary_comment_is_kept():
    """Leading side: the cut is at the outermost trivia-bearing separator, here a Join's."""
    doc = _braced(Join((NIL, _comment_sep(), Text("x")), Text("|")))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(
                content=Concat((Text("|"), HARDLINE, Text("// c"), HARDLINE, Text("|"), Text("x"))),
                indent=1,
            ),
            Text("}"),
        )
    )
    assert _render(resolved) == "{|\n    // c\n    |x}"


def test_nest_leading_run_keeps_every_spec_after_the_comment_in_order():
    """Leading side: a BeforeSpec and a second comment after the first comment stay, in order.

    Hand-built. Generated code emits the `[comment, BeforeSpec]` prefix (an optional item right
    after the gap); the second comment, whose trivia has no leading break, is not a generated
    shape and is there so that dropping or reordering anything past the first comment shows.
    """
    second = _comment_sep(trivia=Concat([Text("// d"), HARDLINE]))
    doc = _braced(Concat([_comment_sep(), BeforeSpec(NBSP), second, Text("x")]), before=None)

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(
                content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("// d"), HARDLINE, Text("x"))),
                indent=1,
            ),
            Text("}"),
        )
    )
    assert _render(resolved) == "{\n    // c\n    // d\n    x}"


def test_group_boundary_comment_still_extracts():
    """A comment at a Group's boundary leaves the group."""
    doc = Concat([Text("{"), AfterSpec(HARDLINE), Group(Concat([_comment_sep(), Text("x")])), Text("}")])

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat((Text("{"), HARDLINE, Text("// c"), HARDLINE, Group(Text("x")), Text("}")))


def test_group_in_nest_keeps_boundary_comment_in_nest():
    """A Group extracting through an enclosing Nest does not strip the comment out of the Nest."""
    doc = Nest(content=Group(Concat([_comment_sep(), Text("x")])), indent=1)

    resolved = resolve_spacing_specs(doc)

    assert resolved == Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE, Group(Text("x")))), indent=1)


def test_nest_in_group_keeps_boundary_comment():
    doc = Group(Nest(content=Concat([_comment_sep(), Text("x")]), indent=1))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Group(Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("x"))), indent=1))


def test_group_sharing_opening_anchor_with_nest_breaks_on_boundary_comment():
    """`group from after "{" to "}"` beside `nest from after "{" to before "}"`: the group wraps the comment.

    The nest keeps its leading run, so the outer AfterSpec and the BeforeSpec beside `}` are
    standalone and dropped; the comment's HardLine is inside the group, which breaks.
    """
    doc = Concat(
        [
            Text("{"),
            AfterSpec(LINE),
            Group(
                Concat(
                    [
                        Nest(
                            content=Concat(
                                [
                                    _comment_sep(),
                                    Text("y;"),
                                    SeparatorSpec(spacing=LINE, preserved_trivia=None, required=False),
                                    Text("y;"),
                                ]
                            ),
                            indent=1,
                        ),
                        BeforeSpec(LINE),
                        Text("}"),
                    ]
                )
            ),
        ]
    )

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Group(
                Concat(
                    (
                        Nest(
                            content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("y;"), LINE, Text("y;"))),
                            indent=1,
                        ),
                        Text("}"),
                    )
                )
            ),
        )
    )
    assert Renderer(RendererConfig(indent_width=4, max_width=80)).render(resolved) == "{\n    // c\n    y;\n    y;}"


def test_nest_in_nest_keeps_boundary_comment_in_inner_nest():
    doc = Nest(content=Nest(content=Concat([_comment_sep(), Text("x")]), indent=1), indent=1)

    resolved = resolve_spacing_specs(doc)

    assert resolved == Nest(
        content=Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE, Text("x"))), indent=1), indent=1
    )


def test_comment_only_nest_leaf_is_unchanged():
    """A single-child nest content is a leaf and never extracted."""
    resolved = resolve_spacing_specs(Nest(content=_comment_sep(), indent=1))

    assert resolved == Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE)), indent=1)


def test_comment_only_nest_with_second_control_node_keeps_comment():
    resolved = resolve_spacing_specs(Nest(content=Concat([_comment_sep(), BeforeSpec(NIL)]), indent=1))

    assert resolved == Nest(content=Concat((HARDLINE, Text("// c"), HARDLINE)), indent=1)


def test_nest_boundary_comment_keeps_preserved_blank():
    """A preserved blank line before a boundary comment is kept once, not doubled or lost."""
    trivia = Concat([HardLine(blank_lines=1), Text("// c"), HARDLINE])
    doc = _braced(Concat([_comment_sep(trivia=trivia), Text("x")]), before=None)

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(content=Concat((HardLine(blank_lines=1), Text("// c"), HARDLINE, Text("x"))), indent=1),
            Text("}"),
        )
    )
    assert _render(resolved) == "{\n\n    // c\n    x}"


def _paren_term(trivia_sep: SeparatorSpec, before: Doc, *, lead: SeparatorSpec | None = None) -> Doc:
    """fegen's `term` shape: an after-spec and an empty gap follow the trailing comment.

    `lead`, when given, is the nest's first child, ahead of the content.
    """
    return Group(
        Concat(
            [
                Text("("),
                AfterSpec(LINE),
                Nest(
                    content=Concat(
                        [
                            *([lead] if lead is not None else []),
                            Text("x"),
                            trivia_sep,
                            AfterSpec(NBSP),
                            SeparatorSpec(spacing=NIL, preserved_trivia=None, required=False),
                        ]
                    ),
                    indent=1,
                ),
                BeforeSpec(before),
                Text(")"),
            ]
        )
    )


@pytest.mark.parametrize("before", [LINE, HARDLINE], ids=["line", "hardline"])
def test_nest_trailing_comment_drops_spacing_tail(before: Doc):
    """Spacing specs beyond the outermost trivia are dropped: `)` lands at the delimiter column."""
    resolved = resolve_spacing_specs(_paren_term(_comment_sep(), before))

    assert resolved == Group(
        Concat(
            (
                Text("("),
                Nest(content=Concat((Text("x"), HARDLINE, Text("// c"), HARDLINE)), indent=1),
                Text(")"),
            )
        )
    )
    assert _render(resolved) == "(x\n    // c\n)"


def test_nest_trailing_same_line_comment_keeps_source_whitespace():
    trivia = Concat([NBSP, Text("/* c */"), NBSP])
    resolved = resolve_spacing_specs(_paren_term(_comment_sep(trivia=trivia), LINE))

    assert resolved == Group(
        Concat(
            (
                Text("("),
                Nest(content=Concat((Text("x"), NBSP, Text("/* c */"), NBSP)), indent=1),
                Text(")"),
            )
        )
    )
    assert _render(resolved) == "(x /* c */ )"


_LINE_SEP = SeparatorSpec(spacing=LINE, preserved_trivia=None, required=False)


@pytest.mark.parametrize(
    ("trivia_sep", "expected_content", "flat", "broken"),
    [
        pytest.param(
            _comment_sep(trivia=Concat([NBSP, Text("/* c */"), NBSP])),
            Concat((Text("x"), NBSP, Text("/* c */"), NBSP)),
            "( x /* c */ )",
            "(\n    x /* c */ )",
            id="same_line",
        ),
        pytest.param(
            _comment_sep(),
            Concat((Text("x"), HARDLINE, Text("// c"), HARDLINE)),
            "(\n    x\n    // c\n)",
            "(\n    x\n    // c\n)",
            id="own_line",
        ),
    ],
)
def test_nest_trailing_comment_in_broken_group(
    trivia_sep: SeparatorSpec, expected_content: Doc, flat: str, broken: str
):
    """A comment-bearing boundary gap is not a break opportunity: the delimiter lands where the trivia leaves it.

    The leading spacing separator gives the group a soft break after `(`, so at width 8 the group
    breaks; a same-line comment keeps `)` on its line in both modes.
    """
    resolved = resolve_spacing_specs(_paren_term(trivia_sep, LINE, lead=_LINE_SEP))

    assert resolved == Group(Concat((Text("("), LINE, Nest(content=expected_content, indent=1), Text(")"))))
    assert Renderer(RendererConfig(indent_width=4, max_width=80)).render(resolved) == flat
    assert Renderer(RendererConfig(indent_width=4, max_width=8)).render(resolved) == broken


# ---- A source-preserved blank count at a gap flanked by two anchor spacings ----


def _blank_sep(blank_lines: int, *, required: bool = False) -> SeparatorSpec:
    """The separator a generator emits at a gap whose source held `blank_lines` blanks (after the cap)."""
    return SeparatorSpec(
        spacing=HardLine(blank_lines), preserved_trivia=None, required=required, preserved_blank_lines=blank_lines
    )


def _anchored(after: Doc, seps: list[Doc], before: Doc | None) -> Doc:
    """`x`, AfterSpec(after), *seps, [BeforeSpec(before)], `y`."""
    docs: list[Doc] = [Text("x"), AfterSpec(after), *seps]
    if before is not None:
        docs.append(BeforeSpec(before))
    docs.append(Text("y"))
    return Concat(docs)


def test_triple_keeps_preserved_blank_count():
    """Two hard anchors around a separator carrying a preserved count resolve to that count."""
    resolved = resolve_spacing_specs(_anchored(HARDLINE, [_blank_sep(2)], HARDLINE))

    assert resolved == Concat((Text("x"), HardLine(2), Text("y")))
    assert _render(resolved) == "x\n\n\ny"


def test_triple_ignores_configured_blank_spacing():
    """The same spacing without a preserved count is configured, and the anchors' merge wins."""
    sep = SeparatorSpec(spacing=HardLine(2), preserved_trivia=None, required=False)

    resolved = resolve_spacing_specs(_anchored(HARDLINE, [sep], HARDLINE))

    assert resolved == Concat((Text("x"), HARDLINE, Text("y")))


@pytest.mark.parametrize("anchor", [NBSP, SOFTLINE, NIL, LINE], ids=["nbsp", "soft", "nil", "line"])
def test_triple_promotes_preserved_count_over_non_hardline_anchors(anchor: Doc):
    resolved = resolve_spacing_specs(_anchored(anchor, [_blank_sep(1)], anchor))

    assert resolved == Concat((Text("x"), HardLine(1), Text("y")))


def test_triple_with_zero_count_keeps_anchor_merge():
    """A single-newline gap carries no count: `nbsp` anchors still render a space."""
    sep = SeparatorSpec(spacing=HARDLINE, preserved_trivia=None, required=False)

    resolved = resolve_spacing_specs(_anchored(NBSP, [sep], NBSP))

    assert resolved == Concat((Text("x"), NBSP, Text("y")))
    assert _render(resolved) == "x y"


def test_triple_keeps_larger_anchor_blank_count():
    resolved = resolve_spacing_specs(_anchored(HardLine(2), [_blank_sep(1)], HARDLINE))

    assert resolved == Concat((Text("x"), HardLine(2), Text("y")))


_CONFIGURED_BLANK_2 = SeparatorSpec(spacing=HardLine(2), preserved_trivia=None, required=False)


@pytest.mark.parametrize(
    "seps",
    [[_CONFIGURED_BLANK_2, _blank_sep(1)], [_blank_sep(1), _CONFIGURED_BLANK_2]],
    ids=["configured_first", "preserved_first"],
)
def test_consecutive_merge_carries_preserved_count(seps: list[Doc]):
    """A configured blank(2) fused with a preserved 1 keeps the count 1 whichever comes first."""
    merged = _mutate_consecutive_specs(deque(seps))

    assert merged == [
        SeparatorSpec(spacing=HardLine(2), preserved_trivia=None, required=False, preserved_blank_lines=1)
    ]
    assert resolve_spacing_specs(_anchored(HARDLINE, seps, HARDLINE)) == Concat((Text("x"), HardLine(1), Text("y")))
    assert resolve_spacing_specs(_anchored(HARDLINE, seps, None)) == Concat((Text("x"), HardLine(2), Text("y")))


def test_consecutive_merge_takes_larger_preserved_count():
    merged = _mutate_consecutive_specs(deque([_blank_sep(1), _blank_sep(2)]))

    assert merged == [_blank_sep(2)]


@pytest.mark.parametrize(
    "seps",
    [[_comment_sep(), _blank_sep(1)], [_blank_sep(1), _comment_sep()]],
    ids=["trivia_first", "trivia_second"],
)
def test_consecutive_merge_trivia_operand_drops_count(seps: list[Doc]):

    merged = _mutate_consecutive_specs(deque(seps))

    assert merged == [_comment_sep()]


def test_pair_mutators_unchanged_by_preserved_count():
    assert resolve_spacing_specs(_anchored(NBSP, [_blank_sep(1)], None)) == Concat((Text("x"), HardLine(1), Text("y")))
    zero = SeparatorSpec(spacing=HARDLINE, preserved_trivia=None, required=False)
    assert resolve_spacing_specs(_anchored(NBSP, [zero], None)) == Concat((Text("x"), NBSP, Text("y")))


def test_join_drops_preserved_count_at_anchored_gap():
    doc = Join((Text("x"), AfterSpec(HARDLINE), _blank_sep(1), BeforeSpec(HARDLINE), Text("y")), NBSP)

    resolved = resolve_spacing_specs(doc)

    assert _render(resolved) == "x y"


def test_nest_boundary_comment_and_anchored_trailing_blank():
    """A boundary comment's blank and a trailing anchored blank are each kept once."""
    trivia = Concat([HardLine(blank_lines=1), Text("// c"), HARDLINE])
    doc = _braced(Concat([_comment_sep(trivia=trivia), Text("x"), AfterSpec(HARDLINE), _blank_sep(1)]))

    resolved = resolve_spacing_specs(doc)

    assert resolved == Concat(
        (
            Text("{"),
            Nest(content=Concat((HardLine(blank_lines=1), Text("// c"), HARDLINE, Text("x"))), indent=1),
            HardLine(1),
            Text("}"),
        )
    )
    assert _render(resolved) == "{\n\n    // c\n    x\n\n}"


def test_preserved_count_repr():
    assert repr(_blank_sep(1)) == (
        "SeparatorSpec(spacing=HardLine(blank_lines=1), preserved_trivia=None, required=False, preserved_blank_lines=1)"
    )
    assert "preserved_blank_lines" not in repr(_CONFIGURED_BLANK_2)
