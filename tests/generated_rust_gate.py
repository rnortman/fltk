"""Build a throwaway Cargo crate out of generated Rust and hand it to ``cargo``.

The Rust emitters produce public API for out-of-tree consumers (CLAUDE.md), and a source string
that reads right can still be Rust that does not compile — a misplaced brace, a missing ``Box``
on a cyclic field, an unused binding under ``-D warnings``. Nor can a substring assertion say
what the compiled code *does*. This assembles one crate holding a module per grammar shape —
CST, and whichever of AST / parser / unparser / serde the shape asks for — plus that shape's own
Rust ``#[test]``s, so the generated code is compiled and run where ``make check`` can see it.

The crate is a workspace of its own so it resolves against the repo's runtime crates by path
without joining the root workspace. Its `python` and `test-introspection` features exist only
because the generated CST gates items on them; nothing here enables either, so no pyo3 is linked.
"""

from __future__ import annotations

import dataclasses
import shutil
import subprocess
from pathlib import Path

from fltk.fegen import ast_config as ac
from fltk.fegen import ast_model as am
from fltk.fegen import ast_test_grammars as fixtures
from fltk.fegen.gsm2ast_rs import generate_ast_rs
from fltk.fegen.gsm2parser_rs import RustParserGenerator
from fltk.fegen.gsm2serde_rs import generate_de_rs
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from fltk.unparse.gsm2unparser_rs import RustUnparserGenerator

_REPO_ROOT = Path(__file__).parent.parent

_MANIFEST = """[workspace]

[package]
name = "fltk-generated-rust-gate"
version = "0.0.0"
edition = "2021"
publish = false

# Declared, never enabled: the generated CST gates its pyo3 items on them, and an undeclared
# feature name is an `unexpected_cfg` warning, which `-D warnings` turns into a build failure.
[features]
python = []
test-introspection = []

[dependencies]
fltk-cst-core = {{ path = "{root}/crates/fltk-cst-core", default-features = false }}
fltk-ast-core = {{ path = "{root}/crates/fltk-ast-core", features = ["uuid", "decimal"] }}
fltk-parser-core = {{ path = "{root}/crates/fltk-parser-core" }}
fltk-unparser-core = {{ path = "{root}/crates/fltk-unparser-core" }}
fltk-serde-core = {{ path = "{root}/crates/fltk-serde-core" }}
serde = {{ version = "1", features = ["derive"] }}
"""


@dataclasses.dataclass(frozen=True)
class Case:
    """One grammar whose generated Rust has to compile, and optionally to behave."""

    name: str
    """The crate module the generated files land in; a valid Rust identifier."""

    grammar: str
    sidecar: str | None = None

    runtime: str = ""
    """Rust ``#[test]`` source for this shape, if it is exercised at runtime as well as compiled.

    Emitted as a child module of the case, so it reads ``super::ast`` / ``super::cst`` and reaches
    whichever generated parser or unparser the case asked for.
    """

    support: str = ""
    """Extra Rust the case's ``mod.rs`` carries — a ``custom(...)`` rule's user-supplied type."""

    ast: bool = True
    """Whether the AST module is generated; false for a shape that gates the unparser alone."""

    serde: bool = False
    """Whether the serde description module is emitted, so a derived target can deserialize.

    The emitter writes shape descriptions and entry points against ``fltk-serde-core``'s
    vocabulary; nothing but a compiler says the two halves still agree, and a warning in the
    emitted module is a hard build failure in every consumer under ``-D warnings``.

    Where the case also has an AST module, the serde module is generated against it, so the
    ``Deserialize`` impls on the generated AST types are compiled too.
    """

    parser: bool = False
    """Whether a generated Rust parser is emitted, so a runtime test can parse real text."""

    unparser: bool = False
    """Whether a generated Rust unparser is emitted, for a round trip through the formatter."""

    goal: str | None = None
    """The rule the ``parse_str`` / ``unparse_str`` conveniences target; the first one by default."""

    def model(self) -> am.AstModel:
        grammar = fixtures.classified_grammar(self.grammar)
        config = None if self.sidecar is None else ac.load_ast_config(self.sidecar, grammar, {ac.Backend.RUST})
        return am.build_ast_model(grammar, config)


def write_crate(directory: Path, cases: list[Case]) -> Path:
    """Write the gate crate into ``directory`` and return its manifest path."""
    source = directory / "src"
    source.mkdir(parents=True, exist_ok=True)
    manifest = directory / "Cargo.toml"
    manifest.write_text(_MANIFEST.format(root=_REPO_ROOT))
    source.joinpath("lib.rs").write_text("".join(f"pub mod {case.name};\n" for case in cases))
    for case in cases:
        model = case.model()
        module = source / case.name
        module.mkdir(exist_ok=True)
        declarations = ["pub mod cst;\n"]
        module.joinpath("cst.rs").write_text(RustCstGenerator(model.grammar).generate())
        if case.ast:
            declarations.append("pub mod ast;\n")
            module.joinpath("ast.rs").write_text(
                generate_ast_rs(
                    model,
                    cst_mod_path="super::cst",
                    parser_mod_path="super::parser" if case.parser else None,
                    unparser_mod_path="super::unparser" if case.unparser else None,
                    goal_rule=case.goal,
                )
            )
        if case.parser:
            declarations.append("pub mod parser;\n")
            module.joinpath("parser.rs").write_text(RustParserGenerator(model.grammar).generate())
        if case.unparser:
            declarations.append("pub mod unparser;\n")
            module.joinpath("unparser.rs").write_text(RustUnparserGenerator(model.grammar).generate())
        if case.serde:
            declarations.append("pub mod de;\n")
            module.joinpath("de.rs").write_text(
                generate_de_rs(
                    model,
                    cst_mod_path="super::cst",
                    parser_mod_path="super::parser" if case.parser else None,
                    goal_rule=case.goal,
                    ast_mod_path="super::ast" if case.ast else None,
                )
            )
        if case.runtime:
            declarations.append("#[cfg(test)]\nmod runtime;\n")
            module.joinpath("runtime.rs").write_text(case.runtime)
        module.joinpath("mod.rs").write_text("".join(declarations) + case.support)
    return manifest


def run_cargo(command: str, manifest: Path, target_dir: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one cargo subcommand over the gate crate.

    The Rust toolchain is mandatory for this repo (CLAUDE.md), so a missing ``cargo`` is a hard
    failure rather than a skip: a compile gate that can silently not run is not a gate.

    Resolution is offline. Every third-party crate the gate needs — `indexmap`, `regex-automata`,
    `uuid`, `rust_decimal` and their transitive deps — is already in the root workspace's
    `Cargo.lock` and therefore in the local registry cache once the repo has been built, so the
    gate crate resolves from that cache instead of reaching the network and picking whatever
    versions happen to be current. Its own lockfile is throwaway and untracked, which is why
    `make check-locks` never sees it.
    """
    cargo = shutil.which("cargo")
    assert cargo is not None, "cargo is required to compile the generated Rust modules"
    return subprocess.run(  # noqa: S603
        [
            cargo,
            command,
            "--offline",
            "--manifest-path",
            str(manifest),
            "--target-dir",
            str(target_dir),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
