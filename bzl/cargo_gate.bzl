"""The files cargo reads off disk for one root-workspace member.

The pytest compile gates (`tests/BUILD.bazel`, `_CARGO_GATE`) hand cargo a throwaway crate with
path dependencies on this repo, and cargo loads *every* workspace member's manifest before it
resolves anything. So each member has to put its manifest and sources in those tests' runfiles,
and `//:cargo_workspace_files` collects the groups.

Stated as a macro because the content is the same for every member and the failure mode is not a
build error: a missing group fails minutes into an unsandboxed `size = "large"` gate, as a cargo
"failed to read manifest". `tests/test_cargo_workspace_files.py` is the other half — it checks
that every member the root manifest declares actually has its group in the collection.
"""

def cargo_gate_files(srcs = None, name = "cargo_gate_files"):
    """Declare the compile gates' filegroup for the calling workspace member.

    Args:
        srcs: the crate's Rust sources; defaults to the same `src/**/*.rs` glob the crate's
            library targets use. Pass the package's existing source list where it has one, so
            the set is stated once.
        name: the filegroup name; the collection in the root package expects the default.
    """
    native.filegroup(
        name = name,
        srcs = ["Cargo.toml"] + (native.glob(["src/**/*.rs"]) if srcs == None else srcs),
        visibility = ["//:__pkg__"],
    )
