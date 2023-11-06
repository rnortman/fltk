import typing
from dataclasses import dataclass, field
from typing import Final, Mapping, Optional, Union


class ParamType:
    pass


@dataclass(frozen=True, eq=True)
class TypeParam(ParamType):
    bound: Optional["Type"]


TYPE: Final = TypeParam(bound=None)


@dataclass(frozen=True, eq=True)
class ValueParam(ParamType):
    value_type: "Type"


Argument = Union["Type", int, str]
KeyArgument = Union["TypeKey", int, str]


@dataclass(frozen=True, eq=True)
class TypeKey:
    cname: Optional[str]
    params: tuple[tuple[str, ParamType], ...]
    instantiates: Optional["TypeKey"]
    arguments: tuple[tuple[str, KeyArgument], ...]


_type_registry: Final[dict[TypeKey, "Type"]] = {}

_TypeSubclass = typing.TypeVar("_TypeSubclass", bound="Type")


def _freeze_args(args: Mapping[str, Argument]) -> tuple[tuple[str, KeyArgument], ...]:
    return tuple((name, arg.key if isinstance(arg, Type) else arg) for name, arg in args.items())


def lookup_type(type_key: TypeKey) -> "Type":
    return _type_registry[type_key]


@dataclass(kw_only=True)
class Type:
    key: TypeKey = field(init=False)
    cname: Optional[str]
    params: Mapping[str, ParamType]
    instantiates: Optional["Type"]
    arguments: Mapping[str, Argument]

    @classmethod
    def make(
        cls: typing.Type[_TypeSubclass],
        *,
        cname: Optional[str] = None,
        params: Optional[Mapping[str, ParamType]] = None,
        instantiates: Optional["Type"] = None,
        arguments: Optional[Mapping[str, Argument]] = None,
    ) -> _TypeSubclass:
        return cls(
            cname=cname,
            params=(params if params is not None else {}),
            instantiates=instantiates,
            arguments=(arguments if arguments is not None else {}),
        )

    def __post_init__(self) -> None:
        self.key = TypeKey(
            cname=self.cname,
            params=tuple((name, typ) for name, typ in self.params.items()),
            instantiates=self.instantiates.key if self.instantiates else None,
            arguments=_freeze_args(self.arguments),
        )
        if self.key in _type_registry:
            # raise KeyError(f"Type with key {self.key} already registered")
            pass
        _type_registry[self.key] = self

    def instantiate(self, **arguments: Argument) -> "Type":
        for name in arguments:
            if name not in self.params:
                msg = f"Param {name} is not present in type {self}"
                raise KeyError(msg)
        free_params = {name: param for name, param in self.params.items() if name not in arguments}
        return Type(cname=self.cname, params=free_params, instantiates=self, arguments=arguments)

    def root_type(self) -> "Type":
        if self.instantiates is None:
            return self
        return self.instantiates.root_type()

    def get_arg(self, name: str) -> Argument:
        try:
            return self.arguments[name]
        except KeyError:
            pass
        if self.instantiates:
            return self.instantiates.get_arg(name)
        msg = f"No argument for parameter {name} provided"
        raise KeyError(msg)

    def get_arg_as_type(self, name: str) -> "Type":
        try:
            result = self.arguments[name]
            if not isinstance(result, Type):
                msg = f"Expected Type but got {result}"
                raise ValueError(msg)
            return result
        except KeyError:
            pass
        if self.instantiates:
            return self.instantiates.get_arg_as_type(name)
        msg = f"No argument for parameter {name} provided"
        raise KeyError(msg)

    def get_args(self) -> Mapping[str, Argument]:
        return {param: self.get_arg(param) for param in self.root_type().params}
