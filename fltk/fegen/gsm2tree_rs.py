"""Rust CST code generator for fltk.fegen grammars.

Generates PyO3-based Rust source code from a gsm.Grammar, producing the
same Python-visible API as gsm2tree.py but as compiled Rust extension classes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from fltk.fegen import gsm, naming
from fltk.fegen.gsm2tree import CstGenerator, ModelType
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg

# Valid identifier pattern (matches fegen.fltkg:16 grammar rule for identifiers)
_IDENTIFIER_RE = re.compile(r"^[_a-z][_a-z0-9]*$")


def _rust_variant_name(label: str) -> str:
    """Label -> CamelCase Rust enum variant. 'no_ws' -> 'NoWs'."""
    return naming.snake_to_upper_camel(label)


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

    def _rule_info(self) -> list[tuple[str, list[str], str]]:
        """Return [(class_name, sorted_labels, rule_name)] for every rule in the grammar.

        Raises RuntimeError for missing rule models (invariant violation) and for
        rules whose model has no types (empty-model rules cannot be emitted).
        """
        result: list[tuple[str, list[str], str]] = []
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
            result.append((class_name, labels, rule.name))
        return result

    def _child_variants_for_rule(self, rule_name: str) -> tuple[list[str], bool]:
        """Return (sorted_child_class_names, has_span_child) for a rule's model.

        sorted_child_class_names: class names of referenced rule nodes (e.g. ["Identifier", "Trivia"]).
        has_span_child: True if the model includes a Span (terminal/literal/regex) child type.
        """
        model = self._py_gen.rule_models[rule_name]
        child_class_names: list[str] = []
        has_span = False
        for model_type in model.types:
            if isinstance(model_type, str):
                child_class_names.append(self._py_gen.class_name_for_rule_node(model_type))
            else:
                # TypeKey — must be the Span key
                has_span = True
        return sorted(child_class_names), has_span

    def generate_pyi(self, protocol_module: str) -> str:
        """Return a complete .pyi stub for the generated Rust extension as a string.

        protocol_module: import path of the committed protocol module for this grammar,
        e.g. 'fltk.fegen.fltk_cst_protocol'. All type identities in annotations reference
        it under the alias '_proto', so the stub cannot satisfy pyright with stub-local
        nominal types (§1 of the design).

        Callers write this string to <compiled_module_name>.pyi alongside the .rs file,
        or to a custom path via --pyi-output when the .rs stem differs from the import name.
        """
        lines: list[str] = []

        # Header: ruff noqa for PascalCase module-level names (same as protocol generator).
        lines.append("# ruff: noqa: N802")
        # Safety note: this directory must never gain an __init__.py or it will shadow the
        # compiled extension and break all runtime imports. See design §2.3.
        lines.append("from __future__ import annotations")
        lines.append("import typing")
        lines.append("import fltk.fegen.pyrt.terminalsrc")
        lines.append("import fltk.fegen.pyrt.span")
        lines.append("import fltk._native")
        lines.append(f"import {protocol_module} as _proto")
        lines.append("")
        # NodeKind: runtime is the PyO3 enum; type identity is the protocol's NodeKind.
        # This deliberate divergence (OQ-0(a)) keeps consumer kind-comparisons type-checked.
        lines.append("NodeKind = _proto.NodeKind")
        lines.append("")

        rule_info = self._rule_info()

        # Per-rule class stubs
        for class_name, labels, rule_name in rule_info:
            model = self._py_gen.rule_models[rule_name]
            lines.append(f"class {class_name}:")

            # Nested Label class alias (only when rule has labels, mirroring .rs conditional emission).
            # Use 'Label = _proto.ClassName.Label' (type alias assignment) rather than a ClassVar
            # annotation: the protocol's Label is a nested class, not a ClassVar, and pyright rejects
            # 'ClassVar[type[...]]' when checking structural compatibility with the protocol's nested class.
            if labels:
                lines.append(f"    Label = _proto.{class_name}.Label")

            # kind discriminant: reference protocol's NodeKind so Literal matches
            node_kind_member = self._node_kind_python_name(rule_name)
            lines.append(f"    kind: typing.Literal[_proto.NodeKind.{node_kind_member}]")

            # span: exact protocol union (invariant attribute; narrower would fail conformance)
            lines.append("    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span")

            # children: proto-qualified element types
            child_ann = self._pyi_annotation_for_model_types(model.types, class_name=class_name)
            if labels:
                lines.append(f"    children: list[tuple[typing.Optional[_proto.{class_name}.Label], {child_ann}]]")
            else:
                lines.append(f"    children: list[tuple[None, {child_ann}]]")

            # Generic methods: append, extend, child, extend_children
            label_ann = f"typing.Optional[_proto.{class_name}.Label]" if labels else "None"
            lines.append(f"    def append(self, child: {child_ann}, label: {label_ann} = ...) -> None: ...")
            lines.append(
                f"    def extend(self, children: typing.Iterable[{child_ann}], label: {label_ann} = ...) -> None: ..."
            )
            # extend_children takes _proto.ClassName (not the stub-local class) to avoid
            # contravariance mismatches when pyright checks structural compatibility.
            lines.append(f"    def extend_children(self, other: _proto.{class_name}) -> None: ...")
            if labels:
                child_ret = f"tuple[typing.Optional[_proto.{class_name}.Label], {child_ann}]"
            else:
                child_ret = f"tuple[None, {child_ann}]"
            lines.append(f"    def child(self) -> {child_ret}: ...")

            # Per-label accessor quintet
            for label in labels:
                lann = self._pyi_annotation_for_model_types(model.labels[label], class_name=f"{class_name}.{label}")
                lines.append(f"    def append_{label}(self, child: {lann}) -> None: ...")
                lines.append(f"    def extend_{label}(self, children: typing.Iterable[{lann}]) -> None: ...")
                # children_<label>: typed Iterator[T] (§3 of design: Rust returns list but
                # Iterator is the protocol's declared return type; stub uses narrower declaration
                # so conformance fixtures pass. Callers only ever iterate.)
                lines.append(f"    def children_{label}(self) -> typing.Iterator[{lann}]: ...")  # stub/runtime diverge
                lines.append(f"    def child_{label}(self) -> {lann}: ...")
                lines.append(f"    def maybe_{label}(self) -> typing.Optional[{lann}]: ...")

            lines.append("")

        # No module-level '<Class>: type[<Class>]' attrs: the class definition itself serves as
        # the module-level binding, and emitting a separate variable annotation of the same name
        # would cause pyright 'reportRedeclaration' errors in the stub self-check. CstModule
        # conformance works without them because the class definitions provide 'type[Grammar]' etc.
        # directly as module attributes.

        return "\n".join(lines)

    def _pyi_annotation_for_model_types(self, model_types: Iterable[ModelType], *, class_name: str = "") -> str:
        """Return a proto-qualified annotation string for use in the .pyi stub.

        Transforms the output of protocol_annotation_for_model_types: quoted rule references
        like '"Grammar"' become '_proto.Grammar', while unquoted library paths (e.g.
        'fltk.fegen.pyrt.terminalsrc.Span') are kept as-is.
        """
        # Get the raw annotation string from the protocol machinery.
        raw = self._py_gen.protocol_annotation_for_model_types(model_types=model_types, class_name=class_name)

        # Transform quoted rule refs to _proto-qualified names.
        # Raw form: '"ClassName"' (single-type) or 'typing.Union["A", "B", ...]'
        # We replace each '"ClassName"' occurrence with '_proto.ClassName'.
        def _replace_quoted(m: re.Match[str]) -> str:
            return f"_proto.{m.group(1)}"

        return re.sub(r'"([A-Z][A-Za-z0-9_]*)"', _replace_quoted, raw)

    def generate(self) -> str:
        """Return a complete, compilable .rs file as a string."""
        parts: list[str] = []

        parts.append(self._preamble())

        # Emit NodeKind enum before node structs so the kind getter can reference it.
        parts.append(self._node_kind_block())

        for class_name, labels, rule_name in self._rule_info():
            parts.append(self._label_enum_block(class_name, labels))
            parts.append(self._child_enum_block(class_name, rule_name))
            parts.append(self._node_block(class_name, labels, rule_name))

        parts.append(self._register_classes_fn())

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Preamble
    # ------------------------------------------------------------------

    def _preamble(self) -> str:
        return (
            "use fltk_cst_core::{extract_span, get_source_text_type, get_span_type, Span};\n"
            "use pyo3::exceptions::{PyTypeError, PyValueError};\n"
            "use pyo3::prelude::*;\n"
            "use pyo3::types::{PyList, PyTuple, PyType};\n"
            "use pyo3::PyTypeInfo;\n"
            "\n"
        )

    # ------------------------------------------------------------------
    # NodeKind enum (one per grammar, before all node structs)
    # ------------------------------------------------------------------

    def _node_kind_variant_name(self, class_name: str) -> str:
        """Return the CamelCase Rust variant name for a NodeKind member (same as class_name)."""
        return class_name

    def _node_kind_python_name(self, rule_name: str) -> str:
        """Return the ALL_CAPS Python-visible name for a NodeKind member.

        Delegates to CstGenerator.node_kind_member_name so CstGenerator is the single
        source of truth for this naming convention across .rs, .pyi, and protocol.
        """
        return self._py_gen.node_kind_member_name(rule_name)

    def _node_kind_canonical_name(self, class_name: str) -> str:
        """Return the canonical string for a NodeKind member: 'NodeKind.<UPPER>'."""
        return f"NodeKind.{class_name.upper()}"

    @staticmethod
    def _emit_rust_cross_backend_eq_hash(lines: list[str], type_name: str) -> None:
        """Append cross-backend __eq__ and __hash__ pymethods to ``lines``.

        ``type_name`` is the Rust type used for the own-type fast path (e.g. ``NodeKind`` or
        ``Items_Label``).  The generated __hash__ allocates a PyString per call because CPython's
        salted string hash is required for cross-backend hash agreement (AC4); amortizing this via
        GILOnceCell is deferred.
        """
        lines.append("    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {")
        lines.append(f"        if let Ok(other_kind) = other.extract::<{type_name}>() {{")
        lines.append("            return Ok((self == &other_kind).into_pyobject(py)?.to_owned().unbind().into_any());")
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

    def _node_kind_block(self) -> str:
        """Emit the module-level NodeKind enum + its #[pymethods] block."""
        rule_info = self._rule_info()
        lines: list[str] = []

        lines.append(f"// {'─' * 75}")
        lines.append("// NodeKind")
        lines.append(f"// {'─' * 75}")
        lines.append("")

        lines.append('#[pyclass(frozen, name = "NodeKind")]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append("pub enum NodeKind {")
        for class_name, _labels, rule_name in rule_info:
            python_name = self._node_kind_python_name(rule_name)
            lines.append(f'    #[pyo3(name = "{python_name}")]')
            lines.append(f"    {self._node_kind_variant_name(class_name)},")
        lines.append("}")
        lines.append("")

        # pymethods block: __repr__, _fltk_canonical_name, __eq__, __hash__
        lines.append("#[pymethods]")
        lines.append("impl NodeKind {")
        lines.append("    fn __repr__(&self) -> &'static str {")
        lines.append("        match self {")
        for class_name, _labels, _rule_name in rule_info:
            variant = self._node_kind_variant_name(class_name)
            canonical = self._node_kind_canonical_name(class_name)
            lines.append(f'            NodeKind::{variant} => "{canonical}",')
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    #[getter]")
        lines.append("    fn _fltk_canonical_name(&self) -> &'static str {")
        lines.append("        self.__repr__()")
        lines.append("    }")
        lines.append("")
        self._emit_rust_cross_backend_eq_hash(lines, "NodeKind")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Label enum
    # ------------------------------------------------------------------

    def _label_enum_block(self, class_name: str, labels: list[str]) -> str:
        """Emit the label enum definition and its #[pymethods] block.

        For rules with no labels, emits nothing (Rust enums cannot have zero variants).
        Cross-backend eq/hash is emitted via _emit_rust_cross_backend_eq_hash (shared with NodeKind).
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
        self._emit_rust_cross_backend_eq_hash(lines, enum_name)
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Child enum
    # ------------------------------------------------------------------

    def _child_enum_block(self, class_name: str, rule_name: str) -> str:
        """Emit the per-node child value enum (<Name>Child) + Clone/PartialEq impls."""
        child_classes, has_span = self._child_variants_for_rule(rule_name)
        enum_name = f"{class_name}Child"
        lines: list[str] = []

        lines.append(f"// {enum_name} — native child value enum for {class_name}")
        lines.append("#[derive(Clone)]")
        lines.append(f"pub enum {enum_name} {{")
        if has_span:
            lines.append("    Span(Span),")
        for child_cls in child_classes:
            lines.append(f"    {child_cls}(Box<{child_cls}>),")
        lines.append("}")
        lines.append("")

        # Manual PartialEq (structural, using native span/node equality)
        # Only emit `_ => false` when there are multiple variants; with a single variant the
        # wildcard arm would be unreachable and trigger a clippy/rustc warning.
        num_variants = (1 if has_span else 0) + len(child_classes)
        lines.append(f"impl PartialEq for {enum_name} {{")
        lines.append("    fn eq(&self, other: &Self) -> bool {")
        lines.append("        match (self, other) {")
        if has_span:
            lines.append(f"            ({enum_name}::Span(a), {enum_name}::Span(b)) => a == b,")
        for child_cls in child_classes:
            lines.append(f"            ({enum_name}::{child_cls}(a), {enum_name}::{child_cls}(b)) => a == b,")
        if num_variants > 1:
            lines.append("            _ => false,")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # to_pyobject: translate a native child variant back to a Python object
        # Use _py/_span_type if unused (when only one variant type is present)
        # Note: py is always needed when has_span because get_source_text_type(py) is called in the
        # source-bearing branch.
        py_param = "py" if (child_classes or has_span) else "_py"
        span_type_param = "span_type" if has_span else "_span_type"
        lines.append(f"impl {enum_name} {{")
        lines.append(
            f"    fn to_pyobject(&self, {py_param}: Python<'_>, "
            f"{span_type_param}: &Bound<'_, PyType>) -> PyResult<PyObject> {{"
        )
        lines.append("        match self {")
        if has_span:
            lines.append("            Self::Span(s) => {")
            lines.append("                // Preserve source: if span carries source, construct a canonical")
            lines.append("                // fltk._native.SourceText from the full text string and use it")
            lines.append("                // to build a source-bearing Python Span (cross-cdylib safe).")
            lines.append("                if let Some(full_text) = s.source_full_text_str() {")
            lines.append("                    let st_type = get_source_text_type(py)?;")
            lines.append("                    let py_src = st_type.call1((full_text.as_str(),))?;")
            rust_with_source = (
                '                    span_type.call_method1("with_source",'
                " (s.start(), s.end(), py_src)).map(|b| b.unbind())"
            )
            lines.append(rust_with_source)
            lines.append("                } else {")
            lines.append("                    span_type.call1((s.start(), s.end())).map(|b| b.unbind())")
            lines.append("                }")
            lines.append("            }")
        for child_cls in child_classes:
            lines.append(f"            Self::{child_cls}(n) => Py::new(py, (**n).clone()).map(|p| p.into_any()),")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        # extract_from_pyobject: convert a Python object to this child enum variant
        # Use underscore-prefixed names when parameters are not used in the body
        # to suppress unused_variables warnings (-D warnings in cargo clippy).
        extract_py_param = "py" if has_span else "_py"
        extract_span_type_param = "span_type" if has_span else "_span_type"
        lines.append("    fn extract_from_pyobject(")
        lines.append(f"        {extract_py_param}: Python<'_>,")
        lines.append("        obj: &Bound<'_, PyAny>,")
        lines.append(f"        {extract_span_type_param}: &Bound<'_, PyType>,")
        lines.append("    ) -> PyResult<Self> {")
        if has_span:
            # Try Span first (handles cross-cdylib span)
            lines.append("        // Try Span (terminal child) first — handles cross-cdylib span instances.")
            lines.append("        if obj.is_instance_of::<Span>() || obj.is_instance(span_type)? {")
            lines.append("            return extract_span(py, obj).map(Self::Span);")
            lines.append("        }")
        for child_cls in child_classes:
            lines.append(f"        if obj.is_instance_of::<{child_cls}>() {{")
            lines.append(f"            let node: PyRef<{child_cls}> = obj.extract()?;")
            lines.append(f"            return Ok(Self::{child_cls}(Box::new((*node).clone())));")
            lines.append("        }")
        if not has_span and not child_classes:
            # Degenerate case: no known child types — always error
            lines.append("        let _ = (py, span_type);")
        lines.append("        Err(pyo3::exceptions::PyTypeError::new_err(format!(")
        lines.append(f'            "{class_name}: unsupported child type {{}}",')
        lines.append("            obj.get_type().name()?")
        lines.append("        )))")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Node struct
    # ------------------------------------------------------------------

    def _node_block(self, class_name: str, labels: list[str], rule_name: str) -> str:
        """Emit the node struct definition and its #[pymethods] block."""
        child_classes, has_span = self._child_variants_for_rule(rule_name)
        enum_name = f"{class_name}Child"
        label_type = f"Option<{class_name}_Label>" if labels else "Option<()>"
        lines: list[str] = []

        lines.append(f"// {'─' * 75}")
        lines.append(f"// {class_name}")
        lines.append(f"// {'─' * 75}")
        lines.append("")

        lines.append("#[pyclass]")
        lines.append(f"pub struct {class_name} {{")
        lines.append("    span: Span,")
        lines.append(f"    children: Vec<({label_type}, {enum_name})>,")
        lines.append("}")
        lines.append("")

        # Native PartialEq (used by child enums of parent nodes)
        lines.append(f"impl PartialEq for {class_name} {{")
        lines.append("    fn eq(&self, other: &Self) -> bool {")
        lines.append("        self.span == other.span && self.children == other.children")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # Clone (needed so child enum can clone boxed nodes for Python boundary)
        lines.append(f"impl Clone for {class_name} {{")
        lines.append("    fn clone(&self) -> Self {")
        lines.append(f"        {class_name} {{")
        lines.append("            span: self.span.clone(),")
        lines.append("            children: self.children.clone(),")
        lines.append("        }")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # Native plain-impl block: GIL-free constructors and accessors for pure-Rust use.
        # These allow downstream Rust code (and #[cfg(test)] modules) to build and inspect
        # node trees without acquiring the GIL or calling through pyo3.
        lines.append(f"impl {class_name} {{")
        lines.append("    /// Construct a node with the given span and no children.")
        lines.append("    /// No GIL required.")
        lines.append("    pub fn new_native(span: Span) -> Self {")
        lines.append(f"        {class_name} {{")
        lines.append("            span,")
        lines.append("            children: Vec::new(),")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Return a reference to the stored native `Span`.")
        lines.append("    pub fn span_native(&self) -> &Span {")
        lines.append("        &self.span")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Return a slice of the native children.")
        lines.append(f"    pub fn children_native(&self) -> &[({label_type}, {enum_name})] {{")
        lines.append("        self.children.as_slice()")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Push a child onto the native children `Vec`.")
        lines.append(f"    pub fn push_child_native(&mut self, label: {label_type}, child: {enum_name}) {{")
        lines.append("        self.children.push((label, child));")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # pymethods block
        lines.append("#[pymethods]")
        lines.append(f"impl {class_name} {{")

        lines.extend(self._new_method(class_name))
        lines.extend(self._span_getter_setter())
        lines.extend(self._kind_getter(class_name))

        if labels:
            lines.extend(self._label_classattr(class_name))

        lines.extend(self._children_getter(class_name, enum_name))
        lines.extend(self._generic_append(class_name, enum_name, label_type, labels))
        lines.extend(self._generic_extend(class_name, enum_name, label_type, labels))
        lines.extend(self._generic_extend_children(class_name))
        lines.extend(self._generic_child(class_name, enum_name, label_type, labels))

        for label in labels:
            lines.extend(self._per_label_methods(class_name, label, enum_name))

        lines.extend(self._eq_method(class_name))
        lines.extend(self._hash_method(class_name))
        lines.extend(self._repr_method(class_name, enum_name))

        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    def _new_method(self, class_name: str) -> list[str]:
        return [
            "    #[new]",
            "    #[pyo3(signature = (*, span = None))]",
            "    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Self> {",
            "        let native_span = match span {",
            "            Some(s) => extract_span(py, s)?,",
            "            None => Span::unknown(),",
            "        };",
            f"        Ok({class_name} {{",
            "            span: native_span,",
            "            children: Vec::new(),",
            "        })",
            "    }",
            "",
        ]

    def _span_getter_setter(self) -> list[str]:
        return [
            "    #[getter]",
            "    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {",
            "        // Return a fltk._native.Span so consumers always get the canonical type",
            "        // regardless of which cdylib the node is defined in.",
            "        // Preserve source: if the stored span carries source, construct a canonical",
            "        // fltk._native.SourceText from the full text string (cross-cdylib safe).",
            "        let span_cls = get_span_type(py)?;",
            "        if let Some(full_text) = self.span.source_full_text_str() {",
            "            let st_type = get_source_text_type(py)?;",
            "            let py_src = st_type.call1((full_text.as_str(),))?;",
            "            span_cls",
            '                .call_method1("with_source", (self.span.start(), self.span.end(), py_src))',
            "                .map(|b| b.unbind())",
            "        } else {",
            "            span_cls",
            "                .call1((self.span.start(), self.span.end()))",
            "                .map(|b| b.unbind())",
            "        }",
            "    }",
            "",
            "    #[setter]",
            "    fn set_span(&mut self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {",
            "        self.span = extract_span(py, value)?;",
            "        Ok(())",
            "    }",
            "",
        ]

    def _kind_getter(self, class_name: str) -> list[str]:
        """Emit a #[getter] fn kind(&self) -> NodeKind returning this node's NodeKind member."""
        variant = self._node_kind_variant_name(class_name)
        return [
            "    #[getter]",
            "    fn kind(&self) -> NodeKind {",
            f"        NodeKind::{variant}",
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

    def _children_getter(self, _class_name: str, _enum_name: str) -> list[str]:
        """Emit the `children` Python getter that rebuilds a list from the native Vec."""
        return [
            "    #[getter]",
            "    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {",
            "        let span_type = get_span_type(py)?;",
            "        let result = PyList::empty(py);",
            "        for (label, child) in &self.children {",
            "            let label_obj: PyObject = match label {",
            "                None => py.None(),",
            "                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),",
            "            };",
            "            let child_obj = child.to_pyobject(py, &span_type)?;",
            "            let tup = PyTuple::new(py, [label_obj, child_obj])?;",
            "            result.append(tup)?;",
            "        }",
            "        Ok(result.unbind())",
            "    }",
            "",
        ]

    def _generic_append(self, class_name: str, enum_name: str, _label_type: str, labels: list[str]) -> list[str]:
        return [
            "    #[pyo3(signature = (child, label = None))]",
            "    fn append(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {",  # noqa: E501
            "        let span_type = get_span_type(py)?;",
            f"        let native_child = {enum_name}::extract_from_pyobject(py, child, &span_type)?;",
            "        let native_label = match label {",
            *self._label_from_pyobject_match(class_name, labels),
            "        };",
            "        self.children.push((native_label, native_child));",
            "        Ok(())",
            "    }",
            "",
        ]

    def _label_from_pyobject_match(self, class_name: str, labels: list[str]) -> list[str]:
        """Emit the match arms for converting an Option<PyObject> label to native label type."""
        if not labels:
            return [
                "            None => None,",
                "            Some(lbl) => {",
                "                let lbl_type = lbl.bind(py).get_type().name()?;",
                "                return Err(PyTypeError::new_err(format!(",
                f'                    "{class_name}.append: no labels defined for this node; got {{}} label",',
                "                    lbl_type",
                "                )));",
                "            }",
            ]
        enum_name = f"{class_name}_Label"
        lines = [
            "            None => None,",
            "            Some(lbl) => {",
            f"                if let Ok(native_lbl) = lbl.bind(py).extract::<{enum_name}>() {{",
            "                    Some(native_lbl)",
            "                } else {",
            "                    return Err(PyTypeError::new_err(format!(",
            f'                        "{class_name}.append: label argument is not a {enum_name}; got {{}}",',
            "                        lbl.bind(py).get_type().name()?",
            "                    )));",
            "                }",
            "            }",
        ]
        return lines

    def _generic_extend(self, class_name: str, enum_name: str, _label_type: str, labels: list[str]) -> list[str]:
        return [
            "    #[pyo3(signature = (children, label = None))]",
            "    fn extend(",
            "        &mut self,",
            "        py: Python<'_>,",
            "        children: &Bound<'_, PyAny>,",
            "        label: Option<PyObject>,",
            "    ) -> PyResult<()> {",
            "        let span_type = get_span_type(py)?;",
            "        let native_label = match label {",
            *self._label_from_pyobject_match(class_name, labels),
            "        };",
            "        let iter = children.try_iter()?;",
            "        for child_result in iter {",
            "            let child = child_result?;",
            f"            let native_child = {enum_name}::extract_from_pyobject(py, &child, &span_type)?;",
            "            self.children.push((native_label.clone(), native_child));",
            "        }",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_extend_children(self, class_name: str) -> list[str]:
        """Emit extend_children(&mut self, other: &NodeType) that bulk-copies children preserving labels.

        Used by generated parsers for inline_to_parent items: instead of mutating the
        throwaway list returned by the `children` getter, the parser calls this method to
        transfer children from a sub-parser result into the parent node's native Vec.
        """
        return [
            f"    fn extend_children(&mut self, other: PyRef<'_, {class_name}>) -> PyResult<()> {{",
            "        for (label, child) in &other.children {",
            "            self.children.push((label.clone(), child.clone()));",
            "        }",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_child(self, _class_name: str, _enum_name: str, _label_type: str, _labels: list[str]) -> list[str]:
        return [
            "    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {",
            "        let n = self.children.len();",
            "        if n != 1 {",
            "            return Err(PyValueError::new_err(format!(",
            '                "Expected one child but have {n}"',
            "            )));",
            "        }",
            "        let span_type = get_span_type(py)?;",
            "        let (label, child) = &self.children[0];",
            "        let label_obj: PyObject = match label {",
            "            None => py.None(),",
            "            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),",
            "        };",
            "        let child_obj = child.to_pyobject(py, &span_type)?;",
            "        Ok(PyTuple::new(py, [label_obj, child_obj])?.into_any().unbind())",
            "    }",
            "",
        ]

    def _per_label_methods(self, class_name: str, label: str, child_enum_name: str) -> list[str]:
        label_enum_name = f"{class_name}_Label"
        rust_variant = _rust_variant_name(label)

        lines: list[str] = []

        # append_<label>: push one child with the given label
        lines.extend(
            [
                f"    fn append_{label}(&mut self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {{",
                "        let span_type = get_span_type(py)?;",
                f"        let native_child = {child_enum_name}::extract_from_pyobject(py, child, &span_type)?;",
                f"        self.children.push((Some({label_enum_name}::{rust_variant}), native_child));",
                "        Ok(())",
                "    }",
                "",
            ]
        )

        # extend_<label>: push multiple children with the given label
        lines.extend(
            [
                f"    fn extend_{label}(&mut self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {{",
                "        let span_type = get_span_type(py)?;",
                "        let iter = children.try_iter()?;",
                "        for child_result in iter {",
                "            let child = child_result?;",
                f"            let native_child = {child_enum_name}::extract_from_pyobject(py, &child, &span_type)?;",
                f"            self.children.push((Some({label_enum_name}::{rust_variant}), native_child));",
                "        }",
                "        Ok(())",
                "    }",
                "",
            ]
        )

        # children_<label>: return list of all children with matching label
        lines.extend(
            [
                f"    fn children_{label}(&self, py: Python<'_>) -> PyResult<Py<PyList>> {{",
                "        let span_type = get_span_type(py)?;",
                "        let result = PyList::empty(py);",
                "        for (label, child) in &self.children {",
                f"            if *label == Some({label_enum_name}::{rust_variant}) {{",
                "                result.append(child.to_pyobject(py, &span_type)?)?;",
                "            }",
                "        }",
                "        Ok(result.unbind())",
                "    }",
                "",
            ]
        )

        # child_<label>: return the single child with matching label; error if not exactly one
        lines.extend(
            [
                f"    fn child_{label}(&self, py: Python<'_>) -> PyResult<PyObject> {{",
                "        let span_type = get_span_type(py)?;",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (label, child) in &self.children {",
                f"            if *label == Some({label_enum_name}::{rust_variant}) {{",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(child.to_pyobject(py, &span_type)?);",
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

        # maybe_<label>: return optional single child with matching label; error if more than one
        lines.extend(
            [
                f"    fn maybe_{label}(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {{",
                "        let span_type = get_span_type(py)?;",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (label, child) in &self.children {",
                f"            if *label == Some({label_enum_name}::{rust_variant}) {{",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(child.to_pyobject(py, &span_type)?);",
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
            "        // Native structural equality: no Python .eq() on stored state",
            "        let eq = self == &*other_node;",
            "        Ok(eq.into_pyobject(py)?.to_owned().unbind().into_any())",
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

    def _repr_method(self, class_name: str, _child_enum_name: str) -> list[str]:
        return [
            "    fn __repr__(&self, _py: Python<'_>) -> String {",
            '        let span_repr = format!("Span(start={}, end={})", self.span.start(), self.span.end());',
            "        let children_len = self.children.len();",
            "        format!(",
            f'            "{class_name}(span={{span_repr}}, children=[<{{children_len}} child(ren)>])"',
            "        )",
            "    }",
            "",
        ]

    # ------------------------------------------------------------------
    # register_classes
    # ------------------------------------------------------------------

    def _register_classes_fn(self) -> str:
        lines: list[str] = []
        lines.append("pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {")
        # NodeKind must be registered before node structs (whose kind getter returns it).
        lines.append("    module.add_class::<NodeKind>()?;")
        for class_name, labels, _rule_name in self._rule_info():
            if labels:
                enum_name = f"{class_name}_Label"
                lines.append(f"    module.add_class::<{enum_name}>()?;")
            lines.append(f"    module.add_class::<{class_name}>()?;")
        lines.append("    Ok(())")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)
