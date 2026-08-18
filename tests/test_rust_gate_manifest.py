"""The compile gate's declared build outputs are exactly what its case library writes.

`//tests:rust_gate_srcs` is a Bazel action, and an action declares its outputs statically, so the
file set that `tests/rust_gate_cases.py`'s `CASES` implies is written out a second time as
`_RUST_GATE_FILES` in `tests/BUILD.bazel`. Two ways the copies can disagree, and each loses
something:

- a path declared and never written fails the action loudly, so that direction is already gated;
- a path written and never declared is the quiet one — the generator would emit a module the
  crate never compiles, and a case could stop being generated at all with the crate still green.

The runtime half is the same hazard one level down, at two scales: a case that declares
`#[test]`s and emits a `runtime.rs` holding none compiles and runs nothing, and a case that
quietly loses a test inside its module runs less than it did. `//tests:rust_gate_runtime_test`
is one target over one crate and reports neither, so both are pinned here — the module's
existence and its test count — which is what the retired `cargo test` output parsing bought.
"""

from __future__ import annotations

import ast
import pathlib
import re

from fltk.fegen.gsm2tree_rs import RustCstGenerator
from tests.rust_gate_cases import CASES, generated_files

_BUILD_FILE = pathlib.Path(__file__).parent / "BUILD.bazel"


def _declared_files() -> list[str]:
    """The `_RUST_GATE_FILES` list as the BUILD file spells it.

    Read as a Starlark list literal rather than by regex over the file: the value is what the
    genrule declares, so anything that is not a plain list of strings is a mismatch worth failing
    on rather than parsing around.
    """
    marker = "_RUST_GATE_FILES = "
    start = _BUILD_FILE.read_text().index(marker) + len(marker)
    text = _BUILD_FILE.read_text()[start:]
    end = text.index("\n]\n") + len("\n]")
    return ast.literal_eval(text[:end])


def test_the_declared_outputs_are_what_the_cases_generate() -> None:
    assert _declared_files() == generated_files(CASES)


def test_every_case_name_is_its_own_module() -> None:
    names = [case.name for case in CASES]
    assert len(names) == len(set(names)), "case names are the crate's module names"


def test_the_no_ast_serde_mode_still_has_a_compiled_witness() -> None:
    assert any(case.serde and not case.ast for case in CASES)


_GATED_SHARED_IMPORT = '#[cfg(feature = "python")]\nuse fltk_cst_core::Shared;\n'


def test_the_span_only_case_still_has_the_shape_it_exists_for() -> None:
    """`span_only` is the crate's only witness for the cfg-gated `Shared` import.

    Give its grammar a rule reference and the child-class union stops being empty: the import
    goes back to bare, the crate still compiles, clippy is still clean, the python-flavor probe
    still builds and every runtime test still passes. The case degrades into one more ordinary
    case with the whole suite green, so its defining property is asserted here rather than left
    to the grammar's spelling.
    """
    case = next(case for case in CASES if case.name == "span_only")
    cst_rs = RustCstGenerator(case.model().grammar).generate()
    assert _GATED_SHARED_IMPORT in cst_rs, "the case's grammar must have no node children"
    assert "\nuse fltk_cst_core::Shared;\n" not in cst_rs.replace(_GATED_SHARED_IMPORT, "")


def test_every_runtime_module_carries_at_least_one_test() -> None:
    """A `runtime.rs` with no `#[test]` in it is a case that compiles and asserts nothing."""
    for case in CASES:
        if case.runtime:
            assert "#[test]" in case.runtime, f"{case.name} declares a runtime module with no test"


#: How many `#[test]` functions each case's runtime module carries. Pinned because
#: `//tests:rust_gate_runtime_test` is one target over one crate: deleting a test inside a
#: runtime module leaves it green with less coverage and nothing else in the tree notices.
_RUNTIME_TEST_COUNTS = {
    "ast_guide": 3,
    "boxed_link_fold": 1,
    "config": 30,
    "fold": 18,
    "literal_labels": 6,
    "merged": 7,
    "multi_tree": 5,
    "no_ast": 2,
    "nullable_loop": 2,
    "prelude": 1,
    "preserve_blanks": 3,
    "preserved_comment_blanks": 5,
    "rule_level_blanks": 2,
    "serde_guide": 3,
    "serialize": 9,
    "shapes": 5,
    "span_only": 7,
    "task": 5,
    "union_label": 5,
}

_RUST_TEST_FN = re.compile(r"#\[test\]\s*(?:async\s+)?fn\s+(\w+)")


def test_every_runtime_module_still_runs_the_tests_it_declared() -> None:
    """A silently shrinking runtime module is coverage decay in the largest generated-Rust suite."""
    counted = {case.name: len(_RUST_TEST_FN.findall(case.runtime)) for case in CASES if case.runtime}
    assert counted == _RUNTIME_TEST_COUNTS


def test_no_runtime_module_declares_the_same_test_twice() -> None:
    """Two `#[test] fn` of one name in a module do not compile; one of them is a lost assertion."""
    for case in CASES:
        names = _RUST_TEST_FN.findall(case.runtime)
        assert len(names) == len(set(names)), f"{case.name} declares a duplicate test name"
