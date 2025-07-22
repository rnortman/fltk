"""Test for the Group/AfterSpec/SeparatorSpec resolution fix."""

from fltk.unparse.combinators import (
    HARDLINE,
    LINE,
    NIL,
    AfterSpec,
    BeforeSpec,
    Group,
    Nest,
    SeparatorSpec,
    Text,
    concat,
)
from fltk.unparse.resolve_specs import resolve_spacing_specs


def test_group_trailing_afterspec_with_separator():
    """Test that AfterSpec at end of Group is extracted and merged with following SeparatorSpec."""
    # Create the pattern: Group(..., Text(';'), AfterSpec(HardLine)), SeparatorSpec(Nil)
    doc = concat(
        [
            Group(
                concat(
                    [
                        Text("rule"),
                        AfterSpec(LINE),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text(":="),
                        AfterSpec(LINE),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text(";"),
                        AfterSpec(HARDLINE),  # This should be extracted
                    ]
                )
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),  # This should merge with the AfterSpec
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # The resolved doc should have:
    # 1. Group without the trailing AfterSpec
    # 2. The HardLine from the AfterSpec (since SeparatorSpec had Nil spacing)

    expected = concat(
        [
            Group(
                concat(
                    [
                        Text("rule"),
                        LINE,
                        Text(":="),
                        LINE,
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                )
            ),
            HARDLINE,  # The AfterSpec's HardLine should appear here
        ]
    )
    assert resolved == expected


def test_group_leading_beforespec_with_separator():
    """Test that BeforeSpec at start of Group is extracted and merged with preceding SeparatorSpec."""
    # Create the pattern: SeparatorSpec(Nil), Group(BeforeSpec(LINE), Text('rule'), ...)
    doc = concat(
        [
            Text("previous_rule"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),  # This should merge with the BeforeSpec
            Group(
                concat(
                    [
                        BeforeSpec(LINE),  # This should be extracted
                        Text("rule"),
                        Text(":="),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                )
            ),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # The resolved doc should have:
    # 1. Text('previous_rule')
    # 2. The LINE from the BeforeSpec (since SeparatorSpec had Nil spacing)
    # 3. Group without the leading BeforeSpec
    expected = concat(
        [
            Text("previous_rule"),
            LINE,  # The BeforeSpec's LINE should appear here
            Group(
                concat(
                    [
                        Text("rule"),
                        Text(":="),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                )
            ),
        ]
    )
    assert resolved == expected


def test_group_trailing_afterspec_no_separator():
    """Test that AfterSpec at end of Group is removed when no SeparatorSpec follows."""
    doc = concat(
        [
            Group(
                concat(
                    [
                        Text("rule"),
                        Text(";"),
                        AfterSpec(HARDLINE),
                    ]
                )
            ),
            Text("next_rule"),  # No SeparatorSpec, so AfterSpec should be discarded
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The AfterSpec should be removed since there's no SeparatorSpec
    expected = concat(
        [
            Group(
                concat(
                    [
                        Text("rule"),
                        Text(";"),
                    ]
                )
            ),
            Text("next_rule"),
        ]
    )

    assert resolved == expected


def test_group_both_leading_and_trailing_specs():
    """Test that both leading BeforeSpec and trailing AfterSpec are extracted correctly."""
    # Create: SeparatorSpec, Group(BeforeSpec, ..., AfterSpec), SeparatorSpec
    doc = concat(
        [
            Text("previous"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Group(
                concat(
                    [
                        BeforeSpec(LINE),  # Should be extracted
                        Text("rule"),
                        Text(":="),
                        Text("body"),
                        Text(";"),
                        AfterSpec(HARDLINE),  # Should be extracted
                    ]
                )
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Text("next"),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # Should have: Text, LINE (from BeforeSpec), Group, HARDLINE (from AfterSpec), Text
    expected = concat(
        [
            Text("previous"),
            LINE,
            Group(
                concat(
                    [
                        Text("rule"),
                        Text(":="),
                        Text("body"),
                        Text(";"),
                    ]
                )
            ),
            HARDLINE,
            Text("next"),
        ]
    )
    assert resolved == expected


def test_nest_trailing_afterspec_with_separator():
    """Test that AfterSpec at end of Nest is extracted and merged with following SeparatorSpec."""
    # Create the pattern: Nest(..., Text(';'), AfterSpec(HardLine)), SeparatorSpec(Nil)
    doc = concat(
        [
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        AfterSpec(LINE),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text(":="),
                        AfterSpec(LINE),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        SeparatorSpec(NIL, preserved_trivia=None, required=False),
                        Text(";"),
                        AfterSpec(HARDLINE),  # This should be extracted
                    ]
                ),
                indent=4,
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),  # This should merge with the AfterSpec
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # The resolved doc should have:
    # 1. Nest without the trailing AfterSpec
    # 2. The HardLine from the AfterSpec (since SeparatorSpec had Nil spacing)
    expected = concat(
        [
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        LINE,
                        Text(":="),
                        LINE,
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                ),
                indent=4,
            ),
            HARDLINE,  # The AfterSpec's HardLine should appear here
        ]
    )

    # Check the structure
    assert resolved == expected


def test_nest_leading_beforespec_with_separator():
    """Test that BeforeSpec at start of Nest is extracted and merged with preceding SeparatorSpec."""
    # Create the pattern: SeparatorSpec(Nil), Nest(BeforeSpec(LINE), Text('rule'), ...)
    doc = concat(
        [
            Text("previous_rule"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),  # This should merge with the BeforeSpec
            Nest(
                content=concat(
                    [
                        BeforeSpec(LINE),  # This should be extracted
                        Text("rule"),
                        Text(":="),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                ),
                indent=4,
            ),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # The resolved doc should have:
    # 1. Text('previous_rule')
    # 2. The LINE from the BeforeSpec (since SeparatorSpec had Nil spacing)
    # 3. Nest without the leading BeforeSpec
    expected = concat(
        [
            Text("previous_rule"),
            LINE,  # The BeforeSpec's LINE should appear here
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        Text(":="),
                        Text("name"),
                        Text(":"),
                        Text("identifier"),
                        Text(";"),
                    ]
                ),
                indent=4,
            ),
        ]
    )

    # Check the structure
    assert resolved == expected


def test_nest_trailing_afterspec_no_separator():
    """Test that AfterSpec at end of Nest is removed when no SeparatorSpec follows."""
    doc = concat(
        [
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        Text(";"),
                        AfterSpec(HARDLINE),
                    ]
                ),
                indent=4,
            ),
            Text("next_rule"),  # No SeparatorSpec, so AfterSpec should be discarded
        ]
    )

    resolved = resolve_spacing_specs(doc)

    # The AfterSpec should be removed since there's no SeparatorSpec
    expected = concat(
        [
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        Text(";"),
                    ]
                ),
                indent=4,
            ),
            Text("next_rule"),
        ]
    )

    assert resolved == expected


def test_nest_both_leading_and_trailing_specs():
    """Test that both leading BeforeSpec and trailing AfterSpec are extracted correctly."""
    # Create: SeparatorSpec, Nest(BeforeSpec, ..., AfterSpec), SeparatorSpec
    doc = concat(
        [
            Text("previous"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Nest(
                content=concat(
                    [
                        BeforeSpec(LINE),  # Should be extracted
                        Text("rule"),
                        Text(":="),
                        Text("body"),
                        Text(";"),
                        AfterSpec(HARDLINE),  # Should be extracted
                    ]
                ),
                indent=4,
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Text("next"),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # Should have: Text, LINE (from BeforeSpec), Nest, HARDLINE (from AfterSpec), Text
    expected = concat(
        [
            Text("previous"),
            LINE,
            Nest(
                content=concat(
                    [
                        Text("rule"),
                        Text(":="),
                        Text("body"),
                        Text(";"),
                    ]
                ),
                indent=4,
            ),
            HARDLINE,
            Text("next"),
        ]
    )
    assert resolved == expected


def test_group_nest_group_nested():
    """Test nested cases like Group(Nest(Group(...)))."""
    # Create: Group(Nest(Group(BeforeSpec, ..., AfterSpec)))
    doc = concat(
        [
            Text("before"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Group(
                Nest(
                    content=Group(
                        concat(
                            [
                                BeforeSpec(LINE),  # Should be extracted from inner Group
                                Text("inner"),
                                AfterSpec(HARDLINE),  # Should be extracted from inner Group
                            ]
                        )
                    ),
                    indent=4,
                )
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Text("after"),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # Should have: Text, LINE (from BeforeSpec), Group(Nest(Group)), HARDLINE (from AfterSpec), Text
    expected = concat(
        [
            Text("before"),
            LINE,
            Group(
                Nest(
                    content=Group(
                        concat(
                            [
                                Text("inner"),
                            ]
                        )
                    ),
                    indent=4,
                )
            ),
            HARDLINE,
            Text("after"),
        ]
    )
    assert resolved == expected


def test_nest_group_nest_nested():
    """Test nested cases like Nest(Group(Nest(...)))."""
    # Create: Nest(Group(Nest(BeforeSpec, ..., AfterSpec)))
    doc = concat(
        [
            Text("before"),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Nest(
                content=Group(
                    Nest(
                        content=concat(
                            [
                                BeforeSpec(LINE),  # Should be extracted from inner Nest
                                Text("inner"),
                                AfterSpec(HARDLINE),  # Should be extracted from inner Nest
                            ]
                        ),
                        indent=4,
                    )
                ),
                indent=2,
            ),
            SeparatorSpec(NIL, preserved_trivia=None, required=False),
            Text("after"),
        ]
    )

    # Resolve specs
    resolved = resolve_spacing_specs(doc)

    # Should have: Text, LINE (from BeforeSpec), Nest(Group(Nest)), HARDLINE (from AfterSpec), Text
    expected = concat(
        [
            Text("before"),
            LINE,
            Nest(
                content=Group(
                    Nest(
                        content=concat(
                            [
                                Text("inner"),
                            ]
                        ),
                        indent=4,
                    )
                ),
                indent=2,
            ),
            HARDLINE,
            Text("after"),
        ]
    )
    assert resolved == expected
