import dataclasses as dc
from typing import Any, TypeVar

_T = TypeVar("_T")


def thaw(cls: type[_T]) -> type[Any]:
    fields = dc.fields(cls)  # type: ignore
    result = dc.make_dataclass(
        cls_name=cls.__name__,
        fields=((f.name, f.type, f) for f in fields),
    )
    return result


def as_class(obj: Any, cls: type[_T]) -> _T:
    return cls(**{f.name: getattr(obj, f.name) for f in dc.fields(obj)})
