"""Rust source fragments the Rust emitters share.

The AST emitter (:mod:`fltk.fegen.gsm2ast_rs`) and the serde emitter both turn facts the
:mod:`fltk.fegen.ast_model` computed into Rust that the ``fltk-ast-core`` runtime consumes.  Where
the *same* model fact is rendered by both, the rendering has one home — here — so a change to the
runtime's vocabulary is one edit rather than one per backend, and the two emitters cannot describe
the same tree two ways.

Nothing here analyses anything: every function takes a value the model already computed and
spells it as Rust.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from fltk.fegen import ast_model as am
from fltk.fegen import grammar_shape as gshape
from fltk.fegen.gsm2parser_rs import rust_str_lit

RUNTIME = "::fltk_ast_core"
"""The runtime crate generated Rust names by absolute path, so a rule name cannot shadow it."""

SERDE_RUNTIME = "::fltk_serde_core"
"""The serde runtime, which re-exports the dispatch vocabulary and ``UNBOUNDED``.

A ``de.rs``-only consumer depends on ``serde`` and this crate and nothing else, so a table
rendered for that module names the vocabulary through the re-export rather than through
``fltk-ast-core`` directly.
"""

DISPATCH = f"{RUNTIME}::dispatch"
"""The runtime module holding the sum-rule dispatch vocabulary."""


def indent(lines: Iterable[str], columns: int) -> list[str]:
    """Every line moved right by ``columns``."""
    return [" " * columns + line for line in lines]


def member_lines(name: str, value: Sequence[str]) -> list[str]:
    """One ``name: value,`` entry of a struct literal, whose value may run over several lines."""
    if len(value) == 1:
        return [f"{name}: {value[0]},"]
    return [f"{name}: {value[0]}", *value[1:-1], f"{value[-1]},"]


def string(text: str) -> str:
    """One Rust string literal."""
    return f'"{rust_str_lit(text)}"'


def count(bound: float, runtime: str = RUNTIME) -> str:
    """One count bound, as the runtime's own spelling of it."""
    return f"{runtime}::UNBOUNDED" if bound == math.inf else str(int(bound))


def usize_slice(values: Sequence[int]) -> str:
    """One Rust slice of indices."""
    return f"&[{', '.join(str(value) for value in values)}]"


def dispatch_kind(kind: str, runtime: str = RUNTIME) -> str:
    """One dispatch pair's child kind: a referenced rule's name, or the runtime's text sentinel.

    The sentinel is named rather than spelled out, so the model's constant and the runtime's
    cannot drift apart without a build failure in every consumer.
    """
    return f"{runtime}::dispatch::TEXT_KIND" if kind == gshape.TEXT_KIND else string(kind)


def parse_skeleton_lines(goal: str, parser_alias: str, failed: str, ok: str) -> list[str]:
    """The body of a one-call entry point: parse ``src`` as ``goal``, then hand over the tree.

    Both entry points a grammar can carry — ``parse_str`` into the AST types, ``from_str`` into a
    serde target — parse the same way, and the three checks are correctness-bearing: a
    depth-rejected parse still comes back holding a tree, and the position it stopped at counts
    characters rather than bytes.  ``failed`` is the statement each returns its own parse error
    through, and ``ok`` the expression it hands the parsed node to.  The lines are unindented; a
    caller places them in its own function body.
    """
    return [
        f"let mut parser = {parser_alias}::Parser::new(src, filename, false);",
        f"let result = parser.apply__parse_{goal}(0);",
        "// A depth-rejected parse can still come back as `Some` holding a wrong tree.",
        "if parser.depth_exceeded() {",
        f"    {failed}",
        "}",
        "let Some(parsed) = result else {",
        f"    {failed}",
        "};",
        "// The whole input has to be consumed; `pos` counts characters, not bytes.",
        "if parsed.pos != src.chars().count() as i64 {",
        f"    {failed}",
        "}",
        f"Ok({ok})",
    ]


def dispatch_table_lines(name: str, rule_name: str, dispatch: am.SumDispatch, runtime: str = RUNTIME) -> list[str]:
    """The ``static`` describing how one sum rule's alternatives are told apart.

    The runtime evaluates it; the emitters only write it down, which is what keeps one selection
    rule behind every backend that has to recover an alternative from a node.  ``runtime`` is the
    crate path the vocabulary is named through: ``fltk-ast-core`` for the AST module, its
    re-export in ``fltk-serde-core`` for a ``de.rs``.
    """
    module = f"{runtime}::dispatch"
    lines = [
        f"/// How rule `{rule_name}`'s alternatives are told apart by a node's labeled children.",
        f"static {name}: {module}::Table = {module}::Table {{",
        "    pairs: &[",
    ]
    for pair in dispatch.pairs:
        lines.append(
            f"        {module}::Pair {{ label: {string(pair.label)}, kind: {dispatch_kind(pair.kind, runtime)} }},"
        )
    lines.extend(("    ],", "    alternatives: &["))
    for alternative in dispatch.alternatives:
        lines.extend(_alternative_lines(alternative, runtime))
    lines.extend(("    ],", "};"))
    return lines


def _alternative_lines(alternative: am.AltDispatch, runtime: str) -> list[str]:
    """One alternative's entry in a dispatch table."""
    module = f"{runtime}::dispatch"
    lines = [f"        {module}::Alt {{", f"            variant: {alternative.variant_index},"]
    if not alternative.bounds:
        lines.append("            bounds: &[],")
    else:
        lines.append("            bounds: &[")
        for bound in alternative.bounds:
            lines.append(
                f"                {module}::Bound {{ label: {string(bound.label)}, "
                f"pairs: {usize_slice(bound.pairs)}, minimum: {bound.minimum}, "
                f"maximum: {count(bound.maximum, runtime)} }},"
            )
        lines.append("            ],")
    lines.extend((f"            forbidden: {usize_slice(alternative.forbidden)},", "        },"))
    return lines
