# Deep review — reuse (round 5, pass 1)

Base: 1e920dc  HEAD: fe10193

## reuse-1

- **File:line**: `examples/gear/gear_resolver.py:111-142` (`_module_parts`, `_nodes_of_kind`, `_labeled_child`, `_span`, `_span_text`)
- **What's duplicated**: The gear resolver hand-rolls its own "decode a CST child" logic —
  `_span()` branches on `child.kind == SpanKind.SPAN` to pick `child.start/child.end` vs.
  `child.span.start/child.span.end`, and `_labeled_child()` linear-scans `node.children`
  comparing `label.name` — to locate `use_stmt`/`IMPORTITEM` children and read their text.
- **Existing function/utility**: `fltk/lsp/classify.py:178-199`, `child_surface(label, child,
  text, tables)`. Its docstring states exactly this intent: "Decode one `(label, child)` pair
  into the fields matcher dispatch needs... The paint walk and the symbol-extraction walk share
  this so both decode a child identically." It already performs the identical
  `is_span = child.kind == SpanKind.SPAN` branch and start/end extraction that
  `gear_resolver._span` reimplements, and additionally returns the label name and (for node
  children) the resolved rule name — a superset of what `_labeled_child`/`_span_text` compute by
  hand.
- **Consequence**: `gear_resolver.py` is explicitly documented (module docstring, and design
  §4.8/§2.4) as "the worked example for writing your own resolver" for downstream authors. A
  third decoding path for the same span/node distinction — alongside `classify.py`'s walk and
  `symbols.py`'s `_walk` — means any future change to how span vs. node children are
  distinguished (e.g. a new `SpanKind`, or additional CST child metadata) has to be found and
  fixed in this third place too, and a downstream resolver author copying this file as their
  template inherits the un-reused version rather than the one the rest of the LSP stack is kept
  in sync via `child_surface`.

## reuse-2

- **File:line**: `fltk/lsp/server.py:443-160` (`FltkLanguageServer._workspace_root`) vs.
  `fltk/lsp/project.py:132-137` (`ProjectHost.uri_to_path`)
- **What's duplicated**: `_workspace_root` inlines the URI-to-filesystem-path conversion twice
  (once for `workspace.folders`, once for `workspace.root_uri`):
  ```python
  fs_path = uris.to_fs_path(first.uri)
  if fs_path is not None:
      return pathlib.Path(fs_path)
  ```
  This is the same `uris.to_fs_path(...)` → `pathlib.Path(...) if not None else None` pattern
  that `project.py` extracts as a one-line reusable method in the very same diff.
- **Existing function/utility**: `ProjectHost.uri_to_path` (`fltk/lsp/project.py:132-134`):
  `fs_path = uris.to_fs_path(uri); return pathlib.Path(fs_path) if fs_path is not None else
  None`. It is a pure function of `uri` (does not touch `self`), so it could be a module-level
  helper both `project.py` and `server.py._workspace_root` call, instead of `server.py`
  re-deriving the conversion inline twice more.
- **Consequence**: three copies of the same conversion (two inline in `_workspace_root`, one as
  `ProjectHost.uri_to_path`) in files introduced/touched in the same round. If URI-to-path
  handling ever needs a fix or extension (e.g. handling `to_fs_path` returning an empty string
  vs. `None`, or adding URI-scheme validation), fixing only `ProjectHost.uri_to_path` silently
  leaves `_workspace_root`'s two inline copies on the old behavior.

## reuse-3

- **File:line**: `fltk/lsp/test_project.py:133-137` (`_offset`), `fltk/lsp/test_server_crossfile.py:99-103`
  (`_nth`), `fltk/lsp/test_gear_demo.py:45-50` (`_nth_offset`)
- **What's duplicated**: All three new test modules define byte-for-byte the same "find the
  offset of the Nth occurrence of a substring" helper:
  ```python
  idx = -1
  for _ in range(occurrence + 1):
      idx = text.index(needle, idx + 1)
  return idx
  ```
  under three different names, in three files all added in this round.
- **Existing function/utility**: `fltk/lsp/conftest.py` is the suite's established home for
  helpers shared across `fltk/lsp` test modules (already hosts `build_hello_engine`,
  `token_for`, `token_type_at`, used by the engine/CLI/feature tests). None of the three new
  modules add their helper there, so each reinvents it independently instead of adding it once
  to the existing shared-helpers module.
- **Consequence**: the three copies are already textually identical but have already drifted
  in signature (`_offset`'s `occurrence` has a `= 0` default, the other two don't) and docstring
  presence (`test_gear_demo.py`'s is documented, the other two aren't). Future edits to the
  offset-finding behavior (e.g. Unicode/codepoint edge cases, or a clearer failure message on a
  missing occurrence) have three call sites to find and update instead of one, and new cross-file
  tests are likely to add a fourth copy rather than discover an existing one, since it isn't in
  `conftest.py` where the rest of the suite's shared fixtures live.
