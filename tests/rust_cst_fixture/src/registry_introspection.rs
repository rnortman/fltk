// Python-callable wrappers around the fltk-cst-core registry introspection API.
//
// These functions are test-only plumbing: they expose the fixture crate's own
// CANONICAL_REGISTRY static to Python.  They must live in this crate (not in
// fltk._native) because each cdylib statically links its own fltk-cst-core and
// therefore has its own CANONICAL_REGISTRY instance.  Wrappers in fltk._native
// would observe a different registry and miss entries created by the fixture.
//
// Synthetic-address callers (TestDirectRegistrySemantics) use small integers far
// below any heap Arc address.  The addr/handle pairing contract in force_register
// (registry.rs:87-91) is not violated: no generated accessor ever looks up a
// synthetic address, so corrupt typed-accessor returns are impossible.
use fltk_cst_core::registry;
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Return a plain `dict` snapshot of the registry: {int Arc-address → handle (strong ref)}.
///
/// The returned dict holds strong references; callers must `del` the snapshot before
/// any `gc.collect()` / eviction check, or the snapshot will prevent eviction.
#[pyfunction]
pub fn _registry_snapshot(py: Python<'_>) -> PyResult<Bound<'_, PyDict>> {
    registry::snapshot(py)
}

/// Look up the canonical handle for `addr`.  Returns the handle or `None` if absent/evicted.
#[pyfunction]
pub fn _registry_lookup(py: Python<'_>, addr: usize) -> PyResult<Option<Py<PyAny>>> {
    registry::lookup(py, addr)
}

/// Register `obj` as the canonical handle for `addr` if no live entry exists.
///
/// Returns `True` if `obj` was newly registered, `False` if a live entry already existed
/// (in which case `obj` was not installed).
///
/// Synthetic-address callers: use a counter starting at 1 to generate addresses that
/// cannot collide with real Arc addresses.  Weak eviction cleans them up when test
/// objects die regardless.
#[pyfunction]
pub fn _registry_register_if_absent(py: Python<'_>, addr: usize, obj: &Bound<'_, PyAny>) -> PyResult<bool> {
    registry::register_if_absent(py, addr, obj)
}

/// Force-set `obj` as the canonical handle for `addr`, overwriting any previous entry.
///
/// Synthetic-address callers: use a counter starting at 1 to generate addresses that
/// cannot collide with real Arc addresses.  Weak eviction cleans them up when test
/// objects die regardless.
#[pyfunction]
pub fn _registry_force_register(py: Python<'_>, addr: usize, obj: &Bound<'_, PyAny>) -> PyResult<()> {
    registry::force_register(py, addr, obj)
}
