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


class ProjectHost:
    """The server's :class:`~fltk.lsp.resolver.ResolverHost`, over a snapshot + disk.

    ``open_docs`` maps a URI to ``(version, text)`` for every document the client currently has
    open; it is a point-in-time snapshot the server copies on the loop thread and never mutates.
    ``root_path`` is the workspace root captured at ``initialize`` (``None`` if the client
    provided none). Analysis reuses the single ``engine``; only complete analyses are cached and
    returned -- a partial or failed parse yields ``None`` and is not cached, so a later fix
    re-analyzes.
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
        self._warned_unreadable: set[str] = set()
        # Client-surfacable warnings (unreadable workspace files, directory-scan errors) accumulated
        # since the last drain; the server emits them as ``window/logMessage``.
        self._warnings: list[str] = []

    def drain_warnings(self) -> list[str]:
        """Return and clear the client-surfacable warnings gathered while serving requests."""
        warnings = self._warnings
        self._warnings = []
        return warnings

    def document(self, uri: str) -> ResolvedDocument | None:
        entry = self._ensure(uri)
        return entry.document if entry is not None else None

    def line_index(self, uri: str) -> LineIndex | None:
        """The cached line table for ``uri``, analyzing it if needed; ``None`` when unavailable."""
        entry = self._ensure(uri)
        return entry.line_index if entry is not None else None

    def workspace_files(self) -> Sequence[str]:
        if self._root_path is None:
            return ()
        suffixes = tuple(self._resolver.file_suffixes)

        def _on_scan_error(error: OSError) -> None:
            # os.walk otherwise swallows a permission/vanished-directory error, silently dropping a
            # whole subtree; record it so the omission is at least visible in the client's log.
            where = getattr(error, "filename", None) or self._root_path
            self._warnings.append(f"fltk-lsp: could not scan {where}: {error}")

        result: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self._root_path, onerror=_on_scan_error):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for filename in filenames:
                if filename.endswith(suffixes):
                    result.append(self.path_to_uri(pathlib.Path(dirpath) / filename))
        result.sort()
        return tuple(result)

    def root_path(self) -> pathlib.Path | None:
        return self._root_path

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

    def _ensure(self, uri: str) -> _CachedDoc | None:
        """Return the cached analysis for ``uri``, (re)analyzing on a version-key mismatch.

        Open-buffer text wins over disk. Only a complete analysis is cached and returned; a
        partial/failed parse or an unreadable file yields ``None``.
        """
        uri = canonical_uri(uri)
        source = self._source(uri)
        if source is None:
            return None
        text, version_key = source

        cached = self._cache.get(uri)
        if cached is not None and cached.version_key == version_key:
            return cached

        analysis = self._engine.analyze(text)
        if analysis.error is not None or analysis.tree is None or analysis.symbols is None:
            return None

        entry = _CachedDoc(
            version_key=version_key,
            document=ResolvedDocument(uri=uri, text=text, tree=analysis.tree, symbols=analysis.symbols),
            line_index=LineIndex(text),
        )
        self._cache[uri] = entry
        return entry

    def _source(self, uri: str) -> tuple[str, _VersionKey] | None:
        """The current ``(text, version_key)`` for ``uri`` -- open buffer or disk -- or ``None``.

        A disk file whose ``(mtime_ns, size)`` still matches the cache is not re-read; the caller
        short-circuits on the matching key. An unreadable or non-UTF-8 file logs once and yields
        ``None``.
        """
        open_entry = self._open_docs.get(uri)
        if open_entry is not None:
            version, text = open_entry
            return text, ("open", version)

        path = self.uri_to_path(uri)
        if path is None:
            return None
        try:
            stat = path.stat()
        except OSError:
            return None
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
            return None
        return text, version_key


def _identity(target: ExternalTarget) -> tuple[str, int, int]:
    """A target's identity -- its selection range only; declaration ranges never participate."""
    return (target.uri, target.name_start, target.name_end)


class Hazard(enum.Enum):
    """Why a same-file rename must be refused while a resolver is active.

    ``NONE`` is the only value that permits the rename; every other value (and, in the server
    layer, any exception raised while computing the hazard) refuses it -- fail-closed by
    construction, so a new value can never accidentally take the permit path.
    """

    NONE = "none"
    IMPORT_BINDING = "import_binding"
    CROSS_FILE = "cross_file"


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
        return self._references(doc, offset, include_declaration=include_declaration, resolutions={})

    def rename_hazard(self, doc: ResolvedDocument, symbol: Symbol, offset: int) -> Hazard:
        """Whether renaming ``symbol`` (under ``offset``) same-file would break the project.

        ``IMPORT_BINDING`` when the symbol redirects elsewhere (renaming it locally would detach it
        from its import); ``CROSS_FILE`` when any occurrence lives in another file; else ``NONE``.
        The requesting document is resolved once and that resolution is reused for the global scan,
        so the canonical-target rule matches the read-side references query exactly.
        """
        resolutions: dict[str, CrossFileResolution] = {}
        if self._resolution(doc, resolutions).symbol_targets.get(symbol) is not None:
            return Hazard.IMPORT_BINDING
        # TODO(rename-guard-incomplete-scan): an incomplete workspace scan -- a directory-walk error,
        # or a neighbor that is unreadable or unparseable and so dropped from the reference scan --
        # lets this return NONE (permit) even though an undetected cross-file reference may live in
        # the skipped file. The scan surfaces the omission only as an advisory warning; whether the
        # guard should instead refuse on any imperfect scan is an unresolved policy question (refusing
        # on every transiently unparseable neighbor would gut rename during live editing).
        occurrences = self._references(doc, offset, include_declaration=True, resolutions=resolutions)
        if occurrences is not None:
            for occ_uri, _start, _end in occurrences:
                if occ_uri != doc.uri:
                    return Hazard.CROSS_FILE
        return Hazard.NONE

    def _references(
        self,
        doc: ResolvedDocument,
        offset: int,
        *,
        include_declaration: bool,
        resolutions: dict[str, CrossFileResolution],
    ) -> list[Occurrence] | None:
        target = self._target_for(doc, offset, resolutions)
        if target is None:
            return None
        target_id = _identity(target)
        declaration = (target.name_start, target.name_end)
        results: set[Occurrence] = set()
        for scanned in self._scan_docs(doc, target):
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

    def _scan_docs(self, doc: ResolvedDocument, target: ExternalTarget) -> Iterator[ResolvedDocument]:
        """The target's home document, the requesting document, and every workspace file, once each.

        The requesting document is served from the passed-in ``doc`` (the server's
        current-or-last-good snapshot), never re-read from the host, so the read-only stale-serving
        policy holds for it while other documents come from the host cache.
        """
        seen: set[str] = set()
        for uri in (target.uri, doc.uri, *self._host.workspace_files()):
            if uri in seen:
                continue
            seen.add(uri)
            if uri == doc.uri:
                yield doc
            else:
                scanned = self._host.document(uri)
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
