"""One consumer source, either CST backend — proved at runtime and under pyright.

The user-facing claim of the protocol-typed forward direction is that a downstream application can
switch CST backends without rewriting its own code.  Two shapes of that claim are checked here over
the fegen family, which is the only grammar with a committed concrete CST module, a committed
protocol module and committed Rust stubs:

* **protocol-typed consumer** — one module annotated purely against
  ``fltk.fegen.fltk_cst_protocol``, fed by a thin per-backend caller.  It descends the tree with
  the CST accessors, so it covers the reads a consumer makes below the parse boundary.
* **switchable-import consumer** — two copies of one source whose *only* difference is the backend
  import line, with parameters annotated ``cst.<Class>``.  It converts at the boundary and descends
  in AST space, which is how a consumer of the AST layer is meant to be written.

The static half runs pyright over both shapes plus a freshly generated fegen AST module; the
runtime half executes the switchable source against a real parse from each backend and compares the
results.  A negative fixture keeps the static half from passing vacuously.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import typing

import pytest

from fltk.fegen import fltk_parser
from tests.fegen_ast_fixture import AST_MODULE_NAME, FEGEN_FLTKG, write_fegen_ast_module
from tests.parser_parity import parse_py_cst, parse_rust_cst
from tests.pyright_test_utils import (
    _diags_for_file,
    _run_pyright_over_dir,
    write_pyright_config,
)

if typing.TYPE_CHECKING:
    import types
    from collections.abc import Iterator

_REPO_ROOT = pathlib.Path(__file__).parent.parent

_PY_BACKEND_IMPORT = "import fltk.fegen.fltk_cst as cst"
_RS_BACKEND_IMPORT = "import fegen_rust_cst.cst as cst"

_BACKEND_MARKER = "@BACKEND_IMPORT@"


# ---------------------------------------------------------------------------
# Fixture sources
# ---------------------------------------------------------------------------

_SUMMARY_FORMAT = '''\
# ruff: noqa
"""The summary format both consumer shapes below emit.

The two consumers exist to contrast *descent* — CST accessors against AST fields — and a test
asserts their output is identical.  Keeping the formatting here means a format change is one
edit rather than two that have to stay in lockstep.
"""

from __future__ import annotations

import generated_fegen_ast as fegen_ast


def term_text(value: fegen_ast.Term) -> str:
    """A term, dispatched over the AST sum."""
    if isinstance(value, fegen_ast.Identifier):
        return "ref:" + value.text
    if isinstance(value, fegen_ast.Literal):
        return "lit:" + value.text
    if isinstance(value, fegen_ast.TermRegex):
        return "re:" + value.regex.text
    return "alt:" + str(len(value.alternatives.items))


def item_text(value: fegen_ast.Item, term: str) -> str:
    """One item: its optional label, its already-summarised term, its optional quantifier."""
    label = "" if value.label is None else value.label.text + ":"
    quantifier = "" if value.quantifier is None else value.quantifier.value.name
    return label + term + quantifier


def rule_text(value: fegen_ast.Rule, parts: list[str]) -> str:
    """One rule: its name, its span, and its already-summarised items."""
    return value.name.text + "@" + str(value.span.start) + "-" + str(value.span.end) + "=" + "|".join(parts)
'''

_CONSUMER_SHARED = '''\
# ruff: noqa
"""A grammar summariser that names no CST backend at all.

It descends the tree with the CST accessors, so it covers the reads a consumer makes below the
parse boundary; the formatting it shares with the switchable consumer lives in summary_format.
"""

from __future__ import annotations

import fltk.fegen.fltk_cst_protocol as cstp

import generated_fegen_ast as fegen_ast
import summary_format


def term_summary(term: cstp.Term) -> str:
    return summary_format.term_text(fegen_ast.term_from_cst(term))


def item_summary(item: cstp.Item) -> str:
    return summary_format.item_text(fegen_ast.Item.from_cst(item), term_summary(item.term()))


def rule_summary(rule: cstp.Rule) -> str:
    parts = [item_summary(item) for items in rule.alternatives().items() for item in items.item()]
    return summary_format.rule_text(fegen_ast.Rule.from_cst(rule), parts)


def grammar_summary(grammar: cstp.Grammar) -> list[str]:
    """The whole grammar, summarised."""
    return [rule_summary(rule) for rule in grammar.rule()]
'''

_CONSUMER_BACKEND = '''\
# ruff: noqa
"""Hand this backend's nodes to the protocol-typed consumer."""

from __future__ import annotations

@BACKEND_IMPORT@

import consumer_shared


def summarise(grammar: cst.Grammar) -> list[str]:
    return consumer_shared.grammar_summary(grammar)


def summarise_rule(rule: cst.Rule) -> str:
    return consumer_shared.rule_summary(rule)


def summarise_term(term: cst.Term) -> str:
    return consumer_shared.term_summary(term)
'''

_SWITCHABLE_TEMPLATE = '''\
# ruff: noqa
"""A grammar summariser typed against whichever backend the next line imports.

It converts at the parse boundary and descends in AST space; the formatting it shares with the
protocol-typed consumer lives in summary_format.
"""

from __future__ import annotations

@BACKEND_IMPORT@

import generated_fegen_ast as fegen_ast
import summary_format


def describe_item(value: fegen_ast.Item) -> str:
    return summary_format.item_text(value, summary_format.term_text(value.term))


def describe_rule(value: fegen_ast.Rule) -> str:
    parts = [describe_item(item) for items in value.alternatives.items for item in items.item]
    return summary_format.rule_text(value, parts)


def term_summary(term: cst.Term) -> str:
    return summary_format.term_text(fegen_ast.term_from_cst(term))


def rule_summary(rule: cst.Rule) -> str:
    return describe_rule(fegen_ast.Rule.from_cst(rule))


def grammar_summary(grammar: cst.Grammar) -> list[str]:
    return [describe_rule(rule) for rule in fegen_ast.Grammar.from_cst(grammar).rule]
'''

_CONSUMER_BAD = """\
# ruff: noqa
from __future__ import annotations

import fltk.fegen.fltk_cst as py_cst
import fegen_rust_cst.cst as rust_cst

import generated_fegen_ast as fegen_ast


fegen_ast.Rule.from_cst(py_cst.Grammar())
fegen_ast.rule_from_cst(rust_cst.Grammar())
"""


def _with_backend(template: str, backend_import: str) -> str:
    return template.replace(_BACKEND_MARKER, backend_import)


_PROTOCOL_TYPED_FIXTURES = ("consumer_shared.py", "consumer_py.py", "consumer_rs.py")
_SWITCHABLE_FIXTURES = ("switchable_py.py", "switchable_rs.py")
_NEGATIVE_FIXTURE = "consumer_bad.py"
_STATIC_FIXTURES = (*_PROTOCOL_TYPED_FIXTURES, *_SWITCHABLE_FIXTURES, _NEGATIVE_FIXTURE)


def _write_fixture_dir(target: pathlib.Path, *, include_static_only: bool) -> None:
    """Write the generated AST module and the consumer fixtures into ``target``.

    ``include_static_only`` adds the fixtures that exist for pyright alone — the two per-backend
    callers and the negative — which import the Rust stub package and so are not importable at
    runtime without the built extension.  The protocol-typed consumer names no backend, so it is
    written either way and the runtime half executes it too.
    """
    write_fegen_ast_module(target)
    (target / "summary_format.py").write_text(_SUMMARY_FORMAT)
    (target / "switchable_py.py").write_text(_with_backend(_SWITCHABLE_TEMPLATE, _PY_BACKEND_IMPORT))
    (target / "switchable_rs.py").write_text(_with_backend(_SWITCHABLE_TEMPLATE, _RS_BACKEND_IMPORT))
    (target / "consumer_shared.py").write_text(_CONSUMER_SHARED)
    if include_static_only:
        (target / "consumer_py.py").write_text(_with_backend(_CONSUMER_BACKEND, _PY_BACKEND_IMPORT))
        (target / "consumer_rs.py").write_text(_with_backend(_CONSUMER_BACKEND, _RS_BACKEND_IMPORT))
        (target / "consumer_bad.py").write_text(_CONSUMER_BAD)


# ---------------------------------------------------------------------------
# Static half
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def consumer_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, typing.Any]]]:
    """Both consumer shapes plus the AST module, checked in one pyright invocation.

    Needs no built extension: pyright reads ``fltk/_stubs/fegen_rust_cst/cst.pyi`` for the Rust
    backend, which is exactly what a downstream consumer's own pyright run does.
    """
    tmpdir = tmp_path_factory.mktemp("ast_switchable_consumer")
    write_pyright_config(tmpdir, extra_paths=[str(_REPO_ROOT), str(_REPO_ROOT / "fltk" / "_stubs"), str(tmpdir)])
    _write_fixture_dir(tmpdir, include_static_only=True)
    # A fixture the tests below name but nobody wrote would yield no diagnostics, so every
    # zero-error assertion would pass on a file that does not exist.
    missing = [name for name in _STATIC_FIXTURES if not (tmpdir / name).is_file()]
    assert not missing, f"fixture files the tests name were never written: {missing}"
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


@pytest.mark.parametrize("fixture", _PROTOCOL_TYPED_FIXTURES)
def test_a_protocol_typed_consumer_takes_either_backend(
    consumer_diagnostics: dict[str, list[dict[str, typing.Any]]],
    fixture: str,
) -> None:
    errors = _diags_for_file(consumer_diagnostics, fixture)
    assert errors == [], f"{fixture} does not type-check:\n{errors}"


@pytest.mark.parametrize("fixture", _SWITCHABLE_FIXTURES)
def test_the_switchable_import_consumer_type_checks_on_both_backends(
    consumer_diagnostics: dict[str, list[dict[str, typing.Any]]],
    fixture: str,
) -> None:
    errors = _diags_for_file(consumer_diagnostics, fixture)
    assert errors == [], f"{fixture} does not type-check:\n{errors}"


def test_the_two_switchable_copies_differ_only_in_the_backend_import() -> None:
    """The claim the two fixtures above make is only worth anything if the sources really match."""
    python_lines = _with_backend(_SWITCHABLE_TEMPLATE, _PY_BACKEND_IMPORT).splitlines()
    rust_lines = _with_backend(_SWITCHABLE_TEMPLATE, _RS_BACKEND_IMPORT).splitlines()
    assert len(python_lines) == len(rust_lines)
    differing = [(left, right) for left, right in zip(python_lines, rust_lines, strict=True) if left != right]
    assert differing == [(_PY_BACKEND_IMPORT, _RS_BACKEND_IMPORT)]


def test_a_wrong_class_node_is_still_refused_at_the_from_cst_boundary(
    consumer_diagnostics: dict[str, list[dict[str, typing.Any]]],
) -> None:
    """Every other fixture here asserts zero errors, so the forward signatures need a negative.

    A ``from_cst`` widened into vacuity — ``node: object``, or a protocol whose classes stopped
    discriminating — would leave the positives green while downstream code lost the check.
    """
    errors = _diags_for_file(consumer_diagnostics, _NEGATIVE_FIXTURE)
    assert len(errors) == 2, errors
    assert {error["rule"] for error in errors} == {"reportArgumentType"}, errors
    assert all('of type "Rule"' in error["message"] for error in errors), errors


# ---------------------------------------------------------------------------
# Runtime half
# ---------------------------------------------------------------------------

_GRAMMAR_TEXT = """\
word := value:/[a-z]+/ ;
atom := name:word | lit:"x" ;
items := item:atom+ , tail:atom? ;
group := inner:(a:word , b:word) ;
kw := %"hello" ;
"""

_rust_available = importlib.util.find_spec("fegen_rust_cst") is not None
_needs_rust = pytest.mark.skipif(
    not _rust_available,
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)


@pytest.fixture(scope="module")
def switchable_modules(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, types.ModuleType]]:
    """Import the rendered switchable sources, so the runtime half runs the very same text.

    The Rust copy names the extension in a real import line, so it can only be imported where the
    extension is built; the Python copy always is, so a lane without the extension still executes
    half of the comparison.  Every test that reaches into the Rust copy carries ``_needs_rust``, so
    such a lane reports skips rather than a quietly smaller test set.
    """
    tmpdir = tmp_path_factory.mktemp("ast_switchable_runtime")
    _write_fixture_dir(tmpdir, include_static_only=False)
    sys.path.insert(0, str(tmpdir))
    names = ["consumer_shared", "switchable_py", *(["switchable_rs"] if _rust_available else [])]
    try:
        yield {name: importlib.import_module(name) for name in names}
    finally:
        sys.path.remove(str(tmpdir))
        for name in [*names, "summary_format", AST_MODULE_NAME]:
            sys.modules.pop(name, None)


def _python_cst(text: str, rule: str) -> typing.Any:
    return parse_py_cst(fltk_parser, rule, text)


def _rust_cst(text: str, rule: str) -> typing.Any:
    import fegen_rust_cst.parser  # noqa: PLC0415

    return parse_rust_cst(fegen_rust_cst.parser, rule, text)


def test_the_switchable_consumer_summarises_a_python_backed_tree(
    switchable_modules: dict[str, types.ModuleType],
) -> None:
    """Sanity floor: the source runs, and it reports what the grammar actually says."""
    summary = switchable_modules["switchable_py"].grammar_summary(_python_cst(_GRAMMAR_TEXT, "grammar"))
    assert summary[0].startswith("word@0-")
    assert summary[1].endswith('=name:ref:word|lit:lit:"x"')
    assert summary[2].endswith("=item:ref:atomONE_OR_MORE|tail:ref:atomOPTIONAL")
    assert summary[3].endswith("=inner:alt:1")
    assert summary[4].endswith('=lit:"hello"')


@_needs_rust
def test_both_backends_summarise_a_tree_identically(
    switchable_modules: dict[str, types.ModuleType],
) -> None:
    from_python = switchable_modules["switchable_py"].grammar_summary(_python_cst(_GRAMMAR_TEXT, "grammar"))
    from_rust = switchable_modules["switchable_rs"].grammar_summary(_rust_cst(_GRAMMAR_TEXT, "grammar"))
    assert from_python == from_rust


@_needs_rust
@pytest.mark.parametrize(
    ("rule", "text"),
    [("rule", 'atom := name:word | lit:"x" ;'), ("term", "word"), ("term", '"x"'), ("term", "/[a-z]+/")],
)
def test_the_other_cst_typed_entry_points_agree_across_backends(
    switchable_modules: dict[str, types.ModuleType],
    rule: str,
    text: str,
) -> None:
    entry = f"{rule}_summary"
    from_python = getattr(switchable_modules["switchable_py"], entry)(_python_cst(text, rule))
    from_rust = getattr(switchable_modules["switchable_rs"], entry)(_rust_cst(text, rule))
    assert from_python == from_rust


@_needs_rust
def test_either_copy_of_the_source_accepts_either_backends_tree(
    switchable_modules: dict[str, types.ModuleType],
) -> None:
    """The annotations pick a backend; the code does not.

    Both copies compile to the same bytecode — ``cst`` is only ever named in annotations, which
    ``from __future__ import annotations`` never evaluates — so each copy converts either tree.
    That is the runtime shape of the static claim above.
    """
    python_tree = _python_cst(_GRAMMAR_TEXT, "grammar")
    rust_tree = _rust_cst(_GRAMMAR_TEXT, "grammar")
    py_module = switchable_modules["switchable_py"]
    rs_module = switchable_modules["switchable_rs"]
    assert py_module.grammar_summary(rust_tree) == rs_module.grammar_summary(python_tree)


@pytest.mark.parametrize("backend", ["python", pytest.param("rust", marks=_needs_rust)])
def test_the_protocol_typed_consumer_descends_either_backends_tree(
    switchable_modules: dict[str, types.ModuleType],
    backend: str,
) -> None:
    """Exercises the CST accessor surface directly, not through the AST layer."""
    tree = _python_cst(_GRAMMAR_TEXT, "grammar") if backend == "python" else _rust_cst(_GRAMMAR_TEXT, "grammar")
    expected = switchable_modules["switchable_py"].grammar_summary(_python_cst(_GRAMMAR_TEXT, "grammar"))
    assert switchable_modules["consumer_shared"].grammar_summary(tree) == expected


@_needs_rust
def test_the_consumer_reads_the_fegen_grammar_itself_through_both_backends(
    switchable_modules: dict[str, types.ModuleType],
) -> None:
    """A real, large input rather than a fixture snippet: fegen's own grammar file."""
    text = FEGEN_FLTKG.read_text()
    from_python = switchable_modules["switchable_py"].grammar_summary(_python_cst(text, "grammar"))
    from_rust = switchable_modules["switchable_rs"].grammar_summary(_rust_cst(text, "grammar"))
    assert from_python == from_rust
    assert len(from_python) > 10
