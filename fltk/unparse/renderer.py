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
                # Token content: embedded newlines are bytes, never layout breaks. A non-empty
                # Text at a layout line start takes the pending indent once (append_content);
                # an empty one is a no-op. Afterwards the renderer is never at a layout line
                # start, and the column is the width of the content's last physical line.
                append_content(doc.content, indent)
                _, newline, last = doc.content.rpartition("\n")
                if newline:
                    current_column = len(last)

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

                if self._fits(remaining_width, test_queue.copy(), at_line_start=at_beginning_of_line):
                    queue.insert(0, (indent, Mode.FLAT, doc.content))
                else:
                    queue.insert(0, (indent, Mode.BREAK, doc.content))

            else:
                error_msg = f"Unknown document type: {type(doc)}"
                raise ValueError(error_msg)

        return "".join(result)

    def _fits(self, width: int, items: list[tuple[int, Mode, Doc]], *, at_line_start: bool) -> bool:
        """Check if documents fit in remaining width when rendered flat.

        Indentation is charged exactly where `append_content` writes it -- once per non-empty
        call made at a layout line start, at the indent of the item making it -- and the
        line-start flag is re-armed exactly where `break_line` sets it. A Text is one
        `append_content` call; a Comment is one per line, with a `break_line` between.
        `at_line_start` is the renderer's `at_beginning_of_line` when the check begins.
        """
        if width < 0:
            return False

        column = 0  # Current column position

        # TODO(quality-fit-cursor-hand-mirrors-output-state-machine): `pay_indent` and `charge`
        # restate `append_content` / `break_line` rather than sharing their position state.
        def pay_indent(indent: int, *, nonempty: bool) -> None:
            """Mirror `append_content`'s indent: non-empty content at a line start pays it first."""
            nonlocal column, at_line_start
            if nonempty and at_line_start:
                column += indent
                at_line_start = False

        def charge(n: int, indent: int) -> bool:
            """Mirror `append_content` for `n` columns of content; return whether it still fits."""
            nonlocal column
            pay_indent(indent, nonempty=n > 0)
            column += n
            return column <= width

        while items:
            indent, mode, doc = items.pop(0)

            if isinstance(doc, Nil):
                continue
            elif isinstance(doc, Text):
                # A non-empty Text at a line start takes the indent once, before its first byte,
                # even when that byte is a newline. Continuation segments start at physical
                # column 0 and are never charged (the Text arm of `render` writes them verbatim).
                pay_indent(indent, nonempty=bool(doc.content))
                for i, segment in enumerate(doc.content.split("\n")):
                    if i > 0:
                        column = 0
                    column += len(segment)
                    if column > width:
                        return False
            elif isinstance(doc, Comment):
                # Each comment line is its own `append_content`, after a `break_line`.
                for i, comment_line in enumerate(doc.content.split("\n")):
                    if i > 0:
                        column = 0
                        at_line_start = True
                    if not charge(len(comment_line), indent):
                        return False
            elif isinstance(doc, Line | Nbsp):
                # One space in flat mode.
                if not charge(1, indent):
                    return False
            elif isinstance(doc, SoftLine):
                # Nothing in flat mode
                pass
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
