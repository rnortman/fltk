use fltk_cst_core::CstError;
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

/// Discriminant enum identifying the concrete node type of a CST node.
///
/// One variant per grammar rule. Returned by `kind()` on every data struct
/// and handle. Python-visible name is the same ALL_CAPS form as the protocol.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "NodeKind")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "ITEMS")]
    Items,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Identifier,
    Items,
    Trivia,
}

#[cfg(feature = "python")]
#[pymethods]
impl NodeKind {
    fn __repr__(&self) -> &'static str {
        match self {
            NodeKind::Identifier => "NodeKind.IDENTIFIER",
            NodeKind::Items => "NodeKind.ITEMS",
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
// IdentifierLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Identifier_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `IdentifierLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Identifier_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum IdentifierLabel {
    #[pyo3(name = "NAME")]
    Name,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum IdentifierLabel {
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl IdentifierLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            IdentifierLabel::Name => "Identifier.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<IdentifierLabel>() {
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

/// Child value enum for `Identifier` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

/// CST data struct for `Identifier`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone, Debug)]
pub struct Identifier {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<IdentifierLabel>, IdentifierChild)>,
}

impl PartialEq for Identifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Identifier {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Identifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Identifier
    }

    /// Return a reference to the stored [`Span`].
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Return a slice of all children (unfiltered).
    ///
    /// Each entry is `(label, child)`. Use the per-label accessors
    /// (`children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`) for type-safe access.
    pub fn children(&self) -> &[(Option<IdentifierLabel>, IdentifierChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<IdentifierLabel>, child: IdentifierChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<IdentifierLabel>, IdentifierChild), CstError> {
        match self.children.as_slice() {
            [single] => Ok(single),
            slice => Err(CstError::ChildCount {
                label: "<any>",
                expected: "1",
                found: slice.len(),
            }),
        }
    }

    /// Copy all children from `other` into `self`, sharing the `Shared<T>` arcs.
    ///
    /// Children are appended (Arc reference-count bumps, not deep copies),
    /// matching the Python backend's reference-copy behavior. Labels are preserved.
    ///
    /// The borrow checker prevents `self.extend_children(self)` at the data-struct
    /// level (`&mut` + `&` of the same value don't coexist). For self-extend from
    /// Python, the handle pymethod handles it via snapshotting.
    pub fn extend_children(&mut self, other: &Self) {
        self.children.extend(other.children.iter().cloned());
    }

    /// Return an iterator over `Span` children labelled `name`.
    ///
    /// Off-type variants stored under the `name` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_name(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name))
            .map(|(_, child)| match child { IdentifierChild::Span(s) => s })
    }

    /// Return the single child labelled `name`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_name(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                IdentifierChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `name`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_name(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                IdentifierChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `name`.
    pub fn append_name(&mut self, span: Span) {
        self.children.push((Some(IdentifierLabel::Name), IdentifierChild::Span(span)));
    }

    /// Append multiple `Span` children with label `name`.
    pub fn extend_name(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(IdentifierLabel::Name), IdentifierChild::Span(s))));
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
        Ok(IdentifierLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<IdentifierLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<IdentifierLabel>() {
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
        // TODO(rust-cst-accessor-clone-efficiency): clones the full children Vec
        // before checking len. Could check len under the read guard and only clone
        // the single needed entry, avoiding O(total-children) allocation on the error path.
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
        self.inner.write().children.push((Some(IdentifierLabel::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = IdentifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(IdentifierLabel::Name), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(IdentifierLabel::Name) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_name above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(IdentifierLabel::Name) {
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
        // TODO(rust-cst-accessor-clone-efficiency): see children_name above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(IdentifierLabel::Name) {
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
// ItemsLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Items_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ItemsLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Items_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemsLabel {
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "NO_WS")]
    NoWs,
    #[pyo3(name = "WS_ALLOWED")]
    WsAllowed,
    #[pyo3(name = "WS_REQUIRED")]
    WsRequired,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemsLabel {
    Item,
    NoWs,
    WsAllowed,
    WsRequired,
}

#[cfg(feature = "python")]
#[pymethods]
impl ItemsLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ItemsLabel::Item => "Items.Label.ITEM",
            ItemsLabel::NoWs => "Items.Label.NO_WS",
            ItemsLabel::WsAllowed => "Items.Label.WS_ALLOWED",
            ItemsLabel::WsRequired => "Items.Label.WS_REQUIRED",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ItemsLabel>() {
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

/// Child value enum for `Items` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ItemsChild {
    Span(Span),
    Identifier(Shared<Identifier>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for ItemsChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ItemsChild::Span(a), ItemsChild::Span(b)) => a == b,
            (ItemsChild::Identifier(a), ItemsChild::Identifier(b)) => a == b,
            (ItemsChild::Trivia(a), ItemsChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

#[cfg(feature = "python")]
impl ItemsChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
            Self::Identifier(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyIdentifier { inner: shared.clone() };
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
        span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        // Try Span (terminal child) first — handles cross-cdylib span instances.
        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {
            return extract_span(py, obj).map(Self::Span);
        }
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
            "Items: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Items
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Items`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone, Debug)]
pub struct Items {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ItemsLabel>, ItemsChild)>,
}

impl PartialEq for Items {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Items {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Items {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Items
    }

    /// Return a reference to the stored [`Span`].
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Return a slice of all children (unfiltered).
    ///
    /// Each entry is `(label, child)`. Use the per-label accessors
    /// (`children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`) for type-safe access.
    pub fn children(&self) -> &[(Option<ItemsLabel>, ItemsChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ItemsLabel>, child: ItemsChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ItemsLabel>, ItemsChild), CstError> {
        match self.children.as_slice() {
            [single] => Ok(single),
            slice => Err(CstError::ChildCount {
                label: "<any>",
                expected: "1",
                found: slice.len(),
            }),
        }
    }

    /// Copy all children from `other` into `self`, sharing the `Shared<T>` arcs.
    ///
    /// Children are appended (Arc reference-count bumps, not deep copies),
    /// matching the Python backend's reference-copy behavior. Labels are preserved.
    ///
    /// The borrow checker prevents `self.extend_children(self)` at the data-struct
    /// level (`&mut` + `&` of the same value don't coexist). For self-extend from
    /// Python, the handle pymethod handles it via snapshotting.
    pub fn extend_children(&mut self, other: &Self) {
        self.children.extend(other.children.iter().cloned());
    }

    /// Return an iterator over `Shared<Identifier>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Identifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
            .filter_map(|(_, child)| match child {
                ItemsChild::Identifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Identifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Identifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "item" }),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `item`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_item(&self) -> Result<Option<&Shared<Identifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Identifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "item" }),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
                    .count(),
            }),
        }
    }

    /// Append a child with label `item`, accepting `Identifier` or `Shared<Identifier>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Identifier>>) {
        self.children.push((Some(ItemsLabel::Item), ItemsChild::Identifier(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Identifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemsLabel::Item), ItemsChild::Identifier(c.into()))));
    }

    /// Return an iterator over `Span` children labelled `no_ws`.
    ///
    /// Off-type variants stored under the `no_ws` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_no_ws(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs))
            .filter_map(|(_, child)| match child {
                ItemsChild::Span(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `no_ws`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_no_ws(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "no_ws" }),
            },
            _ => Err(CstError::ChildCount {
                label: "no_ws",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `no_ws`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_no_ws(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "no_ws" }),
            },
            _ => Err(CstError::ChildCount {
                label: "no_ws",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `no_ws`.
    pub fn append_no_ws(&mut self, span: Span) {
        self.children.push((Some(ItemsLabel::NoWs), ItemsChild::Span(span)));
    }

    /// Append multiple `Span` children with label `no_ws`.
    pub fn extend_no_ws(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(ItemsLabel::NoWs), ItemsChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `ws_allowed`.
    ///
    /// Off-type variants stored under the `ws_allowed` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_ws_allowed(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed))
            .filter_map(|(_, child)| match child {
                ItemsChild::Span(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `ws_allowed`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_ws_allowed(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "ws_allowed" }),
            },
            _ => Err(CstError::ChildCount {
                label: "ws_allowed",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `ws_allowed`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_ws_allowed(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "ws_allowed" }),
            },
            _ => Err(CstError::ChildCount {
                label: "ws_allowed",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `ws_allowed`.
    pub fn append_ws_allowed(&mut self, span: Span) {
        self.children.push((Some(ItemsLabel::WsAllowed), ItemsChild::Span(span)));
    }

    /// Append multiple `Span` children with label `ws_allowed`.
    pub fn extend_ws_allowed(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(ItemsLabel::WsAllowed), ItemsChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `ws_required`.
    ///
    /// Off-type variants stored under the `ws_required` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_ws_required(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired))
            .filter_map(|(_, child)| match child {
                ItemsChild::Span(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `ws_required`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_ws_required(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "ws_required" }),
            },
            _ => Err(CstError::ChildCount {
                label: "ws_required",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `ws_required`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_ws_required(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Span(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "ws_required" }),
            },
            _ => Err(CstError::ChildCount {
                label: "ws_required",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `ws_required`.
    pub fn append_ws_required(&mut self, span: Span) {
        self.children.push((Some(ItemsLabel::WsRequired), ItemsChild::Span(span)));
    }

    /// Append multiple `Span` children with label `ws_required`.
    pub fn extend_ws_required(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(ItemsLabel::WsRequired), ItemsChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Items")]
pub struct PyItems {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Items>,
}

#[cfg(feature = "python")]
impl PyItems {
    /// Return a reference to the inner `Shared<Items>`.
    pub fn shared(&self) -> &Shared<Items> {
        &self.inner
    }

    /// Wrap a `Shared<Items>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Items>) -> PyResult<Py<PyItems>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyItems { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyItems>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyItems {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyItems>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Items {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyItems { inner: shared };
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
        NodeKind::Items
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ItemsLabel::type_object(py).into_any().unbind())
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
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ItemsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Items.append: label argument is not a Items_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ItemsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Items.extend: label argument is not a Items_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyItems) -> PyResult<()> {
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
        // TODO(rust-cst-accessor-clone-efficiency): clones the full children Vec
        // before checking len. Could check len under the read guard and only clone
        // the single needed entry, avoiding O(total-children) allocation on the error path.
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

    fn append_item(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemsLabel::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemsLabel::Item), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_item(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::Item) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_item above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::Item) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one item child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Items.child_item: count==1 but found==None; logic error"))
    }

    fn maybe_item(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_item above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::Item) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one item child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_no_ws(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemsLabel::NoWs), native_child));
        Ok(())
    }

    fn extend_no_ws(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemsLabel::NoWs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_no_ws(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::NoWs) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_no_ws above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::NoWs) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one no_ws child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Items.child_no_ws: count==1 but found==None; logic error"))
    }

    fn maybe_no_ws(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_no_ws above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::NoWs) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one no_ws child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_ws_allowed(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemsLabel::WsAllowed), native_child));
        Ok(())
    }

    fn extend_ws_allowed(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemsLabel::WsAllowed), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_ws_allowed(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsAllowed) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_ws_allowed above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsAllowed) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one ws_allowed child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Items.child_ws_allowed: count==1 but found==None; logic error"))
    }

    fn maybe_ws_allowed(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_ws_allowed above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsAllowed) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one ws_allowed child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_ws_required(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemsLabel::WsRequired), native_child));
        Ok(())
    }

    fn extend_ws_required(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemsLabel::WsRequired), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_ws_required(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsRequired) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_ws_required above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsRequired) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one ws_required child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Items.child_ws_required: count==1 but found==None; logic error"))
    }

    fn maybe_ws_required(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_ws_required above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(ItemsLabel::WsRequired) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one ws_required child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyItems>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyItems> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Items'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Items(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// TriviaLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Trivia_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `TriviaLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Trivia_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TriviaLabel {
    #[pyo3(name = "CONTENT")]
    Content,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TriviaLabel {
    Content,
}

#[cfg(feature = "python")]
#[pymethods]
impl TriviaLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            TriviaLabel::Content => "Trivia.Label.CONTENT",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<TriviaLabel>() {
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

/// Child value enum for `Trivia` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

/// CST data struct for `Trivia`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone, Debug)]
pub struct Trivia {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<TriviaLabel>, TriviaChild)>,
}

impl PartialEq for Trivia {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Trivia {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Trivia {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Trivia
    }

    /// Return a reference to the stored [`Span`].
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Return a slice of all children (unfiltered).
    ///
    /// Each entry is `(label, child)`. Use the per-label accessors
    /// (`children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`) for type-safe access.
    pub fn children(&self) -> &[(Option<TriviaLabel>, TriviaChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<TriviaLabel>, child: TriviaChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<TriviaLabel>, TriviaChild), CstError> {
        match self.children.as_slice() {
            [single] => Ok(single),
            slice => Err(CstError::ChildCount {
                label: "<any>",
                expected: "1",
                found: slice.len(),
            }),
        }
    }

    /// Copy all children from `other` into `self`, sharing the `Shared<T>` arcs.
    ///
    /// Children are appended (Arc reference-count bumps, not deep copies),
    /// matching the Python backend's reference-copy behavior. Labels are preserved.
    ///
    /// The borrow checker prevents `self.extend_children(self)` at the data-struct
    /// level (`&mut` + `&` of the same value don't coexist). For self-extend from
    /// Python, the handle pymethod handles it via snapshotting.
    pub fn extend_children(&mut self, other: &Self) {
        self.children.extend(other.children.iter().cloned());
    }

    /// Return an iterator over `Span` children labelled `content`.
    ///
    /// Off-type variants stored under the `content` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_content(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content))
            .map(|(_, child)| match child { TriviaChild::Span(s) => s })
    }

    /// Return the single child labelled `content`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_content(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TriviaChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `content`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_content(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TriviaChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `content`.
    pub fn append_content(&mut self, span: Span) {
        self.children.push((Some(TriviaLabel::Content), TriviaChild::Span(span)));
    }

    /// Append multiple `Span` children with label `content`.
    pub fn extend_content(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(TriviaLabel::Content), TriviaChild::Span(s))));
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
        Ok(TriviaLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<TriviaLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<TriviaLabel>() {
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
        // TODO(rust-cst-accessor-clone-efficiency): clones the full children Vec
        // before checking len. Could check len under the read guard and only clone
        // the single needed entry, avoiding O(total-children) allocation on the error path.
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
        self.inner.write().children.push((Some(TriviaLabel::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TriviaLabel::Content), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.
        // Could filter inside the read guard (clone only matching entries) to avoid
        // O(total-children) Arc clones for accessors that match a small subset.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(TriviaLabel::Content) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        // TODO(rust-cst-accessor-clone-efficiency): see children_content above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(TriviaLabel::Content) {
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
        // TODO(rust-cst-accessor-clone-efficiency): see children_content above.
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(TriviaLabel::Content) {
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
    module.add_class::<IdentifierLabel>()?;
    module.add_class::<PyIdentifier>()?;
    module.add_class::<ItemsLabel>()?;
    module.add_class::<PyItems>()?;
    module.add_class::<TriviaLabel>()?;
    module.add_class::<PyTrivia>()?;
    Ok(())
}
