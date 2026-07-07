# Judge verdict — deep review (fltklsp round 2: engine/CLI/dogfood)

Phase: deep. Base 87dbc0d..HEAD 4fd9449 (round-1 fix commit f1e7f60; round-2 fix commit 4fd9449).
Round 2 — APPROVED or ESCALATE only.
Round 1 approved 25 of 26 dispositions and disputed exactly one: efficiency-4, a
`TODO(lsp-classify-hotpath)` item failing rubric Q2 (safe design fully specified in the TODO's own
text; deferral rested on batching convenience). This round verifies the promotion of that item to
Fixed and re-confirms the surrounding state; the 25 previously-approved dispositions are unchanged
by the new commit (diff f1e7f60..4fd9449 touches only `lsp_config.py`, `classify.py`, `TODO.md`,
and workflow docs) and are not re-walked.

## Added TODOs walk

### efficiency-2 / efficiency-3 — TODO(lsp-classify-hotpath), `classify.py:293` and `classify.py:393`
Round-1 assessment (both pass Q1 and Q2: design-stage sweep-line/walk-fusion rewrite of the
interval-resolution core, concrete unmet trigger, pre-existing code) stands. Round-2 state
verified: `TODO.md` entry now lists exactly these two items; the two inline
`TODO(lsp-classify-hotpath)` comments at `_winner_segments` and the second `_default_intervals`
loop are the only remaining occurrences in `fltk/` — slug/comment/entry in sync.
Assessment: TODOs acceptable.

### efficiency-4 — was TODO, now Fixed (the round-1 disputed item)
Diff at `lsp_config.py:444-453`: `ByLabel` gained
`name_upper: str = dataclasses.field(init=False, compare=False, repr=False)`, set in
`__post_init__` via `object.__setattr__(self, "name_upper", self.name.upper())` — exactly the
frozen-dataclass-safe, equality-surface-preserving form the round-1 verdict prescribed.
Diff at `classify.py:240-241`: `_matches` compares `label_name == match.name_upper`; the inline
TODO comment at that site is removed. `TODO.md` entry drops item (3) and the `lsp_config.py`
location; items 1–2 retained (see above). `compare=False`/`repr=False` keep by-value equality
keyed on `name` alone, so the `test_lsp_resolve.py` equality constraint identified in round 1 is
preserved. Full `uv run pytest fltk/lsp/` at HEAD 4fd9449: 129 passed.
Assessment: promotion complete and correct. Accept.

## Other findings walk

No other disposition changed between f1e7f60 and 4fd9449. The dispositions doc's quality-1 and
efficiency-4 sections were updated to record the promotion; the recorded state matches the code
(verified against `lsp_config.py`, `classify.py`, `TODO.md`, and the test run above). The 25
round-1-approved dispositions (22 Fixed verified, 1 Won't-Do sound, 2 TODOs acceptable) carry
forward unchanged.

## Disputed items

None. The single round-1 dispute is resolved.

## Approved

26 of 26 findings: 23 Fixed verified (efficiency-4 promoted this round), 1 Won't-Do sound,
2 TODOs acceptable (efficiency-2, efficiency-3).

---

## Verdict: APPROVED

All dispositions acceptable at HEAD 4fd9449.
