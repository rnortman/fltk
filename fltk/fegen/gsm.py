"""Grammar Semantic Model (GSM) for fltk.fegen"""

import dataclasses
from abc import ABC, abstractmethod
from enum import Enum
from typing import Final, Mapping, Optional, Sequence, Union


@dataclasses.dataclass(frozen=True, slots=True)
class Grammar:
    rules: Sequence["Rule"]
    identifiers: Mapping[str, "Rule"]


@dataclasses.dataclass(frozen=True, slots=True)
class Rule:
    name: str
    alternatives: Sequence["Items"]


class Separator(Enum):
    NO_WS = "NO_WS"
    WS_REQUIRED = "WS_REQUIRED"
    WS_ALLOWED = "WS_ALLOWED"


@dataclasses.dataclass(frozen=True, slots=True)
class Items:
    items: Sequence["Item"]
    sep_after: Sequence[Separator]


@dataclasses.dataclass(frozen=True, slots=True)
class Item:
    label: Optional[str]
    disposition: "Disposition"
    term: "Term"
    quantifier: "Quantifier"


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Identifier:
    value: str


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Literal:
    value: str


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Regex:
    value: str


Term = Union[
    "Invocation",
    Identifier,  # This must be a rule name
    Literal,
    Regex,
    Sequence[Items],
]


class Disposition(Enum):
    SUPPRESS = "suppress"
    INCLUDE = "include"
    INLINE = "inline"


class Arity(Enum):
    ZERO: Final = 0
    ONE: Final = 1
    MULTIPLE: Final = object()


class Quantifier(ABC):
    @abstractmethod
    def min(self) -> Arity:  # noqa: A003
        ...

    @abstractmethod
    def max(self) -> Arity:  # noqa: A003
        ...

    def is_optional(self) -> bool:
        return self.min() == Arity.ZERO

    def is_required(self) -> bool:
        return not self.is_optional()

    def is_multiple(self) -> bool:
        return self.max() == Arity.MULTIPLE


class Required(Quantifier):
    def min(self) -> Arity:  # noqa: A003
        return Arity.ONE

    def max(self) -> Arity:  # noqa: A003
        return Arity.ONE


REQUIRED: Final = Required()


class NotRequired(Quantifier):
    def min(self) -> Arity:  # noqa: A003
        return Arity.ZERO

    def max(self) -> Arity:  # noqa: A003
        return Arity.ONE


NOT_REQUIRED: Final = NotRequired()


class OneOrMore(Quantifier):
    def min(self) -> Arity:  # noqa: A003
        return Arity.ONE

    def max(self) -> Arity:  # noqa: A003
        return Arity.MULTIPLE


ONE_OR_MORE: Final = OneOrMore()


class ZeroOrMore(Quantifier):
    def min(self) -> Arity:  # noqa: A003
        return Arity.ZERO

    def max(self) -> Arity:  # noqa: A003
        return Arity.MULTIPLE


ZERO_OR_MORE: Final = ZeroOrMore()


@dataclasses.dataclass(frozen=True, slots=True)
class Invocation:
    method_name: str
    expression: Optional["Expression"]


Expression = Union["Add", Invocation, Identifier]


class Add:
    lhs: Expression
    rhs: Expression


@dataclasses.dataclass(frozen=True, slots=True)
class Var:
    name: str
    init_value: Optional[str]
