"""Shared BUILD scaffolding for fltk's two-flavor runtime crates.

Each runtime crate ships two `rust_library` targets with the same `crate_name`: the
default one, which carries pyo3 (directly, or through the fltk-cst-core edge), and
`:no_python`, which a pure-Rust consumer links. The two differ only in which flavor of
the fltk deps they name — everything else must stay identical, and a dep or feature
added to one flavor alone breaks nothing in-tree (the cdylib path still builds) while
breaking pure-Rust consumers out-of-tree. Emitting both from one macro call is what
makes that divergence unrepresentable.

Loaded by fltk's own crate BUILD files only, never by a consumer, so the
"no bazel_skylib in consumer-loaded .bzl" rule (MODULE.bazel) does not reach it.
"""

load("@rules_rust//rust:defs.bzl", "rust_library", "rust_test")

_EDITION = "2021"

def _flavor_label_violation(label):
    """Return the non-bare fltk_deps label message, or None.

    Bare labels only: `//crates/fltk-cst-core:something` already names a flavor, and
    appending to it would silently produce a nonexistent target.
    """
    if ":" in label:
        return ("fltk_runtime_library: fltk_deps take bare package labels (the macro derives " +
                "the :no_python flavor); got '{}'.".format(label))
    return None

def _no_python_flavor(label):
    """The `:no_python` sibling of a bare package label (fails on a non-bare one)."""
    msg = _flavor_label_violation(label)
    if msg != None:
        fail(msg)
    return label + ":no_python"

def fltk_runtime_library(
        name,
        crate_name,
        srcs,
        features = [],
        python_features = [],
        fltk_deps = [],
        hub_deps = [],
        python_deps = [],
        test_deps = []):
    """Emit a runtime crate's two library flavors plus the unit-test target.

    Args:
      name: the default (pyo3-carrying) target's name. The other flavor is always
        `:no_python`, the label pure-Rust consumers and this macro's own dep
        derivation both depend on.
      crate_name: the Rust crate name, shared by both flavors.
      srcs: the source list, evaluated by the caller (glob is package-scoped).
      features: crate features both flavors turn on.
      python_features: features only the default flavor turns on (just fltk-cst-core's
        `python` today).
      fltk_deps: bare labels of other fltk runtime crates. The default flavor takes them
        as written; `:no_python` takes their `:no_python` flavor.
      hub_deps: @fltk_crates labels both flavors take.
      python_deps: deps only the default flavor takes (pyo3).
      test_deps: extra deps for the unit-test target (dev-dependencies).

    The tests ride the `:no_python` flavor, which is the whole feature set for every
    crate whose python-gated code is a pyclass surface with no unit tests of its own.
    A crate that does need its tests run at the python feature set declares its own
    `rust_test` beside this call — see `//crates/fltk-cst-core:python_test`. That works
    because the @fltk_crates hub unifies pyo3's `extension-module`, so such a binary
    links no libpython and needs no interpreter at build or run time; without that
    unification it would need non-hermetic PYO3_PYTHON wiring a Bazel sandbox cannot
    supply. Note `crate = ":<lib>"` is not a shortcut for it: rust_test does not inherit
    crate_features, so it would silently produce a second copy of the `:no_python`
    binary.
    """
    rust_library(
        name = name,
        srcs = srcs,
        crate_features = features + python_features,
        crate_name = crate_name,
        edition = _EDITION,
        visibility = ["//visibility:public"],
        deps = fltk_deps + hub_deps + python_deps,
    )

    rust_library(
        name = "no_python",
        srcs = srcs,
        crate_features = features,
        crate_name = crate_name,
        edition = _EDITION,
        visibility = ["//visibility:public"],
        deps = [_no_python_flavor(dep) for dep in fltk_deps] + hub_deps,
    )

    rust_test(
        name = "no_python_test",
        crate = ":no_python",
        deps = test_deps,
    )

# Not public API. Exported solely for //tests/bazel_rules.
runtime_crate_internals = struct(
    flavor_label_violation = _flavor_label_violation,
    no_python_flavor = _no_python_flavor,
)
