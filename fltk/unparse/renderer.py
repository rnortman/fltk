"""Wadler-Lindig pretty-printing algorithm implementation."""

from dataclasses import dataclass
from enum import Enum

from fltk.unparse.combinators import (
    Comment,
    Concat,
    Doc,
    Group,
    HardLine,
    Line,
    Nbsp,
    Nest,
    Nil,
    SoftLine,
    Text,
)


@dataclass
class RendererConfig:
    """Configuration for the formatter."""

    indent_width: int = 4
    max_width: int = 80


class Mode(Enum):
    """Rendering mode for groups."""

    FLAT = "flat"  # Render line breaks as spaces/nothing
    BREAK = "break"  # Render line breaks as newlines


# Type alias for the rendering queue
# Each item is (indent_level, mode, document)
RenderItem = tuple[int, Mode, Doc]


class Renderer:
    """Wadler-Lindig pretty-printer for combinator documents."""

    def __init__(self, config: RendererConfig | None = None) -> None:
        self.config = config or RendererConfig()

    def render(self, doc: Doc) -> str:
        """Render a document with the given maximum width."""
        result = []
        current_column = 0
        at_beginning_of_line = True

        # Helper functions that capture local state
        def break_line() -> None:
            """Append a newline and mark that we're at beginning of line."""
            nonlocal at_beginning_of_line, current_column
            result.append("\n")
            at_beginning_of_line = True
            current_column = 0

        def append_content(text: str, indent: int) -> None:
            """Append text, adding indentation if at beginning of line."""
            nonlocal at_beginning_of_line, current_column
            if text and at_beginning_of_line:
                indentation = " " * indent
                result.append(indentation)
                current_column = indent
                at_beginning_of_line = False
            if text:
                result.append(text)
                current_column += len(text)

        # Queue of items to process: (indent, mode, doc)
        queue: list[RenderItem] = [(0, Mode.FLAT, Group(doc))]

        while queue:
            indent, mode, doc = queue.pop(0)

            if isinstance(doc, Nil):
                continue

            elif isinstance(doc, Text):
                # Text nodes: render content as-is, but track newlines for column position
                lines = doc.content.split("\n")
                for i, line in enumerate(lines):
                    if i > 0:
                        break_line()
                    append_content(line, indent)

            elif isinstance(doc, Comment):
                # Comment nodes: re-indent multi-line content
                lines = doc.content.split("\n")
                for i, line in enumerate(lines):
                    if i > 0:
                        break_line()
                    # For comments, we always append the line (even if empty)
                    # but use append_content to handle indentation properly
                    append_content(line, indent)

            elif isinstance(doc, Line):
                if mode == Mode.FLAT:
                    append_content(" ", indent)
                else:
                    break_line()

            elif isinstance(doc, SoftLine):
                if mode == Mode.FLAT:
                    # SoftLine renders as nothing in flat mode
                    pass
                else:
                    break_line()

            elif isinstance(doc, Nbsp):
                # Non-breaking space always renders as space
                append_content(" ", indent)

            elif isinstance(doc, HardLine):
                # Hard lines always break
                for _ in range(1 + doc.blank_lines):
                    break_line()

            elif isinstance(doc, Concat):
                # Expand concat docs in reverse order to maintain order
                for d in reversed(doc.docs):
                    queue.insert(0, (indent, mode, d))

            elif isinstance(doc, Nest):
                new_indent = indent + doc.indent * self.config.indent_width
                queue.insert(0, (new_indent, mode, doc.content))

            elif isinstance(doc, Group):
                # Check if group fits on current line
                remaining_width = self.config.max_width - current_column
                test_queue = [(indent, Mode.FLAT, doc.content)]

                if self._fits(remaining_width, test_queue.copy()):
                    queue.insert(0, (indent, Mode.FLAT, doc.content))
                else:
                    queue.insert(0, (indent, Mode.BREAK, doc.content))

            else:
                error_msg = f"Unknown document type: {type(doc)}"
                raise ValueError(error_msg)

        return "".join(result)

    def _fits(self, width: int, items: list[tuple[int, Mode, Doc]]) -> bool:
        """Check if documents fit in remaining width when rendered flat."""
        if width < 0:
            return False

        column = 0  # Current column position

        while items:
            indent, mode, doc = items.pop(0)

            if isinstance(doc, Nil):
                continue
            elif isinstance(doc, Text | Comment):
                # Both Text and Comment are newline-aware for width calculation
                lines = doc.content.split("\n")
                for i, line in enumerate(lines):
                    if i > 0:
                        # Newline resets column to 0
                        column = 0
                    column += len(line)
                    if column > width:
                        return False
            elif isinstance(doc, Line):
                column += 1  # Space in flat mode
                if column > width:
                    return False
            elif isinstance(doc, SoftLine):
                # Nothing in flat mode
                pass
            elif isinstance(doc, Nbsp):
                column += 1
                if column > width:
                    return False
            elif isinstance(doc, HardLine):
                return False  # Forces break
            elif isinstance(doc, Concat):
                for d in reversed(doc.docs):
                    items.insert(0, (indent, mode, d))
            elif isinstance(doc, Nest):
                new_indent = indent + doc.indent * self.config.indent_width
                items.insert(0, (new_indent, mode, doc.content))
            elif isinstance(doc, Group):
                items.insert(0, (indent, Mode.FLAT, doc.content))

        return True
