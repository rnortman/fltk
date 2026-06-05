use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::{PyList, PyTuple};
use pyo3::PyTypeInfo;

/// Cached reference to `fltk._native.UnknownSpan`.
/// Fetched once on first node construction; avoids a Python import per call.
static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();

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
        if let Ok(other_label) = other.extract::<Grammar_Label>() {
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
// Grammar
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Grammar {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Grammar {
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
        Ok(Grammar {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Grammar_Label::type_object(py).into_any().unbind())
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

    fn append_rule(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Grammar_Label::Rule.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_rule(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Grammar_Label::Rule.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_rule(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Grammar_Label::Rule.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Grammar.children_rule: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_rule(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Grammar_Label::Rule.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Grammar.child_rule: children[{idx}] is not a tuple: {e}"
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
                "Expected one rule child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Grammar.child_rule: count==1 but found==None; logic error"))
    }

    fn maybe_rule(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Grammar_Label::Rule.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Grammar.maybe_rule: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Grammar'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Grammar(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Rule_Label>() {
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
// Rule
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Rule {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Rule {
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
        Ok(Rule {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Rule_Label::type_object(py).into_any().unbind())
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

    fn append_alternatives(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Rule_Label::Alternatives.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Rule_Label::Alternatives.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Rule_Label::Alternatives.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.children_alternatives: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Rule_Label::Alternatives.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.child_alternatives: children[{idx}] is not a tuple: {e}"
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
                "Expected one alternatives child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Rule.child_alternatives: count==1 but found==None; logic error"))
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Rule_Label::Alternatives.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.maybe_alternatives: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_name(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Rule_Label::Name.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_name(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Rule_Label::Name.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_name(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Rule_Label::Name.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.children_name: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_name(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Rule_Label::Name.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.child_name: children[{idx}] is not a tuple: {e}"
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
        Ok(found.expect("invariant: Rule.child_name: count==1 but found==None; logic error"))
    }

    fn maybe_name(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Rule_Label::Name.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Rule.maybe_name: children[{idx}] is not a tuple: {e}"
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
        if !other.is_instance_of::<Rule>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<Rule> = other.extract()?;
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Rule'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Rule(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Alternatives_Label>() {
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
// Alternatives
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Alternatives {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Alternatives {
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
        Ok(Alternatives {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Alternatives_Label::type_object(py).into_any().unbind())
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

    fn append_items(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Alternatives_Label::Items.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_items(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Alternatives_Label::Items.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_items(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Alternatives_Label::Items.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Alternatives.children_items: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_items(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Alternatives_Label::Items.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Alternatives.child_items: children[{idx}] is not a tuple: {e}"
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
                "Expected one items child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Alternatives.child_items: count==1 but found==None; logic error"))
    }

    fn maybe_items(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Alternatives_Label::Items.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Alternatives.maybe_items: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Alternatives'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Alternatives(span={span_repr}, children={children_repr})"
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
        if let Ok(other_label) = other.extract::<Item_Label>() {
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
// Item
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Item {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Item {
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
        Ok(Item {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Item_Label::type_object(py).into_any().unbind())
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

    fn append_disposition(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Item_Label::Disposition.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_disposition(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Item_Label::Disposition.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_disposition(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Item_Label::Disposition.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.children_disposition: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_disposition(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Item_Label::Disposition.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.child_disposition: children[{idx}] is not a tuple: {e}"
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
                "Expected one disposition child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_disposition: count==1 but found==None; logic error"))
    }

    fn maybe_disposition(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Item_Label::Disposition.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.maybe_disposition: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one disposition child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_label(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Item_Label::Label.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_label(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Item_Label::Label.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_label(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Item_Label::Label.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.children_label: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_label(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Item_Label::Label.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.child_label: children[{idx}] is not a tuple: {e}"
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
                "Expected one label child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_label: count==1 but found==None; logic error"))
    }

    fn maybe_label(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Item_Label::Label.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.maybe_label: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one label child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_quantifier(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Item_Label::Quantifier.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_quantifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Item_Label::Quantifier.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_quantifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Item_Label::Quantifier.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.children_quantifier: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_quantifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Item_Label::Quantifier.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.child_quantifier: children[{idx}] is not a tuple: {e}"
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
                "Expected one quantifier child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_quantifier: count==1 but found==None; logic error"))
    }

    fn maybe_quantifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Item_Label::Quantifier.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.maybe_quantifier: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one quantifier child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_term(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Item_Label::Term.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_term(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Item_Label::Term.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_term(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Item_Label::Term.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.children_term: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_term(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Item_Label::Term.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.child_term: children[{idx}] is not a tuple: {e}"
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
                "Expected one term child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Item.child_term: count==1 but found==None; logic error"))
    }

    fn maybe_term(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Item_Label::Term.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Item.maybe_term: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Item'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Item(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Term_Label>() {
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
// Term
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Term {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Term {
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
        Ok(Term {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Term_Label::type_object(py).into_any().unbind())
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

    fn append_alternatives(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Term_Label::Alternatives.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_alternatives(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Term_Label::Alternatives.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_alternatives(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Term_Label::Alternatives.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.children_alternatives: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_alternatives(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Term_Label::Alternatives.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.child_alternatives: children[{idx}] is not a tuple: {e}"
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
                "Expected one alternatives child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_alternatives: count==1 but found==None; logic error"))
    }

    fn maybe_alternatives(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Term_Label::Alternatives.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.maybe_alternatives: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one alternatives child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_identifier(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Term_Label::Identifier.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_identifier(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Term_Label::Identifier.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_identifier(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Term_Label::Identifier.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.children_identifier: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_identifier(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Term_Label::Identifier.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.child_identifier: children[{idx}] is not a tuple: {e}"
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
                "Expected one identifier child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_identifier: count==1 but found==None; logic error"))
    }

    fn maybe_identifier(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Term_Label::Identifier.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.maybe_identifier: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one identifier child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_literal(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Term_Label::Literal.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_literal(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Term_Label::Literal.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_literal(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Term_Label::Literal.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.children_literal: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_literal(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Term_Label::Literal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.child_literal: children[{idx}] is not a tuple: {e}"
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
                "Expected one literal child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_literal: count==1 but found==None; logic error"))
    }

    fn maybe_literal(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Term_Label::Literal.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.maybe_literal: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one literal child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_regex(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Term_Label::Regex.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_regex(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Term_Label::Regex.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_regex(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Term_Label::Regex.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.children_regex: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_regex(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Term_Label::Regex.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.child_regex: children[{idx}] is not a tuple: {e}"
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
                "Expected one regex child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Term.child_regex: count==1 but found==None; logic error"))
    }

    fn maybe_regex(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Term_Label::Regex.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Term.maybe_regex: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Term'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Term(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Disposition_Label>() {
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
// Disposition
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Disposition {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Disposition {
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
        Ok(Disposition {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Disposition_Label::type_object(py).into_any().unbind())
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

    fn append_include(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Disposition_Label::Include.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_include(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Disposition_Label::Include.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_include(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Disposition_Label::Include.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.children_include: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_include(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Disposition_Label::Include.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.child_include: children[{idx}] is not a tuple: {e}"
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
                "Expected one include child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_include: count==1 but found==None; logic error"))
    }

    fn maybe_include(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Disposition_Label::Include.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.maybe_include: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one include child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_inline(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Disposition_Label::Inline.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_inline(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Disposition_Label::Inline.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_inline(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Disposition_Label::Inline.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.children_inline: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_inline(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Disposition_Label::Inline.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.child_inline: children[{idx}] is not a tuple: {e}"
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
                "Expected one inline child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_inline: count==1 but found==None; logic error"))
    }

    fn maybe_inline(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Disposition_Label::Inline.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.maybe_inline: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one inline child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_suppress(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Disposition_Label::Suppress.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_suppress(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Disposition_Label::Suppress.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_suppress(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Disposition_Label::Suppress.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.children_suppress: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_suppress(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Disposition_Label::Suppress.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.child_suppress: children[{idx}] is not a tuple: {e}"
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
                "Expected one suppress child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Disposition.child_suppress: count==1 but found==None; logic error"))
    }

    fn maybe_suppress(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Disposition_Label::Suppress.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Disposition.maybe_suppress: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Disposition'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Disposition(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<Quantifier_Label>() {
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
// Quantifier
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct Quantifier {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl Quantifier {
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
        Ok(Quantifier {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(Quantifier_Label::type_object(py).into_any().unbind())
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

    fn append_one_or_more(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Quantifier_Label::OneOrMore.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_one_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Quantifier_Label::OneOrMore.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_one_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Quantifier_Label::OneOrMore.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.children_one_or_more: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_one_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Quantifier_Label::OneOrMore.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.child_one_or_more: children[{idx}] is not a tuple: {e}"
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
                "Expected one one_or_more child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_one_or_more: count==1 but found==None; logic error"))
    }

    fn maybe_one_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Quantifier_Label::OneOrMore.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.maybe_one_or_more: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one one_or_more child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_optional(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Quantifier_Label::Optional.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_optional(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Quantifier_Label::Optional.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_optional(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Quantifier_Label::Optional.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.children_optional: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_optional(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Quantifier_Label::Optional.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.child_optional: children[{idx}] is not a tuple: {e}"
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
                "Expected one optional child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_optional: count==1 but found==None; logic error"))
    }

    fn maybe_optional(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Quantifier_Label::Optional.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.maybe_optional: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one optional child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_zero_or_more(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Quantifier_Label::ZeroOrMore.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_zero_or_more(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Quantifier_Label::ZeroOrMore.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_zero_or_more(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Quantifier_Label::ZeroOrMore.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.children_zero_or_more: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_zero_or_more(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Quantifier_Label::ZeroOrMore.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.child_zero_or_more: children[{idx}] is not a tuple: {e}"
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
                "Expected one zero_or_more child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Quantifier.child_zero_or_more: count==1 but found==None; logic error"))
    }

    fn maybe_zero_or_more(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Quantifier_Label::ZeroOrMore.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Quantifier.maybe_zero_or_more: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'Quantifier'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "Quantifier(span={span_repr}, children={children_repr})"
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
        if let Ok(other_label) = other.extract::<RawString_Label>() {
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
// RawString
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct RawString {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl RawString {
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
        Ok(RawString {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(RawString_Label::type_object(py).into_any().unbind())
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

    fn append_value(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = RawString_Label::Value.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = RawString_Label::Value.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = RawString_Label::Value.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "RawString.children_value: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = RawString_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "RawString.child_value: children[{idx}] is not a tuple: {e}"
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
        Ok(found.expect("invariant: RawString.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = RawString_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "RawString.maybe_value: children[{idx}] is not a tuple: {e}"
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
        if !other.is_instance_of::<RawString>() {
            return Ok(py.NotImplemented());
        }
        let other_node: PyRef<RawString> = other.extract()?;
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'RawString'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "RawString(span={span_repr}, children={children_repr})"
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

    fn append_value(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Literal_Label::Value.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_value(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Literal_Label::Value.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_value(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Literal_Label::Value.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.children_value: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_value(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Literal_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.child_value: children[{idx}] is not a tuple: {e}"
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
        Ok(found.expect("invariant: Literal.child_value: count==1 but found==None; logic error"))
    }

    fn maybe_value(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Literal_Label::Value.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Literal.maybe_value: children[{idx}] is not a tuple: {e}"
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

    fn append_block_comment(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Trivia_Label::BlockComment.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_block_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Trivia_Label::BlockComment.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_block_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Trivia_Label::BlockComment.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.children_block_comment: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_block_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Trivia_Label::BlockComment.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.child_block_comment: children[{idx}] is not a tuple: {e}"
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
                "Expected one block_comment child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Trivia.child_block_comment: count==1 but found==None; logic error"))
    }

    fn maybe_block_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Trivia_Label::BlockComment.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.maybe_block_comment: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one block_comment child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_line_comment(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = Trivia_Label::LineComment.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_line_comment(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = Trivia_Label::LineComment.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_line_comment(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = Trivia_Label::LineComment.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.children_line_comment: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_line_comment(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = Trivia_Label::LineComment.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.child_line_comment: children[{idx}] is not a tuple: {e}"
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
                "Expected one line_comment child but have {count}"
            )));
        }
        Ok(found.expect("invariant: Trivia.child_line_comment: count==1 but found==None; logic error"))
    }

    fn maybe_line_comment(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = Trivia_Label::LineComment.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "Trivia.maybe_line_comment: children[{idx}] is not a tuple: {e}"
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
        if let Ok(other_label) = other.extract::<LineComment_Label>() {
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
// LineComment
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct LineComment {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl LineComment {
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
        Ok(LineComment {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(LineComment_Label::type_object(py).into_any().unbind())
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
        let label = LineComment_Label::Content.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = LineComment_Label::Content.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = LineComment_Label::Content.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.children_content: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = LineComment_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.child_content: children[{idx}] is not a tuple: {e}"
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
        Ok(found.expect("invariant: LineComment.child_content: count==1 but found==None; logic error"))
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = LineComment_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.maybe_content: children[{idx}] is not a tuple: {e}"
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

    fn append_prefix(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = LineComment_Label::Prefix.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_prefix(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = LineComment_Label::Prefix.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_prefix(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = LineComment_Label::Prefix.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.children_prefix: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_prefix(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = LineComment_Label::Prefix.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.child_prefix: children[{idx}] is not a tuple: {e}"
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
                "Expected one prefix child but have {count}"
            )));
        }
        Ok(found.expect("invariant: LineComment.child_prefix: count==1 but found==None; logic error"))
    }

    fn maybe_prefix(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = LineComment_Label::Prefix.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "LineComment.maybe_prefix: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'LineComment'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "LineComment(span={span_repr}, children={children_repr})"
        ))
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
        if let Ok(other_label) = other.extract::<BlockComment_Label>() {
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
// BlockComment
// ───────────────────────────────────────────────────────────────────────────

#[pyclass]
pub struct BlockComment {
    #[pyo3(get, set)]
    span: PyObject,
    #[pyo3(get)]
    children: Py<PyList>,
}

#[pymethods]
impl BlockComment {
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
        Ok(BlockComment {
            span: span_obj,
            children: PyList::empty(py).unbind(),
        })
    }

    #[classattr]
    #[allow(non_snake_case)]
    fn Label(py: Python<'_>) -> PyResult<PyObject> {
        Ok(BlockComment_Label::type_object(py).into_any().unbind())
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
        let label = BlockComment_Label::Content.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_content(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = BlockComment_Label::Content.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_content(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = BlockComment_Label::Content.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.children_content: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_content(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = BlockComment_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.child_content: children[{idx}] is not a tuple: {e}"
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
        Ok(found.expect("invariant: BlockComment.child_content: count==1 but found==None; logic error"))
    }

    fn maybe_content(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = BlockComment_Label::Content.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.maybe_content: children[{idx}] is not a tuple: {e}"
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

    fn append_end(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = BlockComment_Label::End.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_end(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = BlockComment_Label::End.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_end(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = BlockComment_Label::End.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.children_end: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_end(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = BlockComment_Label::End.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.child_end: children[{idx}] is not a tuple: {e}"
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
                "Expected one end child but have {count}"
            )));
        }
        Ok(found.expect("invariant: BlockComment.child_end: count==1 but found==None; logic error"))
    }

    fn maybe_end(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = BlockComment_Label::End.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.maybe_end: children[{idx}] is not a tuple: {e}"
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
                "Expected at most one end child but have at least 2",
            ));
        }
        Ok(found)
    }

    fn append_start(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {
        let label = BlockComment_Label::Start.into_pyobject(py)?.into_any();
        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;
        self.children.bind(py).append(tup)?;
        Ok(())
    }

    fn extend_start(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {
        let label = BlockComment_Label::Start.into_pyobject(py)?.into_any().unbind();
        let iter = children.try_iter()?;
        for child_result in iter {
            let child = child_result?;
            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;
            self.children.bind(py).append(tup)?;
        }
        Ok(())
    }

    fn children_start(&self, py: Python<'_>) -> PyResult<Py<PyList>> {
        let label_obj = BlockComment_Label::Start.into_pyobject(py)?;
        let result = PyList::empty(py);
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.children_start: children[{idx}] is not a tuple: {e}"
                ))
            })?;
            if tup.get_item(0)?.eq(&label_obj)? {
                result.append(tup.get_item(1)?)?;
            }
        }
        Ok(result.unbind())
    }

    fn child_start(&self, py: Python<'_>) -> PyResult<PyObject> {
        let label_obj = BlockComment_Label::Start.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.child_start: children[{idx}] is not a tuple: {e}"
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
                "Expected one start child but have {count}"
            )));
        }
        Ok(found.expect("invariant: BlockComment.child_start: count==1 but found==None; logic error"))
    }

    fn maybe_start(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let label_obj = BlockComment_Label::Start.into_pyobject(py)?;
        let mut found: Option<PyObject> = None;
        let mut count = 0usize;
        for (idx, item) in self.children.bind(py).iter().enumerate() {
            let tup = item.downcast::<PyTuple>().map_err(|e| {
                PyTypeError::new_err(format!(
                    "BlockComment.maybe_start: children[{idx}] is not a tuple: {e}"
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
        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;
        if !span_eq {
            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());
        }
        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;
        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())
    }

    fn __hash__(&self) -> PyResult<isize> {
        Err(PyTypeError::new_err("unhashable type: 'BlockComment'"))
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let span_repr = self.span.bind(py).repr()?.to_string();
        let children_repr = self.children.bind(py).repr()?.to_string();
        Ok(format!(
            "BlockComment(span={span_repr}, children={children_repr})"
        ))
    }

}

pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
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
