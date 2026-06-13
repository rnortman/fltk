/// Canonical wrapper registry — ensures at most one live Python handle per `Shared<T>` allocation.
///
/// # Purpose
/// When Rust returns a node-typed child to Python, it must return the *same* Python object
/// on every call (Python `is`-identity must be stable).  Without caching, every `to_pyobject`
/// call would call `Py::new(py, handle)` and mint a fresh Python object, so `a is b` would
/// always be `False` even if `a` and `b` refer to the same node.
///
/// The registry maps `Arc` address (`usize`) → `Py<PyAny>` (weak reference) and is stored in
/// a process-wide `PyOnceLock<Py<PyAny>>` holding a Python `weakref.WeakValueDictionary`.
///
/// # Invariant
/// At most one live Python handle exists per unique `Shared<T>` allocation.
/// - **wrap-out** (`get_or_register`): looks up by Arc address; hit → bump refcount and return;
///   miss → caller creates the handle, then calls `get_or_register` to install it.
/// - **hand-in** (`register_if_absent`): when Python passes a handle to Rust (e.g. `append`),
///   the handle is registered as canonical for its `Shared` address if not already present.
///
/// # ABA safety
/// Weak values auto-evict when the handle is GC'd.  Address reuse is only possible after
/// both the handle *and* the `Arc` are dead, at which point the entry is already evicted
/// (the canonical handle holds the `Arc` strongly via `Shared<T>` inside the `PyNode` struct).
///
/// # GIL
/// All operations require the GIL (`py: Python<'_>`).  The registry itself is a Python
/// `weakref.WeakValueDictionary`, so all access goes through Python object protocol.
use pyo3::prelude::*;
use pyo3::sync::PyOnceLock;
#[cfg(any(test, feature = "test-introspection"))]
use pyo3::types::PyDict;

/// Process-wide registry: a Python `weakref.WeakValueDictionary` mapping
/// Arc-address (int key) → canonical Python handle (weak value).
static CANONICAL_REGISTRY: PyOnceLock<Py<PyAny>> = PyOnceLock::new();

/// Return the process-wide `weakref.WeakValueDictionary`, initialising it on first call.
fn get_registry(py: Python<'_>) -> PyResult<Bound<'_, PyAny>> {
    let obj = CANONICAL_REGISTRY.get_or_try_init(py, || {
        let weakref = py.import("weakref")?;
        let wvd = weakref.getattr("WeakValueDictionary")?.call0()?;
        Ok::<Py<PyAny>, PyErr>(wvd.unbind())
    })?;
    Ok(obj.bind(py).clone())
}

/// Look up the canonical handle for `arc_addr` in the registry.
///
/// Returns `Some(handle)` if a live canonical handle is registered for this address,
/// `None` otherwise (miss: first wrap-out, or previous canonical handle was GC'd).
pub fn lookup(py: Python<'_>, arc_addr: usize) -> PyResult<Option<Py<PyAny>>> {
    let registry = get_registry(py)?;
    let key = arc_addr.into_pyobject(py)?;
    let result = registry.call_method1("get", (key, py.None()))?;
    if result.is_none() {
        Ok(None)
    } else {
        Ok(Some(result.unbind()))
    }
}

/// Register `handle` as the canonical handle for `arc_addr` if no live entry exists.
///
/// Returns `true` if the handle was newly registered, `false` if an existing live handle
/// was already present (in which case `handle` is *not* the canonical one — callers
/// should return the existing canonical handle instead).
pub fn register_if_absent(py: Python<'_>, arc_addr: usize, handle: &Bound<'_, PyAny>) -> PyResult<bool> {
    let registry = get_registry(py)?;
    let key = arc_addr.into_pyobject(py)?;
    // `setdefault(key, value)` inserts only when key is absent (or weak value is dead).
    // Returns the existing value if present, the newly-set value if absent.
    // We compare the returned object to `handle` by identity to tell which case it was.
    let result = registry.call_method1("setdefault", (key, handle))?;
    Ok(result.is(handle))
}

/// Force-set `handle` as the canonical handle for `arc_addr`, overwriting any previous entry.
///
/// Used during hand-in: when Python passes a handle to Rust and there is no entry yet
/// (the node was just created in Python and hasn't been read through the Rust side),
/// we install the Python-side handle so wrap-out later returns the same object.
///
/// Prefer `register_if_absent` when the caller can tolerate returning the previously-registered
/// canonical handle; use `force_register` only when the caller *owns* the handle (e.g.
/// `py_new` minting a fresh `Shared` + handle where no alias can exist yet).
///
/// # Caller contract
/// `arc_addr` must be the address of the `Arc` inside the `Shared<T>` that `handle` wraps.
/// Registering an address with an unrelated object corrupts typed accessors: a subsequent
/// `get_or_insert_with` hit will return the unrelated object to callers that cast it to the
/// expected node type.  Only use this function from generated code or `to_py_canonical` where
/// the address/handle pairing is guaranteed by construction.
pub fn force_register(py: Python<'_>, arc_addr: usize, handle: &Bound<'_, PyAny>) -> PyResult<()> {
    let registry = get_registry(py)?;
    let key = arc_addr.into_pyobject(py)?;
    registry.set_item(key, handle)?;
    Ok(())
}

/// Look up `arc_addr`; on hit return the existing handle, on miss call `make_handle` to
/// create a new handle, register it, and return it.
///
/// This is the canonical wrap-out helper: child accessors (`children`, `child_<lbl>`, etc.)
/// call this to ensure every wrap-out of the same `Shared` returns the same Python handle.
///
/// `make_handle` must not hold any node read/write lock when called — lock discipline.
pub fn get_or_insert_with(
    py: Python<'_>,
    arc_addr: usize,
    make_handle: impl FnOnce() -> PyResult<Py<PyAny>>,
) -> PyResult<Py<PyAny>> {
    if let Some(existing) = lookup(py, arc_addr)? {
        return Ok(existing);
    }
    let handle = make_handle()?;
    // Register; if another thread raced us, `register_if_absent` returns false and
    // we look up again to get the winner.  (Single-threaded Python: this never races.)
    let registered = register_if_absent(py, arc_addr, handle.bind(py))?;
    if registered {
        Ok(handle)
    } else {
        // Race (single-threaded Python: unreachable in practice).
        // If somehow reached, the winner's entry must still be live — return it or error.
        lookup(py, arc_addr)?.ok_or_else(|| {
            pyo3::exceptions::PyRuntimeError::new_err(
                "registry invariant violated: entry evicted immediately after register_if_absent returned false"
            )
        })
    }
}

/// Build a `PyDict` snapshot of the registry for testing/debugging.
///
/// Returns a plain `dict` copy of the `WeakValueDictionary`'s current live entries.
/// Only compiled under `cfg(test)` or the `test-introspection` feature; never enabled
/// in production builds.
///
/// Uses `.items()` rather than the `dict(mapping)` constructor to avoid a TOCTOU
/// race: `dict(WeakValueDictionary)` does `keys()` then `__getitem__` per key, and
/// `__getitem__` raises `KeyError` if the weak value died between the two steps
/// (e.g. if an allocation inside the copy triggers cyclic GC).  `WeakValueDictionary
/// .items()` dereferences each weakref and skips dead entries atomically per entry.
#[cfg(any(test, feature = "test-introspection"))]
pub fn snapshot(py: Python<'_>) -> PyResult<Bound<'_, PyDict>> {
    let registry = get_registry(py)?;
    let dict_class = py.import("builtins")?.getattr("dict")?;
    let items = registry.call_method0("items")?;
    let d = dict_class.call1((items,))?;
    d.cast_into::<PyDict>().map_err(|e| e.into())
}
