"""FLTK Rust Bazel rules.

This file provides:
  - generate_rust_parser: a rule that runs FLTK's Rust codegen on a grammar file
    and emits cst.rs + parser.rs as Bazel action outputs.
  - fltk_pyo3_cdylib: a macro that compiles those generated sources + a
    consumer-authored lib.rs into a PyO3 cdylib (rust_shared_library with
    extension-module), wrapped in a py_library that places the resulting .so on
    the correct import path and carries @fltk//:native_py so that
    `import fltk._native` resolves in the test sandbox.

Load this file to use the Rust-backend Bazel integration:
    load("@fltk//:rust.bzl", "generate_rust_parser", "fltk_pyo3_cdylib")

This file is intentionally separate from rules.bzl so that a pure-Python Bazel
consumer that never loads rust.bzl does not transitively require rules_rust to be
registered.
"""

load("@rules_rust//rust:defs.bzl", "rust_shared_library")
load("@rules_python//python:defs.bzl", "py_library")

# ---- generate_rust_parser -------------------------------------------------------

def _generate_rust_parser_impl(ctx):
    """Implementation for generate_rust_parser rule.

    Runs two separate genparser actions:
      1. gen-rust-cst  <grammar> <cst_out>
      2. gen-rust-parser <grammar> <parser_out> --cst-mod-path <path>

    Both actions are independent (no shared --output-dir).  The generated files
    use fixed basenames "cst.rs" and "parser.rs" so that bare `mod cst;` /
    `mod parser;` declarations in a co-located lib.rs resolve correctly.
    """
    grammar = ctx.file.src

    # Declare the two output files in a subdirectory named after the rule.
    cst_out = ctx.actions.declare_file(ctx.attr.name + "/cst.rs")
    parser_out = ctx.actions.declare_file(ctx.attr.name + "/parser.rs")

    # --- Action 1: gen-rust-cst ---
    cst_args = ctx.actions.args()
    cst_args.add("gen-rust-cst")
    cst_args.add(grammar)
    cst_args.add(cst_out)

    ctx.actions.run(
        inputs = [grammar],
        outputs = [cst_out],
        arguments = [cst_args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust CST for grammar %s" % grammar.short_path,
    )

    # --- Action 2: gen-rust-parser ---
    parser_args = ctx.actions.args()
    parser_args.add("gen-rust-parser")
    parser_args.add(grammar)
    parser_args.add(parser_out)
    parser_args.add("--cst-mod-path")
    parser_args.add(ctx.attr.cst_mod_path)

    ctx.actions.run(
        inputs = [grammar],
        outputs = [parser_out],
        arguments = [parser_args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust parser for grammar %s" % grammar.short_path,
    )

    return [DefaultInfo(files = depset([cst_out, parser_out]))]

generate_rust_parser = rule(
    implementation = _generate_rust_parser_impl,
    attrs = {
        "src": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "The FLTK grammar file (.fltkg).",
        ),
        "cst_mod_path": attr.string(
            default = "super::cst",
            doc = (
                "Rust module path passed to gen-rust-parser as --cst-mod-path. " +
                "Defaults to 'super::cst', which works when cst.rs and parser.rs " +
                "are siblings under the same crate root (the fltk_pyo3_cdylib macro " +
                "assembles exactly this layout). Override when you use a different " +
                "module hierarchy."
            ),
        ),
        "_gen_tool": attr.label(
            default = Label("//:genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
    doc = """Generate Rust CST and parser sources from an FLTK grammar file.

Emits two action outputs:
  <name>/cst.rs    — generated CST node classes (PyO3 Rust)
  <name>/parser.rs — generated parser (PyO3 Rust)

These files are designed to be consumed by fltk_pyo3_cdylib, which assembles
them alongside a consumer-authored lib.rs into a single crate directory and
compiles the result into a PyO3 cdylib.

The fixed basenames (cst.rs / parser.rs) are load-bearing: a consumer lib.rs
that contains `mod cst;` and `mod parser;` relies on these exact names.

Example:
    generate_rust_parser(
        name = "clockwork_rs_srcs",
        src  = "clockwork.fltkg",
        cst_mod_path = "super::cst",  # default; can omit
    )
""",
)

# ---- fltk_pyo3_cdylib -----------------------------------------------------------

def fltk_pyo3_cdylib(
        name,
        rs_srcs,
        lib_rs,
        deps = [],
        crate_features = [],
        recursion_limit = 512,
        visibility = None,
        **kwargs):
    """Compile generated Rust CST/parser sources + a consumer lib.rs into a PyO3 cdylib.

    The macro performs four steps:

    1. **Crate-source assembly**: copies lib.rs, cst.rs, and parser.rs into a
       single gendir so that bare `mod cst;` / `mod parser;` in lib.rs resolve.
       The generated files are Bazel action outputs (in a different directory
       from the consumer-authored lib.rs); without this assembly step, rustc
       would fail with "file not found for module `cst`".

    2. **Cdylib compilation**: compiles the assembled sources into a
       rust_shared_library (cdylib) with extension-module feature, linking
       @fltk//crates/fltk-cst-core and @fltk//crates/fltk-parser-core.

    3. **ABI3 rename**: renames the produced lib<name>.so to <name>.abi3.so.
       rules_rust emits lib<crate_name>.so; CPython's stable-ABI loader requires
       the abi3 suffix (the convention maturin produces for abi3-py310 builds).

    4. **py_library wrapper**: places <name>.abi3.so on the Python import path
       and carries @fltk//:native_py as a data dep so `import fltk._native`
       resolves inside any test sandbox that depends on this target (closing
       invariant #1: fltk._native must be importable by the consumer cdylib).

    Consumer lib.rs template:
        use fltk_cst_core::register_submodule;
        use pyo3::prelude::*;
        mod cst;    // generated cst.rs (resolved by macro crate-source assembly)
        mod parser; // generated parser.rs (same)

        #[pymodule]
        fn <name>(m: &Bound<'_, PyModule>) -> PyResult<()> {
            register_submodule(m, "cst", cst::register_classes)?;
            register_submodule(m, "parser", parser::register_classes)?;
            Ok(())
        }

    Note on recursion_limit: the macro injects `#![recursion_limit = "<N>"]` as
    the very first line of the assembled lib.rs, so consumer lib.rs files must
    NOT include their own `#![recursion_limit]` — the macro owns that line.

    Args:
        name: Module name. Must match the `#[pymodule]` fn name in lib_rs and
              the importable module name (e.g. "clockwork_native"). This becomes
              the crate name and the .so stem. Invariant: the `#[pymodule]` fn
              in lib_rs must have exactly this name.
        rs_srcs: Label of a generate_rust_parser target that provides cst.rs
                 and parser.rs as outputs (e.g. ":clockwork_rs_srcs").
                 WARNING: the assembly step copies every file from rs_srcs into
                 the crate gendir by basename AFTER writing lib.rs.  If rs_srcs
                 emits a file whose basename is "lib.rs" it will silently
                 overwrite the assembled crate root (losing the injected
                 recursion_limit and the consumer lib_rs content).  Always
                 pass a generate_rust_parser target here; do not pass a label
                 whose outputs include "lib.rs".
        lib_rs: Label or file of the consumer-authored lib.rs that declares
                `mod cst;`, `mod parser;`, and the `#[pymodule]` entry point.
        deps: Extra rust_library deps to link into the cdylib (for consumer
              native Rust code that coexists with the generated modules).
        crate_features: Extra crate features beyond the mandatory
                        ["extension-module"] the macro always adds.
        recursion_limit: Integer recursion limit injected as
                         `#![recursion_limit = "<N>"]` at the top of the
                         assembled crate root.  Default 512, which is sufficient
                         for grammars with deep recursive type references
                         (e.g. Clockwork's DFL expression chain).  Increase for
                         grammars with deeper recursion.  The symptom of too low
                         a limit is E0275 "overflow evaluating `Shared<X>: Send".
        visibility: Visibility for the resulting py_library target (name). The
                    intermediate targets are package-private.
        **kwargs: Forwarded to rust_shared_library (e.g. rustc_flags).
    """

    # Step 1: Crate-source assembly.
    #
    # We need lib.rs, cst.rs, and parser.rs in the same directory so that
    # bare `mod cst;` / `mod parser;` in lib.rs find their siblings.
    #
    # lib.rs is a consumer source file; cst.rs and parser.rs are outputs of
    # generate_rust_parser (in <rs_srcs_name>/cst.rs, <rs_srcs_name>/parser.rs
    # relative to the package gendir).
    #
    # Strategy: a single genrule that receives all three inputs and copies them
    # into a flat gendir.  We use `basename` in the shell command to strip the
    # <rs_srcs_name>/ prefix from the generated files.
    crate_lib_rs = name + "_crate_root/lib.rs"
    crate_cst_rs = name + "_crate_root/cst.rs"
    crate_parser_rs = name + "_crate_root/parser.rs"

    native.genrule(
        name = name + "_assemble_crate",
        srcs = [lib_rs, rs_srcs],
        outs = [crate_lib_rs, crate_cst_rs, crate_parser_rs],
        cmd = """
            OUTDIR=$$(dirname $(location {crate_lib_rs}))
            printf '#![recursion_limit = "{recursion_limit}"]\\n' > $$OUTDIR/lib.rs
            cat $(location {lib_rs}) >> $$OUTDIR/lib.rs
            for f in $(locations {rs_srcs}); do
                cp $$f $$OUTDIR/$$(basename $$f)
            done
            test -f $$OUTDIR/cst.rs || {{ echo "ERROR: cst.rs not produced by rs_srcs (expected basename cst.rs in outputs)"; exit 1; }}
            test -f $$OUTDIR/parser.rs || {{ echo "ERROR: parser.rs not produced by rs_srcs (expected basename parser.rs in outputs)"; exit 1; }}
        """.format(
            crate_lib_rs = crate_lib_rs,
            lib_rs = lib_rs,
            rs_srcs = rs_srcs,
            recursion_limit = recursion_limit,
        ),
    )

    # Step 2: Compile the cdylib.
    rust_shared_library(
        name = name + "_cdylib",
        srcs = [
            ":" + name + "_assemble_crate",
        ],
        crate_name = name,
        crate_root = ":" + crate_lib_rs,
        edition = "2021",
        # "extension-module" enables the pyo3 extension-module feature (no libpython link).
        # "python" must be set explicitly: Cargo would forward it via the feature definition
        # `extension-module = ["python", "pyo3/extension-module"]`, but Bazel crate_features
        # do not forward — each feature is set independently.  Without "python", the generated
        # register_classes symbols (gated on #[cfg(feature = "python")]) are compiled out and
        # the crate root's unconditional register_submodule calls fail to link.
        crate_features = ["extension-module", "python"] + crate_features,
        deps = [
            # Use Label() so these cross-repo labels are resolved relative to the FLTK module
            # (where this macro is defined), not the calling package.  In Bzlmod, string labels
            # passed to rule attrs in a macro are resolved at rule-instantiation time in the
            # caller's repository context, so bare "//crates/..." would resolve to
            # @clockwork//crates/... when called from Clockwork — which does not exist.
            Label("//crates/fltk-cst-core"),
            Label("//crates/fltk-parser-core"),
            Label("@fltk_crates//:pyo3"),
        ] + deps,
        **kwargs
    )

    # Step 3: ABI3 rename: lib<name>.so -> <name>.abi3.so.
    # rules_rust produces lib<crate_name>.so; CPython expects the abi3 suffix.
    # Use $(location ...) rather than $< to avoid positional ambiguity if rules_rust
    # ever emits additional files alongside the .so (e.g. debug info).
    abi3_so = name + ".abi3.so"
    native.genrule(
        name = name + "_so",
        srcs = [":" + name + "_cdylib"],
        outs = [abi3_so],
        cmd = "cp $(location :{cdylib}) $@".format(cdylib = name + "_cdylib"),
    )

    # Step 4: py_library wrapper.
    # - data: the consumer cdylib .abi3.so, placed on the Python path so
    #   `import <name>` resolves.
    # - deps: @fltk//:native_py, which transitively brings fltk/_native.abi3.so
    #   onto the path so `import fltk._native` resolves (invariant #1: the
    #   generated cst.rs resolves the canonical Span type via fltk._native at
    #   runtime; without native_py in the sandbox the pure-Python fallback fires).
    py_library(
        name = name,
        data = [":" + name + "_so"],
        deps = [Label("@fltk//:native_py")],
        imports = ["."],
        visibility = visibility,
    )
