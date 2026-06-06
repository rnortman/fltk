use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::{PyList, PyTuple};
use pyo3::PyTypeInfo;

/// Cached reference to `fltk._native.UnknownSpan`.
/// Fetched once on first node construction; avoids a Python import per call.
static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();

// ───────────────────────────────────────────────────────────────────────────
// NodeKind
// ───────────────────────────────────────────────────────────────────────────

#[allow(non_camel_case_types)]
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
        if let Ok(other_label) = other.extract::<Identifier_Label>() {
            return Ok((self == &other_label).into_pyobject(py)?.to_owned().unbind().into_any());
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
// Identifier
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Identifier {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Identifier {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
        let span_obj = match span {
            Some(s) => s,
            None => UNKNOWN_SPAN_CACHE
                .get_or_try_init(py, || -> PyResult<PyObject> {
                    Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())
                })?
                .clone_ref(py),
        };
        Ok(Identifier {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
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

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let tup = PyTuple::new(py, [label_val, child])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let list = self.children.bind(py);
        let n = list.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        Ok(list.get_item(0)?.unbind())
    }

    fn append_name(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Identifier_Label::Name.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Identifier_Label::Name.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Identifier_Label::Name.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Identifier.children_name: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Identifier_Label::Name.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Identifier.child_name: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Identifier_Label::Name.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Identifier.maybe_name: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Identifier'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Identifier(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Items_Label>() {
            return Ok((self == &other_label).into_pyobject(py)?.to_owned().unbind().into_any());
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
// Items
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Items {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Items {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
        let span_obj = match span {
            Some(s) => s,
            None => UNKNOWN_SPAN_CACHE
                .get_or_try_init(py, || -> PyResult<PyObject> {
                    Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())
                })?
                .clone_ref(py),
        };
        Ok(Items {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
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

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let tup = PyTuple::new(py, [label_val, child])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let list = self.children.bind(py);
        let n = list.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        Ok(list.get_item(0)?.unbind())
    }

    fn append_item(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Items_Label::Item.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_item(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Items_Label::Item.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_item(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Items_Label::Item.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.children_item: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_item(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Items_Label::Item.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.child_item: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Items_Label::Item.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.maybe_item: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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

    fn append_no_ws(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Items_Label::NoWs.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_no_ws(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Items_Label::NoWs.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_no_ws(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Items_Label::NoWs.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.children_no_ws: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_no_ws(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Items_Label::NoWs.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.child_no_ws: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Items_Label::NoWs.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.maybe_no_ws: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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

    fn append_ws_allowed(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Items_Label::WsAllowed.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_ws_allowed(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Items_Label::WsAllowed.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_ws_allowed(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Items_Label::WsAllowed.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.children_ws_allowed: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_allowed(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Items_Label::WsAllowed.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.child_ws_allowed: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Items_Label::WsAllowed.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.maybe_ws_allowed: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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

    fn append_ws_required(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Items_Label::WsRequired.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_ws_required(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Items_Label::WsRequired.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_ws_required(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Items_Label::WsRequired.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.children_ws_required: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_ws_required(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Items_Label::WsRequired.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.child_ws_required: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Items_Label::WsRequired.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Items.maybe_ws_required: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Items'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Items(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Trivia_Label>() {
            return Ok((self == &other_label).into_pyobject(py)?.to_owned().unbind().into_any());
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
// Trivia
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Trivia {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Trivia {
    #[new]
    #[pyo3(signature = (*, span = None))]
    fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {
        let span_obj = match span {
            Some(s) => s,
            None => UNKNOWN_SPAN_CACHE
                .get_or_try_init(py, || -> PyResult<PyObject> {
                    Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())
                })?
                .clone_ref(py),
        };
        Ok(Trivia {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
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

    #[pyo3(signature = (child, label = None))]
    fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let tup = PyTuple::new(py, [label_val, child])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    #[pyo3(signature = (children, label = None))]
    fn extend(
        &self,
        py: Python<'_>,
        children: &Bound<'_, PyAny>,
        label: Option<PyObject>,
    ) -> PyResult<()> {
        let label_val = label.unwrap_or_else(|| py.None());
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {
        let list = self.children.bind(py);
        let n = list.len();
        if n != 1 {
            return Err(PyValueError::new_err(format!(
                "Expected one child but have {n}"
            )));
        }
        Ok(list.get_item(0)?.unbind())
    }

    fn append_content(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Trivia_Label::Content.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Trivia_Label::Content.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Trivia_Label::Content.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.children_content: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Trivia_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.child_content: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let label_obj = Trivia_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.maybe_content: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                count += 1;
                if count == 1 {
                    found = Some(tup.get_item(1)?.unbind());
                } else {
                    break;
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Trivia'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Trivia(span={span_repr}, children={children_repr})"
        ))
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
