"""Where the generated PEP 561 stub packages sit, for the suites that read or type-check them.

The stub packages exist only as Bazel outputs, and the path to each is a Bazel layout decision
(`extension_name` names the directory) rather than something a test should restate. Stating them
once here is what keeps a test from guessing.

`pathlib.Path(__file__).parent.parent` is the tree root in every lane, including a test module's
own: pytest does not resolve the file it collects, so a runfiles entry that is a symlink into the
checkout still reports its runfiles path, and a Bazel-only output next to it is found. That is
why the constants below are the only thing this module exports — a second name for the root would
be a second spelling of the value each suite already has.

A type checker reaches a stub package by putting the *parent* directory on its search path, so
both names are given for each: the package directory to read files out of, and its parent to hand
to pyright as an `extraPaths` entry.
"""

from __future__ import annotations

import pathlib

_TREE_ROOT = pathlib.Path(__file__).parent.parent

#: Parent of the `fegen_rust_cst` stub package; goes on a type checker's search path.
FEGEN_RUST_CST_STUB_ROOT = _TREE_ROOT / "crates" / "fegen-rust"

#: The `fegen_rust_cst` stub package itself (cst.pyi, unparser.pyi, __init__.pyi).
FEGEN_RUST_CST_STUB_DIR = FEGEN_RUST_CST_STUB_ROOT / "fegen_rust_cst"

#: Parent of the `rust_parser_fixture` stub package.
RUST_PARSER_FIXTURE_STUB_ROOT = _TREE_ROOT / "tests" / "rust_parser_fixture"

#: The `rust_parser_fixture` stub package itself.
RUST_PARSER_FIXTURE_STUB_DIR = RUST_PARSER_FIXTURE_STUB_ROOT / "rust_parser_fixture"
