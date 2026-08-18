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


def _from(recipe: str, marker: str) -> str:
    """The recipe from ``marker`` onwards, asserting rather than raising when it is gone.

    A bare ``str.index`` on incidental recipe text turns a benign reshape into a
    ``ValueError`` in the test body, which sends the reader to the slicing code instead of to
    the property the test is named for.
    """
    assert marker in recipe, f"{marker!r} is gone from this recipe, so the test cannot locate its region: {recipe}"
    return recipe[recipe.index(marker) :]


def test_the_pyo3_guard_survives_in_the_bazel_test_recipe() -> None:
    """`bazel test //...` cannot state this property, and no step name carries it.

    A `:no_python` graph that has picked up pyo3 builds and tests exactly like one that has
    not, so a green run witnesses nothing without this explicit check.
    """
    recipe = _recipe("bazel-test")
    assert 'attr(name, "^no_python$$", //...) union kind("rust_binary rule", //...)' in recipe, recipe
    assert 'test -n "$$labels"' in recipe, f"an empty target derivation must fail, not pass: {recipe}"
    assert "deps(set(" in recipe, f"the pyo3 assertion must run over the union, not one cquery per target: {recipe}"
    _assert_the_union_carries_its_own_control(recipe)
    assert "grep -qi pyo3" in recipe, recipe


def _assert_the_union_carries_its_own_control(recipe: str) -> None:
    """The union cquery's *own* output has to be shown to be a real graph.

    A bare "fltk-cst-core:no_python is mentioned somewhere in this recipe" is satisfied by the
    per-target `rdeps` control alone, which is a different query over a different (unconfigured)
    graph: the configured half could be deleted with the suite green, and a union cquery that
    printed nothing would then pass `! grep -qi pyo3` vacuously.
    """
    union = _from(recipe, "deps(set(")
    assert "\"$$graph\" | grep -q 'fltk-cst-core:no_python'" in union, (
        f"the union cquery's own output must be checked for the runtime crate: {recipe}"
    )


def test_the_positive_control_stays_per_target_in_both_lanes() -> None:
    """A negative assertion over a graph that is not what you think it is passes vacuously.

    The control is what rules that out, and it has to hold for *every* derived target: over a
    union, one member reaching the runtime crates satisfies it for all the others, so a target
    that stopped reaching them at all — retargeted, stubbed, aliased somewhere harmless — would
    go on passing "no pyo3" while proving nothing. `rdeps(set(...), X)` names every member that
    reaches X, which restores the per-target fact in one query rather than one per target.
    """
    for lane, universe in (("bazel-test", "$$labels"), ("bazel-consumer-check", "$$targets")):
        recipe = _recipe(lane)
        control = _from(recipe, "rdeps(set(")
        expression = re.match(r"rdeps\(set\((?P<universe>.*?)\), (?P<reached>[^)]+)\)", control)
        assert expression is not None, f"{lane}'s control is not an rdeps over a target set: {recipe}"
        assert universe in expression.group("universe"), (
            f"{lane}'s control must run over the same derived target set its pyo3 assertion does: {recipe}"
        )
        assert expression.group("reached").endswith("//crates/fltk-cst-core:no_python"), (
            f"{lane}'s control names no runtime crate to reach: {recipe}"
        )
        assert re.search(r"for target in \$\$\w+; do", control), (
            f"{lane} must require the control of every derived target, not of the set: {recipe}"
        )
        assert 'grep -qxF "$$target"' in control, (
            f"{lane} must match each target against a whole line of the rdeps output: {recipe}"
        )


def test_the_pyo3_guard_attributes_a_union_failure_and_still_fails() -> None:
    """A union hit names no target, so the per-target loop survives as the failure path.

    The `exit 1` sits after the loop unconditionally: the union already proved pyo3 is
    reachable, so the loop disagreeing is itself a failure — a fallback that could turn a
    red union result green would be worse than none.
    """
    for lane in ("bazel-test", "bazel-consumer-check"):
        recipe = _recipe(lane)
        attribution = _from(recipe, "grep -qi pyo3; then")
        assert "for target in $$" in attribution, f"{lane} lost its per-target attribution loop: {recipe}"
        assert re.search(r"done; \\\n\s*exit 1;", attribution), (
            f"{lane}'s attribution fallback must fail unconditionally after the loop: {recipe}"
        )


def _passing_path(recipe: str) -> str:
    """The recipe minus the per-target attribution block, which runs only on a red gate."""
    attribution = _from(recipe, "grep -qi pyo3; then")
    assert "fi; \\" in attribution, f"the attribution block never closes its `if`: {recipe}"
    head = recipe[: recipe.index("grep -qi pyo3; then")]
    return head + attribution[attribution.index("fi; \\") :]


def test_a_green_gate_run_pays_one_configured_cquery_per_graph() -> None:
    """The batched shape is the whole point of the guard's reshape, and only a count states it.

    Re-adding the per-target `cquery deps($target)` loop to the *passing* path satisfies every
    other assertion here — `deps(set(` is still there, so are the controls and the attribution
    block — while restoring the ~60s of serial cquery dispatch this gate was measured to lose to
    it. The per-target control is held to a loading-phase `bazel query` for the same reason: as a
    `cquery` it costs ~25s to prove a fact about the unconfigured graph.
    """
    for lane, cqueries in (("bazel-test", 1), ("bazel-consumer-check", 2)):
        passing = _passing_path(_recipe(lane))
        assert passing.count("bazel cquery") == cqueries, (
            f"{lane}'s passing path runs {passing.count('bazel cquery')} configured cqueries, not {cqueries}: {passing}"
        )
        assert 'bazel query "rdeps(set(' in passing, (
            f"{lane}'s positive control must stay a loading-phase query, not a cquery: {passing}"
        )


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
    """The cross-module half of the same property, over the consumer's own three targets.

    Batched into one union cquery like the root lane's. The serde assertions stay on
    `deps(//:consumer_serde)` alone: over the union the property is satisfiable by any member.
    """
    recipe = _recipe("bazel-consumer-check")
    for target in ("//:consumer_ast", "//:consumer_fmt_bin", "//:consumer_serde"):
        assert target in recipe, f"{target} lost its pyo3 cquery: {recipe}"
    assert "deps(set(" in recipe, f"the pyo3 assertion must run over the union, not one cquery per target: {recipe}"
    _assert_the_union_carries_its_own_control(recipe)
    assert "grep -qi pyo3" in recipe, recipe
    serde_step = _from(recipe, "deps(//:consumer_serde)")
    assert "consumer_crates.*:serde" in serde_step, f"the one-serde assertion went missing: {recipe}"
    assert "fltk_crates.*:serde" in serde_step, (
        f"the serde assertions must run against deps(//:consumer_serde), not the union: {recipe}"
    )


def test_verbose_defaults_quiet_locally_and_verbose_in_ci() -> None:
    """The gate is unreadable in CI when it prints nothing until the end, and noisy locally."""
    text = _MAKEFILE.read_text()
    assert re.search(r"^VERBOSE \?= \$\(if \$\(filter true,\$\(CI\)\),1,0\)$", text, re.MULTILINE), (
        "VERBOSE must be `?=`-assigned from an exact `CI=true` match, so both the CI default "
        "and an explicit override hold"
    )


# TODO(check-common-executable-coverage): every assertion over the `check-common` recipe below is
# a grep on Makefile text, so the shell it describes is never run — a VERBOSE comparison against
# the wrong token, a failure that does not propagate, or a broken arithmetic expansion all pass.
def test_quiet_mode_buffers_and_dumps_on_failure() -> None:
    """Quiet must stay quiet only about a *passing* step.

    A buffered failure whose buffer is never printed says a step failed with no reason why.
    """
    recipe = _recipe("check-common")
    quiet = _quiet_arm(recipe)
    assert "tmpfile=$$(mktemp)" in quiet, recipe
    assert '>"$$tmpfile" 2>&1' in quiet, f"the quiet path must still buffer the step's output: {recipe}"
    assert 'cat "$$tmpfile"' in quiet, f"a buffered failure must dump its buffer: {recipe}"
    assert "FAILED: $$step" in quiet, recipe


def _quiet_arm(recipe: str) -> str:
    """The buffering arm of ``check-common``, located by what it does rather than by `else`."""
    return _from(recipe, "tmpfile=$$(mktemp)")


def _verbose_arm(recipe: str) -> str:
    """The streaming arm: from the VERBOSE test up to where the buffering arm begins."""
    branch = _from(recipe, '[ "$(VERBOSE)" = "1" ]')
    return branch[: branch.index("tmpfile=$$(mktemp)")] if "tmpfile=$$(mktemp)" in branch else branch


def test_verbose_mode_streams() -> None:
    """Verbose mode streams each step's output as it runs.

    No redirect at all — a tee or tmpfile would put Bazel's progress UI behind a pipe.
    The `FAILED: $$step` trailer stays in both arms so grepping for it works either way.
    """
    recipe = _recipe("check-common")
    assert '[ "$(VERBOSE)" = "1" ]' in recipe, f"check-common must branch on VERBOSE: {recipe}"
    verbose = _verbose_arm(recipe)
    assert re.search(r"\$\(MAKE\) \$\$step \|\| \{ echo \"FAILED: \$\$step", verbose), (
        f"the verbose arm must run the step unredirected and still print the FAILED trailer: {recipe}"
    )
    assert "mktemp" not in verbose and '>"$$tmpfile"' not in verbose, (
        f"the verbose arm must not buffer the step's output: {recipe}"
    )


def test_every_step_reports_its_wall_time() -> None:
    """Step-granular wall time, the answer to "why is `make check` slow".

    The echoes sit outside the VERBOSE branch — available in both modes, not just the one
    where you happened to suspect a problem.
    """
    recipe = _recipe("check-common")
    assert "check-common: running $$step" in recipe, f"no heartbeat when a step starts: {recipe}"
    passed = "check-common: $$step passed in"
    assert passed in recipe, f"no per-step wall time when a step passes: {recipe}"
    assert re.search(r'fi; \\\n\s*echo "check-common: \$\$step passed in', recipe), (
        f"the timing echo must follow the `fi` closing the VERBOSE branch, so both modes reach it: {recipe}"
    )
    quiet = _quiet_arm(recipe)
    assert passed not in quiet[: quiet.rindex("fi; \\")], (
        f"the timing echo sits inside the buffering arm, so verbose runs report no timing: {recipe}"
    )
    assert "gate_start" in recipe, f"the whole gate's wall time is the number the developer quotes: {recipe}"


def test_a_failing_step_reports_its_wall_time_too() -> None:
    """A failed gate that took forever is the case where the number matters most.

    A step that died three seconds in and one that hung for twenty minutes end a CI log the
    same way otherwise, and the gate total never prints at all on a failure.
    """
    recipe = _recipe("check-common")
    for mode, arm in (("verbose", _verbose_arm(recipe)), ("quiet", _quiet_arm(recipe))):
        failure = _from(arm, "FAILED: $$step")
        failure = failure[: failure.index("\n")]
        assert "step_start" in failure, f"the {mode} arm's failure line reports no step duration: {recipe}"
        assert "gate_start" in failure, f"the {mode} arm's failure line reports no gate total: {recipe}"


def test_the_heartbeat_says_which_step_carries_the_lint_surface() -> None:
    """The step names no longer partition the work, so the timings need saying so.

    `bazel test --config lint //...` builds every lint target, which leaves `bazel-lint` a
    cache-hit confirmation. Unannotated, the pair reads as "linting takes two seconds" and
    points the next person optimizing the gate at the wrong lane.
    """
    recipe = _recipe("check-common")
    for step in ("bazel-test", "bazel-lint"):
        assert re.search(rf'{step}\) note="[^"]+";;', recipe), (
            f"{step}'s heartbeat carries no note about what its time covers: {recipe}"
        )
    assert recipe.count("$$note") >= 2, f"the note must ride both the start and the timing line: {recipe}"


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
    block to name.
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
    offenders = [line for line in _MAKEFILE.read_text().splitlines() if line.startswith("\t") and names_uv(line)]
    assert not offenders, f"uv is retired but these recipe lines still invoke it: {offenders}"


def test_every_step_is_a_declared_phony_target() -> None:
    """A step named in the list but not built is a `make` failure the loop reports as the step's."""
    text = _MAKEFILE.read_text()
    phony = text[text.index(".PHONY:") : text.index("\n\n", text.index(".PHONY:"))].replace("\\\n", " ").split()
    for step in check_steps():
        assert step in phony, f"{step} is in CHECK_STEPS but not .PHONY"
