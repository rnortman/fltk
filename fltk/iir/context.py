"""Compiler context and type registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from fltk.iir import model as iir
from fltk.iir.py import reg as pyreg
from fltk.iir.py.reg import TypeInfo
from fltk.iir.typemodel import Type, TypeKey


class TypeRegistry:
    """Type registry for storing type information during compilation."""

    def __init__(self) -> None:
        self._types: dict[TypeKey, TypeInfo] = {}

    def register_type(self, type_info: TypeInfo) -> None:
        """Register a type, allowing re-registration of identical types."""
        existing = self._types.get(type_info.typ.key)
        if existing is not None and existing != type_info:
            msg = f"Conflicting type registration: {type_info} (existing: {existing})"
            raise ValueError(msg)
        self._types[type_info.typ.key] = type_info

    def lookup(self, typ: Type) -> TypeInfo:
        """Look up type information for a given type."""
        return self._types[typ.key]

    def contains(self, typ: Type) -> bool:
        """Check if a type is registered."""
        return typ.key in self._types

    def copy(self) -> TypeRegistry:
        """Create a copy of this registry."""
        new_registry = TypeRegistry()
        new_registry._types = self._types.copy()
        return new_registry


@dataclass
class CompilerContext:
    """Compiler context holding all compiler state and services."""

    python_type_registry: TypeRegistry = field(default_factory=TypeRegistry)
    capture_trivia: bool = False


def create_default_context(*, capture_trivia: bool = False) -> CompilerContext:
    """Create a default compiler context with standard type registrations."""
    context = CompilerContext(capture_trivia=capture_trivia)

    # Register built-in types from model.py
    _register_builtin_types(context.python_type_registry)

    return context


def get_parser_types():
    """Get the parser-specific types for use in parser generation."""
    apply_result_type = iir.Type.make(cname="ApplyResultType", params={"pos_type": iir.TYPE, "result_type": iir.TYPE})
    terminal_span_type = iir.Type.make(cname="Span")
    memo_entry_type = iir.Type.make(
        cname="MemoEntry",
        params={"RuleId": iir.TYPE, "PosType": iir.TYPE, "ResultType": iir.TYPE},
    )
    error_tracker_type = iir.Type.make(
        cname="ErrorTracker",
        params={"RuleId": iir.TYPE},
    )

    return apply_result_type, terminal_span_type, memo_entry_type, error_tracker_type


def _register_builtin_types(registry: TypeRegistry) -> None:
    """Register built-in types that were previously registered globally."""

    # Register the same built-in types that model.py registers globally
    builtin_types = [
        pyreg.TypeInfo(typ=iir.Void, module=pyreg.Builtins, name="None"),
        pyreg.TypeInfo(typ=iir.UInt64, module=pyreg.Builtins, name="int"),
        pyreg.TypeInfo(typ=iir.IndexInt, module=pyreg.Builtins, name="int"),
        pyreg.TypeInfo(typ=iir.SignedIndexInt, module=pyreg.Builtins, name="int"),
        pyreg.TypeInfo(typ=iir.Bool, module=pyreg.Builtins, name="bool"),
        pyreg.TypeInfo(typ=iir.String, module=pyreg.Builtins, name="str"),
        pyreg.TypeInfo(typ=iir.Maybe, module=pyreg.Module(("typing",)), name="Optional"),
        pyreg.TypeInfo(
            typ=iir.GenericImmutableSequence,
            module=pyreg.Module(["typing"]),
            name="Sequence",
            concrete_name="list",
        ),
        pyreg.TypeInfo(
            typ=iir.GenericMutableHashmap,
            module=pyreg.Module(("collections", "abc")),
            name="MutableMapping",
            concrete_name="dict",
        ),
    ]

    # Register parser-specific types
    apply_result_type = iir.Type.make(cname="ApplyResultType", params={"pos_type": iir.TYPE, "result_type": iir.TYPE})
    builtin_types.append(
        pyreg.TypeInfo(
            typ=apply_result_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
            name="ApplyResult",
        )
    )

    terminal_span_type = iir.Type.make(cname="Span")
    builtin_types.append(
        pyreg.TypeInfo(
            typ=terminal_span_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
            name="Span",
        )
    )

    memo_entry_type = iir.Type.make(
        cname="MemoEntry",
        params={"RuleId": iir.TYPE, "PosType": iir.TYPE, "ResultType": iir.TYPE},
    )
    builtin_types.append(
        pyreg.TypeInfo(
            typ=memo_entry_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
            name="MemoEntry",
        )
    )

    error_tracker_type = iir.Type.make(
        cname="ErrorTracker",
        params={"RuleId": iir.TYPE},
    )
    builtin_types.append(
        pyreg.TypeInfo(
            typ=error_tracker_type,
            module=pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
            name="ErrorTracker",
        )
    )

    for type_info in builtin_types:
        registry.register_type(type_info)
