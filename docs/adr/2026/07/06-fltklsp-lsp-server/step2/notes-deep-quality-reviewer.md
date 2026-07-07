# Deep quality review — round 2 (M2 fltk-lsp pygls server)

Diff reviewed: 9719bab7..d9ab841 (HEAD). Design: `step2/design.md` (frozen).

## quality-1: import-time monkeypatch of pygls private internals is the only thing standing between the server and silent coordinate corruption

`fltk/lsp/server.py:45-59` — `_constrain_pygls_encodings()` assigns
`pygls.capabilities._SUPPORTED_ENCODINGS` (an underscore-private module attribute of a
third-party library) as a side effect of importing `fltk.lsp.server`.

Two distinct problems:

1. **Process-global side effect.** Any *other* pygls server running in the same process
   (a downstream app embedding both fltk-lsp and its own pygls server, or tests) has its
   encoding negotiation silently narrowed just because this module was imported. That is
   action at a distance an importer cannot see or opt out of.
2. **Silent-failure mode when the patch stops sticking.** The dependency pin is
   `pygls>=2,<3` (`pyproject.toml`), so any pygls 2.x.y patch release in a *user's*
   environment may rename/inline the private attribute without any fltk code change or
   fltk CI run. Assignment to a module attribute always succeeds, so the patch becomes a
   silent no-op; pygls then negotiates `utf-8` with clients that offer it, and
   `_encoding()` (`server.py:127-132`) maps *any* non-utf-32 advertised value — including
   `utf-8` — to `UTF16`. Every emitted Range/token position is then wrong for non-ASCII
   documents, with no error anywhere. The design (§4.5) explicitly names "two independent
   decision-makers" as the bug class to rule out; this implementation rules it out only
   as long as a private attribute keeps existing.

**Consequence.** The in-tree e2e test (`test_server.py::test_initialize_utf8_first_...`)
catches the drift only when fltk's own CI runs against the new pygls; deployed servers
resolve the dep independently and corrupt positions silently. And the global mutation is
exactly the kind of workaround that propagates: the next pygls-behavior gap will also be
"just patch the private attr".

**Fix.**
- Make the patch fail loudly instead of silently: assert the attribute exists before
  overwriting (e.g. `getattr(_pygls_capabilities, "_SUPPORTED_ENCODINGS")` raising
  `AttributeError` at import) so an incompatible pygls is a startup crash, not corrupt
  coordinates.
- Make `_encoding()` defensive in the same direction: if the advertised value is neither
  `Utf16` nor `Utf32`, raise / log loudly rather than defaulting to UTF16. That is one
  `if` and converts the worst failure mode (silent corruption) into a visible one.
- Consider narrowing the pygls pin (e.g. `<2.2`) until pygls grows a public injection
  point, and note the private-attr dependency in the code comment so the next bump
  re-verifies it (the comment currently describes the mechanism but not that it rides on
  a private name that must be re-checked per pygls release).

## quality-2: debounced analysis is a fire-and-forget task — exceptions vanish (observability gap)

`fltk/lsp/server.py:242-247` (`schedule_debounced`) creates the debounce task with
`asyncio.ensure_future(self._debounced_analyze(uri))` and stores it only for
cancellation. `_debounced_analyze` → `analyze_and_publish` → `_analyze_blocking` can
raise anything except `RecursionError` (the only exception the engine catches,
`engine.py:152`): a classify bug, an exec'd-parser bug, or `document.source` failing.
Nothing awaits or attaches a done-callback to the task, so the exception surfaces only as
asyncio's GC-time "Task exception was never retrieved" stderr noise — never as a
`window/logMessage`, never as a diagnostic.

**Consequence.** The exact incident this layer will have — "highlighting/diagnostics
stopped updating in my editor" — becomes undiagnosable from the editor's LSP log, which
is the only observability surface an end user of a downstream language has. The rest of
the module is careful about this (the formatting path threads a `logs` list back to the
loop thread precisely to report failures); the push path is the one hole.

**Fix.** Wrap `_debounced_analyze`'s body (after the sleep) in
`try/except Exception: self.window_log_message(... MessageType.Error ...)` — mirroring
the formatting path's policy — or attach a done-callback on the task that logs
non-cancellation exceptions.

## quality-3: formatting-pipeline memoization is one tri-state smeared across four fields

`fltk/lsp/server.py:120-123` — `_fmt_parser`, `_fmt_unparser`, `_fmt_built`,
`_fmt_failed` jointly encode a single tri-state (unbuilt / built / failed-permanently).
The split forces `_format_blocking` to re-establish consistency with runtime asserts
(`server.py:303-304`), and nothing but discipline prevents the illegal states
(`_fmt_built=True, _fmt_parser=None`, or both flags set).

**Consequence.** Every future change to the pipeline (M3/M4 will touch this file) has to
keep four fields coherent; the asserts are a standing admission that the type doesn't.

**Fix.** One field, e.g.
`_fmt_pipeline: tuple[ParserResult, UnparserResult] | _BuildFailed | None`
(sentinel class or `Literal`-tagged), or a tiny frozen dataclass holding
`parser/unparser` with a separate `failed: bool` only if needed. The asserts disappear
and illegal states become unrepresentable.

## quality-4: `drop()` doesn't invalidate in-flight work; `_store`'s `setdefault` resurrects closed-document state

`fltk/lsp/server.py:249-256` (`drop`) cancels the debounce task and pops `_docs` /
`_inflight`, but an analysis already running on the worker (from `didOpen` or a pull
handler) completes afterward and lands in `_store` (`server.py:147-163`), whose
`self._docs.setdefault(uri, _DocState())` recreates the entry for the closed document.
Two effects:

- **State leak**: closed URIs re-accumulate `_DocState` (tree + tokens + encoded tokens)
  that nothing will ever drop again until process exit.
- **Stale-serving across close/reopen**: editors restart version numbers on reopen
  (didOpen version is commonly 0 or 1 again). If the resurrected state carries
  `analyzed_version == 1` and the document is reopened at version 1 with *different*
  text, `_ensure_analyzed`'s `state.analyzed_version == version` short-circuit
  (`server.py:185-190`) serves the pre-close analysis — wrong tree, wrong tokens — to
  pull handlers. The `_GoodAnalysis` snapshot discipline that rules out cross-version
  coordinate mixing *within* a document's life is undone at the close/reopen boundary.

**Consequence.** A rare, timing-dependent wrong-answer bug plus an unbounded (if slow)
leak, in exactly the code whose docstrings advertise "can never mix coordinates from two
versions".

**Fix.** Per-URI generation counter: bump it in `drop()` (and on `didOpen`), capture it
when an analysis is submitted, and have `_store` discard results from an older
generation instead of `setdefault`-ing state back into existence. Alternatively, make
`_store` update only URIs currently present in `_docs` and create the entry explicitly
in the open path.

## quality-5: `start_rule` is duplicated between the engine and the server

The engine already stores the start rule (`engine.py:90`, `self._start_rule`) and uses
it for every analysis parse; `create_server(..., *, start_rule)` threads a second,
independent copy (`server_cli.py:66`, `server.py:112`) used for the formatting parses
(`server.py:305, 316`). The two must agree — analysis and formatting parsing the same
language with different start rules is nonsense — but nothing ties them together except
the CLI happening to pass the same variable twice.

**Consequence.** A second constructor of `create_server` (tests already are one,
`test_server.py:252`; downstream embedders are next) can pass a mismatched pair and get
a server whose diagnostics and formatter disagree about what the document *is*. Classic
redundant-parameter drift.

**Fix.** Add a read-only `start_rule` property to `AnalysisEngine` (one line — the field
already exists) and drop the `create_server`/`FltkLanguageServer` parameter, reading
`engine.start_rule` instead. The design (§4.7) wrote the current signature, but the
surface is pre-release and unshipped; collapsing the duplication now is cheap and
consistent with the design's own single-owner philosophy for the encoding.

## quality-6: `_SERVER_VERSION` hand-duplicates the package version

`fltk/lsp/server.py:38` — `_SERVER_VERSION = "0.2.0"` duplicates `pyproject.toml`'s
`version = "0.2.0"`. The next release bump will not know to touch this constant.

**Consequence.** The server advertises a stale version in `initialize` forever after the
first version bump — precisely the field operators use to check "which server version am
I actually running" when triaging editor issues, so the drift bites during diagnosis.

**Fix.** `importlib.metadata.version("fltk")` (cheap at server construction; fall back to
`"unknown"` on `PackageNotFoundError` for odd dev setups), or drop the version argument
and let pygls omit it.

## quality-7: "round-1" / "this round" workflow references in code comments

Comments in shipped code reference the review-workflow's round structure, which is
ephemeral ADR-process context, not a property of the code:

- `fltk/lsp/engine.py:73` — "``highlight`` is a thin wrapper preserving round-1 behavior"
- `fltk/lsp/engine.py:168` — "preserving round-1 behavior and types exactly"
- `fltk/lsp/features.py:27` — "must set-equal round-1's ``lsp_config.TOKEN_LEGEND``"
- `fltk/lsp/features.py:49-50` — "must set-equal round-1's ``lsp_config.LSP_STANDARD_MODIFIERS``"
- `fltk/lsp/server.py:41` — "Module constant, not configurable this round."
- `fltk/lsp/test_engine_analyze.py:3` — "pinned to remain byte-for-byte what round 1 produced"
- `fltk/lsp/test_features.py:61,66` — `..._set_equal_round1_...` test names

**Consequence.** "Round 1" means nothing to a reader without the `docs/adr/.../step2/`
workflow docs open; these comments rot the moment that context ages out. Round-1 code
already planted a few of these (`lsp_config.py:42,604`, `highlight_cli.py:30`), so the
pattern is actively propagating — each new round adds more.

**Fix.** State the actual contract in code terms: "``highlight`` delegates to ``analyze``
and preserves its original result type and behavior"; "must set-equal
``lsp_config.TOKEN_LEGEND`` (pinned by a test)"; "not configurable" (full stop). Rename
the two tests (`..._set_equal_token_legend`). Optionally sweep the round-1 instances in
the same pass since they're one-word edits.
