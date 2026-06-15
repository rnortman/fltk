"""Rust lib.rs generator for FLTK pyo3 cdylib crates.

Generates the module-wiring boilerplate lib.rs that every Rust-backend consumer
needs: use declarations, mod declarations, and the #[pymodule] entry point.
Unlike the CST/parser generators, this does not consume grammar rules — lib.rs
has no rule-derived content.  It is a small templating unit over a structured
description of the module layout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Standard Rust identifier: letter or underscore, then alphanumerics or underscores.
_RUST_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_rust_ident(value: str, label: str) -> None:
    """Raise ValueError if value is not a valid Rust identifier."""
    if not value or not _RUST_IDENT_RE.match(value):
        msg = f"Invalid Rust identifier for {label}: {value!r}"
        raise ValueError(msg)


@dataclass(frozen=True)
class Submodule:
    """Describes one Rust submodule registered into the #[pymodule]."""

    mod_name: str
    """Rust `mod <mod_name>;` — the .rs file basename stem."""

    submodule_name: str
    """Python submodule name passed to register_submodule."""

    register_fn: str = "register_classes"
    """Registration entry point function name within the Rust module."""

    def validate(self) -> None:
        """Raise ValueError if any field is not a valid Rust identifier.

        Note: validation is limited to Rust identifier syntax.  A register_fn that is a
        valid identifier but not a reachable function in the Rust crate will produce a
        Rust compile error rather than a Python-level error here.
        # TODO(submodule-register-fn-convention): document or enforce the convention that
        # register_fn should be 'register_classes' to match the codegenned crate shape.
        """
        _validate_rust_ident(self.mod_name, "mod_name")
        _validate_rust_ident(self.submodule_name, "submodule_name")
        _validate_rust_ident(self.register_fn, "register_fn")


@dataclass(frozen=True)
class LibSpec:
    """Complete description of a lib.rs module layout."""

    module_name: str
    """#[pymodule] fn name; the importable module name (e.g. 'clockwork_native')."""

    submodules: tuple[Submodule, ...]
    """Submodules to declare and register."""

    register_span_types: bool = False
    """If True, emit Span/SourceText class registration and span module import."""

    unknown_span_static: bool = False
    """If True, emit the UNKNOWN_SPAN static declaration and once-init."""

    @staticmethod
    def standard(module_name: str, *, with_parser: bool = True) -> LibSpec:
        """Convenience constructor for the standard one-CST [+ one-parser] layout.

        Args:
            module_name: The #[pymodule] function name / importable module name.
            with_parser: If True (default), include cst + parser submodules.
                         If False, include only the cst submodule.
        """
        submodules: list[Submodule] = [Submodule("cst", "cst")]
        if with_parser:
            submodules.append(Submodule("parser", "parser"))
        return LibSpec(module_name=module_name, submodules=tuple(submodules))

    def validate(self) -> None:
        """Raise ValueError if any field contains invalid identifiers."""
        _validate_rust_ident(self.module_name, "module_name")
        for sub in self.submodules:
            sub.validate()
        if not self.submodules and not self.register_span_types and not self.unknown_span_static:
            msg = "LibSpec.submodules must not be empty when no span types or UNKNOWN_SPAN are registered"
            raise ValueError(msg)
        if self.unknown_span_static and not self.register_span_types:
            msg = (
                "LibSpec.unknown_span_static=True requires register_span_types=True: "
                "UNKNOWN_SPAN initialization calls Span::unknown() and the generated code "
                "references Span, which is only imported when register_span_types is True"
            )
            raise ValueError(msg)


class RustLibGenerator:
    """Generates a complete lib.rs string from a LibSpec."""

    def __init__(self, spec: LibSpec) -> None:
        spec.validate()
        self.spec = spec

    def generate(self) -> str:
        """Generate and return the complete lib.rs source string."""
        spec = self.spec
        lines: list[str] = []

        # --- use declarations ---
        if spec.submodules:
            lines.append("use fltk_cst_core::register_submodule;")
        lines.append("use pyo3::prelude::*;")
        if spec.unknown_span_static:
            lines.append("use pyo3::sync::PyOnceLock;")
        lines.append("")

        # --- mod declarations ---
        if spec.register_span_types:
            lines.append("mod span;")
        for sub in spec.submodules:
            lines.append(f"mod {sub.mod_name};")
        lines.append("")

        # --- extra use for span types ---
        if spec.register_span_types:
            lines.append("use span::{SourceText, Span};")
            lines.append("")

        # --- UNKNOWN_SPAN static ---
        # The static is set once at module init (see the #[pymodule] body below) and
        # exposed to Python callers as `UnknownSpan`.  Generated node code does not
        # read it directly — each extension caches the sentinel via its own
        # PyOnceLock by importing fltk._native.UnknownSpan at runtime.
        if spec.unknown_span_static:
            lines.append(
                f"// UNKNOWN_SPAN is set at module init (below) and exposed as `{spec.module_name}.UnknownSpan`."
            )
            lines.append("pub(crate) static UNKNOWN_SPAN: PyOnceLock<Py<PyAny>> = PyOnceLock::new();")
            lines.append("")

        # --- #[pymodule] function ---
        lines.append("#[pymodule]")
        lines.append(f"fn {spec.module_name}(m: &Bound<'_, PyModule>) -> PyResult<()> {{")

        body: list[str] = []

        if spec.register_span_types:
            body.append("    // Canonical Span/SourceText/UnknownSpan live at the top level.")
            body.append("    m.add_class::<Span>()?;")
            body.append("    m.add_class::<SourceText>()?;")

        if spec.unknown_span_static:
            # TODO(native-span-init-error-context): Py::new failure here surfaces as a generic
            # pyo3 RuntimeError with no indication that it occurred during UnknownSpan sentinel
            # creation.  Wrap with a structured message for on-call clarity.
            body.append("    let unknown_span_obj = Py::new(m.py(), Span::unknown())?.into_any();")
            body.append('    m.add("UnknownSpan", unknown_span_obj.clone_ref(m.py()))?;')
            body.append("    UNKNOWN_SPAN")
            body.append("        .set(m.py(), unknown_span_obj)")
            body.append('        .expect("UNKNOWN_SPAN already set; module initialized twice");')

        if (spec.register_span_types or spec.unknown_span_static) and spec.submodules:
            body.append("")

        for sub in spec.submodules:
            body.append(f'    register_submodule(m, "{sub.submodule_name}", {sub.mod_name}::{sub.register_fn})?;')

        body.append("    Ok(())")
        body.append("}")

        lines.extend(body)
        lines.append("")  # trailing newline

        return "\n".join(lines)
