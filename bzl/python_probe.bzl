"""Compile one compile-gate case's generated `cst.rs` at the `python` feature set.

`//tests:rust_gate_lib` builds every case with no features, so each `#[cfg(feature = "python")]`
item in a generated `cst.rs` is compiled out there and nothing else in the tree builds these
grammars with pyo3 linked. A probe is that same file — copied from the gate crate's own output,
not generated a second time, because "the file the gate compiles" is the probe's whole claim —
in a crate of its own with the python-flavored `fltk-cst-core` and the `@fltk_crates//:pyo3`
every extension links. rlib only, so no interpreter is linked.

Compiling is the assertion: a bare std spelling no name list mentions, a pyo3 macro expansion
that stops being hygienic, or a `use` the gated half needs and does not get, fails the build.
The `build_test` is what makes `bazel test //...` build a crate carrying no `#[test]`; clippy
comes from the lint aspect that sweeps every rust target.

One macro rather than a copied block per case: the wiring (feature set, edition, dep list) is
what a probe *means*, and a stale copy of it still compiles — just not at the configuration
anyone believes it covers. For the same reason the feature itself is asserted rather than
assumed: every probe gets a `crate_features_test` over its compile action's argv, so a probe
that stops passing `python` to rustc reds a test instead of building the gated half away.
"""

load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_rust//rust:defs.bzl", "rust_library")
load(":crate_features_test.bzl", "crate_features_test")

def python_feature_probe(name, case):
    """Declare the genrule, rust_library, build_test and feature-argv test for one case's probe.

    Args:
      name: the `rust_library` target name; the genrule and the two tests derive theirs from it.
      case: the `tests/rust_gate_cases.py` case name, i.e. the gate crate module holding the
        `cst.rs` this probe compiles.
    """
    srcs_name = name + "_srcs"
    lib_rs = name + "/src/lib.rs"
    cst_rs = name + "/src/cst.rs"

    native.genrule(
        name = srcs_name,
        srcs = ["rust_gate/src/" + case + "/cst.rs"],
        outs = [lib_rs, cst_rs],
        cmd = "echo 'pub mod cst;' > $(location " + lib_rs + ") && " +
              "cp $(location rust_gate/src/" + case + "/cst.rs) $(location " + cst_rs + ")",
    )

    rust_library(
        name = name,
        srcs = [":" + srcs_name],
        crate_features = ["python"],
        crate_name = "fltk_" + name,
        crate_root = lib_rs,
        edition = "2021",
        deps = [
            "//crates/fltk-cst-core",
            "@fltk_crates//:pyo3",
        ],
    )

    build_test(
        name = name + "_build_test",
        targets = [":" + name],
    )

    crate_features_test(
        name = name + "_feature_test",
        target_under_test = ":" + name,
        expected_features = ["python"],
    )
