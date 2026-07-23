"""Consumer smoke test: the @fltk-built Rust extension imports and parses.

Driven as a plain script (no pytest in the consumer module's dependency graph).

This proves a downstream consumer can, from an external-repo context:
  - load @fltk//:rust.bzl and use generate_rust_parser + fltk_pyo3_cdylib cross-module,
  - compile the resulting PyO3 cdylib,
  - import the compiled extension and parse a sample input, and
  - read the generated CST accessors, with every span resolving to the canonical
    fltk._native.Span type rather than one minted by the consumer's own cdylib.
"""

from __future__ import annotations

import sys

# Bazel-generated PyO3 extension; see BUILD.bazel.
import consumer_native

import fltk._native


def test_fltk_native_is_rust_path() -> None:
    """fltk._native must resolve to the compiled .so, not the stub-only directory."""
    # Without the .so on the path, `import fltk._native` still succeeds: fltk/_native/ holds
    # __init__.pyi and no __init__.py, so it resolves as an implicit namespace package with
    # no attributes at all.  Probing for Span is what distinguishes the two cases.
    assert hasattr(fltk._native, "Span"), "fltk._native has no Span — the Rust .so is not on the path"


def test_parse_num() -> None:
    src = "42"
    parser = consumer_native.parser.Parser(src)
    result = parser.apply__parse_num(0)
    assert result is not None, "Rust parser returned None for a valid num"
    assert result.pos == len(src), f"parser did not consume full input: pos={result.pos}, len={len(src)}"

    node = result.result
    assert node is not None, "CST root node is None"
    span = node.span
    assert span is not None, "node.span is None"
    assert span.start == 0, f"expected span.start=0, got {span.start}"
    assert span.end == len(src), f"expected span.end={len(src)}, got {span.end}"
    # Cross-cdylib type resolution: a span handed out by the consumer's own cdylib must BE the
    # canonical fltk._native.Span, not a same-shaped Span this cdylib registered for itself.
    # Span is #[pyclass(frozen)] and unsubclassable, so identity is the property to assert.
    assert type(span) is fltk._native.Span, (
        f"node.span type {type(span)!r} is not the canonical fltk._native.Span — "
        f"cross-cdylib span type resolution broke"
    )

    # Generated label accessor for `num := value:/[0-9]+/`.
    value = node.child_value()
    assert type(value) is fltk._native.Span, (
        f"child_value() type {type(value)!r} is not the canonical fltk._native.Span — "
        f"cross-cdylib span type resolution broke"
    )
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
