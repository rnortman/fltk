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
#[derive(Clone, PartialEq, Eq, Hash)]
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
// Grammar_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Grammar_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Grammar_Label {
    #[pyo3(name = "RULE")]
    Rule,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Grammar_Label {
    Rule,
}

#[cfg(feature = "python")]
#[pymethods]
impl Grammar_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Grammar_Label::Rule => "Grammar.Label.RULE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Grammar_Label>() {
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

// GrammarChild — child value enum for Grammar
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Grammar`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Grammar {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Grammar_Label>, GrammarChild)>,
}

impl PartialEq for Grammar {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Grammar {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Grammar {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Grammar_Label>, GrammarChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Grammar_Label>, child: GrammarChild) {
        self.children.push((label, child));
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
        Ok(Grammar_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Grammar_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Grammar_Label>() {
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

    fn append_rule(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = GrammarChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Grammar_Label::Rule), native_child));
        Ok(())
    }

    fn extend_rule(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GrammarChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Grammar_Label::Rule), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_rule(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Grammar_Label::Rule) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_rule(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Grammar_Label::Rule) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one rule child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Grammar.child_rule: count==1 but found==None; logic error"))
    }

    fn maybe_rule(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Grammar_Label::Rule) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one rule child but have at least 2",
            ));
        }
        Ok(found)
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
// Rule_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Rule_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Rule_Label {
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "NAME")]
    Name,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Rule_Label {
    Alternatives,
    Name,
}

#[cfg(feature = "python")]
#[pymethods]
impl Rule_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Rule_Label::Alternatives => "Rule.Label.ALTERNATIVES",
            Rule_Label::Name => "Rule.Label.NAME",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Rule_Label>() {
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

// RuleChild — child value enum for Rule
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Rule`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Rule {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Rule_Label>, RuleChild)>,
}

impl PartialEq for Rule {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Rule {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Rule {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Rule_Label>, RuleChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Rule_Label>, child: RuleChild) {
        self.children.push((label, child));
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
        Ok(Rule_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Rule_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Rule_Label>() {
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

    fn append_alternatives(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Rule_Label::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Rule_Label::Alternatives), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Rule_Label::Alternatives) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Rule_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one alternatives child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Rule.child_alternatives: count==1 but found==None; logic error"))
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Rule_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_name(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Rule_Label::Name), native_child));
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Rule_Label::Name), native_child);
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
            if *lbl == Some(Rule_Label::Name) {
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
            if *lbl == Some(Rule_Label::Name) {
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
        Ok(found.expect("invariant: Rule.child_name: count==1 but found==None; logic error"))
    }

    fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Rule_Label::Name) {
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
// Alternatives_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Alternatives_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Alternatives_Label {
    #[pyo3(name = "ITEMS")]
    Items,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Alternatives_Label {
    Items,
}

#[cfg(feature = "python")]
#[pymethods]
impl Alternatives_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Alternatives_Label::Items => "Alternatives.Label.ITEMS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Alternatives_Label>() {
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

// AlternativesChild — child value enum for Alternatives
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Alternatives`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Alternatives {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Alternatives_Label>, AlternativesChild)>,
}

impl PartialEq for Alternatives {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Alternatives {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Alternatives {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Alternatives_Label>, AlternativesChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Alternatives_Label>, child: AlternativesChild) {
        self.children.push((label, child));
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
        Ok(Alternatives_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Alternatives_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Alternatives_Label>() {
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

    fn append_items(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = AlternativesChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Alternatives_Label::Items), native_child));
        Ok(())
    }

    fn extend_items(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AlternativesChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Alternatives_Label::Items), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_items(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Alternatives_Label::Items) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_items(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Alternatives_Label::Items) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one items child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Alternatives.child_items: count==1 but found==None; logic error"))
    }

    fn maybe_items(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Alternatives_Label::Items) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one items child but have at least 2",
            ));
        }
        Ok(found)
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
// Items_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Items_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Items_Label {
    #[pyo3(name = "ITEM")]
    Item,
    #[pyo3(name = "NO_WS")]
    NoWs,
    #[pyo3(name = "WS_ALLOWED")]
    WsAllowed,
    #[pyo3(name = "WS_REQUIRED")]
    WsRequired,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Items_Label {
    Item,
    NoWs,
    WsAllowed,
    WsRequired,
}

#[cfg(feature = "python")]
#[pymethods]
impl Items_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Items_Label::Item => "Items.Label.ITEM",
            Items_Label::NoWs => "Items.Label.NO_WS",
            Items_Label::WsAllowed => "Items.Label.WS_ALLOWED",
            Items_Label::WsRequired => "Items.Label.WS_REQUIRED",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Items_Label>() {
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

// ItemsChild — child value enum for Items
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Items`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Items {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Items_Label>, ItemsChild)>,
}

impl PartialEq for Items {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Items {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Items {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Items_Label>, ItemsChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Items_Label>, child: ItemsChild) {
        self.children.push((label, child));
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
        Ok(Items_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Items_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Items_Label>() {
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
        self.inner.write().children.push((Some(Items_Label::Item), native_child));
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Items_Label::Item), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_item(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::Item) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::Item) {
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
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::Item) {
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
        self.inner.write().children.push((Some(Items_Label::NoWs), native_child));
        Ok(())
    }

    fn extend_no_ws(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Items_Label::NoWs), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_no_ws(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::NoWs) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::NoWs) {
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
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::NoWs) {
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
        self.inner.write().children.push((Some(Items_Label::WsAllowed), native_child));
        Ok(())
    }

    fn extend_ws_allowed(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Items_Label::WsAllowed), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_ws_allowed(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsAllowed) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsAllowed) {
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
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsAllowed) {
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
        self.inner.write().children.push((Some(Items_Label::WsRequired), native_child));
        Ok(())
    }

    fn extend_ws_required(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Items_Label::WsRequired), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_ws_required(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsRequired) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsRequired) {
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
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Items_Label::WsRequired) {
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
// Item_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Item_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Item_Label {
    #[pyo3(name = "DISPOSITION")]
    Disposition,
    #[pyo3(name = "LABEL")]
    Label,
    #[pyo3(name = "QUANTIFIER")]
    Quantifier,
    #[pyo3(name = "TERM")]
    Term,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Item_Label {
    Disposition,
    Label,
    Quantifier,
    Term,
}

#[cfg(feature = "python")]
#[pymethods]
impl Item_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Item_Label::Disposition => "Item.Label.DISPOSITION",
            Item_Label::Label => "Item.Label.LABEL",
            Item_Label::Quantifier => "Item.Label.QUANTIFIER",
            Item_Label::Term => "Item.Label.TERM",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Item_Label>() {
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

// ItemChild — child value enum for Item
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Item`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Item {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Item_Label>, ItemChild)>,
}

impl PartialEq for Item {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Item {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Item {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Item_Label>, ItemChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Item_Label>, child: ItemChild) {
        self.children.push((label, child));
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
        Ok(Item_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Item_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Item_Label>() {
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

    fn append_disposition(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Item_Label::Disposition), native_child));
        Ok(())
    }

    fn extend_disposition(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Item_Label::Disposition), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_disposition(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Disposition) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_disposition(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Disposition) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one disposition child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_disposition: count==1 but found==None; logic error"))
    }

    fn maybe_disposition(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Disposition) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one disposition child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_label(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Item_Label::Label), native_child));
        Ok(())
    }

    fn extend_label(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Item_Label::Label), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_label(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Label) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_label(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Label) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one label child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_label: count==1 but found==None; logic error"))
    }

    fn maybe_label(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Label) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one label child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_quantifier(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Item_Label::Quantifier), native_child));
        Ok(())
    }

    fn extend_quantifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Item_Label::Quantifier), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_quantifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Quantifier) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_quantifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Quantifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one quantifier child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_quantifier: count==1 but found==None; logic error"))
    }

    fn maybe_quantifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Quantifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one quantifier child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_term(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Item_Label::Term), native_child));
        Ok(())
    }

    fn extend_term(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Item_Label::Term), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_term(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Term) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_term(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Term) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one term child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_term: count==1 but found==None; logic error"))
    }

    fn maybe_term(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Item_Label::Term) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one term child but have at least 2",
            ));
        }
        Ok(found)
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
// Term_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Term_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Term_Label {
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "LITERAL")]
    Literal,
    #[pyo3(name = "REGEX")]
    Regex,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Term_Label {
    Alternatives,
    Identifier,
    Literal,
    Regex,
}

#[cfg(feature = "python")]
#[pymethods]
impl Term_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Term_Label::Alternatives => "Term.Label.ALTERNATIVES",
            Term_Label::Identifier => "Term.Label.IDENTIFIER",
            Term_Label::Literal => "Term.Label.LITERAL",
            Term_Label::Regex => "Term.Label.REGEX",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Term_Label>() {
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

// TermChild — child value enum for Term
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Term`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Term {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Term_Label>, TermChild)>,
}

impl PartialEq for Term {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Term {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Term {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Term_Label>, TermChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Term_Label>, child: TermChild) {
        self.children.push((label, child));
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
        Ok(Term_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Term_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Term_Label>() {
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

    fn append_alternatives(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Term_Label::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Term_Label::Alternatives), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Alternatives) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one alternatives child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_alternatives: count==1 but found==None; logic error"))
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_identifier(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Term_Label::Identifier), native_child));
        Ok(())
    }

    fn extend_identifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Term_Label::Identifier), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_identifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Identifier) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_identifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Identifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one identifier child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_identifier: count==1 but found==None; logic error"))
    }

    fn maybe_identifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Identifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one identifier child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_literal(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Term_Label::Literal), native_child));
        Ok(())
    }

    fn extend_literal(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Term_Label::Literal), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_literal(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Literal) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_literal(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Literal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one literal child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_literal: count==1 but found==None; logic error"))
    }

    fn maybe_literal(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Literal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one literal child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_regex(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Term_Label::Regex), native_child));
        Ok(())
    }

    fn extend_regex(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Term_Label::Regex), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_regex(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Regex) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_regex(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Regex) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one regex child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_regex: count==1 but found==None; logic error"))
    }

    fn maybe_regex(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Term_Label::Regex) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one regex child but have at least 2",
            ));
        }
        Ok(found)
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
// Disposition_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Disposition_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Disposition_Label {
    #[pyo3(name = "INCLUDE")]
    Include,
    #[pyo3(name = "INLINE")]
    Inline,
    #[pyo3(name = "SUPPRESS")]
    Suppress,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Disposition_Label {
    Include,
    Inline,
    Suppress,
}

#[cfg(feature = "python")]
#[pymethods]
impl Disposition_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Disposition_Label::Include => "Disposition.Label.INCLUDE",
            Disposition_Label::Inline => "Disposition.Label.INLINE",
            Disposition_Label::Suppress => "Disposition.Label.SUPPRESS",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Disposition_Label>() {
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

// DispositionChild — child value enum for Disposition
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Disposition`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Disposition {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Disposition_Label>, DispositionChild)>,
}

impl PartialEq for Disposition {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Disposition {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Disposition {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Disposition_Label>, DispositionChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Disposition_Label>, child: DispositionChild) {
        self.children.push((label, child));
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
        Ok(Disposition_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Disposition_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Disposition_Label>() {
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

    fn append_include(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Disposition_Label::Include), native_child));
        Ok(())
    }

    fn extend_include(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Disposition_Label::Include), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_include(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Include) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_include(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Include) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one include child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_include: count==1 but found==None; logic error"))
    }

    fn maybe_include(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Include) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one include child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_inline(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Disposition_Label::Inline), native_child));
        Ok(())
    }

    fn extend_inline(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Disposition_Label::Inline), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_inline(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Inline) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_inline(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Inline) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one inline child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_inline: count==1 but found==None; logic error"))
    }

    fn maybe_inline(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Inline) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one inline child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_suppress(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Disposition_Label::Suppress), native_child));
        Ok(())
    }

    fn extend_suppress(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Disposition_Label::Suppress), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_suppress(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Suppress) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_suppress(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Suppress) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one suppress child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_suppress: count==1 but found==None; logic error"))
    }

    fn maybe_suppress(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Disposition_Label::Suppress) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one suppress child but have at least 2",
            ));
        }
        Ok(found)
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
// Quantifier_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Quantifier_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Quantifier_Label {
    #[pyo3(name = "ONE_OR_MORE")]
    OneOrMore,
    #[pyo3(name = "OPTIONAL")]
    Optional,
    #[pyo3(name = "ZERO_OR_MORE")]
    ZeroOrMore,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Quantifier_Label {
    OneOrMore,
    Optional,
    ZeroOrMore,
}

#[cfg(feature = "python")]
#[pymethods]
impl Quantifier_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Quantifier_Label::OneOrMore => "Quantifier.Label.ONE_OR_MORE",
            Quantifier_Label::Optional => "Quantifier.Label.OPTIONAL",
            Quantifier_Label::ZeroOrMore => "Quantifier.Label.ZERO_OR_MORE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<Quantifier_Label>() {
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

// QuantifierChild — child value enum for Quantifier
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `Quantifier`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct Quantifier {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<Quantifier_Label>, QuantifierChild)>,
}

impl PartialEq for Quantifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Quantifier {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        Quantifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<Quantifier_Label>, QuantifierChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<Quantifier_Label>, child: QuantifierChild) {
        self.children.push((label, child));
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
        Ok(Quantifier_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Quantifier_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<Quantifier_Label>() {
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

    fn append_one_or_more(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Quantifier_Label::OneOrMore), native_child));
        Ok(())
    }

    fn extend_one_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Quantifier_Label::OneOrMore), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_one_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::OneOrMore) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_one_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::OneOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one one_or_more child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_one_or_more: count==1 but found==None; logic error"))
    }

    fn maybe_one_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::OneOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one one_or_more child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_optional(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Quantifier_Label::Optional), native_child));
        Ok(())
    }

    fn extend_optional(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Quantifier_Label::Optional), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_optional(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::Optional) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_optional(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::Optional) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one optional child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_optional: count==1 but found==None; logic error"))
    }

    fn maybe_optional(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::Optional) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one optional child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_zero_or_more(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Quantifier_Label::ZeroOrMore), native_child));
        Ok(())
    }

    fn extend_zero_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Quantifier_Label::ZeroOrMore), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_zero_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::ZeroOrMore) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_zero_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::ZeroOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one zero_or_more child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_zero_or_more: count==1 but found==None; logic error"))
    }

    fn maybe_zero_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Quantifier_Label::ZeroOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one zero_or_more child but have at least 2",
            ));
        }
        Ok(found)
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
// RawString_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "RawString_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum RawString_Label {
    #[pyo3(name = "VALUE")]
    Value,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum RawString_Label {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl RawString_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            RawString_Label::Value => "RawString.Label.VALUE",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<RawString_Label>() {
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

// RawStringChild — child value enum for RawString
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `RawString`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct RawString {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<RawString_Label>, RawStringChild)>,
}

impl PartialEq for RawString {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl RawString {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        RawString {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<RawString_Label>, RawStringChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<RawString_Label>, child: RawStringChild) {
        self.children.push((label, child));
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
        Ok(RawString_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RawString_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<RawString_Label>() {
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

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RawStringChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(RawString_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RawStringChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(RawString_Label::Value), native_child);
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
            if *lbl == Some(RawString_Label::Value) {
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
            if *lbl == Some(RawString_Label::Value) {
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
        Ok(found.expect("invariant: RawString.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(RawString_Label::Value) {
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
// Literal_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "Literal_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    #[pyo3(name = "VALUE")]
    Value,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    Value,
}

#[cfg(feature = "python")]
#[pymethods]
impl Literal_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Literal_Label::Value => "Literal.Label.VALUE",
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

    fn append_value(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Literal_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Literal_Label::Value), native_child);
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
            if *lbl == Some(Literal_Label::Value) {
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
            if *lbl == Some(Literal_Label::Value) {
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
        Ok(found.expect("invariant: Literal.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Literal_Label::Value) {
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
    #[pyo3(name = "BLOCK_COMMENT")]
    BlockComment,
    #[pyo3(name = "LINE_COMMENT")]
    LineComment,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Trivia_Label {
    BlockComment,
    LineComment,
}

#[cfg(feature = "python")]
#[pymethods]
impl Trivia_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            Trivia_Label::BlockComment => "Trivia.Label.BLOCK_COMMENT",
            Trivia_Label::LineComment => "Trivia.Label.LINE_COMMENT",
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

    fn append_block_comment(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Trivia_Label::BlockComment), native_child));
        Ok(())
    }

    fn extend_block_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Trivia_Label::BlockComment), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_block_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::BlockComment) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_block_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::BlockComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one block_comment child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Trivia.child_block_comment: count==1 but found==None; logic error"))
    }

    fn maybe_block_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::BlockComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one block_comment child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_line_comment(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(Trivia_Label::LineComment), native_child));
        Ok(())
    }

    fn extend_line_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(Trivia_Label::LineComment), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_line_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::LineComment) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_line_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::LineComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one line_comment child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Trivia.child_line_comment: count==1 but found==None; logic error"))
    }

    fn maybe_line_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(Trivia_Label::LineComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one line_comment child but have at least 2",
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

// ───────────────────────────────────────────────────────────────────────────
// LineComment_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "LineComment_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum LineComment_Label {
    #[pyo3(name = "CONTENT")]
    Content,
    #[pyo3(name = "PREFIX")]
    Prefix,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum LineComment_Label {
    Content,
    Prefix,
}

#[cfg(feature = "python")]
#[pymethods]
impl LineComment_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            LineComment_Label::Content => "LineComment.Label.CONTENT",
            LineComment_Label::Prefix => "LineComment.Label.PREFIX",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<LineComment_Label>() {
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

// LineCommentChild — child value enum for LineComment
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `LineComment`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct LineComment {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<LineComment_Label>, LineCommentChild)>,
}

impl PartialEq for LineComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl LineComment {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        LineComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<LineComment_Label>, LineCommentChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<LineComment_Label>, child: LineCommentChild) {
        self.children.push((label, child));
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
        Ok(LineComment_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LineComment_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<LineComment_Label>() {
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
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LineComment_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LineComment_Label::Content), native_child);
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
            if *lbl == Some(LineComment_Label::Content) {
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
            if *lbl == Some(LineComment_Label::Content) {
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
        Ok(found.expect("invariant: LineComment.child_content: count==1 but found==None; logic error"))
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(LineComment_Label::Content) {
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

    fn append_prefix(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(LineComment_Label::Prefix), native_child));
        Ok(())
    }

    fn extend_prefix(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(LineComment_Label::Prefix), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_prefix(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(LineComment_Label::Prefix) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_prefix(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(LineComment_Label::Prefix) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one prefix child but have {count}"
            )));
        }
        Ok(found.expect("invariant: LineComment.child_prefix: count==1 but found==None; logic error"))
    }

    fn maybe_prefix(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(LineComment_Label::Prefix) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one prefix child but have at least 2",
            ));
        }
        Ok(found)
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
// BlockComment_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[cfg(feature = "python")]
#[pyclass(frozen, name = "BlockComment_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum BlockComment_Label {
    #[pyo3(name = "CONTENT")]
    Content,
    #[pyo3(name = "END")]
    End,
    #[pyo3(name = "START")]
    Start,
}

#[allow(non_camel_case_types)]
#[cfg(not(feature = "python"))]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum BlockComment_Label {
    Content,
    End,
    Start,
}

#[cfg(feature = "python")]
#[pymethods]
impl BlockComment_Label {
    fn __repr__(&self) -> &'static str {
        match self {
            BlockComment_Label::Content => "BlockComment.Label.CONTENT",
            BlockComment_Label::End => "BlockComment.Label.END",
            BlockComment_Label::Start => "BlockComment.Label.START",
        }
    }

    #[getter]
    fn _fltk_canonical_name(&self) -> &'static str {
        self.__repr__()
    }

    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {
        if let Ok(other_kind) = other.extract::<BlockComment_Label>() {
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

// BlockCommentChild — child value enum for BlockComment
// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.
#[derive(Clone)]
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

/// CST data struct for `BlockComment`. Node-typed children are [`Shared<T>`] —
/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.
#[derive(Clone)]
pub struct BlockComment {
    // Not pub: use span() / children() / push_child() — the stable accessor API.
    // Direct field access bypasses any future validation logic on setters.
    span: Span,
    children: Vec<(Option<BlockComment_Label>, BlockCommentChild)>,
}

impl PartialEq for BlockComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl BlockComment {
    /// Construct a node with the given span and no children.
    /// GIL-free.
    pub fn new(span: Span) -> Self {
        BlockComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored `Span`.
    pub fn span(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the children.
    pub fn children(&self) -> &[(Option<BlockComment_Label>, BlockCommentChild)] {
        self.children.as_slice()
    }

    /// Replace the node's span.
    pub fn set_span(&mut self, span: Span) {
        self.span = span;
    }

    /// Push a child onto the children `Vec`.
    pub fn push_child(&mut self, label: Option<BlockComment_Label>, child: BlockCommentChild) {
        self.children.push((label, child));
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
        Ok(BlockComment_Label::type_object(py).into_any().unbind())
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<BlockComment_Label>() {
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
                if let Ok(native_lbl) = lbl.bind(py).extract::<BlockComment_Label>() {
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
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockComment_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockComment_Label::Content), native_child);
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
            if *lbl == Some(BlockComment_Label::Content) {
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
            if *lbl == Some(BlockComment_Label::Content) {
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
        Ok(found.expect("invariant: BlockComment.child_content: count==1 but found==None; logic error"))
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::Content) {
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

    fn append_end(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockComment_Label::End), native_child));
        Ok(())
    }

    fn extend_end(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockComment_Label::End), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_end(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::End) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_end(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::End) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one end child but have {count}"
            )));
        }
        Ok(found.expect("invariant: BlockComment.child_end: count==1 but found==None; logic error"))
    }

    fn maybe_end(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::End) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one end child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_start(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.inner.write().children.push((Some(BlockComment_Label::Start), native_child));
        Ok(())
    }

    fn extend_start(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            let entry = (Some(BlockComment_Label::Start), native_child);
            self.inner.write().children.push(entry);
        }
        Ok(())
    }

    fn children_start(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let result = PyList::empty(py);
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::Start) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_start(&self, py: Python<'_>) -> PyResult<PyObject> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::Start) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one start child but have {count}"
            )));
        }
        Ok(found.expect("invariant: BlockComment.child_start: count==1 but found==None; logic error"))
    }

    fn maybe_start(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let snapshot: Vec<_> = {
            let guard = self.inner.read();
            guard.children.clone()
        };
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (lbl, child) in &snapshot {
            if *lbl == Some(BlockComment_Label::Start) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py)?);
                }
            }
        }
        if count > 1 {
            return Err(PyValueError::new_err(
                "Expected at most one start child but have at least 2",
            ));
        }
        Ok(found)
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

#[cfg(feature = "python")]
pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<Grammar_Label>()?;
    module.add_class::<PyGrammar>()?;
    module.add_class::<Rule_Label>()?;
    module.add_class::<PyRule>()?;
    module.add_class::<Alternatives_Label>()?;
    module.add_class::<PyAlternatives>()?;
    module.add_class::<Items_Label>()?;
    module.add_class::<PyItems>()?;
    module.add_class::<Item_Label>()?;
    module.add_class::<PyItem>()?;
    module.add_class::<Term_Label>()?;
    module.add_class::<PyTerm>()?;
    module.add_class::<Disposition_Label>()?;
    module.add_class::<PyDisposition>()?;
    module.add_class::<Quantifier_Label>()?;
    module.add_class::<PyQuantifier>()?;
    module.add_class::<Identifier_Label>()?;
    module.add_class::<PyIdentifier>()?;
    module.add_class::<RawString_Label>()?;
    module.add_class::<PyRawString>()?;
    module.add_class::<Literal_Label>()?;
    module.add_class::<PyLiteral>()?;
    module.add_class::<Trivia_Label>()?;
    module.add_class::<PyTrivia>()?;
    module.add_class::<LineComment_Label>()?;
    module.add_class::<PyLineComment>()?;
    module.add_class::<BlockComment_Label>()?;
    module.add_class::<PyBlockComment>()?;
    Ok(())
}
