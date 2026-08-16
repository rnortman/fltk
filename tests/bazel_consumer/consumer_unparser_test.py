"""Consumer smoke test: the @fltk-built extension exposes a working unparser submodule.

Driven as a plain script (no pytest in the consumer module's dependency graph).

This proves a downstream consumer can, from an external-repo context, ask
`fltk_pyo3_cdylib`/`generate_rust_parser` for `unparser = True` and get an importable,
callable unparser out of the compiled extension. Both halves matter and neither is
witnessed by a build: the crate root must declare and register `mod unparser;` (an
unregistered submodule simply is not there at import time), and the `.fltkfmt` spec must
have reached the generator (a default-config unparser imports and runs identically, and
differs only in the rendered text).
"""

from __future__ import annotations

import sys

# Bazel-generated PyO3 extension; see BUILD.bazel.
import consumer_unparser_native


def test_unparser_submodule_is_registered() -> None:
    assert hasattr(consumer_unparser_native, "unparser"), (
        "the compiled extension has no `unparser` submodule — the generated crate root did not declare and register it"
    )


def test_unparse_applies_the_baked_format_spec() -> None:
    src = "1+2"
    # The generated binding takes (text, filename, capture_trivia) positionally; unparsing
    # reads the trivia nodes, so capture_trivia must be on.
    parser = consumer_unparser_native.parser.Parser(src, None, True)
    result = parser.apply__parse_sum(0)
    assert result is not None, "Rust parser returned None for a valid sum"

    unparser = consumer_unparser_native.unparser.Unparser()
    rendered = unparser.unparse_sum(result.result)
    # consumer_unparser.fltkfmt puts one space on each side of "+", so the rendered text
    # differs from the input: a default-config unparser would render "1+2" here.
    assert rendered == "1 + 2", f"expected '1 + 2' from the baked format spec, got {rendered!r}"


def test_unparse_to_doc_renders_at_a_chosen_width() -> None:
    parser = consumer_unparser_native.parser.Parser("1+2", None, True)
    result = parser.apply__parse_sum(0)
    assert result is not None

    doc = consumer_unparser_native.unparser.Unparser().unparse_sum_doc(result.result)
    assert doc is not None, "unparse_sum_doc returned None for a parsed tree"
    assert doc.render(max_width=40) == "1 + 2"


if __name__ == "__main__":
    # Discover rather than enumerate: a hand-maintained call list silently drops any test
    # added later, and the py_test still reports PASSED.
    tests = sorted(name for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj))
    assert tests, "no test_* functions found in this module"
    for test_name in tests:
        globals()[test_name]()
        sys.stdout.write(f"ok: {test_name}\n")
