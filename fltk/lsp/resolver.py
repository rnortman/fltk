"""The resolver plugin contract and its loader (**provisional public API**).

A *resolver* is a small Python object a downstream language ships to turn same-file symbol
analysis into cross-file go-to-definition and find-references. The server loads one via the
``fltk-lsp --resolver SPEC`` flag and, for each analyzed document, asks it a single question:
given this document's :class:`~fltk.lsp.symbols.SymbolTable` (its exported symbols and its
same-file-unresolvable references) plus the ability to obtain other analyzed documents, where
do things *really* live?

The contract's foundation is the per-document seam :func:`fltk.lsp.symbols.extract` already
produces: a ``Reference`` whose ``symbol is None`` is exactly a same-file-unresolvable
reference, and each ``Symbol`` is part of the file's definable surface. A resolver maps those
to :class:`ExternalTarget` locations in other files.

Provisional: this protocol has exactly one in-repo implementation (the ``gear`` demo) until a
real downstream language validates it. It is **subject to change until validated against a
real downstream language** -- do not treat it as frozen public API yet.

Resolver-author guidance:

- ``resolve`` is called once per document (batch, not per-reference): walk the document's
  import constructs once and answer everything.
- Copy all four offsets of an :class:`ExternalTarget` verbatim from the target document's
  ``SymbolTable`` entry. Only ``(uri, name_start, name_end)`` participates in identity
  matching, but a divergent declaration range still degrades the peek window.
- Chase re-export chains yourself via ``host.document``; the server never recurses. Bound
  your own recursion -- import cycles are the normal state of a live-edited project.
- Missing/unparsable import targets should yield no entry (silent degradation), matching the
  same-file unresolved-reference policy.
- Import-path segments come from untrusted document text. Validate them before touching the
  filesystem -- reject path separators, ``..``, and absolute parts (or confirm the resolved
  target stays under ``host.root_path()``) so a hostile file cannot traverse out of the
  workspace and disclose arbitrary readable files through go-to-definition.
"""

from __future__ import annotations

import dataclasses
import importlib
import importlib.util
import pathlib
import sys
import typing
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

if typing.TYPE_CHECKING:
    from fltk.lsp import symbols


class ResolverError(ValueError):
    """A ``--resolver`` spec that cannot be loaded into a valid resolver.

    Subclasses ``ValueError`` so the CLI's existing fail-fast handler maps it to a stderr
    message and exit 1 alongside grammar/spec content errors.
    """


@dataclasses.dataclass(frozen=True)
class ResolvedDocument:
    """One analyzed document as the resolver sees it.

    ``tree`` is the analysis-grammar CST root; ``symbols`` is its extracted table. All four
    are one consistent version of the document -- never a live buffer paired with a stale tree.
    """

    uri: str
    text: str
    tree: Any
    symbols: symbols.SymbolTable


@dataclasses.dataclass(frozen=True)
class ExternalTarget:
    """A definition site in another (or the same) file, in codepoint offsets.

    ``name_start``/``name_end`` are the selection range (the identifying name span);
    ``range_start``/``range_end`` are the declaration range (the peek window). Identity, wherever
    the server compares targets, is ``(uri, name_start, name_end)`` only.
    """

    uri: str
    name_start: int
    name_end: int
    range_start: int
    range_end: int


@dataclasses.dataclass(frozen=True)
class CrossFileResolution:
    """The resolver's answers for one document.

    ``ref_targets`` gives cross-file targets for references left unresolved same-file (keyed by
    the exact ``Reference`` objects from ``doc.symbols``). ``symbol_targets`` gives redirects
    for symbols that are import bindings -- 'this local symbol is really declared over there' --
    keyed by the exact ``Symbol`` objects; it drives definition-chaining and the global
    find-references match. Both default empty; keys not drawn from ``doc.symbols`` simply never
    match.
    """

    ref_targets: Mapping[symbols.Reference, ExternalTarget] = dataclasses.field(default_factory=dict)
    symbol_targets: Mapping[symbols.Symbol, ExternalTarget] = dataclasses.field(default_factory=dict)


class ResolverHost(Protocol):
    """Server-provided services a resolver may call. All methods are cheap-or-cached."""

    def document(self, uri: str) -> ResolvedDocument | None:
        """Analyze and cache the document at ``uri`` (open-buffer text if the client has it
        open, else disk), returning ``None`` if unreadable, nonexistent, or only partially
        parseable -- resolvers only ever see complete analyses."""
        ...

    def workspace_files(self) -> Sequence[str]:
        """URIs of workspace files matching the resolver's ``file_suffixes``; empty when the
        client provided no workspace root."""
        ...

    def root_path(self) -> pathlib.Path | None:
        """The workspace root as a filesystem path, or ``None`` when the client provided none."""
        ...

    def uri_to_path(self, uri: str) -> pathlib.Path | None:
        """Filesystem path for a ``file:`` URI, or ``None`` for a non-file URI."""
        ...

    def path_to_uri(self, path: pathlib.Path) -> str:
        """The ``file:`` URI for a filesystem path."""
        ...


@runtime_checkable
class Resolver(Protocol):
    """A downstream language's cross-file resolver.

    ``file_suffixes`` (e.g. ``(".gear",)``) drives the workspace scan; every entry must be a
    non-empty, ``.``-prefixed extension. ``resolve`` is called once per analyzed document.
    """

    file_suffixes: Sequence[str]

    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution:
        """Cross-file resolutions for ``doc``, using ``host`` to reach other documents."""
        ...


_DEFAULT_ATTR = "create_resolver"


def load_resolver(spec: str) -> Resolver:
    """Load and validate a resolver from ``SPEC``.

    ``SPEC`` is ``module.path:attr`` or ``path/to/file.py:attr``; the ``:attr`` is optional and
    defaults to ``create_resolver``. A head is treated as a filesystem path when it names an
    existing file, ends in ``.py``, or contains a path separator; otherwise it is an importable
    module. ``attr`` names either a ``Resolver`` instance or a zero-argument factory returning
    one -- an object without a ``resolve`` attribute that is callable is invoked.

    Raises :class:`ResolverError` (a ``ValueError``) with an actionable message on any failure:
    a bad import, a missing/wrong-typed ``attr``, a missing ``resolve`` method, or empty or
    non-``.``-prefixed ``file_suffixes``.
    """
    head, attr = _split_spec(spec)
    module = _import_head(head)

    try:
        obj = getattr(module, attr)
    except AttributeError:
        msg = f"resolver spec '{spec}': module '{head}' has no attribute '{attr}'"
        raise ResolverError(msg) from None

    resolver = _instantiate(obj, spec)
    _validate(resolver, spec)
    return typing.cast("Resolver", resolver)


def _split_spec(spec: str) -> tuple[str, str]:
    """Split ``SPEC`` into ``(head, attr)``, defaulting ``attr`` to ``create_resolver``.

    The attribute separator is the last ``:``, but only when what follows is a bare Python
    identifier -- so a Windows drive letter or a ``:`` inside a path never gets mistaken for an
    attribute separator.
    """
    if not spec:
        msg = "resolver spec is empty; expected 'module.path:attr' or 'path/to/file.py:attr'"
        raise ResolverError(msg)
    head, sep, tail = spec.rpartition(":")
    if sep and tail.isidentifier():
        return head, tail
    return spec, _DEFAULT_ATTR


def _looks_like_path(head: str) -> bool:
    """Whether ``head`` should be loaded as a file rather than imported as a module.

    TODO(resolver-spec-file-recognition): the bare ``is_file()`` check makes recognition depend on
    the server's cwd -- a bare module spec (``mylang.resolvers``) is exec'd as a file when a
    same-named file exists in cwd (e.g. a hostile workspace the editor spawned the server inside),
    rather than imported. Narrowing recognition to the unambiguous signals (``.py``/separator) would
    close this, but that contradicts the frozen design's "a path is recognized by an existing file"
    rule, so it needs a design delta.
    """
    return pathlib.Path(head).is_file() or head.endswith(".py") or "/" in head or "\\" in head


def _import_head(head: str) -> Any:
    if not head:
        msg = "resolver spec has an empty module/file part"
        raise ResolverError(msg)
    if _looks_like_path(head):
        return _import_file(head)
    try:
        return importlib.import_module(head)
    except ImportError as exc:
        msg = f"resolver spec: cannot import module '{head}': {exc}"
        raise ResolverError(msg) from exc


def _import_file(head: str) -> Any:
    path = pathlib.Path(head)
    if not path.is_file():
        msg = f"resolver spec: file '{head}' does not exist"
        raise ResolverError(msg)
    module_name = f"_fltk_resolver_{path.resolve().stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        msg = f"resolver spec: cannot load file '{head}' as a Python module"
        raise ResolverError(msg)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the module's own relative imports and dataclass machinery resolve.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        msg = f"resolver spec: error importing file '{head}': {exc}"
        raise ResolverError(msg) from exc
    return module


def _instantiate(obj: object, spec: str) -> object:
    """A resolver instance from ``obj``: an already-built instance is used directly; a class or a
    zero-argument factory is invoked.

    A ``Resolver`` *class* has a ``resolve`` attribute too (the unbound function), so the
    already-an-instance shortcut must exclude classes -- otherwise ``--resolver mod:GearResolver``
    (naming the class instead of the ``create_resolver`` factory) would pass validation and then
    ``TypeError`` on every call, the half-working server startup is meant to rule out."""
    if not isinstance(obj, type) and hasattr(obj, "resolve"):
        return obj
    if callable(obj):
        try:
            return obj()
        except Exception as exc:
            msg = f"resolver spec '{spec}': factory call failed: {exc}"
            raise ResolverError(msg) from exc
    msg = f"resolver spec '{spec}': attribute is neither a resolver (no 'resolve' method) nor callable"
    raise ResolverError(msg)


def _validate(resolver: object, spec: str) -> None:
    resolve = getattr(resolver, "resolve", None)
    if not callable(resolve):
        msg = f"resolver spec '{spec}': resolver has no callable 'resolve' method"
        raise ResolverError(msg)
    suffixes = getattr(resolver, "file_suffixes", None)
    if suffixes is None or isinstance(suffixes, str | bytes) or not isinstance(suffixes, Sequence):
        msg = f"resolver spec '{spec}': file_suffixes must be a sequence of extensions (e.g. ('.gear',))"
        raise ResolverError(msg)
    suffix_list = list(suffixes)
    if not suffix_list:
        msg = f"resolver spec '{spec}': file_suffixes is empty; at least one extension is required"
        raise ResolverError(msg)
    for suffix in suffix_list:
        if not isinstance(suffix, str) or not suffix.startswith("."):
            msg = f"resolver spec '{spec}': every file_suffix must be a '.'-prefixed string; got {suffix!r}"
            raise ResolverError(msg)
