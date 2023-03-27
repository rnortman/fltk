"""Grammar Semantic Model (GSM) for fltk.fegen"""

from abc import ABC, abstractmethod
from collections import abc
import dataclasses
from enum import Enum
from typing import Final, Optional, Sequence, Union


@dataclasses.dataclass(frozen=True, slots=True)
class Grammar:
    rules: Sequence["Rule"]
    vars: Sequence["Var"]
    identifiers: abc.Mapping[str, Union["Rule", "Var"]]


@dataclasses.dataclass(frozen=True, slots=True)
class Rule:
    name: str
    alternatives: Sequence["Items"]
    labels: abc.Mapping[str, Sequence[int]]  # Mapping from label to indices of alternatives with that label


@dataclasses.dataclass(frozen=True, slots=True)
class Items:
    items: Sequence["Item"]
    labels: abc.Mapping[str, int]  # Mapping from label to index of that item in items


@dataclasses.dataclass(frozen=True, slots=True)
class Item:
    label: Optional[str]
    disposition: Optional["Disposition"]
    term: "Term"
    quantifier: "Quantifier"


# class TermType:
#     class Regex(RawString):
#         pass


class Identifier:
    pass


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Literal:
    value: str

Term = Union[
    "Invocation",
    Identifier,                 # This must be a rule name
    Literal,
    # TermType.Regex,
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
    def min(self) -> Arity:
        ...

    @abstractmethod
    def max(self) -> Arity:
        ...


class Required(Quantifier):
    def min(self) -> Arity:
        return Arity.ONE

    def max(self) -> Arity:
        return Arity.ONE


REQUIRED: Final = Required()


class NotRequired(Quantifier):
    def min(self) -> Arity:
        return Arity.ZERO

    def max(self) -> Arity:
        return Arity.ONE


NOT_REQUIRED: Final = NotRequired()


class OneOrMore(Quantifier):
    def min(self) -> Arity:
        return Arity.ONE

    def max(self) -> Arity:
        return Arity.MULTIPLE


ONE_OR_MORE: Final = OneOrMore()


class ZeroOrMore(Quantifier):
    def min(self) -> Arity:
        return Arity.ZERO

    def max(self) -> Arity:
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
