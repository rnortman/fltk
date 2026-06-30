"""Unit tests for gsm2lib_rs.py — RustLibGenerator and LibSpec."""

from __future__ import annotations

import ast

import pytest

from fltk.fegen.gsm2lib_rs import LibSpec, RustLibGenerator, Submodule, render_stub_package_init

# ---------------------------------------------------------------------------
# Standard output — design §4 "Unit (string output)" items
# ---------------------------------------------------------------------------


def test_standard_output_contains_required_imports() -> None:
    """Standard lib.rs contains the required use declarations."""
    spec = LibSpec.standard("clockwork_native")
    src = RustLibGenerator(spec).generate()

    assert "use fltk_cst_core::register_submodule;" in src
    assert "use pyo3::prelude::*;" in src


def test_standard_output_contains_mod_declarations() -> None:
    """Standard lib.rs contains mod cst; and mod parser;."""
    spec = LibSpec.standard("clockwork_native")
    src = RustLibGenerator(spec).generate()

    assert "mod cst;" in src
    assert "mod parser;" in src


def test_standard_output_contains_pymodule_fn() -> None:
    """Standard lib.rs contains the #[pymodule] fn with the correct name."""
    spec = LibSpec.standard("clockwork_native")
    src = RustLibGenerator(spec).generate()

    assert "fn clockwork_native(" in src


def test_standard_output_contains_registrations() -> None:
    """Standard lib.rs contains both register_submodule calls."""
    spec = LibSpec.standard("my_module")
    src = RustLibGenerator(spec).generate()

    assert 'register_submodule(m, "cst", cst::register_classes)' in src
    assert 'register_submodule(m, "parser", parser::register_classes)' in src


def test_standard_output_contains_ok() -> None:
    """Standard lib.rs contains Ok(())."""
    spec = LibSpec.standard("my_module")
    src = RustLibGenerator(spec).generate()

    assert "Ok(())" in src


def test_standard_output_no_recursion_limit() -> None:
    """Standard lib.rs must NOT contain recursion_limit (Bazel macro owns it)."""
    spec = LibSpec.standard("clockwork_native")
    src = RustLibGenerator(spec).generate()

    assert "recursion_limit" not in src


def test_standard_output_no_span_types() -> None:
    """Standard lib.rs must NOT register Span/SourceText/UnknownSpan."""
    spec = LibSpec.standard("clockwork_native")
    src = RustLibGenerator(spec).generate()

    assert "Span" not in src
    assert "SourceText" not in src
    assert "UnknownSpan" not in src
    assert "UNKNOWN_SPAN" not in src


# ---------------------------------------------------------------------------
# --no-parser / with_parser=False  — design §4 "Unit" items
# ---------------------------------------------------------------------------


def test_no_parser_omits_parser_mod_and_registration() -> None:
    """with_parser=False omits mod parser; and the parser registration."""
    spec = LibSpec.standard("my_module", with_parser=False)
    src = RustLibGenerator(spec).generate()

    assert "mod cst;" in src
    assert "mod parser;" not in src
    assert '"parser"' not in src


def test_no_parser_keeps_cst() -> None:
    """with_parser=False still emits mod cst; and cst registration."""
    spec = LibSpec.standard("my_module", with_parser=False)
    src = RustLibGenerator(spec).generate()

    assert "mod cst;" in src
    assert 'register_submodule(m, "cst", cst::register_classes)' in src


# ---------------------------------------------------------------------------
# with_unparser  — design §2.5 LibSpec wiring
# ---------------------------------------------------------------------------


def test_default_omits_unparser() -> None:
    """with_unparser defaults to False: no mod unparser; or registration."""
    spec = LibSpec.standard("my_module")
    src = RustLibGenerator(spec).generate()

    assert "mod unparser;" not in src
    assert '"unparser"' not in src


def test_with_unparser_emits_unparser_mod_and_registration() -> None:
    """with_unparser=True emits mod unparser; and its register_submodule call."""
    spec = LibSpec.standard("my_module", with_unparser=True)
    src = RustLibGenerator(spec).generate()

    assert "mod unparser;" in src
    assert 'register_submodule(m, "unparser", unparser::register_classes)' in src


def test_with_unparser_keeps_cst_and_parser() -> None:
    """with_unparser=True (parser default True) emits all three submodules."""
    spec = LibSpec.standard("my_module", with_unparser=True)
    src = RustLibGenerator(spec).generate()

    assert "mod cst;" in src
    assert "mod parser;" in src
    assert "mod unparser;" in src


def test_with_unparser_no_parser() -> None:
    """with_parser=False, with_unparser=True emits cst + unparser, no parser."""
    spec = LibSpec.standard("my_module", with_parser=False, with_unparser=True)
    src = RustLibGenerator(spec).generate()

    assert "mod cst;" in src
    assert "mod unparser;" in src
    assert "mod parser;" not in src
    assert '"parser"' not in src


def test_with_unparser_registration_order() -> None:
    """Submodule registrations are emitted cst, parser, unparser in order."""
    spec = LibSpec.standard("my_module", with_unparser=True)
    src = RustLibGenerator(spec).generate()

    cst_pos = src.index('register_submodule(m, "cst"')
    parser_pos = src.index('register_submodule(m, "parser"')
    unparser_pos = src.index('register_submodule(m, "unparser"')
    assert cst_pos < parser_pos < unparser_pos


# ---------------------------------------------------------------------------
# Validation — design §4 "Unit" items
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_name",
    ["", "1bad", "has space", "a-b"],
)
def test_invalid_module_name_raises_value_error(module_name: str) -> None:
    """Invalid module_name raises ValueError naming the offending value."""
    with pytest.raises(ValueError, match=module_name if module_name else "module_name"):
        LibSpec(module_name=module_name, submodules=()).validate()


def test_valid_underscore_prefix_module_name() -> None:
    """Module names starting with underscore (e.g. _native) are valid."""
    spec = LibSpec.standard("_native")
    src = RustLibGenerator(spec).generate()
    assert "fn _native(" in src


def test_empty_submodules_raises_value_error() -> None:
    """LibSpec with no submodules and no span/UNKNOWN_SPAN raises ValueError."""
    with pytest.raises(ValueError, match="submodules"):
        LibSpec(module_name="my_module", submodules=()).validate()


def test_unknown_span_static_without_register_span_types_raises_value_error() -> None:
    """unknown_span_static=True requires register_span_types=True; omitting it raises ValueError."""
    with pytest.raises(ValueError, match="register_span_types"):
        LibSpec(
            module_name="_native",
            submodules=(),
            register_span_types=False,
            unknown_span_static=True,
        ).validate()


# ---------------------------------------------------------------------------
# gen-rust-lib span-only path (--no-cst --register-span-types --unknown-span-static)
# ---------------------------------------------------------------------------


def _span_only_spec() -> LibSpec:
    """Return a span-only LibSpec equivalent to what --no-cst --register-span-types --unknown-span-static produces."""
    return LibSpec(
        module_name="_native",
        submodules=(),
        register_span_types=True,
        unknown_span_static=True,
    )


def test_span_only_contains_span_module() -> None:
    """Span-only lib.rs contains mod span; and use span::{SourceText, Span}."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "mod span;" in src
    assert "use span::{SourceText, Span};" in src


def test_span_only_contains_py_once_lock() -> None:
    """Span-only lib.rs uses pyo3::sync::PyOnceLock for the UNKNOWN_SPAN static."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "pyo3::sync::PyOnceLock" in src


def test_span_only_registers_span_classes() -> None:
    """Span-only lib.rs registers Span and SourceText as Python classes."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "m.add_class::<Span>()" in src
    assert "m.add_class::<SourceText>()" in src


def test_span_only_adds_unknown_span_attribute() -> None:
    """Span-only lib.rs adds UnknownSpan as a module attribute."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert 'm.add("UnknownSpan"' in src


def test_span_only_unknown_span_static() -> None:
    """Span-only lib.rs declares the UNKNOWN_SPAN static."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "UNKNOWN_SPAN" in src


def test_span_only_unknown_span_once_init_message() -> None:
    """Span-only lib.rs contains the exact once-init expect message."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "UNKNOWN_SPAN already set; module initialized twice" in src


def test_span_only_fn_name() -> None:
    """Span-only lib.rs defines fn _native(...)."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "fn _native(" in src


def test_span_only_zero_register_submodule_calls() -> None:
    """Span-only lib.rs emits no register_submodule import or call sites."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "register_submodule" not in src


def test_span_only_no_poc_cst_or_fegen_cst() -> None:
    """Span-only lib.rs does not reference poc_cst or fegen_cst."""
    src = RustLibGenerator(_span_only_spec()).generate()

    assert "poc_cst" not in src
    assert "fegen_cst" not in src
    assert "cst_generated" not in src
    assert "cst_fegen" not in src


def test_span_only_output_ends_with_newline() -> None:
    """Span-only _native lib.rs ends with a newline."""
    src = RustLibGenerator(_span_only_spec()).generate()
    assert src.endswith("\n")


# ---------------------------------------------------------------------------
# Submodule.validate() — direct field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_name", ["", "1start", "has-hyphen", "has space"])
def test_submodule_mod_name_validation(bad_name: str) -> None:
    """Invalid mod_name raises ValueError."""
    sub = Submodule(mod_name=bad_name, submodule_name="ok")
    with pytest.raises(ValueError):
        sub.validate()


@pytest.mark.parametrize("bad_name", ["", "1start", "has-hyphen"])
def test_submodule_submodule_name_validation(bad_name: str) -> None:
    """Invalid submodule_name raises ValueError."""
    sub = Submodule(mod_name="ok", submodule_name=bad_name)
    with pytest.raises(ValueError):
        sub.validate()


# ---------------------------------------------------------------------------
# Output ends with newline
# ---------------------------------------------------------------------------


def test_standard_output_ends_with_newline() -> None:
    """Generated lib.rs ends with a newline."""
    spec = LibSpec.standard("my_module")
    src = RustLibGenerator(spec).generate()
    assert src.endswith("\n")


# ---------------------------------------------------------------------------
# register_span_types=True, unknown_span_static=False combination
# Exercises the conditional-emission path: span types registered, no UNKNOWN_SPAN static.
# ---------------------------------------------------------------------------


def _span_types_no_unknown_span_spec() -> LibSpec:
    """A LibSpec with span type registration but no UNKNOWN_SPAN static."""
    return LibSpec(
        module_name="my_ext",
        submodules=(Submodule("cst", "cst"),),
        register_span_types=True,
        unknown_span_static=False,
    )


def test_span_types_without_unknown_span_emits_span_module_and_classes() -> None:
    """register_span_types=True, unknown_span_static=False: mod span; and class registrations present."""
    src = RustLibGenerator(_span_types_no_unknown_span_spec()).generate()

    assert "mod span;" in src
    assert "use span::{SourceText, Span};" in src
    assert "m.add_class::<Span>()" in src
    assert "m.add_class::<SourceText>()" in src


def test_span_types_without_unknown_span_omits_unknown_span_static() -> None:
    """register_span_types=True, unknown_span_static=False: UNKNOWN_SPAN static and PyOnceLock absent."""
    src = RustLibGenerator(_span_types_no_unknown_span_spec()).generate()

    assert "UNKNOWN_SPAN" not in src
    assert "PyOnceLock" not in src


def test_span_types_without_unknown_span_still_registers_submodules() -> None:
    """register_span_types=True, unknown_span_static=False: submodule registrations coexist with span types."""
    src = RustLibGenerator(_span_types_no_unknown_span_spec()).generate()

    assert "register_submodule" in src
    assert 'register_submodule(m, "cst", cst::register_classes)' in src


# ---------------------------------------------------------------------------
# render_stub_package_init — stub-package __init__.pyi marker (design §2.2, §5)
# ---------------------------------------------------------------------------


def test_render_stub_package_init_names_extension_and_submodules() -> None:
    """Marker text names the extension and each submodule."""
    text = render_stub_package_init("myext", ["alpha", "beta", "gamma"])

    assert "myext" in text
    assert "alpha" in text
    assert "beta" in text
    assert "gamma" in text


def test_render_stub_package_init_is_comment_only_empty_module() -> None:
    """Marker is comment-only: every non-blank line is a comment and it parses as an empty module."""
    text = render_stub_package_init("fegen_rust_cst", ["cst", "parser", "unparser"])

    for line in text.splitlines():
        assert line == "" or line.lstrip().startswith("#")
    assert ast.parse(text).body == []


def test_render_stub_package_init_ends_with_newline() -> None:
    """Marker ends with a trailing newline (ruff-stable)."""
    text = render_stub_package_init("fegen_rust_cst", ["cst", "parser"])

    assert text.endswith("\n")


def test_render_stub_package_init_is_idempotent() -> None:
    """Re-rendering with the same inputs yields byte-identical text."""
    args = ("rust_parser_fixture", ["cst", "parser", "unparser"])

    assert render_stub_package_init(*args) == render_stub_package_init(*args)


def test_render_stub_package_init_rejects_bad_extension_name() -> None:
    """Invalid extension name raises ValueError naming the field."""
    with pytest.raises(ValueError, match="extension_name"):
        render_stub_package_init("1bad", ["cst"])


def test_render_stub_package_init_rejects_bad_submodule() -> None:
    """A non-identifier submodule entry raises ValueError."""
    with pytest.raises(ValueError, match="submodule"):
        render_stub_package_init("ext", ["cst", "has-hyphen"])


def test_render_stub_package_init_rejects_empty_submodules() -> None:
    """Empty submodule list raises ValueError."""
    with pytest.raises(ValueError, match="submodule"):
        render_stub_package_init("ext", [])
