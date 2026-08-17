"""The ``CHECK_STEPS`` order the Makefile's lock gates depend on, and ``check-cargo-lock``' coverage.

A step that only *diffs* a generated file passes vacuously unless the step that *rewrites* that
file has already run: `check-bazel-locks` diffs the two `MODULE.bazel.lock` files the Bazel lanes
repair in place (bzlmod's default `lockfile_mode` is `update`). That ordering is stated in a
comment above the list, and a comment cannot fail: appending a new lockfile-rewriting step after
`check-bazel-locks` would silently restore the blind spot that gate was added to close — a stale
tracked lockfile that every gate run repairs locally and no gate run demands be committed.

`Cargo.lock` has no rewriting step at all, so `check-cargo-lock` probes each manifest with
`cargo metadata --locked` itself. Both that probe and the diff derive their manifests from the
tracked `Cargo.lock` set rather than naming them, so neither can go blind to a lock the tree
gained — which is what the tests below hold in place.
"""

from __future__ import annotations

import pathlib
import re

from tests.uv_scan import names_uv

_MAKEFILE = pathlib.Path(__file__).parent.parent / "Makefile"

#: The shape of a legal step: a Bazel lane, or a diff of a tracked lockfile. `bazel test //...`
#: runs the tests and `bazel build --config lint //...` runs the linters, so a step outside this
#: shape is either a duplicate of something in the build graph or a lane that belongs in it.
_STEP_SHAPE = re.compile(r"\Abazel-[a-z-]+\Z|\Acheck-[a-z-]+-locks?\Z")

#: The lanes the gate is *for*. Adding a step is a one-file edit; dropping one of these is not.
_REQUIRED_STEPS = ("bazel-toolchain-guard", "bazel-test", "bazel-lint", "bazel-consumer-check")


def check_steps() -> list[str]:
    """The ``CHECK_STEPS`` list, in the order ``check-common`` runs it."""
    text = _MAKEFILE.read_text()
    start = text.index("CHECK_STEPS :=")
    assignment = text[start + len("CHECK_STEPS :=") :]
    lines: list[str] = []
    for line in assignment.splitlines():
        lines.append(line.removesuffix("\\"))
        if not line.rstrip().endswith("\\"):
            break
    return " ".join(lines).split()


def test_no_cargo_build_test_or_lint_lane_comes_back() -> None:
    """`bazel test`/`bazel build --config lint` own that work; a cargo lane would duplicate it."""
    cargo = [step for step in check_steps() if step.startswith("cargo-")]
    assert not cargo, f"{cargo} is a cargo lane in CHECK_STEPS: the Bazel lanes already run that work"


def test_every_step_is_a_bazel_lane_or_a_lock_diff() -> None:
    """The gate's two jobs. Anything else belongs in the build graph, not beside it."""
    strays = [step for step in check_steps() if not _STEP_SHAPE.match(step)]
    assert not strays, f"{strays} is neither a `bazel-*` lane nor a `check-*-lock` diff"


def test_the_gate_still_runs_every_bazel_lane() -> None:
    """Dropping a lane silently shrinks what `make check` covers to whatever remains."""
    steps = check_steps()
    missing = [step for step in _REQUIRED_STEPS if step not in steps]
    assert not missing, f"CHECK_STEPS no longer runs {missing}, so `make check` stopped covering it"


def test_both_lock_diffs_are_in_the_gate() -> None:
    """A lock nothing diffs is a tracked file every local run repairs and no run demands."""
    diffs = {step for step in check_steps() if step.startswith("check-")}
    assert diffs == {"check-cargo-lock", "check-bazel-locks"}, diffs


def test_the_bazel_lock_diff_is_the_last_step() -> None:
    """It has to see the repair the Bazel lanes make, and nothing after it may rewrite a lock."""
    steps = check_steps()
    assert steps[-1] == "check-bazel-locks", steps
    for lane in ("bazel-test", "bazel-consumer-check"):
        assert steps.index(lane) < steps.index("check-bazel-locks"), steps


def _check_cargo_lock_recipe() -> str:
    text = _MAKEFILE.read_text()
    start = text.index("\ncheck-cargo-lock:")
    return text[start : text.index("\n\n", start)]


def test_both_halves_of_the_cargo_gate_derive_their_manifests_from_git() -> None:
    """Neither half may carry a hand-written list: a list covers only what it happens to name.

    Both the staleness probe and the diff take the tracked `Cargo.lock` set from `git ls-files`,
    so a crate that later regains a tracked lock is picked up by both at once. A literal path in
    the recipe is the failure mode this replaces — two hand-written lists that agree with each
    other and not with the tree.
    """
    recipe = _check_cargo_lock_recipe()
    assert recipe.count("git ls-files '*Cargo.lock'") == 2, recipe
    assert "$${lock%Cargo.lock}Cargo.toml" in recipe, f"the probed manifest must come from the lock: {recipe}"
    assert "--manifest-path $$manifest" in recipe, f"the probe must take the derived manifest: {recipe}"
    assert "git diff --exit-code -- $$(git ls-files '*Cargo.lock')" in recipe, recipe

    # A path spelled out in a command is a list that has to be maintained; the messages are
    # prose and may name whatever they like.
    words = [word.strip(";\\'\"") for word in recipe.split() if not word.startswith("FAIL:")]
    named = [word for word in words if "/" in word and word.endswith(("Cargo.toml", "Cargo.lock"))]
    assert not named, f"check-cargo-lock names {named} literally instead of deriving it: {recipe}"


def test_the_cargo_gate_fails_rather_than_passing_on_an_empty_derivation() -> None:
    """A derived list that resolves to nothing must be an error, not a green vacuous run."""
    recipe = _check_cargo_lock_recipe()
    assert 'test -n "$$locks"' in recipe, recipe


def test_the_dependabot_cargo_directories_are_derived_from_the_same_locks() -> None:
    """The updater's directory list is the one restatement of the tracked-lock set.

    A crate that regains a tracked lock is probed and diffed by this gate but gets no
    dependency updates until the updater names it too, and nothing else pairs the two files.
    """
    recipe = _check_cargo_lock_recipe()
    assert ".github/dependabot.yml" in recipe, f"nothing pairs the updater to the tracked locks: {recipe}"
    assert 'test -n "$$declared"' in recipe, f"an empty parse must fail rather than compare equal: {recipe}"
    assert 'test "$$derived" = "$$declared"' in recipe, recipe


def _recipe(target: str) -> str:
    text = _MAKEFILE.read_text()
    start = text.index(f"\n{target}:")
    return text[start : text.index("\n\n", start)]


def test_the_pyo3_guard_survives_in_the_bazel_test_recipe() -> None:
    """`bazel test //...` cannot state this property, and no step name carries it.

    A `:no_python` graph that has picked up pyo3 builds and tests exactly like one that has
    not, so a green run witnesses nothing without this explicit check.
    """
    recipe = _recipe("bazel-test")
    assert 'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...)' in recipe, recipe
    assert 'test -n "$$labels"' in recipe, f"an empty target derivation must fail, not pass: {recipe}"
    assert "fltk-cst-core:no_python" in recipe, f"the positive control is what proves the cquery ran: {recipe}"
    assert "grep -qi pyo3" in recipe, recipe


def test_the_pyo3_guard_survives_in_the_consumer_recipe() -> None:
    """The cross-module half of the same property, over the consumer's own three targets."""
    recipe = _recipe("bazel-consumer-check")
    for target in ("//:consumer_ast", "//:consumer_fmt_bin", "//:consumer_serde"):
        assert target in recipe, f"{target} lost its pyo3 cquery: {recipe}"
    assert "fltk-cst-core:no_python" in recipe, f"the positive control is what proves the cquery ran: {recipe}"
    assert "grep -qi pyo3" in recipe, recipe
    assert "consumer_crates.*:serde" in recipe, f"the one-serde assertion went missing: {recipe}"
    assert "fltk_crates.*:serde" in recipe, recipe


def test_no_recipe_invokes_uv() -> None:
    """A `uv` call would be a second Python dependency writer."""
    offenders = [line for line in _MAKEFILE.read_text().splitlines() if line.startswith("\t") and names_uv(line)]
    assert not offenders, f"uv is retired but these recipe lines still invoke it: {offenders}"


def test_every_step_is_a_declared_phony_target() -> None:
    """A step named in the list but not built is a `make` failure the loop reports as the step's."""
    text = _MAKEFILE.read_text()
    phony = text[text.index(".PHONY:") : text.index("\n\n", text.index(".PHONY:"))].replace("\\\n", " ").split()
    for step in check_steps():
        assert step in phony, f"{step} is in CHECK_STEPS but not .PHONY"
