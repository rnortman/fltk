"""Binding-level depth-limit tests for rust_parser_fixture.Parser (§4, §5, §6 of depth-limit design).

Tests T5, T6, T7 from the design's test plan. Uses the nest/nest_sum rules (§5) which have
apply-depth proportional to input nesting — unlike other fixture rules which are left-recursive
(seed-grow handles them at constant depth).

Requires rust_parser_fixture to be built: run 'make build-rust-parser-fixture' first.
"""

from __future__ import annotations

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)


def _default_max_depth() -> int:
    """Return DEFAULT_MAX_DEPTH by reading it from a freshly constructed parser."""
    return rust_parser_fixture.Parser("0").max_depth


def _make_nest(depth: int) -> str:
    """Return a nest input nested `depth` levels deep: depth parens around a number."""
    return "(" * depth + "42" + ")" * depth


# T5: Parser(text, max_depth=N) on deeply nested input raises RecursionError;
#     same input with larger max_depth parses successfully.
# Also covers binding-level flag-outranks-result for nest_sum.


def test_t5_nest_raises_recursion_error_at_small_limit():
    text = _make_nest(50)
    p = rust_parser_fixture.Parser(text, max_depth=10)
    with pytest.raises(RecursionError):
        p.apply__parse_nest(0)


def test_t5_nest_succeeds_with_larger_limit():
    text = _make_nest(50)
    p = rust_parser_fixture.Parser(text, max_depth=200)
    result = p.apply__parse_nest(0)
    assert result is not None
    assert result.pos == len(text)


def test_t5_nest_sum_raises_recursion_error_flag_outranks_some():
    """nest_sum on '1+<deeply-nested>' raises RecursionError despite in-flight Some (§2 flag-outranks-result)."""
    rhs = _make_nest(50)
    text = "1+" + rhs
    p = rust_parser_fixture.Parser(text, max_depth=10)
    with pytest.raises(RecursionError):
        p.apply__parse_nest_sum(0)


def test_t5_depth_exceeded_getter_false_on_success():
    text = _make_nest(5)
    p = rust_parser_fixture.Parser(text, max_depth=50)
    result = p.apply__parse_nest(0)
    assert result is not None
    assert p.depth_exceeded is False


def test_t5_max_depth_getter():
    p = rust_parser_fixture.Parser("42", max_depth=42)
    assert p.max_depth == 42


def test_t5_default_max_depth_getter():
    p = rust_parser_fixture.Parser("42")
    assert p.max_depth == _default_max_depth()


def test_t5_spent_instance_raises_on_subsequent_call():
    """After depth-exceeded, a subsequent call on the same instance also raises RecursionError.

    The second call uses apply__parse_nest_sum (a different rule than the first call),
    so its cache is cold. This proves the sticky flag — not a cached Failure entry — is
    responsible for the RecursionError on the second call.
    T3 (cargo) is the definitive stickiness proof with cache clearing; this test pins
    the binding-layer observable contract independently of cache state.
    """
    text = _make_nest(50)
    p = rust_parser_fixture.Parser(text, max_depth=10)
    with pytest.raises(RecursionError):
        p.apply__parse_nest(0)
    # Instance is spent; call a different rule (cold cache) — proves sticky flag, not cache.
    with pytest.raises(RecursionError):
        p.apply__parse_nest_sum(0)


# T6: default Parser on input nested DEFAULT_MAX_DEPTH + 100 raises RecursionError
#     without crashing the process (empirically pins §6 decision rule).


def test_t6_default_limit_fires_before_native_overflow():
    """Default limit fires on input nested DEFAULT_MAX_DEPTH + 100; process survives."""
    depth = _default_max_depth() + 100
    text = _make_nest(depth)
    p = rust_parser_fixture.Parser(text)
    with pytest.raises(RecursionError):
        p.apply__parse_nest(0)


# T7: existing test suite passes unchanged — default limit is not triggered by corpus.
# Covered implicitly by the rest of the test suite running cleanly; no explicit test needed.
# Shallow-nest corpus in test_rust_parser_parity_fixture.py also exercises nest/nest_sum
# at depths well below any limit.
