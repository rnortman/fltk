use fltk_cst_core::Span;
use fltk_cst_core::Shared;
#[cfg(feature = "python")]
use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};
#[cfg(feature = "python")]
use fltk_cst_core::registry;
#[cfg(feature = "python")]
use pyo3::exceptions::{PyTypeError, PyValueError};
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::{PyList, PyTuple, PyType};
#[cfg(feature = "python")]
use pyo3::PyTypeInfo;


// ───────────────────────────────────────────────────────────────────────────
// NodeKind
// ───────────────────────────────────────────────────────────────────────────

#[cfg(feature = "python")]
#[pyclass(frozen, name = "NodeKind")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum NodeKind {
    #[pyo3(name = "CONFIG")]
    Config,
    #[pyo3(name = "ENTRY")]
    Entry,
    #[pyo3(name = "OPERATOR")]
    Operator,
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "LITERAL")]
    Literal,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Config,
    Entry,
    Operator,
    Identifier,
    Literal,
    Trivia,
}

#[cfg(feature = "python")]
#[pymethods]
impl NodeKind {
    fn __repr__(&self) -> &'static str {
        match self {
            NodeKind::Config => "NodeKind.CONFIG",
            NodeKind::Entry => "NodeKind.ENTRY",
            NodeKind::Operator => "NodeKind.OPERATOR",
            NodeKind::Identifier => "NodeKind.IDENTIFIER",
            NodeKind::Literal => "NodeKind.LITERAL",
            NodeKind::Trivia => "NodeKind.TRIVIA",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<NodeKind>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Config_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Config_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Config_Label {
    #[pyo3(name = "ENTRY")]
    Entry,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Config_Label {
    Entry,
}

#[cfg(feature = "python")]
#[pymethods]
impl Config_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Config_Label::Entry => "Config.Label.ENTRY",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Config_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// ConfigChild — child value enum for Config
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum ConfigChild {
    Entry(Shared<Entry>),
}

impl PartialEq for ConfigChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ConfigChild::Entry(a), ConfigChild::Entry(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl ConfigChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Entry(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyEntry { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<PyEntry>() {
            let handle: PyRef<PyEntry> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Entry(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Config: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Config
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Config`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Config {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Config_Label>, ConfigChild)>,
}

impl PartialEq for Config {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Config {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Config {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Config_Label>, ConfigChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Config_Label>, child: ConfigChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Config")]
pub struct PyConfig {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Config>,
}

#[cfg(feature = "python")]
impl PyConfig {
    /// Return a reference to the inner `Shared<Config>`.
    pub fn shared(&self) -> &Shared<Config> {
        &self.inner
    }

    /// Wrap a `Shared<Config>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Config>) -> PyResult<Py<PyConfig>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyConfig { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyConfig>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyConfig {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyConfig>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Config {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyConfig { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Config
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Config_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Config_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Config.append: label argument is not a Config_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Config_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Config.extend: label argument is not a Config_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ConfigChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyConfig) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_entry(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Config_Label::Entry), native_child));
        Ok(())
    }

    fn extend_entry(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ConfigChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Config_Label::Entry), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_entry(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Config_Label::Entry) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_entry(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Config_Label::Entry) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one entry child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Config.child_entry: count==1 but found==None; logic error"))
    }

    fn maybe_entry(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Config_Label::Entry) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one entry child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyConfig>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyConfig> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Config'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Config(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Entry_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Entry_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Entry_Label {
    #[pyo3(name = "KEY")]
    Key,
    #[pyo3(name = "OP")]
    Op,
    #[pyo3(name = "VALUE")]
    Value,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Entry_Label {
    Key,
    Op,
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl Entry_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Entry_Label::Key => "Entry.Label.KEY",
            Entry_Label::Op => "Entry.Label.OP",
            Entry_Label::Value => "Entry.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Entry_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// EntryChild — child value enum for Entry
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum EntryChild {
    Identifier(Shared<Identifier>),
    Literal(Shared<Literal>),
    Operator(Shared<Operator>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for EntryChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (EntryChild::Identifier(a), EntryChild::Identifier(b)) => a == b,
            (EntryChild::Literal(a), EntryChild::Literal(b)) => a == b,
            (EntryChild::Operator(a), EntryChild::Operator(b)) => a == b,
            (EntryChild::Trivia(a), EntryChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

#[cfg(feature = "python")]
impl EntryChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Identifier(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyIdentifier { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Literal(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyLiteral { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Operator(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyOperator { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Trivia(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyTrivia { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<PyIdentifier>() {
            let handle: PyRef<PyIdentifier> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Identifier(shared));
        }
        if obj.is_instance_of::<PyLiteral>() {
            let handle: PyRef<PyLiteral> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Literal(shared));
        }
        if obj.is_instance_of::<PyOperator>() {
            let handle: PyRef<PyOperator> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Operator(shared));
        }
        if obj.is_instance_of::<PyTrivia>() {
            let handle: PyRef<PyTrivia> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Trivia(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Entry: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Entry
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Entry`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Entry {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Entry_Label>, EntryChild)>,
}

impl PartialEq for Entry {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Entry {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Entry {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Entry_Label>, EntryChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Entry_Label>, child: EntryChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Entry")]
pub struct PyEntry {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Entry>,
}

#[cfg(feature = "python")]
impl PyEntry {
    /// Return a reference to the inner `Shared<Entry>`.
    pub fn shared(&self) -> &Shared<Entry> {
        &self.inner
    }

    /// Wrap a `Shared<Entry>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Entry>) -> PyResult<Py<PyEntry>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyEntry { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyEntry>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyEntry {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyEntry>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Entry {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyEntry { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Entry
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Entry_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Entry_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Entry.append: label argument is not a Entry_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Entry_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Entry.extend: label argument is not a Entry_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyEntry) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_key(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Entry_Label::Key), native_child));
        Ok(())
    }

    fn extend_key(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Entry_Label::Key), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_key(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Key) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_key(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Key) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one key child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_key: count==1 but found==None; logic error"))
    }

    fn maybe_key(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Key) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one key child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_op(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Entry_Label::Op), native_child));
        Ok(())
    }

    fn extend_op(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Entry_Label::Op), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_op(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Op) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_op(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Op) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one op child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_op: count==1 but found==None; logic error"))
    }

    fn maybe_op(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Op) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one op child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Entry_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Entry_Label::Value), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Value) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one value child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Entry_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one value child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyEntry>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyEntry> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Entry'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Entry(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Operator_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Operator_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Operator_Label {
    #[pyo3(name = "APPEND")]
    Append,
    #[pyo3(name = "ASSIGN")]
    Assign,
    #[pyo3(name = "REMOVE")]
    Remove,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Operator_Label {
    Append,
    Assign,
    Remove,
}

#[cfg(feature = "python")]
#[pymethods]
impl Operator_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Operator_Label::Append => "Operator.Label.APPEND",
            Operator_Label::Assign => "Operator.Label.ASSIGN",
            Operator_Label::Remove => "Operator.Label.REMOVE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Operator_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// OperatorChild — child value enum for Operator
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum OperatorChild {
    Span(Span),
}

impl PartialEq for OperatorChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (OperatorChild::Span(a), OperatorChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl OperatorChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        // Try Span (terminal child) first — handles cross-cdylib span instances.
        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {
            return extract_span(py, obj).map(Self::Span);
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Operator: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Operator
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Operator`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Operator {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Operator_Label>, OperatorChild)>,
}

impl PartialEq for Operator {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Operator {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Operator {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Operator_Label>, OperatorChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Operator_Label>, child: OperatorChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Operator")]
pub struct PyOperator {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Operator>,
}

#[cfg(feature = "python")]
impl PyOperator {
    /// Return a reference to the inner `Shared<Operator>`.
    pub fn shared(&self) -> &Shared<Operator> {
        &self.inner
    }

    /// Wrap a `Shared<Operator>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Operator>) -> PyResult<Py<PyOperator>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyOperator { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyOperator>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyOperator {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyOperator>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Operator {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyOperator { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Operator
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Operator_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Operator_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Operator.append: label argument is not a Operator_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Operator_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Operator.extend: label argument is not a Operator_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyOperator) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_append(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Operator_Label::Append), native_child));
        Ok(())
    }

    fn extend_append(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Operator_Label::Append), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_append(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Append) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_append(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Append) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one append child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_append: count==1 but found==None; logic error"))
    }

    fn maybe_append(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Append) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one append child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_assign(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Operator_Label::Assign), native_child));
        Ok(())
    }

    fn extend_assign(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Operator_Label::Assign), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_assign(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Assign) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_assign(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Assign) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one assign child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_assign: count==1 but found==None; logic error"))
    }

    fn maybe_assign(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Assign) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one assign child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_remove(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Operator_Label::Remove), native_child));
        Ok(())
    }

    fn extend_remove(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Operator_Label::Remove), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_remove(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Remove) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_remove(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Remove) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one remove child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_remove: count==1 but found==None; logic error"))
    }

    fn maybe_remove(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Operator_Label::Remove) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one remove child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyOperator>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyOperator> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Operator'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Operator(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Identifier_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Identifier_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Identifier_Label {
    #[pyo3(name = "NAME")]
    Name,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Identifier_Label {
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl Identifier_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Identifier_Label::Name => "Identifier.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Identifier_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// IdentifierChild — child value enum for Identifier
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum IdentifierChild {
    Span(Span),
}

impl PartialEq for IdentifierChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (IdentifierChild::Span(a), IdentifierChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl IdentifierChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        // Try Span (terminal child) first — handles cross-cdylib span instances.
        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {
            return extract_span(py, obj).map(Self::Span);
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Identifier: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Identifier
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Identifier`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Identifier {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Identifier_Label>, IdentifierChild)>,
}

impl PartialEq for Identifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Identifier {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Identifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Identifier_Label>, IdentifierChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Identifier_Label>, child: IdentifierChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Identifier")]
pub struct PyIdentifier {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Identifier>,
}

#[cfg(feature = "python")]
impl PyIdentifier {
    /// Return a reference to the inner `Shared<Identifier>`.
    pub fn shared(&self) -> &Shared<Identifier> {
        &self.inner
    }

    /// Wrap a `Shared<Identifier>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Identifier>) -> PyResult<Py<PyIdentifier>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyIdentifier { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyIdentifier>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyIdentifier {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyIdentifier>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Identifier {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyIdentifier { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Identifier
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Identifier_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = IdentifierChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Identifier_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Identifier.append: label argument is not a Identifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Identifier_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Identifier.extend: label argument is not a Identifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = IdentifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyIdentifier) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_name(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = IdentifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Identifier_Label::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = IdentifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Identifier_Label::Name), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Identifier_Label::Name) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Identifier_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one name child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Identifier.child_name: count==1 but found==None; logic error"))
    }

    fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Identifier_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one name child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyIdentifier>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyIdentifier> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Identifier'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Identifier(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Literal_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Literal_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    #[pyo3(name = "INT_VAL")]
    IntVal,
    #[pyo3(name = "STR_VAL")]
    StrVal,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    IntVal,
    StrVal,
}

#[cfg(feature = "python")]
#[pymethods]
impl Literal_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Literal_Label::IntVal => "Literal.Label.INT_VAL",
            Literal_Label::StrVal => "Literal.Label.STR_VAL",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Literal_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// LiteralChild — child value enum for Literal
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum LiteralChild {
    Span(Span),
}

impl PartialEq for LiteralChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (LiteralChild::Span(a), LiteralChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl LiteralChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        // Try Span (terminal child) first — handles cross-cdylib span instances.
        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {
            return extract_span(py, obj).map(Self::Span);
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Literal: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Literal
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Literal`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Literal {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Literal_Label>, LiteralChild)>,
}

impl PartialEq for Literal {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Literal {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Literal {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Literal_Label>, LiteralChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Literal_Label>, child: LiteralChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Literal")]
pub struct PyLiteral {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Literal>,
}

#[cfg(feature = "python")]
impl PyLiteral {
    /// Return a reference to the inner `Shared<Literal>`.
    pub fn shared(&self) -> &Shared<Literal> {
        &self.inner
    }

    /// Wrap a `Shared<Literal>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Literal>) -> PyResult<Py<PyLiteral>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyLiteral { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyLiteral>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyLiteral {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyLiteral>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Literal {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyLiteral { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Literal
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Literal_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Literal_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Literal.append: label argument is not a Literal_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Literal_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Literal.extend: label argument is not a Literal_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyLiteral) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_int_val(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Literal_Label::IntVal), native_child));
        Ok(())
    }

    fn extend_int_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Literal_Label::IntVal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_int_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::IntVal) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_int_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::IntVal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one int_val child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Literal.child_int_val: count==1 but found==None; logic error"))
    }

    fn maybe_int_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::IntVal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one int_val child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_str_val(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Literal_Label::StrVal), native_child));
        Ok(())
    }

    fn extend_str_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Literal_Label::StrVal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_str_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::StrVal) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_str_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::StrVal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one str_val child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Literal.child_str_val: count==1 but found==None; logic error"))
    }

    fn maybe_str_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::StrVal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one str_val child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyLiteral>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyLiteral> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Literal'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Literal(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Trivia_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Trivia_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Trivia_Label {
    #[pyo3(name = "CONTENT")]
    Content,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Trivia_Label {
    Content,
}

#[cfg(feature = "python")]
#[pymethods]
impl Trivia_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Trivia_Label::Content => "Trivia.Label.CONTENT",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Trivia_Label>() {
            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());
        }
        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {
            if let Ok(cn_str) = cn.extract::<&str>() {
                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());
            }
        }
        Ok(py.NotImplemented())
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        pyo3::types::PyAnyMethods::hash(
            pyo3::types::PyString::new(py, self.__repr__()).as_any()
        )
    }
}

// TriviaChild — child value enum for Trivia
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
pub enum TriviaChild {
    Span(Span),
}

impl PartialEq for TriviaChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (TriviaChild::Span(a), TriviaChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl TriviaChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
        }
    }

    fn extract_from_pyobject(
        py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        // Try Span (terminal child) first — handles cross-cdylib span instances.
        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {
            return extract_span(py, obj).map(Self::Span);
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Trivia: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Trivia
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Trivia`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Trivia {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Trivia_Label>, TriviaChild)>,
}

impl PartialEq for Trivia {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Trivia {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Trivia {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Trivia_Label>, TriviaChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Trivia_Label>, child: TriviaChild) {
        self.children.push((label, child));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Trivia")]
pub struct PyTrivia {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Trivia>,
}

#[cfg(feature = "python")]
impl PyTrivia {
    /// Return a reference to the inner `Shared<Trivia>`.
    pub fn shared(&self) -> &Shared<Trivia> {
        &self.inner
    }

    /// Wrap a `Shared<Trivia>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Trivia>) -> PyResult<Py<PyTrivia>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyTrivia { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyTrivia>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyTrivia {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyTrivia>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Trivia {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyTrivia { inner: shared };
        let py_obj = Py::new(py, handle)?;
        // Register as canonical — fresh Shared, no alias can exist yet.
        registry::force_register(py, addr, py_obj.bind(py))?;
        Ok(py_obj)
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Snapshot the span under the read lock, then drop the guard before
        // calling span_to_pyobject — which performs Python work (Py::new or
        // Python method calls) that must not happen while a node lock is held.
        let span = self.inner.read().span.clone();
        span_to_pyobject(py, &span)
    }

    #[setter]
    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.inner.write().span = extract_span(py, value)?;
        Ok(())
    }

    #[getter]
    fn kind(&self) -> NodeKind {
        NodeKind::Trivia
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Trivia_Label::type_object(py).into_any().unbind())
    }

    #[getter]
    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).
        // Lock scope: acquire read, snapshot, release before touching Python.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (label, child) in &snapshot {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Trivia_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Trivia.append: label argument is not a Trivia_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        self.inner.write().children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<Trivia_Label>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Trivia.extend: label argument is not a Trivia_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyTrivia) -> PyResult<()> {
        // Snapshot other's children first: the read guard is dropped at the end of
        // this block, so the write lock below is safe even when self and other are
        // the same node (self-extend). No ptr_eq call is needed here — the snapshot
        // approach handles self-extend structurally.
        // Lock scope: hold read only long enough to clone the Arc-based children vec.
        let snapshot: Vec<_> = {
            let guard = other.inner.read();
            guard.children.clone()
        };
        // Node-typed children are pushed directly as Shared<T> values.  Registry
        // consistency is maintained lazily: wrap-out registers on first Python read
        // via get_or_insert_with (registry.rs).  Eagerly registering here would be
        // a no-op — the WeakValueDictionary would evict handles held by nothing.
        self.inner.write().children.extend(snapshot);
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let n = snapshot.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let (label, child) = &snapshot[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_content(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Trivia_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Trivia_Label::Content), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::Content) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one content child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Trivia.child_content: count==1 but found==None; logic error"))
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one content child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyTrivia>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyTrivia> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Trivia'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Trivia(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

#[cfg(feature = "python")]
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<Config_Label>()?;
    module.add_class::<PyConfig>()?;
    module.add_class::<Entry_Label>()?;
    module.add_class::<PyEntry>()?;
    module.add_class::<Operator_Label>()?;
    module.add_class::<PyOperator>()?;
    module.add_class::<Identifier_Label>()?;
    module.add_class::<PyIdentifier>()?;
    module.add_class::<Literal_Label>()?;
    module.add_class::<PyLiteral>()?;
    module.add_class::<Trivia_Label>()?;
    module.add_class::<PyTrivia>()?;
    Ok(())
}
