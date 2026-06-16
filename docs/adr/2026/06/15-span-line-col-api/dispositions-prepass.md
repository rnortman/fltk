# Dispositions — span-line-col-api prepass

## slop

No findings (notes-prepass-slop.md: "No findings.").

## scope-1: TODO.md missing required entries for two deferred items

- Disposition: Fixed
- Action: Added `## \`linecol-cache-consolidate\`` and `## \`py-span-linecol-cache\`` entries to
  `TODO.md` (end of file, after `extend-children-owned`). Each entry names the concrete follow-up,
  the deferral rationale, and the code location, satisfying the CLAUDE.md "TODO System" two-piece
  requirement (entry + `TODO(slug)` comment). The code-side comments already existed at
  `crates/fltk-parser-core/src/terminalsrc.rs:167,178` and `fltk/fegen/pyrt/terminalsrc.py:133`.
- Severity assessment: Without `TODO.md` entries the code comments are orphaned; the burndown
  ground-truth audit would fail to join against either slug. Low operational risk, but a process
  gap that makes deferred items invisible to the standard tracking workflow.

## scope-2: `pos_to_line_col` sentinel changed — design §2.5 said "unchanged"

- Disposition: Fixed
- Action: The implementation is correct (sentinel `len` is the right value; `len-1` truncated the
  last character). Reconciled three places so the record is consistent with actual behavior:
  1. `tests/test_span.py:392-396` — replaced stale comment "legacy uses `len-1`" with accurate
     text: "Both implementations now use sentinel = len (exclusive past-end)."
  2. `docs/adr/2026/06/15-span-line-col-api/design.md` §2.5 note 3 — updated "its observable
     behavior … is unchanged" to document the sentinel bug-fix as an intentional behavioral change.
  3. `docs/adr/2026/06/15-span-line-col-api/design.md` §2.4 and §2.12 — updated "unchanged" /
     "left untouched" references to note the sentinel correction exception.
- Severity assessment: The old `len-1` sentinel was a latent bug (final character absent from
  `line_span.text()` for sources without a trailing `\n`). Correcting it is strictly better for
  consumers. Documenting it as a behavioral change (rather than leaving "unchanged" in the design)
  is important for any out-of-tree caller who relied on the truncated `line_span.end`.

## scope-3: `resolve_line_col` docstring describes old `len - 1` sentinel

- Disposition: Fixed
- Action: Updated `crates/fltk-cst-core/src/span.rs:208-210` docstring. Changed "final sentinel
  of `len - 1`" to "final sentinel equal to `len` (exclusive end of the last line) for non-empty
  text without a trailing `\n`, or `-1` for empty input." The inline comment at lines 225-229
  (already accurate) is unchanged.
- Severity assessment: A reader of the public `resolve_line_col` doc would have expected
  `line_span.end == len - 1` but gotten `len` — a one-off discrepancy that would surface as a
  confusing test failure on a first-time reader tracing the sentinel logic.
