"""Server-side project layer: ``ProjectHost`` and ``ProjectNavigator``.

``ProjectHost`` is the server's :class:`~fltk.lsp.resolver.ResolverHost`: it analyzes and
caches other files a resolver asks about, reading open-editor buffers over disk, and enumerates
the workspace files matching the resolver's suffixes. ``ProjectNavigator`` is the generic,
lsprotocol-free query layer over ``(ProjectHost, Resolver)`` that turns a cursor position into a
cross-file definition target or the deduplicated set of cross-file reference occurrences.

Both are touched only from the server's single analysis worker (never the protocol loop), so
neither locks. The host consults an immutable snapshot of the open-document map handed to it at
construction plus disk -- never the live pygls workspace, which the loop thread mutates
concurrently.
"""

from __future__ import annotations

import dataclasses
import enum
import logging
import os
import pathlib
from typing import TYPE_CHECKING, NamedTuple

from pygls import uris

from fltk.lsp import features
from fltk.lsp.positions import LineIndex
from fltk.lsp.resolver import CrossFileResolution, ExternalTarget, ResolvedDocument

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence

    from fltk.lsp.engine import AnalysisEngine
    from fltk.lsp.resolver import Resolver
    from fltk.lsp.symbols import Symbol

_LOGGER = logging.getLogger(__name__)


def uri_to_path(uri: str) -> pathlib.Path | None:
    """Filesystem path for a ``file:`` URI, or ``None`` for a non-file (unrepresentable) URI."""
    fs_path = uris.to_fs_path(uri)
    return pathlib.Path(fs_path) if fs_path is not None else None


def canonical_uri(uri: str) -> str:
    """``uri`` normalized to pygls's ``from_fs_path`` spelling.

    Clients serialize ``file:`` URIs differently than pygls does (Windows drive letters,
    percent-encoding), so two URIs naming the same file need not be string-equal. Round-tripping
    through the filesystem path collapses them to one canonical form for identity comparison and
    snapshot lookup. Non-file URIs and paths pygls cannot round-trip are returned unchanged, and an
    already-canonical URI is unchanged (idempotent).
    """
    fs_path = uris.to_fs_path(uri)
    if fs_path is None:
        return uri
    return uris.from_fs_path(fs_path) or uri


# A reference occurrence as the navigator reports it, before the server renders it to a
# ``lsp.Location``: the home URI and the codepoint span.
Occurrence = tuple[str, int, int]

# Cache validity key: ``("open", version)`` for a client-open document, ``("disk", mtime_ns,
# size)`` for a file read from disk. An access whose key differs from the cached one re-analyzes.
_VersionKey = tuple[object, ...]


class _CachedDoc(NamedTuple):
    """One analyzed document plus its cache-validity key and line table."""

    version_key: _VersionKey
    document: ResolvedDocument
    line_index: LineIndex


@dataclasses.dataclass(frozen=True)
class _Unavailable:
    """Why a URI could not be analyzed; the text is what the warning and the refusal show.

    ``logged`` is set when this failure has already been reported to the client log.
    """

    reason: str
    logged: bool = False


class ProjectHost:
    """The server's :class:`~fltk.lsp.resolver.ResolverHost`, over a snapshot + disk.

    ``open_docs`` maps a URI to ``(version, text)`` for every document the client currently has
    open; it is a point-in-time snapshot the server copies on the loop thread and never mutates.
    ``root_path`` is the workspace root captured at ``initialize`` (``None`` if the client
    provided none). Analysis reuses the single ``engine``; only complete analyses are returned. Both
    outcomes are cached under the file's version key, so an unchanged broken file is parsed once
    however many lookups reach it, and a fix (a new version key) re-analyzes.

    A URI that cannot be analyzed (non-``file:``, unstattable, unreadable, partial or failed parse)
    has two lookups: ``document()`` returns ``None`` and is silent about why; ``scan_document()``
    also records the reason in ``scan_omissions()`` and warns. A directory-walk error in
    ``workspace_files()`` is recorded the same way, whoever called it.
    """

    def __init__(
        self,
        engine: AnalysisEngine,
        resolver: Resolver,
        *,
        root_path: pathlib.Path | None,
        open_docs: Mapping[str, tuple[int, str]] | None = None,
    ) -> None:
        self._engine = engine
        self._resolver = resolver
        self._root_path = root_path
        self._open_docs: Mapping[str, tuple[int, str]] = (
            {canonical_uri(uri): value for uri, value in open_docs.items()} if open_docs else {}
        )
        self._cache: dict[str, _CachedDoc] = {}
        self._failed: dict[str, tuple[_VersionKey, _Unavailable]] = {}
        self._warned_unreadable: set[str] = set()
        # Client-surfacable warnings (unreadable workspace files, directory-scan errors) accumulated
        # since the last drain; the server emits them as ``window/logMessage``.
        self._warnings: list[str] = []
        # Files and directories a scan could not analyze, ``name -> reason``.
        self._omissions: dict[str, str] = {}

    def drain_warnings(self) -> list[str]:
        """Return and clear the client-surfacable warnings gathered while serving requests."""
        warnings = self._warnings
        self._warnings = []
        return warnings

    def document(self, uri: str) -> ResolvedDocument | None:
        entry = self._ensure(uri)
        return entry.document if isinstance(entry, _CachedDoc) else None

    def scan_document(self, uri: str) -> ResolvedDocument | None:
        """``document()`` for a URI a scan enumerated: a failure is recorded, not just skipped.

        The reason lands in ``scan_omissions()`` under the canonical URI, and a warning naming the
        URI is queued unless this failure is already in the log.
        """
        entry = self._ensure(uri)
        if isinstance(entry, _CachedDoc):
            return entry.document
        key = canonical_uri(uri)
        if key not in self._omissions:
            self._omissions[key] = entry.reason
            if not entry.logged:
                self._warnings.append(f"fltk-lsp: could not analyze workspace file {uri}: {entry.reason}")
        return None

    def scan_omissions(self) -> Mapping[str, str]:
        """Every file or directory a scan could not analyze, ``name -> reason``."""
        return self._omissions

    def line_index(self, uri: str) -> LineIndex | None:
        """The cached line table for ``uri``, analyzing it if needed; ``None`` when unavailable."""
        entry = self._ensure(uri)
        return entry.line_index if isinstance(entry, _CachedDoc) else None

    def workspace_files(self) -> Sequence[str]:
        if self._root_path is None:
            return ()

        def _on_scan_error(error: OSError) -> None:
            # os.walk otherwise swallows a permission/vanished-directory error, silently dropping a
            # whole subtree; record it so the omission is at least visible in the client's log.
            # The dropped subtree makes the listing incomplete, so it is also a scan omission.
            where = getattr(error, "filename", None) or self._root_path
            self._warnings.append(f"fltk-lsp: could not scan {where}: {error}")
            self._omissions[str(where)] = f"directory scan error: {error}"

        result: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self._root_path, onerror=_on_scan_error):
            dirnames[:] = [d for d in dirnames if _is_project_dir(d)]
            for filename in filenames:
                # Only regular files (or symlinks to one): a dangling symlink -- an editor lock
                # file such as Emacs's ``.#name`` -- or a FIFO is not a project file.
                if self._is_project_file(filename) and os.path.isfile(os.path.join(dirpath, filename)):
                    result.append(self.path_to_uri(pathlib.Path(dirpath) / filename))
        result.sort()
        return tuple(result)

    def open_documents(self) -> Sequence[str]:
        """The open buffers ``workspace_files()`` would list if they were saved, sorted.

        A ``file:`` URI under the root whose directories below the root and whose file name pass
        the same predicates the walk prunes and filters with. Lexical, like the walk (no symlink
        resolution); ``()`` with no root.
        """
        if self._root_path is None:
            return ()
        result: list[str] = []
        for uri in self._open_docs:
            path = uri_to_path(uri)
            if path is None or not path.is_relative_to(self._root_path):
                continue
            below_root = path.relative_to(self._root_path).parent.parts
            if all(_is_project_dir(part) for part in below_root) and self._is_project_file(path.name):
                result.append(uri)
        result.sort()
        return tuple(result)

    def root_path(self) -> pathlib.Path | None:
        return self._root_path

    def _is_project_file(self, name: str) -> bool:
        """Whether a file named ``name`` in a project directory is a project file."""
        return name.endswith(tuple(self._resolver.file_suffixes))

    def uri_to_path(self, uri: str) -> pathlib.Path | None:
        return uri_to_path(uri)

    def path_to_uri(self, path: pathlib.Path) -> str:
        """The ``file:`` URI for ``path``.

        Falls back to ``""`` when pygls cannot represent the path as a ``file:`` URI (a rare,
        odd-platform case); an empty URI addresses nothing, so ``document("")`` returns ``None`` and
        a resolver that copies it into an :class:`ExternalTarget` produces a no-op navigation rather
        than a crash.
        """
        return uris.from_fs_path(str(path)) or ""

    def _ensure(self, uri: str) -> _CachedDoc | _Unavailable:
        """Return the cached analysis for ``uri``, (re)analyzing on a version-key mismatch.

        Open-buffer text wins over disk. Only a complete analysis is returned; a partial/failed
        parse or an unavailable file yields the reason as ``_Unavailable``. A parse failure is
        cached under its version key like a success.
        """
        uri = canonical_uri(uri)
        source = self._source(uri)
        if isinstance(source, _Unavailable):
            return source
        text, version_key = source

        cached = self._cache.get(uri)
        if cached is not None and cached.version_key == version_key:
            return cached
        failed = self._failed.get(uri)
        if failed is not None and failed[0] == version_key:
            return failed[1]

        analysis = self._engine.analyze(text)
        if analysis.error is not None:
            first_line = analysis.error.message.partition("\n")[0]
            return self._fail(uri, version_key, f"parse error: {first_line}" if first_line else "parse error")
        if analysis.tree is None or analysis.symbols is None:
            return self._fail(uri, version_key, "analysis incomplete")

        entry = _CachedDoc(
            version_key=version_key,
            document=ResolvedDocument(uri=uri, text=text, tree=analysis.tree, symbols=analysis.symbols),
            line_index=LineIndex(text),
        )
        self._cache[uri] = entry
        return entry

    def _fail(self, uri: str, version_key: _VersionKey, reason: str) -> _Unavailable:
        """Cache and return a failed analysis of ``uri`` at ``version_key``."""
        failure = _Unavailable(reason)
        self._failed[uri] = (version_key, failure)
        return failure

    def _source(self, uri: str) -> tuple[str, _VersionKey] | _Unavailable:
        """The current ``(text, version_key)`` for ``uri`` -- open buffer or disk -- or why not.

        A disk file whose ``(mtime_ns, size)`` still matches the cache is not re-read; the caller
        short-circuits on the matching key. An unreadable or non-UTF-8 file logs once.
        """
        open_entry = self._open_docs.get(uri)
        if open_entry is not None:
            version, text = open_entry
            return text, ("open", version)

        path = self.uri_to_path(uri)
        if path is None:
            return _Unavailable("not a file: URI")
        try:
            stat = path.stat()
        except OSError as exc:
            return _Unavailable(f"cannot stat: {exc}")
        version_key: _VersionKey = ("disk", stat.st_mtime_ns, stat.st_size)

        cached = self._cache.get(uri)
        if cached is not None and cached.version_key == version_key:
            return cached.document.text, version_key
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            if uri not in self._warned_unreadable:
                self._warned_unreadable.add(uri)
                _LOGGER.warning("fltk-lsp: could not read workspace file %s as UTF-8; skipping", uri)
                self._warnings.append(f"fltk-lsp: could not read workspace file {uri}; skipping ({exc})")
            return _Unavailable(f"could not read as UTF-8: {exc}", logged=True)
        return text, version_key


def _is_project_dir(name: str) -> bool:
    """Whether a directory named ``name`` below the workspace root is part of the project."""
    # TODO(correctness-persistently-broken-project-files-disable-rename-permanently): no way to
    # exclude intentionally-unparseable files (error-test fixtures) from the project boundary.
    return not name.startswith(".")


def _identity(target: ExternalTarget) -> tuple[str, int, int]:
    """A target's identity -- its selection range only; declaration ranges never participate."""
    return (target.uri, target.name_start, target.name_end)


class Hazard(enum.Enum):
    """Why a same-file rename must be refused while a resolver is active.

    - ``NONE``: nothing found; the only value that permits the rename.
    - ``IMPORT_BINDING``: the symbol redirects to a declaration in another file.
    - ``CROSS_FILE``: an occurrence of the symbol lives in another file.
    - ``INCOMPLETE_SCAN``: the scan of the guard's universe dropped at least one file or
      directory; which ones is in ``ProjectHost.scan_omissions()``.

    The server permits only on ``hazard is Hazard.NONE``; every other value, and any exception
    raised while computing the hazard, refuses -- so a new value refuses even before the server
    has a message for it.
    """

    NONE = "none"
    IMPORT_BINDING = "import_binding"
    CROSS_FILE = "cross_file"
    INCOMPLETE_SCAN = "incomplete_scan"


class ProjectNavigator:
    """Cross-file definition/references queries over ``(ProjectHost, Resolver)``.

    A symbol's *canonical target* is its ``symbol_targets`` redirect if the resolver gives one
    (the symbol is an import binding declared elsewhere), else its own local declaration; identity
    is the selection range only. One redirect hop by construction -- ``ExternalTarget`` is
    terminal. Resolutions are recomputed per query (cheap walks); a resolver exception propagates
    out to the server layer, which catches it.
    """

    def __init__(self, host: ProjectHost, resolver: Resolver) -> None:
        self._host = host
        self._resolver = resolver

    def definition(self, doc: ResolvedDocument, offset: int) -> ExternalTarget | None:
        """The canonical target the cursor addresses, or ``None`` when it addresses nothing."""
        return self._target_for(doc, offset, {})

    def references(self, doc: ResolvedDocument, offset: int, *, include_declaration: bool) -> list[Occurrence] | None:
        """Every cross-file occurrence of the symbol the cursor addresses, deduplicated and sorted.

        The definition's own name span is included per ``include_declaration``; import bindings and
        both same-file and cross-file references to the target are always included. ``None`` when
        the cursor addresses nothing resolvable.
        """
        return self._references(doc, offset, include_declaration=include_declaration, resolutions={}, record=False)

    def rename_hazard(self, doc: ResolvedDocument, symbol: Symbol, offset: int) -> Hazard:
        """Whether renaming ``symbol`` (under ``offset``) same-file would break the project.

        ``IMPORT_BINDING`` when the symbol redirects elsewhere (renaming it locally would detach it
        from its import); ``CROSS_FILE`` when any occurrence lives in another file;
        ``INCOMPLETE_SCAN`` when any file in the scan universe (see ``_scan_docs``) could not be
        analyzed or the directory walk failed; else ``NONE``. The scan always runs to completion,
        so ``ProjectHost.scan_omissions()`` lists every omission. The requesting document is
        resolved once and that resolution is reused for the global scan, so the canonical-target
        rule matches the read-side references query exactly.
        """
        resolutions: dict[str, CrossFileResolution] = {}
        if self._resolution(doc, resolutions).symbol_targets.get(symbol) is not None:
            return Hazard.IMPORT_BINDING
        occurrences = self._references(doc, offset, include_declaration=True, resolutions=resolutions, record=True)
        if occurrences is not None and any(occ_uri != doc.uri for occ_uri, _start, _end in occurrences):
            return Hazard.CROSS_FILE
        if self._host.scan_omissions():
            return Hazard.INCOMPLETE_SCAN
        return Hazard.NONE

    def _references(
        self,
        doc: ResolvedDocument,
        offset: int,
        *,
        include_declaration: bool,
        resolutions: dict[str, CrossFileResolution],
        record: bool,
    ) -> list[Occurrence] | None:
        target = self._target_for(doc, offset, resolutions)
        if target is None:
            return None
        target_id = _identity(target)
        declaration = (target.name_start, target.name_end)
        results: set[Occurrence] = set()
        for scanned in self._scan_docs(doc, target, record=record):
            resolution = self._resolution(scanned, resolutions)
            for symbol in scanned.symbols.symbols:
                if self._canonical_identity(scanned, symbol, resolution) != target_id:
                    continue
                is_target = (scanned.uri, symbol.name_start, symbol.name_end) == target_id
                for start, end in scanned.symbols.occurrences(symbol):
                    if is_target and (start, end) == declaration and not include_declaration:
                        continue
                    results.add((scanned.uri, start, end))
            for ref in scanned.symbols.references:
                if ref.symbol is None:
                    redirect = resolution.ref_targets.get(ref)
                    if redirect is not None and _identity(redirect) == target_id:
                        results.add((scanned.uri, ref.start, ref.end))
        return sorted(results)

    def _scan_docs(self, doc: ResolvedDocument, target: ExternalTarget, *, record: bool) -> Iterator[ResolvedDocument]:
        """Every analyzable document in the scan universe, once each.

        The universe is the target's home URI, the requesting URI, ``workspace_files()``, and the
        open buffers the walk would list if saved (``open_documents()``). The requesting document is
        served from the passed-in ``doc`` (the server's current-or-last-good snapshot), never re-read
        from the host, so the read-only stale-serving policy holds for it while other documents come
        from the host cache. With ``record`` an unanalyzable URI is recorded as a scan omission
        (``scan_document``); without it, it is skipped silently (``document``).
        """
        lookup = self._host.scan_document if record else self._host.document
        seen: set[str] = set()
        for uri in (target.uri, doc.uri, *self._host.workspace_files(), *self._host.open_documents()):
            if uri in seen:
                continue
            seen.add(uri)
            if uri == doc.uri:
                yield doc
            else:
                scanned = lookup(uri)
                if scanned is not None:
                    yield scanned

    def _target_for(
        self, doc: ResolvedDocument, offset: int, resolutions: dict[str, CrossFileResolution]
    ) -> ExternalTarget | None:
        symbol = features.symbol_target(doc.symbols, offset)
        if symbol is not None:
            return self._canonical(doc, symbol, resolutions)
        ref = doc.symbols.reference_at(offset)
        if ref is not None and ref.symbol is None:
            return self._resolution(doc, resolutions).ref_targets.get(ref)
        return None

    def _canonical(
        self, doc: ResolvedDocument, symbol: Symbol, resolutions: dict[str, CrossFileResolution]
    ) -> ExternalTarget:
        redirect = self._resolution(doc, resolutions).symbol_targets.get(symbol)
        if redirect is not None:
            return redirect
        return ExternalTarget(
            uri=doc.uri,
            name_start=symbol.name_start,
            name_end=symbol.name_end,
            range_start=symbol.range_start,
            range_end=symbol.range_end,
        )

    def _canonical_identity(
        self, doc: ResolvedDocument, symbol: Symbol, resolution: CrossFileResolution
    ) -> tuple[str, int, int]:
        redirect = resolution.symbol_targets.get(symbol)
        if redirect is not None:
            return _identity(redirect)
        return (doc.uri, symbol.name_start, symbol.name_end)

    def _resolution(self, doc: ResolvedDocument, resolutions: dict[str, CrossFileResolution]) -> CrossFileResolution:
        cached = resolutions.get(doc.uri)
        if cached is None:
            cached = self._resolver.resolve(doc, self._host)
            resolutions[doc.uri] = cached
        return cached
