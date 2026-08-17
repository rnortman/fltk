"""The one `cargo` matcher, shared by the retirement gates that scan a command surface.

cargo is retired: nothing in this repo declares a cargo package, no check step or CI step
invokes the tool, and every Rust target is built by Bazel's own hermetic toolchain. Two
surfaces have to stay clear of an invocation — the CI workflow (`test_ci_workflow.py`) and the
Makefile, `.bazelrc`, agent-hook config and Starlark (`test_cargo_retirement.py`). Self-tested
in `test_cargo_retirement.py`.

Only *invocations* match. Prose is free to say cargo was retired, and the names of the
crate_universe artifacts (`cargo-bazel-lock.json`, `cargo-bazel-resolved.lock`,
`CARGO_BAZEL_REPIN`, `@fltk_crates`) are hyphenated or underscored spellings that no shell
would resolve to the binary; what may not survive is a command a reader could run or a step a
machine does run.
"""

from __future__ import annotations

import pathlib
import re

from tests import retirement_scan as scan

#: `cargo` as a command word, with an argument after it. Three shapes have to be hits, because
#: all three are how a machine with a host toolchain actually spells the binary:
#:
#: - bare (`cargo test`, `cargo  metadata`, a tab-separated `cargo\tfetch` in a recipe);
#: - path-qualified (`$HOME/.cargo/bin/cargo fetch`, `/usr/local/bin/cargo build`), which is the
#:   spelling used when the binary is not on `PATH`;
#: - hyphenated tool form (`cargo-deny check`, `cargo-nextest run`) — the same binaries, invoked
#:   without going through the `cargo` dispatcher.
#:
#: And the argument itself may be a subcommand (`test`), a toolchain selector (`+nightly`) or a
#: flag (`--version`), so the token after the command word is `[+\-a-z]` rather than a letter.
#:
#: What must stay clear of it is the hermetic crate_universe machinery, whose spellings sit in
#: live code: `cargo-bazel-lock.json` and `cargo-bazel-resolved.lock` are excluded by the
#: `-bazel` carve-out and by requiring whitespace after a bare `cargo`, `CARGO_BAZEL_REPIN` by
#: case, and `cargo_lockfile` by the `\s` too.
CARGO_INVOCATION = re.compile(r"(?<![\w.-])(?:[\w./~$-]*/)?cargo(?:-(?!bazel)[a-z][\w-]*)?\s+[+\-a-z]")

#: Invocation-like spellings without an argument after the command word: the tag that used to
#: make a py_test run outside the sandbox so it could reach a host toolchain, the rustup
#: toolchain installer action, and `cargo` (bare or path-qualified) as the last word of a line.
CARGO_ARTIFACT = re.compile(r"\brequires-cargo\b|\brust-toolchain@|(?<![\w.-])(?:[\w./~$-]*/)?cargo\s*$")


def names_cargo(line: str) -> bool:
    """True when the line invokes cargo or names one of the escape hatches it needed."""
    return bool(CARGO_INVOCATION.search(line) or CARGO_ARTIFACT.search(line))


def offenders(paths: list[pathlib.Path], root: pathlib.Path) -> list[str]:
    """Every `<path>:<lineno>: <line>` in `paths` that names cargo, relative to `root`.

    Comments are stripped: every surface scanned through here explains the retirement in prose,
    and "no cargo lane survives" has the shape of an invocation.
    """
    return scan.offenders(paths, root, names_cargo, strip_comments=True)
