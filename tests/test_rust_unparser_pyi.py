"""Pyright coverage for the committed fixture unparser .pyi stub (design OQ-3).

The Rust unparser generator emits a ``.pyi`` describing the ``Unparser`` / ``Doc`` Python
surface (``gsm2unparser_rs.RustUnparserGenerator.generate_pyi``).  For the
``rust_parser_fixture`` grammar that stub is committed at
``fltk/_stubs/rust_parser_fixture/unparser.pyi`` and types each ``unparse_{rule}`` method's
``node`` parameter against the committed CST protocol module
``tests/rust_parser_fixture_cst_protocol.py`` (the analog of the CST backend's
``fltk/_stubs/fegen_rust_cst/cst.pyi`` + ``fltk.fegen.fltk_cst_protocol`` precedent).

The committed stub is already in pyright's checked set (it lives under ``fltk/``, which the
project ``[tool.pyright]`` ``include`` covers), so ``make typecheck`` guards the stub's own
internal consistency.  These tests add what the project run does not: a *consumer-facing*
guard that a downstream caller gets a genuinely typed surface --

- a correct consumer of ``rust_parser_fixture.unparser`` is pyright-clean, and
- a misuse (passing a non-node where a ``_proto`` node type is required) is a pyright error,

so the stub demonstrably *constrains* types rather than degrading to ``Any``.  These run via
the committed ``.pyi`` alone (no built extension), so they do not require
``make build-rust-parser-fixture``.
"""

from __future__ import annotations

import pathlib

import pytest

from tests.pyright_test_utils import (
    _diags_for_file,
    _run_pyright_over_dir,
    pyright_runnable,
    write_pyright_config,
)

_REPO_ROOT = pathlib.Path(__file__).parent.parent
_STUB_DIR = _REPO_ROOT / "fltk" / "_stubs" / "rust_parser_fixture"
_UNPARSER_PYI = _STUB_DIR / "unparser.pyi"
_STUB_INIT_PYI = _STUB_DIR / "__init__.pyi"
_PROTOCOL_MODULE = _REPO_ROOT / "tests" / "rust_parser_fixture_cst_protocol.py"

# A correct consumer: construct the Unparser, call a string method (-> str | None) and the
# additive Doc method (-> Doc | None), render the Doc.  node is typed via the committed
# protocol module, so a downstream Rust-CST node structurally conforms without a cast.
_CONSUMER_OK = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp
import tests.rust_parser_fixture_cst_protocol as proto


def use(node: proto.Num) -> str | None:
    u = unp.Unparser()
    rendered: str | None = u.unparse_num(node, max_width=80, indent_width=4)
    doc: unp.Doc | None = u.unparse_num_doc(node)
    if doc is not None:
        return doc.render(max_width=40)
    return rendered
"""

# A misuse: passing an int where the stub requires a _proto.Num node.  If the stub typed node
# as Any this would NOT error; a reportArgumentType error proves the surface is constrained.
_CONSUMER_BAD = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp


def misuse() -> None:
    u = unp.Unparser()
    u.unparse_num(123)
"""

# A misuse: assigning unparse_num's return (str | None) to a str-only variable.  This errors only
# if the stub keeps `| None`; if the return were narrowed to `str` (or degraded to Any) it would
# silently type-check.  Guards the return type's `| None`, which the OK consumer cannot detect
# (str | None, str, and Any are all assignable to a `str | None` target).
_CONSUMER_BAD_NARROWING = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp
import tests.rust_parser_fixture_cst_protocol as proto


def bad_narrow(node: proto.Num) -> None:
    u = unp.Unparser()
    result: str = u.unparse_num(node)
"""

# A misuse: assigning Doc.render()'s return (str) to an int-only variable.  This errors only if
# render() is typed `-> str`; if it degraded to Any the assignment would silently type-check.
_CONSUMER_BAD_RENDER = """\
from __future__ import annotations

import rust_parser_fixture.unparser as unp
import tests.rust_parser_fixture_cst_protocol as proto


def bad_render(node: proto.Num) -> None:
    u = unp.Unparser()
    doc: unp.Doc | None = u.unparse_num_doc(node)
    if doc is not None:
        result: int = doc.render()
"""


@pytest.fixture(scope="session")
def pyright_available() -> bool:
    return pyright_runnable()


@pytest.fixture(scope="module")
def consumer_pyright_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict]]:
    """Run pyright once over the consumer fixtures, resolving the committed stub.

    The tmpdir pyrightconfig adds the repo root (for ``tests.rust_parser_fixture_cst_protocol``
    and the stub package) and ``fltk/_stubs`` (for the ``rust_parser_fixture`` stub package) to
    ``extraPaths``, so pyright resolves ``rust_parser_fixture.unparser`` to the committed
    ``unparser.pyi`` exactly as the project-wide run does via ``pyproject``'s ``extraPaths``.
    """
    tmpdir = tmp_path_factory.mktemp("unparser_pyi")
    write_pyright_config(tmpdir, extra_paths=[str(_REPO_ROOT), str(_REPO_ROOT / "fltk" / "_stubs")])
    (tmpdir / "consumer_ok.py").write_text(_CONSUMER_OK)
    (tmpdir / "consumer_bad.py").write_text(_CONSUMER_BAD)
    (tmpdir / "consumer_bad_narrowing.py").write_text(_CONSUMER_BAD_NARROWING)
    (tmpdir / "consumer_bad_render.py").write_text(_CONSUMER_BAD_RENDER)
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


def test_committed_stub_artifacts_exist() -> None:
    """The committed stub, its package marker, and its protocol module are present.

    A missing file here means `make gencode` was not run (or its output was not committed),
    which would silently disable the pyright coverage below.
    """
    assert _UNPARSER_PYI.is_file(), f"missing committed unparser stub: {_UNPARSER_PYI}"
    assert _STUB_INIT_PYI.is_file(), f"missing stub package marker: {_STUB_INIT_PYI}"
    assert _PROTOCOL_MODULE.is_file(), f"missing CST protocol module: {_PROTOCOL_MODULE}"
    text = _UNPARSER_PYI.read_text()
    assert "import tests.rust_parser_fixture_cst_protocol as _proto" in text
    assert "class Unparser:" in text
    assert "class Doc:" in text


def test_consumer_pyright_clean(consumer_pyright_diagnostics: dict[str, list[dict]]) -> None:
    """A correct consumer of rust_parser_fixture.unparser type-checks against the committed stub."""
    errors = _diags_for_file(consumer_pyright_diagnostics, "consumer_ok.py")
    assert errors == [], f"Unexpected pyright errors consuming the committed unparser stub:\n{errors}"


def test_consumer_misuse_is_type_error(consumer_pyright_diagnostics: dict[str, list[dict]]) -> None:
    """Passing a non-node where a _proto node type is required is a pyright error.

    Proves the committed stub constrains the node parameter (it would not error if node were Any),
    so the OQ-3 typed surface is genuinely useful to downstream consumers.
    """
    errors = _diags_for_file(consumer_pyright_diagnostics, "consumer_bad.py")
    assert any(d.get("rule") == "reportArgumentType" for d in errors), (
        "Expected a reportArgumentType error for passing int where _proto.Num is required; "
        f"got {errors!r}. The committed unparser stub may have degraded to an Any-typed surface."
    )


def test_consumer_return_keeps_optional(consumer_pyright_diagnostics: dict[str, list[dict]]) -> None:
    """unparse_{rule}'s return type retains `| None` (assigning it to bare str is an error).

    The OK consumer assigns into a `str | None` target, which accepts `str | None`, `str`, and
    `Any` alike, so it cannot detect a dropped `| None`.  This bad consumer would silently pass
    if the committed stub narrowed the return to `str` (or `Any`), so the asserted error guards
    the `| None` that downstream callers rely on to mean "could not unparse".
    """
    errors = _diags_for_file(consumer_pyright_diagnostics, "consumer_bad_narrowing.py")
    assert any(d.get("rule") in ("reportAssignmentType", "reportArgumentType") for d in errors), (
        "Expected a type error assigning str | None to str; "
        f"got {errors!r}. The committed stub may have dropped | None from the unparse_num return."
    )


def test_consumer_render_returns_str(consumer_pyright_diagnostics: dict[str, list[dict]]) -> None:
    """Doc.render() is typed `-> str` (assigning it to int is an error), not Any.

    The OK consumer returns `render()`'s result into a `str | None` function, which `Any` also
    satisfies, so it cannot detect a degraded return.  This bad consumer would silently pass if
    render() returned `Any`, so the asserted error proves the return type is a concrete `str`.
    """
    errors = _diags_for_file(consumer_pyright_diagnostics, "consumer_bad_render.py")
    assert any(d.get("rule") == "reportAssignmentType" for d in errors), (
        "Expected a reportAssignmentType error assigning str to int; "
        f"got {errors!r}. The committed stub's Doc.render() may have degraded to Any."
    )
