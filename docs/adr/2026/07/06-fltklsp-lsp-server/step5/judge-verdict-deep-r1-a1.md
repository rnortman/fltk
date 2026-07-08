# Judge verdict — deep review, round 5 (r1, attempt 1)

Phase: deep. Base `1e920dc`..HEAD `481ba2e` (dispositions reviewed `fe10193`; fixes landed in
`481ba2e`, verified against that commit). Round 1.
Notes: 7 reviewer files; 27 findings (quality-4 merged into errhandling-2, quality-6 into
errhandling-4 by the responder — merges verified as genuine, both underlying complaints addressed).

## Added TODOs walk

### security-2 — TODO(resolver-spec-file-recognition) at `fltk/lsp/resolver.py:_looks_like_path`
Q1 (worth doing): yes — a bare-module spec (`mylang.resolvers`) is exec'd from a same-named cwd
file; editors commonly spawn servers with cwd = workspace root, so a hostile workspace gets
arbitrary Python run at startup for a user with a bare-module resolver config. Real, if narrow (no
shipped config affected; gear/README use explicit `.py` paths).
Q2 (design/owner input required): yes — the fix (drop the bare `is_file()` recognition) directly
contradicts frozen design §4.3, which states "a path is recognized by an existing file or a
`.py`/`/` in the head." Reconciling requires a design delta; the frozen doc cannot be edited in
respond mode.
Mechanics: `TODO(resolver-spec-file-recognition)` comment present in the `_looks_like_path`
docstring with the full hazard and the design-conflict reason; matching `TODO.md` entry present
with slug, description, deferral context, and location. Both halves of the TODO convention
satisfied.
Assessment: TODO acceptable.

## Other findings walk

### errhandling-1 — Fixed
Claim: unreadable workspace file reported only to the module logger (stderr), never the client;
design §4.2 promised a `window/logMessage`.
Evidence: `ProjectHost._warnings` + `drain_warnings()` (`project.py:104-112`); `_source` appends
the unreadable-file message (`project.py:217`); `_drain` helper (`server.py:581-584`) called in all
three blocking methods on both the success and exception paths, so warnings ride the existing
worker→loop logs list. Test `test_unreadable_file_returns_none_and_warns_once` pins document→None,
exactly one warning, and warn-once dedup.
Assessment: fix routes the report through the design's chosen channel. Accept.

### errhandling-2 — Fixed (merged with quality-4)
Claim: resolver-failure catches log `{exc!r}` only; the file's own convention
(`_debounced_analyze`) demands `traceback.format_exc()` because the stack is the only client-side
diagnostic for third-party resolver code.
Evidence: all three catch sites (`_definition_blocking`, `_references_blocking`,
`_rename_guard_blocking`) now log `traceback.format_exc()` — verified in the diff at
`server.py:522-527, 560-565, 600-603`.
Assessment: matches the convention at every site the finding named. Accept.

### errhandling-3 — Fixed (residual disputed — see Disputed items)
Claim: `os.walk` with default `onerror=None` silently drops unreadable subtrees; references
under-report and the rename guard can fail open; "at minimum" the §4.6 fail-closed intent should
be reconciled with the silently-under-reporting scan.
Evidence: `_on_scan_error` callback records the error into the surfaced warnings
(`project.py:128-135`), drained to the client on every cross-file request including the rename
guard. The primary ask (surface the omission) is implemented as specified.
Residual: the guard still *permits* a rename after an incomplete scan — the warning is advisory.
The responder's rationale (the §4.6 "any exception during the global query refuses" mandate vs.
the §4.2/§5 errors-become-`None` policy is a tension the design did not resolve; resolving it
unilaterally would exceed the spec) is substantively fair: refusing on *any* imperfect scan would
also refuse whenever a neighbor file is transiently unparseable — "the normal state" of live
editing per §5 — making rename near-unusable, so the right policy genuinely needs a design cycle.
But that makes this the same shape as security-2: a real residual on the one safety-critical path,
created this round, whose fix needs a design delta — and it received no durable marker (no
TODO(slug), no escalation), only a paragraph in a dispositions doc that will rot.
Assessment: primary fix verified; residual disposition incomplete — needs a TODO (see Disputed).

### errhandling-4 — Fixed (merged with quality-6)
Claim (low confidence, per the reviewer): `path_to_uri` swallows conversion failure into an `""`
sentinel, undocumented.
Evidence: docstring at `project.py:149-157` now documents the sentinel and its degradation
behavior (`document("")` → `None`; copied into `ExternalTarget` → no-op navigation). Not widened
to `-> str | None`: design §4.1 pins the `ResolverHost` protocol signature as
`path_to_uri(self, path: pathlib.Path) -> str` — verified in the frozen doc — so the signature
change the reviewer floated is a protocol change requiring a design delta. The reviewer's own
alternative ("return `""` deliberately, documented") is what landed.
Assessment: proportionate for a low-confidence finding whose stronger fix contradicts the frozen
protocol. Accept.

### correctness-1 — Fixed
Claim: `_instantiate` accepts a `Resolver` *class* as an instance (classes have a `resolve`
attribute), producing the permanently half-working server §4.3 forbids.
Evidence: `not isinstance(obj, type) and hasattr(obj, "resolve")` shortcut; a class falls through
to the callable/factory branch and is instantiated (`resolver.py:_instantiate`, verified in diff
with an explanatory docstring). Test `test_module_attr_class_is_instantiated` pins it.
Assessment: addresses the exact failure at the named site, with the test the reviewer asked for.
Accept.

### correctness-2 — Fixed (fix verified; missing test disputed — see Disputed items)
Claim: all cross-file identity comparisons are raw string equality between client-serialized and
pygls-serialized URIs; on divergent clients (Windows VS Code) the rename guard fails open and
references drop cross-file occurrences.
Evidence: `canonical_uri` (`project.py:45-57`) round-trips through `to_fs_path`→`from_fs_path`,
idempotent, non-file URIs passed through. Applied at every boundary the finding named: `open_docs`
keys canonicalized in `ProjectHost.__init__`, incoming URIs in `_ensure`, and the requesting
`ResolvedDocument` built with `canonical_uri(uri)` in `definition_crossfile`,
`references_crossfile`, and the rename handler. Host-produced URIs (`path_to_uri`,
`workspace_files`, cached documents) are `from_fs_path`-canonical by construction, so both sides
of every comparison (`_source` lookup, `_canonical_identity != target_id`, `_scan_docs` dedup,
guard's `occ_uri != doc.uri`) now collapse to one form. The fix is correct and complete.
Gap: the reviewer's suggested fix explicitly included "Add a test with a deliberately
non-canonical (percent-encoded) client URI." No such test exists (grepped: no canonicalization
test in `test_project.py`/`test_server_crossfile.py`/`test_server.py`). Because `canonical_uri` is
idempotent on the canonical URIs every existing test constructs, the entire suite passes
**with or without this fix** — reverting `canonical_uri` to the identity function would go
undetected. A high-severity fail-open fix with zero pinning coverage, in a TDD project.
Assessment: code fix accepted; disposition incomplete without the test (see Disputed).

### security-1 — Fixed
Claim: `gear.server.command` is workspace-settable argv (published LSP-extension CVE class); no
explicit untrusted-workspace posture.
Evidence: `"scope": "machine"` on the setting and
`"capabilities": {"untrustedWorkspaces": {"supported": false}}` — both verified in the
`package.json` diff, with the markdownDescription explaining why.
Assessment: both one-line fixes the reviewer named, landed. Accept.

### security-3 — Fixed
Claim: the gear resolver (the downstream template) builds filesystem paths from untrusted document
text, safe only by accident of gear's grammar; copies inherit a traversal primitive.
Evidence: `resolve()` now rejects any segment failing `str.isidentifier()` before touching the
filesystem, with a comment explaining the untrusted-text hazard (`gear_resolver.py` diff); a
validate-segments bullet added to `resolver.py`'s resolver-author guidance — both halves of the
suggested fix.
Assessment: template hardened by construction. Accept.

### reuse-1 — Won't-Do
Claim: `gear_resolver.py` reimplements span/label decoding that `classify.child_surface`
centralizes.
Rationale check: `child_surface(label, child, text, tables)` requires a `GrammarTables` argument
(verified at `classify.py:178-183`) that the `ResolverHost` protocol does not provide — a resolver
receives only `(doc, host)` (design §4.1) and genuinely cannot call it. Moreover design §4.8/§2.4
bill the file as the standalone worked example downstream authors copy; coupling it to fltk's
internal classify helper would make the template unrepresentative of what an out-of-tree resolver
can write. The reimplemented portion is a three-line span/label idiom, not the matcher-dispatch
surface `child_surface` exists to share.
Assessment: the finding's premise (an existing usable utility) fails against the protocol's actual
surface, and the Won't-Do argues active harm to the file's designed purpose. Accept.

### reuse-2 — Fixed
Claim: `_workspace_root` inlines the `to_fs_path`→`Path` conversion twice while `project.py`
extracts the same thing.
Evidence: module-level `uri_to_path` (`project.py:39-42`); `ProjectHost.uri_to_path` delegates;
`server.py:_workspace_root` calls it for both branches (verified in diff; `pygls.uris` import
dropped from server.py).
Assessment: one copy remains. Accept.

### reuse-3 — Fixed
Claim: three byte-identical Nth-occurrence-offset helpers across three new test modules.
Evidence: `nth_offset` added to `fltk/lsp/conftest.py` (the suite's established shared-helper
home); all three modules import it and their private copies are deleted (verified in diff).
Assessment: accept.

### quality-1 — Fixed (partial); deferral accepted
Claim: six-param threading and a triplicated `ResolvedDocument`-from-`_GoodAnalysis` preamble
across the cross-file entry points; a `_CrossFileRequest` + unified runner suggested.
Evidence: `_GoodAnalysis.resolved_document(uri)` (`server.py:117-120`) removes the verbatim
triplication at all three sites; the rename guard's `type: ignore[union-attr]` is gone (resolver
now reached through `navigator.rename_hazard`, per quality-3). The larger request-object refactor
is deferred with a real argument: the design roadmap (§7) plans the next consumers
(`workspace/symbol`, call hierarchy) as the natural consolidation point, and shaping the
abstraction before a third consumer exists is a legitimate premature-abstraction concern, not a
dodge — the concrete duplication (the part that can silently drift) is what was removed.
Assessment: the load-bearing portion is fixed; the deferred portion is a structure judgment the
roadmap already earmarks. Accept.

### quality-2 — Fixed (with quality-3)
Claim: stringly-typed rename verdict fails **open** on any unrecognized value — inverted from the
§4.6 fail-closed mandate.
Evidence: `Hazard` enum (`project.py:227-237`); server consumes via `_RENAME_REFUSALS` where only
`Hazard.NONE` is absent from the map and `None` (query failure) is an explicit refusing key
(`server.py:572-578`, rename handler diff) — an unmapped future value refuses by construction.
Exactly the inversion the reviewer prescribed.
Assessment: fail-closed by construction, pyright-checkable. Accept.

### quality-3 — Fixed (with efficiency-2)
Claim: the rename guard reaches around `ProjectNavigator` to call the resolver directly, splitting
canonical-target semantics across layers.
Evidence: `ProjectNavigator.rename_hazard(doc, symbol, offset) -> Hazard`
(`project.py:267-283`) owns the redirect check and global scan; the server guard keeps only the
fail-closed try/except and message rendering. Unit tests `test_rename_hazard_flags_import_binding`
/ `_flags_cross_file_definition` added.
Assessment: matches the suggested fix including the enum shape. Accept.

### quality-4 — Fixed (merged into errhandling-2)
Same complaint (traceback omission), same three sites; see errhandling-2. Accept.

### quality-5 — Fixed
Claim: no-workspace-root degradation completely silent; design §5 promised "logged once at
initialize."
Evidence: `_maybe_warn_no_root` + `_warned_no_root` flag (`server.py:413-425, 189-191`), called
from `definition_crossfile`, `references_crossfile`, and the rename handler — one Info
`window/logMessage` at first resolver-path use. First-use rather than initialize-time is the
reviewer's own suggested mechanism ("since there is no initialize hook to attach to").
Assessment: accept.

### quality-6 — Fixed (merged into errhandling-4)
See errhandling-4. Accept.

### quality-7 — Fixed
Claim: ephemeral "(M5)" milestone tags in module docstrings.
Evidence: dropped from both `resolver.py` and `project.py` docstrings; "provisional public API"
retained (verified in diff).
Assessment: accept.

### efficiency-1 — Won't-Do
Claim: `ProjectHost` rebuilt per request discards its analysis cache; every find-references
re-parses the workspace; the version-key machinery's cross-request benefit never lands.
Rationale check against the design: §4.1 records the no-resolution-cache/per-request recompute
policy as a deliberate, documented limitation ("Definition/references are user-action-rate...
revisit on evidence — the ProjectHost cache is where an index would grow"); §4.2's threading model
hands the open-docs snapshot to the host at construction per submit; §5 accepts the O(files)
references cost and explicitly prescribes **no `TODO(slug)`** absent concrete evidence (step4 §3.2
convention); §7 names `ProjectHost` as the seam to grow "when a real consumer's scale demands."
The reviewer's distinction (retaining the existing cache ≠ a persistent index) has technical
merit — the version-key validation would make cross-request reuse safe — but a cross-request host
is a lifecycle change (retention, growth, snapshot re-pointing) the design deliberately did not
take, with zero measured need at demo scale. The Won't-Do argues the active harm (premature
complexity against an explicit design posture) rather than mere out-of-scope.
Assessment: design-consistent; the design even forbids the speculative TODO. Accept.

### efficiency-2 — Fixed (with quality-3)
Claim (reviewer's own framing: minor): rename guard double-resolves the requesting document and
materializes the full sorted occurrence set for a boolean.
Evidence: `rename_hazard` resolves once and threads the shared `resolutions` dict into
`_references(..., resolutions=...)` (`project.py:275-283`) — double-resolve gone. The early-exit
mode was declined with a sound reason: the common "ok" rename must scan every file anyway to prove
absence, so a short-circuit helps only refusals; not worth a second query mode.
Assessment: the real redundancy fixed; the declined half is correctly reasoned. Accept.

### test-1 — Fixed
Evidence: `test_definition_from_last_good_after_break` breaks the requesting doc via a
syntax-error `didChange` then asserts cross-file definition still resolves from last-good —
exactly the `_GoodAnalysis.text` version-mixing scenario the finding named (verified in diff).
Accept.

### test-2 — Fixed
Evidence: `test_raising_resolver_degrades_references_but_fails_rename_closed` extended with a
`_definition` call asserting same-file fallback to the local import binding, exercising
`features.definition_location` from the degrade path (verified in diff). Accept.

### test-3 — Fixed
Evidence: `test_definition_through_prealias_name` cursors on `Square` inside the `use` statement
(occurrence 0 — the `NAME`-label binding) and asserts navigation to the cross-file definition,
pinning the previously untouched half of the `("NAME", "ALIAS")` redirect loop (verified in diff).
Accept.

### test-4 — Fixed
Evidence: `test_unreadable_file_returns_none_and_warns_once` writes invalid UTF-8, asserts
`document()` → `None`, exactly one drained warning, and no re-emission on second access —
covering the warn-once dedup via the errhandling-1 mechanism (stronger than the caplog approach
the reviewer sketched, since it pins the client-visible channel). Accept.

### test-5 — Fixed
Evidence: `test_definition_via_workspace_folders` initializes with `workspace_folders` (no
`root_uri`) and asserts end-to-end cross-file definition, covering `_workspace_root`'s previously
dead `workspace.folders` branch (verified in diff). Accept.

## Disputed items

- **correctness-2 — add the non-canonical-URI test.** The fix is correct but invisible to the
  suite: `canonical_uri` is idempotent on the canonical URIs every existing test constructs, so
  reverting it to the identity function keeps all 2971 tests green while silently reopening the
  fail-open rename-guard hazard the fix closes. Concrete fix, mechanical on Linux: (a) a
  `test_project.py` unit test constructing `ProjectHost` with `open_docs` keyed by a deliberately
  percent-encoded spelling (e.g. encode one letter of the filename) and asserting
  `host.document(<canonical form>)` serves the open-buffer text; and/or (b) a navigator-level test
  where the requesting `ResolvedDocument.uri` is passed through `canonical_uri` from a
  non-canonical spelling and `rename_hazard`/`references` identity still matches. Either pins the
  fix; the reviewer's suggested fix explicitly asked for this and the project protocol is TDD.

- **errhandling-3 residual — durable marker for the guard-vs-incomplete-scan policy.** The
  surfacing fix is accepted; leaving the §4.6-vs-§5 reconciliation *only* in the dispositions doc
  is not. This round created the rename guard, and its behavior on an incomplete scan (walk error,
  unreadable or unparseable neighbor) is fail-open-with-a-warning — a policy the design did not
  decide and that genuinely needs a design cycle (refusing on any imperfect scan would gut rename
  during live editing; permitting weakens the one fail-closed path). That is precisely the shape
  security-2 correctly handled with a TODO. Concrete fix: add a `TODO(slug)` (e.g.
  `TODO(rename-guard-incomplete-scan)`) at `ProjectNavigator.rename_hazard` or the guard's
  `workspace_files` consumption, plus the matching `TODO.md` entry recording the tension and that
  resolving it needs a design delta. No behavior change required this round.

## Approved

25 of 27 findings fully resolved: 22 Fixed verified (including two merged pairs and one accepted
partial), 2 Won't-Do sound (reuse-1, efficiency-1 — both design-backed, premises verified against
code and the frozen doc), 1 TODO acceptable (security-2, rubric passed). The three
frozen-design-conflict dispositions the orchestrator flagged (security-2 TODO, reuse-1 and
efficiency-1 Won't-Do) all check out against the design's actual text — none is a dodge.

---

## Verdict: REWORK

Two dispositions incomplete (correctness-2 missing its pinning test; errhandling-3's residual
design tension needs a TODO), both cheap and concrete. Round 1.
