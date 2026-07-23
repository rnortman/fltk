"""Consumer smoke test: the @fltk-generated pure-Python parser imports and parses.

Driven as a plain script (no pytest in the consumer module's dependency graph).

This proves a downstream consumer can:
  - load @fltk//:rules.bzl and instantiate generate_parser cross-module,
  - import the generated parser + CST modules as top-level names, and
  - parse a sample input end-to-end and read the generated CST accessors.
"""

from __future__ import annotations

import sys

# Bazel-generated modules; see BUILD.bazel.
import consumer_cst
import consumer_parser

from fltk.fegen.pyrt import terminalsrc


def test_parse_num() -> None:
    src = "42"
    parser = consumer_parser.Parser(terminalsrc.TerminalSource(src))
    result = parser.apply__parse_num(0)
    assert result is not None, "pure-Python parser returned None for a valid num"
    assert result.pos == len(src), f"parser did not consume full input: pos={result.pos}, len={len(src)}"

    node = result.result
    assert isinstance(node, consumer_cst.Num), f"CST root is {type(node)!r}, expected consumer_cst.Num"
    # Generated label accessor for `num := value:/[0-9]+/`.
    value = node.child_value()
    assert (value.start, value.end) == (0, len(src)), (
        f"child_value() span {value.start}..{value.end} does not cover the input 0..{len(src)}"
    )


if __name__ == "__main__":
    # Discover rather than enumerate: a hand-maintained call list silently drops any test
    # added later, and the py_test still reports PASSED.
    tests = sorted(name for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj))
    assert tests, "no test_* functions found in this module"
    for test_name in tests:
        globals()[test_name]()
        sys.stdout.write(f"ok: {test_name}\n")
