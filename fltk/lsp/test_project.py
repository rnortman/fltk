"""Tests for the project layer: ``ProjectHost`` caching/scan/text-source and ``ProjectNavigator``.

A tiny fixture language (``def``/``ref``/``use`` statements) and a test-local resolver that
resolves import bindings and unresolved references by name across the workspace exercise both
resolver hooks -- ``symbol_targets`` (with a deliberately divergent declaration range, to pin the
selection-range-only identity rule) and ``ref_targets`` (the hook the gear demo does not use).
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import TYPE_CHECKING

import pytest
from pygls import uris

from fltk import plumbing
from fltk.lsp.conftest import nth_offset
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.lsp_config import load_lsp_config
from fltk.lsp.project import Hazard, ProjectHost, ProjectNavigator, canonical_uri
from fltk.lsp.resolver import CrossFileResolution, ExternalTarget

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fltk.lsp.resolver import ResolvedDocument, Resolver, ResolverHost
    from fltk.lsp.symbols import Symbol


# `def Name;` defines a symbol; `use Name;` defines an import binding; `ref Name;` references any
# kind, resolving same-file if a matching def/use is in scope, else staying unresolved.
FIX_GRAMMAR = r"""
top := , item* ;
item := def_stmt | ref_stmt | use_stmt ;
def_stmt := kw:"def" : name:word . ";" , ;
ref_stmt := kw:"ref" : name:word . ";" , ;
use_stmt := kw:"use" : name:word . ";" , ;
word := value:/[A-Za-z_][A-Za-z0-9_]*/ ;
_trivia := (ws)+ ;
ws := chars:/\s+/ ;
"""

FIX_LSP = """
rule def_stmt { def name: symbol; }
rule ref_stmt { ref name: *; }
rule use_stmt { def name: import; }
"""


def _engine() -> AnalysisEngine:
    grammar = plumbing.parse_grammar(FIX_GRAMMAR)
    resolved = load_lsp_config(FIX_LSP, grammar)
    return AnalysisEngine(grammar, resolved, start_rule="top")


class _NameResolver:
    """Resolves import bindings and unresolved refs to same-named ``def`` symbols elsewhere.

    ``symbol_targets`` entries deliberately collapse the target's declaration range onto its name
    span -- divergent from the real ``def`` node's range -- so tests confirm identity matching
    ignores the declaration range.
    """

    file_suffixes: Sequence[str] = (".fix",)

    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution:
        index = _index_defs(host)
        ref_targets = {}
        symbol_targets = {}
        for symbol in doc.symbols.symbols:
            if symbol.kind == ("import",):
                hit = index.get(symbol.name)
                if hit is not None and hit[0] != doc.uri:
                    target_uri, target = hit
                    # Divergent declaration range (name span, not the real def node span).
                    symbol_targets[symbol] = ExternalTarget(
                        uri=target_uri,
                        name_start=target.name_start,
                        name_end=target.name_end,
                        range_start=target.name_start,
                        range_end=target.name_end,
                    )
        for ref in doc.symbols.references:
            if ref.symbol is None:
                hit = index.get(ref.name)
                if hit is not None and hit[0] != doc.uri:
                    target_uri, target = hit
                    ref_targets[ref] = ExternalTarget(
                        uri=target_uri,
                        name_start=target.name_start,
                        name_end=target.name_end,
                        range_start=target.range_start,
                        range_end=target.range_end,
                    )
        return CrossFileResolution(ref_targets=ref_targets, symbol_targets=symbol_targets)


def _index_defs(host: ResolverHost) -> dict[str, tuple[str, Symbol]]:
    """Map each real (``kind == ('symbol',)``) def name to ``(uri, symbol)`` across the workspace."""
    index: dict[str, tuple[str, Symbol]] = {}
    for uri in host.workspace_files():
        doc = host.document(uri)
        if doc is None:
            continue
        for symbol in doc.symbols.symbols:
            if symbol.kind == ("symbol",) and symbol.name not in index:
                index[symbol.name] = (uri, symbol)
    return index


class _RaisingResolver:
    file_suffixes: Sequence[str] = (".fix",)

    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution:  # noqa: ARG002
        msg = "boom"
        raise RuntimeError(msg)


def _uri(path: pathlib.Path) -> str:
    uri = uris.from_fs_path(str(path))
    assert uri is not None
    return uri


def _write(root: pathlib.Path, name: str, text: str) -> str:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _uri(path)


# --- ProjectHost -------------------------------------------------------------------------------


def test_open_buffer_beats_disk(tmp_path: pathlib.Path) -> None:
    uri = _write(tmp_path, "a.fix", "def OnDisk;\n")
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path, open_docs={uri: (1, "def InBuffer;\n")})
    doc = host.document(uri)
    assert doc is not None
    assert [s.name for s in doc.symbols.symbols] == ["InBuffer"]


def test_disk_cache_reuse_and_invalidation(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.fix"
    path.write_text("def A;\n", encoding="utf-8")
    uri = _uri(path)
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)

    first = host.document(uri)
    assert first is not None
    # Unchanged file: same analysis object reused (version-keyed cache hit).
    assert host.document(uri) is first

    # Rewrite with different content and size: version key changes, re-analysis happens.
    path.write_text("def A;\ndef B;\n", encoding="utf-8")
    second = host.document(uri)
    assert second is not None
    assert second is not first
    assert [s.name for s in second.symbols.symbols] == ["A", "B"]


def test_partial_and_failed_return_none(tmp_path: pathlib.Path) -> None:
    uri = _write(tmp_path, "bad.fix", "def ;\n")
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    assert host.document(uri) is None
    # Still None on a repeat access (a failed parse is never cached as a usable document).
    assert host.document(uri) is None


def test_missing_file_returns_none(tmp_path: pathlib.Path) -> None:
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    uri = _uri(tmp_path / "nope.fix")
    assert host.document(uri) is None
    assert host.line_index(uri) is None


def test_unreadable_file_returns_none_and_warns_once(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "bad.fix"
    path.write_bytes(b"\xff\xfe def A;\n")  # not valid UTF-8
    uri = _uri(path)
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)

    assert host.document(uri) is None
    warnings = host.drain_warnings()
    assert len(warnings) == 1
    assert uri in warnings[0]

    # A second access still yields None but must not re-emit the warning (warn-once).
    assert host.document(uri) is None
    assert host.drain_warnings() == []


def test_canonical_uri_collapses_percent_encoding(tmp_path: pathlib.Path) -> None:
    # A client (e.g. Windows VS Code) may percent-encode a path character that pygls does not, so
    # two string-unequal URIs name the same file. `canonical_uri` must collapse them and be
    # idempotent on the already-canonical form -- otherwise every cross-file identity comparison
    # (rename guard, references dedup) is raw string equality and fails open on such a client.
    path = tmp_path / "a.fix"
    canonical = _uri(path)
    assert canonical.endswith("a.fix")
    noncanonical = canonical[: -len("a.fix")] + "%61.fix"  # %61 == 'a'
    assert noncanonical != canonical
    assert canonical_uri(noncanonical) == canonical
    assert canonical_uri(canonical) == canonical


def test_open_buffer_served_through_noncanonical_uri(tmp_path: pathlib.Path) -> None:
    # The open-document snapshot is keyed by a non-canonical (percent-encoded) client spelling, but a
    # lookup by the canonical form must still hit the open buffer -- pins that `open_docs` keys and
    # the `document()` lookup are both canonicalized. Without that, this reads stale disk text.
    path = tmp_path / "a.fix"
    path.write_text("def OnDisk;\n", encoding="utf-8")
    canonical = _uri(path)
    noncanonical = canonical[: -len("a.fix")] + "%61.fix"
    assert noncanonical != canonical
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path, open_docs={noncanonical: (1, "def InBuffer;\n")})
    doc = host.document(canonical)
    assert doc is not None
    assert [s.name for s in doc.symbols.symbols] == ["InBuffer"]


def test_workspace_scan_filters_suffixes_and_dot_dirs(tmp_path: pathlib.Path) -> None:
    a = _write(tmp_path, "a.fix", "def A;\n")
    b = _write(tmp_path, "sub/b.fix", "def B;\n")
    _write(tmp_path, "c.txt", "not fix\n")
    _write(tmp_path, ".hidden/d.fix", "def D;\n")
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    assert set(host.workspace_files()) == {a, b}


def test_line_index_available(tmp_path: pathlib.Path) -> None:
    uri = _write(tmp_path, "a.fix", "def A;\ndef B;\n")
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    line_index = host.line_index(uri)
    assert line_index is not None
    assert line_index.line_of(0) == 0


def test_no_root_scan_empty_but_open_buffers_served(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "a.fix"
    path.write_text("def A;\n", encoding="utf-8")
    uri = _uri(path)
    host = ProjectHost(_engine(), _NameResolver(), root_path=None, open_docs={uri: (1, "def Open;\n")})
    assert host.workspace_files() == ()
    doc = host.document(uri)
    assert doc is not None
    assert [s.name for s in doc.symbols.symbols] == ["Open"]


def test_uri_path_roundtrip(tmp_path: pathlib.Path) -> None:
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    path = tmp_path / "a.fix"
    uri = host.path_to_uri(path)
    assert host.uri_to_path(uri) == path


# --- ProjectNavigator --------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _Fixture:
    host: ProjectHost
    navigator: ProjectNavigator
    lib_uri: str
    extra_uri: str
    main_uri: str
    lib_text: str
    extra_text: str
    main_text: str

    def main_doc(self) -> ResolvedDocument:
        doc = self.host.document(self.main_uri)
        assert doc is not None
        return doc

    def lib_doc(self) -> ResolvedDocument:
        doc = self.host.document(self.lib_uri)
        assert doc is not None
        return doc

    def extra_doc(self) -> ResolvedDocument:
        doc = self.host.document(self.extra_uri)
        assert doc is not None
        return doc


def _fixture(tmp_path: pathlib.Path, resolver: Resolver | None = None) -> _Fixture:
    lib_text = "def Gear;\n"
    extra_text = "def Loose;\n"
    main_text = "use Gear;\nref Gear;\nref Loose;\n"
    lib_uri = _write(tmp_path, "lib.fix", lib_text)
    extra_uri = _write(tmp_path, "extra.fix", extra_text)
    main_uri = _write(tmp_path, "main.fix", main_text)
    host = ProjectHost(_engine(), _NameResolver(), root_path=tmp_path)
    navigator = ProjectNavigator(host, resolver or _NameResolver())
    return _Fixture(host, navigator, lib_uri, extra_uri, main_uri, lib_text, extra_text, main_text)


def test_definition_on_import_binding_redirects_cross_file(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    # Cursor on `Gear` in `use Gear;`.
    offset = nth_offset(fx.main_text, "Gear", 0)
    target = fx.navigator.definition(fx.main_doc(), offset)
    assert target is not None
    assert target.uri == fx.lib_uri
    lib_gear = nth_offset(fx.lib_text, "Gear")
    assert (target.name_start, target.name_end) == (lib_gear, lib_gear + 4)
    # The resolver deliberately diverged the declaration range onto the name span.
    assert (target.range_start, target.range_end) == (lib_gear, lib_gear + 4)


def test_definition_on_local_ref_chains_through_binding(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    # Cursor on `Gear` in `ref Gear;` -- resolves same-file to the import binding, then cross-file.
    offset = nth_offset(fx.main_text, "Gear", 1)
    target = fx.navigator.definition(fx.main_doc(), offset)
    assert target is not None
    assert target.uri == fx.lib_uri


def test_definition_on_unresolved_ref_uses_ref_targets(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    offset = nth_offset(fx.main_text, "Loose")
    target = fx.navigator.definition(fx.main_doc(), offset)
    assert target is not None
    assert target.uri == fx.extra_uri


def test_definition_addresses_nothing(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    # Offset on the `use` keyword, not a name.
    assert fx.navigator.definition(fx.main_doc(), 0) is None


def test_references_from_definition_aggregates_cross_file(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    lib_gear = nth_offset(fx.lib_text, "Gear")
    locs = fx.navigator.references(fx.lib_doc(), lib_gear, include_declaration=True)
    assert locs is not None
    use_gear = nth_offset(fx.main_text, "Gear", 0)
    ref_gear = nth_offset(fx.main_text, "Gear", 1)
    assert set(locs) == {
        (fx.lib_uri, lib_gear, lib_gear + 4),  # the declaration
        (fx.main_uri, use_gear, use_gear + 4),  # the import binding
        (fx.main_uri, ref_gear, ref_gear + 4),  # a local ref to the binding
    }


def test_references_excludes_declaration(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    lib_gear = nth_offset(fx.lib_text, "Gear")
    locs = fx.navigator.references(fx.lib_doc(), lib_gear, include_declaration=False)
    assert locs is not None
    assert (fx.lib_uri, lib_gear, lib_gear + 4) not in locs
    use_gear = nth_offset(fx.main_text, "Gear", 0)
    assert (fx.main_uri, use_gear, use_gear + 4) in locs


def test_references_includes_unresolved_ref_matches(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    loose = nth_offset(fx.extra_text, "Loose")
    locs = fx.navigator.references(fx.extra_doc(), loose, include_declaration=True)
    assert locs is not None
    main_loose = nth_offset(fx.main_text, "Loose")
    assert (fx.extra_uri, loose, loose + len("Loose")) in locs
    assert (fx.main_uri, main_loose, main_loose + len("Loose")) in locs


def test_references_deduplicated(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    lib_gear = nth_offset(fx.lib_text, "Gear")
    locs = fx.navigator.references(fx.lib_doc(), lib_gear, include_declaration=True)
    assert locs is not None
    assert len(locs) == len(set(locs))


def test_resolver_exception_propagates(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path, resolver=_RaisingResolver())
    offset = nth_offset(fx.main_text, "Gear", 0)
    with pytest.raises(RuntimeError, match="boom"):
        fx.navigator.definition(fx.main_doc(), offset)


def test_rename_hazard_flags_import_binding(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    main_doc = fx.main_doc()
    binding = next(s for s in main_doc.symbols.symbols if s.name == "Gear")
    offset = nth_offset(fx.main_text, "Gear", 0)  # the `use Gear;` binding site
    assert fx.navigator.rename_hazard(main_doc, binding, offset) is Hazard.IMPORT_BINDING


def test_rename_hazard_flags_cross_file_definition(tmp_path: pathlib.Path) -> None:
    fx = _fixture(tmp_path)
    lib_doc = fx.lib_doc()
    gear = next(s for s in lib_doc.symbols.symbols if s.name == "Gear")
    offset = nth_offset(fx.lib_text, "Gear", 0)
    # `Gear` is defined here but imported/referenced in main.fix -- a same-file rename is unsafe.
    assert fx.navigator.rename_hazard(lib_doc, gear, offset) is Hazard.CROSS_FILE
