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
    #[pyo3(name = "IDENTIFIER")]
    Identifier,
    #[pyo3(name = "ITEMS")]
    Items,
    #[pyo3(name = "TRIVIA")]
    Trivia,
}

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
    Identifier(Box<Identifier>),
    Trivia(Box<Trivia>),
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

impl ItemsChild {
    fn to_pyobject(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self {
            Self::Span(s) => {
                // span_to_pyobject: O(1) Arc clone, no string copy; preserves
                // Arc-sharing so multiple reads of the same span merge without error.
                span_to_pyobject(py, s)
            }
            Self::Identifier(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),
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
        if obj.is_instance_of::<Identifier>() {
            let node: PyRef<Identifier> = obj.extract()?;
            return Ok(Self::Identifier(Box::new((*node).clone())));
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
        NodeKind::Items
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Items_Label::type_object(py).into_any().unbind())
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
        let (label, child) = &self.children[0];
        let label_obj: PyObject = match label {
            None => py.None(),
            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),
        };
        let child_obj = child.to_pyobject(py)?;
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::Item) {
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::NoWs) {
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsAllowed) {
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
        let result = PyList::empty(py);
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
                result.append(child.to_pyobject(py)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
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
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (label, child) in &self.children {
            if *label == Some(Items_Label::WsRequired) {
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
    module.add_class::<Identifier_Label>()?;
    module.add_class::<Identifier>()?;
    module.add_class::<Items_Label>()?;
    module.add_class::<Items>()?;
    module.add_class::<Trivia_Label>()?;
    module.add_class::<Trivia>()?;
    Ok(())
}
