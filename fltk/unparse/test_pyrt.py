"""Unit tests for the unparser runtime support (``fltk.unparse.pyrt``).

Distinct from ``tests/test_pyrt_errors.py``, which despite the name is scoped to
``fltk.fegen.pyrt.errors`` and cross-pinned with the Rust escape tests.
"""

from __future__ import annotations

import pytest

from fltk.unparse.pyrt import raise_preserved_trivia_failure


def test_raise_preserved_trivia_failure_names_rule_and_pos() -> None:
    """The helper raises ValueError naming the rule and child position, refusing to drop comments."""
    with pytest.raises(ValueError, match="refusing to silently drop comments") as exc_info:
        raise_preserved_trivia_failure("my_rule", 3)
    msg = str(exc_info.value)
    assert "my_rule" in msg
    assert "child position 3" in msg
    assert "unparse__trivia returned None" in msg
