"""Tests for the label canonical-name format.

The format is a wire format between three producers — the concrete CST emitter, the protocol
emitter and the Rust codegen — and one consumer, the AST runtime's bucket keys.  Everything here
checks that the shared spelling and the shared reading agree, and that the committed modules'
labels really carry what the helpers produce.
"""

from __future__ import annotations

import enum
import typing

import pytest

from fltk.fegen import fltk_cst, fltk_cst_protocol
from fltk.fegen.pyrt import label_protocol


class TestCanonicalNameFormat:
    def test_the_spelling_is_class_label_member(self) -> None:
        assert label_protocol.label_canonical_name("Items", "ITEM") == "Items.Label.ITEM"

    @pytest.mark.parametrize(("class_name", "member"), [("Items", "ITEM"), ("Grammar", "RULE"), ("X", "A_B")])
    def test_the_member_component_reads_back(self, class_name: str, member: str) -> None:
        """The decoder the AST runtime buckets with is the inverse of the encoder."""
        canonical = label_protocol.label_canonical_name(class_name, member)

        assert label_protocol.label_member_name(canonical) == member

    def test_a_name_without_a_separator_is_its_own_member_component(self) -> None:
        assert label_protocol.label_member_name("FROB") == "FROB"


class TestCommittedBackendsCarryTheFormat:
    """The concrete enums and the protocol sentinels both spell what the helpers produce."""

    def test_concrete_label_members(self) -> None:
        checked = 0
        for name in dir(fltk_cst):
            node_class = getattr(fltk_cst, name)
            label_class = getattr(node_class, "Label", None)
            if not (isinstance(node_class, type) and isinstance(label_class, type)):
                continue
            if not issubclass(label_class, enum.Enum):
                continue
            for member in label_class:
                canonical = typing.cast("label_protocol.LabelProtocol", member)._fltk_canonical_name
                assert canonical == label_protocol.label_canonical_name(name, member.name)
                assert label_protocol.label_member_name(canonical) == member.name
                checked += 1
        assert checked > 0, "no concrete Label members found; the sweep found nothing to check"

    def test_protocol_label_sentinels(self) -> None:
        checked = 0
        for name in fltk_cst_protocol.__all__:
            if not name.endswith("Label"):
                continue
            namespace = getattr(fltk_cst_protocol, name)
            node_class_name = name.removesuffix("Label")
            for member_name, member in vars(namespace).items():
                if member_name.startswith("_"):
                    continue
                assert member._fltk_canonical_name == label_protocol.label_canonical_name(node_class_name, member_name)
                assert label_protocol.label_member_name(member._fltk_canonical_name) == member_name
                checked += 1
        assert checked > 0, "no protocol label sentinels found; the sweep found nothing to check"
