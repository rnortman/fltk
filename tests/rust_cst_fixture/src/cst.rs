use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};
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
#[pyclass(frozen, name = "Config_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Config_Label {
    #[pyo3(name = "ENTRY")]
    Entry,
}

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

// ConfigChild — native child value enum for Config
#[derive(Clone)]
pub enum ConfigChild {
    Entry(Box<Entry>),
}

impl PartialEq for ConfigChild {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ConfigChild::Entry(a), ConfigChild::Entry(b)) => a == b,
        }
    }
}

impl ConfigChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Entry(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Entry>() {
            let node: PyRef<Entry> = obj.extract()?;
            return Ok(Self::Entry(Box::new((*node).clone())));
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

#[pyclass]
pub struct Config {
    span: Span,
    children: Vec<(Option<Config_Label>, ConfigChild)>,
}

impl PartialEq for Config {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Config {
    fn clone(&self) -> Self {
        Config {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Config {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Config {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Config_Label>, ConfigChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Config_Label>, child: ConfigChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Config {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Config {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ConfigChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Config>) -> PyResult<()> {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_entry(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = ConfigChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Config_Label::Entry), native_child));
        Ok(())
    }

    fn extend_entry(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = ConfigChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Config_Label::Entry), native_child));
        }
        Ok(())
    }

    fn children_entry(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Config_Label::Entry) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_entry(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Config_Label::Entry) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Config_Label::Entry) {
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
        if !other.is_instance_of::<Config>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Config> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Config'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Config(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Entry_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// EntryChild — native child value enum for Entry
#[derive(Clone)]
pub enum EntryChild {
    Identifier(Box<Identifier>),
    Literal(Box<Literal>),
    Operator(Box<Operator>),
    Trivia(Box<Trivia>),
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
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Literal(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Operator(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
            Self::Trivia(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
        }
    }

    fn extract_from_pyobject(
        _py: Python<'_>,
        obj: &Bound<'_, PyAny>,
        _span_type: &Bound<'_, PyType>,
    ) -> PyResult<Self> {
        if obj.is_instance_of::<Identifier>() {
            let node: PyRef<Identifier> = obj.extract()?;
            return Ok(Self::Identifier(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Literal>() {
            let node: PyRef<Literal> = obj.extract()?;
            return Ok(Self::Literal(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Operator>() {
            let node: PyRef<Operator> = obj.extract()?;
            return Ok(Self::Operator(Box::new((*node).clone())));
        }
        if obj.is_instance_of::<Trivia>() {
            let node: PyRef<Trivia> = obj.extract()?;
            return Ok(Self::Trivia(Box::new((*node).clone())));
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

#[pyclass]
pub struct Entry {
    span: Span,
    children: Vec<(Option<Entry_Label>, EntryChild)>,
}

impl PartialEq for Entry {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Entry {
    fn clone(&self) -> Self {
        Entry {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Entry {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Entry {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Entry_Label>, EntryChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Entry_Label>, child: EntryChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Entry {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Entry {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Entry>) -> PyResult<()> {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_key(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Entry_Label::Key), native_child));
        Ok(())
    }

    fn extend_key(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Entry_Label::Key), native_child));
        }
        Ok(())
    }

    fn children_key(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Key) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_key(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Key) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Key) {
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

    fn append_op(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Entry_Label::Op), native_child));
        Ok(())
    }

    fn extend_op(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Entry_Label::Op), native_child));
        }
        Ok(())
    }

    fn children_op(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Op) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_op(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Op) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Op) {
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

    fn append_value(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = EntryChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Entry_Label::Value), native_child));
        Ok(())
    }

    fn extend_value(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = EntryChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Entry_Label::Value), native_child));
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Value) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Value) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Entry_Label::Value) {
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
        if !other.is_instance_of::<Entry>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Entry> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Entry'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Entry(span={span_repr}, children=[<{children_len} child(ren)>])"
        )
    }

}

// ───────────────────────────────────────────────────────────────────────────
// Operator_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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

// OperatorChild — native child value enum for Operator
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

impl OperatorChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // span_to_pyobject: O(1) Arc clone, no string copy; preserves
                // Arc-sharing so multiple reads of the same span merge without error.
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

#[pyclass]
pub struct Operator {
    span: Span,
    children: Vec<(Option<Operator_Label>, OperatorChild)>,
}

impl PartialEq for Operator {
    fn eq(&self, other: &Self) -> bool {
        self.span == other.span && self.children == other.children
    }
}

impl Clone for Operator {
    fn clone(&self) -> Self {
        Operator {
            span: self.span.clone(),
            children: self.children.clone(),
        }
    }
}

impl Operator {
    /// Construct a node with the given span and no children.
    /// No GIL required.
    pub fn new_native(span: Span) -> Self {
        Operator {
            span,
            children: Vec::new(),
        }
    }

    /// Return a reference to the stored native `Span`.
    pub fn span_native(&self) -> &Span {
        &self.span
    }

    /// Return a slice of the native children.
    pub fn children_native(&self) -> &[(Option<Operator_Label>, OperatorChild)] {
        self.children.as_slice()
    }

    /// Push a child onto the native children `Vec`.
    pub fn push_child_native(&mut self, label: Option<Operator_Label>, child: OperatorChild) {
        self.children.push((label, child));
    }
}

#[pymethods]
impl Operator {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {
        let native_span = match span {
            Some(s) => extract_span(py, s)?,
            None => Span::unknown(),
        };
        Ok(Operator {
            span: native_span,
            children: Vec::new(),
        })
    }

    #[getter]
    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {
        // Return a fltk._native.Span so consumers always get the canonical type
        // regardless of which cdylib the node is defined in.
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
    }

    #[setter]
    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        self.span = extract_span(py, value)?;
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {
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
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((native_label.clone(), native_child));
        }
        Ok(())
    }

    fn extend_children(&mut self, other: PyRef<'_, Operator>) -> PyResult<()> {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Operator_Label::Append), native_child));
        Ok(())
    }

    fn extend_append(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Operator_Label::Append), native_child));
        }
        Ok(())
    }

    fn children_append(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Append) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_append(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Append) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Append) {
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

    fn append_assign(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Operator_Label::Assign), native_child));
        Ok(())
    }

    fn extend_assign(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Operator_Label::Assign), native_child));
        }
        Ok(())
    }

    fn children_assign(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Assign) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_assign(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Assign) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Assign) {
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

    fn append_remove(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = OperatorChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Operator_Label::Remove), native_child));
        Ok(())
    }

    fn extend_remove(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = OperatorChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Operator_Label::Remove), native_child));
        }
        Ok(())
    }

    fn children_remove(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Remove) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_remove(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Remove) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Operator_Label::Remove) {
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
        if !other.is_instance_of::<Operator>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Operator> = other.extract()?;
        // Native structural equality: no Python .eq() on stored state
        let eq = self == &*other_node;
        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Operator'"))
    }

    fn __repr__(&self, _py: Python<'_>) -> String {
        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());
        let children_len = self.children.len();
        format!(
            "Operator(span={span_repr}, children=[<{children_len} child(ren)>])"
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
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // span_to_pyobject: O(1) Arc clone, no string copy; preserves
                // Arc-sharing so multiple reads of the same span merge without error.
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
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Identifier_Label::Name) {
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
// Literal_Label
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
#[pyclass(frozen, name = "Literal_Label")]
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Literal_Label {
    #[pyo3(name = "INT_VAL")]
    IntVal,
    #[pyo3(name = "STR_VAL")]
    StrVal,
}

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
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // span_to_pyobject: O(1) Arc clone, no string copy; preserves
                // Arc-sharing so multiple reads of the same span merge without error.
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
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_int_val(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Literal_Label::IntVal), native_child));
        Ok(())
    }

    fn extend_int_val(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Literal_Label::IntVal), native_child));
        }
        Ok(())
    }

    fn children_int_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::IntVal) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_int_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::IntVal) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::IntVal) {
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

    fn append_str_val(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = LiteralChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Literal_Label::StrVal), native_child));
        Ok(())
    }

    fn extend_str_val(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = LiteralChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Literal_Label::StrVal), native_child));
        }
        Ok(())
    }

    fn children_str_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::StrVal) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_str_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::StrVal) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Literal_Label::StrVal) {
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
    #[pyo3(name = "CONTENT")]
    Content,
}

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

// TriviaChild — native child value enum for Trivia
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

impl TriviaChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // span_to_pyobject: O(1) Arc clone, no string copy; preserves
                // Arc-sharing so multiple reads of the same span merge without error.
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
        // Preserve source via span_to_pyobject: O(1) Arc clone, no string copy.
        span_to_pyobject(py, &self.span)
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())
    }

    fn append_content(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let native_child = TriviaChild::extract_from_pyobject(py, child, &span_type)?;
        self.children.push((Some(Trivia_Label::Content), native_child));
        Ok(())
    }

    fn extend_content(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let span_type = get_span_type(py)?;
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let native_child = TriviaChild::extract_from_pyobject(py, &child, &span_type)?;
            self.children.push((Some(Trivia_Label::Content), native_child));
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::Content) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::Content) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Trivia_Label::Content) {
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

pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NodeKind>()?;
    module.add_class::<Config_Label>()?;
    module.add_class::<Config>()?;
    module.add_class::<Entry_Label>()?;
    module.add_class::<Entry>()?;
    module.add_class::<Operator_Label>()?;
    module.add_class::<Operator>()?;
    module.add_class::<Identifier_Label>()?;
    module.add_class::<Identifier>()?;
    module.add_class::<Literal_Label>()?;
    module.add_class::<Literal>()?;
    module.add_class::<Trivia_Label>()?;
    module.add_class::<Trivia>()?;
    Ok(())
}
