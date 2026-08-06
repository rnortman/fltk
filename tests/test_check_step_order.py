"""The order of ``CHECK_STEPS`` in the Makefile, which two of its steps depend on to work.

A step that only *diffs* a generated file passes vacuously unless the step that *rewrites* that
file has already run: `check-locks` diffs a `Cargo.lock` the maturin builds under `test` re-resolve
in place, and `check-bazel-locks` diffs the two `MODULE.bazel.lock` files the Bazel lanes repair in
place (bzlmod's default `lockfile_mode` is `update`). Both orderings are stated in a comment above
the list, and a comment cannot fail: appending a new lockfile-rewriting step after
`check-bazel-locks` would silently restore the blind spot that gate was added to close — a stale
tracked lockfile that every gate run repairs locally and no gate run demands be committed.
"""

from __future__ import annotations

import pathlib

_MAKEFILE = pathlib.Path(__file__).parent.parent / "Makefile"


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


def test_the_bazel_lock_diff_is_the_last_step() -> None:
    """It has to see the repair the Bazel lanes make, and nothing after it may rewrite a lock."""
    steps = check_steps()
    assert steps[-1] == "check-bazel-locks", steps
    for lane in ("bazel-check", "bazel-consumer-check"):
        assert steps.index(lane) < steps.index("check-bazel-locks"), steps


def test_the_lockfile_diff_runs_after_the_step_that_rewrites_a_stale_lock() -> None:
    steps = check_steps()
    assert steps.index("test") < steps.index("check-locks"), steps


def test_every_step_is_a_declared_phony_target() -> None:
    """A step named in the list but not built is a `make` failure the loop reports as the step's."""
    text = _MAKEFILE.read_text()
    phony = text[text.index(".PHONY:") : text.index("\n\n", text.index(".PHONY:"))].replace("\\\n", " ").split()
    for step in check_steps():
        assert step in phony, f"{step} is in CHECK_STEPS but not .PHONY"
