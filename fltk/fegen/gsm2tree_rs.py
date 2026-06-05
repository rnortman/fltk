"""Rust CST code generator for fltk.fegen grammars.

Generates PyO3-based Rust source code from a gsm.Grammar, producing the
same Python-visible API as gsm2tree.py but as compiled Rust extension classes.
"""

from __future__ import annotations

import re

from fltk.fegen import gsm
from fltk.fegen.gsm2tree import CstGenerator
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg

# Valid identifier pattern (matches fegen.fltkg:16 grammar rule for identifiers)
_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")
# TODO(extract-rule-name-to-class-name): _rust_variant_name duplicates the
# underscore-to-CamelCase transform in CstGenerator.class_name_for_rule_node
# (gsm2tree.py:46), UnparserGenerator.class_name_for_rule_node
# (gsm2unparser.py:638), and an inline list-comp (gsm2unparser.py:1888).
# Extract to a shared helper in fltk/fegen/gsm2tree.py or fltk/fegen/naming.py.


def _rust_variant_name(label: str) -> str:
    """Label -> CamelCase Rust enum variant. 'no_ws' -> 'NoWs'."""
    return "".join(part.capitalize() for part in label.split("_"))


def _python_label_name(label: str) -> str:
    """Label -> ALL_CAPS Python-visible name. 'no_ws' -> 'NO_WS'."""
    return label.upper()


class RustCstGenerator:
    """Generates a complete .rs file from a gsm.Grammar.

    Takes a raw gsm.Grammar (not yet trivia-processed) and produces a string
    containing a complete, compilable .rs file with PyO3 CST node classes.
    """

    def __init__(self, grammar: gsm.Grammar):
        context = create_default_context()
        grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
        self._py_gen = CstGenerator(
            grammar=grammar_with_trivia,
            py_module=pyreg.Builtins,
            context=context,
        )
        self.grammar = grammar_with_trivia

        # Validate all rule names and item labels before any emission.
        # rule.name and item.label are interpolated directly into Rust identifiers
        # and string literals; invalid characters produce malformed or executable
        # generated source (build-time code injection on the developer/CI host).
        for rule in self.grammar.rules:
            if not _IDENTIFIER_RE.match(rule.name):
                msg = f"Rule name {rule.name!r} is not a valid identifier (must match {_IDENTIFIER_RE.pattern!r})"
                raise ValueError(msg)
            for alt in rule.alternatives:
                for item in alt.items:
                    if item.label is not None and not _IDENTIFIER_RE.match(item.label):
                        msg = (
                            f"Item label {item.label!r} in rule {rule.name!r} is not a valid identifier "
                            f"(must match {_IDENTIFIER_RE.pattern!r})"
                        )
                        raise ValueError(msg)

    def _rule_info(self) -> list[tuple[str, list[str]]]:
        """Return [(class_name, sorted_labels)] for every rule in the grammar.

        Raises RuntimeError for missing rule models (invariant violation) and for
        rules whose model has no types (empty-model rules cannot be emitted).
        """
        result: list[tuple[str, list[str]]] = []
        for rule in self.grammar.rules:
            try:
                model = self._py_gen.rule_models[rule.name]
            except KeyError as exc:
                msg = (
                    f"No model for rule {rule.name!r} in _rule_info(); "
                    f"available rules: {sorted(self._py_gen.rule_models)}"
                )
                raise RuntimeError(msg) from exc
            if not model.types:
                class_name = self._py_gen.class_name_for_rule_node(rule.name)
                msg = (
                    f"Model class `{class_name}` would have no members; "
                    "ensure there is at least one term included in the model."
                )
                raise RuntimeError(msg)
            class_name = self._py_gen.class_name_for_rule_node(rule.name)
            labels = sorted(model.labels.keys())
            result.append((class_name, labels))
        return result

    def generate(self) -> str:
        """Return a complete, compilable .rs file as a string."""
        parts: list[str] = []

        parts.append(self._preamble())

        for class_name, labels in self._rule_info():
            parts.append(self._label_enum_block(class_name, labels))
            parts.append(self._node_block(class_name, labels))

        parts.append(self._register_classes_fn())

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------

    def _preamble(self) -> str:
        # TODO(rust-cst-shared-rlib): if user extensions ever need to link Rust-level
        # shared types (e.g. a typed Span), Option D (fltk-cst-common rlib + Cargo
        # workspace) is the clean answer. Today span is opaque PyObject; no linkage needed.
        return (
            "use pyo3::exceptions::{PyTypeError, PyValueError};\n"
            "use pyo3::prelude::*;\n"
            "use pyo3::sync::GILOnceCell;\n"
            "use pyo3::types::{PyList, PyTuple};\n"
            "use pyo3::PyTypeInfo;\n"
            "\n"
            "/// Cached reference to `fltk._native.UnknownSpan`.\n"
            "/// Fetched once on first node construction; avoids a Python import per call.\n"
            "static UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject> = GILOnceCell::new();\n"
        )

    # ------------------------------------------------------------------
    # Label enum
    # ------------------------------------------------------------------

    def _label_enum_block(self, class_name: str, labels: list[str]) -> str:
        """Emit the label enum definition and its #[pymethods] block.

        For rules with no labels, emits nothing (Rust enums cannot have zero variants).
        """
        if not labels:
            return ""

        enum_name = f"{class_name}_Label"
        lines: list[str] = []

        lines.append(f"// {'─' * 75}")
        lines.append(f"// {enum_name}")
        lines.append(f"// {'─' * 75}")
        lines.append("")

        lines.append("#[allow(non_camel_case_types)]")
        lines.append(f'#[pyclass(frozen, name = "{enum_name}")]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append(f"pub enum {enum_name} {{")
        for label in labels:
            rust_variant = _rust_variant_name(label)
            python_name = _python_label_name(label)
            lines.append(f'    #[pyo3(name = "{python_name}")]')
            lines.append(f"    {rust_variant},")
        lines.append("}")
        lines.append("")

        # pymethods block: __repr__, _fltk_canonical_name, __eq__, __hash__
        lines.append("#[pymethods]")
        lines.append(f"impl {enum_name} {{")
        lines.append("    fn __repr__(&self) -> &'static str {")
        lines.append("        match self {")
        for label in labels:
            rust_variant = _rust_variant_name(label)
            python_name = _python_label_name(label)
            lines.append(f'            {enum_name}::{rust_variant} => "{class_name}.Label.{python_name}",')
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    #[getter]")
        lines.append("    fn _fltk_canonical_name(&self) -> &'static str {")
        lines.append("        self.__repr__()")
        lines.append("    }")
        lines.append("")
        lines.append("    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {")
        lines.append(f"        if let Ok(other_label) = other.extract::<{enum_name}>() {{")
        lines.append("            return Ok((self == &other_label).into_pyobject(py)?.to_owned().unbind().into_any());")
        lines.append("        }")
        lines.append('        if let Ok(cn) = other.getattr(pyo3::intern!(py, "_fltk_canonical_name")) {')
        lines.append("            if let Ok(cn_str) = cn.extract::<&str>() {")
        lines.append(
            "                return Ok((self.__repr__() == cn_str).into_pyobject(py)?.to_owned().unbind().into_any());"
        )
        lines.append("            }")
        lines.append("        }")
        lines.append("        Ok(py.NotImplemented())")
        lines.append("    }")
        lines.append("")
        lines.append("    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {")
        lines.append("        pyo3::types::PyAnyMethods::hash(")
        lines.append("            pyo3::types::PyString::new(py, self.__repr__()).as_any()")
        lines.append("        )")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Node struct
    # ------------------------------------------------------------------

    def _node_block(self, class_name: str, labels: list[str]) -> str:
        """Emit the node struct definition and its #[pymethods] block."""
        lines: list[str] = []

        lines.append(f"// {'─' * 75}")
        lines.append(f"// {class_name}")
        lines.append(f"// {'─' * 75}")
        lines.append("")

        lines.append("#[pyclass]")
        lines.append(f"pub struct {class_name} {{")
        lines.append("    #[pyo3(get, set)]")
        lines.append("    span: PyObject,")
        lines.append("    #[pyo3(get)]")
        lines.append("    children: Py<PyList>,")
        lines.append("}")
        lines.append("")

        # pymethods block
        lines.append("#[pymethods]")
        lines.append(f"impl {class_name} {{")

        lines.extend(self._new_method(class_name))

        if labels:
            lines.extend(self._label_classattr(class_name))

        lines.extend(self._generic_append())
        lines.extend(self._generic_extend())
        lines.extend(self._generic_child())

        for label in labels:
            lines.extend(self._per_label_methods(class_name, label))

        lines.extend(self._eq_method(class_name))
        lines.extend(self._hash_method(class_name))
        lines.extend(self._repr_method(class_name))

        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    def _new_method(self, class_name: str) -> list[str]:
        return [
            "    #[new]",
            "    #[pyo3(signature = (*, span = None))]",
            "    fn new(py: Python<'_>, span: Option<PyObject>) -> PyResult<Self> {",
            "        let span_obj = match span {",
            "            Some(s) => s,",
            "            None => UNKNOWN_SPAN_CACHE",
            "                .get_or_try_init(py, || -> PyResult<PyObject> {",
            '                    Ok(py.import("fltk._native")?.getattr("UnknownSpan")?.unbind())',
            "                })?",
            "                .clone_ref(py),",
            "        };",
            f"        Ok({class_name} {{",
            "            span: span_obj,",
            "            children: PyList::empty(py).unbind(),",
            "        })",
            "    }",
            "",
        ]

    def _label_classattr(self, class_name: str) -> list[str]:
        enum_name = f"{class_name}_Label"
        return [
            "    #[classattr]",
            "    #[allow(non_snake_case)]",
            "    fn Label(py: Python<'_>) -> PyResult<PyObject> {",
            f"        Ok({enum_name}::type_object(py).into_any().unbind())",
            "    }",
            "",
        ]

    def _generic_append(self) -> list[str]:
        return [
            "    #[pyo3(signature = (child, label = None))]",
            "    fn append(&self, py: Python<'_>, child: PyObject, label: Option<PyObject>) -> PyResult<()> {",
            "        let label_val = label.unwrap_or_else(|| py.None());",
            "        let tup = PyTuple::new(py, [label_val, child])?;",
            "        self.children.bind(py).append(tup)?;",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_extend(self) -> list[str]:
        return [
            "    #[pyo3(signature = (children, label = None))]",
            "    fn extend(",
            "        &self,",
            "        py: Python<'_>,",
            "        children: &Bound<'_, PyAny>,",
            "        label: Option<PyObject>,",
            "    ) -> PyResult<()> {",
            "        let label_val = label.unwrap_or_else(|| py.None());",
            "        let iter = children.try_iter()?;",
            "        for child_result in iter {",
            "            let child = child_result?;",
            "            let tup = PyTuple::new(py, [label_val.clone_ref(py).into_bound(py), child])?;",
            "            self.children.bind(py).append(tup)?;",
            "        }",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_child(self) -> list[str]:
        return [
            "    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {",
            "        let list = self.children.bind(py);",
            "        let n = list.len();",
            "        if n != 1 {",
            "            return Err(PyValueError::new_err(format!(",
            '                "Expected one child but have {n}"',
            "            )));",
            "        }",
            "        Ok(list.get_item(0)?.unbind())",
            "    }",
            "",
        ]

    def _per_label_methods(self, class_name: str, label: str) -> list[str]:
        enum_name = f"{class_name}_Label"
        rust_variant = _rust_variant_name(label)

        lines: list[str] = []

        lines.extend(
            [
                f"    fn append_{label}(&self, py: Python<'_>, child: PyObject) -> PyResult<()> {{",
                f"        let label = {enum_name}::{rust_variant}.into_pyobject(py)?.into_any();",
                "        let tup = PyTuple::new(py, [label, child.into_bound(py)])?;",
                "        self.children.bind(py).append(tup)?;",
                "        Ok(())",
                "    }",
                "",
            ]
        )

        lines.extend(
            [
                f"    fn extend_{label}(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {{",
                f"        let label = {enum_name}::{rust_variant}.into_pyobject(py)?.into_any().unbind();",
                "        let iter = children.try_iter()?;",
                "        for child_result in iter {",
                "            let child = child_result?;",
                "            let tup = PyTuple::new(py, [label.bind(py).clone(), child])?;",
                "            self.children.bind(py).append(tup)?;",
                "        }",
                "        Ok(())",
                "    }",
                "",
            ]
        )

        # TODO(perf-label-identity-comparison): the generated `tup.get_item(0)?.eq(&label_obj)?`
        # below performs an O(children) linear scan with equality comparison per access.
        # Identity comparison (`is`) or pre-grouped storage would be O(1). Defer until
        # profiling confirms a bottleneck; faithfully reproduces the Phase 2 template.
        lines.extend(
            [
                f"    fn children_{label}(&self, py: Python<'_>) -> PyResult<Py<PyList>> {{",
                f"        let label_obj = {enum_name}::{rust_variant}.into_pyobject(py)?;",
                "        let result = PyList::empty(py);",
                "        for (idx, item) in self.children.bind(py).iter().enumerate() {",
                "            let tup = item.downcast::<PyTuple>().map_err(|e| {",
                "                PyTypeError::new_err(format!(",
                f'                    "{class_name}.children_{label}: children[{{idx}}] is not a tuple: {{e}}"',
                "                ))",
                "            })?;",
                "            if tup.get_item(0)?.eq(&label_obj)? {",
                "                result.append(tup.get_item(1)?)?;",
                "            }",
                "        }",
                "        Ok(result.unbind())",
                "    }",
                "",
            ]
        )

        lines.extend(
            [
                f"    fn child_{label}(&self, py: Python<'_>) -> PyResult<PyObject> {{",
                f"        let label_obj = {enum_name}::{rust_variant}.into_pyobject(py)?;",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (idx, item) in self.children.bind(py).iter().enumerate() {",
                "            let tup = item.downcast::<PyTuple>().map_err(|e| {",
                "                PyTypeError::new_err(format!(",
                f'                    "{class_name}.child_{label}: children[{{idx}}] is not a tuple: {{e}}"',
                "                ))",
                "            })?;",
                "            if tup.get_item(0)?.eq(&label_obj)? {",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(tup.get_item(1)?.unbind());",
                "                } else {",
                "                    break;",
                "                }",
                "            }",
                "        }",
                "        if count != 1 {",
                "            return Err(PyValueError::new_err(format!(",
                f'                "Expected one {label} child but have {{count}}"',
                "            )));",
                "        }",
                f'        Ok(found.expect("invariant: {class_name}.child_{label}: count==1 but found==None; logic error"))',  # noqa: E501
                "    }",
                "",
            ]
        )

        lines.extend(
            [
                f"    fn maybe_{label}(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {{",
                f"        let label_obj = {enum_name}::{rust_variant}.into_pyobject(py)?;",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (idx, item) in self.children.bind(py).iter().enumerate() {",
                "            let tup = item.downcast::<PyTuple>().map_err(|e| {",
                "                PyTypeError::new_err(format!(",
                f'                    "{class_name}.maybe_{label}: children[{{idx}}] is not a tuple: {{e}}"',
                "                ))",
                "            })?;",
                "            if tup.get_item(0)?.eq(&label_obj)? {",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(tup.get_item(1)?.unbind());",
                "                } else {",
                "                    break;",
                "                }",
                "            }",
                "        }",
                "        if count > 1 {",
                "            return Err(PyValueError::new_err(",
                f'                "Expected at most one {label} child but have at least 2",',
                "            ));",
                "        }",
                "        Ok(found)",
                "    }",
                "",
            ]
        )

        return lines

    def _eq_method(self, class_name: str) -> list[str]:
        return [
            "    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {",
            f"        if !other.is_instance_of::<{class_name}>() {{",
            "            return Ok(py.NotImplemented());",
            "        }",
            f"        let other_node: PyRef<{class_name}> = other.extract()?;",
            "        let span_eq = self.span.bind(py).eq(other_node.span.bind(py))?;",
            "        if !span_eq {",
            "            return Ok(false.into_pyobject(py)?.to_owned().unbind().into_any());",
            "        }",
            "        let children_eq = self.children.bind(py).eq(other_node.children.bind(py))?;",
            "        Ok(children_eq.into_pyobject(py)?.to_owned().unbind().into_any())",
            "    }",
            "",
        ]

    def _hash_method(self, class_name: str) -> list[str]:
        return [
            "    fn __hash__(&self) -> PyResult<isize> {",
            f"        Err(PyTypeError::new_err(\"unhashable type: '{class_name}'\"))",
            "    }",
            "",
        ]

    def _repr_method(self, class_name: str) -> list[str]:
        return [
            "    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {",
            "        let span_repr = self.span.bind(py).repr()?.to_string();",
            "        let children_repr = self.children.bind(py).repr()?.to_string();",
            "        Ok(format!(",
            f'            "{class_name}(span={{span_repr}}, children={{children_repr}})"',
            "        ))",
            "    }",
            "",
        ]

    # ------------------------------------------------------------------
    # register_classes
    # ------------------------------------------------------------------

    def _register_classes_fn(self) -> str:
        lines: list[str] = []
        lines.append("pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {")
        for class_name, labels in self._rule_info():
            if labels:
                enum_name = f"{class_name}_Label"
                lines.append(f"    module.add_class::<{enum_name}>()?;")
            lines.append(f"    module.add_class::<{class_name}>()?;")
        lines.append("    Ok(())")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)
