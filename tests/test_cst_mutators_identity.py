"""Rust identity tests for named mutators (§4.3 of cst-named-mutators design).

Verifies registry / handle-identity properties for insert / remove_at /
replace_at / clear on Rust CST nodes:

- Handle obtained before remove_at remains valid and usable after removal.
- remove_at return value *is* the previously obtained handle (is-stable).
- Removed child re-inserted via insert/append → subsequent reads return the
  same handle (is-stable).
- replace_at: evicted child's externally held handle unaffected; new child
  read back is-stable.
- Registry eviction: clear() + handle drop + GC → registry entry absent and
  weakref dead.

Requires phase4_roundtrip_cst built with test-introspection (the default for
that fixture).  All tests are skipped if the fixture is not importable.

Test-authoring disciplines (same as test_registry_gc_eviction.py):

- Delta assertions, not absolutes: the registry is process-wide.
- Snapshot dicts hold strong refs — del before GC assertions.
- Frame locals pin handles — del before eviction assertions.
- CPython refcounting is deterministic; gc.collect() called per convention.
"""

from __future__ import annotations

import gc

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fixture not available
# ---------------------------------------------------------------------------

phase4_roundtrip_cst = pytest.importorskip(
    "phase4_roundtrip_cst",
    reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
)

_registry_snapshot = phase4_roundtrip_cst._registry_snapshot
cst = phase4_roundtrip_cst.cst
Entry = cst.Entry
Identifier = cst.Identifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _addr_of(node) -> int:
    """Return the Arc address for *node* from the current snapshot.

    Never returns the snapshot itself (would pin the handle).
    Raises AssertionError if node is not in the registry.
    """
    addr = next((k for k, v in _registry_snapshot().items() if v is node), None)
    if addr is None:
        msg = f"node {node!r} not found in registry snapshot"
        raise AssertionError(msg)
    return addr


# ---------------------------------------------------------------------------
# §4.3 identity tests
# ---------------------------------------------------------------------------


class TestRemoveAtIdentity:
    """Handle identity properties for remove_at."""

    def test_handle_before_remove_still_valid(self) -> None:
        """Handle obtained before remove_at remains valid and usable after removal."""
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        parent.remove_at(0)

        # child handle is still a live, usable Identifier
        assert isinstance(child, Identifier)
        # Can still append it elsewhere
        parent2 = Entry()
        parent2.append_key(child)
        assert parent2.child_key() is child
        del parent, parent2, child

    def test_remove_at_return_is_same_handle(self) -> None:
        """remove_at return value *is* the previously obtained handle for that child."""
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        _, returned = parent.remove_at(0)
        assert returned is child
        del parent, child, returned

    def test_removed_child_reinserted_via_insert_is_stable(self) -> None:
        """Removed child re-inserted via insert → subsequent children read returns same handle."""
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        lbl, removed = parent.remove_at(0)
        assert removed is child

        parent.insert(0, child, label=lbl)
        via_children = parent.children[0][1]
        via_accessor = parent.child_key()
        assert via_children is child
        assert via_accessor is child
        del parent, child, removed, via_children, via_accessor

    def test_removed_child_reinserted_via_append_is_stable(self) -> None:
        """Removed child re-inserted via append → handle is-stable on subsequent reads."""
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        _, removed = parent.remove_at(0)
        parent.append_key(child)
        assert parent.child_key() is child
        del parent, child, removed


class TestReplaceAtIdentity:
    """Handle identity properties for replace_at."""

    def test_evicted_child_handle_unaffected(self) -> None:
        """replace_at: externally held handle for the evicted child remains valid."""
        parent = Entry()
        child_orig = Identifier()
        child_new = Identifier()
        parent.append_key(child_orig)

        parent.replace_at(0, child_new, label=Entry.Label.KEY)

        # child_orig handle still valid — it was removed, not destroyed
        assert isinstance(child_orig, Identifier)
        del parent, child_orig, child_new

    def test_new_child_read_back_is_stable(self) -> None:
        """replace_at: new child read back via accessor is the same handle."""
        parent = Entry()
        child_orig = Identifier()
        child_new = Identifier()
        parent.append_key(child_orig)

        parent.replace_at(0, child_new, label=Entry.Label.KEY)

        assert parent.child_key() is child_new
        del parent, child_orig, child_new


class TestClearRegistryEviction:
    """Registry eviction after clear()."""

    def test_clear_then_drop_evicts_registry_entry(self) -> None:
        """clear() + drop handle + GC → registry entry absent.

        Pins two things:
        1. clear() holds no strong reference to removed children.
        2. The registry self-evicts after removal (§2.5 of design).
        """
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        # Confirm child is in the registry before clear
        snap_before = _registry_snapshot()
        assert any(v is child for v in snap_before.values()), "child not in registry before clear"
        addr = next(k for k, v in snap_before.items() if v is child)
        del snap_before  # release strong ref before GC

        parent.clear()
        del child  # drop only external reference
        gc.collect()

        snap_after = _registry_snapshot()
        assert addr not in snap_after, (
            f"registry entry at addr {addr} still present after clear() + handle drop + GC; "
            "clear() must not retain a strong handle reference"
        )
        del snap_after, parent

    def test_remove_at_then_drop_evicts_registry_entry(self) -> None:
        """remove_at() + discard return + drop handle + GC → registry entry absent.

        Pins that remove_at holds no strong reference to the removed child after
        the return value is itself discarded (§2.5 of design).
        """
        parent = Entry()
        child = Identifier()
        parent.append_key(child)

        # Confirm child is in the registry before remove_at
        snap_before = _registry_snapshot()
        assert any(v is child for v in snap_before.values()), "child not in registry before remove_at"
        addr = next(k for k, v in snap_before.items() if v is child)
        del snap_before  # release strong ref before GC

        # Discard the return value immediately so the only strong ref is `child`.
        _ = parent.remove_at(0)
        del _  # drop the return value (which is the same handle as child)
        del child  # drop the only remaining external reference
        gc.collect()

        snap_after = _registry_snapshot()
        assert addr not in snap_after, (
            f"registry entry at addr {addr} still present after remove_at() + handle drop + GC; "
            "remove_at must not retain a strong handle reference"
        )
        del snap_after, parent
