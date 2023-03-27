import dataclasses as dc
from typing import Any, Type, TypeVar

_T = TypeVar('_T')
_U = TypeVar('_U')


def thaw(cls: Type[_T]) -> Type[_U]:
    fields = dc.fields(cls)  # type: ignore
    result = dc.make_dataclass(
        cls_name=cls.__name__,
        fields=((f.name,
                 f.type,
                 f) for f in fields),
    )
    return result


def as_class(obj: Any, cls: Type[_T]) -> _T:
    return cls(**{f.name: getattr(obj, f.name) for f in dc.fields(obj)})
