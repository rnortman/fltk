"""Grammar Semantic Model (GSM) for fltk.fegen"""

import dataclasses
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional, Union

if TYPE_CHECKING:
    from fltk.iir.context import CompilerContext
else:
    CompilerContext = object


TRIVIA_RULE_NAME: Final[str] = "_trivia"


@dataclasses.dataclass(frozen=True, slots=True)
class Grammar:
    rules: Sequence["Rule"]
    identifiers: Mapping[str, "Rule"]


@dataclasses.dataclass(frozen=True, slots=True)
class Rule:
    name: str
    alternatives: Sequence["Items"]
    is_trivia_rule: bool = False
    _can_be_nil: bool | None = dataclasses.field(default=None, init=False, compare=False, repr=False)
    _computing_nil: bool = dataclasses.field(default=False, init=False, compare=False, repr=False)

    def can_be_nil(self, grammar: "Grammar") -> bool:
        """Check if this rule can match empty string (memoized)."""
        if self._can_be_nil is not None:
            return self._can_be_nil

        # Detect cycles
        if self._computing_nil:
            return False  # Conservative: assume not nil in cycles

        # Mark as computing
        object.__setattr__(self, "_computing_nil", True)

        try:
            # Rule is nil if ANY alternative can be nil
            result = any(alt.can_be_nil(grammar) for alt in self.alternatives)
            object.__setattr__(self, "_can_be_nil", result)
            return result
        finally:
            object.__setattr__(self, "_computing_nil", False)


class Separator(Enum):
    NO_WS = "NO_WS"
    WS_REQUIRED = "WS_REQUIRED"
    WS_ALLOWED = "WS_ALLOWED"

    def can_be_nil(self) -> bool:
        """Check if separator can be nil."""
        if self == Separator.NO_WS:  # .
            return True
        elif self == Separator.WS_ALLOWED:  # ,
            return True
        elif self == Separator.WS_REQUIRED:  # :
            return False  # Never nil since trivia rule cannot be nil
        return False


@dataclasses.dataclass(frozen=True, slots=True)
class Items:
    items: Sequence["Item"]
    sep_after: Sequence[Separator]
    initial_sep: Separator = Separator.NO_WS
    _can_be_nil: bool | None = dataclasses.field(default=None, init=False, compare=False, repr=False)

    def can_be_nil(self, grammar: "Grammar") -> bool:
        """Check if this Items sequence can be nil."""
        if self._can_be_nil is not None:
            return self._can_be_nil

        # Initial separator must be nil
        if not self.initial_sep.can_be_nil():
            object.__setattr__(self, "_can_be_nil", False)
            return False

        # ALL items must be nil for sequence to be nil
        for i, item in enumerate(self.items):
            if not item.can_be_nil(grammar):
                object.__setattr__(self, "_can_be_nil", False)
                return False
            # Separator after this item must be nil
            if not self.sep_after[i].can_be_nil():
                object.__setattr__(self, "_can_be_nil", False)
                return False

        object.__setattr__(self, "_can_be_nil", True)
        return True


@dataclasses.dataclass(frozen=True, slots=True)
class Item:
    label: str | None
    disposition: "Disposition"
    term: "Term"
    quantifier: "Quantifier"

    def can_be_nil(self, grammar: "Grammar") -> bool:  # noqa: ARG002
        """Check if this item can be nil."""
        # Item nil if quantifier allows nil (regardless of term)
        return self.quantifier.is_optional()


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Identifier:
    value: str

    def can_be_nil(self, grammar: "Grammar") -> bool:
        """Check if referenced rule can be nil."""
        rule = grammar.identifiers.get(self.value)
        return rule is not None and rule.can_be_nil(grammar)


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Literal:
    value: str

    def can_be_nil(self, grammar: "Grammar") -> bool:  # noqa: ARG002
        """Literal is nil only if empty string."""
        return self.value == ""


@dataclasses.dataclass(frozen=True, eq=True, slots=True)
class Regex:
    value: str
    _can_be_nil: bool | None = dataclasses.field(default=None, init=False, compare=False, repr=False)

    def can_be_nil(self, grammar: "Grammar") -> bool:  # noqa: ARG002
        """Check if regex can match empty string (memoized)."""
        if self._can_be_nil is not None:
            return self._can_be_nil

        result = self._test_regex_empty()
        object.__setattr__(self, "_can_be_nil", result)
        return result

    def _test_regex_empty(self) -> bool:
        """Test if regex pattern can match empty string."""
        try:
            compiled = re.compile(self.value)
            return compiled.match("") is not None
        except re.error:
            # Invalid regex - conservative approach
            return False


Term = Union[
    "Invocation",
    Identifier,  # This must be a rule name
    Literal,
    Regex,
    Sequence[Items],
]


def term_can_be_nil(term: Term, grammar: "Grammar") -> bool:
    """Helper to check if any Term type can be nil."""
    if isinstance(term, Identifier | Literal | Regex | Invocation):
        return term.can_be_nil(grammar)
    elif isinstance(term, Sequence):  # List[Items] for parentheses
        # Parentheses are nil if ANY alternative can be nil
        return any(items.can_be_nil(grammar) for items in term)
    return False


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

    def can_be_nil(self, grammar: "Grammar") -> bool:  # noqa: ARG002
        """Invocations are never nil."""
        return False


Expression = Union["Add", Invocation, Identifier]


class Add:
    lhs: Expression
    rhs: Expression


@dataclasses.dataclass(frozen=True, slots=True)
class Var:
    name: str
    init_value: str | None


def classify_trivia_rules(grammar: Grammar) -> Grammar:
    """Classify rules as trivia/non-trivia based on reachability from TRIVIA_RULE_NAME rule.

    Returns a new Grammar with updated Rule.is_trivia_rule flags.
    """
    trivia_rule = grammar.identifiers.get(TRIVIA_RULE_NAME)
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
    validate_trivia_rule_not_nil(new_grammar)
    validate_no_repeated_nil_items(new_grammar)

    return new_grammar


def _mark_trivia_reachable(rule: Rule, identifiers: Mapping[str, Rule], reachable: set[str]) -> None:
    """Recursively mark all rules reachable from the given rule."""
    if rule.name in reachable:
        return

    reachable.add(rule.name)

    for items in rule.alternatives:
        _mark_trivia_reachable_in_items(items, identifiers, reachable)


def _mark_trivia_reachable_in_items(items: Items, identifiers: Mapping[str, Rule], reachable: set[str]) -> None:
    """Recursively mark all rules reachable from the given items."""
    for item in items.items:
        if isinstance(item.term, Identifier):
            referenced_rule = identifiers.get(item.term.value)
            if referenced_rule:
                _mark_trivia_reachable(referenced_rule, identifiers, reachable)
        elif isinstance(item.term, Sequence):
            # Process each alternative in the sequence
            for alt_items in item.term:
                _mark_trivia_reachable_in_items(alt_items, identifiers, reachable)


def validate_trivia_rule_not_nil(grammar: Grammar) -> None:
    """Validate that the trivia rule cannot be nil."""
    trivia_rule = grammar.identifiers.get(TRIVIA_RULE_NAME)
    if trivia_rule and trivia_rule.can_be_nil(grammar):
        msg = (
            f"Trivia rule '{TRIVIA_RULE_NAME}' cannot match empty string. "
            f"This would cause parsing issues throughout the grammar. "
            f"Ensure the trivia rule always matches at least some whitespace."
        )
        raise ValueError(msg)


def validate_no_repeated_nil_items(grammar: Grammar) -> None:
    """Validate no + or * quantified items can be nil."""
    errors = []

    for rule in grammar.rules:
        for alt_idx, alternative in enumerate(rule.alternatives):
            for item_idx, item in enumerate(alternative.items):
                if item.quantifier.is_multiple():  # + or *
                    if term_can_be_nil(item.term, grammar):
                        errors.append(
                            f"Rule '{rule.name}' alternative {alt_idx} item {item_idx}: "
                            f"Repeated item can match empty string, causing infinite loops. "
                            f"Consider making the item required or restructuring the grammar."
                        )

    if errors:
        raise ValueError("Repeated potentially-nil items found:\n" + "\n".join(errors))


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

    if TRIVIA_RULE_NAME in grammar.identifiers:
        return grammar

    trivia_rule = Rule(
        name=TRIVIA_RULE_NAME,
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
    new_identifiers[TRIVIA_RULE_NAME] = trivia_rule

    return Grammar(rules=new_rules, identifiers=new_identifiers)
