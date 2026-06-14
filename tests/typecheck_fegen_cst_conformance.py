# ruff: noqa
"""Static conformance fixture: fegen_rust_cst.cst satisfies CstModule without a cast.

This file is checked in and validated by the repo-wide `uv run pyright` gate (§2.3, §4 B4).
It uses the stub at fltk/_stubs/fegen_rust_cst/cst.pyi — pyright reads the stub, not the compiled
extension — so no Rust toolchain is needed for the check.

If pyright reports errors here, the stub's type annotations diverge from the CstModule
protocol. Fix the stub (re-run make gencode) and ensure the annotations satisfy CstModule.
"""

from __future__ import annotations

import fltk.fegen.fltk_cst_protocol as cstp
import fegen_rust_cst.cst as fegen_cst

# B4 static conformance: whole-module no-cast assignment must produce zero pyright errors.
_m: cstp.CstModule = fegen_cst


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
