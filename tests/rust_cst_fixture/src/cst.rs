use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::{PyList, PyTuple};
use pyo3::PyTypeInfo;

/// Cached reference to `fltk._native.UnknownSpan`.
/// Fetched once on first node construction; avoids a Python import per call.
static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();

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
        if let Ok(other_label) = other.extract::<Config_Label>() {
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
// Config
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Config {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Config {
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
        Ok(Config {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Config_Label::type_object(py).into_any().unbind())
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

    fn append_entry(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Config_Label::Entry.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_entry(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Config_Label::Entry.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_entry(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Config_Label::Entry.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Config.children_entry: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_entry(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Config_Label::Entry.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Config.child_entry: children[{idx}] is not a tuple: {e}"
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
                "Expected one entry child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Config.child_entry: count==1 but found==None; logic error"))
    }

    fn maybe_entry(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Config_Label::Entry.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Config.maybe_entry: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Config'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Config(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Entry_Label>() {
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
// Entry
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Entry {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Entry {
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
        Ok(Entry {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Entry_Label::type_object(py).into_any().unbind())
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

    fn append_key(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Entry_Label::Key.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_key(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Entry_Label::Key.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_key(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Entry_Label::Key.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.children_key: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_key(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Entry_Label::Key.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.child_key: children[{idx}] is not a tuple: {e}"
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
                "Expected one key child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_key: count==1 but found==None; logic error"))
    }

    fn maybe_key(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Entry_Label::Key.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.maybe_key: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one key child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_op(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Entry_Label::Op.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_op(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Entry_Label::Op.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_op(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Entry_Label::Op.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.children_op: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_op(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Entry_Label::Op.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.child_op: children[{idx}] is not a tuple: {e}"
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
                "Expected one op child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_op: count==1 but found==None; logic error"))
    }

    fn maybe_op(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Entry_Label::Op.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.maybe_op: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one op child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_value(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Entry_Label::Value.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Entry_Label::Value.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Entry_Label::Value.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.children_value: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Entry_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.child_value: children[{idx}] is not a tuple: {e}"
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
                "Expected one value child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Entry.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Entry_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Entry.maybe_value: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Entry'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Entry(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Operator_Label>() {
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
// Operator
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Operator {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Operator {
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
        Ok(Operator {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Operator_Label::type_object(py).into_any().unbind())
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

    fn append_append(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Operator_Label::Append.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_append(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Operator_Label::Append.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_append(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Operator_Label::Append.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.children_append: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_append(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Operator_Label::Append.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.child_append: children[{idx}] is not a tuple: {e}"
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
                "Expected one append child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_append: count==1 but found==None; logic error"))
    }

    fn maybe_append(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Operator_Label::Append.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.maybe_append: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one append child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_assign(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Operator_Label::Assign.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_assign(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Operator_Label::Assign.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_assign(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Operator_Label::Assign.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.children_assign: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_assign(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Operator_Label::Assign.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.child_assign: children[{idx}] is not a tuple: {e}"
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
                "Expected one assign child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_assign: count==1 but found==None; logic error"))
    }

    fn maybe_assign(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Operator_Label::Assign.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.maybe_assign: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one assign child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_remove(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Operator_Label::Remove.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_remove(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Operator_Label::Remove.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_remove(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Operator_Label::Remove.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.children_remove: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_remove(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Operator_Label::Remove.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.child_remove: children[{idx}] is not a tuple: {e}"
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
                "Expected one remove child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Operator.child_remove: count==1 but found==None; logic error"))
    }

    fn maybe_remove(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Operator_Label::Remove.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Operator.maybe_remove: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Operator'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Operator(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Literal_Label>() {
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
// Literal
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Literal {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Literal {
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
        Ok(Literal {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Literal_Label::type_object(py).into_any().unbind())
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

    fn append_int_val(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Literal_Label::IntVal.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_int_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Literal_Label::IntVal.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_int_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Literal_Label::IntVal.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.children_int_val: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_int_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Literal_Label::IntVal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.child_int_val: children[{idx}] is not a tuple: {e}"
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
                "Expected one int_val child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Literal.child_int_val: count==1 but found==None; logic error"))
    }

    fn maybe_int_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Literal_Label::IntVal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.maybe_int_val: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one int_val child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_str_val(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Literal_Label::StrVal.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_str_val(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Literal_Label::StrVal.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_str_val(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Literal_Label::StrVal.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.children_str_val: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_str_val(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Literal_Label::StrVal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.child_str_val: children[{idx}] is not a tuple: {e}"
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
                "Expected one str_val child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Literal.child_str_val: count==1 but found==None; logic error"))
    }

    fn maybe_str_val(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Literal_Label::StrVal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.maybe_str_val: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Literal'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Literal(span={span_repr}, children={children_repr})"
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
