"""No emitted `cst.rs` or `ast.rs` line names a std item without its path.

A grammar rule name becomes an UpperCamel item at module scope in the generated CST and AST
modules, and Rust resolves a module's own item before the prelude — so a rule named `option` turns
every bare `Option<…>` in that module into a type error in a file the consumer cannot edit. The two
emitters therefore spell std items absolute through the table in `fltk.fegen.rust_emit`.

The `prelude` case in `tests/test_generated_rust_gate.py` compiles a grammar whose rule names are
the std prelude's, which is the strongest witness there is — but it witnesses only the emission
sites that grammar instantiates, and only the halves of `cst.rs` the gate crate's feature set
compiles: it never enables `python`, so every `#[cfg(feature = "python")]` emission is compiled out
of it, and no crate in this repo builds a *shadowing* grammar with pyo3 linked. Three tests here
close those gaps:

- the emitters' own Rust strings, so an emission site no grammar in the suite reaches is covered
  too (`.map(Box::new)` on an optional boxed hoist has no occurrence in any committed artifact);
- the committed artifacts, so an emitter fix that was never followed by a regeneration fails here;
- one throwaway pyo3 crate over a shadowing grammar, so the pyo3 half of `cst.rs` — accessors,
  mutators, `__repr__`, the `PyResult` returns — is compiled under the shadow rather than scanned.
  That is also the one check here not bounded by a name list: it fails on a bare std name nobody
  thought to add below.

Only the two shadowable emitters are scanned. `parser.rs`, `unparser*.rs` and `de.rs` declare no
grammar-derived module-level item and reach the CST and AST types through `use super::…` aliases,
so their bare spellings cannot be shadowed and stay bare by design.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

from fltk.fegen import ast_test_grammars as fixtures
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from tests.generated_rust_gate import run_cargo
from tests.test_generated_rust_gate import PRELUDE_GRAMMAR

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


def _tracked_artifacts() -> list[pathlib.Path]:
    """The committed generated CST and AST modules."""
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


def test_the_committed_cst_and_ast_artifacts_spell_no_std_item_bare() -> None:
    """The tracked generated modules carry the qualification the emitters write.

    An emitter fix that was not followed by `make gencode` leaves an artifact that still compiles —
    every crate in this repo has a grammar without a prelude-colliding rule name — and ships the
    stale spelling to the next consumer who reads it as the shape to expect.
    """
    stale = {
        str(path.relative_to(_REPO_ROOT)): bare
        for path in _tracked_artifacts()
        if (bare := _bare_spellings(path.read_text()))
    }
    assert not stale, f"tracked generated modules name a std item bare; run `make gencode` then `make fix`: {stale}"


# The pyo3 requirement is read off the fixture crate rather than repeated, so the probe crate below
# is always linted against the pyo3 the repo actually depends on; an unresolvable requirement fails
# the offline build loudly instead of quietly testing a different macro expansion.
_FIXTURE_MANIFEST = _REPO_ROOT / "tests" / "rust_parser_fixture" / "Cargo.toml"
_PYO3_REQUIREMENT = re.compile(r'^pyo3 = \{ version = "([^"]+)"', re.MULTILINE)

_PROBE_MANIFEST = """[workspace]

[package]
name = "fltk-prelude-python-probe"
version = "0.0.0"
edition = "2021"
publish = false

[lib]
# rlib only: nothing here links libpython, so the probe needs no interpreter to lint.
crate-type = ["rlib"]

[features]
python = ["dep:pyo3", "fltk-cst-core/python"]
test-introspection = ["python", "fltk-cst-core/test-introspection"]

[dependencies]
fltk-cst-core = {{ path = "{root}/crates/fltk-cst-core", default-features = false }}
pyo3 = {{ version = "{pyo3}", features = ["abi3-py310"], optional = true }}
"""


def test_the_python_gated_half_of_a_shadowing_cst_module_compiles(tmp_path: pathlib.Path) -> None:
    """The pyo3 items of a generated `cst.rs` compile beside `pub struct Option` and friends.

    The compile gate's crate declares the `python` feature and never enables it, and the only
    artifacts built with pyo3 come from grammars with no prelude-colliding rule name — so half the
    file a pyo3 consumer gets was qualified by inspection and by the scans above, never by rustc.
    Consumers of the Python bindings are out-of-tree and invisible here (CLAUDE.md), which is
    exactly the surface that needs the compiler rather than a name list: this also fails on a bare
    std spelling `_STD_NAMES` does not mention, and on a pyo3 macro expansion that stops being
    hygienic under shadowing.
    """
    requirement = _PYO3_REQUIREMENT.search(_FIXTURE_MANIFEST.read_text())
    assert requirement is not None, f"{_FIXTURE_MANIFEST} no longer declares pyo3 the way this test reads it"

    source = tmp_path / "src"
    source.mkdir()
    source.joinpath("lib.rs").write_text("pub mod cst;\n")
    grammar = fixtures.classified_grammar(PRELUDE_GRAMMAR)
    source.joinpath("cst.rs").write_text(RustCstGenerator(grammar).generate())
    manifest = tmp_path / "Cargo.toml"
    manifest.write_text(_PROBE_MANIFEST.format(root=_REPO_ROOT, pyo3=requirement.group(1)))

    result = run_cargo("clippy", manifest, tmp_path / "target", "--features", "python", "--", "-D", "warnings")
    assert result.returncode == 0, result.stdout + result.stderr


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
