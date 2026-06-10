"""B4 runtime-agreement tests: fltk/_native/fegen_cst.pyi vs the compiled fltk._native.fegen_cst.

Validates two directions over the generated fegen_cst surface:
  1. Every class, method, and classattr declared in the .pyi exists on the runtime module.
  2. Every public runtime member of fltk._native.fegen_cst is declared in the .pyi.

Scope is fegen_cst only; fltk._native top-level members (PoC classes, Span, SourceText,
UnknownSpan) are verified separately in tests/test_native.py. Top-level PoC classes are
intentionally omitted from the stub — see fltk/_native/__init__.pyi header comment.

Skips cleanly when fltk._native is unimportable (extension not yet built).
"""

from __future__ import annotations

import ast
import functools
import importlib
import pathlib
from types import ModuleType

import pytest

# --------------------------------------------------------------------------- #
# Skip guard                                                                    #
# --------------------------------------------------------------------------- #

_NATIVE_AVAILABLE = importlib.util.find_spec("fltk._native") is not None


def _try_import_fegen_cst() -> ModuleType | None:
    try:
        import fltk._native.fegen_cst as fc  # noqa: PLC0415

        return fc
    except (ImportError, ModuleNotFoundError):
        return None


_FEGEN_CST_MODULE = _try_import_fegen_cst()

skip_if_no_native = pytest.mark.skipif(
    _FEGEN_CST_MODULE is None,
    reason="fltk._native.fegen_cst not importable — run 'uv run maturin develop' first",
)

# --------------------------------------------------------------------------- #
# Parse the committed .pyi stub                                                 #
# --------------------------------------------------------------------------- #

_STUB_PATH = pathlib.Path(__file__).parent.parent / "fltk" / "_native" / "fegen_cst.pyi"


@functools.cache
def _parse_stub() -> ast.Module:
    """Parse and cache the stub file; subsequent calls return the cached AST."""
    return ast.parse(_STUB_PATH.read_text())


def _stub_classes_with_members() -> dict[str, set[str]]:
    """Return {class_name: {member_name, ...}} for each stub class.

    Only includes methods and simple attribute assignments/annotations — the
    public interface surface; dunder names (including __init__) are excluded.
    """
    tree = _parse_stub()
    result: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        members: set[str] = set()
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and not stmt.name.startswith("_"):
                members.add(stmt.name)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if not stmt.target.id.startswith("_"):
                    members.add(stmt.target.id)
            elif isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and not t.id.startswith("_"):
                        members.add(t.id)
        result[node.name] = members
    return result


def _stub_top_level_names() -> set[str]:
    """Return names of top-level module-level assignments/aliases in the stub."""
    tree = _parse_stub()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("_"):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if not node.target.id.startswith("_"):
                names.add(node.target.id)
    return names


# --------------------------------------------------------------------------- #
# Runtime-to-stub direction: stub must declare everything the runtime has       #
# --------------------------------------------------------------------------- #

# _XxxLabel names (e.g. Grammar_Label) are PyO3 implementation detail enums.
# They are registered as module attributes by the generated code but are accessed
# via ClassName.Label in the stub (which aliases the protocol's Label class).
# Excluding them from the "runtime has it, stub must declare it" direction is
# deliberate: they are internal artifacts, not part of the public interface.
_KNOWN_RUNTIME_EXTRAS = frozenset(
    {
        "Alternatives_Label",
        "BlockComment_Label",
        "Disposition_Label",
        "Grammar_Label",
        "Identifier_Label",
        "Item_Label",
        "Items_Label",
        "LineComment_Label",
        "Literal_Label",
        "Quantifier_Label",
        "RawString_Label",
        "Rule_Label",
        "Term_Label",
        "Trivia_Label",
    }
)


@skip_if_no_native
class TestRuntimeToStub:
    """Every public runtime member of fegen_cst is declared in the stub."""

    def test_runtime_classes_in_stub(self) -> None:
        """All public class names on the runtime module are in the stub."""
        assert _FEGEN_CST_MODULE is not None
        runtime_public = {
            name
            for name in dir(_FEGEN_CST_MODULE)
            if not name.startswith("_") and isinstance(getattr(_FEGEN_CST_MODULE, name), type)
        }
        stub_names = _stub_top_level_names()
        missing = runtime_public - stub_names - _KNOWN_RUNTIME_EXTRAS
        assert not missing, (
            f"Runtime classes missing from stub: {sorted(missing)}. "
            "Add them to fltk/_native/fegen_cst.pyi or _KNOWN_RUNTIME_EXTRAS if intentionally omitted."
        )

    def test_runtime_module_attrs_in_stub(self) -> None:
        """Non-class public module attributes on the runtime are in the stub."""
        assert _FEGEN_CST_MODULE is not None
        runtime_non_class = {
            name
            for name in dir(_FEGEN_CST_MODULE)
            if not name.startswith("_") and not isinstance(getattr(_FEGEN_CST_MODULE, name), type)
        }
        stub_names = _stub_top_level_names()
        missing = runtime_non_class - stub_names - _KNOWN_RUNTIME_EXTRAS
        assert not missing, (
            f"Runtime module attrs missing from stub: {sorted(missing)}. Add them to fltk/_native/fegen_cst.pyi."
        )


# --------------------------------------------------------------------------- #
# Stub-to-runtime direction: every stub-declared member exists at runtime      #
# --------------------------------------------------------------------------- #


@skip_if_no_native
class TestStubToRuntime:
    """Every class and member declared in the stub exists on the runtime module."""

    def test_stub_classes_exist_at_runtime(self) -> None:
        """All stub-declared classes are importable from fltk._native.fegen_cst."""
        assert _FEGEN_CST_MODULE is not None
        stub_classes = _stub_classes_with_members()
        for class_name in stub_classes:
            assert hasattr(_FEGEN_CST_MODULE, class_name), (
                f"Stub declares class {class_name!r} but fltk._native.fegen_cst has no such attribute."
            )

    def test_stub_members_exist_at_runtime(self) -> None:
        """All stub-declared methods and class attrs exist on the corresponding runtime classes."""
        assert _FEGEN_CST_MODULE is not None
        stub_classes = _stub_classes_with_members()
        for class_name, members in stub_classes.items():
            runtime_cls = getattr(_FEGEN_CST_MODULE, class_name, None)
            if runtime_cls is None:
                continue  # caught by test_stub_classes_exist_at_runtime
            for member in members:
                assert hasattr(runtime_cls, member), (
                    f"Stub declares {class_name}.{member} but the runtime class lacks it. "
                    "Update the stub or the generator."
                )

    def test_stub_node_kind_in_stub(self) -> None:
        """Stub's NodeKind alias exists at runtime."""
        assert _FEGEN_CST_MODULE is not None
        assert hasattr(_FEGEN_CST_MODULE, "NodeKind"), "Stub declares NodeKind but runtime module lacks it."
