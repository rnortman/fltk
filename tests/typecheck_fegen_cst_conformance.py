# ruff: noqa
"""Static conformance fixture: both CST backends satisfy CstModule without a cast.

This file is checked in and named explicitly in `[tool.pyright] include` (pyproject.toml), so the
repo-wide `//:pyright` gate type-checks it — the rest of `tests/` is outside that gate.
It uses the generated fegen_rust_cst/cst.pyi stub — pyright reads the stub, not the compiled
extension — so no Rust toolchain is needed for the check.

If pyright reports errors here, one backend's annotations diverge from the CstModule protocol.
Fix the emitter rather than adding a cast: a cast here would hide
exactly the breakage this file exists to catch — a consumer whose source is annotated against the
protocol can then no longer pass that backend's nodes.
"""

from __future__ import annotations

import fltk.fegen.fltk_cst as py_cst
import fltk.fegen.fltk_cst_protocol as cstp
import fegen_rust_cst.cst as fegen_cst
from fltk.fegen.pyrt.label_protocol import LabelProtocol

# B4 static conformance: whole-module no-cast assignment must produce zero pyright errors.
_m_rust: cstp.CstModule = fegen_cst
_m_python: cstp.CstModule = py_cst

# Label conformance: every label flavor must be assignable to LabelProtocol without a cast — the
# type every protocol label slot, protocol mutator `label:` param and Rust stub `variant()` uses.
_label_concrete: LabelProtocol = py_cst.Items.Label.ITEM
_label_protocol: LabelProtocol = cstp.ItemsLabel.ITEM
_label_rust: LabelProtocol = fegen_cst.Items.Label.ITEM


# Per-class no-cast fixtures: each stub class must be assignable to its protocol counterpart.
def _check_grammar(x: fegen_cst.Grammar) -> None:
    _x: cstp.Grammar = x


def _check_rule(x: fegen_cst.Rule) -> None:
    _x: cstp.Rule = x


def _check_alternatives(x: fegen_cst.Alternatives) -> None:
    _x: cstp.Alternatives = x


def _check_items(x: fegen_cst.Items) -> None:
    _x: cstp.Items = x


def _check_item(x: fegen_cst.Item) -> None:
    _x: cstp.Item = x


def _check_term(x: fegen_cst.Term) -> None:
    _x: cstp.Term = x


def _check_disposition(x: fegen_cst.Disposition) -> None:
    _x: cstp.Disposition = x


def _check_quantifier(x: fegen_cst.Quantifier) -> None:
    _x: cstp.Quantifier = x


def _check_identifier(x: fegen_cst.Identifier) -> None:
    _x: cstp.Identifier = x


def _check_rawstring(x: fegen_cst.RawString) -> None:
    _x: cstp.RawString = x


def _check_literal(x: fegen_cst.Literal) -> None:
    _x: cstp.Literal = x


def _check_trivia(x: fegen_cst.Trivia) -> None:
    _x: cstp.Trivia = x


def _check_linecomment(x: fegen_cst.LineComment) -> None:
    _x: cstp.LineComment = x


def _check_blockcomment(x: fegen_cst.BlockComment) -> None:
    _x: cstp.BlockComment = x


# The same per-class no-cast fixtures for the Python backend: a concrete dataclass must be
# assignable to its protocol counterpart, so one protocol-annotated consumer takes both.


def _check_py_grammar(x: py_cst.Grammar) -> None:
    _x: cstp.Grammar = x


def _check_py_rule(x: py_cst.Rule) -> None:
    _x: cstp.Rule = x


def _check_py_alternatives(x: py_cst.Alternatives) -> None:
    _x: cstp.Alternatives = x


def _check_py_items(x: py_cst.Items) -> None:
    _x: cstp.Items = x


def _check_py_item(x: py_cst.Item) -> None:
    _x: cstp.Item = x


def _check_py_term(x: py_cst.Term) -> None:
    _x: cstp.Term = x


def _check_py_disposition(x: py_cst.Disposition) -> None:
    _x: cstp.Disposition = x


def _check_py_quantifier(x: py_cst.Quantifier) -> None:
    _x: cstp.Quantifier = x


def _check_py_identifier(x: py_cst.Identifier) -> None:
    _x: cstp.Identifier = x


def _check_py_rawstring(x: py_cst.RawString) -> None:
    _x: cstp.RawString = x


def _check_py_literal(x: py_cst.Literal) -> None:
    _x: cstp.Literal = x


def _check_py_trivia(x: py_cst.Trivia) -> None:
    _x: cstp.Trivia = x


def _check_py_linecomment(x: py_cst.LineComment) -> None:
    _x: cstp.LineComment = x


def _check_py_blockcomment(x: py_cst.BlockComment) -> None:
    _x: cstp.BlockComment = x


# Construction through CstModule: a consumer that holds only the protocol module must be able to
# build nodes with it, which is what makes a backend-agnostic tree builder writable at all.
def _build_through_module(mod: cstp.CstModule) -> cstp.Items:
    items = mod.Items()
    item = mod.Item()
    items.append(item)
    return items


_built_rust: cstp.Items = _build_through_module(fegen_cst)
_built_python: cstp.Items = _build_through_module(py_cst)


# Mutation through the protocol: the mutator surface must be callable on a protocol-typed node,
# with a label taken off the node (the only label flavor every backend accepts at runtime).
def _mutate_through_protocol(node: cstp.Items, child: cstp.Item) -> None:
    node.append(child)
    node.extend([child])
    node.append_item(child)
    node.extend_item([child])
    label, existing = node.child()
    node.insert(0, child, label)
    node.replace_at(0, child, label)
    _removed: tuple[LabelProtocol | None, object] = node.remove_at(0)
    node.extend_children(node)
    node.clear()


def _mutate_rust(node: fegen_cst.Items, child: fegen_cst.Item) -> None:
    _mutate_through_protocol(node, child)


def _mutate_python(node: py_cst.Items, child: py_cst.Item) -> None:
    _mutate_through_protocol(node, child)


# The same mutators on a concrete node, called with protocol-typed arguments: this is the widened
# input surface, and the direction a consumer holding a protocol node but a concrete container hits.
def _mutate_concrete_with_protocol_inputs(node: py_cst.Items, child: cstp.Item, label: LabelProtocol) -> None:
    node.append(child, label)
    node.extend([child], label)
    node.insert(0, child, label)
    node.replace_at(0, child, label)
    node.append_item(child)
