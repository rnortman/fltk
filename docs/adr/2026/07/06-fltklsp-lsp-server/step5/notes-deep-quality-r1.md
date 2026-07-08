# Deep review — quality (round 5, r1)

Reviewed: `1e920dc..fe10193` (HEAD fe10193). Scope: resolver plugin API, `ProjectHost`/`ProjectNavigator`, server cross-file wiring, gear demo, VS Code extension.

Overall shape is good: layering (resolver protocol / project layer / server rendering) matches the design, the logs-list-returned-from-worker pattern is applied consistently, and the gear resolver is a genuinely readable reference implementation. Findings below are about the cross-file server path's duplication, one fail-open string protocol, and observability gaps.

---

## quality-1: Cross-file request path — parameter sprawl and triplicated preamble

**Where:** `fltk/lsp/server.py:486-635` (`_definition_blocking`, `_references_blocking`, `definition_crossfile`, `references_crossfile`), plus the rename guard at `server.py:689-695`.

**Issue:** The same request context is threaded as loose parameters through every cross-file entry point: `(doc, offset, requesting_line_index, enc, open_docs, root)` — six positional/keyword params per blocking method. The async wrappers duplicate an identical preamble three times: `_serveable_for` → offset compute → `ResolvedDocument(uri=..., text=good.text, tree=good.tree, symbols=good.symbols)` → `_open_docs_snapshot()` → `_workspace_root()` → `run_in_executor` → log flush → degraded fallback. The `ResolvedDocument`-from-`_GoodAnalysis` construction appears verbatim three times (lines 591, 613, 689). The two executor submissions are even inconsistent in style — positional args for definition, a `lambda` for references (forced by the keyword-only params, which is itself a symptom). And resolver presence is re-proven two different ways (`assert self._resolver is not None` in `_project`, `# type: ignore[union-attr]` in `_rename_guard_blocking`).

**Consequence:** The roadmap explicitly plans more consumers of exactly this shape (`workspace/symbol`, call hierarchy, cross-file rename — design §1, §7). Each will copy the six-param signature and the eight-line preamble again; a change to the snapshot policy (e.g. adding `didChangeWatchedFiles` state) then has to be applied in N places, and the loop-thread-snapshot discipline the comments carefully document is re-implemented, not enforced, at each call site.

**Fix:** Introduce a small frozen `_CrossFileRequest` (or similar) built once on the loop thread — `doc: ResolvedDocument, line_index: LineIndex, enc: PositionEncoding, open_docs: ..., root: ...` — with a helper on `_GoodAnalysis` (or a module function) for the `ResolvedDocument` construction, and a single `await self._run_crossfile(request, blocking_fn)` that owns executor submission + log flushing. Blocking methods then take `(request, offset, ...)`. Pass the non-None resolver into the context to eliminate both the `assert` and the `type: ignore`.

---

## quality-2: Rename-guard verdict is stringly typed and fails **open** on an unrecognized value

**Where:** `fltk/lsp/server.py:554-582` (`_rename_guard_blocking` returns `tuple[str, ...]`), consumed at `server.py:698-706`.

**Issue:** The guard's verdict is a raw `str` in {`"ok"`, `"cross_file"`, `"import_binding"`, `"error"`} with return type just `str`. The consumer checks the three failure strings with `if verdict == ...` and otherwise **proceeds with the rename**. So any drift — a typo in a future edit, a new verdict value added on the producer side but not the consumer — silently takes the "ok" path. That is exactly inverted from the fail-closed policy this guard exists to implement (design §4.6: "any exception during its global query refuses the rename"); the failure mode of the code's own protocol is fail-open.

**Consequence:** The one place in the round where the design demands fail-closed is guarded by string comparisons pyright cannot check. A future refactor (e.g. adding a `"shadowed"` verdict for cross-file rename) breaks silently by permitting the rename it meant to refuse.

**Fix:** Make the verdict an `enum.Enum` (or at minimum `Literal["ok", "cross_file", "import_binding", "error"]` so pyright checks both sides), and invert the consumer: map verdict → refusal message in a dict; only an explicit `OK` proceeds, anything else raises. That is fail-closed by construction and collapses the three `if` blocks.

---

## quality-3: Rename guard reaches around `ProjectNavigator` to call the resolver directly

**Where:** `fltk/lsp/server.py:571-574` (`self._resolver.resolve(doc, host)` then `navigator.references(...)`).

**Issue:** Everywhere else, the navigator is the sole owner of canonical-target semantics (redirect-or-local, selection-range-only identity — `project.py` docstrings make this its charter). The rename guard is the one caller that goes behind it: it invokes `resolver.resolve()` directly to check `symbol_targets.get(symbol)`, then calls `navigator.references(doc, offset, ...)` — which re-resolves the same document from scratch (fresh `resolutions` dict) and re-derives the symbol from the offset the server already resolved to a `Symbol`. The import-binding rule ("a redirected symbol must not be renamed") is canonical-target knowledge, but it now lives in the server layer.

**Consequence:** Guard semantics are split across two layers: if the redirect/identity rules evolve (e.g. multi-hop chains, or the roadmap's cross-file rename which the design says will grow out of exactly this query), the server-side half is easy to miss. The doc is also resolved twice per guard — harmless today, but it's the pattern that propagates.

**Fix:** Add a navigator method, e.g. `rename_hazard(doc, symbol, offset) -> Hazard` (enum: `NONE | IMPORT_BINDING | CROSS_FILE`), performing the redirect check and the global scan with one shared `resolutions` dict. The server keeps only the fail-closed try/except and message rendering.

---

## quality-4: Resolver-failure logs omit the traceback the project's own convention says is essential

**Where:** `fltk/lsp/server.py:506-509, 539-542, 575-576` — all three resolver catch sites log `f"...: {exc!r}"`.

**Issue:** `_debounced_analyze` (server.py:373-382) established the convention *with a rationale in the comment*: failures surfaced only through `window/logMessage` must carry `traceback.format_exc()`, because "the stack is the only way to tell which stage broke from the client's server log alone." A resolver exception is the strongest case for that rule: the failing code is a third-party plugin the fltk authors have never seen, running under an editor where the client log is the only diagnostic channel. `RuntimeError('...')` with no stack tells a downstream resolver author nothing about which line of *their* code failed.

**Consequence:** The design names clockwork's resolver as the next consumer (§7). Its author's first resolver bug produces an unactionable one-line log; the debugging path becomes "add prints to the plugin and restart the editor" — precisely the incident-time gap the existing convention exists to prevent.

**Fix:** Include `traceback.format_exc()` in the three resolver-failure messages (or a shared `_resolver_failure_log(feature: str) -> tuple[...]` helper, which also unifies the three near-identical message strings).

---

## quality-5: "No workspace root" degradation is completely silent

**Where:** `fltk/lsp/server.py:443-460` (`_workspace_root`), `fltk/lsp/project.py:88-90` (`workspace_files` returns `()`).

**Issue:** When the client provides no workspace root, find-references silently shrinks to same-file, and the gear resolver returns empty resolutions (gear_resolver.py:60-63) — go-to-def through imports silently stops working. Nothing is logged anywhere. Design §5 explicitly promised "Logged once at initialize" for this case; there is no initialize hook and no log at first use either.

**Consequence:** A user who opens a single `.gear` file (no folder) gets a server that looks configured (resolver loaded, no error) but never navigates cross-file, with zero evidence in the client log. This is the classic "works on my machine" support incident, and it will be the first thing a downstream language's users hit.

**Fix:** Log one `window/logMessage` (Warning/Info) the first time a resolver-path request runs with `_workspace_root() is None` — e.g. a `_warned_no_root` flag on the server — since there is no initialize hook to attach to. Message should say cross-file navigation is degraded and why.

---

## quality-6: `ProjectHost.path_to_uri` swallows failure into an `""` sentinel

**Where:** `fltk/lsp/project.py:112-113`: `return uris.from_fs_path(str(path)) or ""`.

**Issue:** When pygls cannot form a URI, the method silently returns the empty string, which then flows into `host.document("")` (returns `None` after a failed round-trip) or into an `ExternalTarget.uri` a resolver builds — producing a no-match with no signal, and an empty-string key in caches/identity tuples.

**Consequence:** A resolver author on an odd platform/path gets "navigation just doesn't work" with nothing to grep for; `""` as a URI is the kind of sentinel that later gets compared or stored somewhere it shouldn't.

**Fix:** Either log once and return `""` deliberately (documented), or better: since the `ResolverHost` protocol is still provisional, make it `-> str | None` to match `uri_to_path`'s honest signature, and have the one in-repo caller (`workspace_files`) skip `None`.

---

## quality-7: Milestone tags in module docstrings

**Where:** `fltk/lsp/resolver.py:1` ("(M5, **provisional public API**)"), `fltk/lsp/project.py:1` ("(M5)").

**Issue:** "M5" is a workflow-milestone label from the ADR planning docs; no other `fltk/lsp` module carries one (engine.py, features.py, server.py, symbols.py are all milestone-free). The *provisional* label is design-mandated and should stay; the milestone number is ephemeral workflow vocabulary that means nothing once the ADR round is history.

**Consequence:** Docstrings that point at workflow artifacts rot: a reader two years out has no "M5" to consult, and the tag invites the next round to keep numbering modules.

**Fix:** Drop the "(M5)"/"M5," fragments; keep "provisional public API" and the substantive docstring content unchanged.

---

No workaround-for-existing-bug patterns found: the `_GoodAnalysis.text` addition fixes the real gap (last-good text previously survived only as `LineIndex._text`) rather than reaching into the private field, which is the right direct fix.
