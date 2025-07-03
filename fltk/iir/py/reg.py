# Python type and handler registries
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from fltk.iir.typemodel import Type


@dataclass(frozen=True, eq=True)
class Module:
    import_path: Sequence[str]


Builtins: Final = Module(import_path=())


@dataclass(frozen=True, eq=True)
class TypeInfo:
    typ: Type
    module: Module
    name: str
    concrete_name: str | None = None

    def import_name(self, *, concrete: bool = False) -> str:
        if concrete and self.concrete_name:
            return self.concrete_name
        return ".".join([*list(self.module.import_path), self.name])
