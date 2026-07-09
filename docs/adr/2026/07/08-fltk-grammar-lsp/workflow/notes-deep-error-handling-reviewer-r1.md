# Deep error-handling review — r1

Commit reviewed: 0e6b0c5096e6b8f7b0211da2f905143d49181aa3 (base 9473bf9)
Scope: error observability and response in the changed code (grammar_cli.py, server_cli.py refactor, extension.js). Grammar/format sidecar files are declarative specs with no error-handling surface; tests are out of lane.

## errhandling-1

- File:line: `editors/vscode/extension.js:54-55` (`startClient`).
- Broken error path: `clients.set(languageId, client); client.start();` — the Promise returned by `client.start()` is neither awaited nor `.catch()`-ed, and the client is inserted into the `clients` map *before* start is attempted. The only re-entry guard is `if (clients.has(languageId)) return;` at line 33.
- Why: In vscode-languageclient the `start()` promise rejects when the server process fails to launch (uv missing, wrong `fltk.grammars.server.command`, pygls-less env exiting before I/O, transient contention — the design's own "Bazel lock contention / slow first launch" cases). That rejection is dropped (unhandled promise rejection). Because the failed client is already cached, `maybeStart` / `onDidOpenTextDocument` can never retry it for the rest of the session.
- Consequence: A failed or transient server launch silently yields *no* highlighting/diagnostics/formatting for that language for the whole session, with no user-visible signal at the editing surface and no automatic retry. The error is only discoverable if the user manually opens the language server's output channel. On-call/user cannot tell "server crashed on startup" from "extension didn't activate" without digging. The lazy-start optimization turns a one-time transient failure into a persistent dead language.
- What must change: Attach a rejection handler to `client.start()` that (a) surfaces the failure to the user (e.g. `window.showErrorMessage` / at minimum a logged, findable message) and (b) removes the client from `clients` on failure so a subsequent document-open can retry, rather than caching a permanently-dead client. At minimum, do not insert into `clients` until start resolves, and log the rejection.

## errhandling-2 (minor / already mitigated — noted for completeness)

- File:line: `fltk/lsp/grammar_cli.py:88` (`BUILTIN_LANGUAGES[language.value]`).
- Broken error path: Two parallel structures (`Language` enum and `BUILTIN_LANGUAGES` dict) must stay coupled; a subscript with no guard would raise a bare `KeyError` if an enum member had no dict entry. With `pretty_exceptions_enable=False` that surfaces as a raw traceback, not the clean fail-fast message the rest of the CLI gives.
- Why / consequence: This is a developer-invariant, not a runtime input path — Typer restricts `language` to enum values, and the values are literally the dict keys defined adjacently. The drift risk is real but is explicitly guarded by `test_language_enum_matches_registry` (test_grammar_lsp.py:75), which asserts the enum value set equals the registry key set. So the invariant is enforced at CI time and cannot ship broken. No change required; recorded only because it is a keyed-lookup-on-coupled-structures pattern.

## Non-findings verified

- `server_cli.serve` refactor: the `(ValueError, OSError)` fail-fast handler and the lazy-pygls `ImportError` handler are preserved verbatim from the original `main`; behavior of `fltk-lsp` is unchanged and both produce clean stderr + non-zero exit. Correct expected-bad-input handling.
- `grammar_cli.resolve_paths`: `assert grammar is not None` is a pure type-narrowing invariant assertion (materialize of a non-None name always returns non-None); safe even if stripped under `-O`. Missing packaged sidecars on a normal install fall through to `AnalysisEngine.from_paths` → OSError → clean handling; a missing resource is a shipped-package (release) bug guarded by the registry-integrity test. `ExitStack` correctly outlives `server.start_io()` and unwinds on `typer.Exit`.
- test teardown `contextlib.suppress(Exception)` (test_grammar_lsp.py) is justified and scoped to shutdown teardown — appropriate, and test code is out of lane regardless.
