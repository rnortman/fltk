use fltk_cst_core::{extract_span, get_source_text_type, get_span_type, Span};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple, PyType};
use pyo3::PyTypeInfo;


// ───────────────────────────────────────────────────────────────────────────
// NodeKind
// ───────────────────────────────────────────────────────────────────────────

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
#[pyclass(frozen, name = "Grammar_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Grammar_Label {
    #[pyo3(name = "RULE")]
    Rule,
}

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

// GrammarChild — native child value enum for Grammar
#[derive(Clone)]
pub enum GrammarChild {
    Rule(Box<Rule>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, _span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Rule(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Rule>() {
            let node: PyRef<Rule> = obj.extract()?;
            return Ok(Self::Rule(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Grammar {
    span: Span,
    children: Vec<(Option<Grammar_Label>, GrammarChild)>,
}

impl PartialEq for Grammar {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Grammar {
    fn clone(&self) -> Self {
        Grammar {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Grammar {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Grammar {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Grammar_Label>, GrammarChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Grammar_Label>, child: GrammarChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Grammar {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Grammar {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Grammar.append: label argument is not a Grammar_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GrammarChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Grammar>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_rule(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = GrammarChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Grammar_Label::Rule), native_child));
        Ok(())
    }

    fn extend_rule(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = GrammarChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Grammar_Label::Rule), native_child));
        }
        Ok(())
    }

    fn children_rule(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Grammar_Label::Rule) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_rule(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Grammar_Label::Rule) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Grammar_Label::Rule) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Grammar>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Grammar> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Grammar'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Grammar(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Rule_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Rule_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Rule_Label {
    #[pyo3(name = "ALTERNATIVES")]
    Alternatives,
    #[pyo3(name = "NAME")]
    Name,
}

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

// RuleChild — native child value enum for Rule
#[derive(Clone)]
pub enum RuleChild {
    Alternatives(Box<Alternatives>),
    Identifier(Box<Identifier>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, _span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Alternatives(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Alternatives>() {
            let node: PyRef<Alternatives> = obj.extract()?;
            return Ok(Self::Alternatives(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Identifier>() {
            let node: PyRef<Identifier> = obj.extract()?;
            return Ok(Self::Identifier(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Rule {
    span: Span,
    children: Vec<(Option<Rule_Label>, RuleChild)>,
}

impl PartialEq for Rule {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Rule {
    fn clone(&self) -> Self {
        Rule {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Rule {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Rule {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Rule_Label>, RuleChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Rule_Label>, child: RuleChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Rule {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Rule {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Rule.append: label argument is not a Rule_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Rule>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_alternatives(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Rule_Label::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Rule_Label::Alternatives), native_child));
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Alternatives) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_name(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RuleChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Rule_Label::Name), native_child));
        Ok(())
    }

    fn extend_name(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RuleChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Rule_Label::Name), native_child));
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Name) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Rule_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Rule>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Rule> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Rule'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Rule(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Alternatives_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Alternatives_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Alternatives_Label {
    #[pyo3(name = "ITEMS")]
    Items,
}

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

// AlternativesChild — native child value enum for Alternatives
#[derive(Clone)]
pub enum AlternativesChild {
    Items(Box<Items>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, _span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Items(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Items>() {
            let node: PyRef<Items> = obj.extract()?;
            return Ok(Self::Items(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Alternatives {
    span: Span,
    children: Vec<(Option<Alternatives_Label>, AlternativesChild)>,
}

impl PartialEq for Alternatives {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Alternatives {
    fn clone(&self) -> Self {
        Alternatives {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Alternatives {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Alternatives {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Alternatives_Label>, AlternativesChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Alternatives_Label>, child: AlternativesChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Alternatives {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Alternatives {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Alternatives.append: label argument is not a Alternatives_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AlternativesChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Alternatives>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_items(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = AlternativesChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Alternatives_Label::Items), native_child));
        Ok(())
    }

    fn extend_items(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = AlternativesChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Alternatives_Label::Items), native_child));
        }
        Ok(())
    }

    fn children_items(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Alternatives_Label::Items) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_items(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Alternatives_Label::Items) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Alternatives_Label::Items) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Alternatives>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Alternatives> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Alternatives'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Alternatives(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Items_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// ItemsChild — native child value enum for Items
#[derive(Clone)]
pub enum ItemsChild {
    Span(Span),
    Item(Box<Item>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
            }
            Self::Item(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
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
        if obj.is_instance_of::<Item>() {
            let node: PyRef<Item> = obj.extract()?;
            return Ok(Self::Item(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Items {
    span: Span,
    children: Vec<(Option<Items_Label>, ItemsChild)>,
}

impl PartialEq for Items {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Items {
    fn clone(&self) -> Self {
        Items {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Items {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Items {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Items_Label>, ItemsChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Items_Label>, child: ItemsChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Items {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Items {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Items.append: label argument is not a Items_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Items>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_item(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Items_Label::Item), native_child));
        Ok(())
    }

    fn extend_item(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Items_Label::Item), native_child));
        }
        Ok(())
    }

    fn children_item(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_no_ws(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Items_Label::NoWs), native_child));
        Ok(())
    }

    fn extend_no_ws(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Items_Label::NoWs), native_child));
        }
        Ok(())
    }

    fn children_no_ws(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_ws_allowed(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Items_Label::WsAllowed), native_child));
        Ok(())
    }

    fn extend_ws_allowed(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Items_Label::WsAllowed), native_child));
        }
        Ok(())
    }

    fn children_ws_allowed(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_ws_required(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemsChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Items_Label::WsRequired), native_child));
        Ok(())
    }

    fn extend_ws_required(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemsChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Items_Label::WsRequired), native_child));
        }
        Ok(())
    }

    fn children_ws_required(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Items>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Items> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Items'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Items(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Item_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// ItemChild — native child value enum for Item
#[derive(Clone)]
pub enum ItemChild {
    Disposition(Box<Disposition>),
    Identifier(Box<Identifier>),
    Quantifier(Box<Quantifier>),
    Term(Box<Term>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, _span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Disposition(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Quantifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Term(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Disposition>() {
            let node: PyRef<Disposition> = obj.extract()?;
            return Ok(Self::Disposition(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Identifier>() {
            let node: PyRef<Identifier> = obj.extract()?;
            return Ok(Self::Identifier(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Quantifier>() {
            let node: PyRef<Quantifier> = obj.extract()?;
            return Ok(Self::Quantifier(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Term>() {
            let node: PyRef<Term> = obj.extract()?;
            return Ok(Self::Term(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Item {
    span: Span,
    children: Vec<(Option<Item_Label>, ItemChild)>,
}

impl PartialEq for Item {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Item {
    fn clone(&self) -> Self {
        Item {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Item {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Item {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Item_Label>, ItemChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Item_Label>, child: ItemChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Item {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Item {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Item.append: label argument is not a Item_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Item>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_disposition(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Item_Label::Disposition), native_child));
        Ok(())
    }

    fn extend_disposition(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Item_Label::Disposition), native_child));
        }
        Ok(())
    }

    fn children_disposition(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Disposition) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_disposition(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Disposition) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Disposition) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_label(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Item_Label::Label), native_child));
        Ok(())
    }

    fn extend_label(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Item_Label::Label), native_child));
        }
        Ok(())
    }

    fn children_label(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Label) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_label(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Label) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Label) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_quantifier(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Item_Label::Quantifier), native_child));
        Ok(())
    }

    fn extend_quantifier(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Item_Label::Quantifier), native_child));
        }
        Ok(())
    }

    fn children_quantifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Quantifier) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_quantifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Quantifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Quantifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_term(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ItemChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Item_Label::Term), native_child));
        Ok(())
    }

    fn extend_term(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ItemChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Item_Label::Term), native_child));
        }
        Ok(())
    }

    fn children_term(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Term) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_term(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Term) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Item_Label::Term) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Item>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Item> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Item'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Item(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Term_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// TermChild — native child value enum for Term
#[derive(Clone)]
pub enum TermChild {
    Alternatives(Box<Alternatives>),
    Identifier(Box<Identifier>),
    Literal(Box<Literal>),
    RawString(Box<RawString>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>, _span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Alternatives(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Literal(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::RawString(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Alternatives>() {
            let node: PyRef<Alternatives> = obj.extract()?;
            return Ok(Self::Alternatives(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Identifier>() {
            let node: PyRef<Identifier> = obj.extract()?;
            return Ok(Self::Identifier(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Literal>() {
            let node: PyRef<Literal> = obj.extract()?;
            return Ok(Self::Literal(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<RawString>() {
            let node: PyRef<RawString> = obj.extract()?;
            return Ok(Self::RawString(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Term {
    span: Span,
    children: Vec<(Option<Term_Label>, TermChild)>,
}

impl PartialEq for Term {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Term {
    fn clone(&self) -> Self {
        Term {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Term {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Term {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Term_Label>, TermChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Term_Label>, child: TermChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Term {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Term {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Term.append: label argument is not a Term_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Term>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_alternatives(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Term_Label::Alternatives), native_child));
        Ok(())
    }

    fn extend_alternatives(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Term_Label::Alternatives), native_child));
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Alternatives) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Alternatives) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_identifier(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Term_Label::Identifier), native_child));
        Ok(())
    }

    fn extend_identifier(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Term_Label::Identifier), native_child));
        }
        Ok(())
    }

    fn children_identifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Identifier) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_identifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Identifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Identifier) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_literal(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Term_Label::Literal), native_child));
        Ok(())
    }

    fn extend_literal(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Term_Label::Literal), native_child));
        }
        Ok(())
    }

    fn children_literal(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Literal) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_literal(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Literal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Literal) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_regex(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TermChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Term_Label::Regex), native_child));
        Ok(())
    }

    fn extend_regex(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TermChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Term_Label::Regex), native_child));
        }
        Ok(())
    }

    fn children_regex(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Regex) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_regex(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Regex) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Term_Label::Regex) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Term>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Term> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Term'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Term(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Disposition_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// DispositionChild — native child value enum for Disposition
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

impl DispositionChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct Disposition {
    span: Span,
    children: Vec<(Option<Disposition_Label>, DispositionChild)>,
}

impl PartialEq for Disposition {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Disposition {
    fn clone(&self) -> Self {
        Disposition {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Disposition {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Disposition {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Disposition_Label>, DispositionChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Disposition_Label>, child: DispositionChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Disposition {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Disposition {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Disposition.append: label argument is not a Disposition_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Disposition>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_include(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Disposition_Label::Include), native_child));
        Ok(())
    }

    fn extend_include(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Disposition_Label::Include), native_child));
        }
        Ok(())
    }

    fn children_include(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Include) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_include(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Include) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Include) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_inline(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Disposition_Label::Inline), native_child));
        Ok(())
    }

    fn extend_inline(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Disposition_Label::Inline), native_child));
        }
        Ok(())
    }

    fn children_inline(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Inline) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_inline(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Inline) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Inline) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_suppress(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = DispositionChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Disposition_Label::Suppress), native_child));
        Ok(())
    }

    fn extend_suppress(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = DispositionChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Disposition_Label::Suppress), native_child));
        }
        Ok(())
    }

    fn children_suppress(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Suppress) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_suppress(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Suppress) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Disposition_Label::Suppress) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Disposition>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Disposition> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Disposition'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Disposition(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Quantifier_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// QuantifierChild — native child value enum for Quantifier
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

impl QuantifierChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct Quantifier {
    span: Span,
    children: Vec<(Option<Quantifier_Label>, QuantifierChild)>,
}

impl PartialEq for Quantifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Quantifier {
    fn clone(&self) -> Self {
        Quantifier {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Quantifier {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Quantifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Quantifier_Label>, QuantifierChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Quantifier_Label>, child: QuantifierChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Quantifier {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Quantifier {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Quantifier.append: label argument is not a Quantifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Quantifier>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_one_or_more(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Quantifier_Label::OneOrMore), native_child));
        Ok(())
    }

    fn extend_one_or_more(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Quantifier_Label::OneOrMore), native_child));
        }
        Ok(())
    }

    fn children_one_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::OneOrMore) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_one_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::OneOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::OneOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_optional(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Quantifier_Label::Optional), native_child));
        Ok(())
    }

    fn extend_optional(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Quantifier_Label::Optional), native_child));
        }
        Ok(())
    }

    fn children_optional(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::Optional) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_optional(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::Optional) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::Optional) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_zero_or_more(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = QuantifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Quantifier_Label::ZeroOrMore), native_child));
        Ok(())
    }

    fn extend_zero_or_more(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = QuantifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Quantifier_Label::ZeroOrMore), native_child));
        }
        Ok(())
    }

    fn children_zero_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::ZeroOrMore) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_zero_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::ZeroOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Quantifier_Label::ZeroOrMore) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Quantifier>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Quantifier> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Quantifier'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Quantifier(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Identifier_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Identifier_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Identifier_Label {
    #[pyo3(name = "NAME")]
    Name,
}

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

// IdentifierChild — native child value enum for Identifier
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

impl IdentifierChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct Identifier {
    span: Span,
    children: Vec<(Option<Identifier_Label>, IdentifierChild)>,
}

impl PartialEq for Identifier {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Identifier {
    fn clone(&self) -> Self {
        Identifier {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Identifier {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Identifier {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Identifier_Label>, IdentifierChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Identifier_Label>, child: IdentifierChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Identifier {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Identifier {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Identifier.append: label argument is not a Identifier_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = IdentifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Identifier>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_name(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = IdentifierChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Identifier_Label::Name), native_child));
        Ok(())
    }

    fn extend_name(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = IdentifierChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Identifier_Label::Name), native_child));
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Identifier>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Identifier> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Identifier'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Identifier(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// RawString_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "RawString_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum RawString_Label {
    #[pyo3(name = "VALUE")]
    Value,
}

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

// RawStringChild — native child value enum for RawString
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

impl RawStringChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct RawString {
    span: Span,
    children: Vec<(Option<RawString_Label>, RawStringChild)>,
}

impl PartialEq for RawString {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for RawString {
    fn clone(&self) -> Self {
        RawString {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl RawString {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        RawString {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<RawString_Label>, RawStringChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<RawString_Label>, child: RawStringChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl RawString {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(RawString {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "RawString.append: label argument is not a RawString_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RawStringChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, RawString>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_value(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = RawStringChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(RawString_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = RawStringChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(RawString_Label::Value), native_child));
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(RawString_Label::Value) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(RawString_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(RawString_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<RawString>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<RawString> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'RawString'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "RawString(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Literal_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Literal_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    #[pyo3(name = "VALUE")]
    Value,
}

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

// LiteralChild — native child value enum for Literal
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

impl LiteralChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct Literal {
    span: Span,
    children: Vec<(Option<Literal_Label>, LiteralChild)>,
}

impl PartialEq for Literal {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Literal {
    fn clone(&self) -> Self {
        Literal {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Literal {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Literal {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Literal_Label>, LiteralChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Literal_Label>, child: LiteralChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Literal {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Literal {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Literal.append: label argument is not a Literal_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Literal>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_value(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Literal_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Literal_Label::Value), native_child));
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::Value) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::Value) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Literal>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Literal> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Literal'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Literal(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Trivia_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Trivia_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Trivia_Label {
    #[pyo3(name = "BLOCK_COMMENT")]
    BlockComment,
    #[pyo3(name = "LINE_COMMENT")]
    LineComment,
}

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

// TriviaChild — native child value enum for Trivia
#[derive(Clone)]
pub enum TriviaChild {
    Span(Span),
    BlockComment(Box<BlockComment>),
    LineComment(Box<LineComment>),
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
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
            }
            Self::BlockComment(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::LineComment(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
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
        if obj.is_instance_of::<BlockComment>() {
            let node: PyRef<BlockComment> = obj.extract()?;
            return Ok(Self::BlockComment(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<LineComment>() {
            let node: PyRef<LineComment> = obj.extract()?;
            return Ok(Self::LineComment(Box::new((*node).clone())));
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

#[pyclass]
pub struct Trivia {
    span: Span,
    children: Vec<(Option<Trivia_Label>, TriviaChild)>,
}

impl PartialEq for Trivia {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Trivia {
    fn clone(&self) -> Self {
        Trivia {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Trivia {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Trivia {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Trivia_Label>, TriviaChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Trivia_Label>, child: TriviaChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Trivia {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Trivia {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "Trivia.append: label argument is not a Trivia_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Trivia>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_block_comment(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Trivia_Label::BlockComment), native_child));
        Ok(())
    }

    fn extend_block_comment(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Trivia_Label::BlockComment), native_child));
        }
        Ok(())
    }

    fn children_block_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::BlockComment) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_block_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::BlockComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::BlockComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_line_comment(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Trivia_Label::LineComment), native_child));
        Ok(())
    }

    fn extend_line_comment(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Trivia_Label::LineComment), native_child));
        }
        Ok(())
    }

    fn children_line_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::LineComment) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_line_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::LineComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::LineComment) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<Trivia>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Trivia> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Trivia'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Trivia(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// LineComment_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "LineComment_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum LineComment_Label {
    #[pyo3(name = "CONTENT")]
    Content,
    #[pyo3(name = "PREFIX")]
    Prefix,
}

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

// LineCommentChild — native child value enum for LineComment
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

impl LineCommentChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct LineComment {
    span: Span,
    children: Vec<(Option<LineComment_Label>, LineCommentChild)>,
}

impl PartialEq for LineComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for LineComment {
    fn clone(&self) -> Self {
        LineComment {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl LineComment {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        LineComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<LineComment_Label>, LineCommentChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<LineComment_Label>, child: LineCommentChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl LineComment {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(LineComment {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "LineComment.append: label argument is not a LineComment_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, LineComment>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_content(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(LineComment_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(LineComment_Label::Content), native_child));
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Content) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_prefix(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LineCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(LineComment_Label::Prefix), native_child));
        Ok(())
    }

    fn extend_prefix(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LineCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(LineComment_Label::Prefix), native_child));
        }
        Ok(())
    }

    fn children_prefix(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Prefix) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_prefix(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Prefix) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(LineComment_Label::Prefix) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<LineComment>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<LineComment> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'LineComment'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "LineComment(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// BlockComment_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// BlockCommentChild — native child value enum for BlockComment
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

impl BlockCommentChild {
    fn to_pyobject(&self, py: Python<'_>, span_type: &Bound<'_, PyType>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // Preserve source: if span carries source, construct a canonical
                // fltk._native.SourceText from the full text string and use it
                // to build a source-bearing Python Span (cross-cdylib safe).
                if let Some(full_text) = s.source_full_text_str() {
                    let st_type = get_source_text_type(py)?;
                    let py_src = st_type.call1((full_text.as_str(),))?;
                    span_type.call_method1("with_source", (s.start(), s.end(), py_src)).map(|b| b.unbind())
                } else {
                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())
                }
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

#[pyclass]
pub struct BlockComment {
    span: Span,
    children: Vec<(Option<BlockComment_Label>, BlockCommentChild)>,
}

impl PartialEq for BlockComment {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for BlockComment {
    fn clone(&self) -> Self {
        BlockComment {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl BlockComment {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        BlockComment {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<BlockComment_Label>, BlockCommentChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<BlockComment_Label>, child: BlockCommentChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl BlockComment {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(BlockComment {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source: if the stored span carries source, construct a canonical
        // fltk._native.SourceText from the full text string (cross-cdylib safe).
        let span_cls = get_span_type(py)?;
        if let Some(full_text) = self.span.source_full_text_str() {
            let st_type = get_source_text_type(py)?;
            let py_src = st_type.call1((full_text.as_str(),))?;
            span_cls
                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))
                .map(|b| b.unbind())
        } else {
            span_cls
                .call1((self.span.start(), self.span.end()))
                .map(|b| b.unbind())
        }
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            let label_obj: PyObject = match label {
                None => py.None(),
                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
            };
            let child_obj = child.to_pyobject(py, &span_type)?;
            let tup = PyTuple::new(py, [label_obj, child_obj])?;
            result.append(tup)?;
        }
        Ok(result.unbind())
    }

    #[pyo3(signature = (child, label = None))]
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        self.children.push((native_label, native_child));
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &mut self,
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
                        "BlockComment.append: label argument is not a BlockComment_Label; got {}",
                        lbl.bind(py).get_type().name()?
                    )));
                }
            }
        };
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, BlockComment>) -> PyResult<()> {
        for (label, child) in &other.children {
            self.children.push((label.clone(), child.clone()));
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let n = self.children.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        let span_type = get_span_type(py)?;
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py, &span_type)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_content(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(BlockComment_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(BlockComment_Label::Content), native_child));
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Content) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Content) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_end(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(BlockComment_Label::End), native_child));
        Ok(())
    }

    fn extend_end(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(BlockComment_Label::End), native_child));
        }
        Ok(())
    }

    fn children_end(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::End) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_end(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::End) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::End) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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

    fn append_start(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = BlockCommentChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(BlockComment_Label::Start), native_child));
        Ok(())
    }

    fn extend_start(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = BlockCommentChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(BlockComment_Label::Start), native_child));
        }
        Ok(())
    }

    fn children_start(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let span_type = get_span_type(py)?;
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Start) {
                result.append(child.to_pyobject(py, &span_type)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_start(&self, py: Python<'_>) -> PyResult<PyObject> {
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Start) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        let span_type = get_span_type(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(BlockComment_Label::Start) {
                count += 1;
                if count == 1 {
                    found = Some(child.to_pyobject(py, &span_type)?);
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
        if !other.is_instance_of::<BlockComment>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<BlockComment> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'BlockComment'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "BlockComment(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<Grammar_Label>()?;
    module.add_class::<Grammar>()?;
    module.add_class::<Rule_Label>()?;
    module.add_class::<Rule>()?;
    module.add_class::<Alternatives_Label>()?;
    module.add_class::<Alternatives>()?;
    module.add_class::<Items_Label>()?;
    module.add_class::<Items>()?;
    module.add_class::<Item_Label>()?;
    module.add_class::<Item>()?;
    module.add_class::<Term_Label>()?;
    module.add_class::<Term>()?;
    module.add_class::<Disposition_Label>()?;
    module.add_class::<Disposition>()?;
    module.add_class::<Quantifier_Label>()?;
    module.add_class::<Quantifier>()?;
    module.add_class::<Identifier_Label>()?;
    module.add_class::<Identifier>()?;
    module.add_class::<RawString_Label>()?;
    module.add_class::<RawString>()?;
    module.add_class::<Literal_Label>()?;
    module.add_class::<Literal>()?;
    module.add_class::<Trivia_Label>()?;
    module.add_class::<Trivia>()?;
    module.add_class::<LineComment_Label>()?;
    module.add_class::<LineComment>()?;
    module.add_class::<BlockComment_Label>()?;
    module.add_class::<BlockComment>()?;
    Ok(())
}
