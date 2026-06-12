use fltk_cst_core::CstError;
use fltk_cst_core::Span;
use fltk_cst_core::Shared;
use std::fmt;
#[cfg(feature = "python")]
use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};
#[cfg(feature = "python")]
use fltk_cst_core::registry;
#[cfg(feature = "python")]
use pyo3::exceptions::{PyIndexError, PyTypeError, PyValueError};
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
    #[pyo3(name = "VALUENODE")]
    ValueNode,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Config,
    Entry,
    Operator,
    Identifier,
    Literal,
    ValueNode,
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
            NodeKind::ValueNode => "NodeKind.VALUENODE",
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
// ConfigLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Config_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ConfigLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Config_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ConfigLabel {
    #[pyo3(name = "ENTRY")]
    Entry,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ConfigLabel {
    Entry,
}

#[cfg(feature = "python")]
#[pymethods]
impl ConfigLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ConfigLabel::Entry => "Config.Label.ENTRY",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ConfigLabel>() {
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

/// Child value enum for `Config` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

impl ConfigChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Entry(s) => Some(DropWorklistItem::Entry(s)),
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

/// CST data struct for `Config`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Config {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ConfigLabel>, ConfigChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Config {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Config")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Config {
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

impl PartialEq for Config {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Config {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Config {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Config
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
    pub fn children(&self) -> &[(Option<ConfigLabel>, ConfigChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ConfigLabel>, child: ConfigChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ConfigLabel>, ConfigChild), CstError> {
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

    /// Return an iterator over `Shared<Entry>` children labelled `entry`.
    ///
    /// Off-type variants stored under the `entry` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_entry(&self) -> impl Iterator<Item = &Shared<Entry>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry))
            .map(|(_, child)| match child { ConfigChild::Entry(s) => s })
    }

    /// Return the single child labelled `entry`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_entry(&self) -> Result<&Shared<Entry>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ConfigChild::Entry(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "entry",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `entry`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_entry(&self) -> Result<Option<&Shared<Entry>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ConfigChild::Entry(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "entry",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry))
                    .count(),
            }),
        }
    }

    /// Append a child with label `entry`, accepting `Entry` or `Shared<Entry>`.
    pub fn append_entry(&mut self, child: impl Into<Shared<Entry>>) {
        self.children.push((Some(ConfigLabel::Entry), ConfigChild::Entry(child.into())));
    }

    /// Append multiple children with label `entry`.
    pub fn extend_entry(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Entry>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ConfigLabel::Entry), ConfigChild::Entry(c.into()))));
    }

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<ConfigLabel>, child: ConfigChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<ConfigLabel>, ConfigChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<ConfigLabel>, child: ConfigChild,
    ) -> (Option<ConfigLabel>, ConfigChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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
        Ok(ConfigLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ConfigLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ConfigLabel>() {
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ConfigLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Config.insert: label argument is not a Config_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Config.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ConfigLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Config.replace_at: label argument is not a Config_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Config.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
    }

    fn append_entry(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ConfigLabel::Entry), native_child));
        Ok(())
    }

    fn extend_entry(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ConfigChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ConfigLabel::Entry), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_entry(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ConfigLabel::Entry))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_entry(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ConfigLabel::Entry) {
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
                "Expected one entry child but have {count}"
            )));
        }
        first.expect("invariant: Config.child_entry: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_entry(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ConfigLabel::Entry) {
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
                "Expected at most one entry child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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
// EntryLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Entry_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `EntryLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Entry_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum EntryLabel {
    #[pyo3(name = "KEY")]
    Key,
    #[pyo3(name = "OP")]
    Op,
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum EntryLabel {
    Key,
    Op,
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl EntryLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            EntryLabel::Key => "Entry.Label.KEY",
            EntryLabel::Op => "Entry.Label.OP",
            EntryLabel::Value => "Entry.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<EntryLabel>() {
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

/// Child value enum for `Entry` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

impl EntryChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Identifier(s) => Some(DropWorklistItem::Identifier(s)),
            Self::Literal(s) => Some(DropWorklistItem::Literal(s)),
            Self::Operator(s) => Some(DropWorklistItem::Operator(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
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

/// CST data struct for `Entry`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Entry {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<EntryLabel>, EntryChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Entry {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Entry")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Entry {
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

impl PartialEq for Entry {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Entry {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Entry {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Entry
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
    pub fn children(&self) -> &[(Option<EntryLabel>, EntryChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<EntryLabel>, child: EntryChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<EntryLabel>, EntryChild), CstError> {
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

    /// Return an iterator over `Shared<Identifier>` children labelled `key`.
    ///
    /// Off-type variants stored under the `key` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_key(&self) -> impl Iterator<Item = &Shared<Identifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key))
            .filter_map(|(_, child)| match child {
                EntryChild::Identifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `key`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_key(&self) -> Result<&Shared<Identifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                EntryChild::Identifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "key" }),
            },
            _ => Err(CstError::ChildCount {
                label: "key",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `key`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_key(&self) -> Result<Option<&Shared<Identifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                EntryChild::Identifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "key" }),
            },
            _ => Err(CstError::ChildCount {
                label: "key",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key))
                    .count(),
            }),
        }
    }

    /// Append a child with label `key`, accepting `Identifier` or `Shared<Identifier>`.
    pub fn append_key(&mut self, child: impl Into<Shared<Identifier>>) {
        self.children.push((Some(EntryLabel::Key), EntryChild::Identifier(child.into())));
    }

    /// Append multiple children with label `key`.
    pub fn extend_key(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Identifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(EntryLabel::Key), EntryChild::Identifier(c.into()))));
    }

    /// Return an iterator over `Shared<Operator>` children labelled `op`.
    ///
    /// Off-type variants stored under the `op` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_op(&self) -> impl Iterator<Item = &Shared<Operator>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op))
            .filter_map(|(_, child)| match child {
                EntryChild::Operator(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `op`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_op(&self) -> Result<&Shared<Operator>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                EntryChild::Operator(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "op" }),
            },
            _ => Err(CstError::ChildCount {
                label: "op",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `op`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_op(&self) -> Result<Option<&Shared<Operator>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                EntryChild::Operator(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "op" }),
            },
            _ => Err(CstError::ChildCount {
                label: "op",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op))
                    .count(),
            }),
        }
    }

    /// Append a child with label `op`, accepting `Operator` or `Shared<Operator>`.
    pub fn append_op(&mut self, child: impl Into<Shared<Operator>>) {
        self.children.push((Some(EntryLabel::Op), EntryChild::Operator(child.into())));
    }

    /// Append multiple children with label `op`.
    pub fn extend_op(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Operator>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(EntryLabel::Op), EntryChild::Operator(c.into()))));
    }

    /// Return an iterator over `Shared<Literal>` children labelled `value`.
    ///
    /// Off-type variants stored under the `value` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_value(&self) -> impl Iterator<Item = &Shared<Literal>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value))
            .filter_map(|(_, child)| match child {
                EntryChild::Literal(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Shared<Literal>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                EntryChild::Literal(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "value" }),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `value`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_value(&self) -> Result<Option<&Shared<Literal>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                EntryChild::Literal(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "value" }),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a child with label `value`, accepting `Literal` or `Shared<Literal>`.
    pub fn append_value(&mut self, child: impl Into<Shared<Literal>>) {
        self.children.push((Some(EntryLabel::Value), EntryChild::Literal(child.into())));
    }

    /// Append multiple children with label `value`.
    pub fn extend_value(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Literal>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(EntryLabel::Value), EntryChild::Literal(c.into()))));
    }

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<EntryLabel>, child: EntryChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<EntryLabel>, EntryChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<EntryLabel>, child: EntryChild,
    ) -> (Option<EntryLabel>, EntryChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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
        Ok(EntryLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<EntryLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<EntryLabel>() {
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<EntryLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Entry.insert: label argument is not a Entry_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Entry.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<EntryLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Entry.replace_at: label argument is not a Entry_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Entry.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
    }

    fn append_key(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(EntryLabel::Key), native_child));
        Ok(())
    }

    fn extend_key(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(EntryLabel::Key), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_key(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(EntryLabel::Key))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_key(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(EntryLabel::Key) {
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
                "Expected one key child but have {count}"
            )));
        }
        first.expect("invariant: Entry.child_key: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_key(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(EntryLabel::Key) {
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
                "Expected at most one key child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_op(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(EntryLabel::Op), native_child));
        Ok(())
    }

    fn extend_op(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(EntryLabel::Op), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_op(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(EntryLabel::Op))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_op(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(EntryLabel::Op) {
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
                "Expected one op child but have {count}"
            )));
        }
        first.expect("invariant: Entry.child_op: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_op(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(EntryLabel::Op) {
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
                "Expected at most one op child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(EntryLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(EntryLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(EntryLabel::Value))
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
                if *lbl == Some(EntryLabel::Value) {
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
        first.expect("invariant: Entry.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(EntryLabel::Value) {
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
// OperatorLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Operator_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `OperatorLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Operator_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum OperatorLabel {
    #[pyo3(name = "APPEND")]
    Append,
    #[pyo3(name = "ASSIGN")]
    Assign,
    #[pyo3(name = "REMOVE")]
    Remove,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum OperatorLabel {
    Append,
    Assign,
    Remove,
}

#[cfg(feature = "python")]
#[pymethods]
impl OperatorLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            OperatorLabel::Append => "Operator.Label.APPEND",
            OperatorLabel::Assign => "Operator.Label.ASSIGN",
            OperatorLabel::Remove => "Operator.Label.REMOVE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<OperatorLabel>() {
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

/// Child value enum for `Operator` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

impl OperatorChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
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

/// CST data struct for `Operator`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Operator {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<OperatorLabel>, OperatorChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Operator {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Operator")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Operator {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Operator {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Operator {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Operator
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
    pub fn children(&self) -> &[(Option<OperatorLabel>, OperatorChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<OperatorLabel>, child: OperatorChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<OperatorLabel>, OperatorChild), CstError> {
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

    /// Return an iterator over `Span` children labelled `append`.
    ///
    /// Off-type variants stored under the `append` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_append(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append))
            .map(|(_, child)| match child { OperatorChild::Span(s) => s })
    }

    /// Return the single child labelled `append`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_append(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "append",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `append`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_append(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "append",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `append`.
    pub fn append_append(&mut self, span: Span) {
        self.children.push((Some(OperatorLabel::Append), OperatorChild::Span(span)));
    }

    /// Append multiple `Span` children with label `append`.
    pub fn extend_append(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(OperatorLabel::Append), OperatorChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `assign`.
    ///
    /// Off-type variants stored under the `assign` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_assign(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign))
            .map(|(_, child)| match child { OperatorChild::Span(s) => s })
    }

    /// Return the single child labelled `assign`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_assign(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "assign",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `assign`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_assign(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "assign",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `assign`.
    pub fn append_assign(&mut self, span: Span) {
        self.children.push((Some(OperatorLabel::Assign), OperatorChild::Span(span)));
    }

    /// Append multiple `Span` children with label `assign`.
    pub fn extend_assign(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(OperatorLabel::Assign), OperatorChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `remove`.
    ///
    /// Off-type variants stored under the `remove` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_remove(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove))
            .map(|(_, child)| match child { OperatorChild::Span(s) => s })
    }

    /// Return the single child labelled `remove`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_remove(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "remove",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `remove`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_remove(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                OperatorChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "remove",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `remove`.
    pub fn append_remove(&mut self, span: Span) {
        self.children.push((Some(OperatorLabel::Remove), OperatorChild::Span(span)));
    }

    /// Append multiple `Span` children with label `remove`.
    pub fn extend_remove(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(OperatorLabel::Remove), OperatorChild::Span(s))));
    }

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<OperatorLabel>, child: OperatorChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<OperatorLabel>, OperatorChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<OperatorLabel>, child: OperatorChild,
    ) -> (Option<OperatorLabel>, OperatorChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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
        Ok(OperatorLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<OperatorLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<OperatorLabel>() {
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<OperatorLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Operator.insert: label argument is not a Operator_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Operator.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<OperatorLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Operator.replace_at: label argument is not a Operator_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Operator.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
    }

    fn append_append(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(OperatorLabel::Append), native_child));
        Ok(())
    }

    fn extend_append(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(OperatorLabel::Append), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_append(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Append))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_append(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Append) {
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
                "Expected one append child but have {count}"
            )));
        }
        first.expect("invariant: Operator.child_append: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_append(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Append) {
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
                "Expected at most one append child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_assign(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(OperatorLabel::Assign), native_child));
        Ok(())
    }

    fn extend_assign(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(OperatorLabel::Assign), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_assign(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Assign))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_assign(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Assign) {
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
                "Expected one assign child but have {count}"
            )));
        }
        first.expect("invariant: Operator.child_assign: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_assign(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Assign) {
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
                "Expected at most one assign child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_remove(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(OperatorLabel::Remove), native_child));
        Ok(())
    }

    fn extend_remove(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(OperatorLabel::Remove), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_remove(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(OperatorLabel::Remove))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_remove(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Remove) {
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
                "Expected one remove child but have {count}"
            )));
        }
        first.expect("invariant: Operator.child_remove: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_remove(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(OperatorLabel::Remove) {
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
                "Expected at most one remove child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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

impl IdentifierChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
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
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Identifier {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<IdentifierLabel>, IdentifierChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Identifier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Identifier")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
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

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<IdentifierLabel>, child: IdentifierChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<IdentifierLabel>, IdentifierChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<IdentifierLabel>, child: IdentifierChild,
    ) -> (Option<IdentifierLabel>, IdentifierChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = IdentifierChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<IdentifierLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Identifier.insert: label argument is not a Identifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Identifier.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = IdentifierChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<IdentifierLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Identifier.replace_at: label argument is not a Identifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Identifier.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(IdentifierLabel::Name))
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
                if *lbl == Some(IdentifierLabel::Name) {
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
        first.expect("invariant: Identifier.child_name: count==1 but first==None; logic error")
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
                if *lbl == Some(IdentifierLabel::Name) {
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
// LiteralLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Literal_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `LiteralLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Literal_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LiteralLabel {
    #[pyo3(name = "INT_VAL")]
    IntVal,
    #[pyo3(name = "STR_VAL")]
    StrVal,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LiteralLabel {
    IntVal,
    StrVal,
}

#[cfg(feature = "python")]
#[pymethods]
impl LiteralLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LiteralLabel::IntVal => "Literal.Label.INT_VAL",
            LiteralLabel::StrVal => "Literal.Label.STR_VAL",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LiteralLabel>() {
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

/// Child value enum for `Literal` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
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

impl LiteralChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
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

/// CST data struct for `Literal`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Literal {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LiteralLabel>, LiteralChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Literal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Literal")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Literal {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Literal {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Literal {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Literal
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
    pub fn children(&self) -> &[(Option<LiteralLabel>, LiteralChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<LiteralLabel>, child: LiteralChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<LiteralLabel>, LiteralChild), CstError> {
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

    /// Return an iterator over `Span` children labelled `int_val`.
    ///
    /// Off-type variants stored under the `int_val` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_int_val(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal))
            .map(|(_, child)| match child { LiteralChild::Span(s) => s })
    }

    /// Return the single child labelled `int_val`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_int_val(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "int_val",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `int_val`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_int_val(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "int_val",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `int_val`.
    pub fn append_int_val(&mut self, span: Span) {
        self.children.push((Some(LiteralLabel::IntVal), LiteralChild::Span(span)));
    }

    /// Append multiple `Span` children with label `int_val`.
    pub fn extend_int_val(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LiteralLabel::IntVal), LiteralChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `str_val`.
    ///
    /// Off-type variants stored under the `str_val` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_str_val(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal))
            .map(|(_, child)| match child { LiteralChild::Span(s) => s })
    }

    /// Return the single child labelled `str_val`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_str_val(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "str_val",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `str_val`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_str_val(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "str_val",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `str_val`.
    pub fn append_str_val(&mut self, span: Span) {
        self.children.push((Some(LiteralLabel::StrVal), LiteralChild::Span(span)));
    }

    /// Append multiple `Span` children with label `str_val`.
    pub fn extend_str_val(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LiteralLabel::StrVal), LiteralChild::Span(s))));
    }

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<LiteralLabel>, child: LiteralChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<LiteralLabel>, LiteralChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<LiteralLabel>, child: LiteralChild,
    ) -> (Option<LiteralLabel>, LiteralChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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
        Ok(LiteralLabel::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LiteralLabel>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LiteralLabel>() {
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LiteralLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Literal.insert: label argument is not a Literal_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Literal.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LiteralLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Literal.replace_at: label argument is not a Literal_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Literal.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
    }

    fn append_int_val(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LiteralLabel::IntVal), native_child));
        Ok(())
    }

    fn extend_int_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LiteralLabel::IntVal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_int_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LiteralLabel::IntVal))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_int_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LiteralLabel::IntVal) {
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
                "Expected one int_val child but have {count}"
            )));
        }
        first.expect("invariant: Literal.child_int_val: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_int_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LiteralLabel::IntVal) {
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
                "Expected at most one int_val child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_str_val(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LiteralLabel::StrVal), native_child));
        Ok(())
    }

    fn extend_str_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LiteralLabel::StrVal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_str_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LiteralLabel::StrVal))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_str_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LiteralLabel::StrVal) {
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
                "Expected one str_val child but have {count}"
            )));
        }
        first.expect("invariant: Literal.child_str_val: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_str_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LiteralLabel::StrVal) {
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
                "Expected at most one str_val child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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
// ValueNodeLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `ValueNode_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `ValueNodeLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "ValueNode_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ValueNodeLabel {
    #[pyo3(name = "OPERAND")]
    Operand,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ValueNodeLabel {
    Operand,
}

#[cfg(feature = "python")]
#[pymethods]
impl ValueNodeLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ValueNodeLabel::Operand => "ValueNode.Label.OPERAND",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<ValueNodeLabel>() {
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

/// Child value enum for `ValueNode` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum ValueNodeChild {
    Identifier(Shared<Identifier>),
    Literal(Shared<Literal>),
}

impl PartialEq for ValueNodeChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ValueNodeChild::Identifier(a), ValueNodeChild::Identifier(b)) => a == b,
            (ValueNodeChild::Literal(a), ValueNodeChild::Literal(b)) => a == b,
            _ => false,
        }
    }
}

impl ValueNodeChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Identifier(s) => Some(DropWorklistItem::Identifier(s)),
            Self::Literal(s) => Some(DropWorklistItem::Literal(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ValueNodeChild {
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
        Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "ValueNode: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// ValueNode
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `ValueNode`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct ValueNode {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<ValueNodeLabel>, ValueNodeChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for ValueNode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("ValueNode")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for ValueNode {
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

impl PartialEq for ValueNode {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl ValueNode {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        ValueNode {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::ValueNode
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
    pub fn children(&self) -> &[(Option<ValueNodeLabel>, ValueNodeChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<ValueNodeLabel>, child: ValueNodeChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<ValueNodeLabel>, ValueNodeChild), CstError> {
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

    /// Return an iterator over children labelled `operand`.
    pub fn children_operand(&self) -> impl Iterator<Item = &ValueNodeChild> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand))
            .map(|(_, child)| child)
    }

    /// Return the single child labelled `operand`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_operand(&self) -> Result<&ValueNodeChild, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand));
        match (matching.next(), matching.next()) {
            (Some((_, child)), None) => Ok(child),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand))
                    .count();
                Err(CstError::ChildCount {
                    label: "operand",
                    expected: "1",
                    found: count,
                })
            }
        }
    }

    /// Return the optional child labelled `operand`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_operand(&self) -> Result<Option<&ValueNodeChild>, CstError> {
        let mut matching = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand));
        match (matching.next(), matching.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => Ok(Some(child)),
            _ => {
                let count = self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand))
                    .count();
                Err(CstError::ChildCount {
                    label: "operand",
                    expected: "0 or 1",
                    found: count,
                })
            }
        }
    }

    /// Append a child with label `operand` (any child enum variant).
    pub fn append_operand(&mut self, child: ValueNodeChild) {
        self.children.push((Some(ValueNodeLabel::Operand), child));
    }

    /// Append multiple children with label `operand`.
    pub fn extend_operand(&mut self, children: impl IntoIterator<Item = ValueNodeChild>) {
        self.children.extend(children.into_iter().map(|c| (Some(ValueNodeLabel::Operand), c)));
    }

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<ValueNodeLabel>, child: ValueNodeChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<ValueNodeLabel>, ValueNodeChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<ValueNodeLabel>, child: ValueNodeChild,
    ) -> (Option<ValueNodeLabel>, ValueNodeChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "ValueNode")]
pub struct PyValueNode {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<ValueNode>,
}

#[cfg(feature = "python")]
impl PyValueNode {
    /// Return a reference to the inner `Shared<ValueNode>`.
    pub fn shared(&self) -> &Shared<ValueNode> {
        &self.inner
    }

    /// Wrap a `Shared<ValueNode>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<ValueNode>) -> PyResult<Py<PyValueNode>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyValueNode { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyValueNode>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyValueNode {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyValueNode>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = ValueNode {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyValueNode { inner: shared };
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
        NodeKind::ValueNode
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(ValueNodeLabel::type_object(py).into_any().unbind())
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
        let native_child = ValueNodeChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValueNodeLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ValueNode.append: label argument is not a ValueNode_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValueNodeLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ValueNode.extend: label argument is not a ValueNode_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ValueNodeChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyValueNode) -> PyResult<()> {
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = ValueNodeChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValueNodeLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ValueNode.insert: label argument is not a ValueNode_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "ValueNode.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = ValueNodeChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<ValueNodeLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "ValueNode.replace_at: label argument is not a ValueNode_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "ValueNode.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
    }

    fn append_operand(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ValueNodeChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ValueNodeLabel::Operand), native_child));
        Ok(())
    }

    fn extend_operand(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ValueNodeChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ValueNodeLabel::Operand), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_operand(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ValueNodeLabel::Operand))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_operand(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ValueNodeLabel::Operand) {
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
                "Expected one operand child but have {count}"
            )));
        }
        first.expect("invariant: ValueNode.child_operand: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_operand(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ValueNodeLabel::Operand) {
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
                "Expected at most one operand child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyValueNode>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyValueNode> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'ValueNode'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "ValueNode(span={span_repr}, children=[<{children_len} child(ren)>])"
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

    /// Insert a child at `index` (Vec::insert semantics: panics if index > len).
    ///
    /// Python-facing clamping is in the `insert` pymethod; native callers must
    /// bounds-check. Unlike `list.insert`, Vec::insert panics on out-of-bounds.
    pub fn insert_child(&mut self, index: usize, label: Option<TriviaLabel>, child: TriviaChild) {
        self.children.insert(index, (label, child));
    }

    /// Remove and return the child at `index` (Vec::remove semantics: panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `remove_at` pymethod.
    pub fn remove_child(&mut self, index: usize) -> (Option<TriviaLabel>, TriviaChild) {
        self.children.remove(index)
    }

    /// Replace the child at `index`, returning the old entry (panics if out of range).
    ///
    /// Panics on out-of-range. Python-facing IndexError is in the `replace_at` pymethod.
    pub fn replace_child(
        &mut self, index: usize, label: Option<TriviaLabel>, child: TriviaChild,
    ) -> (Option<TriviaLabel>, TriviaChild) {
        std::mem::replace(&mut self.children[index], (label, child))
    }

    /// Remove all children.
    pub fn clear_children(&mut self) {
        self.children.clear();
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

    #[pyo3(signature = (index, child, label = None))]
    fn insert(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<TriviaLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Trivia.insert: label argument is not a Trivia_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Index normalization via operator.index (PyNumber_Index semantics).
        // This raises TypeError (not AttributeError) for non-indexable inputs, matching Python's
        // operator.index contract. Must be done BEFORE taking any lock (§2.3 lock discipline).
        // Overflow by sign: positive overflow clamps to len; negative overflow clamps to 0.
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path for the common exact-int case; fall back to sign-based Python call for beyond-i64.
        let (is_negative_big, raw_i64) = if let Ok(i) = raw_idx.extract::<i64>() {
            (false, Some(i))
        } else {
            // Beyond i64: use Python __lt__ to determine sign.  The lt call is still outside
            // any lock, so lock discipline is maintained.
            let neg = raw_idx.lt(0i64)?;
            (neg, None)
        };
        // Now take a single write lock for the entire len-read + clamp + insert sequence.
        let mut guard = self.inner.write();
        let n = guard.children.len();
        let clamped: usize = match raw_i64 {
            Some(i) if i < 0 => {
                let normalized = n as i64 + i;
                if normalized < 0 { 0 } else { normalized as usize }
            }
            Some(i) => {
                let u = i as usize;
                if u > n { n } else { u }
            }
            None => if is_negative_big { 0 } else { n },
        };
        guard.children.insert(clamped, (native_label, native_child));
        Ok(())
    }

    fn remove_at(&self, py: Python<'_>, index: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        // Capture the caller's original string representation BEFORE normalization,
        // so error messages show the original value (e.g. `True` not `1`).
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError (not AttributeError) for
        // non-indexable inputs, matching Python's operator.index contract.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        // Fast path: extract i64. Beyond i64 is always OOB for real trees.
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + Vec::remove atomically (no TOCTOU).
        // On OOB, capture n and return Err after releasing the guard.
        let result: Result<_, usize> = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            match resolved {
                Some(idx) => Ok(guard.children.remove(idx)),
                None => Err(n),
            }
        };
        let (label, child) = result.map_err(|n| {
            PyIndexError::new_err(format!(
                "Trivia.remove_at: index {} out of range ({} children)",
                orig_str, n
            ))
        })?;
        // Python wrap-out happens after the guard is released (§2.3 lock discipline).
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    #[pyo3(signature = (index, child, label = None))]
    fn replace_at(
        &self,
        py: Python<'_>,
        index: &Bound<'_, PyAny>,
        child: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        // Validate child and label BEFORE taking the write lock (§2.3 lock discipline).
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<TriviaLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Trivia.replace_at: label argument is not a Trivia_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        // Capture the caller's original string representation BEFORE normalization.
        let orig_str = index.str()?.to_string_lossy().into_owned();
        // Normalize via operator.index: raises TypeError for non-indexable inputs.
        // All Python work must happen before any lock (§2.3 lock discipline).
        let raw_idx = py
            .import(pyo3::intern!(py, "operator"))?
            .getattr(pyo3::intern!(py, "index"))?
            .call1((index,))?;
        let maybe_i64: Option<i64> = raw_idx.extract::<i64>().ok();
        // Single write lock: resolve + bounds-check + mem::replace atomically (no TOCTOU).
        let old = {
            let mut guard = self.inner.write();
            let n = guard.children.len();
            let resolved: Option<usize> = match maybe_i64 {
                Some(i) if i < 0 => {
                    let normalized = n as i64 + i;
                    if normalized < 0 || normalized as usize >= n { None }
                    else { Some(normalized as usize) }
                }
                Some(i) if (i as usize) < n => Some(i as usize),
                _ => None,
            };
            let idx = match resolved {
                Some(i) => i,
                None => {
                    return Err(PyIndexError::new_err(format!(
                        "Trivia.replace_at: index {} out of range ({} children)",
                        orig_str, n
                    )));
                }
            };
            std::mem::replace(&mut guard.children[idx], (native_label, native_child))
        };
        // Drop old entry outside the lock to avoid recursive lock acquisition
        // if the child's drop chain re-enters Python.
        drop(old);
        Ok(())
    }

    fn clear(&self, _py: Python<'_>) -> PyResult<()> {
        let old = {
            let mut guard = self.inner.write();
            std::mem::take(&mut guard.children)
        };
        // Drop old entries outside the lock.
        drop(old);
        Ok(())
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
    Entry(Shared<Entry>),
    Identifier(Shared<Identifier>),
    Literal(Shared<Literal>),
    Operator(Shared<Operator>),
    Trivia(Shared<Trivia>),
}

impl DropWorklistItem {
    fn drain_into(self, worklist: &mut Vec<DropWorklistItem>) {
        // Each arm: if sole owner, steal children (so the node's Drop early-returns
        // instead of recursing through drop glue); then drop `shared`.
        // count==1 → childless node after steal, trivial drop;
        // count>1 → refcount decrement only. Either way, no recursion.
        match self {
            DropWorklistItem::Entry(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Identifier(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Literal(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Operator(shared) => {
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

#[cfg(all(feature = "python", feature = "test-introspection"))]
#[pyfunction]
fn _registry_snapshot(py: Python<'_>) -> PyResult<pyo3::Bound<'_, pyo3::types::PyDict>> {
    registry::snapshot(py)
}

#[cfg(feature = "python")]
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<ConfigLabel>()?;
    module.add_class::<PyConfig>()?;
    module.add_class::<EntryLabel>()?;
    module.add_class::<PyEntry>()?;
    module.add_class::<OperatorLabel>()?;
    module.add_class::<PyOperator>()?;
    module.add_class::<IdentifierLabel>()?;
    module.add_class::<PyIdentifier>()?;
    module.add_class::<LiteralLabel>()?;
    module.add_class::<PyLiteral>()?;
    module.add_class::<ValueNodeLabel>()?;
    module.add_class::<PyValueNode>()?;
    module.add_class::<TriviaLabel>()?;
    module.add_class::<PyTrivia>()?;
    #[cfg(feature = "test-introspection")]
    module.add_function(wrap_pyfunction!(_registry_snapshot, module)?)?;
    Ok(())
}
