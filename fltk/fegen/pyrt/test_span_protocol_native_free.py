"""Stub-stability guard for ``span_protocol.py``.

The generated pipeline (parser/CST/protocol/unparser) imports ``SpanProtocol``, and its pyright
stub-stability holds structurally only because ``SpanProtocol`` (and now ``LineColPosProtocol``)
name **zero** ``fltk._native`` symbols in their structural surface. The existing "generated files
name no native" scans (``test_cst_protocol.py`` etc.) inspect generated-file text only and
structurally cannot catch a regression introduced inside ``span_protocol.py`` itself.

This module parses ``span_protocol.py`` with ``ast`` and asserts that transitive property directly:
both protocol classes exist, neither class body references ``_native`` (as identifier, attribute
chain root, or string-annotation token), the only ``fltk._native`` imports sit inside a ``Try``
(never under ``if TYPE_CHECKING:``), and no name bound by any ``fltk._native`` import is referenced
within either protocol class body (closing the alias channel).
"""

import ast
import pathlib

import pytest

import fltk.fegen.pyrt.span_protocol as _span_protocol_mod

_SOURCE_PATH = pathlib.Path(_span_protocol_mod.__file__)
_MODULE = ast.parse(_SOURCE_PATH.read_text(encoding="utf-8"))

_PROTOCOL_CLASS_NAMES = ("SpanProtocol", "LineColPosProtocol")


def _class_defs() -> dict[str, ast.ClassDef]:
    return {node.name: node for node in ast.walk(_MODULE) if isinstance(node, ast.ClassDef)}


def _identifiers_in_string_annotation(value: str) -> set[str]:
    """Best-effort parse of a string annotation into the identifier tokens it references."""
    try:
        parsed = ast.parse(value, mode="eval")
    except SyntaxError:
        # Not a valid expression (e.g. a docstring, not an annotation): fall back to no identifiers.
        return set()
    return {node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)}


def _annotation_nodes(class_def: ast.ClassDef) -> list[ast.expr]:
    """Every annotation expression appearing in a class body: function arg/return annotations and
    ``AnnAssign`` targets. Excludes docstrings and other non-annotation string constants."""
    annotations: list[ast.expr] = []
    for node in ast.walk(class_def):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args = node.args
            for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
                if arg is not None and arg.annotation is not None:
                    annotations.append(arg.annotation)
            if node.returns is not None:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
    return annotations


def _referenced_names(class_def: ast.ClassDef) -> set[str]:
    """Every identifier referenced within a class body: ast.Name ids and attribute-chain roots
    (both surface as ast.Name in a full walk), plus identifier tokens inside string
    (forward-reference) annotations. String tokens are collected only from annotation expressions
    (via ``_annotation_nodes``), not from arbitrary docstrings — mirroring the scoping in
    ``test_protocol_class_bodies_name_no_native`` so a docstring that happens to parse as an
    expression cannot feed phantom identifiers into the alias check."""
    names: set[str] = set()
    for child in ast.walk(class_def):
        if isinstance(child, ast.Name):
            names.add(child.id)
    for annotation in _annotation_nodes(class_def):
        for child in ast.walk(annotation):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                names |= _identifiers_in_string_annotation(child.value)
    return names


def _native_import_infos(tree: ast.AST = _MODULE) -> list[tuple[ast.Import | ast.ImportFrom, set[str]]]:
    """Single source of truth for "is this a ``fltk._native`` import, and what does it bind?".

    Both the confinement test and the alias-channel test derive from this, so they can never drift
    into enforcing different definitions of "native import". Recognizes every form that reaches the
    native extension:

      - ``import fltk._native [as x]``
      - ``from fltk._native import Name [as x]``
      - ``from fltk import _native [as x]``  (submodule-as-attribute; pyright resolves via the stub)
      - relative ``from ... import _native [as x]`` / ``from ..._native import Name [as x]``

    The bare ``from fltk import _native`` / relative forms are the alias channel a class-body
    annotation could exploit invisibly at runtime; catching them is the whole point of the guard.
    Relative forms are matched conservatively (any relative import naming ``_native``) — no
    legitimate module does ``from . import _native``, so over-matching the exotic relative shapes is
    safe and missing them is not.
    """
    infos: list[tuple[ast.Import | ast.ImportFrom, set[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bound: set[str] = set()
            for alias in node.names:
                if alias.name == "fltk._native" or alias.name.startswith("fltk._native."):
                    # `import fltk._native` binds `fltk`; `import fltk._native as x` binds `x`.
                    bound.add(alias.asname or alias.name.split(".", 1)[0])
            if bound:
                infos.append((node, bound))
        elif isinstance(node, ast.ImportFrom):
            bound = set()
            module_parts = node.module.split(".") if node.module else []
            imports_from_native_module = (node.level == 0 and module_parts[:2] == ["fltk", "_native"]) or (
                node.level > 0 and bool(module_parts) and module_parts[-1] == "_native"
            )
            if imports_from_native_module:
                # `from fltk._native import X` / `from ..._native import X` binds each imported name.
                for alias in node.names:
                    bound.add(alias.asname or alias.name)
            elif (node.level == 0 and node.module == "fltk") or (node.level > 0 and node.module is None):
                # `from fltk import _native` / `from ... import _native` binds the `_native` submodule.
                for alias in node.names:
                    if alias.name == "_native":
                        bound.add(alias.asname or alias.name)
            if bound:
                infos.append((node, bound))
    return infos


def _native_import_bound_names(tree: ast.AST = _MODULE) -> set[str]:
    """Names bound by any ``fltk._native`` import anywhere in ``tree`` (asname or name)."""
    bound: set[str] = set()
    for _node, names in _native_import_infos(tree):
        bound |= names
    return bound


def _native_import_nodes(tree: ast.AST = _MODULE) -> list[ast.Import | ast.ImportFrom]:
    return [node for node, _names in _native_import_infos(tree)]


def test_both_protocol_classes_present():
    # Guards against a silent rename that would make the other assertions vacuously pass.
    classes = _class_defs()
    for name in _PROTOCOL_CLASS_NAMES:
        assert name in classes, f"{name} missing from span_protocol.py — guard would be vacuous"


def test_protocol_class_bodies_name_no_native():
    classes = _class_defs()
    for name in _PROTOCOL_CLASS_NAMES:
        class_def = classes[name]
        # Identifiers and attribute chains anywhere in the class body must not name native. (A
        # docstring mentioning ``fltk._native`` to explain the bridge is fine — it is neither an
        # identifier reference nor an annotation, so the structural surface stays native-free.)
        for child in ast.walk(class_def):
            if isinstance(child, ast.Name):
                assert "_native" not in child.id, f"{name} references native identifier {child.id!r}"
            elif isinstance(child, ast.Attribute):
                assert "_native" not in child.attr, f"{name} references native attribute {child.attr!r}"
        # String (forward-reference) annotations must not name native either.
        for annotation in _annotation_nodes(class_def):
            for child in ast.walk(annotation):
                if isinstance(child, ast.Constant) and isinstance(child.value, str):
                    assert "_native" not in child.value, f"{name} string annotation names native: {child.value!r}"


def test_native_imports_confined_to_try_fallback():
    # Every fltk._native import must sit inside a Try node (the runtime AnySpan fallback), and none
    # may appear under `if TYPE_CHECKING:` — a TYPE_CHECKING native import is exactly the leak that
    # would make the protocols stub-sensitive while remaining invisible at runtime.
    try_import_nodes: set[int] = set()
    for node in ast.walk(_MODULE):
        if isinstance(node, ast.Try):
            for descendant in ast.walk(node):
                if isinstance(descendant, ast.Import | ast.ImportFrom):
                    try_import_nodes.add(id(descendant))

    typechecking_import_nodes: set[int] = set()
    for node in ast.walk(_MODULE):
        if isinstance(node, ast.If):
            test = node.test
            is_type_checking = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
                isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
            )
            if is_type_checking:
                for descendant in ast.walk(node):
                    if isinstance(descendant, ast.Import | ast.ImportFrom):
                        typechecking_import_nodes.add(id(descendant))

    native_imports = _native_import_nodes()
    assert native_imports, "expected at least the AnySpan try-fallback fltk._native import"
    for node in native_imports:
        assert id(node) in try_import_nodes, "fltk._native import outside a Try fallback"
        assert id(node) not in typechecking_import_nodes, "fltk._native import under if TYPE_CHECKING:"


def test_no_native_bound_name_referenced_in_protocol_bodies():
    # Close the alias channel: even a try-enclosed import whose bound name contains no `_native`
    # substring (e.g. `from fltk._native import LineColPos as _RustLineColPos`) must not be used
    # inside a protocol class body. Scoping to class bodies keeps the legitimate AnySpan use of the
    # `_RustSpan` alias (below the classes) legal.
    bound = _native_import_bound_names()
    classes = _class_defs()
    for name in _PROTOCOL_CLASS_NAMES:
        referenced = _referenced_names(classes[name])
        leaked = bound & referenced
        assert not leaked, f"{name} references native-import-bound name(s): {sorted(leaked)}"


# Bypass shapes that must be detected, or the alias-channel guard is hollow. Each puts a native
# import under `if TYPE_CHECKING:` and references its bound name in a protocol class-body annotation
# — a leak invisible at runtime and to the generated-file "names no native" scans. These pin the
# detector helpers themselves (correctness-1 / quality-1: the plain `from fltk._native import ...`
# form was covered, but the aliased/relative forms were not).
_BYPASS_SNIPPETS = (
    # `from fltk import _native as _rn` — submodule-as-attribute, the natural way to spell it.
    (
        "from typing import TYPE_CHECKING, Protocol\n"
        "if TYPE_CHECKING:\n"
        "    from fltk import _native as _rn\n"
        "class SpanProtocol(Protocol):\n"
        '    def line_col(self) -> "_rn.LineColPos | None": ...\n'
    ),
    # Relative member import `from ..._native import LineColPos as _RLC`.
    (
        "from typing import TYPE_CHECKING, Protocol\n"
        "if TYPE_CHECKING:\n"
        "    from ..._native import LineColPos as _RLC\n"
        "class SpanProtocol(Protocol):\n"
        '    def line_col(self) -> "_RLC | None": ...\n'
    ),
)


@pytest.mark.parametrize("snippet", _BYPASS_SNIPPETS)
def test_alias_channel_bypass_shapes_are_detected(snippet: str):
    tree = ast.parse(snippet)
    bound = _native_import_bound_names(tree)
    assert bound, "native import not detected — detector would let the alias channel through"
    class_def = next(node for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
    referenced = _referenced_names(class_def)
    assert bound & referenced, "class-body native reference not caught by the alias-channel guard"
