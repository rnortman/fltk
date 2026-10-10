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

Recipes in the Makefile are thin call sites: shell with control flow — the step loop and the
no-pyo3 guard — lives in `scripts/`, where `tests/test_check_scripts.py` executes it under stub
binaries. What this module asserts about those two is the call: the arguments each recipe
passes. No test executes `make`.
"""

from __future__ import annotations

import fnmatch
import pathlib
import re
import shlex
import subprocess

from tests.retirement_scan import offenders, uncommented, workspace_files
from tests.uv_scan import names_uv

_REPO_ROOT = pathlib.Path(__file__).parent.parent
_MAKEFILE = _REPO_ROOT / "Makefile"

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


def _from(recipe: str, marker: str) -> str:
    """The recipe from ``marker`` onwards, asserting rather than raising when it is gone.

    A bare ``str.index`` on incidental recipe text turns a benign reshape into a
    ``ValueError`` in the test body, which sends the reader to the slicing code instead of to
    the property the test is named for.
    """
    assert marker in recipe, f"{marker!r} is gone from this recipe, so the test cannot locate its region: {recipe}"
    return recipe[recipe.index(marker) :]


def _guard_call(recipe: str) -> list[str]:
    """The ``scripts/pyo3-guard`` invocation in ``recipe``, as argv after the script path."""
    assert recipe.count("scripts/pyo3-guard") == 1, f"the recipe must call the shared guard exactly once: {recipe}"
    call = recipe[recipe.index("scripts/pyo3-guard") :]
    lines: list[str] = []
    for line in call.splitlines():
        lines.append(line.rstrip().removesuffix("\\").removesuffix(";"))
        if not line.rstrip().endswith("\\"):
            break
    return shlex.split(" ".join(lines))[1:]


def _option(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def test_both_lanes_call_the_shared_pyo3_guard() -> None:
    """One guard, two call sites: the attribution arm runs only on a red gate, so two copies of
    it diverge on the one day it must not be wrong. Each lane names itself in the messages."""
    for lane in ("bazel-test", "bazel-consumer-check"):
        argv = _guard_call(_recipe(lane))
        assert _option(argv, "--lane") == lane, f"{lane} calls the guard with the wrong --lane: {argv}"


def test_the_root_lane_passes_its_configuration_and_its_derived_labels() -> None:
    """`bazel test //...` cannot state "no pyo3", and a derivation that comes back empty must fail.

    The guard's cqueries run at the gate's own configuration, so the lane passes it; the label set
    is derived, not listed, so a new :no_python target or rust_binary is guarded the day it lands.
    """
    recipe = _recipe("bazel-test")
    argv = _guard_call(recipe)
    assert _option(argv, "--cquery-flags") == "--config lint", f"the guard must run at the gate's configuration: {argv}"
    assert _option(argv, "--control") == "//crates/fltk-cst-core:no_python", argv
    assert argv[-1] == "$$labels", f"the guard must run over the derived labels: {argv}"
    head = recipe[: recipe.index("scripts/pyo3-guard")]
    assert (
        'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...) union set(//tests:rust_gate_lib)'
        in head
    ), recipe
    assert 'test -n "$$labels"' in head, f"an empty target derivation must fail, not pass: {recipe}"
    assert "bazel cquery" not in recipe, f"the guard's cqueries belong in scripts/pyo3-guard: {recipe}"


def test_the_consumer_lane_passes_its_three_targets_and_the_cross_module_control() -> None:
    """The cross-module half, at the consumer's default configuration.

    The serde assertions stay on `deps(//:consumer_serde)` alone: over the union the property is
    satisfiable by any member. That is the lane's one configured cquery of its own; the guard's
    single green-path cquery is counted where it runs, in tests/test_check_scripts.py.
    """
    recipe = _recipe("bazel-consumer-check")
    argv = _guard_call(recipe)
    assert _option(argv, "--control") == "@fltk//crates/fltk-cst-core:no_python", argv
    assert "--cquery-flags" not in argv, f"the consumer module has no lint configuration to pass: {argv}"
    assert argv[-3:] == ["//:consumer_ast", "//:consumer_fmt_bin", "//:consumer_serde"], argv
    serde_step = _from(recipe, "deps(//:consumer_serde)")
    assert "consumer_crates.*:serde" in serde_step, f"the one-serde assertion went missing: {recipe}"
    assert "fltk_crates.*:serde" in serde_step, (
        f"the serde assertions must run against deps(//:consumer_serde), not the union: {recipe}"
    )
    assert recipe.count("bazel cquery") == 1, f"only the serde step's cquery belongs in this recipe: {recipe}"


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


def test_verbose_defaults_quiet_locally_and_verbose_in_ci() -> None:
    """The gate is unreadable in CI when it prints nothing until the end, and noisy locally."""
    text = _MAKEFILE.read_text()
    assert re.search(r"^VERBOSE \?= \$\(if \$\(filter true,\$\(CI\)\),1,0\)$", text, re.MULTILINE), (
        "VERBOSE must be `?=`-assigned from an exact `CI=true` match, so both the CI default "
        "and an explicit override hold"
    )


def test_check_common_is_a_call_site_for_the_step_script() -> None:
    """The step loop's control flow is executed by tests/test_check_scripts.py, not read here.

    `$(MAKE)` stays literally on the line: it is what makes GNU make treat the recipe as
    recursive, so `make -n check` still walks the steps and `-j`'s jobserver reaches them.
    """
    recipe = _recipe("check-common")
    body = [line for line in recipe.splitlines() if line.startswith("\t")]
    assert len(body) == 1, f"check-common must be one call into scripts/check-steps: {recipe}"
    argv = shlex.split(body[0].lstrip("\t@"))
    assert argv[0] == "scripts/check-steps", argv
    assert _option(argv, "--make") == "$(MAKE)", argv
    assert _option(argv, "--verbose") == "$(VERBOSE)", argv
    assert argv[-1] == "$(CHECK_STEPS)", argv
    for construct in ("for ", "if ", "mktemp"):
        assert construct not in body[0], f"{construct!r} is control flow; it belongs in scripts/check-steps: {recipe}"


#: Bazel verbs that never configure a target, so `--config lint` is meaningless for them.
#: Everything not named here configures, and a configured invocation without the gate's own
#: configuration is the analysis-cache discard this part exists to remove.
_LOADING_PHASE_VERBS = frozenset({"query"})


def _bazel_invocations(recipe: str) -> list[tuple[str, str]]:
    """Every ``bazel <verb> …`` in a recipe as (verb, the invocation up to its own end)."""
    found: list[tuple[str, str]] = []
    for match in re.finditer(r"(?<![\w.-])bazel ([a-z]+)\b", recipe):
        rest = recipe[match.start() :]
        ends = [rest.index(stop) for stop in ("; \\", "\n") if stop in rest]
        found.append((match.group(1), rest[: min(ends)] if ends else rest))
    return found


def test_root_gate_runs_one_configuration() -> None:
    """Alternating configurations mid-gate discards Bazel's in-memory analysis cache.

    Derived twice over. The *verbs* are derived: every `bazel <verb>` outside the loading-phase
    allowlist must carry the configuration, so a `bazel build` or `bazel run` added later cannot
    slip past a two-verb pattern. The *recipes* are derived from `CHECK_STEPS`, because that list
    is the Makefile's advertised extension point: a new step running a bare `bazel build` in the
    root workspace reintroduces the discard just as effectively as an edit to `bazel-test`.
    `bazel-consumer-check` is exempt — a separate workspace, its own server, and no `build:lint`
    block to name. The pyo3 guard's cqueries run inside `scripts/pyo3-guard`, out of this sweep's
    sight; that they carry the configuration is asserted by executing the script, in
    tests/test_check_scripts.py.
    """
    for step in check_steps():
        if step == "bazel-consumer-check":
            continue
        recipe = _recipe(step)
        unconfigured = [
            invocation
            for verb, invocation in _bazel_invocations(recipe)
            if verb not in _LOADING_PHASE_VERBS and "--config lint" not in invocation
        ]
        assert not unconfigured, f"{unconfigured} in {step} runs a second configuration: {recipe}"
    assert "bazel build --config lint //..." in _recipe("bazel-lint"), "bazel-lint must keep the same configuration"


def test_no_recipe_invokes_uv() -> None:
    """A `uv` call would be a second Python dependency writer."""
    invoking = [line for line in _MAKEFILE.read_text().splitlines() if line.startswith("\t") and names_uv(line)]
    assert not invoking, f"uv is retired but these recipe lines still invoke it: {invoking}"


def test_every_step_is_a_declared_phony_target() -> None:
    """A step named in the list but not built is a `make` failure the loop reports as the step's."""
    text = _MAKEFILE.read_text()
    phony = text[text.index(".PHONY:") : text.index("\n\n", text.index(".PHONY:"))].replace("\\\n", " ").split()
    for step in check_steps():
        assert step in phony, f"{step} is in CHECK_STEPS but not .PHONY"


def test_the_lane_notes_reach_the_steps_the_makefile_names() -> None:
    """`scripts/check-steps` keys its lane notes on step names that `CHECK_STEPS` defines.

    Run over the real list with `true` as the make program: a lane renamed on either side drops
    its note from every gate run, and the timing lines go back to reading as "lint is free".
    """
    result = subprocess.run(  # noqa: S603
        ["bash", str(_REPO_ROOT / "scripts" / "check-steps"), "--make", "true", "--verbose", "1", *check_steps()],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    noted = {
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := re.fullmatch(r"check-common: running (\S+) \[.+\]", line))
    }
    assert noted == {"bazel-test", "bazel-lint"}, f"the lane notes no longer land on bazel-test and bazel-lint: {noted}"


#: A configuration-dependent edge, by its call: `select(`, `config_setting(`, skylib's
#: `config_setting_group(` and its `selects.` family, which bottoms out in `select()`. A call
#: pattern rather than a word, because `.bzl` docstrings are strings the comment stripper keeps.
_SELECT = re.compile(r"\b(select|config_setting|config_setting_group)\s*\(|\bselects\s*\.")


def _tracked_starlark() -> list[pathlib.Path]:
    """The root module's own Starlark in the runfiles tree: every package's BUILD file (the probe
    roll-up carries each in) and every `.bzl`, the analysis-test macros included."""
    return workspace_files(_REPO_ROOT, "BUILD.bazel", "*.bzl")


def _select_hits(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if _SELECT.search(line)]


def test_the_select_matcher_sees_calls_and_not_prose() -> None:
    """A matcher that matches nothing passes the fence below; one that matches prose cries wolf."""
    for line in (
        'config_setting(name = "lint_on", flag_values = {":lint": "true"})',
        "    deps = select({...}),",
        "    deps = selects.with_or({...}),",
        "config_setting_group(",
    ):
        assert _select_hits([line]), f"matcher missed: {line}"
    for path in ("crates/fltk-cst-core/BUILD.bazel", "crates/fltk-parser-core/BUILD.bazel"):
        prose = [line for line in (_REPO_ROOT / path).read_text().splitlines() if "select()" in line]
        assert prose, f"{path} no longer explains why it has no select(); pick another prose fixture"
        hits = _select_hits([line for line in uncommented(_REPO_ROOT / path) if line.strip()])
        assert not hits, f"the prose in {path} must strip to nothing: {hits}"


def test_no_select_in_tracked_starlark() -> None:
    """No `select()` or `config_setting()` text in tracked Starlark, so no edge can switch on the
    lint configuration the root lane's pyo3 guard runs at. It does not see `label_flag`s: the one
    in `crates/fltk-serde-core/BUILD.bazel` is configurable, but no `.bazelrc` lint line sets it."""
    paths = _tracked_starlark()
    names = {str(path.relative_to(_REPO_ROOT)) for path in paths}
    for required in ("bzl/BUILD.bazel", "crates/fltk-cst-core/BUILD.bazel", "rust.bzl"):
        assert required in names, f"{required} is not in the scan set, so the fence is blind: {sorted(names)}"
    assert len(paths) > 10, f"the Starlark scan set collapsed to {sorted(names)}"
    hits = offenders(paths, _REPO_ROOT, lambda line: bool(_SELECT.search(line)), strip_comments=True)
    assert not hits, (
        "`make bazel-test`'s pyo3 guard runs at `--config lint` only, and the per-target control is a "
        "loading-phase query; both are sound because no `select()` exists in the tree (flavours are "
        "parallel targets — see `crates/fltk-cst-core/BUILD.bazel`). These lines introduce one: "
        f"{hits}. If it is needed, narrow this test to the configuration-independent cases and "
        "re-examine the residual in `scripts/pyo3-guard`'s header and `CLAUDE.md`; do not delete it."
    )
