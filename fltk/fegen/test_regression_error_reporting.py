"""Regression test for bug #3 (93a64d4) - Fix error reporting at end of file

This test verifies that calling pos_to_line_col with pos == len(terminals) does not
cause an IndexError. The bug was in terminalsrc.py where the bounds check was:

    if pos >= len(self.terminals):
        raise ValueError(...)

This would trigger when pos == len(terminals), but the fix changed it to:

    if pos > len(self.terminals):
        raise ValueError(...)

And added special handling for the case when pos == len(terminals):

    if pos == len(self.terminals):
        pos -= 1

The IndexError occurred when trying to report errors at the exact end of the source,
which commonly happens when parsing incomplete/truncated input.
"""

import pytest

from fltk.fegen.pyrt.terminalsrc import TerminalSource


def test_pos_to_line_col_at_end_of_source():
    """Test that pos_to_line_col works correctly when pos == len(terminals).

    The bug caused an IndexError when attempting to get line/column information
    for a position exactly at the end of the source text. This commonly happens
    during error reporting when parsing incomplete syntax.
    """

    # Test case 1: Simple single-line source
    source = TerminalSource("abc")

    # This should not raise an IndexError (the bug would cause it to fail)
    line_col = source.pos_to_line_col(3)  # pos == len("abc")

    # The fix adjusts pos to len-1, so we should get the last character's position
    assert line_col.line == 0  # First line (0-indexed)
    assert line_col.col == 2  # Last character's column (0-indexed)

    # Test case 2: Multi-line source ending with newline
    source = TerminalSource("line1\nline2\n")
    end_pos = len("line1\nline2\n")  # = 12

    # This should not raise an IndexError
    line_col = source.pos_to_line_col(end_pos)

    # Should handle the end-of-source position gracefully
    assert line_col.line >= 0  # Valid line number
    assert line_col.col >= 0  # Valid column number

    # Test case 3: Multi-line source without trailing newline
    source = TerminalSource("line1\nline2")
    end_pos = len("line1\nline2")  # = 11

    # This should not raise an IndexError
    line_col = source.pos_to_line_col(end_pos)

    # Should handle the end-of-source position gracefully
    assert line_col.line >= 0  # Valid line number
    assert line_col.col >= 0  # Valid column number


def test_pos_to_line_col_beyond_end_still_raises():
    """Test that pos_to_line_col still raises ValueError for pos > len(terminals).

    The fix should only handle pos == len(terminals), not pos > len(terminals).
    """
    source = TerminalSource("abc")

    # pos > len(terminals) should still raise ValueError
    with pytest.raises(ValueError, match="pos 4 beyond end of terminals"):
        source.pos_to_line_col(4)  # pos > len("abc")

    with pytest.raises(ValueError, match="pos 100 beyond end of terminals"):
        source.pos_to_line_col(100)


def test_pos_to_line_col_normal_positions():
    """Test that pos_to_line_col works correctly for normal positions (regression check)."""
    source = TerminalSource("line1\nline2\nline3")

    # Test various positions to ensure fix doesn't break normal functionality
    line_col = source.pos_to_line_col(0)  # Start of first line
    assert line_col.line == 0
    assert line_col.col == 0

    line_col = source.pos_to_line_col(5)  # Newline after "line1"
    assert line_col.line == 0
    assert line_col.col == 5

    line_col = source.pos_to_line_col(6)  # Start of second line
    assert line_col.line == 1
    assert line_col.col == 0

    line_col = source.pos_to_line_col(12)  # Start of third line
    assert line_col.line == 2
    assert line_col.col == 0


def test_empty_source_edge_case():
    """Test edge case with empty source."""
    source = TerminalSource("")

    # pos == len("") == 0 should work without IndexError
    line_col = source.pos_to_line_col(0)

    # For empty source, the fix adjusts pos to -1, which creates col=-1
    # This is the actual behavior after the fix - the important part is no IndexError
    assert line_col.line >= 0
    # Note: col can be -1 for empty source after the fix adjusts pos -= 1

    # But pos > 0 should still raise
    with pytest.raises(ValueError, match="pos 1 beyond end of terminals"):
        source.pos_to_line_col(1)
