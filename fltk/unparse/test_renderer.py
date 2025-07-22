"""Tests for the renderer."""

from typing import cast

import pytest

from fltk.unparse.combinators import (
    Doc,
    comment,
    concat,
    group,
    hardline,
    line,
    nbsp,
    nest,
    nil,
    softline,
    text,
)
from fltk.unparse.renderer import Mode, Renderer, RendererConfig


def test_simple_text():
    """Test rendering simple text."""
    renderer = Renderer()
    doc = text("hello world")
    assert renderer.render(doc) == "hello world"


def test_empty_doc():
    """Test rendering empty document."""
    renderer = Renderer()
    doc = nil()
    assert renderer.render(doc) == ""


def test_hardline():
    """Test hard line breaks."""
    renderer = Renderer()
    doc = concat([text("line1"), hardline(), text("line2")])
    assert renderer.render(doc) == "line1\nline2"


def test_hardline_with_blanks():
    """Test hard line breaks with blank lines."""
    renderer = Renderer()
    doc = concat([text("line1"), hardline(2), text("line2")])
    assert renderer.render(doc) == "line1\n\n\nline2"


def test_group_fits():
    """Test group that fits on one line."""
    renderer = Renderer(RendererConfig(max_width=80))
    doc = group(concat([text("short"), line(), text("text")]))
    assert renderer.render(doc) == "short text"


def test_group_breaks():
    """Test group that needs to break."""
    renderer = Renderer(RendererConfig(max_width=10))
    doc = group(concat([text("very"), line(), text("long"), line(), text("text")]))
    expected = "very\nlong\ntext"
    assert renderer.render(doc) == expected


def test_nested_groups():
    """Test nested groups with independent breaking."""
    renderer = Renderer(RendererConfig(max_width=10))  # Changed to force breaking

    # Inner group fits even when outer breaks
    inner = group(concat([text("a"), line(), text("b")]))
    outer = group(concat([text("outer"), line(), inner, line(), text("end")]))

    result = renderer.render(outer)
    # Outer group breaks, inner stays together
    assert result == "outer\na b\nend"


def test_nest_indentation():
    """Test indentation with nest."""
    renderer = Renderer(RendererConfig(indent_width=2))
    doc = concat([text("function {"), nest(1, concat([hardline(), text("body")])), hardline(), text("}")])
    expected = "function {\n  body\n}"
    assert renderer.render(doc) == expected


def test_group_with_nest():
    """Test group with nested indentation."""
    renderer = Renderer(RendererConfig(indent_width=4, max_width=15))  # Reduced to force breaking
    doc = group(
        concat(
            [text("{"), nest(1, concat([line(), text("item1"), text(","), line(), text("item2")])), line(), text("}")]
        )
    )

    # Should break and indent
    expected = "{\n    item1,\n    item2\n}"
    assert renderer.render(doc) == expected


def test_softline():
    """Test soft line (nothing or newline)."""
    renderer = Renderer(RendererConfig(max_width=80))

    # Unbroken - softline produces nothing
    doc = group(concat([text("a"), softline(), text("b")]))
    assert renderer.render(doc) == "ab"

    # Broken - softline produces newline
    renderer2 = Renderer(RendererConfig(max_width=1))
    assert renderer2.render(doc) == "a\nb"


def test_nbsp():
    """Test non-breaking space."""
    renderer = Renderer(RendererConfig(max_width=1))
    doc = group(concat([text("a"), nbsp(), text("b")]))
    # Even when broken, nbsp stays as space
    assert renderer.render(doc) == "a b"


def test_complex_nested():
    """Test complex nested structure."""
    renderer = Renderer(RendererConfig(indent_width=2, max_width=25))  # Reduced to force breaking

    doc = concat(
        [
            text("function foo("),
            group(nest(1, concat([softline(), text("arg1: string,"), line(), text("arg2: number")]))),
            text(") {"),
            nest(1, concat([hardline(), text("return arg1 + arg2;"), nest(1, concat([hardline(), text("deep;")]))])),
            hardline(),
            text("}"),
        ]
    )

    expected = "function foo(\n  arg1: string,\n  arg2: number) {\n  return arg1 + arg2;\n    deep;\n}"
    assert renderer.render(doc) == expected


def test_parent_breaks_before_child():
    """Test that parent groups break before child groups."""
    renderer = Renderer(RendererConfig(max_width=20))

    # Create nested groups where the whole thing doesn't fit,
    # but the inner group alone would fit
    inner = group(concat([text("short"), line(), text("text")]))
    outer = group(concat([text("prefix"), line(), inner, line(), text("suffix")]))

    result = renderer.render(outer)
    # The outer group should break, but inner should stay together
    assert result == "prefix\nshort text\nsuffix"


def test_broken_child_forces_parent_break():
    """Test that a broken child group forces parent to break."""
    renderer = Renderer(RendererConfig(max_width=15))

    # Inner group too long to fit
    inner = group(concat([text("very"), line(), text("long"), line(), text("inner"), line(), text("group")]))
    # Outer group would fit if inner didn't break
    outer = group(concat([text("("), line(), inner, line(), text(")")]))

    result = renderer.render(outer)
    # Both should break because inner must break
    expected = "(\nvery\nlong\ninner\ngroup\n)"
    assert result == expected


def test_multiple_subgroups_algorithm_limitation():
    """Test that proves remaining_width is NOT needed for current algorithm."""
    renderer = Renderer(RendererConfig(max_width=24))

    # Each subgroup individually would fit on a line at current indent (0)
    group1 = group(concat([text("short"), line(), text("one")]))  # "short one" = 9 chars
    group2 = group(concat([text("also"), line(), text("short")]))  # "also short" = 10 chars
    group3 = group(concat([text("tiny")]))  # "tiny" = 4 chars

    # Together: "short one also short tiny" = 25 chars > 24
    # Use soft lines between groups so they can break
    outer = group(
        concat(
            [
                group1,
                line(),  # soft line instead of hard space
                group2,
                line(),  # soft line instead of hard space
                group3,
            ]
        )
    )

    result = renderer.render(outer)

    # Current algorithm tests the ENTIRE formatted result against max_width
    # Since "short onealso shorttiny" would be 23 chars (without spaces),
    # but "short one also short tiny" would be 25 chars, it correctly breaks
    # This proves the algorithm works without needing remaining_width tracking

    # The outer group should break because total exceeds limit
    expected = "short one\nalso short\ntiny"  # Should break at soft lines between groups
    assert result == expected


def test_group_nest_group_indent_behavior():
    """Test that group(nest(group(...))) only applies indent when inner breaks."""
    renderer = Renderer(RendererConfig(indent_width=4, max_width=20))

    # Inner group that fits without breaking
    inner_fits = group(concat([text("fits"), line(), text("inline")]))  # "fits inline" = 11 chars

    # Outer structure: group(nest(inner_group))
    outer_fits = group(nest(2, inner_fits))  # 2 * 4 = 8 spaces indent if breaking

    result_fits = renderer.render(outer_fits)

    # Should have indentation because content is inside a Nest
    assert result_fits == "        fits inline"

    # Now test with inner group that must break (exceed 20 chars)
    inner_breaks = group(
        concat(
            [
                text("this"),
                line(),
                text("definitely"),
                line(),
                text("exceeds"),
                line(),
                text("the"),
                line(),
                text("limit"),
            ]
        )
    )

    outer_breaks = group(nest(2, inner_breaks))

    result_breaks = renderer.render(outer_breaks)

    # Should have indentation on all lines because content is inside a Nest
    expected_breaks = "        this\n        definitely\n        exceeds\n        the\n        limit"
    assert result_breaks == expected_breaks


def test_wadler_lindig_respects_width_constraints():
    """Test that Wadler-Lindig correctly handles mid-line groups and width constraints."""
    renderer = Renderer(RendererConfig(max_width=20))

    # Scenario: We have text + group where total would exceed width limit
    # "long prefix " = 12 chars, leaving only 8 chars for group content
    # Group content "medium text" = 11 chars when flat
    # Total: "long prefix medium text" = 23 chars > 20, should break

    group_content = group(
        concat(
            [
                text("medium"),
                line(),
                text("text"),  # "medium text" = 11 chars
            ]
        )
    )

    doc = concat(
        [
            text("long prefix "),  # 12 chars
            group_content,
        ]
    )

    result = renderer.render(doc)

    # Wadler-Lindig correctly identifies that when the group is reached,
    # only 8 chars remain (20 - 12 = 8), but "medium text" needs 11 chars.
    # So it breaks the group to respect the width constraint.
    expected = "long prefix medium\ntext"

    assert result == expected

    # Verify each line respects the width constraint
    lines = result.split("\n")
    for line_text in lines:
        assert len(line_text) <= 20, f"Line '{line_text}' exceeds width limit of 20"


def test_unbreakable_content_exceeds_width():
    """Test algorithm behavior when content has no break points and exceeds width."""
    renderer = Renderer(RendererConfig(max_width=10))

    # Single long text with no break opportunities
    doc = text("this_is_a_very_long_identifier_with_no_spaces")  # 43 chars > 10

    result = renderer.render(doc)

    # Algorithm should still produce the text even though it violates width
    # This is the expected behavior - better to show content than fail
    assert result == "this_is_a_very_long_identifier_with_no_spaces"
    assert len(result) > 10  # Documents the violation


def test_unbreakable_group_content():
    """Test group with unbreakable content that exceeds remaining width."""
    renderer = Renderer(RendererConfig(max_width=20))

    # Text + group where group has no break points
    unbreakable_group = group(text("unbreakable_long_identifier"))  # 26 chars

    doc = concat(
        [
            text("prefix "),  # 7 chars, leaving 13 chars
            unbreakable_group,  # 26 chars, can't break, exceeds remaining 13
        ]
    )

    result = renderer.render(doc)

    # Should produce the content even though it violates width
    expected = "prefix unbreakable_long_identifier"
    assert result == expected
    assert len(result) > 20  # Documents the violation


def test_nested_groups_with_unbreakable_content():
    """Test nested groups where inner content cannot be broken."""
    renderer = Renderer(RendererConfig(max_width=15))

    # Inner group with unbreakable content
    inner = group(text("very_long_unbreakable_name"))  # 26 chars

    # Outer group that would normally try to break
    outer = group(concat([text("start"), line(), inner, line(), text("end")]))

    result = renderer.render(outer)

    # Even though the inner content can't break and exceeds width,
    # the algorithm should handle it gracefully
    expected = "start\nvery_long_unbreakable_name\nend"
    assert result == expected

    # Verify that some lines exceed the width limit
    lines = result.split("\n")
    exceeded = any(len(line) > 15 for line in lines)
    assert exceeded, "Expected at least one line to exceed width limit"


def test_negative_remaining_width():
    """Test behavior when remaining_width becomes negative."""
    renderer = Renderer(RendererConfig(max_width=10))

    # Start with content that uses up most of the width
    # Then add a group that should be evaluated with negative remaining width
    doc = concat(
        [
            text("0123456789"),  # Exactly 10 chars, uses up all width
            group(
                concat(
                    [
                        text("a"),
                        line(),
                        text("b"),  # Should be evaluated with remaining_width = 0
                    ]
                )
            ),
        ]
    )

    result = renderer.render(doc)

    # Algorithm should handle this gracefully
    # Since remaining_width <= 0, group should break
    expected = "0123456789a\nb"
    assert result == expected


def test_zero_width_edge_case():
    """Test edge case with zero max_width."""
    renderer = Renderer(RendererConfig(max_width=0))

    # Even with zero width, algorithm should not crash
    doc = group(concat([text("a"), line(), text("b")]))

    result = renderer.render(doc)

    # Should break everything since nothing fits in 0 width
    expected = "a\nb"
    assert result == expected


def test_hardline_with_negative_remaining_width():
    """Test hardline behavior when remaining width is exhausted."""
    renderer = Renderer(RendererConfig(max_width=5))

    doc = concat(
        [
            text("12345"),  # Uses up all 5 chars
            hardline(),  # Forces break regardless of remaining width
            text("next"),
        ]
    )

    result = renderer.render(doc)

    # HardLine should always work regardless of remaining width
    expected = "12345\nnext"
    assert result == expected


def test_nil_and_empty_text_with_zero_width():
    """Test that Nil and empty Text are correctly handled with zero width."""
    renderer = Renderer(RendererConfig(max_width=0))

    # Test 1: Group with break points - should break when doesn't fit
    breakable_doc = group(concat([text("a"), line(), text("b")]))
    breakable_result = renderer.render(breakable_doc)
    assert breakable_result == "a\nb", "Should break at line() when width exceeded"

    # Test 2: Group without break points - must violate width constraint
    unbreakable_doc = group(concat([text("a"), nil(), text("b")]))
    unbreakable_result = renderer.render(unbreakable_doc)
    assert unbreakable_result == "ab", "Should violate width when no break points available"

    # Test 3: Only empty content should fit even in width 0
    empty_only_doc = group(concat([nil(), text(""), nil()]))
    empty_only_result = renderer.render(empty_only_doc)
    assert empty_only_result == "", "Empty content should fit in width 0"

    # Test 4: Verify Nil doesn't affect width calculation when mixed with break points
    nil_with_breaks_doc = group(concat([text("a"), nil(), line(), nil(), text("b")]))
    nil_with_breaks_result = renderer.render(nil_with_breaks_doc)
    assert nil_with_breaks_result == "a\nb", "Nil should not affect break decisions"

    # Test 5: Empty text doesn't affect width calculation
    empty_text_with_breaks_doc = group(concat([text("a"), text(""), line(), text(""), text("b")]))
    empty_text_with_breaks_result = renderer.render(empty_text_with_breaks_doc)
    assert empty_text_with_breaks_result == "a\nb", "Empty text should not affect break decisions"


def test_zero_width_detailed_behavior():
    """Detailed test of zero width behavior with various combinators."""
    renderer = Renderer(RendererConfig(max_width=0))

    # Test that empty content fits in zero width
    empty_group = group(concat([nil(), text(""), softline()]))
    result = renderer.render(empty_group)
    # SoftLine in flat mode produces nothing, so this should fit
    assert result == ""

    # Test that any non-empty content breaks with zero width
    non_empty_group = group(concat([text("x")]))
    result2 = renderer.render(non_empty_group)
    # Single character can't fit in width 0, but should still be produced
    assert result2 == "x"


def test_fits_function_behavior():
    """Debug the _fits function behavior directly."""
    renderer = Renderer(RendererConfig(max_width=0))

    # Test empty content
    empty_items = cast(list[tuple[int, Mode, Doc]], [(0, Mode.FLAT, nil())])
    fits_empty = renderer._fits(0, empty_items.copy())
    assert fits_empty, "Nil should fit in width 0"

    # Test single character
    single_char_items = cast(list[tuple[int, Mode, Doc]], [(0, Mode.FLAT, text("x"))])
    fits_single = renderer._fits(0, single_char_items.copy())
    assert not fits_single, "Single char should NOT fit in width 0"

    # Test empty text
    empty_text_items = cast(list[tuple[int, Mode, Doc]], [(0, Mode.FLAT, text(""))])
    fits_empty_text = renderer._fits(0, empty_text_items.copy())
    assert fits_empty_text, "Empty text should fit in width 0"

    # Test the problematic case: "a" + nil() + "b"
    concat_doc = concat([text("a"), nil(), text("b")])
    concat_items = cast(list[tuple[int, Mode, Doc]], [(0, Mode.FLAT, concat_doc)])
    fits_concat = renderer._fits(0, concat_items.copy())
    assert not fits_concat, "Text 'a' + nil() + 'b' should NOT fit in width 0"


def test_exact_width_with_softline_and_nil():
    """Test edge case where content fits exactly, testing SOFTLINE and NIL with zero remaining width."""
    # Set up: "some stuff more" = 15 chars exactly
    renderer = Renderer(RendererConfig(max_width=15))

    # Create the structure: group("some", LINE, "stuff", LINE, "more", group(SOFTLINE, NIL, ""))
    # When flat: "some stuff more" = 4 + 1 + 5 + 1 + 4 = 15 chars exactly
    inner_group = group(concat([softline(), nil(), text("")]))
    outer_group = group(concat([text("some"), line(), text("stuff"), line(), text("more"), inner_group]))

    result = renderer.render(outer_group)

    # Should fit exactly without breaking
    # The algorithm will test the inner group with remaining_width = 0
    # (since "some stuff " = 10 chars, "more" = 4 chars, leaving 1 char for the space)
    # Actually: "some stuff " = 11 chars, leaving 4 chars, "more" = 4 chars, leaving 0
    # Then it tests SOFTLINE and NIL with remaining_width = 0
    expected = "some stuff more"
    assert result == expected
    assert len(result) == 15, f"Expected exactly 15 chars, got {len(result)}"

    # Verify the inner group content (more + SOFTLINE + NIL) fits when evaluated with remaining_width=0
    # SOFTLINE in flat mode produces nothing (0 chars)
    # NIL produces nothing (0 chars)
    # So "more" + SOFTLINE + NIL = 4 + 0 + 0 = 4 chars, which should fit in 4 remaining chars


def test_exact_width_boundary_conditions():
    """Test various boundary conditions around exact width fits."""
    renderer = Renderer(RendererConfig(max_width=10))

    # Test 1: Content that fits exactly
    exact_fit = group(concat([text("1234567890")]))  # Exactly 10 chars
    result1 = renderer.render(exact_fit)
    assert result1 == "1234567890"
    assert len(result1) == 10

    # Test 2: Content one char over
    one_over = group(concat([text("12345678901")]))  # 11 chars
    result2 = renderer.render(one_over)
    assert result2 == "12345678901"  # Should still produce content
    assert len(result2) == 11

    # Test 3: Nested groups with exact boundary
    # "prefix " = 7 chars, leaving 3 chars for inner group
    # Inner group "abc" = 3 chars exactly
    inner = group(concat([text("a"), softline(), text("bc")]))  # "abc" when flat
    outer = group(concat([text("prefix "), inner]))
    result3 = renderer.render(outer)
    assert result3 == "prefix abc"
    assert len(result3) == 10


def test_text_with_newlines_width_calculation():
    """Test that newlines in Text nodes correctly reset column for width calculation."""
    renderer = Renderer(RendererConfig(max_width=10))

    # Text with newline should calculate width correctly
    doc = group(concat([text("line1\nab"), line(), text("xyz")]))
    # "line1" = 5 chars (fits)
    # "\n" resets to column 0
    # "ab" = 2 chars
    # " " (from line()) = 1 char
    # "xyz" = 3 chars
    # Total on last line: 2 + 1 + 3 = 6 chars (fits in width 10)
    result = renderer.render(doc)
    assert result == "line1\nab xyz"


def test_comment_with_newlines_width_calculation():
    """Test that newlines in Comment nodes correctly reset column for width calculation."""
    renderer = Renderer(RendererConfig(max_width=10))

    # Comment with newline should calculate width same as Text for fitting
    doc = group(concat([comment("// a\n// b"), line(), text("xyz")]))
    # "// a" = 4 chars
    # "\n" resets to column 0
    # "// b" = 4 chars
    # " " = 1 char
    # "xyz" = 3 chars
    # Total on last line: 4 + 1 + 3 = 8 chars (fits)
    result = renderer.render(doc)
    assert result == "// a\n// b xyz"


def test_comment_reindentation():
    """Test that Comment nodes get re-indented on newlines."""
    renderer = Renderer(RendererConfig(indent_width=4))

    # Comment inside nest should indent all lines including the first
    doc = nest(2, comment("/*\n * Line 1\n * Line 2\n */"))
    result = renderer.render(doc)
    expected = "        /*\n         * Line 1\n         * Line 2\n         */"
    assert result == expected


def test_text_preserves_exact_formatting():
    """Test that Text nodes preserve exact formatting without re-indentation."""
    renderer = Renderer(RendererConfig(indent_width=4))

    # Text inside nest should be indented starting from first line
    doc = nest(2, text("```\ndef foo():\n    pass\n```"))
    result = renderer.render(doc)
    # First line gets indented, subsequent lines preserve their content exactly
    expected = "        ```\n        def foo():\n            pass\n        ```"
    assert result == expected


def test_comment_empty_lines_no_indent():
    """Test that empty lines in comments don't get indented (no trailing whitespace)."""
    renderer = Renderer(RendererConfig(indent_width=4))

    doc = nest(1, comment("/*\n\n * text\n\n */"))
    result = renderer.render(doc)
    # Empty lines should have no spaces, first line should be indented
    expected = "    /*\n\n     * text\n\n     */"
    assert result == expected

    # Verify no trailing whitespace
    lines = result.split("\n")
    assert lines[1] == ""  # Second line should be completely empty
    assert lines[3] == ""  # Fourth line should be completely empty


def test_mixed_text_and_comment():
    """Test mixing Text and Comment nodes."""
    renderer = Renderer(RendererConfig(max_width=20, indent_width=2))

    doc = concat([text("before"), comment("// comment\n// more"), text("\nafter")])
    result = renderer.render(doc)
    # Text nodes preserve exact formatting, comments do not re-indent at top level
    expected = "before// comment\n// more\nafter"
    assert result == expected


def test_nested_comment_indentation():
    """Test nested comment indentation."""
    renderer = Renderer(RendererConfig(indent_width=2))

    doc = concat([text("{\n"), nest(1, comment("// First\n// Second")), text("\n}")])
    result = renderer.render(doc)
    expected = "{\n  // First\n  // Second\n}"
    assert result == expected


def test_group_with_multiline_comment_breaks():
    """Test that groups containing multiline comments handle breaking correctly."""
    renderer = Renderer(RendererConfig(max_width=15))

    # Group that would fit if comment was single line but breaks due to newline
    doc = group(concat([text("x = "), comment("/* a\n * b */"), text(";")]))
    result = renderer.render(doc)
    # Even though "x = /* a * b */;" might fit, the newline forces the actual width calculation
    expected = "x = /* a\n * b */;"
    assert result == expected


def test_comment_relative_indentation_preserved():
    """Test that relative indentation within comments is preserved."""
    renderer = Renderer(RendererConfig(indent_width=4))

    doc = nest(1, comment("/*\n    indented\n        more indented\n*/"))
    result = renderer.render(doc)
    # Base indent is 4, applied to all lines including first
    expected = "    /*\n        indented\n            more indented\n    */"
    assert result == expected


def test_text_with_multiple_newlines():
    """Test Text nodes with multiple consecutive newlines."""
    renderer = Renderer(RendererConfig(max_width=20))

    doc = group(concat([text("line1\n\n\nline2"), line(), text("end")]))
    result = renderer.render(doc)
    # Multiple newlines are preserved, width calculated from last line
    expected = "line1\n\n\nline2 end"
    assert result == expected


def test_comment_first_line_not_reindented():
    """Test that the first line of a comment is not re-indented."""
    renderer = Renderer(RendererConfig(indent_width=4))

    # Even in a nest, first line starts where it's placed
    doc = concat([text("x = "), nest(1, comment("/* start\n * end */"))])
    result = renderer.render(doc)
    # First line "/* start" appears after "x = ", only continuation is indented
    expected = "x = /* start\n     * end */"
    assert result == expected


def test_break_at_nest_boundaries():
    """Test that breaks at the beginning or end of Nest use correct indentation."""
    renderer = Renderer(RendererConfig(indent_width=4, max_width=20))

    # Break right before end of Nest
    doc = concat(
        [
            text("outer"),
            nest(
                1,
                concat(
                    [
                        hardline(),
                        text("inner"),
                        hardline(),  # This break is at the end of the Nest
                    ]
                ),
            ),
            text("after"),  # This should get outer indentation, not inner
        ]
    )
    result = renderer.render(doc)
    expected = "outer\n    inner\nafter"  # "after" has no indentation (outer level)
    assert result == expected

    # Break right at beginning of Nest
    doc2 = concat(
        [
            text("outer"),
            nest(
                1,
                concat(
                    [
                        hardline(),  # This break is at the start of the Nest
                        text("inner"),
                    ]
                ),
            ),
            hardline(),
            text("after"),
        ]
    )
    result2 = renderer.render(doc2)
    expected2 = "outer\n    inner\nafter"  # "inner" gets the Nest indentation
    assert result2 == expected2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
