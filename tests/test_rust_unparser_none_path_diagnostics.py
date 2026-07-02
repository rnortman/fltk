"""Runtime diagnostics for the Rust unparser's invariant-violation None paths.

Site 2 of unparser-none-path-diagnostics: a regex term whose captured ``Span`` yields no
text (here a sourceless span) is an invariant violation. The generated Rust unparser must
``panic!`` (surfacing to Python as ``pyo3_runtime.PanicException``) naming the rule, item,
child position, and span, rather than silently returning ``None`` and deleting the term's
text from the output.

Requires rust_parser_fixture to be built: run 'make build-rust-parser-fixture' first.
"""

from __future__ import annotations

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)

from fltk._native import Span  # noqa: E402


def test_regex_sourceless_span_panics_with_context() -> None:
    """A ``num`` node whose regex ``value`` child is a sourceless span panics naming the failure.

    ``num := value:/[0-9]+/`` — a source-bearing span always yields text, but the two-arg
    ``fltk._native.Span(start, end)`` constructor attaches no source, so ``span.text()`` returns
    ``None``. The generated ``unparse_num`` must panic (not return ``None``), and the message
    must name the rule, the labeled item, the child position, and the span's Debug form (which
    reports ``has_source`` so the sourceless cause is distinguishable).
    """
    num = rust_parser_fixture.cst.Num()
    num.append_value(Span(0, 2))  # two-arg constructor => sourceless span

    unparser = rust_parser_fixture.unparser.Unparser()
    # PanicException subclasses BaseException, not Exception.
    with pytest.raises(BaseException, match="unparse_num: cannot extract text for regex term") as exc_info:
        unparser.unparse_num(num)
    msg = str(exc_info.value)
    assert "label `value`" in msg
    assert "child position 0" in msg
    assert "has_source: false" in msg
