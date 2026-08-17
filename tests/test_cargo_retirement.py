"""cargo is retired, and this is what makes that a property rather than a state.

The all-Bazel migration left cargo alive in three narrow roles — a supply-chain gate, a
lockfile probe, and three compile-gate tests that handed a throwaway crate to a host toolchain.
All three are gone: the compile gates are `rust_test`/`build_test` targets, the third-party
crates are `crate.spec` declarations in `MODULE.bazel`, and the resolution is repinned by the
cargo binary inside rules_rust's hermetic toolchain. Nothing in the tree declares a cargo
package anymore, so there is nothing for a host cargo to build, test or audit.

That is worth a gate because the failure is silent. A test that shells out to a host toolchain
passes on the machine that has one and fails on the machine that does not, and the tree looks
green either way — which is exactly how the retired gates behaved, and why one of them was red
in CI alone for as long as it was.

Two halves, because there are two ways back:

- **The declaration half.** `//:cargo_file_probe` globs the manifest and policy filenames and
  the gate is the *absence* of matches: any file it picks up lands in this target's runfiles,
  where the walk below finds it. A glob sees only its own package, so every package declares a
  probe and the root rolls them up (`bzl/cargo_probe.bzl`) — a manifest under `crates/` is not
  inert, since one carrying its own `[workspace]` table is a whole workspace on its own.
- **The invocation half.** The Makefile, the CI workflow, `.bazelrc`, the agent-hook config and
  the Starlark that builds this repo — every BUILD file the probes carry plus the `.bzl` helpers
  — scanned with comments stripped: every one of them can carry a command, and prose about the
  retirement must not be what turns this red.

What neither half reaches from inside a runfiles tree is a package that never declares a probe:
it ships no files here, so nothing to scan is the same as nothing to find. That one is covered
from outside, by the query sweep in `make bazel-test` that fails on any package with no
`cargo_file_probe`. What stays out of reach entirely is `tests/bazel_consumer`, which is its own
Bazel module and `.bazelignore`d, so no target here can name its files.
"""

from __future__ import annotations

import ast
import pathlib

from tests.cargo_scan import CARGO_ARTIFACT, CARGO_INVOCATION, names_cargo, offenders
from tests.retirement_scan import strip_comment

_REPO_ROOT = pathlib.Path(__file__).parent.parent

#: What a cargo workflow needs in the tree: a manifest, a lock, the audit policy, or the host
#: toolchain pin. The probes glob exactly these.
_RETIRED_FILENAMES = ("Cargo.toml", "Cargo.lock", "deny.toml", "rust-toolchain.toml")

_MAKEFILE = _REPO_ROOT / "Makefile"
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_BAZELRC = _REPO_ROOT / ".bazelrc"
_AGENT_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_STARLARK = (_REPO_ROOT / "rules.bzl", _REPO_ROOT / "rust.bzl", *sorted((_REPO_ROOT / "bzl").glob("*.bzl")))


#: Where third-party crate sources land in the runfiles tree. Every crates.io package ships a
#: manifest, so the walks below have to stop at the workspace's own files or they report pyo3's.
_NOT_OURS = ("bazel-out", "external")


def _ours(path: pathlib.Path) -> bool:
    return path.is_file() and path.relative_to(_REPO_ROOT).parts[0] not in _NOT_OURS


def _build_files() -> list[pathlib.Path]:
    """Every package BUILD file in the runfiles tree — i.e. every one a probe carried in."""
    return sorted(path for path in _REPO_ROOT.rglob("BUILD.bazel") if _ours(path))


def test_no_retired_cargo_file_reaches_the_runfiles_tree() -> None:
    """The probes are globs, so what they declare is whatever the tree holds — ideally nothing."""
    found = [
        str(path.relative_to(_REPO_ROOT))
        for path in _REPO_ROOT.rglob("*")
        if path.name in _RETIRED_FILENAMES and _ours(path)
    ]
    assert not found, f"cargo is retired but these files are back in the tree: {found}"


def test_the_probe_declares_every_retired_filename() -> None:
    """A probe that stopped globbing a name would let that file back in unseen.

    Read off the macro that every package's probe calls rather than restated as a list this test
    also owns: the assertion is that the declaration and this scan cover the same names.
    """
    declared = (_REPO_ROOT / "bzl" / "cargo_probe.bzl").read_text()
    start = declared.index("CARGO_FILENAMES = [")
    for name in _RETIRED_FILENAMES:
        assert f'"{name}"' in declared[start : declared.index("]", start)], f"the probe does not glob {name}"


def _rolled_up_probes() -> list[str]:
    """The sub-package probe labels the root `cargo_file_probe(srcs = [...])` names."""
    text = (_REPO_ROOT / "BUILD.bazel").read_text()
    start = text.index("cargo_file_probe(srcs = [") + len("cargo_file_probe(srcs = ")
    return ast.literal_eval(text[start : text.index("])", start) + 1])


def test_the_probe_reaches_every_package_that_declares_one() -> None:
    """The roll-up is a list, and a list is what goes stale.

    Each probe carries its own package's BUILD file, so the BUILD files in this target's
    runfiles are exactly the packages actually watched. Held to the roll-up itself rather than
    to a number this test also owns: a floor stops moving the day a package is added, and a
    roll-up entry dropped afterwards takes its package out of *both* halves of this gate — the
    file scan and the invocation scan — with the floor still satisfied.
    """
    packages = _build_files()
    assert len(packages) == len(_rolled_up_probes()) + 1, (
        f"the roll-up names {_rolled_up_probes()} plus the root, but the runfiles hold {packages}"
    )
    unprobed = [str(path.relative_to(_REPO_ROOT)) for path in packages if "cargo_file_probe(" not in path.read_text()]
    assert not unprobed, f"these packages reached the runfiles without declaring a probe: {unprobed}"


def test_the_makefile_invokes_no_cargo() -> None:
    """`make check` is the gate; a cargo step in it is a host-toolchain dependency for everyone."""
    hits = offenders([_MAKEFILE], _REPO_ROOT)
    assert not hits, f"cargo is retired but these Makefile lines still invoke it: {hits}"


def test_the_ci_workflow_invokes_no_cargo() -> None:
    """The one lane a developer never runs locally, so a cargo step there fails only in CI."""
    hits = offenders([_WORKFLOW], _REPO_ROOT)
    assert not hits, f"cargo is retired but the CI workflow still names it: {hits}"


def test_the_bazel_config_invokes_no_cargo() -> None:
    """`.bazelrc` can name a tool in an --action_env or a --run_under, for every invocation."""
    hits = offenders([_BAZELRC], _REPO_ROOT)
    assert not hits, f"cargo is retired but .bazelrc still names it: {hits}"


def test_the_agent_hook_config_invokes_no_cargo() -> None:
    """A hook fires per file edit, outside every gate; it is the least visible lane there is."""
    hits = [line for line in _AGENT_SETTINGS.read_text().splitlines() if names_cargo(line)]
    assert not hits, f"cargo is retired but .claude/settings.json still names it: {hits}"


def test_no_build_file_or_starlark_helper_invokes_cargo_or_leaves_the_sandbox_for_it() -> None:
    """`requires-cargo` is scanned too: it is the tag that made a target unsandboxed.

    A genrule or test action can invoke the tool directly, and a `local`/`requires-cargo`
    target is how one reaches a host toolchain at all. Both belong to the same violation.
    """
    paths = _build_files() + [path for path in _STARLARK if path.is_file()]
    assert len(paths) > 5, f"the Starlark scan set collapsed to {paths}"
    hits = offenders(paths, _REPO_ROOT)
    assert not hits, f"cargo is retired but this Starlark still reaches for it: {hits}"


def test_the_scanned_files_are_all_present() -> None:
    """Every scan above is vacuous if its file did not reach the runfiles tree."""
    missing = [
        str(path) for path in (_MAKEFILE, _WORKFLOW, _BAZELRC, _AGENT_SETTINGS, *_STARLARK) if not path.is_file()
    ]
    assert not missing, f"the cargo retirement scan cannot read: {missing}"


def test_the_matcher_recognizes_the_recipes_it_replaced() -> None:
    """A pattern that matches nothing passes every scan above."""
    retired = (
        "\tcargo deny --manifest-path Cargo.toml check --config deny.toml",
        "        cargo metadata --locked --format-version 1 --manifest-path $$manifest >/dev/null \\",
        "        run: cargo fetch --locked",
        '        cmd = "cargo clippy --all-targets -- -D warnings",',
        '    tags = ["local", "requires-cargo"],',
        "      - uses: dtolnay/rust-toolchain@e97e2d8cc328f1b50210efc529dca0028893a2d9",
        "CARGO=cargo",
        # Path-qualified, toolchain-selected and hyphenated-tool spellings: the three ways
        # a host toolchain is invoked besides bare `cargo <subcommand>`.
        "\t$$HOME/.cargo/bin/cargo fetch --locked",
        "        run: /usr/local/bin/cargo build --offline",
        "        run: cargo +nightly clippy",
        "\tcargo +1.97.1 test",
        "\tcargo --locked metadata",
        "\tcargo --version",
        "\tcargo-deny check --config deny.toml",
        "        run: cargo-nextest run",
        "CARGO=/usr/local/bin/cargo",
    )
    for line in retired:
        assert names_cargo(line), f"matcher missed: {line}"

    # Prose is not in this set: callers strip comments first, precisely because "no cargo lane
    # survives" has the shape of an invocation. What must not match is the hermetic
    # crate_universe machinery, whose spellings sit in live code.
    allowed = (
        "    git diff --exit-code -- MODULE.bazel.lock cargo-bazel-lock.json cargo-bazel-resolved.lock",
        "CARGO_BAZEL_REPIN=1 bazel test //...",
        '        "@fltk_crates//:pyo3",',
        '    cargo_lockfile = "//:cargo-bazel-resolved.lock",',
        '    lockfile = "//:cargo-bazel-lock.json",',
        "crate.from_specs(",
        "          path: ~/.cargo/registry",
    )
    for line in allowed:
        assert not names_cargo(line), f"matcher over-matched: {line}"


def test_the_comment_stripper_does_not_hide_a_command_inside_a_string() -> None:
    """The scans strip comments, and a naive stripper is a hole in every one of them."""
    assert names_cargo(strip_comment("    cmd = \"sed 's/x/y/' $< > $@ # keep && cargo build\","))
    assert not names_cargo(strip_comment("# The retired lane ran cargo build here."))
    assert not names_cargo(strip_comment("\tbazel test //...  # replaced cargo test"))


def test_the_two_matcher_halves_are_both_load_bearing() -> None:
    """Either half alone leaves a hole the other cannot see."""
    assert CARGO_INVOCATION.search("cargo build") and not CARGO_ARTIFACT.search("cargo build")
    assert CARGO_ARTIFACT.search('tags = ["requires-cargo"]')
    assert not CARGO_INVOCATION.search('tags = ["requires-cargo"]')
