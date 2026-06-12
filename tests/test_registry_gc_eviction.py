"""GC/eviction/ABA tests for the CST handle registry.

These tests verify the weak-reference eviction guarantees of the canonical handle
registry in fltk-cst-core.  They require the phase4_roundtrip_cst extension to be
built with the `test-introspection` feature.

Test-authoring disciplines enforced throughout this file:

- **Delta assertions, not absolutes.**  The registry is process-wide; other tests
  (e.g. module-level parse fixtures in test_phase4_rust_fixture.py) may hold live
  entries.  Assert presence/absence of addresses *this test created*, never total
  registry size == 0.

- **Snapshot dicts hold strong refs.**  Every snapshot taken before an eviction
  check must be explicitly ``del``'d (or scoped out) before ``gc.collect()``.

- **Frame locals pin handles.**  Drop every local referencing a handle (``del``)
  before asserting eviction.  Helper functions that need to identify which entry
  corresponds to a node return the int address only, never the handle.

- **Determinism.**  CPython refcounting frees handles at last decref;
  ``gc.collect()`` is called anyway per convention.  No timing dependence.

- **``id()`` reuse.**  After eviction a freshly minted handle may reuse the dead
  handle's ``id()``; tests must not assert ``id(new) != id(old)``.  Non-
  resurrection is established by asserting the address was absent from the
  snapshot at the dead point, plus correctness of the fresh handle.
"""

from __future__ import annotations

import gc
import itertools

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fixture not available
# ---------------------------------------------------------------------------

phase4_roundtrip_cst = pytest.importorskip(
    "phase4_roundtrip_cst",
    reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
)

# Registry introspection wrappers exposed on the extension module.
_registry_snapshot = phase4_roundtrip_cst._registry_snapshot
_registry_lookup = phase4_roundtrip_cst._registry_lookup
_registry_register_if_absent = phase4_roundtrip_cst._registry_register_if_absent
_registry_force_register = phase4_roundtrip_cst._registry_force_register

# Node classes exposed through the `cst` submodule.
Entry = phase4_roundtrip_cst.cst.Entry
Identifier = phase4_roundtrip_cst.cst.Identifier

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def addr_of(node) -> int:
    """Return the Arc address for *node* by scanning the current registry snapshot.

    The snapshot is a temporary object; the generator expression drops it
    immediately on return so it cannot pin the handle.

    Raises ``AssertionError`` if *node* is not found in the registry, which
    indicates a registration bug (e.g. ``force_register``/``py_new`` failure)
    rather than a test-authoring defect.
    """
    addr = next((k for k, v in _registry_snapshot().items() if v is node), None)
    if addr is None:
        msg = f"node {node!r} not found in registry snapshot"
        raise AssertionError(msg)
    return addr


# Synthetic address allocator for direct-wrapper tests.  Uses small integers
# starting from 1, far below any mappable heap Arc address, so they cannot
# collide with real Arc addresses.  Weak eviction cleans entries up when test
# objects die regardless.
_synthetic_addr = itertools.count(1)


def _next_addr() -> int:
    return next(_synthetic_addr)


# ---------------------------------------------------------------------------
# Plain weakref-able class for direct-wrapper tests.
# (int/None cannot be stored in a WeakValueDictionary.)
# ---------------------------------------------------------------------------


class _Obj:
    """Minimal weakref-able object for direct registry tests."""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSnapshotPlumbing:
    """Verify that the snapshot/lookup plumbing itself works correctly."""

    def test_snapshot_maps_int_addr_to_handle(self) -> None:
        """Snapshot contains an int key whose value *is* the created node."""
        node = Identifier()
        snapshot = _registry_snapshot()
        assert any(isinstance(k, int) and v is node for k, v in snapshot.items())
        del snapshot, node

    def test_py_new_registers_immediately(self) -> None:
        """A node is present in the snapshot immediately after construction (py_new path)."""
        node = Identifier()
        snapshot = _registry_snapshot()
        addr = next((k for k, v in snapshot.items() if v is node), None)
        assert addr is not None, "node not found in registry snapshot right after construction"
        del snapshot, node


class TestEvictionAndFreshHandles:
    """Verify weak-reference eviction and fresh-handle minting with real fixture nodes."""

    def test_handle_dropped_entry_evicted(self) -> None:
        """After dropping the only handle reference and GC, the entry is gone."""
        node = Identifier()
        addr = addr_of(node)
        del node
        gc.collect()
        snapshot = _registry_snapshot()
        assert addr not in snapshot, f"addr {addr} still present after handle GC"
        del snapshot

    def test_arc_alive_handle_dead_fresh_handle_no_resurrection(self) -> None:
        """Core ABA scenario: handle GC evicts entry even when Arc is still alive.

        After eviction, re-reading via the parent's accessor mints a fresh
        handle at the same Arc address; the fresh handle is correct and canonical.
        """
        parent = Entry()
        child = Identifier()
        parent.append_key(child)
        addr = addr_of(child)
        del child
        gc.collect()
        snapshot_after_gc = _registry_snapshot()
        assert addr not in snapshot_after_gc, (
            f"addr {addr} still present after handle GC — Arc is alive in parent but "
            "handle should have been evicted (registry must hold only a weak ref)"
        )
        del snapshot_after_gc

        # Re-read through the parent: a fresh handle must be minted at the same Arc addr.
        fresh = parent.child_key()
        assert isinstance(fresh, Identifier)
        new_addr = addr_of(fresh)
        assert new_addr == addr, (
            f"fresh handle addr {new_addr} != original addr {addr} — same Arc must produce same address"
        )
        # Canonical handle is stable: two accessor calls return the same Python object.
        assert parent.child_key() is fresh
        del fresh, parent

    def test_stress_create_drop_cycles(self) -> None:
        """Create/drop cycles do not leave stale entries or break identity invariants.

        Runs ~200 iterations.  Within each iteration the two accessor calls must
        return the same Python object (is-identity).  After the loop, none of the
        recorded addresses remain in the registry.
        """
        recorded_addrs: list[int] = []

        for _ in range(200):
            parent = Entry()
            child = Identifier()
            parent.append_key(child)
            assert len(parent.children) == 1 and len(parent.children[0]) == 2, (
                "unexpected children shape after append_key"
            )
            child_via_children = parent.children[0][1]
            child_via_accessor = parent.child_key()
            assert child_via_children is child_via_accessor, (
                "two accessor paths returned different Python objects for the same node"
            )
            recorded_addrs.append(addr_of(child))
            del parent, child, child_via_children, child_via_accessor
            gc.collect()

        snapshot = _registry_snapshot()
        still_live = [a for a in recorded_addrs if a in snapshot]
        assert not still_live, f"stale registry entries remain after all drops: {still_live}"
        del snapshot


class TestDirectRegistrySemantics:
    """Verify registry semantics directly via the Python-callable wrappers.

    Uses synthetic integer addresses (from _next_addr()) to avoid any interaction
    with real Arc addresses.  The objects registered are _Obj instances (plain
    Python class, weakref-capable).

    Note: the ``registered == false`` arm inside ``get_or_insert_with``
    (registry.rs:121-125) requires another thread to install a handle between
    this thread's ``lookup`` miss and its ``register_if_absent`` — impossible
    under single-threaded CPython with the GIL held for the whole Rust call.
    That arm cannot be forced from Python; the test below for
    ``register_if_absent`` returning ``False`` covers the same function-level
    contract the arm depends on.
    """

    def test_lookup_miss_register_hit(self) -> None:
        """lookup miss → register_if_absent True → lookup hit."""
        addr = _next_addr()
        assert _registry_lookup(addr) is None
        obj = _Obj()
        registered = _registry_register_if_absent(addr, obj)
        assert registered is True
        assert _registry_lookup(addr) is obj
        del obj

    def test_register_if_absent_false_when_live_entry(self) -> None:
        """register_if_absent returns False when a live entry exists; existing entry unchanged."""
        addr = _next_addr()
        obj_a = _Obj()
        obj_b = _Obj()
        _registry_register_if_absent(addr, obj_a)
        registered = _registry_register_if_absent(addr, obj_b)
        assert registered is False, "expected False when live entry already present"
        assert _registry_lookup(addr) is obj_a, "existing entry must not be replaced"
        del obj_a, obj_b

    def test_force_register_overwrites_live_entry(self) -> None:
        """force_register replaces a live entry with a new handle."""
        addr = _next_addr()
        obj_a = _Obj()
        obj_b = _Obj()
        _registry_register_if_absent(addr, obj_a)
        _registry_force_register(addr, obj_b)
        assert _registry_lookup(addr) is obj_b, "force_register must overwrite the live entry"
        del obj_a, obj_b

    def test_weak_eviction_direct(self) -> None:
        """After dropping the registered object, lookup returns None and addr absent from snapshot."""
        addr = _next_addr()
        obj = _Obj()
        _registry_register_if_absent(addr, obj)
        del obj
        gc.collect()
        assert _registry_lookup(addr) is None
        snapshot = _registry_snapshot()
        assert addr not in snapshot
        del snapshot

    def test_register_after_eviction_installs_fresh(self) -> None:
        """register_if_absent returns True at an evicted address (dead weak entry is treated as absent)."""
        addr = _next_addr()
        obj_a = _Obj()
        _registry_register_if_absent(addr, obj_a)
        del obj_a
        gc.collect()
        obj_b = _Obj()
        registered = _registry_register_if_absent(addr, obj_b)
        assert registered is True, "evicted entry must not block re-registration"
        assert _registry_lookup(addr) is obj_b
        del obj_b
