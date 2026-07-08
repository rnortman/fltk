# Deep review — error handling — round 5 (resolver API, gear demo, VS Code wiring)

Commit reviewed: fe10193 (base 1e920dc)
Scope: error observability and response only.

Files examined: fltk/lsp/resolver.py, fltk/lsp/project.py, fltk/lsp/server.py (diff),
fltk/lsp/features.py (diff), fltk/lsp/server_cli.py (diff), examples/gear/gear_resolver.py,
fltk/lsp/engine.py (surrounding context).

---

## errhandling-1

**File:** fltk/lsp/project.py:163-169 (`ProjectHost._source`)

**Broken error path:** An unreadable or non-UTF-8 workspace file is reported only via the
module logger — `_LOGGER.warning("fltk-lsp: could not read workspace file %s ...")` — and the
function returns `None`. The design (§4.2: "errors surfaced as `None` (plus one
`window/logMessage`)", §5 "Import target missing/unparsable ... Logged") promised a
client-visible `window/logMessage`. ProjectHost runs on the analysis worker and does not
participate in the `logs: list[(MessageType, str)]` return-and-emit pattern that every other
worker-side path in server.py uses (`_definition_blocking`, `_references_blocking`,
`_rename_guard_blocking` all collect logs and the loop emits them via `window_log_message`).
The warning therefore never reaches the LSP client's server-log channel — it lands only on the
process's Python `logging` (stderr), which an editor user typically never opens.

**Consequence:** A cross-file go-to-def or find-references silently omits a neighbor file whose
encoding is not UTF-8 (or that is transiently unreadable). The editor shows an incomplete or
empty result identical to "no references there." Neither the user nor on-call gets any
editor-visible signal that a file was skipped for an *encoding/IO* reason (as opposed to a
genuine absence of references), so the failure is undiagnosable from the client side — exactly
the channel the design chose to route it to.

**What must change:** Route the unreadable-file report through the same worker→loop logs list
the sibling blocking methods use so it is emitted as a `window/logMessage`, matching the design
and the surrounding convention. (Keeping the module-logger line in addition is fine.)

---

## errhandling-2

**File:** fltk/lsp/server.py:479-483 and 512-516 (`_definition_blocking`, `_references_blocking`
resolver-failure catch)

**Broken error path:** When the resolver raises, the catch logs
`f"...resolver failed during definition; using same-file: {exc!r}"` — the exception *repr*
only, no traceback. The established precedent in this same file for logging a caught worker/task
exception is a full stack: `_debounced_analyze` (server.py:372-382) logs
`traceback.format_exc()` with an explicit comment that "the stack is the only way to tell which
stage broke from the client's server log alone." Resolvers are third-party downstream code
(the whole point of the plugin API), so a failure repr like `KeyError('NAME')` gives on-call
neither the file nor the line inside the resolver that threw.

**Consequence:** A downstream resolver bug degrades navigation to same-file (correct response),
but the only diagnostic emitted is the exception type + message. Whoever maintains the resolver
cannot locate the failing call site from the server log — they must reproduce locally. The
degrade is silent-enough that a systematically-broken resolver (every request degrades) looks
like "cross-file just doesn't work" rather than "the resolver is throwing here."

**What must change:** Log `traceback.format_exc()` (as `_debounced_analyze` does) instead of, or
in addition to, `{exc!r}`, in all three resolver-failure/`error`-verdict catches
(`_definition_blocking`, `_references_blocking`, `_rename_guard_blocking`).

---

## errhandling-3

**File:** fltk/lsp/project.py:89-100 (`ProjectHost.workspace_files`)

**Broken error path:** `os.walk(self._root_path)` is called with the default `onerror=None`,
which silently swallows any `OSError` raised while scanning (unreadable subdirectory, permission
denied, vanished directory mid-walk). Such a subtree simply produces no entries. A nonexistent
root likewise yields an empty walk with no signal. The find-references aggregation
(`ProjectNavigator.references` → `_scan_docs`) then quietly omits every match under the
unscanned subtree.

**Consequence:** find-references silently returns an incomplete result set on a workspace with a
permission-restricted or transiently-unreadable subdirectory — indistinguishable from "no
references exist there." For a feature whose contract is *workspace-wide* references (and which
the rename guard at server.py:685-706 relies on to decide cross-file safety), a silently-skipped
subtree means the rename guard can fail *open* — it can conclude "no cross-file references" and
allow a rename that actually breaks files in the unscanned subtree. On-call sees a corrupted
cross-file rename with no log explaining that a subtree was unreadable.

**What must change:** Pass an `onerror` callback to `os.walk` that records the scan error into
the surfaced logs (per errhandling-1's mechanism), so an unreadable subtree is at least reported
rather than silently dropped. At minimum, the rename guard's fail-closed intent (§4.6) should be
reconciled with the fact that its underlying scan can silently under-report.

---

## errhandling-4 (low confidence)

**File:** fltk/lsp/project.py:109-110 (`ProjectHost.path_to_uri`)

**Broken error path:** `return uris.from_fs_path(str(path)) or ""` converts a failed path→URI
conversion (falsy return from `from_fs_path`) into the empty string, which is then treated as a
valid URI by callers (cache key in `_source`, `target_uri` in gear_resolver.py:77, and any
resolver author's `ExternalTarget.uri`). The error is swallowed into a sentinel that is
syntactically a URI but addresses nothing.

**Consequence:** A path that cannot be represented as a `file:` URI yields `uri=""`. In the gear
resolver this happens to degrade cleanly (`host.document("")` returns `None`), but a resolver
author who builds an `ExternalTarget(uri="", ...)` gets a go-to-def `Location` with an empty URI
that the client cannot open — a silently-broken navigation with no log. This is a public
`ResolverHost` method resolvers are told to use; its swallow-to-sentinel behavior is undocumented
in the docstring ("The `file:` URI for a filesystem path").

**What must change:** Either return `str | None` and document the `None` case, or log when
`from_fs_path` fails rather than emitting `""`. Low confidence because in practice resolvers pass
absolute paths for which `from_fs_path` does not fail.
