"""Unit tests for the resolver plugin loader and contract dataclasses (M5).

``load_resolver`` must accept both ``module.path:attr`` and ``path/to/file.py:attr`` specs,
handle a bare instance or a zero-argument factory, default the attribute to ``create_resolver``,
and fail with an actionable :class:`ResolverError` on every misconfiguration -- so the CLI can
map it to a stderr message and exit 1 before any protocol I/O.
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from fltk.lsp import resolver
from fltk.lsp.resolver import CrossFileResolution, ExternalTarget, ResolverError, load_resolver

# A resolver module body reused across the spec-shape tests: a bare instance, a factory, and a
# few deliberately-broken attributes for the validation cases.
_RESOLVER_SRC = """
from fltk.lsp.resolver import CrossFileResolution


class _Gearish:
    file_suffixes = (".gear", ".gr")

    def resolve(self, doc, host):
        return CrossFileResolution()


instance = _Gearish()


def create_resolver():
    return _Gearish()


def make():
    return _Gearish()


not_a_resolver = 42


class _NoResolve:
    file_suffixes = (".gear",)


no_resolve_method = _NoResolve()


class _BadSuffixes:
    file_suffixes = ()

    def resolve(self, doc, host):
        return CrossFileResolution()


empty_suffixes = _BadSuffixes()


class _UndottedSuffixes:
    file_suffixes = ("gear",)

    def resolve(self, doc, host):
        return CrossFileResolution()


undotted_suffixes = _UndottedSuffixes()


class _StringSuffixes:
    file_suffixes = ".gear"

    def resolve(self, doc, host):
        return CrossFileResolution()


string_suffixes = _StringSuffixes()


def broken_factory():
    raise RuntimeError("boom in factory")
"""


@pytest.fixture
def resolver_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Write ``_RESOLVER_SRC`` as an importable module on ``sys.path``; return its module name."""
    module_name = "_fltk_test_resolver_mod"
    (tmp_path / f"{module_name}.py").write_text(_RESOLVER_SRC)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    return module_name


@pytest.fixture
def resolver_file(tmp_path: Path) -> Path:
    """Write ``_RESOLVER_SRC`` as a standalone ``.py`` file (not on ``sys.path``)."""
    path = tmp_path / "gear_resolver.py"
    path.write_text(_RESOLVER_SRC)
    return path


# --- spec shapes ---------------------------------------------------------------------------


def test_module_attr_instance(resolver_module: str) -> None:
    r = load_resolver(f"{resolver_module}:instance")
    assert tuple(r.file_suffixes) == (".gear", ".gr")
    assert callable(r.resolve)


def test_module_attr_factory(resolver_module: str) -> None:
    r = load_resolver(f"{resolver_module}:make")
    assert tuple(r.file_suffixes) == (".gear", ".gr")


def test_module_attr_class_is_instantiated(resolver_module: str) -> None:
    # Naming the class (not the create_resolver factory) is the natural spec mistake; the loader must
    # instantiate it rather than accept the bare class, whose unbound `resolve` would TypeError on
    # every request and leave a half-working server.
    r = load_resolver(f"{resolver_module}:_Gearish")
    assert not isinstance(r, type)
    assert tuple(r.file_suffixes) == (".gear", ".gr")
    assert callable(r.resolve)


def test_default_attr_convention(resolver_module: str) -> None:
    # No ':attr' -> defaults to create_resolver.
    r = load_resolver(resolver_module)
    assert tuple(r.file_suffixes) == (".gear", ".gr")


def test_file_spec_with_attr(resolver_file: Path) -> None:
    r = load_resolver(f"{resolver_file}:create_resolver")
    assert tuple(r.file_suffixes) == (".gear", ".gr")


def test_file_spec_default_attr(resolver_file: Path) -> None:
    r = load_resolver(str(resolver_file))
    assert tuple(r.file_suffixes) == (".gear", ".gr")


def test_file_spec_recognized_by_dot_py_even_if_absent() -> None:
    # A '.py' head is a file spec, so a missing file reports a file error (not an import error).
    with pytest.raises(ResolverError, match="does not exist"):
        load_resolver("/no/such/gear_resolver.py:create_resolver")


# --- validation failures -------------------------------------------------------------------


def test_bad_module_import() -> None:
    with pytest.raises(ResolverError, match="cannot import module"):
        load_resolver("fltk_no_such_module_xyz:create_resolver")


def test_missing_attr(resolver_module: str) -> None:
    with pytest.raises(ResolverError, match="no attribute"):
        load_resolver(f"{resolver_module}:does_not_exist")


def test_attr_not_a_resolver(resolver_module: str) -> None:
    with pytest.raises(ResolverError, match="neither a resolver.*nor callable"):
        load_resolver(f"{resolver_module}:not_a_resolver")


def test_missing_resolve_method(resolver_module: str) -> None:
    # An instance without 'resolve' is not callable either -> instantiate path rejects it.
    with pytest.raises(ResolverError, match="neither a resolver.*nor callable"):
        load_resolver(f"{resolver_module}:no_resolve_method")


def test_empty_file_suffixes(resolver_module: str) -> None:
    with pytest.raises(ResolverError, match="file_suffixes is empty"):
        load_resolver(f"{resolver_module}:empty_suffixes")


def test_undotted_file_suffix(resolver_module: str) -> None:
    with pytest.raises(ResolverError, match="'.'-prefixed"):
        load_resolver(f"{resolver_module}:undotted_suffixes")


def test_string_file_suffixes_rejected(resolver_module: str) -> None:
    # A bare string is a Sequence of chars; the loader must reject it as a suffix list.
    with pytest.raises(ResolverError, match="sequence of extensions"):
        load_resolver(f"{resolver_module}:string_suffixes")


def test_factory_exception_wrapped(resolver_module: str) -> None:
    with pytest.raises(ResolverError, match="factory call failed"):
        load_resolver(f"{resolver_module}:broken_factory")


def test_empty_spec() -> None:
    with pytest.raises(ResolverError, match="empty"):
        load_resolver("")


def test_file_import_error_wrapped(tmp_path: Path) -> None:
    bad = tmp_path / "broken_resolver.py"
    bad.write_text("import fltk_no_such_module_xyz\n")
    with pytest.raises(ResolverError, match="error importing file"):
        load_resolver(str(bad))


def test_resolver_error_is_value_error() -> None:
    # The CLI's fail-fast handler catches ValueError; ResolverError must be one.
    assert issubclass(ResolverError, ValueError)


# --- contract dataclasses ------------------------------------------------------------------


def test_cross_file_resolution_defaults_empty() -> None:
    res = CrossFileResolution()
    assert res.ref_targets == {}
    assert res.symbol_targets == {}


def test_external_target_is_frozen() -> None:
    target = ExternalTarget(uri="file:///a", name_start=1, name_end=2, range_start=0, range_end=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        target.uri = "file:///b"  # type: ignore[misc]


def test_resolver_runtime_checkable(resolver_module: str) -> None:
    r = load_resolver(f"{resolver_module}:instance")
    assert isinstance(r, resolver.Resolver)
