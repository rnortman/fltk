"""The Python interpreter version is spelled once, and every target that needs it names it.

`python.toolchain(is_default = True)` is honored only for the root module, so a public
`py_binary` without an explicit `python_version` resolves a *consumer's* default interpreter
and finds no matching wheel in the cp310-only pip hub — an analysis failure in a build this
repo never runs, at a target the consumer never named. The attribute is therefore mandatory
here, and a literal version rather than the shared constant is the same defect one bump later:
the target that kept the old spelling breaks only downstream.

The Starlark is read as Starlark-as-Python (`ast`), so the declared set comes from a parse
rather than a list restated here, over every BUILD file the target declares as data. The
`MODULE.bazel` half of the pin cannot `load()` the constant, and the packages this target is not
given as data are swept for a spelled-out version, by `make bazel-toolchain-guard` instead.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

RUNFILES_ROOT = pathlib.Path(__file__).parent.parent

#: Every BUILD file this test can see, which is what `tests/BUILD.bazel` declares as data.
#: A py_binary in an undeclared package is out of reach here; `make bazel-toolchain-guard`
#: sweeps every tracked Starlark file for a version literal to cover that.
BUILD_FILES = sorted(RUNFILES_ROOT.rglob("BUILD.bazel"))
CONSTANT_FILE = RUNFILES_ROOT / "bzl" / "python_version.bzl"
PYRIGHT_FILE = RUNFILES_ROOT / "bzl" / "pyright.bzl"

CONSTANT_NAME = "FLTK_PYTHON_VERSION"

#: An interpreter version literal, in any spelling Starlark and pyright both accept:
#: either quote, and a patch component `rules_python`'s `python.toolchain` also takes.
_VERSION_LITERAL = re.compile(r"['\"]3\.\d+(\.\d+)?['\"]")


def _pinned_version() -> str:
    """The one interpreter version, read out of the constant's own assignment."""
    for node in ast.parse(CONSTANT_FILE.read_text()).body:
        if isinstance(node, ast.Assign) and node.targets[0].id == CONSTANT_NAME:  # type: ignore[union-attr]
            assert isinstance(node.value, ast.Constant)
            return node.value.value
    pytest.fail(f"{CONSTANT_NAME} is not assigned in bzl/python_version.bzl")


def _py_binary_calls() -> dict[str, ast.Call]:
    """Every `py_binary` call in every visible BUILD file: `pkg:target` -> the call node."""
    calls: dict[str, ast.Call] = {}
    for build_file in BUILD_FILES:
        package = build_file.parent.relative_to(RUNFILES_ROOT).as_posix().removeprefix(".")
        for node in ast.walk(ast.parse(build_file.read_text())):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "py_binary":
                continue
            name = next(
                (
                    keyword.value.value
                    for keyword in node.keywords
                    if keyword.arg == "name" and isinstance(keyword.value, ast.Constant)
                ),
                None,
            )
            if name is None:
                pytest.fail(f"//{package}: py_binary at line {node.lineno} names itself with no string literal")
            calls[f"//{package}:{name}"] = node
    return calls


BINARIES = _py_binary_calls()


def test_the_build_files_declare_py_binaries_at_all() -> None:
    """A parse that finds nothing would satisfy every assertion below vacuously."""
    assert BINARIES, "no py_binary parsed out of any visible BUILD file"


@pytest.mark.parametrize("package", ["", "tests"])
def test_the_build_files_this_test_reads_are_the_ones_it_is_meant_to_read(package: str) -> None:
    """Data the BUILD file stops declaring would narrow the sweep silently."""
    assert RUNFILES_ROOT.joinpath(package, "BUILD.bazel") in BUILD_FILES, (
        f"//{package}:BUILD.bazel is not in this test's data, so its py_binary targets go unchecked"
    )


@pytest.mark.parametrize("target", sorted(BINARIES))
def test_every_py_binary_names_the_shared_interpreter_pin(target: str) -> None:
    """Explicit, and by constant: a literal here is a bump that lands in some targets only."""
    keywords = {keyword.arg: keyword.value for keyword in BINARIES[target].keywords}
    value = keywords.get("python_version")
    assert value is not None, (
        f"{target} declares no python_version, so a consumer's default interpreter wins and "
        f"the cp310-only wheels in @pypi have no matching distribution"
    )
    assert isinstance(value, ast.Name) and value.id == CONSTANT_NAME, (
        f"{target} spells its python_version out; use {CONSTANT_NAME} so one bump reaches every target"
    )


@pytest.mark.parametrize("build_file", BUILD_FILES, ids=lambda path: path.as_posix())
def test_the_build_files_carry_no_version_literal(build_file: pathlib.Path) -> None:
    """The constant is only a single source while nothing beside it spells the number."""
    strays = [line for line in build_file.read_text().splitlines() if _VERSION_LITERAL.search(line)]
    assert not strays, f"interpreter version literals in {build_file.name}: {strays}"


@pytest.mark.parametrize("spelling", ['"3.10"', "'3.10'", '"3.10.4"'])
def test_the_stray_literal_detector_reads_every_spelling(spelling: str) -> None:
    """The sweep above is the only guard on bzl/pyright.bzl; a narrowed regex disarms it."""
    assert _VERSION_LITERAL.search(f"    python_version = {spelling},")


def test_the_pyright_rule_defaults_to_the_shared_pin() -> None:
    """pyright's `pythonVersion` is the same pin: a second literal is a second thing to bump."""
    text = PYRIGHT_FILE.read_text()
    assert f'"python_version": attr.string(default = {CONSTANT_NAME})' in text, (
        "bzl/pyright.bzl's python_version default is not the shared constant"
    )
    strays = [line for line in text.splitlines() if _VERSION_LITERAL.search(line)]
    assert not strays, f"interpreter version literals in bzl/pyright.bzl: {strays}"


def test_the_pin_is_a_version_number() -> None:
    """Guards the parse above: a constant read as something else would fail open."""
    assert re.fullmatch(r"3\.\d+(\.\d+)?", _pinned_version()), _pinned_version()
