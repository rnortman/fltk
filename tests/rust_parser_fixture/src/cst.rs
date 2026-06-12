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
    #[pyo3(name = "NUM")]
    Num,
    #[pyo3(name = "NAME")]
    Name,
    #[pyo3(name = "ATOM")]
    Atom,
    #[pyo3(name = "PARENEXPR")]
    ParenExpr,
    #[pyo3(name = "STMT")]
    Stmt,
    #[pyo3(name = "ITEMS")]
    Items,
    #[pyo3(name = "OPTITEM")]
    OptItem,
    #[pyo3(name = "ZEROITEMS")]
    ZeroItems,
    #[pyo3(name = "EXPR")]
    Expr,
    #[pyo3(name = "LVAL")]
    Lval,
    #[pyo3(name = "RVAL")]
    Rval,
    #[pyo3(name = "ARROW")]
    Arrow,
    #[pyo3(name = "LATINWORD")]
    LatinWord,
    #[pyo3(name = "TAGGED")]
    Tagged,
    #[pyo3(name = "VAL")]
    Val,
    #[pyo3(name = "LEADINGWS")]
    LeadingWs,
    #[pyo3(name = "GROUPED")]
    Grouped,
    #[pyo3(name = "RECVIASUB")]
    RecViaSub,
    #[pyo3(name = "NEST")]
    Nest,
    #[pyo3(name = "NESTSUM")]
    NestSum,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Num,
    Name,
    Atom,
    ParenExpr,
    Stmt,
    Items,
    OptItem,
    ZeroItems,
    Expr,
    Lval,
    Rval,
    Arrow,
    LatinWord,
    Tagged,
    Val,
    LeadingWs,
    Grouped,
    RecViaSub,
    Nest,
    NestSum,
    Trivia,
}

#[cfg(feature = "python")]
#[pymethods]
impl NodeKind {
    fn __repr__(&self) -> &'static str {
        match self {
            NodeKind::Num => "NodeKind.NUM",
            NodeKind::Name => "NodeKind.NAME",
            NodeKind::Atom => "NodeKind.ATOM",
            NodeKind::ParenExpr => "NodeKind.PARENEXPR",
            NodeKind::Stmt => "NodeKind.STMT",
            NodeKind::Items => "NodeKind.ITEMS",
            NodeKind::OptItem => "NodeKind.OPTITEM",
            NodeKind::ZeroItems => "NodeKind.ZEROITEMS",
            NodeKind::Expr => "NodeKind.EXPR",
            NodeKind::Lval => "NodeKind.LVAL",
            NodeKind::Rval => "NodeKind.RVAL",
            NodeKind::Arrow => "NodeKind.ARROW",
            NodeKind::LatinWord => "NodeKind.LATINWORD",
            NodeKind::Tagged => "NodeKind.TAGGED",
            NodeKind::Val => "NodeKind.VAL",
            NodeKind::LeadingWs => "NodeKind.LEADINGWS",
            NodeKind::Grouped => "NodeKind.GROUPED",
            NodeKind::RecViaSub => "NodeKind.RECVIASUB",
            NodeKind::Nest => "NodeKind.NEST",
            NodeKind::NestSum => "NodeKind.NESTSUM",
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
// NumLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Num_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `NumLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Num_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NumLabel {
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NumLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl NumLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            NumLabel::Value => "Num.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<NumLabel>() {
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

/// Child value enum for `Num` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum NumChild {
    Span(Span),
}

impl PartialEq for NumChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (NumChild::Span(a), NumChild::Span(b)) => a == b,
        }
    }
}

impl NumChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl NumChild {
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
            "Num: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Num
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Num`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Num {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<NumLabel>, NumChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Num {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Num")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Num {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Num {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Num {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Num
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
    pub fn children(&self) -> &[(Option<NumLabel>, NumChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<NumLabel>, child: NumChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<NumLabel>, NumChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(NumLabel::Value))
            .map(|(_, child)| match child { NumChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NumLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NumChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NumLabel::Value))
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
            .filter(|(lbl, _)| *lbl == Some(NumLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NumChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NumLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(NumLabel::Value), NumChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(NumLabel::Value), NumChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Num")]
pub struct PyNum {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Num>,
}

#[cfg(feature = "python")]
impl PyNum {
    /// Return a reference to the inner `Shared<Num>`.
    pub fn shared(&self) -> &Shared<Num> {
        &self.inner
    }

    /// Wrap a `Shared<Num>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Num>) -> PyResult<Py<PyNum>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyNum { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyNum>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyNum {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyNum>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Num {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyNum { inner: shared };
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
        NodeKind::Num
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(NumLabel::type_object(py).into_any().unbind())
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
        let native_child = NumChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<NumLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Num.append: label argument is not a Num_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<NumLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Num.extend: label argument is not a Num_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NumChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyNum) -> PyResult<()> {
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
        let native_child = NumChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NumLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NumChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NumLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(NumLabel::Value))
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
                if *lbl == Some(NumLabel::Value) {
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
        first.expect("invariant: Num.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(NumLabel::Value) {
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
        if !other.is_instance_of::<PyNum>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyNum> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Num'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Num(span={span_repr}, children=[<{children_len} child(ren)>])"
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
// AtomLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Atom_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `AtomLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Atom_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum AtomLabel {
    #[pyo3(name = "NAME")]
    Name,
    #[pyo3(name = "NUM")]
    Num,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum AtomLabel {
    Name,
    Num,
}

#[cfg(feature = "python")]
#[pymethods]
impl AtomLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            AtomLabel::Name => "Atom.Label.NAME",
            AtomLabel::Num => "Atom.Label.NUM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<AtomLabel>() {
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

/// Child value enum for `Atom` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum AtomChild {
    Name(Shared<Name>),
    Num(Shared<Num>),
}

impl PartialEq for AtomChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (AtomChild::Name(a), AtomChild::Name(b)) => a == b,
            (AtomChild::Num(a), AtomChild::Num(b)) => a == b,
            _ => false,
        }
    }
}

impl AtomChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
        }
    }
}

#[cfg(feature = "python")]
impl AtomChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Atom: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Atom
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Atom`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Atom {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<AtomLabel>, AtomChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Atom {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Atom")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Atom {
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

impl PartialEq for Atom {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Atom {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Atom {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Atom
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
    pub fn children(&self) -> &[(Option<AtomLabel>, AtomChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<AtomLabel>, child: AtomChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<AtomLabel>, AtomChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name))
            .filter_map(|(_, child)| match child {
                AtomChild::Name(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `name`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_name(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                AtomChild::Name(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "name" }),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name))
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
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                AtomChild::Name(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "name" }),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name))
                    .count(),
            }),
        }
    }

    /// Append a child with label `name`, accepting `Name` or `Shared<Name>`.
    pub fn append_name(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(AtomLabel::Name), AtomChild::Name(child.into())));
    }

    /// Append multiple children with label `name`.
    pub fn extend_name(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(AtomLabel::Name), AtomChild::Name(c.into()))));
    }

    /// Return an iterator over `Shared<Num>` children labelled `num`.
    ///
    /// Off-type variants stored under the `num` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_num(&self) -> impl Iterator<Item = &Shared<Num>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num))
            .filter_map(|(_, child)| match child {
                AtomChild::Num(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `num`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_num(&self) -> Result<&Shared<Num>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                AtomChild::Num(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "num" }),
            },
            _ => Err(CstError::ChildCount {
                label: "num",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `num`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_num(&self) -> Result<Option<&Shared<Num>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                AtomChild::Num(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "num" }),
            },
            _ => Err(CstError::ChildCount {
                label: "num",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num))
                    .count(),
            }),
        }
    }

    /// Append a child with label `num`, accepting `Num` or `Shared<Num>`.
    pub fn append_num(&mut self, child: impl Into<Shared<Num>>) {
        self.children.push((Some(AtomLabel::Num), AtomChild::Num(child.into())));
    }

    /// Append multiple children with label `num`.
    pub fn extend_num(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Num>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(AtomLabel::Num), AtomChild::Num(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Atom")]
pub struct PyAtom {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Atom>,
}

#[cfg(feature = "python")]
impl PyAtom {
    /// Return a reference to the inner `Shared<Atom>`.
    pub fn shared(&self) -> &Shared<Atom> {
        &self.inner
    }

    /// Wrap a `Shared<Atom>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Atom>) -> PyResult<Py<PyAtom>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyAtom { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyAtom>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyAtom {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyAtom>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Atom {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyAtom { inner: shared };
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
        NodeKind::Atom
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(AtomLabel::type_object(py).into_any().unbind())
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
        let native_child = AtomChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<AtomLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Atom.append: label argument is not a Atom_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<AtomLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Atom.extend: label argument is not a Atom_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AtomChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyAtom) -> PyResult<()> {
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
        let native_child = AtomChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(AtomLabel::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AtomChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(AtomLabel::Name), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(AtomLabel::Name))
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
                if *lbl == Some(AtomLabel::Name) {
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
        first.expect("invariant: Atom.child_name: count==1 but first==None; logic error")
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
                if *lbl == Some(AtomLabel::Name) {
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

    fn append_num(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = AtomChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(AtomLabel::Num), native_child));
        Ok(())
    }

    fn extend_num(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AtomChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(AtomLabel::Num), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_num(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(AtomLabel::Num))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_num(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(AtomLabel::Num) {
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
                "Expected one num child but have {count}"
            )));
        }
        first.expect("invariant: Atom.child_num: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_num(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(AtomLabel::Num) {
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
                "Expected at most one num child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyAtom>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyAtom> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Atom'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Atom(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ParenExprLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `ParenExpr_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ParenExprLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "ParenExpr_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ParenExprLabel {
    #[pyo3(name = "INNER")]
    Inner,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ParenExprLabel {
    Inner,
}

#[cfg(feature = "python")]
#[pymethods]
impl ParenExprLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ParenExprLabel::Inner => "ParenExpr.Label.INNER",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ParenExprLabel>() {
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

/// Child value enum for `ParenExpr` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ParenExprChild {
    Atom(Shared<Atom>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for ParenExprChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ParenExprChild::Atom(a), ParenExprChild::Atom(b)) => a == b,
            (ParenExprChild::Trivia(a), ParenExprChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl ParenExprChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ParenExprChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
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
            "ParenExpr: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// ParenExpr
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `ParenExpr`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct ParenExpr {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ParenExprLabel>, ParenExprChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for ParenExpr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ParenExpr")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for ParenExpr {
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

impl PartialEq for ParenExpr {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl ParenExpr {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        ParenExpr {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::ParenExpr
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
    pub fn children(&self) -> &[(Option<ParenExprLabel>, ParenExprChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ParenExprLabel>, child: ParenExprChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ParenExprLabel>, ParenExprChild), CstError> {
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

    /// Return an iterator over `Shared<Atom>` children labelled `inner`.
    ///
    /// Off-type variants stored under the `inner` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_inner(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner))
            .filter_map(|(_, child)| match child {
                ParenExprChild::Atom(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `inner`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inner(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ParenExprChild::Atom(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `inner`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inner(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ParenExprChild::Atom(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Append a child with label `inner`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_inner(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(ParenExprLabel::Inner), ParenExprChild::Atom(child.into())));
    }

    /// Append multiple children with label `inner`.
    pub fn extend_inner(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ParenExprLabel::Inner), ParenExprChild::Atom(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "ParenExpr")]
pub struct PyParenExpr {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<ParenExpr>,
}

#[cfg(feature = "python")]
impl PyParenExpr {
    /// Return a reference to the inner `Shared<ParenExpr>`.
    pub fn shared(&self) -> &Shared<ParenExpr> {
        &self.inner
    }

    /// Wrap a `Shared<ParenExpr>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<ParenExpr>) -> PyResult<Py<PyParenExpr>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyParenExpr { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyParenExpr>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyParenExpr {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyParenExpr>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = ParenExpr {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyParenExpr { inner: shared };
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
        NodeKind::ParenExpr
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ParenExprLabel::type_object(py).into_any().unbind())
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
        let native_child = ParenExprChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ParenExprLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ParenExpr.append: label argument is not a ParenExpr_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ParenExprLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ParenExpr.extend: label argument is not a ParenExpr_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ParenExprChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyParenExpr) -> PyResult<()> {
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

    fn append_inner(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ParenExprChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ParenExprLabel::Inner), native_child));
        Ok(())
    }

    fn extend_inner(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ParenExprChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ParenExprLabel::Inner), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inner(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ParenExprLabel::Inner))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inner(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ParenExprLabel::Inner) {
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
                "Expected one inner child but have {count}"
            )));
        }
        first.expect("invariant: ParenExpr.child_inner: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inner(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ParenExprLabel::Inner) {
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
                "Expected at most one inner child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyParenExpr>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyParenExpr> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'ParenExpr'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "ParenExpr(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// StmtLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Stmt_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `StmtLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Stmt_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum StmtLabel {
    #[pyo3(name = "LHS")]
    Lhs,
    #[pyo3(name = "RHS")]
    Rhs,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum StmtLabel {
    Lhs,
    Rhs,
}

#[cfg(feature = "python")]
#[pymethods]
impl StmtLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            StmtLabel::Lhs => "Stmt.Label.LHS",
            StmtLabel::Rhs => "Stmt.Label.RHS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<StmtLabel>() {
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

/// Child value enum for `Stmt` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum StmtChild {
    Atom(Shared<Atom>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for StmtChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (StmtChild::Atom(a), StmtChild::Atom(b)) => a == b,
            (StmtChild::Trivia(a), StmtChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl StmtChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl StmtChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
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
            "Stmt: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Stmt
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Stmt`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Stmt {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<StmtLabel>, StmtChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Stmt {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Stmt")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Stmt {
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

impl PartialEq for Stmt {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Stmt {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Stmt {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Stmt
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
    pub fn children(&self) -> &[(Option<StmtLabel>, StmtChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<StmtLabel>, child: StmtChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<StmtLabel>, StmtChild), CstError> {
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

    /// Return an iterator over `Shared<Atom>` children labelled `lhs`.
    ///
    /// Off-type variants stored under the `lhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_lhs(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs))
            .filter_map(|(_, child)| match child {
                StmtChild::Atom(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `lhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_lhs(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                StmtChild::Atom(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `lhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_lhs(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                StmtChild::Atom(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `lhs`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_lhs(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(StmtLabel::Lhs), StmtChild::Atom(child.into())));
    }

    /// Append multiple children with label `lhs`.
    pub fn extend_lhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(StmtLabel::Lhs), StmtChild::Atom(c.into()))));
    }

    /// Return an iterator over `Shared<Atom>` children labelled `rhs`.
    ///
    /// Off-type variants stored under the `rhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_rhs(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs))
            .filter_map(|(_, child)| match child {
                StmtChild::Atom(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `rhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_rhs(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                StmtChild::Atom(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `rhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_rhs(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                StmtChild::Atom(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `rhs`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_rhs(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(StmtLabel::Rhs), StmtChild::Atom(child.into())));
    }

    /// Append multiple children with label `rhs`.
    pub fn extend_rhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(StmtLabel::Rhs), StmtChild::Atom(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Stmt")]
pub struct PyStmt {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Stmt>,
}

#[cfg(feature = "python")]
impl PyStmt {
    /// Return a reference to the inner `Shared<Stmt>`.
    pub fn shared(&self) -> &Shared<Stmt> {
        &self.inner
    }

    /// Wrap a `Shared<Stmt>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Stmt>) -> PyResult<Py<PyStmt>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyStmt { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyStmt>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyStmt {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyStmt>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Stmt {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyStmt { inner: shared };
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
        NodeKind::Stmt
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(StmtLabel::type_object(py).into_any().unbind())
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
        let native_child = StmtChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<StmtLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Stmt.append: label argument is not a Stmt_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<StmtLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Stmt.extend: label argument is not a Stmt_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = StmtChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyStmt) -> PyResult<()> {
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

    fn append_lhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = StmtChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(StmtLabel::Lhs), native_child));
        Ok(())
    }

    fn extend_lhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = StmtChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(StmtLabel::Lhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_lhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(StmtLabel::Lhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_lhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(StmtLabel::Lhs) {
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
                "Expected one lhs child but have {count}"
            )));
        }
        first.expect("invariant: Stmt.child_lhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_lhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(StmtLabel::Lhs) {
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
                "Expected at most one lhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_rhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = StmtChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(StmtLabel::Rhs), native_child));
        Ok(())
    }

    fn extend_rhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = StmtChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(StmtLabel::Rhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_rhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(StmtLabel::Rhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_rhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(StmtLabel::Rhs) {
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
                "Expected one rhs child but have {count}"
            )));
        }
        first.expect("invariant: Stmt.child_rhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_rhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(StmtLabel::Rhs) {
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
                "Expected at most one rhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyStmt>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyStmt> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Stmt'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Stmt(span={span_repr}, children=[<{children_len} child(ren)>])"
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
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemsLabel {
    Item,
}

#[cfg(feature = "python")]
#[pymethods]
impl ItemsLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ItemsLabel::Item => "Items.Label.ITEM",
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
    Atom(Shared<Atom>),
}

impl PartialEq for ItemsChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ItemsChild::Atom(a), ItemsChild::Atom(b)) => a == b,
        }
    }
}

impl ItemsChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ItemsChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
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
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Items {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ItemsLabel>, ItemsChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Items {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Items")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Items {
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

    /// Return an iterator over `Shared<Atom>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
            .map(|(_, child)| match child { ItemsChild::Atom(s) => s })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Atom(s) => Ok(s),
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
    pub fn maybe_item(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Atom(s) => Ok(Some(s)),
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

    /// Append a child with label `item`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(ItemsLabel::Item), ItemsChild::Atom(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemsLabel::Item), ItemsChild::Atom(c.into()))));
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
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
                if *lbl == Some(ItemsLabel::Item) {
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
        first.expect("invariant: Items.child_item: count==1 but first==None; logic error")
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
                if *lbl == Some(ItemsLabel::Item) {
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
// OptItemLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `OptItem_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `OptItemLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "OptItem_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum OptItemLabel {
    #[pyo3(name = "ITEM")]
    Item,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum OptItemLabel {
    Item,
}

#[cfg(feature = "python")]
#[pymethods]
impl OptItemLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            OptItemLabel::Item => "OptItem.Label.ITEM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<OptItemLabel>() {
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

/// Child value enum for `OptItem` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum OptItemChild {
    Atom(Shared<Atom>),
}

impl PartialEq for OptItemChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (OptItemChild::Atom(a), OptItemChild::Atom(b)) => a == b,
        }
    }
}

impl OptItemChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
        }
    }
}

#[cfg(feature = "python")]
impl OptItemChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "OptItem: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// OptItem
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `OptItem`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct OptItem {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<OptItemLabel>, OptItemChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for OptItem {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("OptItem")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for OptItem {
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

impl PartialEq for OptItem {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl OptItem {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        OptItem {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::OptItem
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
    pub fn children(&self) -> &[(Option<OptItemLabel>, OptItemChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<OptItemLabel>, child: OptItemChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<OptItemLabel>, OptItemChild), CstError> {
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

    /// Return an iterator over `Shared<Atom>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item))
            .map(|(_, child)| match child { OptItemChild::Atom(s) => s })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                OptItemChild::Atom(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `item`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_item(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                OptItemChild::Atom(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item))
                    .count(),
            }),
        }
    }

    /// Append a child with label `item`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(OptItemLabel::Item), OptItemChild::Atom(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(OptItemLabel::Item), OptItemChild::Atom(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "OptItem")]
pub struct PyOptItem {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<OptItem>,
}

#[cfg(feature = "python")]
impl PyOptItem {
    /// Return a reference to the inner `Shared<OptItem>`.
    pub fn shared(&self) -> &Shared<OptItem> {
        &self.inner
    }

    /// Wrap a `Shared<OptItem>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<OptItem>) -> PyResult<Py<PyOptItem>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyOptItem { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyOptItem>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyOptItem {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyOptItem>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = OptItem {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyOptItem { inner: shared };
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
        NodeKind::OptItem
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(OptItemLabel::type_object(py).into_any().unbind())
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
        let native_child = OptItemChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<OptItemLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "OptItem.append: label argument is not a OptItem_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<OptItemLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "OptItem.extend: label argument is not a OptItem_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OptItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyOptItem) -> PyResult<()> {
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
        let native_child = OptItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(OptItemLabel::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OptItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(OptItemLabel::Item), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(OptItemLabel::Item))
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
                if *lbl == Some(OptItemLabel::Item) {
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
        first.expect("invariant: OptItem.child_item: count==1 but first==None; logic error")
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
                if *lbl == Some(OptItemLabel::Item) {
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
        if !other.is_instance_of::<PyOptItem>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyOptItem> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'OptItem'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "OptItem(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ZeroItemsLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `ZeroItems_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ZeroItemsLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "ZeroItems_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ZeroItemsLabel {
    #[pyo3(name = "ITEM")]
    Item,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ZeroItemsLabel {
    Item,
}

#[cfg(feature = "python")]
#[pymethods]
impl ZeroItemsLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ZeroItemsLabel::Item => "ZeroItems.Label.ITEM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ZeroItemsLabel>() {
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

/// Child value enum for `ZeroItems` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ZeroItemsChild {
    Atom(Shared<Atom>),
}

impl PartialEq for ZeroItemsChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ZeroItemsChild::Atom(a), ZeroItemsChild::Atom(b)) => a == b,
        }
    }
}

impl ZeroItemsChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ZeroItemsChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "ZeroItems: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// ZeroItems
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `ZeroItems`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct ZeroItems {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ZeroItemsLabel>, ZeroItemsChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for ZeroItems {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ZeroItems")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for ZeroItems {
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

impl PartialEq for ZeroItems {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl ZeroItems {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        ZeroItems {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::ZeroItems
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
    pub fn children(&self) -> &[(Option<ZeroItemsLabel>, ZeroItemsChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ZeroItemsLabel>, child: ZeroItemsChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ZeroItemsLabel>, ZeroItemsChild), CstError> {
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

    /// Return an iterator over `Shared<Atom>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item))
            .map(|(_, child)| match child { ZeroItemsChild::Atom(s) => s })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ZeroItemsChild::Atom(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `item`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_item(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ZeroItemsChild::Atom(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "item",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item))
                    .count(),
            }),
        }
    }

    /// Append a child with label `item`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(ZeroItemsLabel::Item), ZeroItemsChild::Atom(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ZeroItemsLabel::Item), ZeroItemsChild::Atom(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "ZeroItems")]
pub struct PyZeroItems {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<ZeroItems>,
}

#[cfg(feature = "python")]
impl PyZeroItems {
    /// Return a reference to the inner `Shared<ZeroItems>`.
    pub fn shared(&self) -> &Shared<ZeroItems> {
        &self.inner
    }

    /// Wrap a `Shared<ZeroItems>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<ZeroItems>) -> PyResult<Py<PyZeroItems>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyZeroItems { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyZeroItems>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyZeroItems {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyZeroItems>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = ZeroItems {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyZeroItems { inner: shared };
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
        NodeKind::ZeroItems
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ZeroItemsLabel::type_object(py).into_any().unbind())
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
        let native_child = ZeroItemsChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ZeroItemsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ZeroItems.append: label argument is not a ZeroItems_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ZeroItemsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ZeroItems.extend: label argument is not a ZeroItems_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ZeroItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyZeroItems) -> PyResult<()> {
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
        let native_child = ZeroItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ZeroItemsLabel::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ZeroItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ZeroItemsLabel::Item), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(ZeroItemsLabel::Item))
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
                if *lbl == Some(ZeroItemsLabel::Item) {
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
        first.expect("invariant: ZeroItems.child_item: count==1 but first==None; logic error")
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
                if *lbl == Some(ZeroItemsLabel::Item) {
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
        if !other.is_instance_of::<PyZeroItems>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyZeroItems> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'ZeroItems'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "ZeroItems(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ExprLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Expr_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ExprLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Expr_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ExprLabel {
    #[pyo3(name = "ATOM")]
    Atom,
    #[pyo3(name = "LHS")]
    Lhs,
    #[pyo3(name = "RHS")]
    Rhs,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ExprLabel {
    Atom,
    Lhs,
    Rhs,
}

#[cfg(feature = "python")]
#[pymethods]
impl ExprLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ExprLabel::Atom => "Expr.Label.ATOM",
            ExprLabel::Lhs => "Expr.Label.LHS",
            ExprLabel::Rhs => "Expr.Label.RHS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ExprLabel>() {
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

/// Child value enum for `Expr` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ExprChild {
    Atom(Shared<Atom>),
    Expr(Shared<Expr>),
}

impl PartialEq for ExprChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ExprChild::Atom(a), ExprChild::Atom(b)) => a == b,
            (ExprChild::Expr(a), ExprChild::Expr(b)) => a == b,
            _ => false,
        }
    }
}

impl ExprChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
            Self::Expr(s) => Some(DropWorklistItem::Expr(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ExprChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Expr(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyExpr { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
        }
        if obj.is_instance_of::<PyExpr>() {
            let handle: PyRef<PyExpr> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Expr(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Expr: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Expr
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Expr`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Expr {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ExprLabel>, ExprChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Expr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Expr")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Expr {
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

impl PartialEq for Expr {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Expr {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Expr {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Expr
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
    pub fn children(&self) -> &[(Option<ExprLabel>, ExprChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ExprLabel>, child: ExprChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ExprLabel>, ExprChild), CstError> {
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

    /// Return an iterator over `Shared<Atom>` children labelled `atom`.
    ///
    /// Off-type variants stored under the `atom` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_atom(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom))
            .filter_map(|(_, child)| match child {
                ExprChild::Atom(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `atom`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_atom(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ExprChild::Atom(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "atom" }),
            },
            _ => Err(CstError::ChildCount {
                label: "atom",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `atom`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_atom(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ExprChild::Atom(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "atom" }),
            },
            _ => Err(CstError::ChildCount {
                label: "atom",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom))
                    .count(),
            }),
        }
    }

    /// Append a child with label `atom`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_atom(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(ExprLabel::Atom), ExprChild::Atom(child.into())));
    }

    /// Append multiple children with label `atom`.
    pub fn extend_atom(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ExprLabel::Atom), ExprChild::Atom(c.into()))));
    }

    /// Return an iterator over `Shared<Expr>` children labelled `lhs`.
    ///
    /// Off-type variants stored under the `lhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_lhs(&self) -> impl Iterator<Item = &Shared<Expr>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs))
            .filter_map(|(_, child)| match child {
                ExprChild::Expr(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `lhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_lhs(&self) -> Result<&Shared<Expr>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ExprChild::Expr(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `lhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_lhs(&self) -> Result<Option<&Shared<Expr>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ExprChild::Expr(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `lhs`, accepting `Expr` or `Shared<Expr>`.
    pub fn append_lhs(&mut self, child: impl Into<Shared<Expr>>) {
        self.children.push((Some(ExprLabel::Lhs), ExprChild::Expr(child.into())));
    }

    /// Append multiple children with label `lhs`.
    pub fn extend_lhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Expr>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ExprLabel::Lhs), ExprChild::Expr(c.into()))));
    }

    /// Return an iterator over `Shared<Atom>` children labelled `rhs`.
    ///
    /// Off-type variants stored under the `rhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_rhs(&self) -> impl Iterator<Item = &Shared<Atom>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs))
            .filter_map(|(_, child)| match child {
                ExprChild::Atom(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `rhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_rhs(&self) -> Result<&Shared<Atom>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ExprChild::Atom(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `rhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_rhs(&self) -> Result<Option<&Shared<Atom>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ExprChild::Atom(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `rhs`, accepting `Atom` or `Shared<Atom>`.
    pub fn append_rhs(&mut self, child: impl Into<Shared<Atom>>) {
        self.children.push((Some(ExprLabel::Rhs), ExprChild::Atom(child.into())));
    }

    /// Append multiple children with label `rhs`.
    pub fn extend_rhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Atom>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ExprLabel::Rhs), ExprChild::Atom(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Expr")]
pub struct PyExpr {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Expr>,
}

#[cfg(feature = "python")]
impl PyExpr {
    /// Return a reference to the inner `Shared<Expr>`.
    pub fn shared(&self) -> &Shared<Expr> {
        &self.inner
    }

    /// Wrap a `Shared<Expr>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Expr>) -> PyResult<Py<PyExpr>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyExpr { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyExpr>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyExpr {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyExpr>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Expr {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyExpr { inner: shared };
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
        NodeKind::Expr
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ExprLabel::type_object(py).into_any().unbind())
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
        let native_child = ExprChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ExprLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Expr.append: label argument is not a Expr_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ExprLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Expr.extend: label argument is not a Expr_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ExprChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyExpr) -> PyResult<()> {
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

    fn append_atom(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ExprChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ExprLabel::Atom), native_child));
        Ok(())
    }

    fn extend_atom(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ExprChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ExprLabel::Atom), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_atom(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ExprLabel::Atom))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_atom(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Atom) {
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
                "Expected one atom child but have {count}"
            )));
        }
        first.expect("invariant: Expr.child_atom: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_atom(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Atom) {
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
                "Expected at most one atom child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_lhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ExprChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ExprLabel::Lhs), native_child));
        Ok(())
    }

    fn extend_lhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ExprChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ExprLabel::Lhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_lhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ExprLabel::Lhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_lhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Lhs) {
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
                "Expected one lhs child but have {count}"
            )));
        }
        first.expect("invariant: Expr.child_lhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_lhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Lhs) {
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
                "Expected at most one lhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_rhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ExprChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ExprLabel::Rhs), native_child));
        Ok(())
    }

    fn extend_rhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ExprChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ExprLabel::Rhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_rhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ExprLabel::Rhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_rhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Rhs) {
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
                "Expected one rhs child but have {count}"
            )));
        }
        first.expect("invariant: Expr.child_rhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_rhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ExprLabel::Rhs) {
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
                "Expected at most one rhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyExpr>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyExpr> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Expr'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Expr(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// LvalLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Lval_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `LvalLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Lval_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LvalLabel {
    #[pyo3(name = "BASE")]
    Base,
    #[pyo3(name = "INNER")]
    Inner,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LvalLabel {
    Base,
    Inner,
}

#[cfg(feature = "python")]
#[pymethods]
impl LvalLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LvalLabel::Base => "Lval.Label.BASE",
            LvalLabel::Inner => "Lval.Label.INNER",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LvalLabel>() {
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

/// Child value enum for `Lval` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum LvalChild {
    Name(Shared<Name>),
    Rval(Shared<Rval>),
}

impl PartialEq for LvalChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (LvalChild::Name(a), LvalChild::Name(b)) => a == b,
            (LvalChild::Rval(a), LvalChild::Rval(b)) => a == b,
            _ => false,
        }
    }
}

impl LvalChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
            Self::Rval(s) => Some(DropWorklistItem::Rval(s)),
        }
    }
}

#[cfg(feature = "python")]
impl LvalChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Rval(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyRval { inner: shared.clone() };
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
        if obj.is_instance_of::<PyRval>() {
            let handle: PyRef<PyRval> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Rval(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Lval: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Lval
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Lval`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Lval {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LvalLabel>, LvalChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Lval {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Lval")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Lval {
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

impl PartialEq for Lval {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Lval {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Lval {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Lval
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
    pub fn children(&self) -> &[(Option<LvalLabel>, LvalChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<LvalLabel>, child: LvalChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<LvalLabel>, LvalChild), CstError> {
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

    /// Return an iterator over `Shared<Name>` children labelled `base`.
    ///
    /// Off-type variants stored under the `base` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_base(&self) -> impl Iterator<Item = &Shared<Name>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base))
            .filter_map(|(_, child)| match child {
                LvalChild::Name(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `base`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_base(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LvalChild::Name(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "base" }),
            },
            _ => Err(CstError::ChildCount {
                label: "base",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `base`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_base(&self) -> Result<Option<&Shared<Name>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LvalChild::Name(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "base" }),
            },
            _ => Err(CstError::ChildCount {
                label: "base",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base))
                    .count(),
            }),
        }
    }

    /// Append a child with label `base`, accepting `Name` or `Shared<Name>`.
    pub fn append_base(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(LvalLabel::Base), LvalChild::Name(child.into())));
    }

    /// Append multiple children with label `base`.
    pub fn extend_base(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(LvalLabel::Base), LvalChild::Name(c.into()))));
    }

    /// Return an iterator over `Shared<Rval>` children labelled `inner`.
    ///
    /// Off-type variants stored under the `inner` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_inner(&self) -> impl Iterator<Item = &Shared<Rval>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner))
            .filter_map(|(_, child)| match child {
                LvalChild::Rval(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `inner`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inner(&self) -> Result<&Shared<Rval>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LvalChild::Rval(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `inner`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inner(&self) -> Result<Option<&Shared<Rval>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LvalChild::Rval(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Append a child with label `inner`, accepting `Rval` or `Shared<Rval>`.
    pub fn append_inner(&mut self, child: impl Into<Shared<Rval>>) {
        self.children.push((Some(LvalLabel::Inner), LvalChild::Rval(child.into())));
    }

    /// Append multiple children with label `inner`.
    pub fn extend_inner(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Rval>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(LvalLabel::Inner), LvalChild::Rval(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Lval")]
pub struct PyLval {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Lval>,
}

#[cfg(feature = "python")]
impl PyLval {
    /// Return a reference to the inner `Shared<Lval>`.
    pub fn shared(&self) -> &Shared<Lval> {
        &self.inner
    }

    /// Wrap a `Shared<Lval>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Lval>) -> PyResult<Py<PyLval>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyLval { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyLval>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyLval {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyLval>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Lval {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyLval { inner: shared };
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
        NodeKind::Lval
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(LvalLabel::type_object(py).into_any().unbind())
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
        let native_child = LvalChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LvalLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Lval.append: label argument is not a Lval_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LvalLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Lval.extend: label argument is not a Lval_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LvalChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyLval) -> PyResult<()> {
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

    fn append_base(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LvalChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LvalLabel::Base), native_child));
        Ok(())
    }

    fn extend_base(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LvalChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LvalLabel::Base), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_base(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LvalLabel::Base))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_base(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LvalLabel::Base) {
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
                "Expected one base child but have {count}"
            )));
        }
        first.expect("invariant: Lval.child_base: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_base(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LvalLabel::Base) {
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
                "Expected at most one base child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_inner(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LvalChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LvalLabel::Inner), native_child));
        Ok(())
    }

    fn extend_inner(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LvalChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LvalLabel::Inner), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inner(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LvalLabel::Inner))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inner(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LvalLabel::Inner) {
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
                "Expected one inner child but have {count}"
            )));
        }
        first.expect("invariant: Lval.child_inner: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inner(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LvalLabel::Inner) {
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
                "Expected at most one inner child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyLval>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyLval> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Lval'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Lval(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// RvalLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Rval_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `RvalLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Rval_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RvalLabel {
    #[pyo3(name = "BASE")]
    Base,
    #[pyo3(name = "INNER")]
    Inner,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RvalLabel {
    Base,
    Inner,
}

#[cfg(feature = "python")]
#[pymethods]
impl RvalLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            RvalLabel::Base => "Rval.Label.BASE",
            RvalLabel::Inner => "Rval.Label.INNER",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RvalLabel>() {
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

/// Child value enum for `Rval` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum RvalChild {
    Lval(Shared<Lval>),
    Num(Shared<Num>),
}

impl PartialEq for RvalChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (RvalChild::Lval(a), RvalChild::Lval(b)) => a == b,
            (RvalChild::Num(a), RvalChild::Num(b)) => a == b,
            _ => false,
        }
    }
}

impl RvalChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Lval(s) => Some(DropWorklistItem::Lval(s)),
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
        }
    }
}

#[cfg(feature = "python")]
impl RvalChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Lval(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyLval { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyLval>() {
            let handle: PyRef<PyLval> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Lval(shared));
        }
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Rval: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Rval
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Rval`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Rval {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RvalLabel>, RvalChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Rval {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Rval")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Rval {
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

impl PartialEq for Rval {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Rval {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Rval {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Rval
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
    pub fn children(&self) -> &[(Option<RvalLabel>, RvalChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<RvalLabel>, child: RvalChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<RvalLabel>, RvalChild), CstError> {
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

    /// Return an iterator over `Shared<Num>` children labelled `base`.
    ///
    /// Off-type variants stored under the `base` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_base(&self) -> impl Iterator<Item = &Shared<Num>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base))
            .filter_map(|(_, child)| match child {
                RvalChild::Num(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `base`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_base(&self) -> Result<&Shared<Num>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RvalChild::Num(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "base" }),
            },
            _ => Err(CstError::ChildCount {
                label: "base",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `base`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_base(&self) -> Result<Option<&Shared<Num>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RvalChild::Num(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "base" }),
            },
            _ => Err(CstError::ChildCount {
                label: "base",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base))
                    .count(),
            }),
        }
    }

    /// Append a child with label `base`, accepting `Num` or `Shared<Num>`.
    pub fn append_base(&mut self, child: impl Into<Shared<Num>>) {
        self.children.push((Some(RvalLabel::Base), RvalChild::Num(child.into())));
    }

    /// Append multiple children with label `base`.
    pub fn extend_base(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Num>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RvalLabel::Base), RvalChild::Num(c.into()))));
    }

    /// Return an iterator over `Shared<Lval>` children labelled `inner`.
    ///
    /// Off-type variants stored under the `inner` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_inner(&self) -> impl Iterator<Item = &Shared<Lval>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner))
            .filter_map(|(_, child)| match child {
                RvalChild::Lval(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `inner`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inner(&self) -> Result<&Shared<Lval>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RvalChild::Lval(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `inner`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inner(&self) -> Result<Option<&Shared<Lval>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RvalChild::Lval(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Append a child with label `inner`, accepting `Lval` or `Shared<Lval>`.
    pub fn append_inner(&mut self, child: impl Into<Shared<Lval>>) {
        self.children.push((Some(RvalLabel::Inner), RvalChild::Lval(child.into())));
    }

    /// Append multiple children with label `inner`.
    pub fn extend_inner(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Lval>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RvalLabel::Inner), RvalChild::Lval(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Rval")]
pub struct PyRval {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Rval>,
}

#[cfg(feature = "python")]
impl PyRval {
    /// Return a reference to the inner `Shared<Rval>`.
    pub fn shared(&self) -> &Shared<Rval> {
        &self.inner
    }

    /// Wrap a `Shared<Rval>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Rval>) -> PyResult<Py<PyRval>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyRval { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyRval>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyRval {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyRval>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Rval {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyRval { inner: shared };
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
        NodeKind::Rval
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RvalLabel::type_object(py).into_any().unbind())
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
        let native_child = RvalChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<RvalLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Rval.append: label argument is not a Rval_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RvalLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Rval.extend: label argument is not a Rval_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RvalChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyRval) -> PyResult<()> {
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

    fn append_base(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RvalChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RvalLabel::Base), native_child));
        Ok(())
    }

    fn extend_base(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RvalChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RvalLabel::Base), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_base(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RvalLabel::Base))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_base(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RvalLabel::Base) {
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
                "Expected one base child but have {count}"
            )));
        }
        first.expect("invariant: Rval.child_base: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_base(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RvalLabel::Base) {
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
                "Expected at most one base child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_inner(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RvalChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RvalLabel::Inner), native_child));
        Ok(())
    }

    fn extend_inner(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RvalChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RvalLabel::Inner), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inner(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RvalLabel::Inner))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inner(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RvalLabel::Inner) {
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
                "Expected one inner child but have {count}"
            )));
        }
        first.expect("invariant: Rval.child_inner: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inner(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RvalLabel::Inner) {
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
                "Expected at most one inner child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyRval>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyRval> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Rval'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Rval(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ArrowLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Arrow_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ArrowLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Arrow_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ArrowLabel {
    #[pyo3(name = "TARGET")]
    Target,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ArrowLabel {
    Target,
}

#[cfg(feature = "python")]
#[pymethods]
impl ArrowLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ArrowLabel::Target => "Arrow.Label.TARGET",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ArrowLabel>() {
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

/// Child value enum for `Arrow` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ArrowChild {
    Name(Shared<Name>),
}

impl PartialEq for ArrowChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ArrowChild::Name(a), ArrowChild::Name(b)) => a == b,
        }
    }
}

impl ArrowChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ArrowChild {
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
            "Arrow: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Arrow
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Arrow`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Arrow {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ArrowLabel>, ArrowChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Arrow {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Arrow")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Arrow {
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

impl PartialEq for Arrow {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Arrow {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Arrow {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Arrow
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
    pub fn children(&self) -> &[(Option<ArrowLabel>, ArrowChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ArrowLabel>, child: ArrowChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ArrowLabel>, ArrowChild), CstError> {
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

    /// Return an iterator over `Shared<Name>` children labelled `target`.
    ///
    /// Off-type variants stored under the `target` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_target(&self) -> impl Iterator<Item = &Shared<Name>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target))
            .map(|(_, child)| match child { ArrowChild::Name(s) => s })
    }

    /// Return the single child labelled `target`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_target(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ArrowChild::Name(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "target",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `target`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_target(&self) -> Result<Option<&Shared<Name>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ArrowChild::Name(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "target",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target))
                    .count(),
            }),
        }
    }

    /// Append a child with label `target`, accepting `Name` or `Shared<Name>`.
    pub fn append_target(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(ArrowLabel::Target), ArrowChild::Name(child.into())));
    }

    /// Append multiple children with label `target`.
    pub fn extend_target(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ArrowLabel::Target), ArrowChild::Name(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Arrow")]
pub struct PyArrow {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Arrow>,
}

#[cfg(feature = "python")]
impl PyArrow {
    /// Return a reference to the inner `Shared<Arrow>`.
    pub fn shared(&self) -> &Shared<Arrow> {
        &self.inner
    }

    /// Wrap a `Shared<Arrow>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Arrow>) -> PyResult<Py<PyArrow>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyArrow { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyArrow>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyArrow {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyArrow>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Arrow {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyArrow { inner: shared };
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
        NodeKind::Arrow
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ArrowLabel::type_object(py).into_any().unbind())
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
        let native_child = ArrowChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ArrowLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Arrow.append: label argument is not a Arrow_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ArrowLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Arrow.extend: label argument is not a Arrow_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ArrowChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyArrow) -> PyResult<()> {
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

    fn append_target(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ArrowChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ArrowLabel::Target), native_child));
        Ok(())
    }

    fn extend_target(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ArrowChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ArrowLabel::Target), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_target(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ArrowLabel::Target))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_target(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ArrowLabel::Target) {
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
                "Expected one target child but have {count}"
            )));
        }
        first.expect("invariant: Arrow.child_target: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_target(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ArrowLabel::Target) {
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
                "Expected at most one target child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyArrow>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyArrow> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Arrow'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Arrow(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// LatinWordLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `LatinWord_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `LatinWordLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "LatinWord_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LatinWordLabel {
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LatinWordLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl LatinWordLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LatinWordLabel::Value => "LatinWord.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LatinWordLabel>() {
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

/// Child value enum for `LatinWord` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum LatinWordChild {
    Span(Span),
}

impl PartialEq for LatinWordChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (LatinWordChild::Span(a), LatinWordChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl LatinWordChild {
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
            "LatinWord: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// LatinWord
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `LatinWord`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct LatinWord {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LatinWordLabel>, LatinWordChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for LatinWord {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("LatinWord")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for LatinWord {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl LatinWord {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        LatinWord {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::LatinWord
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
    pub fn children(&self) -> &[(Option<LatinWordLabel>, LatinWordChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<LatinWordLabel>, child: LatinWordChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<LatinWordLabel>, LatinWordChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value))
            .map(|(_, child)| match child { LatinWordChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LatinWordChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value))
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
            .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LatinWordChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(LatinWordLabel::Value), LatinWordChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LatinWordLabel::Value), LatinWordChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "LatinWord")]
pub struct PyLatinWord {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<LatinWord>,
}

#[cfg(feature = "python")]
impl PyLatinWord {
    /// Return a reference to the inner `Shared<LatinWord>`.
    pub fn shared(&self) -> &Shared<LatinWord> {
        &self.inner
    }

    /// Wrap a `Shared<LatinWord>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<LatinWord>) -> PyResult<Py<PyLatinWord>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyLatinWord { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyLatinWord>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyLatinWord {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyLatinWord>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = LatinWord {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyLatinWord { inner: shared };
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
        NodeKind::LatinWord
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(LatinWordLabel::type_object(py).into_any().unbind())
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
        let native_child = LatinWordChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LatinWordLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LatinWord.append: label argument is not a LatinWord_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LatinWordLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LatinWord.extend: label argument is not a LatinWord_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LatinWordChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyLatinWord) -> PyResult<()> {
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
        let native_child = LatinWordChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LatinWordLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LatinWordChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LatinWordLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(LatinWordLabel::Value))
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
                if *lbl == Some(LatinWordLabel::Value) {
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
        first.expect("invariant: LatinWord.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(LatinWordLabel::Value) {
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
        if !other.is_instance_of::<PyLatinWord>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyLatinWord> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'LatinWord'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "LatinWord(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// TaggedLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Tagged_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `TaggedLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Tagged_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TaggedLabel {
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TaggedLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl TaggedLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            TaggedLabel::Value => "Tagged.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<TaggedLabel>() {
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

/// Child value enum for `Tagged` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum TaggedChild {
    Span(Span),
}

impl PartialEq for TaggedChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (TaggedChild::Span(a), TaggedChild::Span(b)) => a == b,
        }
    }
}

#[cfg(feature = "python")]
impl TaggedChild {
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
            "Tagged: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Tagged
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Tagged`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Tagged {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<TaggedLabel>, TaggedChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Tagged {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Tagged")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Tagged {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Tagged {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Tagged {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Tagged
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
    pub fn children(&self) -> &[(Option<TaggedLabel>, TaggedChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<TaggedLabel>, child: TaggedChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<TaggedLabel>, TaggedChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value))
            .map(|(_, child)| match child { TaggedChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TaggedChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value))
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
            .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TaggedChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(TaggedLabel::Value), TaggedChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(TaggedLabel::Value), TaggedChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Tagged")]
pub struct PyTagged {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Tagged>,
}

#[cfg(feature = "python")]
impl PyTagged {
    /// Return a reference to the inner `Shared<Tagged>`.
    pub fn shared(&self) -> &Shared<Tagged> {
        &self.inner
    }

    /// Wrap a `Shared<Tagged>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Tagged>) -> PyResult<Py<PyTagged>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyTagged { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyTagged>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyTagged {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyTagged>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Tagged {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyTagged { inner: shared };
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
        NodeKind::Tagged
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(TaggedLabel::type_object(py).into_any().unbind())
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
        let native_child = TaggedChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<TaggedLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Tagged.append: label argument is not a Tagged_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<TaggedLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Tagged.extend: label argument is not a Tagged_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TaggedChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyTagged) -> PyResult<()> {
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
        let native_child = TaggedChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TaggedLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TaggedChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TaggedLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(TaggedLabel::Value))
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
                if *lbl == Some(TaggedLabel::Value) {
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
        first.expect("invariant: Tagged.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(TaggedLabel::Value) {
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
        if !other.is_instance_of::<PyTagged>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyTagged> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Tagged'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Tagged(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// ValLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Val_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ValLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Val_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ValLabel {
    #[pyo3(name = "ITEM")]
    Item,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ValLabel {
    Item,
}

#[cfg(feature = "python")]
#[pymethods]
impl ValLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ValLabel::Item => "Val.Label.ITEM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ValLabel>() {
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

/// Child value enum for `Val` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ValChild {
    Span(Span),
    Name(Shared<Name>),
    Num(Shared<Num>),
}

impl PartialEq for ValChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ValChild::Span(a), ValChild::Span(b)) => a == b,
            (ValChild::Name(a), ValChild::Name(b)) => a == b,
            (ValChild::Num(a), ValChild::Num(b)) => a == b,
            _ => false,
        }
    }
}

impl ValChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ValChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                span_to_pyobject(py, s)
            }
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Val: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Val
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Val`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Val {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ValLabel>, ValChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Val {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Val")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Val {
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

impl PartialEq for Val {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Val {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Val {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Val
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
    pub fn children(&self) -> &[(Option<ValLabel>, ValChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ValLabel>, child: ValChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ValLabel>, ValChild), CstError> {
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

    /// Return an iterator over children labelled `item`.
    pub fn children_item(&self) -> impl Iterator<Item = &ValChild> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValLabel::Item))
            .map(|(_, child)| child)
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&ValChild, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValLabel::Item));
        match (matching.next(), matching.next()) {
            (Some((_, child)), None) => Ok(child),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ValLabel::Item))
                    .count();
                Err(CstError::ChildCount {
                    label: "item",
                    expected: "1",
                    found: count,
                })
            }
        }
    }

    /// Return the optional child labelled `item`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_item(&self) -> Result<Option<&ValChild>, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValLabel::Item));
        match (matching.next(), matching.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => Ok(Some(child)),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ValLabel::Item))
                    .count();
                Err(CstError::ChildCount {
                    label: "item",
                    expected: "0 or 1",
                    found: count,
                })
            }
        }
    }

    /// Append a child with label `item` (any child enum variant).
    pub fn append_item(&mut self, child: ValChild) {
        self.children.push((Some(ValLabel::Item), child));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = ValChild>) {
        self.children.extend(children.into_iter().map(|c| (Some(ValLabel::Item), c)));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Val")]
pub struct PyVal {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Val>,
}

#[cfg(feature = "python")]
impl PyVal {
    /// Return a reference to the inner `Shared<Val>`.
    pub fn shared(&self) -> &Shared<Val> {
        &self.inner
    }

    /// Wrap a `Shared<Val>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Val>) -> PyResult<Py<PyVal>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyVal { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyVal>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyVal {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyVal>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Val {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyVal { inner: shared };
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
        NodeKind::Val
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ValLabel::type_object(py).into_any().unbind())
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
        let native_child = ValChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Val.append: label argument is not a Val_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Val.extend: label argument is not a Val_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ValChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyVal) -> PyResult<()> {
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
        let native_child = ValChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ValLabel::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ValChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ValLabel::Item), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(ValLabel::Item))
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
                if *lbl == Some(ValLabel::Item) {
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
        first.expect("invariant: Val.child_item: count==1 but first==None; logic error")
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
                if *lbl == Some(ValLabel::Item) {
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
        if !other.is_instance_of::<PyVal>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyVal> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Val'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Val(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// LeadingWsLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `LeadingWs_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `LeadingWsLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "LeadingWs_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LeadingWsLabel {
    #[pyo3(name = "NUM")]
    Num,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LeadingWsLabel {
    Num,
}

#[cfg(feature = "python")]
#[pymethods]
impl LeadingWsLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LeadingWsLabel::Num => "LeadingWs.Label.NUM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LeadingWsLabel>() {
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

/// Child value enum for `LeadingWs` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum LeadingWsChild {
    Num(Shared<Num>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for LeadingWsChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (LeadingWsChild::Num(a), LeadingWsChild::Num(b)) => a == b,
            (LeadingWsChild::Trivia(a), LeadingWsChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl LeadingWsChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl LeadingWsChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
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
            "LeadingWs: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// LeadingWs
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `LeadingWs`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct LeadingWs {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LeadingWsLabel>, LeadingWsChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for LeadingWs {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("LeadingWs")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for LeadingWs {
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

impl PartialEq for LeadingWs {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl LeadingWs {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        LeadingWs {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::LeadingWs
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
    pub fn children(&self) -> &[(Option<LeadingWsLabel>, LeadingWsChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<LeadingWsLabel>, child: LeadingWsChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<LeadingWsLabel>, LeadingWsChild), CstError> {
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

    /// Return an iterator over `Shared<Num>` children labelled `num`.
    ///
    /// Off-type variants stored under the `num` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_num(&self) -> impl Iterator<Item = &Shared<Num>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num))
            .filter_map(|(_, child)| match child {
                LeadingWsChild::Num(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `num`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_num(&self) -> Result<&Shared<Num>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LeadingWsChild::Num(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "num" }),
            },
            _ => Err(CstError::ChildCount {
                label: "num",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `num`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_num(&self) -> Result<Option<&Shared<Num>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LeadingWsChild::Num(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "num" }),
            },
            _ => Err(CstError::ChildCount {
                label: "num",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num))
                    .count(),
            }),
        }
    }

    /// Append a child with label `num`, accepting `Num` or `Shared<Num>`.
    pub fn append_num(&mut self, child: impl Into<Shared<Num>>) {
        self.children.push((Some(LeadingWsLabel::Num), LeadingWsChild::Num(child.into())));
    }

    /// Append multiple children with label `num`.
    pub fn extend_num(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Num>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(LeadingWsLabel::Num), LeadingWsChild::Num(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "LeadingWs")]
pub struct PyLeadingWs {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<LeadingWs>,
}

#[cfg(feature = "python")]
impl PyLeadingWs {
    /// Return a reference to the inner `Shared<LeadingWs>`.
    pub fn shared(&self) -> &Shared<LeadingWs> {
        &self.inner
    }

    /// Wrap a `Shared<LeadingWs>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<LeadingWs>) -> PyResult<Py<PyLeadingWs>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyLeadingWs { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyLeadingWs>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyLeadingWs {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyLeadingWs>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = LeadingWs {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyLeadingWs { inner: shared };
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
        NodeKind::LeadingWs
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(LeadingWsLabel::type_object(py).into_any().unbind())
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
        let native_child = LeadingWsChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LeadingWsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LeadingWs.append: label argument is not a LeadingWs_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LeadingWsLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LeadingWs.extend: label argument is not a LeadingWs_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LeadingWsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyLeadingWs) -> PyResult<()> {
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

    fn append_num(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LeadingWsChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LeadingWsLabel::Num), native_child));
        Ok(())
    }

    fn extend_num(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LeadingWsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LeadingWsLabel::Num), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_num(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LeadingWsLabel::Num))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_num(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LeadingWsLabel::Num) {
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
                "Expected one num child but have {count}"
            )));
        }
        first.expect("invariant: LeadingWs.child_num: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_num(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LeadingWsLabel::Num) {
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
                "Expected at most one num child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyLeadingWs>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyLeadingWs> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'LeadingWs'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "LeadingWs(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// GroupedLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Grouped_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `GroupedLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Grouped_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum GroupedLabel {
    #[pyo3(name = "LEFT")]
    Left,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum GroupedLabel {
    Left,
}

#[cfg(feature = "python")]
#[pymethods]
impl GroupedLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            GroupedLabel::Left => "Grouped.Label.LEFT",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<GroupedLabel>() {
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

/// Child value enum for `Grouped` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum GroupedChild {
    Name(Shared<Name>),
    Num(Shared<Num>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for GroupedChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (GroupedChild::Name(a), GroupedChild::Name(b)) => a == b,
            (GroupedChild::Num(a), GroupedChild::Num(b)) => a == b,
            (GroupedChild::Trivia(a), GroupedChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl GroupedChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl GroupedChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
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
            "Grouped: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Grouped
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Grouped`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Grouped {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<GroupedLabel>, GroupedChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Grouped {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Grouped")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Grouped {
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

impl PartialEq for Grouped {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Grouped {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Grouped {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Grouped
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
    pub fn children(&self) -> &[(Option<GroupedLabel>, GroupedChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<GroupedLabel>, child: GroupedChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<GroupedLabel>, GroupedChild), CstError> {
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

    /// Return an iterator over children labelled `left`.
    pub fn children_left(&self) -> impl Iterator<Item = &GroupedChild> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left))
            .map(|(_, child)| child)
    }

    /// Return the single child labelled `left`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_left(&self) -> Result<&GroupedChild, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left));
        match (matching.next(), matching.next()) {
            (Some((_, child)), None) => Ok(child),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left))
                    .count();
                Err(CstError::ChildCount {
                    label: "left",
                    expected: "1",
                    found: count,
                })
            }
        }
    }

    /// Return the optional child labelled `left`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_left(&self) -> Result<Option<&GroupedChild>, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left));
        match (matching.next(), matching.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => Ok(Some(child)),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left))
                    .count();
                Err(CstError::ChildCount {
                    label: "left",
                    expected: "0 or 1",
                    found: count,
                })
            }
        }
    }

    /// Append a child with label `left` (any child enum variant).
    pub fn append_left(&mut self, child: GroupedChild) {
        self.children.push((Some(GroupedLabel::Left), child));
    }

    /// Append multiple children with label `left`.
    pub fn extend_left(&mut self, children: impl IntoIterator<Item = GroupedChild>) {
        self.children.extend(children.into_iter().map(|c| (Some(GroupedLabel::Left), c)));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Grouped")]
pub struct PyGrouped {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Grouped>,
}

#[cfg(feature = "python")]
impl PyGrouped {
    /// Return a reference to the inner `Shared<Grouped>`.
    pub fn shared(&self) -> &Shared<Grouped> {
        &self.inner
    }

    /// Wrap a `Shared<Grouped>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Grouped>) -> PyResult<Py<PyGrouped>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyGrouped { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyGrouped>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyGrouped {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyGrouped>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Grouped {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyGrouped { inner: shared };
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
        NodeKind::Grouped
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(GroupedLabel::type_object(py).into_any().unbind())
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
        let native_child = GroupedChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<GroupedLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Grouped.append: label argument is not a Grouped_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<GroupedLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Grouped.extend: label argument is not a Grouped_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GroupedChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyGrouped) -> PyResult<()> {
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

    fn append_left(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = GroupedChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(GroupedLabel::Left), native_child));
        Ok(())
    }

    fn extend_left(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GroupedChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(GroupedLabel::Left), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_left(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(GroupedLabel::Left))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_left(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(GroupedLabel::Left) {
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
                "Expected one left child but have {count}"
            )));
        }
        first.expect("invariant: Grouped.child_left: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_left(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(GroupedLabel::Left) {
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
                "Expected at most one left child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyGrouped>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyGrouped> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Grouped'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Grouped(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// RecViaSubLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `RecViaSub_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `RecViaSubLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "RecViaSub_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RecViaSubLabel {
    #[pyo3(name = "INNER")]
    Inner,
    #[pyo3(name = "SUFFIX")]
    Suffix,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RecViaSubLabel {
    Inner,
    Suffix,
}

#[cfg(feature = "python")]
#[pymethods]
impl RecViaSubLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            RecViaSubLabel::Inner => "RecViaSub.Label.INNER",
            RecViaSubLabel::Suffix => "RecViaSub.Label.SUFFIX",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RecViaSubLabel>() {
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

/// Child value enum for `RecViaSub` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum RecViaSubChild {
    Atom(Shared<Atom>),
    Name(Shared<Name>),
    RecViaSub(Shared<RecViaSub>),
}

impl PartialEq for RecViaSubChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (RecViaSubChild::Atom(a), RecViaSubChild::Atom(b)) => a == b,
            (RecViaSubChild::Name(a), RecViaSubChild::Name(b)) => a == b,
            (RecViaSubChild::RecViaSub(a), RecViaSubChild::RecViaSub(b)) => a == b,
            _ => false,
        }
    }
}

impl RecViaSubChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Atom(s) => Some(DropWorklistItem::Atom(s)),
            Self::Name(s) => Some(DropWorklistItem::Name(s)),
            Self::RecViaSub(s) => Some(DropWorklistItem::RecViaSub(s)),
        }
    }
}

#[cfg(feature = "python")]
impl RecViaSubChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Atom(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAtom { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Name(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyName { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::RecViaSub(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyRecViaSub { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAtom>() {
            let handle: PyRef<PyAtom> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Atom(shared));
        }
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
        if obj.is_instance_of::<PyRecViaSub>() {
            let handle: PyRef<PyRecViaSub> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::RecViaSub(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "RecViaSub: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// RecViaSub
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `RecViaSub`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct RecViaSub {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RecViaSubLabel>, RecViaSubChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for RecViaSub {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RecViaSub")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for RecViaSub {
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

impl PartialEq for RecViaSub {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl RecViaSub {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        RecViaSub {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::RecViaSub
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
    pub fn children(&self) -> &[(Option<RecViaSubLabel>, RecViaSubChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<RecViaSubLabel>, child: RecViaSubChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<RecViaSubLabel>, RecViaSubChild), CstError> {
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

    /// Return an iterator over children labelled `inner`.
    pub fn children_inner(&self) -> impl Iterator<Item = &RecViaSubChild> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner))
            .map(|(_, child)| child)
    }

    /// Return the single child labelled `inner`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inner(&self) -> Result<&RecViaSubChild, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner));
        match (matching.next(), matching.next()) {
            (Some((_, child)), None) => Ok(child),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner))
                    .count();
                Err(CstError::ChildCount {
                    label: "inner",
                    expected: "1",
                    found: count,
                })
            }
        }
    }

    /// Return the optional child labelled `inner`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inner(&self) -> Result<Option<&RecViaSubChild>, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner));
        match (matching.next(), matching.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => Ok(Some(child)),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner))
                    .count();
                Err(CstError::ChildCount {
                    label: "inner",
                    expected: "0 or 1",
                    found: count,
                })
            }
        }
    }

    /// Append a child with label `inner` (any child enum variant).
    pub fn append_inner(&mut self, child: RecViaSubChild) {
        self.children.push((Some(RecViaSubLabel::Inner), child));
    }

    /// Append multiple children with label `inner`.
    pub fn extend_inner(&mut self, children: impl IntoIterator<Item = RecViaSubChild>) {
        self.children.extend(children.into_iter().map(|c| (Some(RecViaSubLabel::Inner), c)));
    }

    /// Return an iterator over `Shared<Name>` children labelled `suffix`.
    ///
    /// Off-type variants stored under the `suffix` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_suffix(&self) -> impl Iterator<Item = &Shared<Name>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix))
            .filter_map(|(_, child)| match child {
                RecViaSubChild::Name(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `suffix`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_suffix(&self) -> Result<&Shared<Name>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RecViaSubChild::Name(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "suffix" }),
            },
            _ => Err(CstError::ChildCount {
                label: "suffix",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `suffix`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_suffix(&self) -> Result<Option<&Shared<Name>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RecViaSubChild::Name(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "suffix" }),
            },
            _ => Err(CstError::ChildCount {
                label: "suffix",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix))
                    .count(),
            }),
        }
    }

    /// Append a child with label `suffix`, accepting `Name` or `Shared<Name>`.
    pub fn append_suffix(&mut self, child: impl Into<Shared<Name>>) {
        self.children.push((Some(RecViaSubLabel::Suffix), RecViaSubChild::Name(child.into())));
    }

    /// Append multiple children with label `suffix`.
    pub fn extend_suffix(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Name>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RecViaSubLabel::Suffix), RecViaSubChild::Name(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "RecViaSub")]
pub struct PyRecViaSub {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<RecViaSub>,
}

#[cfg(feature = "python")]
impl PyRecViaSub {
    /// Return a reference to the inner `Shared<RecViaSub>`.
    pub fn shared(&self) -> &Shared<RecViaSub> {
        &self.inner
    }

    /// Wrap a `Shared<RecViaSub>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<RecViaSub>) -> PyResult<Py<PyRecViaSub>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyRecViaSub { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyRecViaSub>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyRecViaSub {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyRecViaSub>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = RecViaSub {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyRecViaSub { inner: shared };
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
        NodeKind::RecViaSub
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RecViaSubLabel::type_object(py).into_any().unbind())
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
        let native_child = RecViaSubChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<RecViaSubLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "RecViaSub.append: label argument is not a RecViaSub_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RecViaSubLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "RecViaSub.extend: label argument is not a RecViaSub_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RecViaSubChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyRecViaSub) -> PyResult<()> {
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

    fn append_inner(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RecViaSubChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RecViaSubLabel::Inner), native_child));
        Ok(())
    }

    fn extend_inner(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RecViaSubChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RecViaSubLabel::Inner), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inner(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Inner))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inner(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RecViaSubLabel::Inner) {
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
                "Expected one inner child but have {count}"
            )));
        }
        first.expect("invariant: RecViaSub.child_inner: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inner(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RecViaSubLabel::Inner) {
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
                "Expected at most one inner child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_suffix(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RecViaSubChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RecViaSubLabel::Suffix), native_child));
        Ok(())
    }

    fn extend_suffix(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RecViaSubChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RecViaSubLabel::Suffix), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_suffix(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RecViaSubLabel::Suffix))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_suffix(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RecViaSubLabel::Suffix) {
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
                "Expected one suffix child but have {count}"
            )));
        }
        first.expect("invariant: RecViaSub.child_suffix: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_suffix(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RecViaSubLabel::Suffix) {
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
                "Expected at most one suffix child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyRecViaSub>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyRecViaSub> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'RecViaSub'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "RecViaSub(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// NestLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Nest_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `NestLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Nest_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NestLabel {
    #[pyo3(name = "INNER")]
    Inner,
    #[pyo3(name = "LEAF")]
    Leaf,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NestLabel {
    Inner,
    Leaf,
}

#[cfg(feature = "python")]
#[pymethods]
impl NestLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            NestLabel::Inner => "Nest.Label.INNER",
            NestLabel::Leaf => "Nest.Label.LEAF",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<NestLabel>() {
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

/// Child value enum for `Nest` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum NestChild {
    Nest(Shared<Nest>),
    Num(Shared<Num>),
}

impl PartialEq for NestChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (NestChild::Nest(a), NestChild::Nest(b)) => a == b,
            (NestChild::Num(a), NestChild::Num(b)) => a == b,
            _ => false,
        }
    }
}

impl NestChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Nest(s) => Some(DropWorklistItem::Nest(s)),
            Self::Num(s) => Some(DropWorklistItem::Num(s)),
        }
    }
}

#[cfg(feature = "python")]
impl NestChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Nest(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNest { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Num(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNest>() {
            let handle: PyRef<PyNest> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Nest(shared));
        }
        if obj.is_instance_of::<PyNum>() {
            let handle: PyRef<PyNum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Num(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "Nest: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Nest
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Nest`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Nest {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<NestLabel>, NestChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Nest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Nest")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Nest {
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

impl PartialEq for Nest {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Nest {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Nest {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Nest
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
    pub fn children(&self) -> &[(Option<NestLabel>, NestChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<NestLabel>, child: NestChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<NestLabel>, NestChild), CstError> {
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

    /// Return an iterator over `Shared<Nest>` children labelled `inner`.
    ///
    /// Off-type variants stored under the `inner` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_inner(&self) -> impl Iterator<Item = &Shared<Nest>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner))
            .filter_map(|(_, child)| match child {
                NestChild::Nest(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `inner`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inner(&self) -> Result<&Shared<Nest>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NestChild::Nest(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `inner`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inner(&self) -> Result<Option<&Shared<Nest>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NestChild::Nest(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "inner" }),
            },
            _ => Err(CstError::ChildCount {
                label: "inner",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner))
                    .count(),
            }),
        }
    }

    /// Append a child with label `inner`, accepting `Nest` or `Shared<Nest>`.
    pub fn append_inner(&mut self, child: impl Into<Shared<Nest>>) {
        self.children.push((Some(NestLabel::Inner), NestChild::Nest(child.into())));
    }

    /// Append multiple children with label `inner`.
    pub fn extend_inner(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Nest>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(NestLabel::Inner), NestChild::Nest(c.into()))));
    }

    /// Return an iterator over `Shared<Num>` children labelled `leaf`.
    ///
    /// Off-type variants stored under the `leaf` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_leaf(&self) -> impl Iterator<Item = &Shared<Num>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf))
            .filter_map(|(_, child)| match child {
                NestChild::Num(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `leaf`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_leaf(&self) -> Result<&Shared<Num>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NestChild::Num(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "leaf" }),
            },
            _ => Err(CstError::ChildCount {
                label: "leaf",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `leaf`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_leaf(&self) -> Result<Option<&Shared<Num>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NestChild::Num(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "leaf" }),
            },
            _ => Err(CstError::ChildCount {
                label: "leaf",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf))
                    .count(),
            }),
        }
    }

    /// Append a child with label `leaf`, accepting `Num` or `Shared<Num>`.
    pub fn append_leaf(&mut self, child: impl Into<Shared<Num>>) {
        self.children.push((Some(NestLabel::Leaf), NestChild::Num(child.into())));
    }

    /// Append multiple children with label `leaf`.
    pub fn extend_leaf(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Num>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(NestLabel::Leaf), NestChild::Num(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Nest")]
pub struct PyNest {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Nest>,
}

#[cfg(feature = "python")]
impl PyNest {
    /// Return a reference to the inner `Shared<Nest>`.
    pub fn shared(&self) -> &Shared<Nest> {
        &self.inner
    }

    /// Wrap a `Shared<Nest>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Nest>) -> PyResult<Py<PyNest>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyNest { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyNest>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyNest {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyNest>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Nest {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyNest { inner: shared };
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
        NodeKind::Nest
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(NestLabel::type_object(py).into_any().unbind())
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
        let native_child = NestChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<NestLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Nest.append: label argument is not a Nest_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<NestLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Nest.extend: label argument is not a Nest_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyNest) -> PyResult<()> {
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

    fn append_inner(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NestChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NestLabel::Inner), native_child));
        Ok(())
    }

    fn extend_inner(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NestLabel::Inner), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inner(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NestLabel::Inner))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inner(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestLabel::Inner) {
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
                "Expected one inner child but have {count}"
            )));
        }
        first.expect("invariant: Nest.child_inner: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inner(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestLabel::Inner) {
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
                "Expected at most one inner child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_leaf(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NestChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NestLabel::Leaf), native_child));
        Ok(())
    }

    fn extend_leaf(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NestLabel::Leaf), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_leaf(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NestLabel::Leaf))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_leaf(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestLabel::Leaf) {
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
                "Expected one leaf child but have {count}"
            )));
        }
        first.expect("invariant: Nest.child_leaf: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_leaf(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestLabel::Leaf) {
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
                "Expected at most one leaf child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyNest>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyNest> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Nest'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Nest(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// NestSumLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `NestSum_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `NestSumLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "NestSum_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NestSumLabel {
    #[pyo3(name = "FIRST")]
    First,
    #[pyo3(name = "LHS")]
    Lhs,
    #[pyo3(name = "RHS")]
    Rhs,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NestSumLabel {
    First,
    Lhs,
    Rhs,
}

#[cfg(feature = "python")]
#[pymethods]
impl NestSumLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            NestSumLabel::First => "NestSum.Label.FIRST",
            NestSumLabel::Lhs => "NestSum.Label.LHS",
            NestSumLabel::Rhs => "NestSum.Label.RHS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<NestSumLabel>() {
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

/// Child value enum for `NestSum` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum NestSumChild {
    Nest(Shared<Nest>),
    NestSum(Shared<NestSum>),
}

impl PartialEq for NestSumChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (NestSumChild::Nest(a), NestSumChild::Nest(b)) => a == b,
            (NestSumChild::NestSum(a), NestSumChild::NestSum(b)) => a == b,
            _ => false,
        }
    }
}

impl NestSumChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Nest(s) => Some(DropWorklistItem::Nest(s)),
            Self::NestSum(s) => Some(DropWorklistItem::NestSum(s)),
        }
    }
}

#[cfg(feature = "python")]
impl NestSumChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Nest(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNest { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::NestSum(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyNestSum { inner: shared.clone() };
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
        if obj.is_instance_of::<PyNest>() {
            let handle: PyRef<PyNest> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Nest(shared));
        }
        if obj.is_instance_of::<PyNestSum>() {
            let handle: PyRef<PyNestSum> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::NestSum(shared));
        }
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "NestSum: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// NestSum
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `NestSum`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct NestSum {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<NestSumLabel>, NestSumChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for NestSum {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("NestSum")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for NestSum {
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

impl PartialEq for NestSum {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl NestSum {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        NestSum {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::NestSum
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
    pub fn children(&self) -> &[(Option<NestSumLabel>, NestSumChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<NestSumLabel>, child: NestSumChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<NestSumLabel>, NestSumChild), CstError> {
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

    /// Return an iterator over `Shared<Nest>` children labelled `first`.
    ///
    /// Off-type variants stored under the `first` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_first(&self) -> impl Iterator<Item = &Shared<Nest>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First))
            .filter_map(|(_, child)| match child {
                NestSumChild::Nest(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `first`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_first(&self) -> Result<&Shared<Nest>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NestSumChild::Nest(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "first" }),
            },
            _ => Err(CstError::ChildCount {
                label: "first",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `first`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_first(&self) -> Result<Option<&Shared<Nest>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NestSumChild::Nest(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "first" }),
            },
            _ => Err(CstError::ChildCount {
                label: "first",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First))
                    .count(),
            }),
        }
    }

    /// Append a child with label `first`, accepting `Nest` or `Shared<Nest>`.
    pub fn append_first(&mut self, child: impl Into<Shared<Nest>>) {
        self.children.push((Some(NestSumLabel::First), NestSumChild::Nest(child.into())));
    }

    /// Append multiple children with label `first`.
    pub fn extend_first(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Nest>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(NestSumLabel::First), NestSumChild::Nest(c.into()))));
    }

    /// Return an iterator over `Shared<NestSum>` children labelled `lhs`.
    ///
    /// Off-type variants stored under the `lhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_lhs(&self) -> impl Iterator<Item = &Shared<NestSum>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs))
            .filter_map(|(_, child)| match child {
                NestSumChild::NestSum(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `lhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_lhs(&self) -> Result<&Shared<NestSum>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NestSumChild::NestSum(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `lhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_lhs(&self) -> Result<Option<&Shared<NestSum>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NestSumChild::NestSum(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "lhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "lhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `lhs`, accepting `NestSum` or `Shared<NestSum>`.
    pub fn append_lhs(&mut self, child: impl Into<Shared<NestSum>>) {
        self.children.push((Some(NestSumLabel::Lhs), NestSumChild::NestSum(child.into())));
    }

    /// Append multiple children with label `lhs`.
    pub fn extend_lhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<NestSum>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(NestSumLabel::Lhs), NestSumChild::NestSum(c.into()))));
    }

    /// Return an iterator over `Shared<Nest>` children labelled `rhs`.
    ///
    /// Off-type variants stored under the `rhs` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_rhs(&self) -> impl Iterator<Item = &Shared<Nest>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs))
            .filter_map(|(_, child)| match child {
                NestSumChild::Nest(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `rhs`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_rhs(&self) -> Result<&Shared<Nest>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                NestSumChild::Nest(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `rhs`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_rhs(&self) -> Result<Option<&Shared<Nest>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                NestSumChild::Nest(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "rhs" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rhs",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs))
                    .count(),
            }),
        }
    }

    /// Append a child with label `rhs`, accepting `Nest` or `Shared<Nest>`.
    pub fn append_rhs(&mut self, child: impl Into<Shared<Nest>>) {
        self.children.push((Some(NestSumLabel::Rhs), NestSumChild::Nest(child.into())));
    }

    /// Append multiple children with label `rhs`.
    pub fn extend_rhs(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Nest>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(NestSumLabel::Rhs), NestSumChild::Nest(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "NestSum")]
pub struct PyNestSum {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<NestSum>,
}

#[cfg(feature = "python")]
impl PyNestSum {
    /// Return a reference to the inner `Shared<NestSum>`.
    pub fn shared(&self) -> &Shared<NestSum> {
        &self.inner
    }

    /// Wrap a `Shared<NestSum>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<NestSum>) -> PyResult<Py<PyNestSum>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyNestSum { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyNestSum>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyNestSum {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyNestSum>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = NestSum {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyNestSum { inner: shared };
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
        NodeKind::NestSum
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(NestSumLabel::type_object(py).into_any().unbind())
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
        let native_child = NestSumChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<NestSumLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "NestSum.append: label argument is not a NestSum_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<NestSumLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "NestSum.extend: label argument is not a NestSum_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestSumChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyNestSum) -> PyResult<()> {
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

    fn append_first(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NestSumChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NestSumLabel::First), native_child));
        Ok(())
    }

    fn extend_first(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestSumChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NestSumLabel::First), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_first(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NestSumLabel::First))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_first(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::First) {
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
                "Expected one first child but have {count}"
            )));
        }
        first.expect("invariant: NestSum.child_first: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_first(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::First) {
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
                "Expected at most one first child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_lhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NestSumChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NestSumLabel::Lhs), native_child));
        Ok(())
    }

    fn extend_lhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestSumChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NestSumLabel::Lhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_lhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Lhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_lhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::Lhs) {
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
                "Expected one lhs child but have {count}"
            )));
        }
        first.expect("invariant: NestSum.child_lhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_lhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::Lhs) {
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
                "Expected at most one lhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_rhs(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = NestSumChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(NestSumLabel::Rhs), native_child));
        Ok(())
    }

    fn extend_rhs(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = NestSumChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(NestSumLabel::Rhs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_rhs(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(NestSumLabel::Rhs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_rhs(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::Rhs) {
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
                "Expected one rhs child but have {count}"
            )));
        }
        first.expect("invariant: NestSum.child_rhs: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_rhs(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(NestSumLabel::Rhs) {
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
                "Expected at most one rhs child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyNestSum>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyNestSum> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'NestSum'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "NestSum(span={span_repr}, children=[<{children_len} child(ren)>])"
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

impl TriviaChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
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
    Atom(Shared<Atom>),
    Expr(Shared<Expr>),
    Lval(Shared<Lval>),
    Name(Shared<Name>),
    Nest(Shared<Nest>),
    NestSum(Shared<NestSum>),
    Num(Shared<Num>),
    RecViaSub(Shared<RecViaSub>),
    Rval(Shared<Rval>),
    Trivia(Shared<Trivia>),
}

impl DropWorklistItem {
    fn drain_into(self, worklist: &mut Vec<DropWorklistItem>) {
        // Each arm: if sole owner, steal children (so the node's Drop early-returns
        // instead of recursing through drop glue); then drop `shared`.
        // count==1 → childless node after steal, trivial drop;
        // count>1 → refcount decrement only. Either way, no recursion.
        match self {
            DropWorklistItem::Atom(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Expr(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Lval(shared) => {
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
            DropWorklistItem::Nest(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::NestSum(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Num(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::RecViaSub(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Rval(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Trivia(shared) => {
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
    module.add_class::<NumLabel>()?;
    module.add_class::<PyNum>()?;
    module.add_class::<NameLabel>()?;
    module.add_class::<PyName>()?;
    module.add_class::<AtomLabel>()?;
    module.add_class::<PyAtom>()?;
    module.add_class::<ParenExprLabel>()?;
    module.add_class::<PyParenExpr>()?;
    module.add_class::<StmtLabel>()?;
    module.add_class::<PyStmt>()?;
    module.add_class::<ItemsLabel>()?;
    module.add_class::<PyItems>()?;
    module.add_class::<OptItemLabel>()?;
    module.add_class::<PyOptItem>()?;
    module.add_class::<ZeroItemsLabel>()?;
    module.add_class::<PyZeroItems>()?;
    module.add_class::<ExprLabel>()?;
    module.add_class::<PyExpr>()?;
    module.add_class::<LvalLabel>()?;
    module.add_class::<PyLval>()?;
    module.add_class::<RvalLabel>()?;
    module.add_class::<PyRval>()?;
    module.add_class::<ArrowLabel>()?;
    module.add_class::<PyArrow>()?;
    module.add_class::<LatinWordLabel>()?;
    module.add_class::<PyLatinWord>()?;
    module.add_class::<TaggedLabel>()?;
    module.add_class::<PyTagged>()?;
    module.add_class::<ValLabel>()?;
    module.add_class::<PyVal>()?;
    module.add_class::<LeadingWsLabel>()?;
    module.add_class::<PyLeadingWs>()?;
    module.add_class::<GroupedLabel>()?;
    module.add_class::<PyGrouped>()?;
    module.add_class::<RecViaSubLabel>()?;
    module.add_class::<PyRecViaSub>()?;
    module.add_class::<NestLabel>()?;
    module.add_class::<PyNest>()?;
    module.add_class::<NestSumLabel>()?;
    module.add_class::<PyNestSum>()?;
    module.add_class::<TriviaLabel>()?;
    module.add_class::<PyTrivia>()?;
    Ok(())
}
