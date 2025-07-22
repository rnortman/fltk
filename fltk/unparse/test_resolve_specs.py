"""Tests for resolve_spacing_specs function."""

from fltk.unparse.combinators import (
    LINE,
    NIL,
    SOFTLINE,
    AfterSpec,
    BeforeSpec,
    Concat,
    Doc,
    Group,
    HardLine,
    Nest,
    SeparatorSpec,
    Text,
)
from fltk.unparse.resolve_specs import _extract_boundary_specs, resolve_spacing_specs


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
