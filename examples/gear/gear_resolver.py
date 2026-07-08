"""The `gear` cross-file resolver — the reference implementation of the fltk-lsp resolver API.

**Provisional API notice.** The resolver protocol (`fltk.lsp.resolver`) is provisional: it has
exactly this one in-repo implementation until a real downstream language validates it, and is
subject to change until then. Treat this file as the worked example for writing your own
resolver, not as a frozen contract.

What a resolver does: for one analyzed document, it turns the same-file symbol analysis
(`doc.symbols`) into cross-file answers. Gear's imports bind *local* symbols — `use
lib::shapes::{Circle, Square as Box}` introduces `Circle` and `Box` as local names — so the
work here is entirely `symbol_targets`: "this local import binding is really declared over
there." (A language whose references stay textually unresolved same-file would instead fill
`ref_targets`; gear never needs that.)

The mapping is deliberately simple and demonstrates the whole surface:

- Walk the document's own CST (`doc.tree`) for `use` statements — `.fltklsp` carries no
  cross-file vocabulary, so the resolver reads the target grammar's import constructs directly.
- Map a module path `a::b` to `<root>/a/b.gear` under `host.root_path()`.
- `host.document()` that file (open-buffer text if the editor has it open, else disk; cached),
  and look up the imported name among its top-level symbols.
- Redirect both the import binding's own name and its alias (when present) to that definition,
  so either identifier navigates. Copy all four offsets verbatim from the target's `Symbol`.

Missing files, unparsable targets, or names the target does not export simply yield no entry —
silent degradation to same-file behavior, the same policy same-file unresolved references
follow. Import cycles are safe: the host caches per-document analyses and gear chases only one
hop by construction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fltk.fegen.pyrt.span_protocol import SpanKind
from fltk.lsp.resolver import CrossFileResolution, ExternalTarget

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fltk.lsp.resolver import ResolvedDocument, ResolverHost

_FILE_SUFFIX = ".gear"


def create_resolver() -> GearResolver:
    """Factory named per the `--resolver module:create_resolver` convention."""
    return GearResolver()


class GearResolver:
    """Resolves gear `use` imports to definitions in other `.gear` files."""

    file_suffixes = (_FILE_SUFFIX,)

    def resolve(self, doc: ResolvedDocument, host: ResolverHost) -> CrossFileResolution:
        root = host.root_path()
        if root is None:
            # No workspace root: nothing to resolve module paths against. Definitions through
            # an import degrade to same-file (unresolved), exactly as with a missing target file.
            return CrossFileResolution()

        # Every local symbol keyed by its selection range, so an import binding found in the CST
        # can be paired with the Symbol object the server holds (mapping keys must be those exact
        # objects to match).
        local_by_span = {(s.name_start, s.name_end): s for s in doc.symbols.symbols}
        symbol_targets: dict[Any, ExternalTarget] = {}
        # Cache each target module's exported symbols within this call, so several `use` statements
        # importing from the same module do not rebuild the export map repeatedly.
        exports_by_uri: dict[str, dict[str, Any]] = {}

        for use_stmt in _nodes_of_kind(doc.tree, "USESTMT"):
            path_node = _labeled_child(use_stmt, "PATH")
            if path_node is None:
                continue
            parts = _module_parts(doc.text, path_node)
            # Module-path segments come from untrusted document text, so a segment could otherwise be
            # a separator or `..` that traverses out of the workspace. Gear's grammar already limits
            # them to identifiers, but validate anyway: this file is a template downstream resolver
            # authors copy, and a real module system whose segments admit `.`/`..` would be
            # exploitable without this guard. (Equivalently, one could confirm the resolved path is
            # relative to `root` before reading it.)
            if not parts or not all(part.isidentifier() for part in parts):
                continue
            target_path = root.joinpath(*parts).with_suffix(_FILE_SUFFIX)
            target_uri = host.path_to_uri(target_path)
            exports = exports_by_uri.get(target_uri)
            if exports is None:
                target_doc = host.document(target_uri)
                if target_doc is None:
                    continue
                exports = {s.name: s for s in target_doc.symbols.root.symbols}
                exports_by_uri[target_uri] = exports

            for item in _nodes_of_kind(use_stmt, "IMPORTITEM"):
                name_child = _labeled_child(item, "NAME")
                if name_child is None:
                    continue
                imported_name = _span_text(doc.text, name_child)
                export = exports.get(imported_name)
                if export is None:
                    continue
                target = ExternalTarget(
                    uri=target_uri,
                    name_start=export.name_start,
                    name_end=export.name_end,
                    range_start=export.range_start,
                    range_end=export.range_end,
                )
                # Redirect the binding under both the imported name and its alias, so both
                # identifiers go to definition and both count as references to it.
                for label in ("NAME", "ALIAS"):
                    child = _labeled_child(item, label)
                    if child is None:
                        continue
                    binding = local_by_span.get(_span(child))
                    if binding is not None:
                        symbol_targets[binding] = target

        return CrossFileResolution(symbol_targets=symbol_targets)


def _module_parts(text: str, path_node: Any) -> list[str]:
    """Split a `module_path` node's text (`a::b::`) into path segments (`['a', 'b']`)."""
    return [part for part in _span_text(text, path_node).split("::") if part]


def _nodes_of_kind(node: Any, kind_name: str) -> Iterator[Any]:
    """Yield every node in the subtree whose CST `kind.name` equals `kind_name`."""
    if getattr(node.kind, "name", None) == kind_name:
        yield node
    for _label, child in node.children:
        if child.kind != SpanKind.SPAN:
            yield from _nodes_of_kind(child, kind_name)


def _labeled_child(node: Any, label: str) -> Any | None:
    """The first child of `node` carrying grammar `label`, or `None`."""
    for lbl, child in node.children:
        if getattr(lbl, "name", None) == label:
            return child
    return None


def _span(child: Any) -> tuple[int, int]:
    """The `(start, end)` codepoint span of a CST child, span-terminal or node alike."""
    if child.kind == SpanKind.SPAN:
        return child.start, child.end
    return child.span.start, child.span.end


def _span_text(text: str, child: Any) -> str:
    start, end = _span(child)
    return text[start:end]
