"""Regression test for bug #6 (a9d6d16) - Fix bug in line/col error reporting

This test verifies that when errors are reported at positions on the first line
of a source file, the column number calculation doesn't produce negative values
and the line span is correctly calculated.

The bug was in terminalsrc.py in the pos_to_line_col method:

Before fix (buggy code):
    return LineColPos(
        line=idx,
        col=pos - self.line_ends[idx - 1] - 1,  # This causes negative col for first line
        line_span=Span(self.line_ends[idx - 1] + 1, self.line_ends[idx]),  # Wrong span for first line
    )

After fix:
    if idx > 0:
        col = pos - self.line_ends[idx - 1] - 1
        line_span = Span(self.line_ends[idx - 1] + 1, self.line_ends[idx])
    else:
        col = pos
        line_span = Span(0, self.line_ends[0])

The issue occurred because:
1. For positions on the first line (idx == 0), the original code tried to access
   self.line_ends[idx - 1] which is self.line_ends[-1] (last element)
2. This resulted in incorrect column calculations and negative column numbers
3. The line span was also incorrectly calculated for the first line

The specific scenario is:
1. Parse a source file that has multiple lines
2. Report an error at a position on the first line
3. Without fix: column number is negative due to incorrect calculation
4. With fix: column number is correctly calculated as the position value
"""

import logging
from typing import Final

from fltk.fegen.pyrt.terminalsrc import TerminalSource

LOG: Final = logging.getLogger(__name__)


def test_line_col_error_first_line():
    """Test that line/col calculation works correctly for positions on the first line.

    Creates a multi-line source and tests pos_to_line_col for various positions
    on the first line to ensure column numbers are not negative and line spans
    are correctly calculated.

    The bug would cause negative column numbers for positions on the first line
    because the calculation was using self.line_ends[idx - 1] when idx == 0,
    which accesses the last element instead of handling the first line case.
    """

    # Create a multi-line source to trigger the bug
    # Line 0: "hello world"  (positions 0-10, newline at 11)
    # Line 1: "second line"  (positions 12-22, newline at 23)
    # Line 2: "third"        (positions 24-28)
    source_text = "hello world\nsecond line\nthird"
    source = TerminalSource(source_text)

    # Test various positions on the first line
    test_positions_first_line = [0, 1, 5, 10, 11]  # Including the newline position

    for pos in test_positions_first_line:
        LOG.info("Testing position %d on first line", pos)
        result = source.pos_to_line_col(pos)

        # Verify this is recognized as first line
        if result.line != 0:
            msg = f"Position {pos} should be on line 0, got line {result.line}"
            raise AssertionError(msg)

        # The key test: column should NOT be negative (this was the bug)
        if result.col < 0:
            msg = (
                f"Bug detected! Position {pos} on first line produced negative column {result.col}. "
                f"This indicates the original bug where line/col calculation used "
                f"self.line_ends[idx - 1] when idx == 0, accessing the wrong array element."
            )
            raise AssertionError(msg)

        # Column should equal the position for first line
        expected_col = pos
        if result.col != expected_col:
            msg = f"Position {pos} should have column {expected_col}, got {result.col}"
            raise AssertionError(msg)

        # Line span should start at 0 for first line
        if result.line_span.start != 0:
            msg = f"First line span should start at 0, got {result.line_span.start}"
            raise AssertionError(msg)

        # Line span should end at the newline position (11 in this case)
        if result.line_span.end != 11:
            msg = f"First line span should end at 11, got {result.line_span.end}"
            raise AssertionError(msg)

        LOG.info(
            "Position %d: line=%d, col=%d, line_span=(%d,%d) - CORRECT",
            pos,
            result.line,
            result.col,
            result.line_span.start,
            result.line_span.end,
        )

    # Also test a few positions on other lines to ensure we didn't break anything
    test_positions_other_lines = [
        (12, 1, 0),  # First char of second line
        (15, 1, 3),  # "o" in "second"
        (24, 2, 0),  # First char of third line
        (28, 2, 4),  # Last char of third line
    ]

    for pos, expected_line, expected_col in test_positions_other_lines:
        LOG.info("Testing position %d on line %d", pos, expected_line)
        result = source.pos_to_line_col(pos)

        if result.line != expected_line:
            msg = f"Position {pos} should be on line {expected_line}, got line {result.line}"
            raise AssertionError(msg)

        if result.col != expected_col:
            msg = f"Position {pos} should have column {expected_col}, got {result.col}"
            raise AssertionError(msg)

        # Column should never be negative on any line
        if result.col < 0:
            msg = f"Position {pos} produced negative column {result.col}"
            raise AssertionError(msg)

        LOG.info(
            "Position %d: line=%d, col=%d, line_span=(%d,%d) - CORRECT",
            pos,
            result.line,
            result.col,
            result.line_span.start,
            result.line_span.end,
        )


def test_line_col_error_edge_cases():
    """Test edge cases for line/col error reporting.

    Tests various edge cases to ensure the fix works correctly in all scenarios:
    - Single line source
    - Empty lines
    - Source ending with newline
    - Source not ending with newline
    """

    # Test 1: Single line source (no newlines)
    single_line = "hello"
    source = TerminalSource(single_line)

    for pos in range(len(single_line)):
        result = source.pos_to_line_col(pos)

        if result.line != 0:
            msg = f"Single line: position {pos} should be on line 0, got {result.line}"
            raise AssertionError(msg)

        if result.col != pos:
            msg = f"Single line: position {pos} should have column {pos}, got {result.col}"
            raise AssertionError(msg)

        if result.col < 0:
            msg = f"Single line: position {pos} produced negative column {result.col}"
            raise AssertionError(msg)

    LOG.info("Single line source test passed")

    # Test 2: Source with empty lines
    empty_lines_source = "line1\n\nline3"
    source = TerminalSource(empty_lines_source)

    # Test position 0 (first line, first char)
    result = source.pos_to_line_col(0)
    if result.line != 0 or result.col != 0 or result.col < 0:
        msg = f"Empty lines: position 0 failed - line={result.line}, col={result.col}"
        raise AssertionError(msg)

    # Test position 6 (empty line)
    result = source.pos_to_line_col(6)
    if result.col < 0:
        msg = f"Empty lines: position 6 produced negative column {result.col}"
        raise AssertionError(msg)

    LOG.info("Empty lines source test passed")

    # Test 3: Source ending with newline
    newline_end = "line1\nline2\n"
    source = TerminalSource(newline_end)

    result = source.pos_to_line_col(0)
    if result.line != 0 or result.col != 0 or result.col < 0:
        msg = f"Newline end: position 0 failed - line={result.line}, col={result.col}"
        raise AssertionError(msg)

    LOG.info("Source ending with newline test passed")


def test_line_col_comprehensive_first_line():
    """Comprehensive test specifically targeting the first line bug.

    This test specifically exercises the code path that was buggy in the original
    implementation. It creates various source texts and tests every position on
    the first line to ensure none produce negative column numbers.
    """

    test_sources = [
        "a",  # Minimal single character
        "abc",  # Short single line
        "hello world",  # Longer single line
        "first\nsecond",  # Two lines
        "line1\nline2\nline3",  # Three lines
        "x\n\n\n",  # Multiple newlines
        "\nstarts with newline",  # Starts with newline
    ]

    for i, source_text in enumerate(test_sources):
        LOG.info("Testing source %d: %r", i, source_text)
        source = TerminalSource(source_text)

        # Find all positions on the first line
        first_newline_pos = source_text.find("\n")
        if first_newline_pos == -1:
            # No newlines, entire string is first line
            first_line_positions = list(range(len(source_text)))
        else:
            # Positions up to and including the newline
            first_line_positions = list(range(first_newline_pos + 1))

        for pos in first_line_positions:
            result = source.pos_to_line_col(pos)

            # This is the core bug check: column must not be negative
            if result.col < 0:
                msg = (
                    f"REGRESSION DETECTED! Source {i} ({source_text!r}), position {pos} "
                    f"produced negative column {result.col}. This indicates the original "
                    f"line/col calculation bug has returned."
                )
                raise AssertionError(msg)

            # Must be on first line
            if result.line != 0:
                msg = f"Source {i}, position {pos} should be line 0, got {result.line}"
                raise AssertionError(msg)

            # For first line, column should equal position
            if result.col != pos:
                msg = f"Source {i}, position {pos} should have col {pos}, got {result.col}"
                raise AssertionError(msg)

            # Line span should start at 0 for first line
            if result.line_span.start != 0:
                msg = f"Source {i}, position {pos} line span should start at 0, got {result.line_span.start}"
                raise AssertionError(msg)

            LOG.debug(
                "Source %d, pos %d: line=%d, col=%d, span=(%d,%d)",
                i,
                pos,
                result.line,
                result.col,
                result.line_span.start,
                result.line_span.end,
            )

        LOG.info("Source %d passed all first line tests", i)
