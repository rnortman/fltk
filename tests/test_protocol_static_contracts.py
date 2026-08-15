"""Pyright-gated static contracts of the protocol surface and of a generated AST module.

The repo-wide pyright gate covers `fltk/` and top-level `*.py` (plus the one named conformance
fixture), so the contracts below — which live in `tests/` fixtures or in an artifact nobody
commits — need their own pyright subprocess to be checked at all:

* the generated Python AST module is type-clean, including every `cstp.` forward annotation;
* `LabelProtocol` rejects an object without `_fltk_canonical_name` (the positive direction is
  gated in `tests/typecheck_fegen_cst_conformance.py`);
* a protocol node's `children` is read-only — no `append`, no assignment;
* `kind == NodeKind.X` narrows a union of protocol nodes, whether the members come from the
  protocol module or from the concrete module that re-exports the same enum.

One pyright invocation covers all fixtures; diagnostics are partitioned per file.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from tests.fegen_ast_fixture import AST_MODULE_NAME, write_fegen_ast_module
from tests.pyright_test_utils import (
    _diags_for_file,
    _run_pyright_over_dir,
    write_pyright_config,
)

_REPO_ROOT = pathlib.Path(__file__).parent.parent

_LABEL_NEGATIVE_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen.pyrt.label_protocol import LabelProtocol


class _NotALabel:
    pass


_bad: LabelProtocol = _NotALabel()
"""

_CHILDREN_READONLY_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen import fltk_cst_protocol as cstp


def mutate(node: cstp.Items) -> None:
    node.children.append((None, node))
    node.children = []
"""

_NARROWING_PROTOCOL_KIND_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen import fltk_cst_protocol as _proto
from fltk.fegen.pyrt.label_protocol import LabelProtocol
from collections.abc import Sequence


def narrow(node: _proto.Items | _proto.Grammar) -> None:
    if node.kind == _proto.NodeKind.ITEMS:
        _children: Sequence[tuple[LabelProtocol | None, object]] = node.children
        _items: Sequence[_proto.Item] = node.item()
    else:
        _children2: Sequence[tuple[LabelProtocol | None, object]] = node.children
        _rules: Sequence[_proto.Rule] = node.rule()
"""

_NARROWING_CONCRETE_KIND_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen import fltk_cst
from fltk.fegen import fltk_cst_protocol as _proto
from collections.abc import Sequence


def narrow(node: _proto.Items | _proto.Grammar) -> None:
    if node.kind == fltk_cst.NodeKind.ITEMS:
        _items: Sequence[_proto.Item] = node.item()
    else:
        _rules: Sequence[_proto.Rule] = node.rule()
"""


_WRONG_NODE_CLASS_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen import fltk_cst
from fltk.fegen import fltk_cst_protocol as cstp
import fegen_rust_cst.cst as rust_cst


def take(node: cstp.Grammar) -> None: ...


take(fltk_cst.Rule())
take(rust_cst.Rule())
"""

_WRONG_MUTATOR_INPUT_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

from fltk.fegen import fltk_cst as py_cst
from fltk.fegen import fltk_cst_protocol as cstp


def mutate_concrete(node: py_cst.Items, wrong: cstp.Grammar) -> None:
    node.append(wrong)
    node.insert(0, wrong)
    node.append_item(wrong)


def mutate_protocol(node: cstp.Items, wrong: cstp.Grammar) -> None:
    node.append(wrong)
    node.insert(0, wrong)
    node.append_item(wrong)
"""

_FIXTURE_SOURCES = {
    "label_negative.py": _LABEL_NEGATIVE_FIXTURE,
    "children_readonly.py": _CHILDREN_READONLY_FIXTURE,
    "narrowing_protocol_kind.py": _NARROWING_PROTOCOL_KIND_FIXTURE,
    "narrowing_concrete_kind.py": _NARROWING_CONCRETE_KIND_FIXTURE,
    "wrong_node_class.py": _WRONG_NODE_CLASS_FIXTURE,
    "wrong_mutator_input.py": _WRONG_MUTATOR_INPUT_FIXTURE,
}


@pytest.fixture(scope="module")
def static_contract_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Write every fixture plus a freshly generated fegen AST module; run pyright once."""
    tmpdir = tmp_path_factory.mktemp("protocol_static_contracts")
    write_pyright_config(tmpdir, extra_paths=[str(_REPO_ROOT), str(_REPO_ROOT / "fltk" / "_stubs")])
    write_fegen_ast_module(tmpdir)
    for name, source in _FIXTURE_SOURCES.items():
        (tmpdir / name).write_text(source)
    # Diagnostics are matched by filename, so a file nobody wrote reads as zero errors and every
    # pyright-clean assertion below would pass on nothing.
    missing = [name for name in (*_FIXTURE_SOURCES, f"{AST_MODULE_NAME}.py") if not (tmpdir / name).is_file()]
    assert not missing, f"fixture files the tests name were never written: {missing}"
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


def test_a_generated_ast_module_is_pyright_clean(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """The emitted AST module type-checks as the downstream consumer's regen would see it.

    Nothing commits a Python AST artifact, so without this the module's own annotations — every
    forward `cstp.<Class>`, the value enums inheriting the astrt mixin, the `cst:` backpointer
    beside concrete construction — are checked for the first time in a consumer's own pyright run.
    """
    errors = _diags_for_file(static_contract_diagnostics, "generated_fegen_ast.py")
    assert errors == [], f"the generated fegen AST module does not type-check:\n{errors}"


def test_a_label_without_the_canonical_name_is_refused(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """LabelProtocol has teeth: the positive cases in the gated fixture prove something."""
    errors = _diags_for_file(static_contract_diagnostics, "label_negative.py")
    assert len(errors) == 1, errors
    assert errors[0]["rule"] == "reportAssignmentType", errors[0]
    assert "_fltk_canonical_name" in errors[0]["message"], errors[0]["message"]


def test_protocol_children_is_read_only(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """The protocol's `children` is a Sequence-returning property: no append, no assignment.

    This is the shape concrete-list covariance depends on: a read-only Sequence lets a concrete
    list[tuple[ConcreteLabel, ...]] satisfy the covariant return without exposing mutators that
    would violate invariance.
    """
    errors = _diags_for_file(static_contract_diagnostics, "children_readonly.py")
    assert len(errors) == 2, errors
    assert {error["rule"] for error in errors} == {"reportAttributeAccessIssue"}, errors
    assert any('Cannot access attribute "append"' in error["message"] for error in errors), errors
    assert any('Cannot assign to attribute "children"' in error["message"] for error in errors), errors


def test_kind_narrows_a_union_of_protocol_nodes(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """`kind == cstp.NodeKind.X` discriminates protocol nodes — what switchable consumers write."""
    errors = _diags_for_file(static_contract_diagnostics, "narrowing_protocol_kind.py")
    assert errors == [], errors


def test_the_concrete_node_kind_also_narrows_a_protocol_node(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """The shared enum, pinned: `cst.NodeKind.X` discriminates protocol nodes just as well.

    The concrete module re-exports the protocol module's NodeKind, so there is one enum and one
    set of Literal types.  A consumer that already compares against the concrete module's members
    keeps narrowing correctly after its node annotations move to the protocol — which is the point
    of sharing the enum rather than mirroring it.
    """
    errors = _diags_for_file(static_contract_diagnostics, "narrowing_concrete_kind.py")
    assert errors == [], errors


def test_a_wrong_node_class_is_still_rejected_by_a_protocol_parameter(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """The conformance suite has teeth: conformance is not vacuous assignability.

    Every other protocol fixture in the repo asserts zero errors, so a protocol widened into
    vacuity — `kind` losing its `Literal`, a child union collapsing to `object` — would leave them
    all green while downstream protocol-typed code stopped catching wrong-node bugs. Both backends
    are checked, so the discrimination cannot be lost on one of them alone.
    """
    errors = _diags_for_file(static_contract_diagnostics, "wrong_node_class.py")
    assert len(errors) == 2, errors
    assert {error["rule"] for error in errors} == {"reportArgumentType"}, errors
    assert all('of type "Grammar"' in error["message"] for error in errors), errors


def test_a_wrong_node_class_is_still_rejected_by_a_widened_mutator(
    static_contract_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """The mutator inputs name the protocol surface, but they still name *which* classes.

    Every other fixture covering the widened inputs is positive — protocol-typed arguments are
    accepted — so a further widening to `object`, to `typing.Any`, or to a child union that
    collapsed would leave them green with the runtime isinstance guard as the only remaining net.
    Both the concrete node's mutators and the protocol's are checked.
    """
    errors = _diags_for_file(static_contract_diagnostics, "wrong_mutator_input.py")
    assert len(errors) == 6, errors
    assert {error["rule"] for error in errors} == {"reportArgumentType"}, errors
    assert all('of type "Grammar"' in error["message"] for error in errors), errors
