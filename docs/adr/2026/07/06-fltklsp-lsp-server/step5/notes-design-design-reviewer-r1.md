# Design review findings — step5 round 1 (design-reviewer)

Verification basis: design.md and exploration.md checked against code at HEAD b1bd373
(`server.py`, `symbols.py`, `features.py`, `classify.py`, `positions.py`, `server_cli.py`,
`pyproject.toml`) and the step1–4 design docs. The load-bearing citations all check out:
`symbols.py:262-274` (`_resolve`), `server.py:671-692` (definition/references handlers),
`server.py:409-423` (capability captures), `create_server` signature, the four
server-defined legend types (`punctuation`/`text`/`constant`/`label`,
`features.py:35-52`, matching the step1 §4.5 caveat quoted in §4.9), keyword/operator
default paint from literal provenance (`classify.py:116-121` — so the gear `.fltklsp`
sketch's omission of keyword/operator scopes is fine), `LineIndex` clamping (step2 §4.5,
`positions.py`), the step3 §7 resolver-seam quote, the step4 completeness-beats-freshness
policy and `_analyze_blocking` snapshot pattern, and the clockwork `use` shape.
`Reference`/`Symbol` are frozen (hashable) as §4.1 requires. Requirements coverage: every
item in the requester's brief (comments/trivia, strings, types, statements, keywords,
operators; formatting; cross-file def/refs; multi-file imports; non-real extension;
automated tests; manual VS Code acceptance; Rust punt) maps to a design section.

Findings below.

---

## design-1 — The default `uv` launch command will not have pygls; the server exits 1 at startup

**Section**: §4.9 (`extension.js` "builds the default command
`uv --project <repo> run fltk-lsp --grammar ...`"), §4.10 step 1, and §6's claim that
"the exact command line it launches is the one `test_server_crossfile` drives".

**What's wrong**: `pygls` is only reachable via the `lsp` optional extra
(`pyproject.toml:27-28`) or transitively via `pytest-lsp` in the `test` dependency group
(`pyproject.toml:44-50`). `uv run` syncs the project plus default groups only (`dev`,
which here contains just maturin — `pyproject.toml:45`); it does not enable extras. So on
a fresh checkout, `uv --project <repo> run fltk-lsp ...` produces an environment without
pygls, and `server_cli.py:44-48` prints "fltk-lsp requires the 'lsp' extra" and exits 1.
It may *appear* to work on the requester's dev machine only because the venv already has
pygls from test-group syncs — exactly the environment-dependent trap.

Compounding it, §6's coverage claim is overstated: the established harness convention
launches `[sys.executable, "-m", "fltk.lsp.server_cli", ...]` (exploration §5.2,
`test_server.py:35-49`), not `uv ... run fltk-lsp`. The server *arguments* are pinned by
`test_server_crossfile.py`; the uv launcher layer — the part that is broken here — is
precisely what no automated test exercises.

**Consequence**: the round's headline acceptance criterion ("runnable from local repo with
`uv` in a way that lets me actually configure my vscode instance here to use it") fails at
step 1 of the §4.10 checklist in any clean environment, with a confusing silent-exit in
the VS Code output panel, and no automated test can catch it.

**Suggested fix**: default command `uv --project <repo> run --extra lsp fltk-lsp ...` (or
add pygls to a default dependency group). The README prerequisite list should also state
the Rust toolchain requirement (CLAUDE.md: without Rust, `uv run` cannot build the
package) and warn that the first launch pays the maturin build. Reword the §6 claim to
"the argument vector, not the launcher, is pinned".

## design-2 — `ResolvedDocument.text` for the requesting document has no source on the last-good path

**Section**: §4.5 ("the requesting document serves from current-or-last-good exactly as
today") together with §4.1 (`ResolvedDocument.text: str`) and §4.8 (the gear resolver
walks `doc.tree`'s `use_stmt` nodes — reading module-path segment names requires slicing
`doc.text` by span).

**What's wrong**: when the requesting document is currently broken, the navigator's
`ResolvedDocument` must be built from `last_good` — but `_GoodAnalysis` stores
`version/line_index/tree/segments/symbols` and **no text** (`server.py:93-107`). The only
copy of the last-good text in the process is the private `LineIndex._text`
(`positions.py:37`), which the design nowhere licenses reaching into. `ProjectHost.document(uri)`
is not a substitute: it analyzes the *current* buffer text and returns `None` for a broken
document (§4.1), contradicting the stated stale-serving policy. The design specifies the
policy but not the mechanism, and the obvious implementer shortcut — pairing the live
buffer text with the last-good tree — mixes document versions: span slices read garbage
module paths, or raise on a shrunken document.

**Consequence**: either cross-file navigation silently breaks exactly during the
edit-with-errors state the stale-serving policy exists for, or a version-mixing bug of the
class `_GoodAnalysis`'s own docstring ("can never mix coordinates from two versions") was
built to rule out.

**Suggested fix**: add `text: str` to `_GoodAnalysis` (one string per open document —
module-private, no public-surface impact), and state that the navigator's requesting-side
`ResolvedDocument` is built from the `_GoodAnalysis` snapshot wholesale.

## design-3 — The rename refusal guard fails open under the blanket resolver-exception policy

**Section**: §4.5 ("Resolver exceptions anywhere in these paths: caught…, degraded to the
same-file answer") applied to §4.6 (the refusal guard "run[s] the global-references
query").

**What's wrong**: for definition/references, degrade-to-same-file is the right disposition.
For the rename guard it inverts the safety property: the guard's whole purpose (§2.3) is
"rename can never silently break other files", but if the resolver (or a workspace-file
analysis inside the global query) raises and the path degrades to the same-file answer,
the guard sees zero cross-file occurrences and **lets the rename proceed**. The design
never distinguishes the two dispositions; "anywhere in these paths" reads as covering
§4.6, whose handler runs on the same worker job.

**Consequence**: a buggy or transiently-failing resolver converts the refusal guard into a
no-op, and a same-file rename of a cross-file-referenced symbol silently corrupts the
project — the exact hazard §2.3 names, now reachable through the error path.

**Suggested fix**: state explicitly that the rename guard fails **closed**: any exception
during the guard's global query refuses the rename with an explanatory error ("cannot
verify cross-file references"), while definition/references keep the degrade-to-same-file
disposition.

## design-4 — "the open-buffer snapshots it needs" cannot be known at submit time; the snapshot rule is underspecified

**Section**: §4.2, Threading: "the workspace-root and open-buffer snapshots it needs are
read on the loop thread at submit time, the pattern step4 established for
`_analyze_blocking`."

**What's wrong**: the step4 pattern works because the needed input (`last_good` for one
URI) is known at submit. Here, *which* URIs the resolver will request via
`host.document()` is decided inside `resolve()` on the worker — unknowable at submit. As
written, an implementer can reasonably read "snapshots it needs" as "read
`self.workspace.get_text_document(uri)` when asked", i.e. from the worker thread — but
pygls's workspace is mutated by `didChange` on the loop thread concurrently, so
worker-side reads can pair version N with text N+1 (the same torn-read hazard
`rename_document`'s snapshot comment guards against, `server.py:437-439`).

**Consequence**: under active typing, cross-file requests intermittently compute offsets
against mismatched text — wrong locations, or out-of-range slices — a race that
demo-scale tests will rarely trip and the acceptance pass may.

**Suggested fix**: specify that the handler snapshots the *entire* open-document map
(`uri -> (version, text)`) on the loop thread at submit and hands it to `ProjectHost`;
`document()` consults only that snapshot plus disk.

## design-5 — Canonical-target matching relies on an undocumented exact-5-tuple equality invariant

**Section**: §4.4 (`canonical(...)` and the references aggregation: "symbols whose
canonical target is `T`", "unresolved references whose `ref_targets` entry is `T`") with
§4.1's `ExternalTarget`.

**What's wrong**: the aggregation compares resolver-produced `ExternalTarget`s against
`local_target(...)` tuples derived from `Symbol` fields. Equality therefore holds only if
the resolver copied `name_start/name_end/range_start/range_end` *exactly* from the target
document's `SymbolTable`. The gear resolver does (§4.8), so every in-repo test passes —
but nothing in the protocol's contract (§4.1) states this. A downstream resolver that
computes its own ranges (e.g. name span right, declaration range off by trivia) produces
targets that never compare equal: find-references silently returns same-file-only results,
and the §4.6 rename guard sees no cross-file occurrences (fail-open again, independent of
design-3). This is a sharp edge in exactly the surface §2.4 declares provisional *public*
API, and the failure is silent by construction.

**Consequence**: the first real downstream resolver (clockwork, §7) can be subtly wrong in
a way no error surfaces — incomplete find-refs and an ineffective rename guard — defeating
the round's purpose of validating the plugin contract.

**Suggested fix**: either match canonical identity on `(uri, name_start, name_end)` only
(the selection range; declaration range is presentation), or make the §4.1 contract state
in the protocol docstring that `ExternalTarget` offsets must be copied verbatim from the
target document's `SymbolTable` — and have the test-local fixture resolver (§6) pin
whichever rule is chosen.

## design-6 — Minor: in-wheel tests depend on out-of-wheel `examples/`

**Section**: §2.5 ("must not ship in the wheel… Tests for them live in `fltk/lsp/` per
the colocated-test convention and locate `examples/` relative to the repo root") and §3's
`test_gear_demo.py` / `test_server_crossfile.py` rows.

**What's wrong**: `tool.maturin.python-packages = ["fltk"]` (`pyproject.toml:34-36`) ships
the whole `fltk` package including colocated `test_*.py`, while `examples/` is correctly
excluded. So the distributed package contains tests whose fixtures do not exist relative
to an installed tree — unlike every existing LSP test, whose fixtures live in the shipped
`fltk/lsp/test_data/`.

**Consequence**: running the test suite from an installed distribution (a thing
downstream packagers do) fails on the two gear suites with path errors rather than a
clean skip; low impact, but it undercuts §2.5's own not-in-wheel rationale.

**Suggested fix**: a module-level `pytest.skip` (or `skipif`) when the resolved
`examples/gear` directory is absent, noted in the design as the intended behavior.
