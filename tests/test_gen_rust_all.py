"""Tests for the merged gen-rust-all CLI subcommand.

gen-rust-all emits every Rust artifact for a grammar from one process. Its contract is that
each artifact is byte-identical to what the corresponding single-purpose subcommand writes —
the Bazel codegen rule runs only the merged form, while the documented ad-hoc recipes and
consumers' own scripts run the single-purpose ones, so a divergence would produce two
different generated trees from the same grammar.
"""

from __future__ import annotations

import pathlib

import pytest
from typer.testing import CliRunner

from fltk.fegen import genparser
from fltk.fegen.genparser import app

GRAMMAR = pathlib.Path("fltk/fegen/test_data/rust_parser_fixture.fltkg").resolve()
FLTKFMT = pathlib.Path("fltk/fegen/test_data/rust_parser_fixture.fltkfmt").resolve()
FLTKAST = pathlib.Path("tests/rust_parser_fixture/rust_parser_fixture.fltkast").resolve()

PROTOCOL_MODULE = "tests.rust_parser_fixture_cst_protocol"
GOAL = "nest_sum"


def _run(*args: str) -> None:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == 0, f"{args[0]} failed:\n{result.output}\n{result.exception}"


def _run_expecting_error(*args: str) -> str:
    result = CliRunner().invoke(app, list(args))
    assert result.exit_code == 1, f"expected exit 1, got {result.exit_code}:\n{result.output}"
    return result.output


def _generate_separately(out: pathlib.Path) -> None:
    """Emit the full artifact set with the five single-purpose subcommands."""
    out.mkdir(parents=True, exist_ok=True)
    _run(
        "gen-rust-cst",
        str(GRAMMAR),
        str(out / "cst.rs"),
        "--protocol-module",
        PROTOCOL_MODULE,
        "--pyi-output",
        str(out / "cst.pyi"),
        "--protocol-output",
        str(out / "cst_protocol.py"),
        "--init-pyi-output",
        str(out / "__init__.pyi"),
        "--extension-name",
        "rpf",
        "--submodules",
        "cst,parser,unparser",
    )
    _run("gen-rust-parser", str(GRAMMAR), str(out / "parser.rs"))
    _run(
        "gen-rust-unparser",
        str(GRAMMAR),
        str(out / "unparser.rs"),
        "--format-config",
        str(FLTKFMT),
        "--protocol-module",
        PROTOCOL_MODULE,
        "--pyi-output",
        str(out / "unparser.pyi"),
    )
    _run(
        "gen-rust-ast",
        str(GRAMMAR),
        str(out / "ast.rs"),
        "--ast-config",
        str(FLTKAST),
        "--parser-mod-path",
        "super::parser",
        "--unparser-mod-path",
        "super::unparser",
        "--goal",
        GOAL,
    )
    _run(
        "gen-rust-serde",
        str(GRAMMAR),
        str(out / "de.rs"),
        "--ast-config",
        str(FLTKAST),
        "--parser-mod-path",
        "super::parser",
        "--ast-mod-path",
        "super::ast",
        "--goal",
        GOAL,
    )


def _generate_merged(out: pathlib.Path) -> None:
    """Emit the same artifact set with one gen-rust-all invocation."""
    out.mkdir(parents=True, exist_ok=True)
    _run(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(out / "cst.rs"),
        "--parser-output",
        str(out / "parser.rs"),
        "--unparser-output",
        str(out / "unparser.rs"),
        "--ast-output",
        str(out / "ast.rs"),
        "--serde-output",
        str(out / "de.rs"),
        "--cst-mod-path",
        "super::cst",
        "--parser-mod-path",
        "super::parser",
        "--unparser-mod-path",
        "super::unparser",
        "--ast-mod-path",
        "super::ast",
        "--ast-config",
        str(FLTKAST),
        "--format-config",
        str(FLTKFMT),
        "--goal",
        GOAL,
        "--protocol-module",
        PROTOCOL_MODULE,
        "--cst-pyi-output",
        str(out / "cst.pyi"),
        "--unparser-pyi-output",
        str(out / "unparser.pyi"),
        "--protocol-output",
        str(out / "cst_protocol.py"),
        "--init-pyi-output",
        str(out / "__init__.pyi"),
        "--extension-name",
        "rpf",
        "--submodules",
        "cst,parser,unparser",
    )


@pytest.fixture(scope="module")
def full_artifact_sets(tmp_path_factory: pytest.TempPathFactory) -> tuple[pathlib.Path, pathlib.Path]:
    """Generate the full artifact set both ways once; the grammar is large."""
    root = tmp_path_factory.mktemp("gen_rust_all")
    separate = root / "separate"
    merged = root / "merged"
    _generate_separately(separate)
    _generate_merged(merged)
    return separate, merged


ARTIFACTS = [
    "cst.rs",
    "parser.rs",
    "unparser.rs",
    "ast.rs",
    "de.rs",
    "cst.pyi",
    "unparser.pyi",
    "cst_protocol.py",
    "__init__.pyi",
]


@pytest.mark.parametrize("artifact", ARTIFACTS)
def test_merged_output_is_byte_identical(full_artifact_sets: tuple[pathlib.Path, pathlib.Path], artifact: str) -> None:
    """Each merged artifact matches the single-purpose subcommand's byte-for-byte."""
    separate, merged = full_artifact_sets
    assert (merged / artifact).read_bytes() == (separate / artifact).read_bytes()


def test_merged_writes_exactly_the_requested_artifacts(
    full_artifact_sets: tuple[pathlib.Path, pathlib.Path],
) -> None:
    """Nothing beyond the named outputs reaches disk.

    Every file is named by its own option precisely so the Bazel action can declare all of
    them; an extra file (a .pyi written to a defaulted path, say) would be an undeclared
    output and fail the action.
    """
    _separate, merged = full_artifact_sets
    assert sorted(p.name for p in merged.iterdir()) == sorted(ARTIFACTS)


def test_minimal_invocation_writes_only_the_cst(tmp_path: pathlib.Path) -> None:
    """--cst-output alone is a legal request; no parser, no unparser, no AST."""
    _run("gen-rust-all", str(GRAMMAR), "--cst-output", str(tmp_path / "cst.rs"))
    assert [p.name for p in tmp_path.iterdir()] == ["cst.rs"]


def test_cst_and_parser_only(tmp_path: pathlib.Path) -> None:
    """The shape the pure-Rust default configuration asks for."""
    _run(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(tmp_path / "cst.rs"),
        "--parser-output",
        str(tmp_path / "parser.rs"),
    )
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cst.rs", "parser.rs"]


@pytest.mark.parametrize(
    ("extra_args", "message"),
    [
        (["--format-config", str(FLTKFMT)], "--format-config requires --unparser-output"),
        (["--goal", GOAL], "--goal requires --ast-output or --serde-output"),
        (["--ast-config", str(FLTKAST)], "--ast-config requires --ast-output or --serde-output"),
        (["--parser-mod-path", "super::parser"], "--parser-mod-path requires --ast-output or --serde-output"),
        (["--unparser-mod-path", "super::unparser"], "--unparser-mod-path requires --ast-output"),
        (["--ast-mod-path", "super::ast"], "--ast-mod-path requires --serde-output"),
        (["--protocol-module", PROTOCOL_MODULE], "--protocol-module requires --cst-pyi-output"),
        (["--cst-pyi-output", "{tmp}/cst.pyi"], "--cst-pyi-output requires --protocol-module"),
        (["--protocol-output", "{tmp}/p.py"], "--protocol-output requires --protocol-module"),
        (["--init-pyi-output", "{tmp}/i.pyi"], "--init-pyi-output requires --extension-name and --submodules"),
        (["--extension-name", "rpf"], "--extension-name requires --init-pyi-output"),
        (["--submodules", "cst,parser"], "--submodules requires --init-pyi-output"),
        (["--cst-mod-path", "not a path"], "--cst-mod-path 'not a path' is not a valid Rust module path"),
        (["--parser-mod-path", "not a path"], "--parser-mod-path 'not a path' is not a valid Rust module path"),
        (["--unparser-mod-path", "not a path"], "--unparser-mod-path 'not a path' is not a valid Rust module path"),
        (["--ast-mod-path", "not a path"], "--ast-mod-path 'not a path' is not a valid Rust module path"),
    ],
)
def test_flag_without_its_output_is_an_error(tmp_path: pathlib.Path, extra_args: list[str], message: str) -> None:
    """A flag shaping an artifact that was not requested is refused, not silently ignored.

    Output paths in the table are `{tmp}`-templated so every file a row could produce lands
    inside the directory the empty-directory assertion inspects; a bare relative path would be
    written to the process CWD, where the assertion cannot see it.
    """
    args = [arg.format(tmp=tmp_path) for arg in extra_args]
    output = _run_expecting_error("gen-rust-all", str(GRAMMAR), "--cst-output", str(tmp_path / "cst.rs"), *args)
    assert message in output
    assert list(tmp_path.iterdir()) == []


def test_unparser_stub_path_is_required_with_a_protocol_module(tmp_path: pathlib.Path) -> None:
    """An unparser plus a protocol module means an unparser stub, and it must be named.

    The stub's default path is derived from the .rs path, which this subcommand never uses: an
    unnamed file is an undeclared output for the build action that runs it.
    """
    output = _run_expecting_error(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(tmp_path / "cst.rs"),
        "--unparser-output",
        str(tmp_path / "unparser.rs"),
        "--protocol-module",
        PROTOCOL_MODULE,
        "--cst-pyi-output",
        str(tmp_path / "cst.pyi"),
    )
    assert "--unparser-output with --protocol-module requires --unparser-pyi-output" in output
    assert list(tmp_path.iterdir()) == []


def test_serde_output_requires_the_sidecar(tmp_path: pathlib.Path) -> None:
    """The serde frontend is shaped entirely by the sidecar; there is no default shape."""
    output = _run_expecting_error(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(tmp_path / "cst.rs"),
        "--serde-output",
        str(tmp_path / "de.rs"),
    )
    assert "--serde-output requires --ast-config" in output
    assert list(tmp_path.iterdir()) == []


def test_unparser_pyi_requires_the_unparser(tmp_path: pathlib.Path) -> None:
    """The unparser stub describes an unparser this invocation would not generate."""
    output = _run_expecting_error(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(tmp_path / "cst.rs"),
        "--protocol-module",
        PROTOCOL_MODULE,
        "--cst-pyi-output",
        str(tmp_path / "cst.pyi"),
        "--unparser-pyi-output",
        str(tmp_path / "unparser.pyi"),
    )
    assert "--unparser-pyi-output requires --unparser-output" in output
    assert list(tmp_path.iterdir()) == []


def test_a_late_generation_failure_writes_nothing(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The merged subcommand is all-or-nothing across artifacts, not just within one.

    A failure while generating the last artifact must not leave the earlier ones on disk: a
    half-updated generated tree still compiles against the previous CST, which is exactly the
    silent staleness the single-purpose subcommands' generate-then-write contract prevents.
    """

    message = "seeded serde generation failure"

    def _boom(*_args: object, **_kwargs: object) -> str:
        raise ValueError(message)

    monkeypatch.setattr(genparser, "generate_rust_serde_source", _boom)

    output = _run_expecting_error(
        "gen-rust-all",
        str(GRAMMAR),
        "--cst-output",
        str(tmp_path / "cst.rs"),
        "--parser-output",
        str(tmp_path / "parser.rs"),
        "--unparser-output",
        str(tmp_path / "unparser.rs"),
        "--ast-output",
        str(tmp_path / "ast.rs"),
        "--serde-output",
        str(tmp_path / "de.rs"),
        "--ast-config",
        str(FLTKAST),
        "--goal",
        GOAL,
        "--parser-mod-path",
        "super::parser",
        "--unparser-mod-path",
        "super::unparser",
        "--ast-mod-path",
        "super::ast",
    )
    assert message in output
    assert list(tmp_path.iterdir()) == []
