"""The aux grammars whose generated Python modules `//:fltk` ships, declared once.

Every consumer of the grammar list — the `generate_parser` calls, the `:fltk_src` exclude
list, the parity gate, and the import test — derives from `AUX_GRAMMARS`.  Adding a grammar
is one entry; an omission from any consumer is a silent hole (the import test, for example,
fails open).

`cst_mod_path` is always `<pkg>.<base>_cst`; the generated CST module bakes
`from <cst_mod_path>_protocol import NodeKind` into its source, so that agreement with the
package the files land in is what makes the import work at all.
"""

load("//:rules.bzl", "generate_parser")

AUX_GRAMMARS = [
    struct(name = "bootstrap_py", grammar = "fltk/fegen/bootstrap.fltkg", base = "bootstrap", pkg = "fltk.fegen"),
    struct(name = "regex_py", grammar = "fltk/fegen/regex.fltkg", base = "regex", pkg = "fltk.fegen"),
    struct(name = "fltkast_py", grammar = "fltk/fegen/fltkast.fltkg", base = "fltkast", pkg = "fltk.fegen"),
    struct(name = "toy_py", grammar = "fltk/unparse/toy.fltkg", base = "toy", pkg = "fltk.unparse"),
    struct(
        name = "unparsefmt_py",
        grammar = "fltk/unparse/unparsefmt.fltkg",
        base = "unparsefmt",
        pkg = "fltk.unparse",
    ),
    struct(name = "fltklsp_py", grammar = "fltk/lsp/fltklsp.fltkg", base = "fltklsp", pkg = "fltk.lsp"),
]

# The four modules a `generate` invocation emits, as (filename suffix, a symbol the module
# always exposes).  The symbol is what the import test asks each module for; `NodeKind` on a
# CST module is the load-bearing one, since the CST module imports it from the protocol module
# rather than defining it — so the assertion also proves the baked dotted path resolves.
_SUFFIXES = [
    ("_cst", "NodeKind"),
    ("_cst_protocol", "NodeKind"),
    ("_parser", "Parser"),
    ("_trivia_parser", "Parser"),
]

def _out_dir(g):
    return g.pkg.replace(".", "/")

def _generated_py():
    paths = []
    for g in AUX_GRAMMARS:
        for suffix, _symbol in _SUFFIXES:
            paths.append(_out_dir(g) + "/" + g.base + suffix + ".py")
    return paths

def _module_args():
    args = []
    for g in AUX_GRAMMARS:
        for suffix, symbol in _SUFFIXES:
            args.append(g.pkg + "." + g.base + suffix + "=" + symbol)
    return args

# Source paths of the committed copies of the generated modules.
GENERATED_PY = _generated_py()

# The targets that produce them.
GENERATED_PY_TARGETS = [":" + g.name for g in AUX_GRAMMARS]

# `<dotted module>=<symbol>` pairs, the argv of the generated-module import test.
GENERATED_PY_MODULE_ARGS = _module_args()

def aux_generate_parsers(gen_tool):
    """Declare the `generate_parser` target for every aux grammar.

    Args:
        gen_tool: The generator binary label.  Must be the stage-0 generator: the full
            `:genparser` transitively imports the very modules these targets produce.
    """
    for g in AUX_GRAMMARS:
        generate_parser(
            name = g.name,
            src = g.grammar,
            base_name = g.base,
            cst_mod_path = g.pkg + "." + g.base + "_cst",
            gen_tool = gen_tool,
            out_dir = _out_dir(g),
        )
