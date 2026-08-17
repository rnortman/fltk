"""No emitted `cst.rs` or `ast.rs` line names a std item without its path.

A grammar rule name becomes an UpperCamel item at module scope in the generated CST and AST
modules, and Rust resolves a module's own item before the prelude — so a rule named `option` turns
every bare `Option<…>` in that module into a type error in a file the consumer cannot edit. The two
emitters therefore spell std items absolute through the table in `fltk.fegen.rust_emit`.

The `prelude` case in `tests/rust_gate_cases.py` compiles a grammar whose rule names are
the std prelude's, which is the strongest witness there is — but it witnesses only the emission
sites that grammar instantiates, and only the halves of `cst.rs` the gate crate's feature set
compiles: it never enables `python`, so every `#[cfg(feature = "python")]` emission is compiled out
of it. The pyo3 half of that same file is compiled by `//tests:prelude_python_probe`, which is not
bounded by a name list: it fails on a bare std name nobody thought to add below. Two scans here
close what neither compilation reaches:

- the emitters' own Rust strings, so an emission site no grammar in the suite reaches is covered
  too (`.map(Box::new)` on an optional boxed hoist has no occurrence in any committed artifact);
- the generated artifacts of every in-tree crate, so an emission site the emitter scan reads as
  prose is covered as real output.

Only the two shadowable emitters are scanned. `parser.rs`, `unparser*.rs` and `de.rs` declare no
grammar-derived module-level item and reach the CST and AST types through `use super::…` aliases,
so their bare spellings cannot be shadowed and stay bare by design.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).parent.parent

# The emitters whose output declares grammar-derived items at module scope.
_SHADOWABLE_EMITTERS = ("fltk/fegen/gsm2tree_rs.py", "fltk/fegen/gsm2ast_rs.py")

# Every std name the two emitters reference in type position, longest spelling first so the
# alternation cannot match `Into` inside `IntoIterator`.
_STD_NAMES = (
    "IntoIterator",
    "Iterator",
    "Into",
    "Option",
    "Result",
    "Vec",
    "Box",
    "String",
    "Drop",
    "PartialEq",
)

# A std name reached by neither a path nor a dotted attribute: `Vec<T>`, `-> String`,
# `impl Drop for`. `::std::vec::Vec` and the `.pyi` emitter's `typing.Iterator` are qualified and
# do not match; `PyResult` and `IntoIterator` are single words and do not match on their tails.
_BARE = re.compile(r"(?<![\w:.])(" + "|".join(_STD_NAMES) + r")\b")


def _bare_spellings(source: str) -> list[str]:
    """Every line of Rust in `source` naming a std item bare, stripped and in order.

    Comments are skipped: they are prose, and prose spells the shorthand. So are `#[derive(…)]`
    lines, which resolve in the macro namespace that no generated item occupies.
    """
    found: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith(("//", "#[derive(")):
            continue
        if _BARE.search(line.split("//", 1)[0]):
            found.append(stripped)
    return found


def _emitted_strings(module_source: str) -> list[str]:
    """Every string literal an emitter module builds output out of.

    Docstrings — the module's, each class's and function's, and the bare-string statements that
    document a module-level constant — are prose about the emitter rather than emitted Rust, so
    they are excluded; they are the one place the shorthand spelling is correct.
    """
    tree = ast.parse(module_source)
    prose = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose
    ]


def _generated_artifacts() -> list[pathlib.Path]:
    """The generated CST and AST modules of every in-tree crate, from the runfiles tree."""
    found = [
        path
        for root in ("crates/*/src", "tests/*/src")
        for path in sorted(_REPO_ROOT.glob(f"{root}/*.rs"))
        if path.name in {"cst.rs", "ast.rs"} or path.name.endswith("_cst.rs")
    ]
    assert len(found) >= 6, f"the artifact glob stopped matching; found {[str(p) for p in found]}"
    return found


@pytest.mark.parametrize("emitter", _SHADOWABLE_EMITTERS)
def test_a_shadowable_emitter_spells_no_std_item_bare(emitter: str) -> None:
    """Every Rust string these two emitters build names its std items by absolute path.

    This is the guard the compile gate cannot be: it covers emission sites no grammar in the suite
    instantiates and both halves of the `python` cfg, so a respelling cannot reach a consumer's
    regenerated module while the suite stays green.
    """
    bare = [line for text in _emitted_strings((_REPO_ROOT / emitter).read_text()) for line in _bare_spellings(text)]
    assert not bare, f"{emitter} emits a bare std spelling; name it through the fltk.fegen.rust_emit table: {bare}"


def test_the_generated_cst_and_ast_artifacts_spell_no_std_item_bare() -> None:
    """The generated modules carry the qualification the emitters write.

    The scan above reads the emitters' string literals; this one reads what they actually
    produced over every grammar in the tree, so a bare spelling assembled from pieces no single
    literal contains is caught too. Every crate here has a grammar without a prelude-colliding
    rule name, so the modules still compile and nothing else would notice.
    """
    stale = {
        str(path.relative_to(_REPO_ROOT)): bare
        for path in _generated_artifacts()
        if (bare := _bare_spellings(path.read_text()))
    }
    assert not stale, f"generated modules name a std item bare; fix fltk.fegen.rust_emit: {stale}"


def test_the_scan_reports_each_bare_spelling_it_exists_to_catch() -> None:
    """The scanner itself, against one planted line per doctrine category.

    A guard whose pattern silently stops matching passes forever, so the categories the two
    emitters actually write — a generic, a return type, a trait in `impl` position, an associated
    call, a bound — are pinned as findings here, and the spellings the doctrine keeps bare are
    pinned as non-findings.
    """
    caught = (
        "pub struct Doc { pub items: Vec<Item> }",
        "fn text(&self) -> String {",
        "impl Drop for ExprBinary {",
        "impl PartialEq for Doc {",
        "let mut out = Vec::new();",
        "children: Option<&Item>,",
        "fn extend<I: IntoIterator<Item = Child>>(&mut self, items: I) {",
        "value.map(Box::new)",
    )
    for line in caught:
        assert _bare_spellings(line) == [line], f"the scan missed a bare spelling: {line}"

    allowed = (
        "let items: ::std::vec::Vec<Item> = ::std::vec::Vec::new();",
        "impl ::std::cmp::PartialEq for Doc {",
        "return Some(child);",
        "Ok(())",
        "#[derive(Clone, Debug, PartialEq, Eq, Hash)]",
        "/// The `Option` accessor for one label.",
        "impl fmt::Debug for Doc {",
        "let previous = std::mem::take(&mut self.children);",
        "    def children_item(self) -> typing.Iterator[Item]: ...",
        "pub fn pos(&self) -> usize {",
    )
    for line in allowed:
        assert _bare_spellings(line) == [], f"the scan reported a spelling the doctrine keeps bare: {line}"
