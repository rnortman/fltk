"""Packaging a compiled PyO3 cdylib as an importable Python extension module.

Internal: fltk's own BUILD files and `//:rust.bzl` load this. It is deliberately not part of the
consumer surface — a cdylib assembled outside fltk's module cannot compile the generated
`#[pyclass]` code, because the pyo3 instance `//crates/fltk-cst-core` links has no injection seam
the way `//crates/fltk-serde-core:serde` does. TODO(bazel-consumer-pyo3-seam). Consumers build
extensions with `fltk_pyo3_cdylib`.
"""

load("@rules_python//python:defs.bzl", "py_library")

def pyo3_extension_py_library(name, cdylib, data = [], visibility = None):
    """Wrap a PyO3 cdylib as an importable Python extension module.

    Two steps, and both carry an invariant that is invisible at build time and shows up as an
    ImportError or a silent pure-Python fallback at run time:

    1. **ABI3 rename**: rules_rust emits `lib<crate_name>.so`; CPython's stable-ABI loader
       wants `<name>.abi3.so` (the convention maturin produces for abi3-py310 builds).
       `$(location ...)` rather than `$<`, so an extra rules_rust output alongside the .so
       (debug info, say) cannot be picked up positionally.
    2. **py_library wrapper**: `imports = ["."]` puts the .so's directory on sys.path so
       `import <name>` resolves, and `@fltk//:native_py` rides along so `import fltk._native`
       does too — the generated cst.rs resolves the canonical Span type through it at run time
       and falls back to pure Python when it is absent.

    Used by fltk_pyo3_cdylib and by the in-tree fixture packages, which assemble their crates
    by hand (they need a cst-core flavor the public macro does not link, or host two grammars
    in one crate root) but package the result identically.

    Args:
        name: the public py_library name, and the .so stem: `<name>.abi3.so`. For an
            importable module this must be the module name.
        cdylib: label of the rust_shared_library producing the extension.
        data: extra files carried on the py_library (a PEP 561 stub package, say).
        visibility: visibility for the py_library; the rename genrule stays package-private.
    """
    native.genrule(
        name = name + "_so",
        srcs = [cdylib],
        outs = [name + ".abi3.so"],
        cmd = "cp $(location {cdylib}) $@".format(cdylib = cdylib),
    )

    py_library(
        name = name,
        data = [":" + name + "_so"] + data,
        deps = [Label("@fltk//:native_py")],
        imports = ["."],
        visibility = visibility,
    )
