# Deep-review dispositions — round 5, r1 (attempt 1)

Base `1e920dc` → reviewed HEAD `fe10193`. All fixes applied on top; full suite (`uv run pytest`)
green (2971 passed, 1 skipped), `ruff check`/`ruff format`/`pyright` clean.

Several findings converged and were fixed together: the rename-guard hardening (quality-2 enum,
quality-3 layering, efficiency-2 double-resolve) landed as one `ProjectNavigator.rename_hazard`
method; the traceback-in-resolver-logs finding was raised by both errhandling-2 and quality-4; the
`path_to_uri` `""` sentinel by both errhandling-4 and quality-6.

---

## errhandling-1
- Disposition: Fixed
- Action: `ProjectHost` now accumulates client-surfacable warnings and exposes `drain_warnings()`
  (`fltk/lsp/project.py:81-85`); `_source` appends the unreadable-file message there in addition to
  the module logger (`project.py:213-217`). The three worker blocking methods drain the host into
  their `logs` list via the new `_drain` helper (`fltk/lsp/server.py:839-842`, called at
  `server.py:_definition_blocking`/`_references_blocking`/`_rename_guard_blocking`), so the report
  reaches the client as `window/logMessage` as design §4.2 promised. New test:
  `test_unreadable_file_returns_none_and_warns_once` (`fltk/lsp/test_project.py`).
- Severity assessment: a neighbor file skipped for an encoding/IO reason was previously invisible to
  the editor user (module logger → stderr), indistinguishable from a genuine no-references result.

## errhandling-2
- Disposition: Fixed (merged with quality-4)
- Action: all three resolver/guard catch sites now log `traceback.format_exc()` instead of `{exc!r}`
  (`fltk/lsp/server.py` `_definition_blocking`, `_references_blocking`, `_rename_guard_blocking`),
  matching the `_debounced_analyze` convention. Verified live: the crossfile tests' server logs now
  carry full stacks pointing into the resolver.
- Severity assessment: a downstream resolver's failing line was previously unlocatable from the
  client log alone; the stack is the only in-editor diagnostic for third-party plugin code.

## errhandling-3
- Disposition: Fixed
- Action: `ProjectHost.workspace_files` now passes an `onerror` callback to `os.walk` that records
  the scan error into the surfaced warnings (`fltk/lsp/project.py:100-107`), so a permission-denied
  or vanished subtree is reported rather than silently dropped.
- Severity assessment: the walk error was totally invisible before. I did not make the scan *raise*
  (which would fail-close the rename guard) because design §5 deliberately chooses silent
  degradation for individually unreadable/unparseable targets on the read path; a subtree that
  produces no entries is the same class. Surfacing it is the design-consistent fix; whether the
  rename guard should refuse on an *incomplete* scan (a §4.6-vs-§5 tension the design did not
  resolve) is left as-is rather than exceeding the spec.

## errhandling-4
- Disposition: Fixed (merged with quality-6)
- Action: documented the `""`-sentinel behavior of `ProjectHost.path_to_uri` in its docstring
  (`fltk/lsp/project.py:109-116`), explaining that an empty URI addresses nothing so `document("")`
  is `None` and a copied `ExternalTarget.uri=""` is a no-op navigation.
- Severity assessment: low (the reviewer tagged it low-confidence; resolvers pass absolute paths
  `from_fs_path` does not reject). Not changed to `-> str | None`: the frozen design §4.1 pins the
  protocol signature as `-> str`, so widening it would contradict an immutable doc; documenting the
  deliberate sentinel is the proportionate fix.

## correctness-1
- Disposition: Fixed
- Action: `_instantiate` now excludes classes from the already-an-instance shortcut
  (`not isinstance(obj, type) and hasattr(obj, "resolve")`) and invokes a class as a factory
  (`fltk/lsp/resolver.py:_instantiate`). New test `test_module_attr_class_is_instantiated`
  (`fltk/lsp/test_resolver_api.py`).
- Severity assessment: high — the natural spec mistake `--resolver mod:GearResolver` previously
  passed startup validation then `TypeError`'d on every definition/references/rename call
  permanently (the half-working server §4.3 forbids).

## correctness-2
- Disposition: Fixed
- Action: added `canonical_uri` (round-trips a URI through the filesystem path to pygls's
  `from_fs_path` spelling; `fltk/lsp/project.py:39-56`) and applied it at every identity boundary:
  `ProjectHost` canonicalizes `open_docs` keys (`project.py` `__init__`) and the incoming URI in
  `_ensure`; the server builds the requesting `ResolvedDocument` with `canonical_uri(uri)` in
  `definition_crossfile`, `references_crossfile`, and the rename guard. Idempotent on
  already-canonical URIs, so Linux behavior is unchanged (full suite green).
- Severity assessment: high on divergent-serialization clients (Windows VS Code sends
  `file:///c%3A/...`): the rename guard's `occ_uri != doc.uri` and the cross-file identity match
  previously failed by string inequality, so the guard could fail **open** (silent project
  corruption, the exact §2.3/§4.6 hazard) and find-references drop cross-file occurrences. Windows
  is not exercised in CI, but the fix collapses both sides to one canonical form and is provably
  inert on the tested platform.

## security-1
- Disposition: Fixed
- Action: `gear.server.command` is now `"scope": "machine"` and the extension declares
  `"capabilities": { "untrustedWorkspaces": { "supported": false } }`
  (`examples/gear/vscode/package.json`).
- Severity assessment: real (published LSP-extension CVE class): a cloned repo's
  `.vscode/settings.json` could otherwise set the launched argv. Machine scope blocks workspace
  override; the explicit untrusted-workspace posture makes the trust decision deliberate. The demo's
  default path does not use the setting, so nothing shipped changes behavior.

## security-2
- Disposition: TODO(resolver-spec-file-recognition)
- Action: `TODO(resolver-spec-file-recognition)` comment at `fltk/lsp/resolver.py:_looks_like_path`
  plus a `TODO.md` entry.
- Severity assessment: real but narrow — a bare-module resolver spec (no `.py`/separator) can be
  exec'd from a same-named cwd file, so a hostile workspace the editor spawned the server inside
  could run arbitrary Python. No shipped config is affected (gear/README use explicit `.py` paths).
  Not Fixed in respond mode because the fix (drop the bare `is_file()` recognition) contradicts the
  frozen design §4.3 ("a path is recognized by an existing file"); reconciling needs a design delta,
  which cannot be authored against an immutable doc here.

## security-3
- Disposition: Fixed
- Action: the gear resolver now rejects any module-path segment that is not a plain identifier
  before touching the filesystem, with a comment explaining the untrusted-text hazard
  (`examples/gear/gear_resolver.py:resolve`); added a resolver-author guidance bullet to
  `fltk/lsp/resolver.py`'s module docstring telling copiers to validate segments (no separators,
  `..`, or absolute parts, or confirm the target stays under the root).
- Severity assessment: gear itself is safe today (its identifier regex excludes `.`/`/`), but the
  file is the template downstream authors copy; a real module system whose segments admit `..`
  would inherit a path-traversal / arbitrary-file-disclosure primitive without the guard.

## reuse-1
- Disposition: Won't-Do
- Action: no change.
- Severity assessment / rationale: `classify.child_surface` requires a `GrammarTables` argument
  (`fltk/lsp/classify.py:178-183`) that the `ResolverHost` protocol does not expose to a resolver,
  and it computes matcher-oriented fields (resolved rule names for node children) the resolver never
  uses. `gear_resolver.py` is deliberately a standalone downstream *template* (design §4.8/§2.4): a
  real out-of-tree resolver cannot reach into fltk's internal `classify` helpers, so coupling the
  example to them would make it non-representative of what a copier can actually write — active harm
  to the file's stated purpose. The reimplemented helpers are a three-line span/label idiom, not the
  cross-cutting span-vs-node metadata `child_surface` centralizes.

## reuse-2
- Disposition: Fixed
- Action: extracted a module-level `uri_to_path(uri)` in `fltk/lsp/project.py:33-36`;
  `ProjectHost.uri_to_path` delegates to it and `server.py._workspace_root` now calls it instead of
  inlining the `to_fs_path → Path` conversion twice (`fltk/lsp/server.py:_workspace_root`).
- Severity assessment: low — three copies of one conversion in same-round files; consolidating
  prevents a future fix landing in only one.

## reuse-3
- Disposition: Fixed
- Action: added `nth_offset` to the suite's shared `fltk/lsp/conftest.py`; `test_project.py`,
  `test_server_crossfile.py`, and `test_gear_demo.py` now import it and dropped their private
  `_offset`/`_nth`/`_nth_offset` copies.
- Severity assessment: low (test-only) — the three copies had already drifted in signature/docstring.

## quality-1
- Disposition: Fixed (partial; broader refactor deferred)
- Action: extracted `_GoodAnalysis.resolved_document(uri)` (`fltk/lsp/server.py:117-120`), removing
  the verbatim `ResolvedDocument(uri=…, text=good.text, tree=good.tree, symbols=good.symbols)`
  triplication in the two read paths; the rename-guard `type: ignore[union-attr]` is gone (the
  resolver is now called through the navigator, quality-3). The larger `_CrossFileRequest`
  object + unified executor-submission runner is not done: it is a structural refactor with
  regression risk beyond respond scope, and the design roadmap (§7) already plans the next consumer
  (`workspace/symbol`, call hierarchy) as the point to consolidate the shape.
- Severity assessment: maintainability — concrete duplication removed; the parameter-list breadth
  remains but is inert until the next consumer lands.

## quality-2
- Disposition: Fixed (with quality-3)
- Action: the rename verdict is now the `Hazard` enum (`fltk/lsp/project.py:227-237`); the server
  maps hazards through `_RENAME_REFUSALS` where **only `Hazard.NONE` (absent from the map) permits
  the rename** and every other value — plus `None`, the query-failure sentinel — refuses
  (`fltk/lsp/server.py` rename handler + `_RENAME_REFUSALS`). Fail-closed by construction; pyright
  now checks both sides.
- Severity assessment: high-value hardening on the one safety-critical guard — a future stray verdict
  can no longer silently take the permit path.

## quality-3
- Disposition: Fixed (with efficiency-2)
- Action: added `ProjectNavigator.rename_hazard(doc, symbol, offset) -> Hazard`
  (`fltk/lsp/project.py:267-283`) that owns the redirect check and the global scan behind the
  navigator's canonical-target charter; the server guard keeps only the fail-closed try/except and
  message rendering. New unit tests `test_rename_hazard_flags_import_binding` /
  `_flags_cross_file_definition` (`fltk/lsp/test_project.py`).
- Severity assessment: layering — canonical-target semantics no longer split across server and
  navigator, so the roadmap's cross-file rename grows from one place.

## quality-4
- Disposition: Fixed (merged into errhandling-2 above).
- Action: see errhandling-2.
- Severity assessment: see errhandling-2.

## quality-5
- Disposition: Fixed
- Action: `_maybe_warn_no_root(root)` logs one `window/logMessage` (Info) the first time a
  resolver-path request runs with `_workspace_root() is None`, gated by a `_warned_no_root` flag
  (`fltk/lsp/server.py`); called from `definition_crossfile`, `references_crossfile`, and the rename
  guard. (No `initialize` hook exists to attach to, matching the design's lazy-accessor pattern.)
- Severity assessment: a user who opened a bare `.gear` file previously got a silently
  cross-file-inert server; now the limitation is stated in the client log.

## quality-6
- Disposition: Fixed (merged into errhandling-4 above).
- Action: see errhandling-4.
- Severity assessment: see errhandling-4.

## quality-7
- Disposition: Fixed
- Action: dropped the `(M5)` / `M5,` milestone fragments from the `resolver.py` and `project.py`
  module docstrings, keeping "provisional public API" and all substantive content.
- Severity assessment: low — the ephemeral workflow tag would rot; no other `fltk/lsp` module carries
  one.

## efficiency-1
- Disposition: Won't-Do
- Action: no change.
- Severity assessment / rationale: holding one persistent `ProjectHost` across requests is a
  cache-lifecycle change (cross-request memory growth, invalidation) against the design's *deliberate*
  per-request-fresh-host choice (§4.2 `_project` "a fresh ProjectHost for this request's snapshot").
  Design §5 explicitly accepts the O(files) references cost as a documented limitation and §7 names
  `ProjectHost` as the seam a persistent index grows from "when a real consumer's scale demands" —
  and §5 states this class of limitation gets **no `TODO(slug)`** absent concrete evidence (the step4
  §3.2 convention). The version-key machinery is not wasted: it provides within-request reuse (an
  import target also scanned) and is exactly that future seam. Adding persistent-cache state now,
  against an explicit design decision and with no measured need, is premature complexity — the harm a
  Won't-Do guards against.

## efficiency-2
- Disposition: Fixed (with quality-3)
- Action: `rename_hazard` resolves the requesting document once and threads that `resolutions` dict
  into the shared `_references(…, resolutions=…)` helper (`fltk/lsp/project.py:275-283, 285-287`), so
  the requesting doc is no longer resolved twice per rename.
- Severity assessment: minor (the reviewer's own framing); the full-scan cost dominates. Not made to
  early-exit the sorted-occurrence materialization — the common "ok" rename must scan all files
  anyway, so a short-circuit helps only the refusal case, not worth the added mode.

## efficiency-3
- Disposition: Fixed
- Action: the gear resolver memoizes each target module's export map per target URI within one
  `resolve()` call (`examples/gear/gear_resolver.py` `exports_by_uri`), so repeated same-module
  `use` statements do not rebuild it.
- Severity assessment: negligible at runtime; fixed because the file is the reference template whose
  patterns propagate to downstream authors.

## test-1
- Disposition: Fixed
- Action: `test_definition_from_last_good_after_break` (`fltk/lsp/test_server_crossfile.py`) breaks
  the requesting document with a syntax-error `didChange`, then asserts cross-file definition still
  resolves — exercising the `_GoodAnalysis.text`-sourced `ResolvedDocument` construction.
- Severity assessment: guards the version-mixing hazard the `_GoodAnalysis.text` field exists to
  prevent.

## test-2
- Disposition: Fixed
- Action: extended `test_raising_resolver_degrades_references_but_fails_rename_closed` with a
  `_definition` call asserting the definition path also degrades to the local same-file import
  binding (`fltk/lsp/test_server_crossfile.py`).
- Severity assessment: the definition degrade path (and its `features.definition_location`
  same-file fallback) was previously unexercised while the parallel references path was guarded.

## test-3
- Disposition: Fixed
- Action: `test_definition_through_prealias_name` positions the cursor on `Square` inside the `use`
  statement (the pre-alias `NAME`-label binding, not the `Box` alias or a usage site) and asserts it
  navigates to `Square`'s definition (`fltk/lsp/test_server_crossfile.py`).
- Severity assessment: pins the `NAME`-label half of the resolver's `for label in ("NAME","ALIAS")`
  redirect that no prior test touched.

## test-4
- Disposition: Fixed
- Action: `test_unreadable_file_returns_none_and_warns_once` writes invalid UTF-8, asserts
  `document()` is `None`, and asserts the warn-once dedup emits exactly one drained warning across
  two accesses (`fltk/lsp/test_project.py`). Properly covers the errhandling-1 path this round adds.
- Severity assessment: the warn-once `_warned_unreadable` gating was new and easy to invert; now
  pinned.

## test-5
- Disposition: Fixed
- Action: `test_definition_via_workspace_folders` initializes with `workspace_folders` (not
  `root_uri`) and asserts cross-file definition works, exercising `_workspace_root`'s
  `self.workspace.folders` branch (`fltk/lsp/test_server_crossfile.py`).
- Severity assessment: that branch — the one a real VS Code folder session actually uses — was dead
  in the suite; now covered end to end.
</content>
</invoke>
