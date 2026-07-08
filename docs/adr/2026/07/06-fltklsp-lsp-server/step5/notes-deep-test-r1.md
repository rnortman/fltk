# Deep test review — round 5 (resolver plugin API, gear demo, VS Code wiring)

Base `1e920dc` → HEAD `fe10193`. Scope: `fltk/lsp/resolver.py`, `fltk/lsp/project.py`,
`fltk/lsp/server.py` cross-file paths, `fltk/lsp/server_cli.py` `--resolver`, and the new
`examples/gear/*` demo + its four new test files.

## Overall assessment

Presence and quality are both strong. `test_resolver_api.py` covers every `load_resolver`
validation branch with real (non-mocked) module/file loading and precise `match=` assertions.
`test_project.py` exercises `ProjectHost` caching/invalidation/text-source precedence and
`ProjectNavigator`'s canonical-target/aggregation logic against a real tiny fixture language
(not mocks), including the deliberately-divergent-declaration-range identity rule the design
calls out as easy to get wrong. `test_gear_demo.py` and `test_server_crossfile.py` drive the
real `gear` grammar/`.fltklsp`/resolver end to end via a real spawned server (pytest-lsp), with
assertions on actual offsets/URIs/text spans rather than "didn't throw" smoke checks. No vacuous
assertions, no over-mocking, no brittle implementation-detail testing found. A handful of new
code paths are nonetheless unexercised; see below.

## Findings

### test-1: Cross-file resolver paths combined with last-good stale-serving are untested

`fltk/lsp/server.py:100-118` — the design's stated reason for adding `_GoodAnalysis.text`
(§2.1/§4.5: "the requesting-side `ResolvedDocument` is built wholesale from that snapshot...
never pairing live buffer text with a last-good tree") is precisely the scenario where the
*current* document version has a parse error and `definition_crossfile`/`references_crossfile`
(`server.py:584-635`) must serve from `state.last_good` instead. No test in
`test_server_crossfile.py` ever breaks the requesting document (via a syntax-error `didChange`)
before issuing a cross-file definition/references request with `--resolver` active. The
pre-existing `test_navigation_served_from_last_good_after_break` in `test_server.py` only
exercises the no-resolver path (predates this round, `server._resolver is None`), so it does not
touch the new `good.text`-sourced `ResolvedDocument` construction at all.

**Consequence**: a bug in wiring `_GoodAnalysis.text` into the resolver path — e.g. accidentally
reading the live (broken) buffer text instead of `good.text`, or a version mismatch between
`good.tree`/`good.symbols`/`good.text` — would silently serve wrong offsets or crash, and no
test would catch it. This is exactly the version-mixing hazard the docstring at
`server.py:100-107` says the field exists to prevent.

**Fix**: add a `test_server_crossfile.py` case that opens `main.gear`, sends a breaking edit
(e.g. delete a closing brace) via `didChange`, then issues `textDocument/definition` (and/or
`textDocument/references`) on a still-valid cross-file target and asserts the last-good
cross-file location is still returned correctly.

### test-2: `definition_crossfile`'s resolver-exception degradation is untested

`server.py:584-602` (`_definition_blocking`'s `except Exception` branch, `server.py:526-537`)
mirrors `references_crossfile`'s degradation path, but only the references side is exercised:
`test_raising_resolver_degrades_references_but_fails_rename_closed`
(`test_server_crossfile.py:270-284`) calls `_references`, never `_definition`, against the
always-raising resolver. `features.definition_location` (the same-file fallback rendering
function used at `server.py:601`) is therefore never invoked from this degradation path in any
test.

**Consequence**: a regression that breaks definition's degrade-to-same-file behavior
specifically (as opposed to references') — e.g. an exception escaping instead of being caught,
or the same-file fallback call site being wrong — would go undetected even though the parallel
references case is guarded.

**Fix**: extend the `raising_client` test (or add a sibling) to also call
`_definition(raising_client, _MAIN_URI, ...)` on a cross-file-eligible position and assert it
degrades to the local (same-file) import-binding location rather than raising or returning the
cross-file target.

### test-3: The pre-alias import name's own navigation is unexercised

`examples/gear/gear_resolver.py:96-104` redirects *both* labels of an `import_item` — `NAME`
(the pre-alias name, e.g. `Square`) and `ALIAS` (e.g. `Box`) — to the target definition, and the
design explicitly calls this out (§4.8: "redirect both the import binding's own name and its
alias... so either identifier navigates"). `gear.fltklsp` backs this with two separate `Symbol`s
(`import_item` has `def name: import;` and `def alias: import;`), so `Square` and `Box` are
distinct local symbols requiring independent matching in `symbol_targets`. Every alias test —
`test_definition_through_alias` (`test_server_crossfile.py:188-197`) and
`test_resolver_resolves_alias_to_original_definition` (`test_gear_demo.py:136-145`) — clicks
only on the *usage* site `frame: Box` (occurrence 1 of `"Box"`), never on `Square` inside
`use lib::shapes::{Circle, Square as Box};` itself (occurrence 0), and no test runs
find-references from/through the pre-alias name either.

**Consequence**: the `NAME`-label redirect half of the resolver's loop
(`for label in ("NAME", "ALIAS")`) could be silently broken (e.g. an off-by-one in which label is
processed, or the loop body accidentally short-circuiting after `ALIAS`) and no test would fail,
despite this being an explicitly documented, distinct behavior.

**Fix**: add a definition (and/or references) test that positions the cursor on `Square` at its
declaration site inside the `use` statement in `main.gear` and asserts it too navigates to
`lib/shapes.gear`'s `Square` definition.

### test-4: `ProjectHost`'s unreadable/non-UTF-8 disk file path is untested

`fltk/lsp/project.py:157-166` — the `except (OSError, UnicodeDecodeError)` branch, including the
warn-once `_warned_unreadable` set (meant to avoid re-logging the same broken file on every
access), has no test. `test_project.py`'s `test_missing_file_returns_none` covers a nonexistent
file (an `OSError` from `.stat()`, a different code path — `_source` returns `None` before ever
reaching the `read_text` call), not an existing-but-unreadable/non-UTF-8 file.

**Consequence**: the warn-once dedup logic (`if uri not in self._warned_unreadable`) is new,
easy to get backwards (e.g. warning on every access, or never warning at all), and untested;
a regression here would only surface as excessive/missing `window/logMessage` spam in a real
editor session, not as a test failure.

**Fix**: add a `ProjectHost` test that writes a file with invalid UTF-8 bytes (or removes read
permission), asserts `host.document(uri)` returns `None`, and asserts a second access does not
re-emit the warning (e.g. via `caplog`, since the current warning path uses the module logger).

### test-5: `_workspace_root()`'s `workspace.folders` branch is untested

`server.py:444-461` — `_workspace_root()` prefers `self.workspace.folders` (multi-root
workspaces) over `self.workspace.root_uri`, but every `test_server_crossfile.py` fixture
initializes with only `root_uri=_ROOT_URI` (`_init_params`, `test_server_crossfile.py:68-74`),
never `workspace_folders=[...]`. The `if folders:` branch (`server.py:449-453`) is therefore dead
in this round's test suite.

**Consequence**: lower-severity than the above (the two branches share nearly all downstream
logic, and `pygls`/LSP-protocol-level folder handling is comparatively mechanical), but a real
VS Code session opening a folder sends `workspace_folders`, not `root_uri` — so the one code path
actually exercised by the manual acceptance pass (§4.10) is the one automated tests skip.

**Fix**: add one `test_server_crossfile.py`-style case (or a lighter unit test constructing
`FltkLanguageServer` directly and populating `self.workspace.folders`) asserting
`_workspace_root()` resolves correctly from `workspace_folders`, and that cross-file
definition/references work end to end when initialized that way instead of via `root_uri`.
