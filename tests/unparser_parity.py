"""Cross-backend unparser parity helpers.

Imported by test_rust_unparser_parity_fixture.py. Not a test module itself.

Factors the parse-independent dispatch: given a Python unparser setup and a Rust
PyUnparser instance, render the same node through both backends' full pipelines
(unparse -> resolve -> render) and assert the rendered strings are byte-equal.
Analogous to parser_parity.run_parity_corpus_entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fltk.plumbing import render_doc, unparse_cst
from fltk.unparse.renderer import RendererConfig

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from fltk.plumbing_types import UnparserResult


def render_config_ids(configs: Iterable[tuple[int, int]]) -> list[str]:
    """pytest parametrize IDs for (max_width, indent_width) render configs.

    Shared so the ID format string lives in one place; the parity test modules hold
    their own `_CONFIGS` (which differ) but derive stable IDs through this helper.
    """
    return [f"w{w}i{i}" for (w, i) in configs]


def unparse_python(
    unparser_result: UnparserResult,
    py_cst: Any,
    text: str,
    rule: str,
    *,
    indent_width: int,
    max_width: int,
) -> str | None:
    """Run the Python unparse -> resolve -> render pipeline.

    Delegates the unparse -> resolve stage to the production plumbing
    (`fltk.plumbing.unparse_cst`) so this test path stays in lock-step with the
    real Python rendering pipeline rather than re-implementing (and drifting
    from) it.

    Returns the rendered string, or None if the unparser fails for this node
    (mirroring the Rust PyUnparser method's Optional[str] return). `unparse_cst`
    raises ValueError both when the unparser returns None and when the rule has
    no unparse method; either is a None parity outcome here, and the reference
    backend always succeeding is enforced by `assert_unparse_parity`.
    """
    try:
        doc = unparse_cst(unparser_result, py_cst, text, rule)
    except ValueError:
        return None
    return render_doc(doc, RendererConfig(indent_width=indent_width, max_width=max_width))


def unparse_rust(
    rust_unparser: Any,
    node: Any,
    rule: str,
    *,
    indent_width: int,
    max_width: int,
) -> str | None:
    """Run the Rust full-pipeline unparse method (unparse -> resolve -> render).

    Returns the rendered string, or None if the unparser fails (Ok(None)).
    """
    method = getattr(rust_unparser, f"unparse_{rule}")
    return method(node, max_width=max_width, indent_width=indent_width)


def assert_unparse_parity(
    unparser_result: UnparserResult,
    py_cst: Any,
    rust_unparser: Any,
    rust_node: Any,
    rule: str,
    text: str,
    *,
    indent_width: int = 4,
    max_width: int = 80,
) -> None:
    """Assert byte-equal rendered output between the Python and Rust unparsers.

    Both backends run their full pipeline at the same RendererConfig. They must
    agree on whether unparsing succeeds and, when it does, on the rendered bytes.
    """
    py_str = unparse_python(unparser_result, py_cst, text, rule, indent_width=indent_width, max_width=max_width)
    # The Python backend is the reference: every corpus entry is a complete valid
    # parse that must unparse, so a None here is a generator/test-infra bug, not a
    # parity outcome. Surface it loudly instead of letting a mutual-None pass.
    assert py_str is not None, (
        f"[rule={rule!r} text={text!r} w={max_width} i={indent_width}] "
        f"Python (reference) unparser returned None for a valid parse — generator or test-infra bug"
    )
    rust_str = unparse_rust(rust_unparser, rust_node, rule, indent_width=indent_width, max_width=max_width)

    assert (py_str is None) == (rust_str is None), (
        f"[rule={rule!r} text={text!r} w={max_width} i={indent_width}] backends disagree on unparse success: "
        f"python={'None' if py_str is None else 'str'} rust={'None' if rust_str is None else 'str'}"
    )
    if py_str is not None:
        assert py_str == rust_str, (
            f"[rule={rule!r} text={text!r} w={max_width} i={indent_width}] rendered-string mismatch:\n"
            f"Python: {py_str!r}\nRust:   {rust_str!r}"
        )
