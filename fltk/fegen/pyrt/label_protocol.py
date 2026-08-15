"""LabelProtocol: the backend-agnostic contract for CST child labels.

Generated protocol modules, concrete CST modules and Rust stubs all annotate label-typed
slots with ``LabelProtocol`` rather than one backend's label class, so a single annotation
accepts every backend's labels.
"""

from typing import Protocol

_LABEL_INFIX = ".Label."


def label_canonical_name(class_name: str, member_name: str) -> str:
    """The canonical name of one label member: ``"<Class>.Label.<MEMBER>"``.

    The cross-backend identity string every CST backend's labels carry as
    ``_fltk_canonical_name``: the Python enum members, the PyO3 pyclasses, the protocol
    module's sentinels.  Equality, hashing, and bucket keys across backends are all keyed on
    it, so every producer must spell it here.
    """
    return f"{class_name}{_LABEL_INFIX}{member_name}"


def label_member_name(canonical_name: str) -> str:
    """The ``<MEMBER>`` component of a label's canonical name.

    The inverse of :func:`label_canonical_name` over its member argument, and the same string a
    Python enum label carries as its member name.  A name carrying no separator is its own
    member component.
    """
    return canonical_name.rsplit(".", 1)[-1]


class LabelProtocol(Protocol):
    """Structural protocol satisfied by every flavor of CST child label.

    Two labels from different backends are ``==`` and hash equal exactly when their
    ``_fltk_canonical_name`` strings match.  That is a semantic contract on the backends, not
    something a type checker can see; the committed cross-backend equality and hash suites are
    what hold the backends to it.

    ``_fltk_canonical_name`` is a read-only property so that both a plain string attribute
    and a ``@property`` getter satisfy it; a mutable protocol attribute would be invariant
    and reject the getter.
    """

    @property
    def _fltk_canonical_name(self) -> str:
        """Cross-backend identity string, ``"<Class>.Label.<MEMBER>"``."""
        ...

    def __hash__(self) -> int:
        """Labels are hashable."""
        ...
