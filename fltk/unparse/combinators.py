"""Pretty-printing combinators for FLTK formatter."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final


@dataclass(slots=True, frozen=True)
class Doc(ABC):
    """Base class for all document combinators."""

    @abstractmethod
    def __repr__(self) -> str:
        """String representation for debugging."""
        pass


@dataclass(slots=True, frozen=True)
class Text(Doc):
    """Literal text content."""

    content: str

    def __repr__(self) -> str:
        return f"Text({self.content!r})"


@dataclass(slots=True, frozen=True)
class Comment(Doc):
    """Comment content that should be re-indented when formatted."""

    content: str

    def __repr__(self) -> str:
        return f"Comment({self.content!r})"


@dataclass(slots=True, frozen=True)
class Line(Doc):
    """Soft line/space - can be a space or newline."""

    def __repr__(self) -> str:
        return "Line"


@dataclass(slots=True, frozen=True)
class Nbsp(Doc):
    """Non-breaking space - always renders as space, never as newline."""

    def __repr__(self) -> str:
        return "Nbsp"


@dataclass(slots=True, frozen=True)
class SoftLine(Doc):
    """Soft break - renders as nothing or newline, never as space."""

    def __repr__(self) -> str:
        return "SoftLine"


@dataclass(slots=True, frozen=True)
class HardLine(Doc):
    """Hard line break - always a newline."""

    blank_lines: int = 0  # Number of additional blank lines

    def __repr__(self) -> str:
        if self.blank_lines:
            return f"HardLine(blank_lines={self.blank_lines})"
        return "HardLine"


@dataclass(slots=True, frozen=True)
class ContentWrapper(Doc):
    """Base class for combinators that wrap content."""

    content: Doc


@dataclass(slots=True, frozen=True)
class Group(ContentWrapper):
    """Try to fit content on one line, otherwise break at all soft lines."""

    def __repr__(self) -> str:
        return f"Group({self.content!r})"


@dataclass(slots=True, frozen=True)
class Nest(ContentWrapper):
    """Indent content by specified amount when breaking."""

    indent: int

    def __repr__(self) -> str:
        return f"Nest({self.indent}, {self.content!r})"


@dataclass(slots=True, frozen=True)
class DocListWrapper(Doc):
    """Base class for combinators that work with multiple documents."""

    docs: Sequence[Doc]


@dataclass(slots=True, frozen=True)
class Concat(DocListWrapper):
    """Concatenate multiple documents."""

    def __repr__(self) -> str:
        return f"Concat({list(self.docs)!r})"


@dataclass(slots=True, frozen=True)
class Join(DocListWrapper):
    """Join multiple documents with a separator."""

    separator: Doc

    def __repr__(self) -> str:
        return f"Join({list(self.docs)!r}, separator={self.separator!r})"


@dataclass(slots=True, frozen=True)
class Nil(Doc):
    """Empty document - produces no output."""

    def __repr__(self) -> str:
        return "Nil"


# Singleton instances for common cases
LINE: Final = Line()
HARDLINE: Final = HardLine()
HARDLINE_BLANK: Final = HardLine(1)
NIL: Final = Nil()
NBSP: Final = Nbsp()
SOFTLINE: Final = SoftLine()


# Helper functions for building combinators
def text(s: str) -> Text:
    """Create a text node."""
    return Text(s)


def line() -> Line:
    """Create a soft line break."""
    return LINE


def hardline(blank_lines: int = 0) -> HardLine:
    """Create a hard line break with optional blank lines."""
    if blank_lines == 0:
        return HARDLINE
    if blank_lines == 1:
        return HARDLINE_BLANK
    return HardLine(blank_lines)


def group(content: Doc) -> Group:
    """Create a group that tries to fit on one line."""
    return Group(content)


def nest(indent: int, content: Doc) -> Nest:
    """Indent content by specified amount."""
    return Nest(content=content, indent=indent)


def concat(docs: Sequence[Doc]) -> Doc:
    """Concatenate documents, flattening nested concats."""
    # Flatten nested concats for efficiency
    flattened = []
    for doc in docs:
        if isinstance(doc, Concat):
            flattened.extend(doc.docs)
        elif not isinstance(doc, Nil):
            flattened.append(doc)

    if not flattened:
        return NIL
    elif len(flattened) == 1:
        return flattened[0]
    else:
        return Concat(tuple(flattened))


def nil() -> Nil:
    """Create an empty document."""
    return NIL


def nbsp() -> Nbsp:
    """Create a non-breaking space."""
    return NBSP


def softline() -> SoftLine:
    """Create a soft line break (nothing or newline)."""
    return SOFTLINE


def comment(s: str) -> Comment:
    """Create a comment node with re-indentable content."""
    return Comment(s)


def indent(amount: int, content: Doc) -> Doc:
    """Create a group with nested indentation."""
    return group(nest(amount, content))


def join(docs: Sequence[Doc], separator: Doc) -> Join:
    """Join documents with a separator between each pair."""
    return Join(tuple(docs), separator)


# Control nodes for spacing specifications
@dataclass(slots=True, frozen=True)
class AfterSpec(Doc):
    """Spacing specification that should be applied after the preceding content."""

    spacing: Doc

    def __repr__(self) -> str:
        return f"AfterSpec({self.spacing!r})"


@dataclass(slots=True, frozen=True)
class BeforeSpec(Doc):
    """Spacing specification that should be applied before the following content."""

    spacing: Doc

    def __repr__(self) -> str:
        return f"BeforeSpec({self.spacing!r})"


@dataclass(slots=True, frozen=True)
class SeparatorSpec(Doc):
    """Default separator spacing (fallback if no before/after specs override)."""

    spacing: Doc | None
    preserved_trivia: Doc | None
    required: bool

    def __repr__(self) -> str:
        return (
            f"SeparatorSpec(spacing={self.spacing!r}, "
            f"preserved_trivia={self.preserved_trivia!r}, required={self.required})"
        )
