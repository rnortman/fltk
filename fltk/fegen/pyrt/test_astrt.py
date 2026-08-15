"""Tests for the AST runtime's backend-neutral pieces.

``bucket_children`` and ``CrossBackendEnumMixin`` are the two places where the runtime reads a
label's identity, and both are on the path a generated ``from_cst`` takes for a CST from any
backend.  What they may rely on is the canonical-name contract every conforming backend
implements — not ``enum.Enum``'s ``name``, which the Rust pyclasses do not have.
"""

from __future__ import annotations

import enum
import typing

import pytest

from fltk.fegen import fltk_cst, fltk_cst_protocol
from fltk.fegen.pyrt import astrt


class _Bare:
    """A label carrying nothing but the canonical name: the whole contract, and no more."""

    def __init__(self, canonical: str) -> None:
        self._fltk_canonical_name = canonical


class _Nameless:
    """A label from no conforming backend at all."""


class TestBucketChildren:
    """The bucket keys are the ``<MEMBER>`` component of the label's canonical name."""

    def test_python_enum_labels_key_by_their_member_names(self) -> None:
        """The keys match the enum member names."""
        labels = [fltk_cst.Items.Label.ITEM, fltk_cst.Items.Label.NO_WS, fltk_cst.Items.Label.ITEM]
        buckets = astrt.bucket_children([(label, index) for index, label in enumerate(labels)])

        assert buckets == {"ITEM": [0, 2], "NO_WS": [1]}
        assert list(buckets) == [label.name for label in dict.fromkeys(labels)]

    def test_protocol_label_sentinels_key_the_same_way(self) -> None:
        """The protocol module's own Label members carry the contract, so they bucket too."""
        buckets = astrt.bucket_children(
            [
                (fltk_cst_protocol.ItemsLabel.ITEM, "a"),
                (fltk_cst_protocol.ItemsLabel.WS_ALLOWED, "b"),
            ]
        )

        assert buckets == {"ITEM": ["a"], "WS_ALLOWED": ["b"]}

    def test_the_two_flavors_land_in_one_bucket(self) -> None:
        """A key is a plain string, so nothing about which flavor produced it survives."""
        buckets = astrt.bucket_children(
            [(fltk_cst.Items.Label.ITEM, "py"), (fltk_cst_protocol.ItemsLabel.ITEM, "proto")]
        )

        assert buckets == {"ITEM": ["py", "proto"]}

    def test_a_label_with_only_a_canonical_name_is_enough(self) -> None:
        """Nothing beyond the contract is read, which is what makes an unseen backend work."""
        buckets = astrt.bucket_children([(_Bare("Widget.Label.FROB"), 1), (_Bare("Widget.Label.FROB"), 2)])

        assert buckets == {"FROB": [1, 2]}

    def test_a_canonical_name_without_dots_is_its_own_key(self) -> None:
        """The suffix of a name with no separator is the whole name."""
        assert astrt.bucket_children([(_Bare("FROB"), 1)]) == {"FROB": [1]}

    def test_source_order_is_preserved_within_a_bucket(self) -> None:
        label = fltk_cst.Items.Label.ITEM
        assert astrt.bucket_children((label, index) for index in range(4)) == {"ITEM": [0, 1, 2, 3]}

    def test_unlabeled_children_are_skipped(self) -> None:
        """Trivia and ``$``-included literals carry no label and record nothing."""
        buckets = astrt.bucket_children([(None, "trivia"), (fltk_cst.Items.Label.ITEM, "x"), (None, "more")])

        assert buckets == {"ITEM": ["x"]}

    def test_a_label_without_the_contract_names_the_attribute_it_lacks(self) -> None:
        """Only conforming backends are supported; there is no fallback to ``.name``."""
        with pytest.raises(AttributeError, match="_fltk_canonical_name"):
            astrt.bucket_children([(typing.cast("typing.Any", _Nameless()), 1)])

    def test_an_enum_label_without_the_contract_is_refused_too(self) -> None:
        """A ``.name`` is not the contract, so a pre-canonical-name CST module regenerates."""

        class Stale(enum.Enum):
            ITEM = enum.auto()

        with pytest.raises(AttributeError, match="_fltk_canonical_name"):
            astrt.bucket_children([(typing.cast("typing.Any", Stale.ITEM), 1)])


class _Colour(astrt.CrossBackendEnumMixin, enum.Enum):
    """A generated value enum, spelled the way the emitter spells one."""

    RED = enum.auto()
    GREEN = enum.auto()


_Colour.RED._fltk_canonical_name = "_Colour.RED"
_Colour.GREEN._fltk_canonical_name = "_Colour.GREEN"


class TestCrossBackendEnumMixin:
    """Same-type equality goes through the canonical name."""

    def test_a_member_equals_itself(self) -> None:
        member = _Colour.RED
        assert member == _Colour.RED
        assert not (member != _Colour.RED)

    def test_distinct_members_are_unequal(self) -> None:
        assert _Colour.RED != _Colour.GREEN
        assert not (_Colour.RED == _Colour.GREEN)

    def test_hash_follows_the_canonical_name(self) -> None:
        assert hash(_Colour.RED) == hash("_Colour.RED")
        assert len({_Colour.RED, _Colour.GREEN}) == 2

    def test_a_member_is_usable_as_a_dict_key(self) -> None:
        table = {_Colour.RED: "warm", _Colour.GREEN: "cool"}
        assert table[_Colour.RED] == "warm"

    def test_another_flavor_carrying_the_same_canonical_name_compares_equal(self) -> None:
        """The whole point of the mixin: a PyO3 counterpart of the same member is the same value."""
        assert _Colour.RED == _Bare("_Colour.RED")
        assert _Colour.RED != _Bare("_Colour.GREEN")

    @pytest.mark.parametrize("other", [None, 1, "_Colour.RED", object()])
    def test_an_operand_carrying_no_canonical_name_is_unequal_never_an_error(self, other: object) -> None:
        assert (_Colour.RED == other) is False
        assert (_Colour.RED != other) is True

    def test_the_mixin_leaves_the_enum_member_name_alone(self) -> None:
        """``enum.Enum`` supplies ``name``; the mixin does not re-declare it."""
        assert _Colour.RED.name == "RED"
        assert typing.get_type_hints(astrt.CrossBackendEnumMixin).keys() == {"_fltk_canonical_name"}
