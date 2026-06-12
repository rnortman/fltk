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
    #[pyo3(name = "GRAMMAR")]
    Grammar,
    #[pyo3(name = "RULE")]
    Rule,
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "ITEMS")]
    Items,
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "TERM")]
    Term,
    #[pyo3(name = "DISPOSITION")]
    Disposition,
    #[pyo3(name = "QUANTIFIER")]
    Quantifier,
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "RAWSTRING")]
    RawString,
    #[pyo3(name = "LITERAL")]
    Literal,
    #[pyo3(name = "TRIVIA")]
    Trivia,
    #[pyo3(name = "LINECOMMENT")]
    LineComment,
    #[pyo3(name = "BLOCKCOMMENT")]
    BlockComment,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum NodeKind {
    Grammar,
    Rule,
    Alternatives,
    Items,
    Item,
    Term,
    Disposition,
    Quantifier,
    Identifier,
    RawString,
    Literal,
    Trivia,
    LineComment,
    BlockComment,
}

#[cfg(feature = "python")]
#[pymethods]
impl NodeKind {
    fn __repr__(&self) -> &'static str {
        match self {
            NodeKind::Grammar => "NodeKind.GRAMMAR",
            NodeKind::Rule => "NodeKind.RULE",
            NodeKind::Alternatives => "NodeKind.ALTERNATIVES",
            NodeKind::Items => "NodeKind.ITEMS",
            NodeKind::Item => "NodeKind.ITEM",
            NodeKind::Term => "NodeKind.TERM",
            NodeKind::Disposition => "NodeKind.DISPOSITION",
            NodeKind::Quantifier => "NodeKind.QUANTIFIER",
            NodeKind::Identifier => "NodeKind.IDENTIFIER",
            NodeKind::RawString => "NodeKind.RAWSTRING",
            NodeKind::Literal => "NodeKind.LITERAL",
            NodeKind::Trivia => "NodeKind.TRIVIA",
            NodeKind::LineComment => "NodeKind.LINECOMMENT",
            NodeKind::BlockComment => "NodeKind.BLOCKCOMMENT",
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
// GrammarLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Grammar_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `GrammarLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Grammar_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum GrammarLabel {
    #[pyo3(name = "RULE")]
    Rule,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum GrammarLabel {
    Rule,
}

#[cfg(feature = "python")]
#[pymethods]
impl GrammarLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            GrammarLabel::Rule => "Grammar.Label.RULE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<GrammarLabel>() {
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

/// Child value enum for `Grammar` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum GrammarChild {
    Rule(Shared<Rule>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for GrammarChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (GrammarChild::Rule(a), GrammarChild::Rule(b)) => a == b,
            (GrammarChild::Trivia(a), GrammarChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl GrammarChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Rule(s) => Some(DropWorklistItem::Rule(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl GrammarChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Rule(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyRule { inner: shared.clone() };
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
        if obj.is_instance_of::<PyRule>() {
            let handle: PyRef<PyRule> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Rule(shared));
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
            "Grammar: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Grammar
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Grammar`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Grammar {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<GrammarLabel>, GrammarChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Grammar {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Grammar")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Grammar {
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

impl PartialEq for Grammar {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Grammar {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Grammar {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Grammar
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
    pub fn children(&self) -> &[(Option<GrammarLabel>, GrammarChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<GrammarLabel>, child: GrammarChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<GrammarLabel>, GrammarChild), CstError> {
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

    /// Return an iterator over `Shared<Rule>` children labelled `rule`.
    ///
    /// Off-type variants stored under the `rule` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_rule(&self) -> impl Iterator<Item = &Shared<Rule>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule))
            .filter_map(|(_, child)| match child {
                GrammarChild::Rule(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `rule`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_rule(&self) -> Result<&Shared<Rule>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                GrammarChild::Rule(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "rule" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rule",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `rule`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_rule(&self) -> Result<Option<&Shared<Rule>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                GrammarChild::Rule(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "rule" }),
            },
            _ => Err(CstError::ChildCount {
                label: "rule",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule))
                    .count(),
            }),
        }
    }

    /// Append a child with label `rule`, accepting `Rule` or `Shared<Rule>`.
    pub fn append_rule(&mut self, child: impl Into<Shared<Rule>>) {
        self.children.push((Some(GrammarLabel::Rule), GrammarChild::Rule(child.into())));
    }

    /// Append multiple children with label `rule`.
    pub fn extend_rule(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Rule>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(GrammarLabel::Rule), GrammarChild::Rule(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Grammar")]
pub struct PyGrammar {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Grammar>,
}

#[cfg(feature = "python")]
impl PyGrammar {
    /// Return a reference to the inner `Shared<Grammar>`.
    pub fn shared(&self) -> &Shared<Grammar> {
        &self.inner
    }

    /// Wrap a `Shared<Grammar>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Grammar>) -> PyResult<Py<PyGrammar>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyGrammar { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyGrammar>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyGrammar {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyGrammar>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Grammar {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyGrammar { inner: shared };
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
        NodeKind::Grammar
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(GrammarLabel::type_object(py).into_any().unbind())
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
        let native_child = GrammarChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<GrammarLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Grammar.append: label argument is not a Grammar_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<GrammarLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Grammar.extend: label argument is not a Grammar_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GrammarChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyGrammar) -> PyResult<()> {
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

    fn append_rule(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = GrammarChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(GrammarLabel::Rule), native_child));
        Ok(())
    }

    fn extend_rule(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GrammarChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(GrammarLabel::Rule), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_rule(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(GrammarLabel::Rule))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_rule(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(GrammarLabel::Rule) {
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
                "Expected one rule child but have {count}"
            )));
        }
        first.expect("invariant: Grammar.child_rule: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_rule(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(GrammarLabel::Rule) {
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
                "Expected at most one rule child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyGrammar>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyGrammar> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Grammar'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Grammar(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// RuleLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Rule_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `RuleLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Rule_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RuleLabel {
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "NAME")]
    Name,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RuleLabel {
    Alternatives,
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl RuleLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            RuleLabel::Alternatives => "Rule.Label.ALTERNATIVES",
            RuleLabel::Name => "Rule.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RuleLabel>() {
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

/// Child value enum for `Rule` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum RuleChild {
    Alternatives(Shared<Alternatives>),
    Identifier(Shared<Identifier>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for RuleChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (RuleChild::Alternatives(a), RuleChild::Alternatives(b)) => a == b,
            (RuleChild::Identifier(a), RuleChild::Identifier(b)) => a == b,
            (RuleChild::Trivia(a), RuleChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl RuleChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Alternatives(s) => Some(DropWorklistItem::Alternatives(s)),
            Self::Identifier(s) => Some(DropWorklistItem::Identifier(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl RuleChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Alternatives(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAlternatives { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
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
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<PyAlternatives>() {
            let handle: PyRef<PyAlternatives> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Alternatives(shared));
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
            "Rule: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Rule
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Rule`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Rule {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RuleLabel>, RuleChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Rule {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Rule")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Rule {
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

impl PartialEq for Rule {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Rule {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Rule {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Rule
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
    pub fn children(&self) -> &[(Option<RuleLabel>, RuleChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<RuleLabel>, child: RuleChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<RuleLabel>, RuleChild), CstError> {
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

    /// Return an iterator over `Shared<Alternatives>` children labelled `alternatives`.
    ///
    /// Off-type variants stored under the `alternatives` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_alternatives(&self) -> impl Iterator<Item = &Shared<Alternatives>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives))
            .filter_map(|(_, child)| match child {
                RuleChild::Alternatives(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `alternatives`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_alternatives(&self) -> Result<&Shared<Alternatives>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RuleChild::Alternatives(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "alternatives" }),
            },
            _ => Err(CstError::ChildCount {
                label: "alternatives",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `alternatives`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_alternatives(&self) -> Result<Option<&Shared<Alternatives>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RuleChild::Alternatives(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "alternatives" }),
            },
            _ => Err(CstError::ChildCount {
                label: "alternatives",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives))
                    .count(),
            }),
        }
    }

    /// Append a child with label `alternatives`, accepting `Alternatives` or `Shared<Alternatives>`.
    pub fn append_alternatives(&mut self, child: impl Into<Shared<Alternatives>>) {
        self.children.push((Some(RuleLabel::Alternatives), RuleChild::Alternatives(child.into())));
    }

    /// Append multiple children with label `alternatives`.
    pub fn extend_alternatives(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Alternatives>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RuleLabel::Alternatives), RuleChild::Alternatives(c.into()))));
    }

    /// Return an iterator over `Shared<Identifier>` children labelled `name`.
    ///
    /// Off-type variants stored under the `name` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_name(&self) -> impl Iterator<Item = &Shared<Identifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name))
            .filter_map(|(_, child)| match child {
                RuleChild::Identifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `name`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_name(&self) -> Result<&Shared<Identifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RuleChild::Identifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "name" }),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `name`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_name(&self) -> Result<Option<&Shared<Identifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RuleChild::Identifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "name" }),
            },
            _ => Err(CstError::ChildCount {
                label: "name",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name))
                    .count(),
            }),
        }
    }

    /// Append a child with label `name`, accepting `Identifier` or `Shared<Identifier>`.
    pub fn append_name(&mut self, child: impl Into<Shared<Identifier>>) {
        self.children.push((Some(RuleLabel::Name), RuleChild::Identifier(child.into())));
    }

    /// Append multiple children with label `name`.
    pub fn extend_name(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Identifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(RuleLabel::Name), RuleChild::Identifier(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Rule")]
pub struct PyRule {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Rule>,
}

#[cfg(feature = "python")]
impl PyRule {
    /// Return a reference to the inner `Shared<Rule>`.
    pub fn shared(&self) -> &Shared<Rule> {
        &self.inner
    }

    /// Wrap a `Shared<Rule>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Rule>) -> PyResult<Py<PyRule>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyRule { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyRule>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyRule {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyRule>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Rule {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyRule { inner: shared };
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
        NodeKind::Rule
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RuleLabel::type_object(py).into_any().unbind())
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
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<RuleLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Rule.append: label argument is not a Rule_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RuleLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Rule.extend: label argument is not a Rule_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyRule) -> PyResult<()> {
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

    fn append_alternatives(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RuleLabel::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RuleLabel::Alternatives), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(RuleLabel::Alternatives))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RuleLabel::Alternatives) {
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
                "Expected one alternatives child but have {count}"
            )));
        }
        first.expect("invariant: Rule.child_alternatives: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(RuleLabel::Alternatives) {
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
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_name(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RuleLabel::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RuleLabel::Name), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(RuleLabel::Name))
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
                if *lbl == Some(RuleLabel::Name) {
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
        first.expect("invariant: Rule.child_name: count==1 but first==None; logic error")
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
                if *lbl == Some(RuleLabel::Name) {
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
        if !other.is_instance_of::<PyRule>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyRule> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Rule'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Rule(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// AlternativesLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Alternatives_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `AlternativesLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Alternatives_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum AlternativesLabel {
    #[pyo3(name = "ITEMS")]
    Items,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum AlternativesLabel {
    Items,
}

#[cfg(feature = "python")]
#[pymethods]
impl AlternativesLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            AlternativesLabel::Items => "Alternatives.Label.ITEMS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<AlternativesLabel>() {
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

/// Child value enum for `Alternatives` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum AlternativesChild {
    Items(Shared<Items>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for AlternativesChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (AlternativesChild::Items(a), AlternativesChild::Items(b)) => a == b,
            (AlternativesChild::Trivia(a), AlternativesChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl AlternativesChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Items(s) => Some(DropWorklistItem::Items(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl AlternativesChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Items(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyItems { inner: shared.clone() };
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
        if obj.is_instance_of::<PyItems>() {
            let handle: PyRef<PyItems> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Items(shared));
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
            "Alternatives: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Alternatives
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Alternatives`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Alternatives {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<AlternativesLabel>, AlternativesChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Alternatives {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Alternatives")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Alternatives {
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

impl PartialEq for Alternatives {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Alternatives {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Alternatives {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Alternatives
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
    pub fn children(&self) -> &[(Option<AlternativesLabel>, AlternativesChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<AlternativesLabel>, child: AlternativesChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<AlternativesLabel>, AlternativesChild), CstError> {
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

    /// Return an iterator over `Shared<Items>` children labelled `items`.
    ///
    /// Off-type variants stored under the `items` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_items(&self) -> impl Iterator<Item = &Shared<Items>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items))
            .filter_map(|(_, child)| match child {
                AlternativesChild::Items(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `items`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_items(&self) -> Result<&Shared<Items>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                AlternativesChild::Items(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "items" }),
            },
            _ => Err(CstError::ChildCount {
                label: "items",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `items`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_items(&self) -> Result<Option<&Shared<Items>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                AlternativesChild::Items(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "items" }),
            },
            _ => Err(CstError::ChildCount {
                label: "items",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items))
                    .count(),
            }),
        }
    }

    /// Append a child with label `items`, accepting `Items` or `Shared<Items>`.
    pub fn append_items(&mut self, child: impl Into<Shared<Items>>) {
        self.children.push((Some(AlternativesLabel::Items), AlternativesChild::Items(child.into())));
    }

    /// Append multiple children with label `items`.
    pub fn extend_items(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Items>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(AlternativesLabel::Items), AlternativesChild::Items(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Alternatives")]
pub struct PyAlternatives {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Alternatives>,
}

#[cfg(feature = "python")]
impl PyAlternatives {
    /// Return a reference to the inner `Shared<Alternatives>`.
    pub fn shared(&self) -> &Shared<Alternatives> {
        &self.inner
    }

    /// Wrap a `Shared<Alternatives>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Alternatives>) -> PyResult<Py<PyAlternatives>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyAlternatives { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyAlternatives>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyAlternatives {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyAlternatives>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Alternatives {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyAlternatives { inner: shared };
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
        NodeKind::Alternatives
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(AlternativesLabel::type_object(py).into_any().unbind())
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
        let native_child = AlternativesChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<AlternativesLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Alternatives.append: label argument is not a Alternatives_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<AlternativesLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Alternatives.extend: label argument is not a Alternatives_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AlternativesChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyAlternatives) -> PyResult<()> {
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

    fn append_items(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = AlternativesChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(AlternativesLabel::Items), native_child));
        Ok(())
    }

    fn extend_items(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AlternativesChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(AlternativesLabel::Items), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_items(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(AlternativesLabel::Items))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_items(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(AlternativesLabel::Items) {
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
                "Expected one items child but have {count}"
            )));
        }
        first.expect("invariant: Alternatives.child_items: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_items(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(AlternativesLabel::Items) {
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
                "Expected at most one items child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyAlternatives>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyAlternatives> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Alternatives'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Alternatives(span={span_repr}, children=[<{children_len} child(ren)>])"
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
    Item(Shared<Item>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for ItemsChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ItemsChild::Span(a), ItemsChild::Span(b)) => a == b,
            (ItemsChild::Item(a), ItemsChild::Item(b)) => a == b,
            (ItemsChild::Trivia(a), ItemsChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl ItemsChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
            Self::Item(s) => Some(DropWorklistItem::Item(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
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
            Self::Item(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyItem { inner: shared.clone() };
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

    /// Return an iterator over `Shared<Item>` children labelled `item`.
    ///
    /// Off-type variants stored under the `item` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_item(&self) -> impl Iterator<Item = &Shared<Item>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item))
            .filter_map(|(_, child)| match child {
                ItemsChild::Item(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `item`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_item(&self) -> Result<&Shared<Item>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemsChild::Item(s) => Ok(s),
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
    pub fn maybe_item(&self) -> Result<Option<&Shared<Item>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemsLabel::Item));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemsChild::Item(s) => Ok(Some(s)),
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

    /// Append a child with label `item`, accepting `Item` or `Shared<Item>`.
    pub fn append_item(&mut self, child: impl Into<Shared<Item>>) {
        self.children.push((Some(ItemsLabel::Item), ItemsChild::Item(child.into())));
    }

    /// Append multiple children with label `item`.
    pub fn extend_item(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Item>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemsLabel::Item), ItemsChild::Item(c.into()))));
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemsLabel::NoWs))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::NoWs) {
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
                "Expected one no_ws child but have {count}"
            )));
        }
        first.expect("invariant: Items.child_no_ws: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_no_ws(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::NoWs) {
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
                "Expected at most one no_ws child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsAllowed))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::WsAllowed) {
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
                "Expected one ws_allowed child but have {count}"
            )));
        }
        first.expect("invariant: Items.child_ws_allowed: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_ws_allowed(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::WsAllowed) {
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
                "Expected at most one ws_allowed child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
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
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemsLabel::WsRequired))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::WsRequired) {
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
                "Expected one ws_required child but have {count}"
            )));
        }
        first.expect("invariant: Items.child_ws_required: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_ws_required(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemsLabel::WsRequired) {
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
                "Expected at most one ws_required child but have at least 2",
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
    #[pyo3(name = "DISPOSITION")]
    Disposition,
    #[pyo3(name = "LABEL")]
    Label,
    #[pyo3(name = "QUANTIFIER")]
    Quantifier,
    #[pyo3(name = "TERM")]
    Term,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ItemLabel {
    Disposition,
    Label,
    Quantifier,
    Term,
}

#[cfg(feature = "python")]
#[pymethods]
impl ItemLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            ItemLabel::Disposition => "Item.Label.DISPOSITION",
            ItemLabel::Label => "Item.Label.LABEL",
            ItemLabel::Quantifier => "Item.Label.QUANTIFIER",
            ItemLabel::Term => "Item.Label.TERM",
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
    Disposition(Shared<Disposition>),
    Identifier(Shared<Identifier>),
    Quantifier(Shared<Quantifier>),
    Term(Shared<Term>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for ItemChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ItemChild::Disposition(a), ItemChild::Disposition(b)) => a == b,
            (ItemChild::Identifier(a), ItemChild::Identifier(b)) => a == b,
            (ItemChild::Quantifier(a), ItemChild::Quantifier(b)) => a == b,
            (ItemChild::Term(a), ItemChild::Term(b)) => a == b,
            (ItemChild::Trivia(a), ItemChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl ItemChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Disposition(s) => Some(DropWorklistItem::Disposition(s)),
            Self::Identifier(s) => Some(DropWorklistItem::Identifier(s)),
            Self::Quantifier(s) => Some(DropWorklistItem::Quantifier(s)),
            Self::Term(s) => Some(DropWorklistItem::Term(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl ItemChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Disposition(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyDisposition { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Identifier(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyIdentifier { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Quantifier(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyQuantifier { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::Term(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyTerm { inner: shared.clone() };
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
        if obj.is_instance_of::<PyDisposition>() {
            let handle: PyRef<PyDisposition> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Disposition(shared));
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
        if obj.is_instance_of::<PyQuantifier>() {
            let handle: PyRef<PyQuantifier> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Quantifier(shared));
        }
        if obj.is_instance_of::<PyTerm>() {
            let handle: PyRef<PyTerm> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Term(shared));
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

    /// Return an iterator over `Shared<Disposition>` children labelled `disposition`.
    ///
    /// Off-type variants stored under the `disposition` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_disposition(&self) -> impl Iterator<Item = &Shared<Disposition>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition))
            .filter_map(|(_, child)| match child {
                ItemChild::Disposition(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `disposition`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_disposition(&self) -> Result<&Shared<Disposition>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::Disposition(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "disposition" }),
            },
            _ => Err(CstError::ChildCount {
                label: "disposition",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `disposition`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_disposition(&self) -> Result<Option<&Shared<Disposition>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::Disposition(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "disposition" }),
            },
            _ => Err(CstError::ChildCount {
                label: "disposition",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition))
                    .count(),
            }),
        }
    }

    /// Append a child with label `disposition`, accepting `Disposition` or `Shared<Disposition>`.
    pub fn append_disposition(&mut self, child: impl Into<Shared<Disposition>>) {
        self.children.push((Some(ItemLabel::Disposition), ItemChild::Disposition(child.into())));
    }

    /// Append multiple children with label `disposition`.
    pub fn extend_disposition(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Disposition>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::Disposition), ItemChild::Disposition(c.into()))));
    }

    /// Return an iterator over `Shared<Identifier>` children labelled `label`.
    ///
    /// Off-type variants stored under the `label` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_label(&self) -> impl Iterator<Item = &Shared<Identifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label))
            .filter_map(|(_, child)| match child {
                ItemChild::Identifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `label`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_label(&self) -> Result<&Shared<Identifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::Identifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "label" }),
            },
            _ => Err(CstError::ChildCount {
                label: "label",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `label`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_label(&self) -> Result<Option<&Shared<Identifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::Identifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "label" }),
            },
            _ => Err(CstError::ChildCount {
                label: "label",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label))
                    .count(),
            }),
        }
    }

    /// Append a child with label `label`, accepting `Identifier` or `Shared<Identifier>`.
    pub fn append_label(&mut self, child: impl Into<Shared<Identifier>>) {
        self.children.push((Some(ItemLabel::Label), ItemChild::Identifier(child.into())));
    }

    /// Append multiple children with label `label`.
    pub fn extend_label(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Identifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::Label), ItemChild::Identifier(c.into()))));
    }

    /// Return an iterator over `Shared<Quantifier>` children labelled `quantifier`.
    ///
    /// Off-type variants stored under the `quantifier` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_quantifier(&self) -> impl Iterator<Item = &Shared<Quantifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier))
            .filter_map(|(_, child)| match child {
                ItemChild::Quantifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `quantifier`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_quantifier(&self) -> Result<&Shared<Quantifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::Quantifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "quantifier" }),
            },
            _ => Err(CstError::ChildCount {
                label: "quantifier",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `quantifier`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_quantifier(&self) -> Result<Option<&Shared<Quantifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::Quantifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "quantifier" }),
            },
            _ => Err(CstError::ChildCount {
                label: "quantifier",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier))
                    .count(),
            }),
        }
    }

    /// Append a child with label `quantifier`, accepting `Quantifier` or `Shared<Quantifier>`.
    pub fn append_quantifier(&mut self, child: impl Into<Shared<Quantifier>>) {
        self.children.push((Some(ItemLabel::Quantifier), ItemChild::Quantifier(child.into())));
    }

    /// Append multiple children with label `quantifier`.
    pub fn extend_quantifier(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Quantifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::Quantifier), ItemChild::Quantifier(c.into()))));
    }

    /// Return an iterator over `Shared<Term>` children labelled `term`.
    ///
    /// Off-type variants stored under the `term` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_term(&self) -> impl Iterator<Item = &Shared<Term>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term))
            .filter_map(|(_, child)| match child {
                ItemChild::Term(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `term`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_term(&self) -> Result<&Shared<Term>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                ItemChild::Term(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "term" }),
            },
            _ => Err(CstError::ChildCount {
                label: "term",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `term`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_term(&self) -> Result<Option<&Shared<Term>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                ItemChild::Term(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "term" }),
            },
            _ => Err(CstError::ChildCount {
                label: "term",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term))
                    .count(),
            }),
        }
    }

    /// Append a child with label `term`, accepting `Term` or `Shared<Term>`.
    pub fn append_term(&mut self, child: impl Into<Shared<Term>>) {
        self.children.push((Some(ItemLabel::Term), ItemChild::Term(child.into())));
    }

    /// Append multiple children with label `term`.
    pub fn extend_term(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Term>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(ItemLabel::Term), ItemChild::Term(c.into()))));
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

    fn append_disposition(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::Disposition), native_child));
        Ok(())
    }

    fn extend_disposition(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::Disposition), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_disposition(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::Disposition))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_disposition(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Disposition) {
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
                "Expected one disposition child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_disposition: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_disposition(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Disposition) {
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
                "Expected at most one disposition child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_label(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::Label), native_child));
        Ok(())
    }

    fn extend_label(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::Label), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_label(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::Label))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_label(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Label) {
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
                "Expected one label child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_label: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_label(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Label) {
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
                "Expected at most one label child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_quantifier(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::Quantifier), native_child));
        Ok(())
    }

    fn extend_quantifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::Quantifier), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_quantifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::Quantifier))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_quantifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Quantifier) {
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
                "Expected one quantifier child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_quantifier: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_quantifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Quantifier) {
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
                "Expected at most one quantifier child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_term(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(ItemLabel::Term), native_child));
        Ok(())
    }

    fn extend_term(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(ItemLabel::Term), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_term(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(ItemLabel::Term))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_term(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Term) {
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
                "Expected one term child but have {count}"
            )));
        }
        first.expect("invariant: Item.child_term: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_term(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(ItemLabel::Term) {
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
                "Expected at most one term child but have at least 2",
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
// TermLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Term_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `TermLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Term_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TermLabel {
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "LITERAL")]
    Literal,
    #[pyo3(name = "REGEX")]
    Regex,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TermLabel {
    Alternatives,
    Identifier,
    Literal,
    Regex,
}

#[cfg(feature = "python")]
#[pymethods]
impl TermLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            TermLabel::Alternatives => "Term.Label.ALTERNATIVES",
            TermLabel::Identifier => "Term.Label.IDENTIFIER",
            TermLabel::Literal => "Term.Label.LITERAL",
            TermLabel::Regex => "Term.Label.REGEX",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<TermLabel>() {
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

/// Child value enum for `Term` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum TermChild {
    Alternatives(Shared<Alternatives>),
    Identifier(Shared<Identifier>),
    Literal(Shared<Literal>),
    RawString(Shared<RawString>),
    Trivia(Shared<Trivia>),
}

impl PartialEq for TermChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (TermChild::Alternatives(a), TermChild::Alternatives(b)) => a == b,
            (TermChild::Identifier(a), TermChild::Identifier(b)) => a == b,
            (TermChild::Literal(a), TermChild::Literal(b)) => a == b,
            (TermChild::RawString(a), TermChild::RawString(b)) => a == b,
            (TermChild::Trivia(a), TermChild::Trivia(b)) => a == b,
            _ => false,
        }
    }
}

impl TermChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Alternatives(s) => Some(DropWorklistItem::Alternatives(s)),
            Self::Identifier(s) => Some(DropWorklistItem::Identifier(s)),
            Self::Literal(s) => Some(DropWorklistItem::Literal(s)),
            Self::RawString(s) => Some(DropWorklistItem::RawString(s)),
            Self::Trivia(s) => Some(DropWorklistItem::Trivia(s)),
        }
    }
}

#[cfg(feature = "python")]
impl TermChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Alternatives(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyAlternatives { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
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
            Self::RawString(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyRawString { inner: shared.clone() };
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
        if obj.is_instance_of::<PyAlternatives>() {
            let handle: PyRef<PyAlternatives> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::Alternatives(shared));
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
        if obj.is_instance_of::<PyRawString>() {
            let handle: PyRef<PyRawString> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::RawString(shared));
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
            "Term: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Term
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Term`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
/// Teardown is iterative: bounded stack at any depth.
#[derive(Clone)]
pub struct Term {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<TermLabel>, TermChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Term {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Term")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Term {
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

impl PartialEq for Term {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Term {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Term {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Term
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
    pub fn children(&self) -> &[(Option<TermLabel>, TermChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<TermLabel>, child: TermChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<TermLabel>, TermChild), CstError> {
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

    /// Return an iterator over `Shared<Alternatives>` children labelled `alternatives`.
    ///
    /// Off-type variants stored under the `alternatives` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_alternatives(&self) -> impl Iterator<Item = &Shared<Alternatives>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives))
            .filter_map(|(_, child)| match child {
                TermChild::Alternatives(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `alternatives`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_alternatives(&self) -> Result<&Shared<Alternatives>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TermChild::Alternatives(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "alternatives" }),
            },
            _ => Err(CstError::ChildCount {
                label: "alternatives",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `alternatives`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_alternatives(&self) -> Result<Option<&Shared<Alternatives>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TermChild::Alternatives(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "alternatives" }),
            },
            _ => Err(CstError::ChildCount {
                label: "alternatives",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives))
                    .count(),
            }),
        }
    }

    /// Append a child with label `alternatives`, accepting `Alternatives` or `Shared<Alternatives>`.
    pub fn append_alternatives(&mut self, child: impl Into<Shared<Alternatives>>) {
        self.children.push((Some(TermLabel::Alternatives), TermChild::Alternatives(child.into())));
    }

    /// Append multiple children with label `alternatives`.
    pub fn extend_alternatives(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Alternatives>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TermLabel::Alternatives), TermChild::Alternatives(c.into()))));
    }

    /// Return an iterator over `Shared<Identifier>` children labelled `identifier`.
    ///
    /// Off-type variants stored under the `identifier` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_identifier(&self) -> impl Iterator<Item = &Shared<Identifier>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier))
            .filter_map(|(_, child)| match child {
                TermChild::Identifier(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `identifier`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_identifier(&self) -> Result<&Shared<Identifier>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TermChild::Identifier(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "identifier" }),
            },
            _ => Err(CstError::ChildCount {
                label: "identifier",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `identifier`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_identifier(&self) -> Result<Option<&Shared<Identifier>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TermChild::Identifier(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "identifier" }),
            },
            _ => Err(CstError::ChildCount {
                label: "identifier",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier))
                    .count(),
            }),
        }
    }

    /// Append a child with label `identifier`, accepting `Identifier` or `Shared<Identifier>`.
    pub fn append_identifier(&mut self, child: impl Into<Shared<Identifier>>) {
        self.children.push((Some(TermLabel::Identifier), TermChild::Identifier(child.into())));
    }

    /// Append multiple children with label `identifier`.
    pub fn extend_identifier(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Identifier>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TermLabel::Identifier), TermChild::Identifier(c.into()))));
    }

    /// Return an iterator over `Shared<Literal>` children labelled `literal`.
    ///
    /// Off-type variants stored under the `literal` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_literal(&self) -> impl Iterator<Item = &Shared<Literal>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal))
            .filter_map(|(_, child)| match child {
                TermChild::Literal(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `literal`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_literal(&self) -> Result<&Shared<Literal>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TermChild::Literal(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "literal" }),
            },
            _ => Err(CstError::ChildCount {
                label: "literal",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `literal`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_literal(&self) -> Result<Option<&Shared<Literal>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TermChild::Literal(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "literal" }),
            },
            _ => Err(CstError::ChildCount {
                label: "literal",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal))
                    .count(),
            }),
        }
    }

    /// Append a child with label `literal`, accepting `Literal` or `Shared<Literal>`.
    pub fn append_literal(&mut self, child: impl Into<Shared<Literal>>) {
        self.children.push((Some(TermLabel::Literal), TermChild::Literal(child.into())));
    }

    /// Append multiple children with label `literal`.
    pub fn extend_literal(&mut self, children: impl IntoIterator<Item = impl Into<Shared<Literal>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TermLabel::Literal), TermChild::Literal(c.into()))));
    }

    /// Return an iterator over `Shared<RawString>` children labelled `regex`.
    ///
    /// Off-type variants stored under the `regex` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_regex(&self) -> impl Iterator<Item = &Shared<RawString>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex))
            .filter_map(|(_, child)| match child {
                TermChild::RawString(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `regex`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_regex(&self) -> Result<&Shared<RawString>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TermChild::RawString(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "regex" }),
            },
            _ => Err(CstError::ChildCount {
                label: "regex",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `regex`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_regex(&self) -> Result<Option<&Shared<RawString>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TermChild::RawString(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "regex" }),
            },
            _ => Err(CstError::ChildCount {
                label: "regex",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex))
                    .count(),
            }),
        }
    }

    /// Append a child with label `regex`, accepting `RawString` or `Shared<RawString>`.
    pub fn append_regex(&mut self, child: impl Into<Shared<RawString>>) {
        self.children.push((Some(TermLabel::Regex), TermChild::RawString(child.into())));
    }

    /// Append multiple children with label `regex`.
    pub fn extend_regex(&mut self, children: impl IntoIterator<Item = impl Into<Shared<RawString>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TermLabel::Regex), TermChild::RawString(c.into()))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Term")]
pub struct PyTerm {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Term>,
}

#[cfg(feature = "python")]
impl PyTerm {
    /// Return a reference to the inner `Shared<Term>`.
    pub fn shared(&self) -> &Shared<Term> {
        &self.inner
    }

    /// Wrap a `Shared<Term>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Term>) -> PyResult<Py<PyTerm>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyTerm { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyTerm>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyTerm {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyTerm>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Term {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyTerm { inner: shared };
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
        NodeKind::Term
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(TermLabel::type_object(py).into_any().unbind())
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
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<TermLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Term.append: label argument is not a Term_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<TermLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Term.extend: label argument is not a Term_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyTerm) -> PyResult<()> {
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

    fn append_alternatives(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TermLabel::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TermLabel::Alternatives), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TermLabel::Alternatives))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Alternatives) {
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
                "Expected one alternatives child but have {count}"
            )));
        }
        first.expect("invariant: Term.child_alternatives: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Alternatives) {
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
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_identifier(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TermLabel::Identifier), native_child));
        Ok(())
    }

    fn extend_identifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TermLabel::Identifier), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_identifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TermLabel::Identifier))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_identifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Identifier) {
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
                "Expected one identifier child but have {count}"
            )));
        }
        first.expect("invariant: Term.child_identifier: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_identifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Identifier) {
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
                "Expected at most one identifier child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_literal(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TermLabel::Literal), native_child));
        Ok(())
    }

    fn extend_literal(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TermLabel::Literal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_literal(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TermLabel::Literal))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_literal(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Literal) {
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
                "Expected one literal child but have {count}"
            )));
        }
        first.expect("invariant: Term.child_literal: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_literal(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Literal) {
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
                "Expected at most one literal child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_regex(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TermLabel::Regex), native_child));
        Ok(())
    }

    fn extend_regex(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TermLabel::Regex), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_regex(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TermLabel::Regex))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_regex(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Regex) {
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
                "Expected one regex child but have {count}"
            )));
        }
        first.expect("invariant: Term.child_regex: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_regex(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TermLabel::Regex) {
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
                "Expected at most one regex child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyTerm>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyTerm> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Term'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Term(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// DispositionLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Disposition_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `DispositionLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Disposition_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum DispositionLabel {
    #[pyo3(name = "INCLUDE")]
    Include,
    #[pyo3(name = "INLINE")]
    Inline,
    #[pyo3(name = "SUPPRESS")]
    Suppress,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum DispositionLabel {
    Include,
    Inline,
    Suppress,
}

#[cfg(feature = "python")]
#[pymethods]
impl DispositionLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            DispositionLabel::Include => "Disposition.Label.INCLUDE",
            DispositionLabel::Inline => "Disposition.Label.INLINE",
            DispositionLabel::Suppress => "Disposition.Label.SUPPRESS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<DispositionLabel>() {
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

/// Child value enum for `Disposition` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum DispositionChild {
    Span(Span),
}

impl PartialEq for DispositionChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (DispositionChild::Span(a), DispositionChild::Span(b)) => a == b,
        }
    }
}

impl DispositionChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl DispositionChild {
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
            "Disposition: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Disposition
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Disposition`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Disposition {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<DispositionLabel>, DispositionChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Disposition {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Disposition")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Disposition {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Disposition {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Disposition {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Disposition
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
    pub fn children(&self) -> &[(Option<DispositionLabel>, DispositionChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<DispositionLabel>, child: DispositionChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<DispositionLabel>, DispositionChild), CstError> {
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

    /// Return an iterator over `Span` children labelled `include`.
    ///
    /// Off-type variants stored under the `include` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_include(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include))
            .map(|(_, child)| match child { DispositionChild::Span(s) => s })
    }

    /// Return the single child labelled `include`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_include(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "include",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `include`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_include(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "include",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `include`.
    pub fn append_include(&mut self, span: Span) {
        self.children.push((Some(DispositionLabel::Include), DispositionChild::Span(span)));
    }

    /// Append multiple `Span` children with label `include`.
    pub fn extend_include(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(DispositionLabel::Include), DispositionChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `inline`.
    ///
    /// Off-type variants stored under the `inline` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_inline(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline))
            .map(|(_, child)| match child { DispositionChild::Span(s) => s })
    }

    /// Return the single child labelled `inline`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_inline(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "inline",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `inline`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_inline(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "inline",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `inline`.
    pub fn append_inline(&mut self, span: Span) {
        self.children.push((Some(DispositionLabel::Inline), DispositionChild::Span(span)));
    }

    /// Append multiple `Span` children with label `inline`.
    pub fn extend_inline(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(DispositionLabel::Inline), DispositionChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `suppress`.
    ///
    /// Off-type variants stored under the `suppress` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_suppress(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress))
            .map(|(_, child)| match child { DispositionChild::Span(s) => s })
    }

    /// Return the single child labelled `suppress`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_suppress(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "suppress",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `suppress`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_suppress(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                DispositionChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "suppress",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `suppress`.
    pub fn append_suppress(&mut self, span: Span) {
        self.children.push((Some(DispositionLabel::Suppress), DispositionChild::Span(span)));
    }

    /// Append multiple `Span` children with label `suppress`.
    pub fn extend_suppress(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(DispositionLabel::Suppress), DispositionChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Disposition")]
pub struct PyDisposition {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Disposition>,
}

#[cfg(feature = "python")]
impl PyDisposition {
    /// Return a reference to the inner `Shared<Disposition>`.
    pub fn shared(&self) -> &Shared<Disposition> {
        &self.inner
    }

    /// Wrap a `Shared<Disposition>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Disposition>) -> PyResult<Py<PyDisposition>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyDisposition { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyDisposition>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyDisposition {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyDisposition>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Disposition {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyDisposition { inner: shared };
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
        NodeKind::Disposition
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(DispositionLabel::type_object(py).into_any().unbind())
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
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<DispositionLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Disposition.append: label argument is not a Disposition_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<DispositionLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Disposition.extend: label argument is not a Disposition_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyDisposition) -> PyResult<()> {
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

    fn append_include(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(DispositionLabel::Include), native_child));
        Ok(())
    }

    fn extend_include(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(DispositionLabel::Include), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_include(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Include))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_include(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Include) {
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
                "Expected one include child but have {count}"
            )));
        }
        first.expect("invariant: Disposition.child_include: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_include(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Include) {
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
                "Expected at most one include child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_inline(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(DispositionLabel::Inline), native_child));
        Ok(())
    }

    fn extend_inline(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(DispositionLabel::Inline), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inline(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Inline))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_inline(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Inline) {
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
                "Expected one inline child but have {count}"
            )));
        }
        first.expect("invariant: Disposition.child_inline: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_inline(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Inline) {
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
                "Expected at most one inline child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_suppress(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(DispositionLabel::Suppress), native_child));
        Ok(())
    }

    fn extend_suppress(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(DispositionLabel::Suppress), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_suppress(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(DispositionLabel::Suppress))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_suppress(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Suppress) {
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
                "Expected one suppress child but have {count}"
            )));
        }
        first.expect("invariant: Disposition.child_suppress: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_suppress(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(DispositionLabel::Suppress) {
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
                "Expected at most one suppress child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyDisposition>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyDisposition> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Disposition'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Disposition(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// QuantifierLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `Quantifier_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `QuantifierLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Quantifier_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum QuantifierLabel {
    #[pyo3(name = "ONE_OR_MORE")]
    OneOrMore,
    #[pyo3(name = "OPTIONAL")]
    Optional,
    #[pyo3(name = "ZERO_OR_MORE")]
    ZeroOrMore,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum QuantifierLabel {
    OneOrMore,
    Optional,
    ZeroOrMore,
}

#[cfg(feature = "python")]
#[pymethods]
impl QuantifierLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            QuantifierLabel::OneOrMore => "Quantifier.Label.ONE_OR_MORE",
            QuantifierLabel::Optional => "Quantifier.Label.OPTIONAL",
            QuantifierLabel::ZeroOrMore => "Quantifier.Label.ZERO_OR_MORE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<QuantifierLabel>() {
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

/// Child value enum for `Quantifier` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum QuantifierChild {
    Span(Span),
}

impl PartialEq for QuantifierChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (QuantifierChild::Span(a), QuantifierChild::Span(b)) => a == b,
        }
    }
}

impl QuantifierChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl QuantifierChild {
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
            "Quantifier: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// Quantifier
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `Quantifier`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct Quantifier {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<QuantifierLabel>, QuantifierChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for Quantifier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Quantifier")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for Quantifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Quantifier {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        Quantifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::Quantifier
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
    pub fn children(&self) -> &[(Option<QuantifierLabel>, QuantifierChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<QuantifierLabel>, child: QuantifierChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<QuantifierLabel>, QuantifierChild), CstError> {
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

    /// Return an iterator over `Span` children labelled `one_or_more`.
    ///
    /// Off-type variants stored under the `one_or_more` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_one_or_more(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore))
            .map(|(_, child)| match child { QuantifierChild::Span(s) => s })
    }

    /// Return the single child labelled `one_or_more`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_one_or_more(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "one_or_more",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `one_or_more`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_one_or_more(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "one_or_more",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `one_or_more`.
    pub fn append_one_or_more(&mut self, span: Span) {
        self.children.push((Some(QuantifierLabel::OneOrMore), QuantifierChild::Span(span)));
    }

    /// Append multiple `Span` children with label `one_or_more`.
    pub fn extend_one_or_more(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(QuantifierLabel::OneOrMore), QuantifierChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `optional`.
    ///
    /// Off-type variants stored under the `optional` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_optional(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional))
            .map(|(_, child)| match child { QuantifierChild::Span(s) => s })
    }

    /// Return the single child labelled `optional`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_optional(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "optional",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `optional`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_optional(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "optional",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `optional`.
    pub fn append_optional(&mut self, span: Span) {
        self.children.push((Some(QuantifierLabel::Optional), QuantifierChild::Span(span)));
    }

    /// Append multiple `Span` children with label `optional`.
    pub fn extend_optional(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(QuantifierLabel::Optional), QuantifierChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `zero_or_more`.
    ///
    /// Off-type variants stored under the `zero_or_more` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_zero_or_more(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore))
            .map(|(_, child)| match child { QuantifierChild::Span(s) => s })
    }

    /// Return the single child labelled `zero_or_more`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_zero_or_more(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "zero_or_more",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `zero_or_more`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_zero_or_more(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                QuantifierChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "zero_or_more",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `zero_or_more`.
    pub fn append_zero_or_more(&mut self, span: Span) {
        self.children.push((Some(QuantifierLabel::ZeroOrMore), QuantifierChild::Span(span)));
    }

    /// Append multiple `Span` children with label `zero_or_more`.
    pub fn extend_zero_or_more(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(QuantifierLabel::ZeroOrMore), QuantifierChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Quantifier")]
pub struct PyQuantifier {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<Quantifier>,
}

#[cfg(feature = "python")]
impl PyQuantifier {
    /// Return a reference to the inner `Shared<Quantifier>`.
    pub fn shared(&self) -> &Shared<Quantifier> {
        &self.inner
    }

    /// Wrap a `Shared<Quantifier>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Quantifier>) -> PyResult<Py<PyQuantifier>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyQuantifier { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyQuantifier>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyQuantifier {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyQuantifier>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = Quantifier {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyQuantifier { inner: shared };
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
        NodeKind::Quantifier
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(QuantifierLabel::type_object(py).into_any().unbind())
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
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<QuantifierLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Quantifier.append: label argument is not a Quantifier_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<QuantifierLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "Quantifier.extend: label argument is not a Quantifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyQuantifier) -> PyResult<()> {
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

    fn append_one_or_more(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(QuantifierLabel::OneOrMore), native_child));
        Ok(())
    }

    fn extend_one_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(QuantifierLabel::OneOrMore), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_one_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::OneOrMore))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_one_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::OneOrMore) {
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
                "Expected one one_or_more child but have {count}"
            )));
        }
        first.expect("invariant: Quantifier.child_one_or_more: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_one_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::OneOrMore) {
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
                "Expected at most one one_or_more child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_optional(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(QuantifierLabel::Optional), native_child));
        Ok(())
    }

    fn extend_optional(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(QuantifierLabel::Optional), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_optional(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::Optional))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_optional(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::Optional) {
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
                "Expected one optional child but have {count}"
            )));
        }
        first.expect("invariant: Quantifier.child_optional: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_optional(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::Optional) {
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
                "Expected at most one optional child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_zero_or_more(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(QuantifierLabel::ZeroOrMore), native_child));
        Ok(())
    }

    fn extend_zero_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(QuantifierLabel::ZeroOrMore), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_zero_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(QuantifierLabel::ZeroOrMore))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_zero_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::ZeroOrMore) {
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
                "Expected one zero_or_more child but have {count}"
            )));
        }
        first.expect("invariant: Quantifier.child_zero_or_more: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_zero_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(QuantifierLabel::ZeroOrMore) {
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
                "Expected at most one zero_or_more child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyQuantifier>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyQuantifier> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Quantifier'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "Quantifier(span={span_repr}, children=[<{children_len} child(ren)>])"
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
// RawStringLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `RawString_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `RawStringLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "RawString_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RawStringLabel {
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum RawStringLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl RawStringLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            RawStringLabel::Value => "RawString.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RawStringLabel>() {
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

/// Child value enum for `RawString` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum RawStringChild {
    Span(Span),
}

impl PartialEq for RawStringChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (RawStringChild::Span(a), RawStringChild::Span(b)) => a == b,
        }
    }
}

impl RawStringChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl RawStringChild {
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
            "RawString: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// RawString
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `RawString`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct RawString {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RawStringLabel>, RawStringChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for RawString {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("RawString")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for RawString {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl RawString {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        RawString {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::RawString
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
    pub fn children(&self) -> &[(Option<RawStringLabel>, RawStringChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<RawStringLabel>, child: RawStringChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<RawStringLabel>, RawStringChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value))
            .map(|(_, child)| match child { RawStringChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                RawStringChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value))
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
            .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                RawStringChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(RawStringLabel::Value), RawStringChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(RawStringLabel::Value), RawStringChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "RawString")]
pub struct PyRawString {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<RawString>,
}

#[cfg(feature = "python")]
impl PyRawString {
    /// Return a reference to the inner `Shared<RawString>`.
    pub fn shared(&self) -> &Shared<RawString> {
        &self.inner
    }

    /// Wrap a `Shared<RawString>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<RawString>) -> PyResult<Py<PyRawString>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyRawString { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyRawString>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyRawString {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyRawString>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = RawString {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyRawString { inner: shared };
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
        NodeKind::RawString
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RawStringLabel::type_object(py).into_any().unbind())
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
        let native_child = RawStringChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<RawStringLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "RawString.append: label argument is not a RawString_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RawStringLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "RawString.extend: label argument is not a RawString_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RawStringChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyRawString) -> PyResult<()> {
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
        let native_child = RawStringChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RawStringLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RawStringChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RawStringLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(RawStringLabel::Value))
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
                if *lbl == Some(RawStringLabel::Value) {
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
        first.expect("invariant: RawString.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(RawStringLabel::Value) {
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
        if !other.is_instance_of::<PyRawString>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyRawString> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'RawString'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "RawString(span={span_repr}, children=[<{children_len} child(ren)>])"
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
    #[pyo3(name = "VALUE")]
    Value,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LiteralLabel {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl LiteralLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LiteralLabel::Value => "Literal.Label.VALUE",
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

    /// Return an iterator over `Span` children labelled `value`.
    ///
    /// Off-type variants stored under the `value` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_value(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value))
            .map(|(_, child)| match child { LiteralChild::Span(s) => s })
    }

    /// Return the single child labelled `value`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_value(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value))
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
            .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LiteralChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "value",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `value`.
    pub fn append_value(&mut self, span: Span) {
        self.children.push((Some(LiteralLabel::Value), LiteralChild::Span(span)));
    }

    /// Append multiple `Span` children with label `value`.
    pub fn extend_value(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LiteralLabel::Value), LiteralChild::Span(s))));
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

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LiteralLabel::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LiteralLabel::Value), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(LiteralLabel::Value))
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
                if *lbl == Some(LiteralLabel::Value) {
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
        first.expect("invariant: Literal.child_value: count==1 but first==None; logic error")
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
                if *lbl == Some(LiteralLabel::Value) {
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
    #[pyo3(name = "BLOCK_COMMENT")]
    BlockComment,
    #[pyo3(name = "LINE_COMMENT")]
    LineComment,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum TriviaLabel {
    BlockComment,
    LineComment,
}

#[cfg(feature = "python")]
#[pymethods]
impl TriviaLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            TriviaLabel::BlockComment => "Trivia.Label.BLOCK_COMMENT",
            TriviaLabel::LineComment => "Trivia.Label.LINE_COMMENT",
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
    BlockComment(Shared<BlockComment>),
    LineComment(Shared<LineComment>),
}

impl PartialEq for TriviaChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (TriviaChild::Span(a), TriviaChild::Span(b)) => a == b,
            (TriviaChild::BlockComment(a), TriviaChild::BlockComment(b)) => a == b,
            (TriviaChild::LineComment(a), TriviaChild::LineComment(b)) => a == b,
            _ => false,
        }
    }
}

impl TriviaChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
            Self::BlockComment(s) => Some(DropWorklistItem::BlockComment(s)),
            Self::LineComment(s) => Some(DropWorklistItem::LineComment(s)),
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
            Self::BlockComment(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyBlockComment { inner: shared.clone() };
                    Py::new(py, handle).map(|p| p.into_any())
                })
            }
            Self::LineComment(shared) => {
                let addr = shared.arc_ptr();
                registry::get_or_insert_with(py, addr, || {
                    let handle = PyLineComment { inner: shared.clone() };
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
        if obj.is_instance_of::<PyBlockComment>() {
            let handle: PyRef<PyBlockComment> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::BlockComment(shared));
        }
        if obj.is_instance_of::<PyLineComment>() {
            let handle: PyRef<PyLineComment> = obj.extract()?;
            let shared = handle.inner.clone();
            let addr = shared.arc_ptr();
            // Hand-in: register this Python handle as canonical for its Shared.
            drop(handle); // release the PyRef before calling Python
            // Propagate registry errors: a swallowed Err here would leave the
            // handle unregistered, causing the next wrap-out to mint a different
            // object and silently break is-stability.
            registry::register_if_absent(py, addr, obj)?;
            return Ok(Self::LineComment(shared));
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
/// Teardown is iterative: bounded stack at any depth.
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

// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for Trivia {
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

    /// Return an iterator over `Shared<BlockComment>` children labelled `block_comment`.
    ///
    /// Off-type variants stored under the `block_comment` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_block_comment(&self) -> impl Iterator<Item = &Shared<BlockComment>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment))
            .filter_map(|(_, child)| match child {
                TriviaChild::BlockComment(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `block_comment`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_block_comment(&self) -> Result<&Shared<BlockComment>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TriviaChild::BlockComment(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "block_comment" }),
            },
            _ => Err(CstError::ChildCount {
                label: "block_comment",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `block_comment`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_block_comment(&self) -> Result<Option<&Shared<BlockComment>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TriviaChild::BlockComment(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "block_comment" }),
            },
            _ => Err(CstError::ChildCount {
                label: "block_comment",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment))
                    .count(),
            }),
        }
    }

    /// Append a child with label `block_comment`, accepting `BlockComment` or `Shared<BlockComment>`.
    pub fn append_block_comment(&mut self, child: impl Into<Shared<BlockComment>>) {
        self.children.push((Some(TriviaLabel::BlockComment), TriviaChild::BlockComment(child.into())));
    }

    /// Append multiple children with label `block_comment`.
    pub fn extend_block_comment(&mut self, children: impl IntoIterator<Item = impl Into<Shared<BlockComment>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TriviaLabel::BlockComment), TriviaChild::BlockComment(c.into()))));
    }

    /// Return an iterator over `Shared<LineComment>` children labelled `line_comment`.
    ///
    /// Off-type variants stored under the `line_comment` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_line_comment(&self) -> impl Iterator<Item = &Shared<LineComment>> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment))
            .filter_map(|(_, child)| match child {
                TriviaChild::LineComment(s) => Some(s),
                _ => None,
            })
    }

    /// Return the single child labelled `line_comment`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_line_comment(&self) -> Result<&Shared<LineComment>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                TriviaChild::LineComment(s) => Ok(s),
                _ => Err(CstError::UnexpectedChildType { label: "line_comment" }),
            },
            _ => Err(CstError::ChildCount {
                label: "line_comment",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `line_comment`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_line_comment(&self) -> Result<Option<&Shared<LineComment>>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                TriviaChild::LineComment(s) => Ok(Some(s)),
                _ => Err(CstError::UnexpectedChildType { label: "line_comment" }),
            },
            _ => Err(CstError::ChildCount {
                label: "line_comment",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment))
                    .count(),
            }),
        }
    }

    /// Append a child with label `line_comment`, accepting `LineComment` or `Shared<LineComment>`.
    pub fn append_line_comment(&mut self, child: impl Into<Shared<LineComment>>) {
        self.children.push((Some(TriviaLabel::LineComment), TriviaChild::LineComment(child.into())));
    }

    /// Append multiple children with label `line_comment`.
    pub fn extend_line_comment(&mut self, children: impl IntoIterator<Item = impl Into<Shared<LineComment>>>) {
        self.children.extend(children.into_iter().map(|c| (Some(TriviaLabel::LineComment), TriviaChild::LineComment(c.into()))));
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

    fn append_block_comment(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TriviaLabel::BlockComment), native_child));
        Ok(())
    }

    fn extend_block_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TriviaLabel::BlockComment), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_block_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TriviaLabel::BlockComment))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_block_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::BlockComment) {
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
                "Expected one block_comment child but have {count}"
            )));
        }
        first.expect("invariant: Trivia.child_block_comment: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_block_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::BlockComment) {
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
                "Expected at most one block_comment child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_line_comment(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(TriviaLabel::LineComment), native_child));
        Ok(())
    }

    fn extend_line_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(TriviaLabel::LineComment), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_line_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(TriviaLabel::LineComment))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_line_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::LineComment) {
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
                "Expected one line_comment child but have {count}"
            )));
        }
        first.expect("invariant: Trivia.child_line_comment: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_line_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(TriviaLabel::LineComment) {
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
                "Expected at most one line_comment child but have at least 2",
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
// LineCommentLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `LineComment_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `LineCommentLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "LineComment_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LineCommentLabel {
    #[pyo3(name = "CONTENT")]
    Content,
    #[pyo3(name = "PREFIX")]
    Prefix,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum LineCommentLabel {
    Content,
    Prefix,
}

#[cfg(feature = "python")]
#[pymethods]
impl LineCommentLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            LineCommentLabel::Content => "LineComment.Label.CONTENT",
            LineCommentLabel::Prefix => "LineComment.Label.PREFIX",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LineCommentLabel>() {
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

/// Child value enum for `LineComment` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum LineCommentChild {
    Span(Span),
}

impl PartialEq for LineCommentChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (LineCommentChild::Span(a), LineCommentChild::Span(b)) => a == b,
        }
    }
}

impl LineCommentChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl LineCommentChild {
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
            "LineComment: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// LineComment
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `LineComment`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct LineComment {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LineCommentLabel>, LineCommentChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for LineComment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("LineComment")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for LineComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl LineComment {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        LineComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::LineComment
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
    pub fn children(&self) -> &[(Option<LineCommentLabel>, LineCommentChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<LineCommentLabel>, child: LineCommentChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<LineCommentLabel>, LineCommentChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content))
            .map(|(_, child)| match child { LineCommentChild::Span(s) => s })
    }

    /// Return the single child labelled `content`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_content(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LineCommentChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content))
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
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LineCommentChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `content`.
    pub fn append_content(&mut self, span: Span) {
        self.children.push((Some(LineCommentLabel::Content), LineCommentChild::Span(span)));
    }

    /// Append multiple `Span` children with label `content`.
    pub fn extend_content(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LineCommentLabel::Content), LineCommentChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `prefix`.
    ///
    /// Off-type variants stored under the `prefix` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_prefix(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix))
            .map(|(_, child)| match child { LineCommentChild::Span(s) => s })
    }

    /// Return the single child labelled `prefix`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_prefix(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                LineCommentChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "prefix",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `prefix`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_prefix(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                LineCommentChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "prefix",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `prefix`.
    pub fn append_prefix(&mut self, span: Span) {
        self.children.push((Some(LineCommentLabel::Prefix), LineCommentChild::Span(span)));
    }

    /// Append multiple `Span` children with label `prefix`.
    pub fn extend_prefix(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(LineCommentLabel::Prefix), LineCommentChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "LineComment")]
pub struct PyLineComment {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<LineComment>,
}

#[cfg(feature = "python")]
impl PyLineComment {
    /// Return a reference to the inner `Shared<LineComment>`.
    pub fn shared(&self) -> &Shared<LineComment> {
        &self.inner
    }

    /// Wrap a `Shared<LineComment>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<LineComment>) -> PyResult<Py<PyLineComment>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyLineComment { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyLineComment>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyLineComment {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyLineComment>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = LineComment {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyLineComment { inner: shared };
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
        NodeKind::LineComment
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(LineCommentLabel::type_object(py).into_any().unbind())
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
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<LineCommentLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LineComment.append: label argument is not a LineComment_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LineCommentLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "LineComment.extend: label argument is not a LineComment_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyLineComment) -> PyResult<()> {
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
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LineCommentLabel::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LineCommentLabel::Content), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Content))
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
                if *lbl == Some(LineCommentLabel::Content) {
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
        first.expect("invariant: LineComment.child_content: count==1 but first==None; logic error")
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
                if *lbl == Some(LineCommentLabel::Content) {
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

    fn append_prefix(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LineCommentLabel::Prefix), native_child));
        Ok(())
    }

    fn extend_prefix(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LineCommentLabel::Prefix), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_prefix(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(LineCommentLabel::Prefix))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_prefix(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LineCommentLabel::Prefix) {
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
                "Expected one prefix child but have {count}"
            )));
        }
        first.expect("invariant: LineComment.child_prefix: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_prefix(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(LineCommentLabel::Prefix) {
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
                "Expected at most one prefix child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyLineComment>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyLineComment> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'LineComment'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "LineComment(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// BlockCommentLabel
// ───────────────────────────────────────────────────────────────────────────

/// Label discriminant enum for children of this node type.
///
/// Python-visible name is `BlockComment_Label` (preserved for compatibility).
/// Rust consumers use the CamelCase `BlockCommentLabel` name.
#[cfg(feature = "python")]
#[pyclass(frozen, name = "BlockComment_Label")]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum BlockCommentLabel {
    #[pyo3(name = "CONTENT")]
    Content,
    #[pyo3(name = "END")]
    End,
    #[pyo3(name = "START")]
    Start,
}

#[cfg(not(feature = "python"))]
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum BlockCommentLabel {
    Content,
    End,
    Start,
}

#[cfg(feature = "python")]
#[pymethods]
impl BlockCommentLabel {
    fn __repr__(&self) -> &'static str {
        match self {
            BlockCommentLabel::Content => "BlockComment.Label.CONTENT",
            BlockCommentLabel::End => "BlockComment.Label.END",
            BlockCommentLabel::Start => "BlockComment.Label.START",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<BlockCommentLabel>() {
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

/// Child value enum for `BlockComment` nodes.
///
/// Node-typed variants hold `Shared<T>` (`Arc<RwLock<T>>`); `Clone` is shallow
/// (increments the reference count, does not copy the node).
#[derive(Clone, Debug)]
pub enum BlockCommentChild {
    Span(Span),
}

impl PartialEq for BlockCommentChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (BlockCommentChild::Span(a), BlockCommentChild::Span(b)) => a == b,
        }
    }
}

impl BlockCommentChild {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
        }
    }
}

#[cfg(feature = "python")]
impl BlockCommentChild {
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
            "BlockComment: unsupported child type {}",
            obj.get_type().name()?
        )))
    }
}

// ───────────────────────────────────────────────────────────────────────────
// BlockComment
// ───────────────────────────────────────────────────────────────────────────

/// CST data struct for `BlockComment`. See [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
///
/// `Debug` output is non-recursive: prints span + child count only. Traverse via `children()` to inspect subtrees.
#[derive(Clone)]
pub struct BlockComment {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<BlockCommentLabel>, BlockCommentChild)>,
}

// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for BlockComment {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("BlockComment")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}

impl PartialEq for BlockComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl BlockComment {
    /// Construct a node with the given span and no children. GIL-free.
    pub fn new(span: Span) -> Self {
        BlockComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return the [`NodeKind`] discriminant for this node type.
    pub fn kind(&self) -> NodeKind {
        NodeKind::BlockComment
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
    pub fn children(&self) -> &[(Option<BlockCommentLabel>, BlockCommentChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the children `Vec`.
    ///
    /// No type-checking is performed: any child variant may be stored under
    /// any label. Per-label typed mutators (`append_<lbl>`, `extend_<lbl>`)
    /// provide type-constrained alternatives.
    pub fn push_child(&mut self, label: Option<BlockCommentLabel>, child: BlockCommentChild) {
        self.children.push((label, child));
    }

    /// Return the single child (any label), or `Err` if there is not exactly one.
    ///
    /// Mirrors the Python `child()` method: count violation → `CstError::ChildCount`.
    pub fn child(&self) -> Result<&(Option<BlockCommentLabel>, BlockCommentChild), CstError> {
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
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content))
            .map(|(_, child)| match child { BlockCommentChild::Span(s) => s })
    }

    /// Return the single child labelled `content`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_content(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content))
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
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "content",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `content`.
    pub fn append_content(&mut self, span: Span) {
        self.children.push((Some(BlockCommentLabel::Content), BlockCommentChild::Span(span)));
    }

    /// Append multiple `Span` children with label `content`.
    pub fn extend_content(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(BlockCommentLabel::Content), BlockCommentChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `end`.
    ///
    /// Off-type variants stored under the `end` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_end(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End))
            .map(|(_, child)| match child { BlockCommentChild::Span(s) => s })
    }

    /// Return the single child labelled `end`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_end(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "end",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `end`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_end(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "end",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `end`.
    pub fn append_end(&mut self, span: Span) {
        self.children.push((Some(BlockCommentLabel::End), BlockCommentChild::Span(span)));
    }

    /// Append multiple `Span` children with label `end`.
    pub fn extend_end(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(BlockCommentLabel::End), BlockCommentChild::Span(s))));
    }

    /// Return an iterator over `Span` children labelled `start`.
    ///
    /// Off-type variants stored under the `start` label are silently skipped.
    /// Use `children()` (the untyped slice) for a lossless view.
    pub fn children_start(&self) -> impl Iterator<Item = &Span> + '_ {
        self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start))
            .map(|(_, child)| match child { BlockCommentChild::Span(s) => s })
    }

    /// Return the single child labelled `start`, or `Err` if not exactly one.
    ///
    /// Count is checked by label match first (`CstError::ChildCount`); if the
    /// count is valid and the surviving child has the wrong variant type,
    /// `CstError::UnexpectedChildType` is returned (single-typed labels only).
    pub fn child_start(&self) -> Result<&Span, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start));
        match (it.next(), it.next()) {
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(s),
            },
            _ => Err(CstError::ChildCount {
                label: "start",
                expected: "1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start))
                    .count(),
            }),
        }
    }

    /// Return the optional child labelled `start`, or `Err` if more than one.
    ///
    /// Returns `Ok(None)` for zero, `Ok(Some(...))` for one,
    /// `Err(CstError::ChildCount)` for two or more.
    pub fn maybe_start(&self) -> Result<Option<&Span>, CstError> {
        let mut it = self.children.iter()
            .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start));
        match (it.next(), it.next()) {
            (None, _) => Ok(None),
            (Some((_, child)), None) => match child {
                BlockCommentChild::Span(s) => Ok(Some(s)),
            },
            _ => Err(CstError::ChildCount {
                label: "start",
                expected: "0 or 1",
                found: self.children.iter()
                    .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start))
                    .count(),
            }),
        }
    }

    /// Append a `Span` child with label `start`.
    pub fn append_start(&mut self, span: Span) {
        self.children.push((Some(BlockCommentLabel::Start), BlockCommentChild::Span(span)));
    }

    /// Append multiple `Span` children with label `start`.
    pub fn extend_start(&mut self, spans: impl IntoIterator<Item = Span>) {
        self.children.extend(spans.into_iter().map(|s| (Some(BlockCommentLabel::Start), BlockCommentChild::Span(s))));
    }
}

#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "BlockComment")]
pub struct PyBlockComment {
    // Not pub: all external access goes through shared() or to_py_canonical().
    // A pub field would let mixed-app Rust code construct an unregistered handle
    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.
    inner: Shared<BlockComment>,
}

#[cfg(feature = "python")]
impl PyBlockComment {
    /// Return a reference to the inner `Shared<BlockComment>`.
    pub fn shared(&self) -> &Shared<BlockComment> {
        &self.inner
    }

    /// Wrap a `Shared<BlockComment>` into a canonical Python handle,
    /// looking up the registry first so the same handle is returned
    /// for the same `Shared` allocation.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<BlockComment>) -> PyResult<Py<PyBlockComment>> {
        let addr = s.arc_ptr();
        let obj = registry::get_or_insert_with(py, addr, || {
            let handle = PyBlockComment { inner: s.clone() };
            Py::new(py, handle).map(|p| p.into_any())
        })?;
        obj.bind(py).downcast::<PyBlockComment>().map(|b| b.clone().unbind()).map_err(|e| e.into())
    }
}

#[cfg(feature = "python")]
#[pymethods]
impl PyBlockComment {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyBlockComment>> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        let data = BlockComment {
            span: native_span,
            children: Vec::new(),
        };
        let shared = Shared::new(data);
        let addr = shared.arc_ptr();
        let handle = PyBlockComment { inner: shared };
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
        NodeKind::BlockComment
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(BlockCommentLabel::type_object(py).into_any().unbind())
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
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        let native_label = match label {
            None => None,
            Some(lbl) => {
                if let Ok(native_lbl) = lbl.bind(py).extract::<BlockCommentLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "BlockComment.append: label argument is not a BlockComment_Label; got {}",
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<BlockCommentLabel>() {
                    Some(native_lbl)
                } else {
                    return Err(PyTypeError::new_err(format!(
                        "BlockComment.extend: label argument is not a BlockComment_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.inner.write().children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&self, _py: Python<'_>, other: &PyBlockComment) -> PyResult<()> {
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
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockCommentLabel::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockCommentLabel::Content), native_child);
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
                .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Content))
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
                if *lbl == Some(BlockCommentLabel::Content) {
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
        first.expect("invariant: BlockComment.child_content: count==1 but first==None; logic error")
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
                if *lbl == Some(BlockCommentLabel::Content) {
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

    fn append_end(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockCommentLabel::End), native_child));
        Ok(())
    }

    fn extend_end(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockCommentLabel::End), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_end(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::End))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_end(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(BlockCommentLabel::End) {
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
                "Expected one end child but have {count}"
            )));
        }
        first.expect("invariant: BlockComment.child_end: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_end(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(BlockCommentLabel::End) {
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
                "Expected at most one end child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn append_start(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockCommentLabel::Start), native_child));
        Ok(())
    }

    fn extend_start(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockCommentLabel::Start), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_start(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        // Lock scope: filter by label under the read guard, cloning only matching
        // children (Arc bump or Span copy each); drop the guard before to_pyobject,
        // which performs Python work that must not happen while a node lock is held.
        let matching: Vec<_> = {
            let guard = self.inner.read();
            guard.children.iter()
                .filter(|(lbl, _)| *lbl == Some(BlockCommentLabel::Start))
                .map(|(_, child)| child.clone())
                .collect()
        };
        let result = PyList::empty(py);
        for child in &matching {
            result.append(child.to_pyobject(py)?)?;
        }
        Ok(result.unbind())
    }

    fn child_start(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(BlockCommentLabel::Start) {
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
                "Expected one start child but have {count}"
            )));
        }
        first.expect("invariant: BlockComment.child_start: count==1 but first==None; logic error")
            .to_pyobject(py)
    }

    fn maybe_start(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        // Lock scope: count label matches and clone only the first under the guard;
        // drop the guard before to_pyobject / exception raise (Python work).
        let (count, first) = {
            let guard = self.inner.read();
            let mut count = 0usize;
            let mut first = None;
            for (lbl, child) in &guard.children {
                if *lbl == Some(BlockCommentLabel::Start) {
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
                "Expected at most one start child but have at least 2",
            ));
        }
        match first {
            None => Ok(None),
            Some(child) => Ok(Some(child.to_pyobject(py)?)),
        }
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if !other.is_instance_of::<PyBlockComment>() {
            return Ok(py.NotImplemented());
        }
        let other_handle: PyRef<PyBlockComment> = other.extract()?;
        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit
        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.
        let eq = self.inner == other_handle.inner;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'BlockComment'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let guard = self.inner.read();
        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());
        let children_len = guard.children.len();
        format!(
            "BlockComment(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// DropWorklistItem
// ───────────────────────────────────────────────────────────────────────────

// Worklist item for iterative node teardown. See the per-node `impl Drop`.
// Module-private: only used by impl Drop and into_drop_item in this file.
enum DropWorklistItem {
    Alternatives(Shared<Alternatives>),
    BlockComment(Shared<BlockComment>),
    Disposition(Shared<Disposition>),
    Identifier(Shared<Identifier>),
    Item(Shared<Item>),
    Items(Shared<Items>),
    LineComment(Shared<LineComment>),
    Literal(Shared<Literal>),
    Quantifier(Shared<Quantifier>),
    RawString(Shared<RawString>),
    Rule(Shared<Rule>),
    Term(Shared<Term>),
    Trivia(Shared<Trivia>),
}

impl DropWorklistItem {
    fn drain_into(self, worklist: &mut Vec<DropWorklistItem>) {
        // Each arm: if sole owner, steal children (so the node's Drop early-returns
        // instead of recursing through drop glue); then drop `shared`.
        // count==1 → childless node after steal, trivial drop;
        // count>1 → refcount decrement only. Either way, no recursion.
        match self {
            DropWorklistItem::Alternatives(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::BlockComment(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Disposition(shared) => {
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
            DropWorklistItem::Item(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Items(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::LineComment(shared) => {
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
            DropWorklistItem::Quantifier(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::RawString(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Rule(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
            }
            DropWorklistItem::Term(shared) => {
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
    module.add_class::<GrammarLabel>()?;
    module.add_class::<PyGrammar>()?;
    module.add_class::<RuleLabel>()?;
    module.add_class::<PyRule>()?;
    module.add_class::<AlternativesLabel>()?;
    module.add_class::<PyAlternatives>()?;
    module.add_class::<ItemsLabel>()?;
    module.add_class::<PyItems>()?;
    module.add_class::<ItemLabel>()?;
    module.add_class::<PyItem>()?;
    module.add_class::<TermLabel>()?;
    module.add_class::<PyTerm>()?;
    module.add_class::<DispositionLabel>()?;
    module.add_class::<PyDisposition>()?;
    module.add_class::<QuantifierLabel>()?;
    module.add_class::<PyQuantifier>()?;
    module.add_class::<IdentifierLabel>()?;
    module.add_class::<PyIdentifier>()?;
    module.add_class::<RawStringLabel>()?;
    module.add_class::<PyRawString>()?;
    module.add_class::<LiteralLabel>()?;
    module.add_class::<PyLiteral>()?;
    module.add_class::<TriviaLabel>()?;
    module.add_class::<PyTrivia>()?;
    module.add_class::<LineCommentLabel>()?;
    module.add_class::<PyLineComment>()?;
    module.add_class::<BlockCommentLabel>()?;
    module.add_class::<PyBlockComment>()?;
    Ok(())
}
