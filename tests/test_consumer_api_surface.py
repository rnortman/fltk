"""What `//:rust.bzl` and the consumer guide publish, held to what a consumer can actually use.

`rust.bzl` and `rules.bzl` are the consumer-facing macro surface: a downstream module loads them
cross-module as `@fltk//:rust.bzl`, so every public name in them is API this repo owes
compatibility on, and every recipe in `docs/bazel-consumer-guide.md` is a thing a consumer is
told to copy.

`pyo3_extension_py_library` is the case that proves the rule needs a gate. A downstream module
cannot use it at all: a hand-assembled cdylib links its own pyo3 instance, not the one
`//crates/fltk-cst-core` links, so nothing built from the recipe works. It now lives in
`bzl/pyo3_ext.bzl`, an internal file `rust.bzl` may load and a consumer may not, and the guide
says self-assembled cdylibs are unsupported instead of printing a recipe. Both halves of that are
one edit away from coming back, which is what this file notices.

Delete these assertions when `TODO(bazel-consumer-pyo3-seam)` lands the seam and republishes the
recipe; until then a published-but-unusable macro is worse than no macro.
"""

from __future__ import annotations

import pathlib

_REPO_ROOT = pathlib.Path(__file__).parent.parent

_CONSUMER_MACRO_FILES = (_REPO_ROOT / "rules.bzl", _REPO_ROOT / "rust.bzl")
_CONSUMER_GUIDE = _REPO_ROOT / "docs" / "bazel-consumer-guide.md"

_UNPUBLISHED = "pyo3_extension_py_library"


def test_the_files_this_gate_reads_are_all_present() -> None:
    """A missing file makes every assertion below pass while checking nothing."""
    missing = [str(path) for path in (*_CONSUMER_MACRO_FILES, _CONSUMER_GUIDE) if not path.is_file()]
    assert not missing, f"the consumer-surface gate cannot read: {missing}"


def test_the_unusable_pyo3_macro_is_not_defined_on_the_consumer_surface() -> None:
    """Defining it in rust.bzl publishes it: a consumer loads that file whole."""
    defining = [
        str(path.relative_to(_REPO_ROOT)) for path in _CONSUMER_MACRO_FILES if f"def {_UNPUBLISHED}" in path.read_text()
    ]
    assert not defining, f"{_UNPUBLISHED} is back on the consumer surface, in {defining}; it belongs in bzl/"


def test_the_internal_home_of_the_pyo3_macro_still_exists() -> None:
    """The negative above is satisfied by deleting the macro outright, which is a different change."""
    internal = (_REPO_ROOT / "bzl" / "pyo3_ext.bzl").read_text()
    assert f"def {_UNPUBLISHED}" in internal, "bzl/pyo3_ext.bzl no longer defines the macro it was moved to hold"


def test_the_consumer_guide_prints_no_recipe_for_it() -> None:
    """A printed recipe is a promise; this one cannot compile in a downstream module."""
    hits = [
        f"{_CONSUMER_GUIDE.name}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(_CONSUMER_GUIDE.read_text().splitlines(), start=1)
        if _UNPUBLISHED in line
    ]
    assert not hits, f"the consumer guide names the unpublished macro again: {hits}"
