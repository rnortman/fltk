/// `Shared<T>` — shared-ownership, interior-mutable wrapper for CST node data structs.
///
/// This is an `Arc<RwLock<T>>` newtype.  Every node-typed child in a generated CST
/// is stored as a `Shared<ChildType>` so that multiple Python handles (and the Rust side)
/// can refer to the *same* in-memory node.  Reference semantics match the Python backend:
/// reading a child twice returns the same object, and mutations are visible through all
/// aliases.
///
/// # Clone semantics
/// `Clone` on `Shared<T>` is **shallow** — it increments the reference count and returns
/// a new handle pointing to the same data.  It does NOT deep-copy the node.  This is
/// deliberate: both the Rust and Python CST backends use reference semantics.
///
/// # Equality
/// `PartialEq` first checks pointer equality (`ptr_eq`) as a short-circuit.  This handles
/// `x == x` (same pointer on both sides) without locking.  Without the short-circuit,
/// comparing a `Shared` against itself would attempt to read-lock the same
/// `std::sync::RwLock` twice on one thread, which `std` documents may deadlock when a
/// writer is queued.
///
/// **Important limitation**: the short-circuit fires only when *the same `Shared` object
/// sits at the same position on both sides* of the comparison (i.e. `ptr_eq` returns true).
/// It does NOT prevent re-entry when a shared node appears anywhere inside the compared
/// trees at a *different* position (position-shifted sharing in a DAG) — e.g. comparing
/// `B` (whose child is `A`) against `C` (whose child is also `A`) will read-lock `A` while
/// the outer guard on `B` or `C` is still held.  `std::sync::RwLock` same-thread
/// read-re-entry may deadlock when a concurrent writer is queued.  Deep `PartialEq` on a
/// DAG is therefore only deadlock-free in the absence of concurrent writers.  Callers in
/// multithreaded contexts must ensure no writer holds a guard on any node in the compared
/// trees during the comparison.
///
/// # Poisoning
/// A panic while a `write()` guard is held poisons a `std::sync::RwLock`.  `Shared` ignores
/// poison via `PoisonError::into_inner` so one panic cannot permanently brick a node tree.
///
/// # Reference cycles
/// Shared ownership makes user-created reference cycles possible.  `PartialEq`, `Debug`,
/// and other recursive operations will loop infinitely on a cycle — the same contract as
/// the Python backend.  Cycles also leak memory (Arc does not break cycles).  Do not create
/// cycles.
use std::fmt;
use std::sync::{Arc, RwLock, RwLockReadGuard, RwLockWriteGuard};

pub struct Shared<T>(Arc<RwLock<T>>);

impl<T> Shared<T> {
    /// Construct a new `Shared<T>` wrapping `value`.
    pub fn new(value: T) -> Self {
        Shared(Arc::new(RwLock::new(value)))
    }

    /// Acquire a read lock, ignoring poison.
    pub fn read(&self) -> RwLockReadGuard<'_, T> {
        self.0.read().unwrap_or_else(|e| e.into_inner())
    }

    /// Acquire a write lock, ignoring poison.
    pub fn write(&self) -> RwLockWriteGuard<'_, T> {
        self.0.write().unwrap_or_else(|e| e.into_inner())
    }

    /// Return `true` if `self` and `other` point to the same allocation.
    ///
    /// This is a cheap pointer comparison (no locking).  Used by `PartialEq` as a
    /// short-circuit to avoid same-lock re-entry.
    pub fn ptr_eq(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.0, &other.0)
    }

    /// Return the raw `Arc` pointer address as a `usize`.
    ///
    /// Used as the registry key in the canonical-wrapper registry.
    pub fn arc_ptr(&self) -> usize {
        Arc::as_ptr(&self.0) as usize
    }
}

impl<T> Clone for Shared<T> {
    /// Shallow clone: increments the reference count.  Does NOT copy the contained value.
    fn clone(&self) -> Self {
        Shared(Arc::clone(&self.0))
    }
}

impl<T: PartialEq> PartialEq for Shared<T> {
    fn eq(&self, other: &Self) -> bool {
        // Short-circuit: same pointer → equal without locking.
        // This handles `x == x` and shared-subtree cases in a DAG, where locking the
        // same RwLock twice on one thread may deadlock (std::sync::RwLock).
        if self.ptr_eq(other) {
            return true;
        }
        // Different allocations: read-lock both and compare by value.
        *self.read() == *other.read()
    }
}

impl<T: fmt::Debug> fmt::Debug for Shared<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Debug::fmt(&*self.read(), f)
    }
}

impl<T> From<T> for Shared<T> {
    fn from(value: T) -> Self {
        Shared::new(value)
    }
}
