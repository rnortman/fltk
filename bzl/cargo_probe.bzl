"""The per-package half of the Cargo retirement gate's declaration probe.

`tests/test_cargo_retirement.py` fails on the *presence* of a Cargo manifest, lock, audit policy
or host-toolchain pin. A glob only sees its own package, so the root package alone cannot witness
a manifest re-appearing under `crates/` or a fixture directory — and such a manifest is not inert:
one that carries its own `[workspace]` table is a complete workspace on its own.

So every package declares its own probe and the root rolls them up into `//:cargo_file_probe`,
whose files land in the gate's runfiles tree where the walk finds them. Each probe carries its
package's `BUILD.bazel` too, which is what gives the gate's other half — the scan for invocations
and for the tag that used to let a target reach a host toolchain — the same per-package reach with
no second list to keep in step.

Bounds worth knowing: a package that never calls this macro ships nothing into the gate's
runfiles, which is why `make bazel-test` sweeps the build graph for packages with no probe — a
runfiles walk cannot see an opt-out. `tests/bazel_consumer` is out of reach either way: it is its
own Bazel module and `.bazelignore`d, so no target here can name its files at all.
"""

# A manifest, a lock, the audit policy, or the host-toolchain pin: what a Cargo workflow needs
# in the tree. tests/test_cargo_retirement.py holds its own list against this one.
CARGO_FILENAMES = [
    "Cargo.toml",
    "Cargo.lock",
    "deny.toml",
    "rust-toolchain.toml",
]

def cargo_file_probe(name = "cargo_file_probe", srcs = []):
    """Declare this package's retirement probe.

    Args:
      name: the target name; the default is what the root package's roll-up expects.
      srcs: extra labels to fold in — the sub-package probes, for the root's roll-up.
    """
    native.filegroup(
        name = name,
        srcs = native.glob(
            ["**/" + filename for filename in CARGO_FILENAMES],
            allow_empty = True,
        ) + ["BUILD.bazel"] + srcs,
        # The root package rolls the sub-probes up; //tests is where the gate reading them lives.
        visibility = [
            "//:__pkg__",
            "//tests:__pkg__",
        ],
    )
