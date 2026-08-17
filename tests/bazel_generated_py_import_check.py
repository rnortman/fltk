"""Import every Bazel-generated aux module from the runfiles copy of `//:fltk`.

The Starlark analysis tests in `tests/bazel_rules` assert where `generate_parser` *declares*
its outputs; nothing there proves the declared path is also where Python looks for the module.
That only holds when `out_dir` and `cst_mod_path` agree with the `imports` of the py_library
carrying the outputs, and it is the property every downstream `from fltk.unparse import
toy_cst` depends on.

Each module is imported by name and asked for one symbol the generator always emits, so a
truncated or empty file fails as loudly as a missing one.  For a CST module that symbol is
`NodeKind`, which it does not define: it imports it from `<cst_mod_path>_protocol`, so the
assertion also proves the dotted path baked into the generated source resolves under the real
package layout rather than only from a flat sys.path.

The modules to check arrive as `<dotted module>=<symbol>` arguments, derived by the target
from the single grammar list in `//bzl:aux_grammars.bzl`.  A hand-maintained copy here would
fail open — a newly added grammar would simply go unchecked.

Not named `*_test.py`: this is a py_test main, run directly rather than collected by pytest,
and the source-tree pytest run would import the committed copies instead of these.
"""

from __future__ import annotations

import importlib
import sys


def _expected(argv: list[str]) -> list[tuple[str, str]]:
    if not argv:
        msg = "no modules to check; expected <dotted.module>=<symbol> arguments"
        raise SystemExit(msg)
    pairs = []
    for arg in argv:
        module_name, separator, attribute = arg.partition("=")
        if not separator or not module_name or not attribute:
            msg = f"malformed argument {arg!r}; expected <dotted.module>=<symbol>"
            raise SystemExit(msg)
        pairs.append((module_name, attribute))
    return pairs


def main() -> None:
    expected = _expected(sys.argv[1:])
    failures: list[str] = []
    for module_name, attribute in expected:
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            failures.append(f"{module_name}: import failed: {exc!r}")
            continue
        if not hasattr(module, attribute):
            failures.append(f"{module_name}: no attribute {attribute!r}")

    if failures:
        detail = "\n  ".join(failures)
        message = f"{len(failures)} of {len(expected)} generated modules unusable:\n  {detail}"
        raise SystemExit(message)


if __name__ == "__main__":
    main()
