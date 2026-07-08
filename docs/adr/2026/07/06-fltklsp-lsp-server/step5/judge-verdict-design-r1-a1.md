# Judge verdict — design review (step5, round 1)

Phase: design. Doc: `docs/adr/2026/07/06-fltklsp-lsp-server/step5/design.md`. Round 1.
Notes: `notes-design-design-reviewer-r1.md` (6 findings). Dispositions:
`dispositions-design-r1-a1.md` (all 6 Fixed, design revised in place).

## Findings walk

### design-1 — Fixed
Claim: default launch command `uv --project <repo> run fltk-lsp ...` omits `--extra lsp`;
pygls lives only in the `lsp` extra (`pyproject.toml:27-28`), so a clean checkout gets a
pygls-less env and `server_cli.py:44-48` exits 1 — the round's headline acceptance
criterion fails at §4.10 step 1, invisibly to tests. Plus two sub-items: README must name
the Rust prerequisite/first-launch build cost, and §6's "the exact command line it
launches is the one `test_server_crossfile` drives" overstates coverage.
Design now: §4.9 builds `uv --project <repo> run --extra lsp fltk-lsp ...` and spells out
why `--extra lsp` is load-bearing, citing `pyproject.toml:27-28` and `server_cli.py:44-48`
("plain `uv run` syncs default groups only (`dev` = maturin)"). §4.9 run-modes: README
prerequisites name Node/npm **and the Rust toolchain** (per CLAUDE.md) and warn the first
launch pays the one-time maturin debug build. §6 reworded: "the **argument vector** … is
the one `test_server_crossfile` drives; the `uv ... run --extra lsp` launcher layer itself
is exercised only by the manual acceptance checklist", and the `test_server_crossfile.py`
bullet names the `[sys.executable, "-m", "fltk.lsp.server_cli", ...]` harness convention
explicitly.
Note on the disposition's framing: the responder says the `--extra lsp` fix "was already
present as reviewed here" while the reviewer quoted the command without it — the
dispositions doc itself says the design was revised in place, so the reviewer plainly read
a pre-fix draft. The framing is immaterial: the current design contains the fix and both
residual sub-items, which is what a Fixed disposition must show.
Assessment: all three parts of the finding addressed at the named sections. Accept.

### design-2 — Fixed
Claim: on the last-good path the requesting document's `ResolvedDocument.text` has no
licensed source — `_GoodAnalysis` (`server.py:93-107`) stores no text; the obvious
shortcut pairs live buffer text with a last-good tree, exactly the version-mixing the
`_GoodAnalysis` docstring rules out.
Design now: §4.5 states `_GoodAnalysis` gains `text: str` (module-private; notes the
last-good text today survives only as private `LineIndex._text`, `positions.py:37`) and
that the requesting-side `ResolvedDocument` is built **wholesale from that snapshot** —
text, tree, symbols, line index all from one version, "never pairing live buffer text with
a last-good tree".
Assessment: the reviewer's suggested mechanism, adopted verbatim and stated as a
constraint. Accept.

### design-3 — Fixed
Claim: the blanket degrade-to-same-file exception policy (§4.5) covered the §4.6 rename
guard, inverting its safety property — a raising resolver would make the guard see zero
cross-file occurrences and let the rename proceed (fail-open on the §2.3 hazard).
Design now: §4.6 states the guard fails **closed** — any exception during its global
query refuses with "cannot rename: could not verify cross-file references" — with the
rationale that degrading would reopen the §2.3 hazard. §4.5's exception bullet is
narrowed ("The one deliberate exception is the rename guard, which fails **closed**
(§4.6)"), the §5 "resolver raises" edge case distinguishes the two dispositions, and §6's
always-raising-resolver test pins both (references degrade, rename refuses).
Assessment: policy split stated in all four places the finding touched, with a test.
Accept.

### design-4 — Fixed
Claim: "the open-buffer snapshots it needs" is unknowable at submit (which URIs
`resolve()` requests is worker-side knowledge), inviting worker-thread reads of the live
pygls workspace — the torn-read hazard `server.py:437-439` guards against.
Design now: §4.2 Threading specifies the handler snapshots the **entire open-document
map** (`uri -> (version, text)`) plus the workspace root on the loop thread at submit;
`document()` consults only that snapshot and disk, never the live workspace; cites
`server.py:437-439`; notes O(open documents) reference-copy cost and why the step4
pattern extends to a whole map.
Assessment: the exact underspecification closed with the reviewer's suggested rule.
Accept.

### design-5 — Fixed
Claim: canonical-target matching silently depended on exact-5-tuple equality of
`ExternalTarget` offsets against `SymbolTable`-derived tuples — undocumented in the §4.1
contract; a downstream resolver with a divergent declaration range gets silently empty
find-refs and a defanged rename guard, in the provisional public surface this round
exists to validate.
Design now: new §4.1 design point — "Canonical identity is the selection range":
identity is `(uri, name_start, name_end)` only, declaration ranges are presentation,
never identity; §4.4's canonical-target definition restates it; the protocol docstring
still instructs verbatim copying of all four offsets; §6's `test_project.py` pins the
rule with a fixture target whose declaration range deliberately diverges yet matches.
Assessment: the responder took the stronger half of the reviewer's either/or (prefix-only
matching removes the silent-failure mode structurally rather than just documenting it)
and kept the docstring guidance too, with a pinning test. Accept.

### design-6 — Fixed
Claim (minor): the wheel ships colocated tests (`tool.maturin.python-packages`,
`pyproject.toml:34-36`) but not `examples/`, so the two gear suites fail with path errors
from an installed distribution instead of skipping.
Design now: §2.5 specifies the two gear suites skip at module level (with an explanatory
reason) when the resolved `examples/gear` directory is absent, citing the packaging facts.
Assessment: reviewer's suggested fix adopted and recorded as intended behavior. Accept.

## Disputed items

None.

## Approved

6 findings: 6 Fixed verified.

---

## Verdict: APPROVED

All six dispositions verified against the revised design text; every fix lands at the
sections the finding named, and the two safety-property findings (design-3, design-5)
were resolved structurally (fail-closed guard; prefix-only canonical identity) rather
than by documentation alone.
