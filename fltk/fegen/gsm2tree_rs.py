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

# Labels whose per-label generated methods collide with fixed method names on the
# handle pyclass.  Rejection is a generation-time error naming the label and method.
# Currently only "children": extend_<lbl> with lbl="children" emits a second
# fn extend_children, which is a latent uncompilable-output bug.
_RESERVED_LABELS: dict[str, str] = {
    "children": "extend_children",
}


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
                    if item.label is not None:
                        if not _IDENTIFIER_RE.match(item.label):
                            msg = (
                                f"Item label {item.label!r} in rule {rule.name!r} is not a valid identifier "
                                f"(must match {_IDENTIFIER_RE.pattern!r})"
                            )
                            raise ValueError(msg)
                        if item.label in _RESERVED_LABELS:
                            colliding_method = _RESERVED_LABELS[item.label]
                            msg = (
                                f"Item label {item.label!r} in rule {rule.name!r} is reserved: "
                                f"it would generate a method 'extend_{item.label}' that collides with "
                                f"the fixed method '{colliding_method}'"
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
            "use fltk_cst_core::Span;\n"
            "use fltk_cst_core::Shared;\n"
            '#[cfg(feature = "python")]\n'
            "use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};\n"
            '#[cfg(feature = "python")]\n'
            "use fltk_cst_core::registry;\n"
            '#[cfg(feature = "python")]\n'
            "use pyo3::exceptions::{PyTypeError, PyValueError};\n"
            '#[cfg(feature = "python")]\n'
            "use pyo3::prelude::*;\n"
            '#[cfg(feature = "python")]\n'
            "use pyo3::types::{PyList, PyTuple, PyType};\n"
            '#[cfg(feature = "python")]\n'
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

        # Emit two enum definitions: one with pyclass/pyo3 attrs for python-on,
        # one plain for python-off.  cfg_attr on enum variant helper attributes
        # (pyo3(name=...)) fails with pyo3 0.23 when the outer pyclass is also
        # behind cfg_attr — the attribute validator fires before proc-macro
        # expansion so pyo3 is not yet registered as a helper attr.
        # Dual-cfg blocks are the correct pyo3-idiomatic workaround.
        # Variant names are extracted once and reused in both blocks to prevent drift.
        variant_names = [
            (self._node_kind_variant_name(cn), self._node_kind_python_name(rn)) for cn, _l, rn in rule_info
        ]
        lines.append('#[cfg(feature = "python")]')
        lines.append('#[pyclass(frozen, name = "NodeKind")]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append("pub enum NodeKind {")
        for variant, python_name in variant_names:
            lines.append(f'    #[pyo3(name = "{python_name}")]')
            lines.append(f"    {variant},")
        lines.append("}")
        lines.append("")
        lines.append('#[cfg(not(feature = "python"))]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append("pub enum NodeKind {")
        for variant, _python_name in variant_names:
            lines.append(f"    {variant},")
        lines.append("}")
        lines.append("")

        # pymethods block: __repr__, _fltk_canonical_name, __eq__, __hash__
        lines.append('#[cfg(feature = "python")]')
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

        # Dual-cfg blocks (same rationale as NodeKind above).
        # Variant names extracted once and reused in both blocks to prevent drift.
        label_variants = [(_rust_variant_name(lbl), _python_label_name(lbl)) for lbl in labels]
        lines.append("#[allow(non_camel_case_types)]")
        lines.append('#[cfg(feature = "python")]')
        lines.append(f'#[pyclass(frozen, name = "{enum_name}")]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append(f"pub enum {enum_name} {{")
        for rust_variant, python_name in label_variants:
            lines.append(f'    #[pyo3(name = "{python_name}")]')
            lines.append(f"    {rust_variant},")
        lines.append("}")
        lines.append("")
        lines.append("#[allow(non_camel_case_types)]")
        lines.append('#[cfg(not(feature = "python"))]')
        lines.append("#[derive(Clone, PartialEq, Eq, Hash)]")
        lines.append(f"pub enum {enum_name} {{")
        for rust_variant, _python_name in label_variants:
            lines.append(f"    {rust_variant},")
        lines.append("}")
        lines.append("")

        # pymethods block: __repr__, _fltk_canonical_name, __eq__, __hash__
        lines.append('#[cfg(feature = "python")]')
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
        """Emit the per-node child value enum (<Name>Child) + Clone/PartialEq impls.

        Node-typed variants use Shared<T> instead of Box<T> (Phase 1 ownership model).
        to_pyobject routes through the canonical-wrapper registry so repeated reads of
        the same child return the same Python handle (is-stable identity).
        extract_from_pyobject extracts the Shared<T> from the handle and hand-ins to registry.
        """
        child_classes, has_span = self._child_variants_for_rule(rule_name)
        enum_name = f"{class_name}Child"
        lines: list[str] = []

        lines.append(f"// {enum_name} — child value enum for {class_name}")
        lines.append("// Node-typed variants hold Shared<T> (Arc<RwLock<T>>); Clone is shallow.")
        lines.append("#[derive(Clone)]")
        lines.append(f"pub enum {enum_name} {{")
        if has_span:
            lines.append("    Span(Span),")
        for child_cls in child_classes:
            # Shared<T> instead of Box<T>
            lines.append(f"    {child_cls}(Shared<{child_cls}>),")
        lines.append("}")
        lines.append("")

        # Manual PartialEq (structural, using native span/node equality).
        # Shared::eq short-circuits on ptr_eq (handles x==x and DAG), then deep-compares.
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

        # to_pyobject/extract_from_pyobject: python-only, gate the entire impl block
        lines.append('#[cfg(feature = "python")]')
        lines.append(f"impl {enum_name} {{")

        # to_pyobject: translate a native child variant back to a Python object.
        # Node variants go through the canonical-wrapper registry so repeated reads
        # return the same Python handle (is-stable identity — resolves
        # TODO(rust-cst-child-node-identity)).
        py_param = "py" if (child_classes or has_span) else "_py"
        lines.append(f"    fn to_pyobject(&self, {py_param}: Python<'_>) -> PyResult<PyObject> {{")
        lines.append("        match self {")
        if has_span:
            lines.append("            Self::Span(s) => {")
            lines.append("                span_to_pyobject(py, s)")
            lines.append("            }")
        for child_cls in child_classes:
            py_handle = f"Py{child_cls}"
            lines.append(f"            Self::{child_cls}(shared) => {{")
            lines.append("                let addr = shared.arc_ptr();")
            lines.append("                registry::get_or_insert_with(py, addr, || {")
            lines.append(f"                    let handle = {py_handle} {{ inner: shared.clone() }};")
            lines.append("                    Py::new(py, handle).map(|p| p.into_any())")
            lines.append("                })")
            lines.append("            }")
        lines.append("        }")
        lines.append("    }")
        lines.append("")

        # extract_from_pyobject: convert a Python object to this child enum variant.
        # For node variants, extracts the Shared<T> from the handle and hand-ins to registry.
        # py is needed for span extraction OR for registry hand-in on node variants.
        needs_py = has_span or bool(child_classes)
        extract_py_param = "py" if needs_py else "_py"
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
            py_handle = f"Py{child_cls}"
            lines.append(f"        if obj.is_instance_of::<{py_handle}>() {{")
            lines.append(f"            let handle: PyRef<{py_handle}> = obj.extract()?;")
            lines.append("            let shared = handle.inner.clone();")
            lines.append("            let addr = shared.arc_ptr();")
            lines.append("            // Hand-in: register this Python handle as canonical for its Shared.")
            lines.append("            drop(handle); // release the PyRef before calling Python")
            lines.append("            // Propagate registry errors: a swallowed Err here would leave the")
            lines.append("            // handle unregistered, causing the next wrap-out to mint a different")
            lines.append("            // object and silently break is-stability.")
            lines.append("            registry::register_if_absent(py, addr, obj)?;")
            lines.append(f"            return Ok(Self::{child_cls}(shared));")
            lines.append("        }")
        if not has_span and not child_classes:
            # Degenerate case: no known child types — always error.
            # Use the underscore-prefixed param names chosen above to suppress unused-variable warnings.
            lines.append("        let _ = (_py, _span_type);")
        lines.append("        Err(pyo3::exceptions::PyTypeError::new_err(format!(")
        lines.append(f'            "{class_name}: unsupported child type {{}}",')
        lines.append("            obj.get_type().name()?")
        lines.append("        )))")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Node struct + handle pyclass
    # ------------------------------------------------------------------

    def _node_block(self, class_name: str, labels: list[str], rule_name: str) -> str:
        """Emit the node data struct, its plain impl, and the Python handle pyclass.

        Phase 1 ownership restructure:
        - Data struct (always compiled): carries `Shared<T>` children, suffixless native API.
        - Handle pyclass (python-gated): wraps `Shared<DataStruct>`, carries all pymethods.
          Python class name is unchanged (name = "ClassName").

        The handle is named Py<ClassName> in Rust; the data struct keeps the original name.
        """
        child_classes, has_span = self._child_variants_for_rule(rule_name)
        enum_name = f"{class_name}Child"
        label_type = f"Option<{class_name}_Label>" if labels else "Option<()>"
        py_handle = f"Py{class_name}"
        lines: list[str] = []

        lines.append(f"// {'─' * 75}")
        lines.append(f"// {class_name}")
        lines.append(f"// {'─' * 75}")
        lines.append("")

        # ── Data struct (always compiled) ──────────────────────────────────────
        # Clone is shallow (Arc clones for node children); called out in comment.
        lines.append(f"/// CST data struct for `{class_name}`. Node-typed children are [`Shared<T>`] —")
        lines.append("/// see [`fltk_cst_core::Shared`] for clone/equality/reference semantics.")
        lines.append("#[derive(Clone)]")
        lines.append(f"pub struct {class_name} {{")
        lines.append("    // Not pub: use span() / children() / push_child() — the stable accessor API.")
        lines.append("    // Direct field access bypasses any future validation logic on setters.")
        lines.append("    span: Span,")
        lines.append(f"    children: Vec<({label_type}, {enum_name})>,")
        lines.append("}")
        lines.append("")

        # Native PartialEq: compares span + children recursively.  For node-typed children,
        # Shared::PartialEq applies a ptr_eq short-circuit which eliminates same-lock re-entry
        # on `x == x`.  DAG comparisons (position-shifted sharing) still hold both guards
        # simultaneously; deadlock-free only absent concurrent writers — see Shared<T> docs.
        lines.append(f"impl PartialEq for {class_name} {{")
        lines.append("    fn eq(&self, other: &Self) -> bool {")
        lines.append("        self.span == other.span && self.children == other.children")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # Plain impl: suffixless Rust-native API (no _native suffix).
        # These are the stable public Rust surface that generated parsers build against.
        lines.append(f"impl {class_name} {{")
        lines.append("    /// Construct a node with the given span and no children.")
        lines.append("    /// GIL-free.")
        lines.append("    pub fn new(span: Span) -> Self {")
        lines.append(f"        {class_name} {{")
        lines.append("            span,")
        lines.append("            children: Vec::new(),")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Return a reference to the stored `Span`.")
        lines.append("    pub fn span(&self) -> &Span {")
        lines.append("        &self.span")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Return a slice of the children.")
        lines.append(f"    pub fn children(&self) -> &[({label_type}, {enum_name})] {{")
        lines.append("        self.children.as_slice()")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Replace the node's span.")
        lines.append("    pub fn set_span(&mut self, span: Span) {")
        lines.append("        self.span = span;")
        lines.append("    }")
        lines.append("")
        lines.append("    /// Push a child onto the children `Vec`.")
        lines.append(f"    pub fn push_child(&mut self, label: {label_type}, child: {enum_name}) {{")
        lines.append("        self.children.push((label, child));")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # ── Handle pyclass (python-gated) ──────────────────────────────────────
        # frozen: handle has no mutable fields (mutation goes through RwLock).
        # weakref: required by the canonical-wrapper registry.
        # name = "ClassName": Python class name is unchanged.
        lines.append('#[cfg(feature = "python")]')
        lines.append(f'#[pyclass(frozen, weakref, name = "{class_name}")]')
        lines.append(f"pub struct {py_handle} {{")
        lines.append("    // Not pub: all external access goes through shared() or to_py_canonical().")
        lines.append("    // A pub field would let mixed-app Rust code construct an unregistered handle")
        lines.append("    // (Py::new(py, PyFoo { inner: s.clone() })), silently breaking is-stability.")
        lines.append(f"    inner: Shared<{class_name}>,")
        lines.append("}")
        lines.append("")

        # Bridge methods on the handle struct (not pymethods — plain Rust)
        lines.append('#[cfg(feature = "python")]')
        lines.append(f"impl {py_handle} {{")
        lines.append(f"    /// Return a reference to the inner `Shared<{class_name}>`.")
        lines.append(f"    pub fn shared(&self) -> &Shared<{class_name}> {{")
        lines.append("        &self.inner")
        lines.append("    }")
        lines.append("")
        lines.append(f"    /// Wrap a `Shared<{class_name}>` into a canonical Python handle,")
        lines.append("    /// looking up the registry first so the same handle is returned")
        lines.append("    /// for the same `Shared` allocation.")
        lines.append(
            f"    pub fn to_py_canonical(py: Python<'_>, s: &Shared<{class_name}>) -> PyResult<Py<{py_handle}>> {{"
        )
        lines.append("        let addr = s.arc_ptr();")
        lines.append("        let obj = registry::get_or_insert_with(py, addr, || {")
        lines.append(f"            let handle = {py_handle} {{ inner: s.clone() }};")
        lines.append("            Py::new(py, handle).map(|p| p.into_any())")
        lines.append("        })?;")
        lines.append(
            f"        obj.bind(py).downcast::<{py_handle}>().map(|b| b.clone().unbind()).map_err(|e| e.into())"
        )
        lines.append("    }")
        lines.append("}")
        lines.append("")

        # pymethods block on the handle
        lines.append('#[cfg(feature = "python")]')
        lines.append("#[pymethods]")
        lines.append(f"impl {py_handle} {{")

        lines.extend(self._new_method(class_name, py_handle))
        lines.extend(self._span_getter_setter())
        lines.extend(self._kind_getter(class_name))

        if labels:
            lines.extend(self._label_classattr(class_name))

        lines.extend(self._children_getter(class_name, enum_name))
        lines.extend(self._generic_append(class_name, enum_name, label_type, labels))
        lines.extend(self._generic_extend(class_name, enum_name, label_type, labels))
        lines.extend(self._generic_extend_children(class_name, py_handle))
        lines.extend(self._generic_child(class_name, enum_name, label_type, labels))

        for label in labels:
            lines.extend(self._per_label_methods(class_name, label, enum_name))

        lines.extend(self._eq_method(class_name, py_handle))
        lines.extend(self._hash_method(class_name))
        lines.extend(self._repr_method(class_name, enum_name))

        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    def _new_method(self, class_name: str, py_handle: str) -> list[str]:
        """Emit the #[new] constructor on the handle pyclass.

        Creates a fresh Shared<DataStruct> and registers the handle as canonical.
        """
        return [
            "    #[new]",
            "    #[pyo3(signature = (*, span = None))]",
            f"    fn new(py: Python<'_>, span: Option<&Bound<'_, PyAny>>) -> PyResult<Py<{py_handle}>> {{",
            "        let native_span = match span {",
            "            Some(s) => extract_span(py, s)?,",
            "            None => Span::unknown(),",
            "        };",
            f"        let data = {class_name} {{",
            "            span: native_span,",
            "            children: Vec::new(),",
            "        };",
            "        let shared = Shared::new(data);",
            "        let addr = shared.arc_ptr();",
            f"        let handle = {py_handle} {{ inner: shared }};",
            "        let py_obj = Py::new(py, handle)?;",
            "        // Register as canonical — fresh Shared, no alias can exist yet.",
            "        registry::force_register(py, addr, py_obj.bind(py))?;",
            "        Ok(py_obj)",
            "    }",
            "",
        ]

    def _span_getter_setter(self) -> list[str]:
        # The handle is frozen (#[pyclass(frozen, ...)]), so all mutating pymethods
        # take &self — mutation goes through the inner RwLock.
        return [
            "    #[getter]",
            "    fn span(&self, py: Python<'_>) -> PyResult<PyObject> {",
            "        // Snapshot the span under the read lock, then drop the guard before",
            "        // calling span_to_pyobject — which performs Python work (Py::new or",
            "        // Python method calls) that must not happen while a node lock is held.",
            "        let span = self.inner.read().span.clone();",
            "        span_to_pyobject(py, &span)",
            "    }",
            "",
            "    #[setter]",
            "    fn set_span(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<()> {",
            "        self.inner.write().span = extract_span(py, value)?;",
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
        """Emit the `children` Python getter that rebuilds a list from the native Vec.

        The returned list is a per-call snapshot; in-place mutation of the list is a
        silent no-op on the tree.  The Python backend returns the node's actual internal
        list, so there is a known backend divergence on list-level identity.
        TODO(rust-cst-children-list-view): closing this would require a live sequence-proxy
        pyclass; deferred as additive per design ADR 2026/06/10-rust-idiomatic-cst-api §7 Q4.

        Node-typed children are routed through the registry so element identity is stable
        (the same child read twice returns the same Python handle object).
        """
        return [
            "    #[getter]",
            "    fn children(&self, py: Python<'_>) -> PyResult<Py<PyList>> {",
            "        // Snapshot the children vec (Arc clones for node children — O(n) refcount bumps).",
            "        // Lock scope: acquire read, snapshot, release before touching Python.",
            "        let snapshot: Vec<_> = {",
            "            let guard = self.inner.read();",
            "            guard.children.clone()",
            "        };",
            "        let result = PyList::empty(py);",
            "        for (label, child) in &snapshot {",
            "            let label_obj: PyObject = match label {",
            "                None => py.None(),",
            "                Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),",
            "            };",
            "            let child_obj = child.to_pyobject(py)?;",
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
            "    fn append(&self, py: Python<'_>, child: &Bound<'_, PyAny>, label: Option<PyObject>) -> PyResult<()> {",
            "        let span_type = get_span_type(py)?;",
            f"        let native_child = {enum_name}::extract_from_pyobject(py, child, &span_type)?;",
            "        let native_label = match label {",
            *self._label_from_pyobject_match(class_name, labels, method_name="append"),
            "        };",
            "        self.inner.write().children.push((native_label, native_child));",
            "        Ok(())",
            "    }",
            "",
        ]

    def _label_from_pyobject_match(self, class_name: str, labels: list[str], method_name: str) -> list[str]:
        """Emit the match arms for converting an Option<PyObject> label to native label type."""
        if not labels:
            return [
                "            None => None,",
                "            Some(lbl) => {",
                "                let lbl_type = lbl.bind(py).get_type().name()?;",
                "                return Err(PyTypeError::new_err(format!(",
                f'                    "{class_name}.{method_name}: no labels defined for this node; got {{}} label",',
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
            f'                        "{class_name}.{method_name}: label argument is not a {enum_name}; got {{}}",',
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
            "        &self,",
            "        py: Python<'_>,",
            "        children: &Bound<'_, PyAny>,",
            "        label: Option<PyObject>,",
            "    ) -> PyResult<()> {",
            "        let span_type = get_span_type(py)?;",
            "        let native_label = match label {",
            *self._label_from_pyobject_match(class_name, labels, method_name="extend"),
            "        };",
            "        let iter = children.try_iter()?;",
            "        for child_result in iter {",
            "            let child = child_result?;",
            f"            let native_child = {enum_name}::extract_from_pyobject(py, &child, &span_type)?;",
            "            self.inner.write().children.push((native_label.clone(), native_child));",
            "        }",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_extend_children(self, _class_name: str, py_handle: str) -> list[str]:
        """Emit extend_children(&self, other: &PyHandle) that bulk-copies children preserving labels.

        Self-extend (node.extend_children(node)) is handled structurally: we snapshot
        the other's children under a read lock, drop the lock, then push onto self.
        No ptr_eq call is needed — once the read guard drops, the write lock below can
        always be acquired, even when self and other are the same node.
        This matches the Python backend's list-copy behavior.
        """
        return [
            f"    fn extend_children(&self, _py: Python<'_>, other: &{py_handle}) -> PyResult<()> {{",
            "        // Snapshot other's children first: the read guard is dropped at the end of",
            "        // this block, so the write lock below is safe even when self and other are",
            "        // the same node (self-extend). No ptr_eq call is needed here — the snapshot",
            "        // approach handles self-extend structurally.",
            "        // Lock scope: hold read only long enough to clone the Arc-based children vec.",
            "        let snapshot: Vec<_> = {",
            "            let guard = other.inner.read();",
            "            guard.children.clone()",
            "        };",
            "        // Node-typed children are pushed directly as Shared<T> values.  Registry",
            "        // consistency is maintained lazily: wrap-out registers on first Python read",
            "        // via get_or_insert_with (registry.rs).  Eagerly registering here would be",
            "        // a no-op — the WeakValueDictionary would evict handles held by nothing.",
            "        self.inner.write().children.extend(snapshot);",
            "        Ok(())",
            "    }",
            "",
        ]

    def _generic_child(self, _class_name: str, _enum_name: str, _label_type: str, _labels: list[str]) -> list[str]:
        return [
            "    fn child(&self, py: Python<'_>) -> PyResult<PyObject> {",
            "        // TODO(rust-cst-accessor-clone-efficiency): clones the full children Vec",
            "        // before checking len. Could check len under the read guard and only clone",
            "        // the single needed entry, avoiding O(total-children) allocation on the error path.",
            "        let snapshot: Vec<_> = {",
            "            let guard = self.inner.read();",
            "            guard.children.clone()",
            "        };",
            "        let n = snapshot.len();",
            "        if n != 1 {",
            "            return Err(PyValueError::new_err(format!(",
            '                "Expected one child but have {n}"',
            "            )));",
            "        }",
            "        let (label, child) = &snapshot[0];",
            "        let label_obj: PyObject = match label {",
            "            None => py.None(),",
            "            Some(lbl) => lbl.clone().into_pyobject(py)?.into_any().unbind(),",
            "        };",
            "        let child_obj = child.to_pyobject(py)?;",
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
                f"    fn append_{label}(&self, py: Python<'_>, child: &Bound<'_, PyAny>) -> PyResult<()> {{",
                "        let span_type = get_span_type(py)?;",
                f"        let native_child = {child_enum_name}::extract_from_pyobject(py, child, &span_type)?;",
                f"        self.inner.write().children.push((Some({label_enum_name}::{rust_variant}), native_child));",
                "        Ok(())",
                "    }",
                "",
            ]
        )

        # extend_<label>: push multiple children with the given label
        lines.extend(
            [
                f"    fn extend_{label}(&self, py: Python<'_>, children: &Bound<'_, PyAny>) -> PyResult<()> {{",
                "        let span_type = get_span_type(py)?;",
                "        let iter = children.try_iter()?;",
                "        for child_result in iter {",
                "            let child = child_result?;",
                f"            let native_child = {child_enum_name}::extract_from_pyobject(py, &child, &span_type)?;",
                f"            let entry = (Some({label_enum_name}::{rust_variant}), native_child);",
                "            self.inner.write().children.push(entry);",
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
                "        // TODO(rust-cst-accessor-clone-efficiency): clones full Vec then filters outside the guard.",
                "        // Could filter inside the read guard (clone only matching entries) to avoid",
                "        // O(total-children) Arc clones for accessors that match a small subset.",
                "        let snapshot: Vec<_> = {",
                "            let guard = self.inner.read();",
                "            guard.children.clone()",
                "        };",
                "        let result = PyList::empty(py);",
                "        for (lbl, child) in &snapshot {",
                f"            if *lbl == Some({label_enum_name}::{rust_variant}) {{",
                "                result.append(child.to_pyobject(py)?)?;",
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
                "        // TODO(rust-cst-accessor-clone-efficiency): see children_{label} above.",
                "        let snapshot: Vec<_> = {",
                "            let guard = self.inner.read();",
                "            guard.children.clone()",
                "        };",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (lbl, child) in &snapshot {",
                f"            if *lbl == Some({label_enum_name}::{rust_variant}) {{",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(child.to_pyobject(py)?);",
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
                "        // TODO(rust-cst-accessor-clone-efficiency): see children_{label} above.",
                "        let snapshot: Vec<_> = {",
                "            let guard = self.inner.read();",
                "            guard.children.clone()",
                "        };",
                "        let mut found: Option<PyObject> = None;",
                "        let mut count = 0usize;",
                "        for (lbl, child) in &snapshot {",
                f"            if *lbl == Some({label_enum_name}::{rust_variant}) {{",
                "                count += 1;",
                "                if count == 1 {",
                "                    found = Some(child.to_pyobject(py)?);",
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

    def _eq_method(self, _class_name: str, py_handle: str) -> list[str]:
        """Emit __eq__ delegating to Shared<T>::PartialEq.

        Shared<T>::PartialEq already implements the ptr_eq short-circuit (handles `x == x`
        without taking the lock twice, which std::sync::RwLock may deadlock on one thread when
        a writer is queued) followed by deep structural comparison.  Delegating here keeps the
        short-circuit logic in one place (shared.rs) rather than duplicated across every
        generated __eq__ body.
        """
        return [
            "    fn __eq__(&self, py: Python<'_>, other: &Bound<'_, PyAny>) -> PyResult<PyObject> {",
            f"        if !other.is_instance_of::<{py_handle}>() {{",
            "            return Ok(py.NotImplemented());",
            "        }",
            f"        let other_handle: PyRef<{py_handle}> = other.extract()?;",
            "        // Delegate to Shared<T>::PartialEq which applies the ptr_eq short-circuit",
            "        // (avoids same-lock re-entry on `x == x`) then deep structural comparison.",
            "        let eq = self.inner == other_handle.inner;",
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
            "        let guard = self.inner.read();",
            '        let span_repr = format!("Span(start={}, end={})", guard.span.start(), guard.span.end());',
            "        let children_len = guard.children.len();",
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
        lines.append('#[cfg(feature = "python")]')
        lines.append("pub fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {")
        # NodeKind must be registered before node structs (whose kind getter returns it).
        lines.append("    module.add_class::<NodeKind>()?;")
        for class_name, labels, _rule_name in self._rule_info():
            if labels:
                enum_name = f"{class_name}_Label"
                lines.append(f"    module.add_class::<{enum_name}>()?;")
            py_handle = f"Py{class_name}"
            lines.append(f"    module.add_class::<{py_handle}>()?;")
        lines.append("    Ok(())")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)
