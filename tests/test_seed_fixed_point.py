"""The self-hosting seed is a fixed point of the generator that produced it.

`fltk/fegen/{fltk_cst,fltk_cst_protocol,fltk_parser,fltk_trivia_parser}.py` are the one set
of generated modules that stays committed: the generator needs them to read any grammar
file, including `fegen.fltkg`, which is where they come from.  Nothing else can tell whether
that committed copy still matches what the current generator emits — a generator change with
no regeneration leaves a seed describing a language the code no longer implements.

This test closes that hole by regenerating the seed into a temp directory and byte-comparing.
Generation normalizes its own output, so the comparison is direct: no formatting step here,
and no second normalization implementation to drift from the first.

Failure means the seed is stale, not that the test is wrong.  Regenerate it and commit the
result together with the generator change.

TODO(bootstrap-fegen-chain): the seed stays committed only because the bootstrap system
cannot generate it today.
"""

from __future__ import annotations

import re
from pathlib import Path

from fltk.fegen import pybackend

_REPO_ROOT = Path(__file__).parent.parent
_SEED_DIR = _REPO_ROOT / "fltk" / "fegen"
_GRAMMAR = _SEED_DIR / "fegen.fltkg"

#: The exact argv shape the seed is regenerated with.  These values are mirrored by the
#: //:regen_seed target in BUILD.bazel, which is the entry point that writes the committed
#: seed; test_regen_seed_target_argv_matches is what fails when the two copies drift, since
#: a gate regenerating with different arguments than the writer proves nothing.
SEED_BASE_NAME = "fltk"
SEED_CST_MODULE = "fltk.fegen.fltk_cst"
SEED_FILES = (
    "fltk_cst.py",
    "fltk_cst_protocol.py",
    "fltk_parser.py",
    "fltk_trivia_parser.py",
)


def _regenerate(target: Path) -> list[Path]:
    return pybackend.generate(_GRAMMAR, SEED_BASE_NAME, SEED_CST_MODULE, output_dir=target)


def test_seed_files_are_present() -> None:
    """The four seed files exist where the generator writes them."""
    for name in SEED_FILES:
        assert (_SEED_DIR / name).is_file(), f"missing seed file {name}"


def test_generate_emits_exactly_the_seed_file_set(tmp_path: Path) -> None:
    """Regeneration writes those four files and nothing else.

    A generator that grew a fifth output would otherwise leave it uncommitted and unnoticed.
    """
    written = _regenerate(tmp_path)
    assert sorted(path.name for path in written) == sorted(SEED_FILES)
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(SEED_FILES)


def test_regen_seed_target_argv_matches() -> None:
    """`//:regen_seed` regenerates the seed with the same arguments this gate uses.

    The two copies live in different languages and cannot import each other, so this is the
    only place that can see both.  Without it, an edit to the BUILD target leaves the gate
    green against a seed the writer can no longer reproduce.
    """
    build_file = (_REPO_ROOT / "BUILD.bazel").read_text()
    stanza = re.search(r"^regen_seed\(\n(.*?)^\)", build_file, re.MULTILINE | re.DOTALL)
    assert stanza is not None, "no regen_seed(...) stanza in BUILD.bazel"
    attrs = dict(re.findall(r'^\s*(\w+) = "([^"]*)",$', stanza.group(1), re.MULTILINE))

    assert attrs.get("base_name") == SEED_BASE_NAME
    assert attrs.get("cst_mod_path") == SEED_CST_MODULE
    assert attrs.get("grammar") == str(_GRAMMAR.relative_to(_REPO_ROOT))
    assert attrs.get("out_dir") == str(_SEED_DIR.relative_to(_REPO_ROOT))


def test_committed_seed_is_a_fixed_point(tmp_path: Path) -> None:
    """Regenerating the seed reproduces the committed bytes exactly.

    No skip when ruff is missing: normalization is part of generation, ruff is a declared
    dependency of the generator, and a skipped gate is indistinguishable from a passing one
    in a suite summary — which is exactly how the seed-staleness hole would reopen.
    """
    _regenerate(tmp_path)

    stale = []
    for name in SEED_FILES:
        regenerated = (tmp_path / name).read_bytes()
        committed = (_SEED_DIR / name).read_bytes()
        if regenerated != committed:
            stale.append(name)

    assert not stale, (
        "committed seed is stale: "
        + ", ".join(stale)
        + ". Regenerate the seed from fltk/fegen/fegen.fltkg and commit the result "
        "alongside the generator change."
    )
