"""The `fltk-ast-core` manifest's two mirrored scalar-builtin declarations.

`uuid` and `rust_decimal` are declared twice: optional under `[dependencies]`, which is what a
Cargo consumer turns on with the `uuid`/`decimal` features, and unconditionally under
`[dev-dependencies]`, which is what gives the Bazel lane's `crate.from_cargo` hub a target for
each so `crates/fltk-ast-core/BUILD.bazel` can turn those features on.  The Bazel lane therefore
compiles the crate against whatever the dev-dependency resolves to, and the Cargo lane against
whatever the optional dependency resolves to; the two agreeing is the whole basis for treating
the Bazel build as equivalent.  Nothing in either build system checks that, so this does — the
same mechanical guard `make bazel-toolchain-guard` gives the other mirror in this repo.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

MANIFEST = pathlib.Path(__file__).parents[1] / "crates" / "fltk-ast-core" / "Cargo.toml"

MIRRORED_CRATES = ("uuid", "rust_decimal")
"""The two crates declared in both tables."""


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return tomllib.loads(MANIFEST.read_text())


@pytest.mark.parametrize("crate", MIRRORED_CRATES)
def test_the_dev_dependency_mirrors_the_optional_dependency(manifest: dict[str, Any], crate: str) -> None:
    """Drift here would build the Bazel lane against a different version or feature set."""
    dependency = manifest["dependencies"].get(crate)
    assert dependency is not None, f"{MANIFEST}: [dependencies] declares no {crate!r}"
    assert dependency.get("optional") is True, f"{crate} is no longer an optional dependency"
    mirror = manifest["dev-dependencies"].get(crate)
    assert mirror is not None, f"{MANIFEST}: [dev-dependencies] declares no {crate!r}"
    assert mirror == {key: value for key, value in dependency.items() if key != "optional"}
