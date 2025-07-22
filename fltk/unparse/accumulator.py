"""DocAccumulator that prevents consecutive trivia nodes."""

from dataclasses import dataclass, replace
from typing import Optional

from fltk.unparse.combinators import NIL, Concat, Doc, Group, Join, Nest, concat


@dataclass(frozen=True)
class DocNode:
    """A node in the linked list of docs"""

    doc: Doc
    tail: Optional["DocNode"] = None


@dataclass(frozen=True)
class DocAccumulator:
    """Immutable document accumulator with tree structure for nesting"""

    head: DocNode | None = None
    last_was_trivia: bool = False
    parent: Optional["DocAccumulator"] = None
    nesting_doc: Doc | None = None

    def add_non_trivia(self, doc: Doc) -> "DocAccumulator":
        """Add non-trivia content, returning new accumulator"""
        new_head = DocNode(doc, self.head)
        return DocAccumulator(head=new_head, last_was_trivia=False, parent=self.parent, nesting_doc=self.nesting_doc)

    def add_trivia(self, doc: Doc) -> "DocAccumulator":
        """Add trivia content, returning new accumulator"""
        new_head = DocNode(doc, self.head)
        return DocAccumulator(head=new_head, last_was_trivia=True, parent=self.parent, nesting_doc=self.nesting_doc)

    def add_accumulator(self, other: "DocAccumulator") -> "DocAccumulator":
        """Merge another accumulator, preserving its trivia state.

        This only works with an already-flattened accumulator with no open nesting docs.
        """
        if other.parent or other.nesting_doc:
            msg = f"Attempt to merge a non-flattened accumulator: {other}"
            raise RuntimeError(msg)
        other_doc = other.doc
        new_head = DocNode(other_doc, self.head)
        return DocAccumulator(
            head=new_head,
            last_was_trivia=other.last_was_trivia if other_doc != NIL else self.last_was_trivia,
            parent=self.parent,
            nesting_doc=self.nesting_doc,
        )

    def push_group(self) -> "DocAccumulator":
        """Start a new group nesting level"""
        return DocAccumulator(
            parent=self,
            nesting_doc=Group(NIL),  # Placeholder
        )

    def push_nest(self, indent: int) -> "DocAccumulator":
        """Start a new nest nesting level"""
        return DocAccumulator(
            parent=self,
            nesting_doc=Nest(content=NIL, indent=indent),  # Placeholder
        )

    def push_join(self, separator: Doc) -> "DocAccumulator":
        """Start a new join nesting level"""
        return DocAccumulator(
            parent=self,
            nesting_doc=Join(docs=(), separator=separator),  # Placeholder
        )

    def pop_group(self) -> "DocAccumulator":
        if not isinstance(self.nesting_doc, Group):
            msg = f"Improperly nested tree: Expected Group but have {type(self.nesting_doc)}"
            raise RuntimeError(msg)
        return self._pop()

    def pop_nest(self) -> "DocAccumulator":
        if not isinstance(self.nesting_doc, Nest):
            msg = f"Improperly nested tree: Expected Nest but have {type(self.nesting_doc)}"
            raise RuntimeError(msg)
        return self._pop()

    def pop_join(self) -> "DocAccumulator":
        if not isinstance(self.nesting_doc, Join):
            msg = f"Improperly nested tree: Expected Join but have {type(self.nesting_doc)}"
            raise RuntimeError(msg)
        return self._pop_join()

    def _pop(self) -> "DocAccumulator":
        """End current nesting level, wrapping content and returning parent"""
        if self.parent is None or self.nesting_doc is None:
            msg = f"Invariant failed: attempt to pop unnested accumulator: {self}"
            raise RuntimeError(msg)
        content = self.doc
        wrapped = replace(self.nesting_doc, content=content)
        return self.parent.add_trivia(wrapped) if self.last_was_trivia else self.parent.add_non_trivia(wrapped)

    def _pop_join(self) -> "DocAccumulator":
        """End join nesting level, converting content to docs list"""
        if self.parent is None or self.nesting_doc is None:
            msg = f"Invariant failed: attempt to pop unnested accumulator: {self}"
            raise RuntimeError(msg)
        content = self.doc
        # For Join, we need to extract the list of docs from the concat
        docs = []
        if isinstance(content, Concat):
            docs = list(content.docs)
        elif content != NIL:
            docs = [content]
        wrapped = replace(self.nesting_doc, docs=tuple(docs))
        return self.parent.add_trivia(wrapped) if self.last_was_trivia else self.parent.add_non_trivia(wrapped)

    @property
    def doc(self) -> Doc:
        """Build final doc for this level"""
        # TODO: This should be memoized for performance.
        docs = []
        current = self.head
        while current:
            docs.append(current.doc)
            current = current.tail
        docs.reverse()
        return concat(docs) if docs else NIL
