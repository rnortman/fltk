from typing import Final, Sequence

# Python type and handler registries

from dataclasses import dataclass

from fltk.iir.typemodel import Type, TypeKey


@dataclass(frozen=True, eq=True)
class Module:
    import_path: Sequence[str]


Builtins: Final = Module(import_path=())


@dataclass(frozen=True, eq=True)
class TypeInfo:
    typ: Type
    module: Module
    name: str

    def import_name(self) -> str:
        return '.'.join(list(self.module.import_path) + [self.name])


_type_registry: dict[TypeKey, TypeInfo] = {}


def register_type(type_info: TypeInfo) -> None:
    try:
        existing_type = _type_registry[type_info.typ.key]
        raise ValueError(f"Cannot register {type_info}: Type already registered as {existing_type}")
    except KeyError:
        pass
    _type_registry[type_info.typ.key] = type_info


def lookup(typ: Type) -> TypeInfo:
    return _type_registry[typ.key]
