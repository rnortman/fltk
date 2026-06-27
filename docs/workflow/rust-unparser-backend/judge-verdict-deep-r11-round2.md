# Judge verdict — deep review r11 (round 2)

Phase: deep. Base 0494f31..HEAD 9c42aa8. Round 2 (APPROVED or ESCALATE only).
Notes: 7 reviewer files (correctness + security: no findings); 9 dispositioned findings.
Round-1 verdict: REWORK on a single item (efficiency-1). Round-2 fix landed in commit 9c42aa8
(`feat(genparser): add generate --protocol-only; rewire gencode`). The other 8 findings were
Fixed-and-verified in round 1 (commit 1cda7da) and their dispositions are unchanged.

## Added TODOs walk

No TODO-dispositioned findings remain. The single round-1 TODO (efficiency-1 /
`unparser-gencode-protocol-only`) was converted to Fixed; see below. `git show 9c42aa8:TODO.md`
no longer contains the `gencode-protocol-only` slug (3 lines removed in the round-2 commit), and
the entry is absent in both base and HEAD — TODO/code/TODO.md are back in sync with no orphan.

## Other findings walk

### efficiency-1 — Fixed (round 2; was TODO(unparser-gencode-protocol-only), ruled do-now in round 1)
Round-1 finding: the `gencode` protocol step ran a full `genparser generate` into a temp dir and
kept only `<base>_cst_protocol.py`, discarding the full CST + parser suite — mechanical, doable-now
redundancy this iteration introduced. Round-1 ruling: do-now (fails rubric Q2), parked TODO not
acceptable.

Round-2 disposition: implement the `--protocol-only` flag and rewire the recipe. Verified:

- **genparser.py** (`git diff 1cda7da..9c42aa8`): `--protocol-only` typer option added; the shared
  CST module write is gated behind `if not protocol_only:`; the protocol module is written
  unconditionally before an early `return` under `if protocol_only:`, so both parser generations are
  skipped. Mutual-exclusion guard added (`--protocol-only` with `--trivia-only`/`--no-trivia-only`
  → `Exit(1)`, since no parsers are produced). The verbose summary no longer reads the
  now-conditional `shared_cst` local — it recomputes `output_dir / f'{base_name}_cst.py'` inline,
  closing the pyright possibly-unbound path. Clean, additive, backward compatible (flag defaults
  False; existing invocations unaffected).
- **Makefile** (base..HEAD): the `mktemp -d` + `set -e`/EXIT-trap + full `generate` + `cp` block is
  replaced by a single `uv run python -m fltk.fegen.genparser generate --protocol-only ...
  --output-dir tests` that writes `tests/rust_parser_fixture_cst_protocol.py` directly. The temp-dir
  dance is gone; with no trailing `rm`/`cp`, the lone `generate`'s exit status is the recipe line's
  status — the errhandling-1 masking concern is structurally moot.
- **Tests** (`fltk/fegen/test_genparser.py`): three new CLI tests, all PASS (ran them):
  `test_generate_protocol_only_emits_only_protocol` (protocol written; `_cst.py`, `_parser.py`,
  `_trivia_parser.py` all absent), `test_generate_protocol_only_matches_full_run` (protocol output
  byte-identical to a full `generate` run — pins the equivalence the rewire relies on), and
  `test_generate_protocol_only_rejects_trivia_flags` (non-zero exit, error message, nothing written).
- **Byte-identical committed artifact**: regenerated `tests/rust_parser_fixture_cst_protocol.py` via
  the rewired `--protocol-only` step + `ruff check --fix` then `ruff format` (the `make fix` order);
  `git diff` is CLEAN — the committed protocol module is reproduced exactly. (An initial apparent
  diff was an artifact of running ruff format-before-check; the `make fix` order converges.)

Assessment: the redundant CST/parser codegen is eliminated, protocol output is provably unchanged,
the round-1 do-now ruling is satisfied, and the errhandling-1 path the old block created is removed.
Disposition correct. Accept.

## Disputed items

None. The sole round-1 dispute (efficiency-1) is resolved.

## Approved

All 9 findings acceptable. 8 unchanged from round 1 (errhandling-1, quality-3, test-1, test-2,
reuse-1, quality-1, reuse-2, quality-2 — all Fixed and verified in round 1; dispositions unchanged,
not re-walked). 1 newly resolved this round (efficiency-1 — Fixed, verified above).

---

## Verdict: APPROVED

The single round-1 defect (efficiency-1, deferred-as-TODO mechanical work) is now properly fixed:
`--protocol-only` flag implemented and tested, recipe rewired, TODO.md entry removed, committed
protocol module reproduced byte-identically. All dispositions acceptable.
Commit 9c42aa8909dbbe8db9864d46e9684ea88e1d484f.
