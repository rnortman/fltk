use fltk_cst_core::CstError;
use fltk_cst_core::Span;
use fltk_cst_core::Shared;
use std::fmt;
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
    #[pyo3(name = "ROOT")]
    Root,
    #[pyo3(name = "NAME")]
    Name,
    #[pyo3(name = "PARSER")]
    Parser,
    #[pyo3(name = "APPLYRESULT")]
    ApplyResult,
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Root,
    Name,
    Parser,
    ApplyResult,
    Item,
    Trivia,
}

#[cfg(feature = "python")]
#[pymethods]
impl NodeKind {
    fn __repr__(&self) -> &'static str {
        match self {
            NodeKind::Root => "NodeKind.ROOT",
            NodeKind::Name => "NodeKind.NAME",
            NodeKind::Parser => "NodeKind.PARSER",
            NodeKind::ApplyResult => "NodeKind.APPLYRESULT",
            NodeKind::Item => "NodeKind.ITEM",
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
// RootLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Root_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `RootLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Root_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RootLabel {
    #[pyo3(name = "ITEM")]
    Item,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RootLabel {
    Item,
}

#[cfg(feature = "python")]
#[pymethods]
impl RootLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            RootLabel::Item => "Root.Label.ITEM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RootLabel>() {
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

/// Child value enum for `Root` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum RootChild {
    Item(Shared<Item>),
}

impl PartialEq for RootChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (RootChild::Item(a), RootChild::Item(b)) => a == b,
        }
    }
}

impl RootChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Item(s) => Some(DropWorklistItem::Item(s)),
        }
    }
}

#[cfg(feature = "python")]
impl RootChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Item(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyItem { inner: shared.clone() };
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
        if obj.is_instance_of::<PyItem>() {
            let handle: PyRef<PyItem> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Item(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Root: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Root
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Root`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Root {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RootLabel>, RootChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Root {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Root")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Root {
    fn drop(&mut self) {
        if self.children.is_empty() {
            return; // also the recursion terminator for nodes drained by the worklist
        }
        // Worklist is allocated lazily: Vec::new() does not heap-allocate until
        // the first push.  drain_into pushes only when it steals (count == 1).
        // In the common backtracking case (shared/memoized children) no steal
        // occurs and no allocation happens.  Owned deep chains allocate once.
        let mut worklist: Vec<DropWorklistItem> = Vec::new();
        for (_, child) in self.children.drain(..) {
            if let Some(item) = child.into_drop_item() {
                item.drain_into(&mut worklist);
            }
        }
        while let Some(item) = worklist.pop() {
            item.drain_into(&mut worklist);
        }
    }
}

impl PartialEq for Root {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Root {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Root {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Root
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
    pub fn children(&self) -> &[(Option<RootLabel>, RootChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<RootLabel>, child: RootChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<RootLabel>, RootChild), CstError> {
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

    /// Return an iterator over `Shared<Item>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Item>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RootLabel::Item))
            .map(|(_, child)| match child { RootChild::Item(s) => s })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Item>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RootLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RootChild::Item(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RootLabel::Item))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `item`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_item(&self) -> Result<Option<&Shared<Item>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RootLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RootChild::Item(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RootLabel::Item))
                    .count(),
            }),
        }
    }

    /// Append a child with label `item`, accepting `Item` or `Shared<Item>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Item>>) {
        self.children.push((Some(RootLabel::Item), RootChild::Item(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Item>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RootLabel::Item), RootChild::Item(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Root")]
pub struct PyRoot {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Root>,
}

#[cfg(feature = "python")]
impl PyRoot {
    /// Return a reference to the inner `Shared<Root>`.
    pub fn shared(&self) -> &Shared<Root> {
        &self.inner
    }

    /// Wrap a `Shared<Root>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Root>) -> PyResult<Py<PyRoot>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyRoot { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyRoot>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyRoot {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyRoot>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Root {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyRoot { inner: shared };
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
        NodeKind::Root
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RootLabel::type_object(py).into_any().unbind())
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
        let native_child = RootChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<RootLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Root.append: label argument is not a Root_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RootLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Root.extend: label argument is not a Root_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RootChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyRoot) -> PyResult<()> {
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_item(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RootChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RootLabel::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RootChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RootLabel::Item), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_item(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RootLabel::Item))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RootLabel::Item) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one item child but have {count}"
            )));
        }
        first.expect("invariant: Root.child_item: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_item(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RootLabel::Item) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one item child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyRoot>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyRoot> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Root'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Root(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// NameLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Name_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `NameLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Name_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NameLabel {
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NameLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl NameLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            NameLabel::Value => "Name.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<NameLabel>() {
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

/// Child value enum for `Name` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum NameChild {
    Span(Span),
}

impl PartialEq for NameChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (NameChild::Span(a), NameChild::Span(b)) => a == b,
        }
    }
}

impl NameChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl NameChild {
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
            "Name: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Name
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Name`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Name {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<NameLabel>, NameChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Name {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Name")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Name {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Name {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Name {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Name
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
    pub fn children(&self) -> &[(Option<NameLabel>, NameChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<NameLabel>, child: NameChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<NameLabel>, NameChild), CstError> {
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

    /// Return an iterator over `Span` children labelled `value`.
    ///
    /// Off-type variants stored under the `value` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_value(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NameLabel::Value))
            .map(|(_, child)| match child { NameChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NameLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NameChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NameLabel::Value))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `value`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_value(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NameLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NameChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NameLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(NameLabel::Value), NameChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(NameLabel::Value), NameChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Name")]
pub struct PyName {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Name>,
}

#[cfg(feature = "python")]
impl PyName {
    /// Return a reference to the inner `Shared<Name>`.
    pub fn shared(&self) -> &Shared<Name> {
        &self.inner
    }

    /// Wrap a `Shared<Name>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Name>) -> PyResult<Py<PyName>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyName { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyName>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyName {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyName>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Name {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyName { inner: shared };
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
        NodeKind::Name
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(NameLabel::type_object(py).into_any().unbind())
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
        let native_child = NameChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<NameLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Name.append: label argument is not a Name_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<NameLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Name.extend: label argument is not a Name_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NameChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyName) -> PyResult<()> {
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NameChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NameLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NameChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NameLabel::Value), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NameLabel::Value))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NameLabel::Value) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one value child but have {count}"
            )));
        }
        first.expect("invariant: Name.child_value: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NameLabel::Value) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one value child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyName>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyName> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Name'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Name(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ParserLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Parser_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ParserLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Parser_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ParserLabel {
    #[pyo3(name = "NAME")]
    Name,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ParserLabel {
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl ParserLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ParserLabel::Name => "Parser.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ParserLabel>() {
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

/// Child value enum for `Parser` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ParserChild {
    Name(Shared<Name>),
}

impl PartialEq for ParserChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ParserChild::Name(a), ParserChild::Name(b)) => a == b,
        }
    }
}

impl ParserChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ParserChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
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
        if obj.is_instance_of::<PyName>() {
            let handle: PyRef<PyName> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Name(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Parser: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Parser
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Parser`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Parser {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ParserLabel>, ParserChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Parser {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Parser")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Parser {
    fn drop(&mut self) {
        if self.children.is_empty() {
            return; // also the recursion terminator for nodes drained by the worklist
        }
        // Worklist is allocated lazily: Vec::new() does not heap-allocate until
        // the first push.  drain_into pushes only when it steals (count == 1).
        // In the common backtracking case (shared/memoized children) no steal
        // occurs and no allocation happens.  Owned deep chains allocate once.
        let mut worklist: Vec<DropWorklistItem> = Vec::new();
        for (_, child) in self.children.drain(..) {
            if let Some(item) = child.into_drop_item() {
                item.drain_into(&mut worklist);
            }
        }
        while let Some(item) = worklist.pop() {
            item.drain_into(&mut worklist);
        }
    }
}

impl PartialEq for Parser {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Parser {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Parser {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Parser
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
    pub fn children(&self) -> &[(Option<ParserLabel>, ParserChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ParserLabel>, child: ParserChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ParserLabel>, ParserChild), CstError> {
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

    /// Return an iterator over `Shared<Name>` children labelled `name`.
    ///
    /// Off-type variants stored under the `name` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_name(&self) -> impl Iterator<Item = &Shared<Name>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name))
            .map(|(_, child)| match child { ParserChild::Name(s) => s })
    }

    /// Return the single child labelled `name`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_name(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ParserChild::Name(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `name`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_name(&self) -> Result<Option<&Shared<Name>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ParserChild::Name(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name))
                    .count(),
            }),
        }
    }

    /// Append a child with label `name`, accepting `Name` or `Shared<Name>`.
    pub fn append_name(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(ParserLabel::Name), ParserChild::Name(child.into())));
    }

    /// Append multiple children with label `name`.
    pub fn extend_name(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ParserLabel::Name), ParserChild::Name(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Parser")]
pub struct PyParser {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Parser>,
}

#[cfg(feature = "python")]
impl PyParser {
    /// Return a reference to the inner `Shared<Parser>`.
    pub fn shared(&self) -> &Shared<Parser> {
        &self.inner
    }

    /// Wrap a `Shared<Parser>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Parser>) -> PyResult<Py<PyParser>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyParser { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyParser>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyParser {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyParser>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Parser {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyParser { inner: shared };
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
        NodeKind::Parser
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ParserLabel::type_object(py).into_any().unbind())
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
        let native_child = ParserChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ParserLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Parser.append: label argument is not a Parser_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ParserLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Parser.extend: label argument is not a Parser_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ParserChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyParser) -> PyResult<()> {
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_name(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ParserChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ParserLabel::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ParserChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ParserLabel::Name), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ParserLabel::Name))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ParserLabel::Name) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one name child but have {count}"
            )));
        }
        first.expect("invariant: Parser.child_name: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ParserLabel::Name) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one name child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyParser>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyParser> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Parser'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Parser(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ApplyResultLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `ApplyResult_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ApplyResultLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "ApplyResult_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ApplyResultLabel {
    #[pyo3(name = "NAME")]
    Name,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ApplyResultLabel {
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl ApplyResultLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ApplyResultLabel::Name => "ApplyResult.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ApplyResultLabel>() {
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

/// Child value enum for `ApplyResult` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ApplyResultChild {
    Name(Shared<Name>),
}

impl PartialEq for ApplyResultChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ApplyResultChild::Name(a), ApplyResultChild::Name(b)) => a == b,
        }
    }
}

impl ApplyResultChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ApplyResultChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
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
        if obj.is_instance_of::<PyName>() {
            let handle: PyRef<PyName> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Name(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "ApplyResult: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// ApplyResult
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `ApplyResult`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct ApplyResult {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ApplyResultLabel>, ApplyResultChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for ApplyResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ApplyResult")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for ApplyResult {
    fn drop(&mut self) {
        if self.children.is_empty() {
            return; // also the recursion terminator for nodes drained by the worklist
        }
        // Worklist is allocated lazily: Vec::new() does not heap-allocate until
        // the first push.  drain_into pushes only when it steals (count == 1).
        // In the common backtracking case (shared/memoized children) no steal
        // occurs and no allocation happens.  Owned deep chains allocate once.
        let mut worklist: Vec<DropWorklistItem> = Vec::new();
        for (_, child) in self.children.drain(..) {
            if let Some(item) = child.into_drop_item() {
                item.drain_into(&mut worklist);
            }
        }
        while let Some(item) = worklist.pop() {
            item.drain_into(&mut worklist);
        }
    }
}

impl PartialEq for ApplyResult {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl ApplyResult {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        ApplyResult {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::ApplyResult
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
    pub fn children(&self) -> &[(Option<ApplyResultLabel>, ApplyResultChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ApplyResultLabel>, child: ApplyResultChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ApplyResultLabel>, ApplyResultChild), CstError> {
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

    /// Return an iterator over `Shared<Name>` children labelled `name`.
    ///
    /// Off-type variants stored under the `name` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_name(&self) -> impl Iterator<Item = &Shared<Name>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name))
            .map(|(_, child)| match child { ApplyResultChild::Name(s) => s })
    }

    /// Return the single child labelled `name`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_name(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ApplyResultChild::Name(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `name`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_name(&self) -> Result<Option<&Shared<Name>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ApplyResultChild::Name(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name))
                    .count(),
            }),
        }
    }

    /// Append a child with label `name`, accepting `Name` or `Shared<Name>`.
    pub fn append_name(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(ApplyResultLabel::Name), ApplyResultChild::Name(child.into())));
    }

    /// Append multiple children with label `name`.
    pub fn extend_name(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ApplyResultLabel::Name), ApplyResultChild::Name(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "ApplyResult")]
pub struct PyApplyResult {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<ApplyResult>,
}

#[cfg(feature = "python")]
impl PyApplyResult {
    /// Return a reference to the inner `Shared<ApplyResult>`.
    pub fn shared(&self) -> &Shared<ApplyResult> {
        &self.inner
    }

    /// Wrap a `Shared<ApplyResult>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<ApplyResult>) -> PyResult<Py<PyApplyResult>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyApplyResult { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyApplyResult>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyApplyResult {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyApplyResult>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = ApplyResult {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyApplyResult { inner: shared };
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
        NodeKind::ApplyResult
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ApplyResultLabel::type_object(py).into_any().unbind())
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
        let native_child = ApplyResultChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ApplyResultLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ApplyResult.append: label argument is not a ApplyResult_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ApplyResultLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ApplyResult.extend: label argument is not a ApplyResult_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ApplyResultChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyApplyResult) -> PyResult<()> {
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_name(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ApplyResultChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ApplyResultLabel::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ApplyResultChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ApplyResultLabel::Name), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ApplyResultLabel::Name))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ApplyResultLabel::Name) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one name child but have {count}"
            )));
        }
        first.expect("invariant: ApplyResult.child_name: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ApplyResultLabel::Name) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one name child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyApplyResult>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyApplyResult> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'ApplyResult'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "ApplyResult(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ItemLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Item_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ItemLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Item_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemLabel {
    #[pyo3(name = "A")]
    A,
    #[pyo3(name = "P")]
    P,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemLabel {
    A,
    P,
}

#[cfg(feature = "python")]
#[pymethods]
impl ItemLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ItemLabel::A => "Item.Label.A",
            ItemLabel::P => "Item.Label.P",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ItemLabel>() {
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

/// Child value enum for `Item` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ItemChild {
    ApplyResult(Shared<ApplyResult>),
    Parser(Shared<Parser>),
}

impl PartialEq for ItemChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ItemChild::ApplyResult(a), ItemChild::ApplyResult(b)) => a == b,
            (ItemChild::Parser(a), ItemChild::Parser(b)) => a == b,
            _ => false,
        }
    }
}

impl ItemChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::ApplyResult(s) => Some(DropWorklistItem::ApplyResult(s)),
            Self::Parser(s) => Some(DropWorklistItem::Parser(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ItemChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::ApplyResult(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyApplyResult { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Parser(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyParser { inner: shared.clone() };
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
        if obj.is_instance_of::<PyApplyResult>() {
            let handle: PyRef<PyApplyResult> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::ApplyResult(shared));
        }
        if obj.is_instance_of::<PyParser>() {
            let handle: PyRef<PyParser> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Parser(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Item: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Item
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Item`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Item {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ItemLabel>, ItemChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Item {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Item")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Item {
    fn drop(&mut self) {
        if self.children.is_empty() {
            return; // also the recursion terminator for nodes drained by the worklist
        }
        // Worklist is allocated lazily: Vec::new() does not heap-allocate until
        // the first push.  drain_into pushes only when it steals (count == 1).
        // In the common backtracking case (shared/memoized children) no steal
        // occurs and no allocation happens.  Owned deep chains allocate once.
        let mut worklist: Vec<DropWorklistItem> = Vec::new();
        for (_, child) in self.children.drain(..) {
            if let Some(item) = child.into_drop_item() {
                item.drain_into(&mut worklist);
            }
        }
        while let Some(item) = worklist.pop() {
            item.drain_into(&mut worklist);
        }
    }
}

impl PartialEq for Item {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Item {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Item {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Item
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
    pub fn children(&self) -> &[(Option<ItemLabel>, ItemChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ItemLabel>, child: ItemChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ItemLabel>, ItemChild), CstError> {
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

    /// Return an iterator over `Shared<ApplyResult>` children labelled `a`.
    ///
    /// Off-type variants stored under the `a` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_a(&self) -> impl Iterator<Item = &Shared<ApplyResult>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::A))
            .filter_map(|(_, child)| match child {
                ItemChild::ApplyResult(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `a`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_a(&self) -> Result<&Shared<ApplyResult>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::A));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::ApplyResult(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "a" }),
            },
            _ => Err(CstError::ChildCount {
                label: "a",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::A))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `a`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_a(&self) -> Result<Option<&Shared<ApplyResult>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::A));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::ApplyResult(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "a" }),
            },
            _ => Err(CstError::ChildCount {
                label: "a",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::A))
                    .count(),
            }),
        }
    }

    /// Append a child with label `a`, accepting `ApplyResult` or `Shared<ApplyResult>`.
    pub fn append_a(&mut self, child: impl Into<Shared<ApplyResult>>) {
        self.children.push((Some(ItemLabel::A), ItemChild::ApplyResult(child.into())));
    }

    /// Append multiple children with label `a`.
    pub fn extend_a(&mut self, children: impl IntoIterator<Item = impl Into<Shared<ApplyResult>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::A), ItemChild::ApplyResult(c.into()))));
    }

    /// Return an iterator over `Shared<Parser>` children labelled `p`.
    ///
    /// Off-type variants stored under the `p` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_p(&self) -> impl Iterator<Item = &Shared<Parser>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::P))
            .filter_map(|(_, child)| match child {
                ItemChild::Parser(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `p`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_p(&self) -> Result<&Shared<Parser>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::P));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::Parser(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "p" }),
            },
            _ => Err(CstError::ChildCount {
                label: "p",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::P))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `p`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_p(&self) -> Result<Option<&Shared<Parser>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::P));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::Parser(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "p" }),
            },
            _ => Err(CstError::ChildCount {
                label: "p",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::P))
                    .count(),
            }),
        }
    }

    /// Append a child with label `p`, accepting `Parser` or `Shared<Parser>`.
    pub fn append_p(&mut self, child: impl Into<Shared<Parser>>) {
        self.children.push((Some(ItemLabel::P), ItemChild::Parser(child.into())));
    }

    /// Append multiple children with label `p`.
    pub fn extend_p(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Parser>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::P), ItemChild::Parser(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Item")]
pub struct PyItem {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Item>,
}

#[cfg(feature = "python")]
impl PyItem {
    /// Return a reference to the inner `Shared<Item>`.
    pub fn shared(&self) -> &Shared<Item> {
        &self.inner
    }

    /// Wrap a `Shared<Item>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Item>) -> PyResult<Py<PyItem>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyItem { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyItem>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyItem {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyItem>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Item {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyItem { inner: shared };
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
        NodeKind::Item
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ItemLabel::type_object(py).into_any().unbind())
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
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ItemLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Item.append: label argument is not a Item_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ItemLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Item.extend: label argument is not a Item_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyItem) -> PyResult<()> {
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_a(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::A), native_child));
        Ok(())
    }

    fn extend_a(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::A), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_a(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::A))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_a(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::A) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one a child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_a: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_a(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::A) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one a child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_p(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::P), native_child));
        Ok(())
    }

    fn extend_p(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::P), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_p(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::P))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_p(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::P) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one p child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_p: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_p(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::P) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one p child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyItem>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyItem> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Item'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Item(span={span_repr}, children=[<{children_len} child(ren)>])"
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
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Trivia {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<TriviaLabel>, TriviaChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Trivia {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Trivia")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
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
        // Lock scope: read len and clone at most the single entry under the guard;
        // drop the guard before any Python work (object conversion, exception raise).
        let (n, entry) = {
            let guard = self.inner.read();
            let n = guard.children.len();
            let entry = if n == 1 { Some(guard.children[0].clone()) } else { None };
            (n, entry)
        };
        let Some((label, child)) = entry else {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        };
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TriviaLabel::Content))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::Content) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one content child but have {count}"
            )));
        }
        first.expect("invariant: Trivia.child_content: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::Content) {
                    count += 1;
                    if count == 1 {
                        first = Some(child.clone());
                    }
                }
            }
            (count, first)
        };
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one content child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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

// ───────────────────────────────────────────────────────────────────────────
// DropWorklistItem
// ───────────────────────────────────────────────────────────────────────────

// Worklist item for iterative node teardown. See the per-node `impl Drop`.
// Module-private: only used by impl Drop and into_drop_item in this file.
enum DropWorklistItem {
    ApplyResult(Shared<ApplyResult>),
    Item(Shared<Item>),
    Name(Shared<Name>),
    Parser(Shared<Parser>),
}

impl DropWorklistItem {
    fn drain_into(self, worklist: &mut Vec<DropWorklistItem>) {
        // Each arm: if sole owner, steal children (so the node's Drop early-returns
        // instead of recursing through drop glue); then drop `shared`.
        // count==1 → childless node after steal, trivial drop;
        // count>1 → refcount decrement only. Either way, no recursion.
        match self {
            DropWorklistItem::ApplyResult(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Item(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Name(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Parser(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
        }
    }
}

#[cfg(feature = "python")]
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<RootLabel>()?;
    module.add_class::<PyRoot>()?;
    module.add_class::<NameLabel>()?;
    module.add_class::<PyName>()?;
    module.add_class::<ParserLabel>()?;
    module.add_class::<PyParser>()?;
    module.add_class::<ApplyResultLabel>()?;
    module.add_class::<PyApplyResult>()?;
    module.add_class::<ItemLabel>()?;
    module.add_class::<PyItem>()?;
    module.add_class::<TriviaLabel>()?;
    module.add_class::<PyTrivia>()?;
    Ok(())
}
