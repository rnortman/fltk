#!/usr/bin/env -S uv run python
"""``fltk-grammar-lsp``: one friendly entry point serving fltk's own grammar DSLs.

fltk ships three DSLs -- ``.fltkg`` grammars, ``.fltkfmt`` formatting specs, and ``.fltklsp``
editor-tooling specs -- each with its grammar and sidecar specs inside the ``fltk`` package. This
CLI resolves those packaged files and starts the generic ``fltk-lsp`` server for one of them:

    fltk-grammar-lsp {fltkg,fltkfmt,fltklsp} [--width N] [--indent N]

The registry supplies every path, so no ``--grammar/--lsp/--fmt/--rule`` flags are needed. Files are
resolved through ``importlib.resources`` so the same command works for editable installs, built
wheels, and Bazel runfiles.
"""

from __future__ import annotations

import contextlib
import dataclasses
import enum
import importlib.resources
from typing import TYPE_CHECKING, Annotated

import typer

from fltk.lsp.server_cli import serve

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(frozen=True)
class BuiltinLanguage:
    """A packaged fltk DSL: the resources anchor and the sidecar file names.

    ``package`` is an ``importlib.resources`` anchor (e.g. ``"fltk.fegen"``); ``grammar`` is the
    ``.fltkg`` file name; ``lsp``/``fmt`` are the optional ``.fltklsp``/``.fltkfmt`` sidecars.
    """

    package: str
    grammar: str
    lsp: str | None
    fmt: str | None


BUILTIN_LANGUAGES: dict[str, BuiltinLanguage] = {
    "fltkg": BuiltinLanguage("fltk.fegen", "fegen.fltkg", "fegen.fltklsp", "fegen.fltkfmt"),
    "fltkfmt": BuiltinLanguage("fltk.unparse", "unparsefmt.fltkg", "unparsefmt.fltklsp", "unparsefmt.fltkfmt"),
    "fltklsp": BuiltinLanguage("fltk.lsp", "fltklsp.fltkg", "fltklsp.fltklsp", "fltklsp.fltkfmt"),
}


class Language(str, enum.Enum):
    """The selectable built-in language ids, matching ``BUILTIN_LANGUAGES`` keys.

    A static enum (not derived from the registry at runtime) so it is usable as the Typer choice
    argument's type annotation under pyright; ``test_language_enum_matches_registry`` guards the two
    against drift.
    """

    fltkg = "fltkg"
    fltkfmt = "fltkfmt"
    fltklsp = "fltklsp"


def resolve_paths(language: BuiltinLanguage, stack: contextlib.ExitStack) -> tuple[Path, Path | None, Path | None]:
    """Materialize a language's packaged files as filesystem paths held open for ``stack``'s lifetime.

    Returns ``(grammar, lsp, fmt)`` where ``lsp``/``fmt`` are ``None`` when the language declares no
    such sidecar. ``as_file`` may extract a zipped resource to a temp file; the returned paths stay
    valid until ``stack`` closes, which must outlive the server.
    """

    def materialize(name: str | None) -> Path | None:
        if name is None:
            return None
        resource = importlib.resources.files(language.package) / name
        return stack.enter_context(importlib.resources.as_file(resource))

    grammar = materialize(language.grammar)
    assert grammar is not None, "a built-in language always names a grammar"
    return grammar, materialize(language.lsp), materialize(language.fmt)


app = typer.Typer(
    name="fltk-grammar-lsp",
    help="Run an LSP server for one of fltk's own grammar DSLs (fltkg, fltkfmt, fltklsp).",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command()
def main(
    language: Annotated[Language, typer.Argument(help="Which built-in fltk DSL to serve")],
    width: Annotated[int, typer.Option("--width", help="Line width for document formatting")] = 80,
    indent: Annotated[int, typer.Option("--indent", help="Indent width for document formatting")] = 2,
) -> None:
    """Serve the built-in LANGUAGE over LSP on stdio using its packaged grammar and specs."""
    builtin = BUILTIN_LANGUAGES[language.value]
    with contextlib.ExitStack() as stack:
        grammar, lsp, fmt = resolve_paths(builtin, stack)
        serve(grammar, lsp=lsp, fmt=fmt, width=width, indent=indent)


if __name__ == "__main__":
    app()
