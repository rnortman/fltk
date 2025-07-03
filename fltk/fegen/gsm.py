"""Grammar Semantic Model (GSM) for fltk.fegen"""

import dataclasses
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional, Union

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext
else:
    CompilerContext = object


@dataclasses.dataclass(frozen=True, slots=True)
class Grammar:
    rules: Sequence["Rule"]
    identifiers: Mapping[str, "Rule"]


@dataclasses.dataclass(frozen=True, slots=True)
class Rule:
    name: str
    alternatives: Sequence["Items"]
    is_trivia_rule: bool = False


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
    label: str | None
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
    ZERO = 0
    ONE = 1
    MULTIPLE = object()


class Quantifier(ABC):
    @abstractmethod
    def min(self) -> Arity: ...

    @abstractmethod
    def max(self) -> Arity: ...

    def is_optional(self) -> bool:
        return self.min() == Arity.ZERO

    def is_required(self) -> bool:
        return not self.is_optional()

    def is_multiple(self) -> bool:
        return self.max() == Arity.MULTIPLE


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
    init_value: str | None


def classify_trivia_rules(grammar: Grammar) -> Grammar:
    """Classify rules as trivia/non-trivia based on reachability from 'trivia' rule.

    Returns a new Grammar with updated Rule.is_trivia_rule flags.
    """
    trivia_rule = grammar.identifiers.get("trivia")
    if not trivia_rule:
        return grammar

    trivia_reachable: set[str] = set()
    _mark_trivia_reachable(trivia_rule, grammar.identifiers, trivia_reachable)

    updated_rules = []
    for rule in grammar.rules:
        if rule.name in trivia_reachable:
            updated_rule = dataclasses.replace(rule, is_trivia_rule=True)
        else:
            updated_rule = rule
        updated_rules.append(updated_rule)

    new_grammar = dataclasses.replace(
        grammar, rules=updated_rules, identifiers={rule.name: rule for rule in updated_rules}
    )

    validate_trivia_separation(new_grammar)

    return new_grammar


def _mark_trivia_reachable(rule: Rule, identifiers: Mapping[str, Rule], reachable: set[str]) -> None:
    """Recursively mark all rules reachable from the given rule."""
    if rule.name in reachable:
        return

    reachable.add(rule.name)

    for items in rule.alternatives:
        for item in items.items:
            if isinstance(item.term, Identifier):
                referenced_rule = identifiers.get(item.term.value)
                if referenced_rule:
                    _mark_trivia_reachable(referenced_rule, identifiers, reachable)


def validate_trivia_separation(grammar: Grammar) -> None:
    """Validate that trivia rules are not referenced by non-trivia rules."""
    errors = []

    for rule in grammar.rules:
        if rule.is_trivia_rule:
            continue

        for items in rule.alternatives:
            for item in items.items:
                if isinstance(item.term, Identifier):
                    referenced_rule = grammar.identifiers.get(item.term.value)
                    if referenced_rule and referenced_rule.is_trivia_rule:
                        errors.append(
                            f"Non-trivia rule '{rule.name}' cannot reference trivia rule '{referenced_rule.name}'"
                        )

    if errors:
        raise ValueError("Trivia separation violations:\n" + "\n".join(errors))


def add_trivia_rule_to_grammar(grammar: Grammar, context: CompilerContext) -> Grammar:  # noqa: ARG001
    """Add built-in trivia rule to grammar if one doesn't exist."""

    if "trivia" in grammar.identifiers:
        return grammar

    trivia_rule = Rule(
        name="trivia",
        alternatives=[
            Items(
                items=[
                    Item(
                        label="content",
                        disposition=Disposition.INCLUDE,
                        term=Regex(r"[\s]+"),
                        quantifier=REQUIRED,
                    )
                ],
                sep_after=[Separator.NO_WS],
            )
        ],
    )

    new_rules = [*list(grammar.rules), trivia_rule]
    new_identifiers = dict(grammar.identifiers)
    new_identifiers["trivia"] = trivia_rule

    return Grammar(rules=new_rules, identifiers=new_identifiers)
