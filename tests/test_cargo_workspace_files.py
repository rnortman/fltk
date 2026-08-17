"""Every root-workspace member reaches the pytest compile gates.

The gates (`tests/test_generated_rust_gate.py` and friends) hand cargo a throwaway crate with
path dependencies on this repo, and cargo loads *every* member of the root workspace before it
resolves anything.  A member whose sources are not in the gates' runfiles is therefore not a
build error but a `cargo` "failed to read manifest", minutes into an unsandboxed `size = "large"`
test that most contributors never run locally.

Two hand-maintained lists have to agree for that not to happen: the `[workspace] members` in the
root `Cargo.toml`, and the `//:cargo_workspace_files` filegroup that names each member's
`cargo_gate_files` group.  Nothing in Bazel ties them together — adding a member is two edits in
two packages — so this is the join.  The BUILD file is read as Starlark-as-Python (`ast`), the
same way `tests/test_cli_binary_targets.py` reads it.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

_REPO_ROOT = pathlib.Path(__file__).parent.parent

MANIFEST = _REPO_ROOT / "Cargo.toml"
BUILD_FILE = _REPO_ROOT / "BUILD.bazel"

COLLECTION = "cargo_workspace_files"
"""The filegroup the compile-gate targets name in `data`."""

GATE_GROUP = "cargo_gate_files"
"""The per-member filegroup name `bzl/cargo_gate.bzl` declares."""


def _workspace_members() -> set[str]:
    """The root workspace's member directories, minus the root package itself ("." )."""
    members = tomllib.loads(MANIFEST.read_text())["workspace"]["members"]
    return {member for member in members if member != "."}


def _collected_labels() -> list[str]:
    """The string srcs of the `//:cargo_workspace_files` filegroup."""
    for node in ast.walk(ast.parse(BUILD_FILE.read_text())):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "filegroup":
            continue
        kwargs = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None}
        name = kwargs.get("name")
        if not isinstance(name, ast.Constant) or name.value != COLLECTION:
            continue
        srcs = kwargs["srcs"]
        # `srcs = [...] + glob([...])`: only the literal list carries labels.
        if isinstance(srcs, ast.BinOp):
            srcs = srcs.left
        return [element.value for element in srcs.elts if isinstance(element, ast.Constant)]
    pytest_message = f"//:{COLLECTION} is not declared in BUILD.bazel"
    raise AssertionError(pytest_message)


def _declared_modules(crate_root: pathlib.Path) -> list[str]:
    """The out-of-line, non-test `mod name;` declarations in a crate root.

    `#[cfg(test)]` modules are skipped: a dependency's test modules are never compiled, so
    their absence from a narrowed `srcs` list is not what breaks the gates.
    """
    modules: list[str] = []
    test_only = False
    for line in crate_root.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#[cfg(test)]"):
            test_only = True
            continue
        declaration = re.match(r"(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*;", stripped)
        if declaration is None:
            if stripped and not stripped.startswith(("#[", "//")):
                test_only = False
            continue
        if not test_only:
            modules.append(declaration.group(1))
        test_only = False
    return modules


def test_every_workspace_member_is_collected() -> None:
    """A new member with no `cargo_gate_files` entry fails here, not inside cargo."""
    collected = set(_collected_labels())
    missing = sorted(member for member in _workspace_members() if f"//{member}:{GATE_GROUP}" not in collected)
    assert not missing, (
        f"root workspace members with no //:{COLLECTION} entry: {missing}. "
        f"Add cargo_gate_files() to each one's BUILD file and the label to the collection."
    )


def test_nothing_collected_has_left_the_workspace() -> None:
    """The reverse: a group named for a directory the workspace no longer contains."""
    members = _workspace_members()
    stale = sorted(
        label
        for label in _collected_labels()
        if label.endswith(":" + GATE_GROUP) and label.removeprefix("//").removesuffix(":" + GATE_GROUP) not in members
    )
    assert not stale, f"//:{COLLECTION} names {stale}, which the root Cargo.toml no longer declares"


def test_each_collected_group_delivers_its_manifest_and_sources() -> None:
    """The groups are in this test's own runfiles, which is what the gates rely on.

    Reading the labels out of the BUILD file only proves they were written down; this proves the
    files they name arrive, because `//:cargo_workspace_files` is data of this target too.

    The sources matter as much as the manifest: `cargo_gate_files` takes an optional `srcs`
    list, so a package can narrow what it ships, and cargo builds the path dependency rather
    than merely reading its manifest. A truncated list is the same "failed to compile" minutes
    into a `size = "large"` gate that a missing filegroup would be.
    """
    for label in _collected_labels():
        if not label.endswith(":" + GATE_GROUP):
            continue
        package = label.removeprefix("//").removesuffix(":" + GATE_GROUP)
        manifest = _REPO_ROOT / package / "Cargo.toml"
        assert manifest.is_file(), f"{label} delivers no {package}/Cargo.toml"
        crate_root = _REPO_ROOT / package / "src" / "lib.rs"
        assert crate_root.is_file(), f"{label} delivers no {package}/src/lib.rs; cargo builds this crate"
        for module in _declared_modules(crate_root):
            source = crate_root.parent / f"{module}.rs"
            directory = crate_root.parent / module / "mod.rs"
            assert source.is_file() or directory.is_file(), (
                f"{label} delivers no source for `mod {module};` in {package}/src/lib.rs"
            )
