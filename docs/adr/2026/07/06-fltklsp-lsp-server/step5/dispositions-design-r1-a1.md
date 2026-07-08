# Dispositions — step5 design review round 1 (design-reviewer findings)

Responder fact-check basis: `pyproject.toml` (lsp extra at 27-28, dev group at 44-45,
`tool.maturin.python-packages` at 34-36), `fltk/lsp/server.py` (`_GoodAnalysis` fields at
93-107 — no text field; rename text-snapshot comment at 437-439; definition/references
handlers at 671-692), `fltk/lsp/positions.py` (`LineIndex._text` private, line 37),
`fltk/lsp/server_cli.py:44-48` (missing-pygls exit 1). All six findings verified as
factually grounded. Design revised in place; cleanup-editor pass applied after the edits.

design-1:
- Disposition: Fixed
- Action: The finding's core fix — `--extra lsp` in the default launch command — was
  already present in the design's §4.9 as reviewed here (the finding quotes an older
  phrasing without it; the pyproject/server_cli facts were re-verified and the current
  command is correct). The two outstanding sub-items were applied: §4.9 run-modes now
  requires the README prerequisites to name the Rust toolchain (per CLAUDE.md, `uv run`
  cannot build without rustup/cargo) and warn about the one-time maturin debug build on
  first launch; §6's coverage claim was reworded — the **argument vector** is pinned by
  `test_server_crossfile.py` via the `[sys.executable, "-m", "fltk.lsp.server_cli", ...]`
  harness convention, while the `uv ... run --extra lsp` launcher layer is exercised only
  by the manual acceptance checklist. The `test_server_crossfile.py` bullet itself now
  states the harness convention explicitly instead of "the real `fltk-lsp` command".
- Severity assessment: without `--extra lsp` the headline acceptance criterion would fail
  at checklist step 1 on any clean checkout, invisibly to automated tests; the residual
  sub-items were documentation/claim accuracy.

design-2:
- Disposition: Fixed
- Action: §4.5 now specifies the mechanism: `_GoodAnalysis` gains a `text: str` field
  (module-private; today the last-good text survives only as the private
  `LineIndex._text`, `positions.py:37`), and the requesting-side `ResolvedDocument` is
  built wholesale from that one snapshot — text, tree, symbols, and line index all from
  the same version, never pairing live buffer text with a last-good tree.
- Severity assessment: as drafted, the stated stale-serving policy had no constructible
  data source on the last-good path; the likely implementer shortcut would mix document
  versions and read garbage module paths — a real correctness gap in exactly the
  edit-with-errors state the policy exists for.

design-3:
- Disposition: Fixed
- Action: §4.6 now states the rename guard fails **closed** — any exception during its
  global query (resolver or workspace-file analysis) refuses the rename with "cannot
  rename: could not verify cross-file references" — with rationale that degrading here
  would reopen the §2.3 hazard. §4.5's exception bullet was narrowed to
  definition/references and cross-references the §4.6 carve-out; the §5 "resolver raises"
  edge case and the §6 test plan (test-local always-raising resolver in
  `test_server_crossfile.py`: references degrade, rename refuses) were aligned.
- Severity assessment: the blanket degrade-to-same-file policy inverted the guard's
  safety property — a raising resolver would make the guard a silent no-op and allow the
  exact silent-corruption rename the guard exists to prevent.

design-4:
- Disposition: Fixed
- Action: §4.2's Threading bullet now specifies that the handler snapshots the entire
  open-document map (`uri -> (version, text)`) plus the workspace root on the loop thread
  at submit time; `ProjectHost.document()` consults only that snapshot and disk, never the
  live pygls workspace — citing the same torn-read hazard `rename_document`'s snapshot
  comment guards against (`server.py:437-439`) and noting the snapshot is O(open docs)
  reference copies.
- Severity assessment: as drafted, "the snapshots it needs" was unknowable at submit and
  invited worker-thread reads of the live workspace, pairing version N with text N+1 —
  an intermittent wrong-locations race under active typing that tests would rarely trip.

design-5:
- Disposition: Fixed
- Action: Canonical identity is now defined as the `(uri, name_start, name_end)` prefix
  only — declaration ranges are presentation, never identity — stated as a new §4.1
  design point, reflected in §4.4's canonical-target definition, and pinned in §6's
  `test_project.py` by a fixture target whose declaration range deliberately diverges yet
  still matches. The §4.1 protocol docstring additionally instructs resolver authors to
  copy all four offsets verbatim from the target document's `SymbolTable` (both halves of
  the reviewer's either/or, since name-span exactness is still required for matching).
- Severity assessment: the undocumented exact-5-tuple invariant would let the first real
  downstream resolver silently produce empty find-references and a defanged rename guard
  — a silent-by-construction failure in the surface this round exists to validate.

design-6:
- Disposition: Fixed
- Action: §2.5 now specifies that the two gear suites skip at module level (with an
  explanatory reason) when the resolved `examples/gear` directory is absent, citing
  `tool.maturin.python-packages` (`pyproject.toml:34-36`) shipping colocated tests while
  `examples/` stays out of the wheel — so an installed-distribution test run skips
  cleanly instead of failing on missing fixtures.
- Severity assessment: low — installed-tree test runs would fail with path errors on two
  suites rather than skip; no runtime impact, but it undercut §2.5's own packaging
  rationale.
