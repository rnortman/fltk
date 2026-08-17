"""The ``CHECK_STEPS`` order the Makefile's lock gate depends on, and the shape of the gate.

A step that only *diffs* a generated file passes vacuously unless the step that *rewrites* that
file has already run: `check-bazel-locks` diffs the tracked Bazel-written locks — the two
`MODULE.bazel.lock` files the Bazel lanes repair in place (bzlmod's default `lockfile_mode` is
`update`) and each workspace's crate_universe pair, which a repin rewrites. That ordering is
stated in a comment above the list, and a comment cannot fail: appending a new
lockfile-rewriting step after `check-bazel-locks` would silently restore the blind spot that
gate was added to close — a stale tracked lockfile that every gate run repairs locally and no
gate run demands be committed.

`check` and `check-ci` are aliases. A divergence between the two lanes is a defect, not a
policy, which is what `test_the_two_lanes_do_not_diverge` holds in place.
"""

from __future__ import annotations

import fnmatch
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


def test_the_lock_diff_is_in_the_gate() -> None:
    """A lock nothing diffs is a tracked file every local run repairs and no run demands."""
    diffs = {step for step in check_steps() if step.startswith("check-")}
    assert diffs == {"check-bazel-locks"}, diffs


def test_the_lock_diff_derives_its_file_set_from_git() -> None:
    """A hand-written list covers only what it happens to name.

    A third Bazel workspace, or a second crate_universe hub in an existing one, brings tracked
    locks that a listed recipe never diffs and that every local run repairs in place — the
    blind spot this step exists to close, reopened for anything outside the list. So the recipe
    derives the set with `git ls-files`, and a derivation that comes back empty has to fail
    rather than diff nothing successfully.
    """
    recipe = _recipe("check-bazel-locks")
    for pattern in ("'*MODULE.bazel.lock'", "'*cargo-bazel-lock.json'", "'*cargo-bazel-resolved.lock'"):
        assert "git ls-files" in recipe and pattern in recipe, f"{pattern} is not derived from git: {recipe}"
    assert 'test -n "$$locks"' in recipe, f"an empty lock derivation must fail, not pass: {recipe}"
    assert "git diff --exit-code -- $$locks" in recipe, f"the diff must run over the derived set: {recipe}"


def test_the_derivation_patterns_still_reach_every_tracked_lock() -> None:
    """The glob patterns themselves can go blind; this is what notices.

    Each of these is rewritten by a lane above the diff step and by nothing else — bzlmod
    repairs a stale `MODULE.bazel.lock` in place, and a repin rewrites the crate_universe pair.
    The derivation above is what makes a *new* one covered; this is what makes a pattern that
    stopped matching a *known* one fail.
    """
    patterns = ("*MODULE.bazel.lock", "*cargo-bazel-lock.json", "*cargo-bazel-resolved.lock")
    for lock in (
        "MODULE.bazel.lock",
        "cargo-bazel-lock.json",
        "cargo-bazel-resolved.lock",
        "tests/bazel_consumer/MODULE.bazel.lock",
        "tests/bazel_consumer/cargo-bazel-lock.json",
        "tests/bazel_consumer/cargo-bazel-resolved.lock",
    ):
        assert any(fnmatch.fnmatch(lock, pattern) for pattern in patterns), (
            f"{lock} is tracked and Bazel-written but no derivation pattern matches it"
        )


def test_the_two_lanes_do_not_diverge() -> None:
    """`check-ci` is an alias. A step on one lane alone is coverage only one of them has."""
    text = _MAKEFILE.read_text()
    assert re.search(r"^check: check-common$", text, re.MULTILINE), text[: text.index("\nfix:")]
    assert re.search(r"^check-ci: check$", text, re.MULTILINE), text[: text.index("\nfix:")]


def test_the_bazel_lock_diff_is_the_last_step() -> None:
    """It has to see the repair the Bazel lanes make, and nothing after it may rewrite a lock."""
    steps = check_steps()
    assert steps[-1] == "check-bazel-locks", steps
    for lane in ("bazel-test", "bazel-consumer-check"):
        assert steps.index(lane) < steps.index("check-bazel-locks"), steps


def test_the_toolchain_guard_derives_its_mirror_set_and_fails_on_an_empty_one() -> None:
    """The Rust version pin has one home and every other module mirrors it.

    A module with no `rust.toolchain` tag rides rules_rust's default compiler over the same
    source with nothing objecting, so the guard reads the pin out of the root MODULE.bazel and
    holds every tracked module that names rules_rust to it. The set is derived from git rather
    than listed, and a derivation covering only the root — which compares equal to itself — is
    a guard checking nothing and must fail.
    """
    recipe = _recipe("bazel-toolchain-guard")
    assert "MODULE.bazel" in recipe and "rust-toolchain.toml" not in recipe, recipe
    assert "git ls-files 'MODULE.bazel' '*/MODULE.bazel'" in recipe, recipe
    assert 'test "$$checked" -gt 1' in recipe, f"the guard must require a mirror beyond the root: {recipe}"


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


def test_the_probe_coverage_sweep_survives_in_the_bazel_test_recipe() -> None:
    """The cargo retirement gate cannot see a package that declares no probe.

    That gate reads a runfiles tree, which a package reaches only through its own
    `cargo_file_probe`; a package that never declares one carries a manifest and a cargo
    invocation with every test green. Only a query over the build graph sees the opt-out.
    """
    recipe = _recipe("bazel-test")
    assert 'attr(name, "^cargo_file_probe$$", //...)' in recipe, recipe
    assert "--output package" in recipe, f"the sweep compares packages, not labels: {recipe}"
    assert 'test -n "$$probed"' in recipe, f"an empty probe derivation must fail, not pass: {recipe}"


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
