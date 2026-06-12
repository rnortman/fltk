# Dispositions: prepass review — rust-generated-ident-collisions

Style: concise, precise, no padding. All items verified against HEAD 4f66083.

---

## slop-1

Finding: `test_multiple_collisions_reported_at_once` hand-rolled four inline `gsm.Rule(...)` blobs instead of reusing `_make_two_rule_grammar`.

Disposition: Fixed (in 4f66083, predating this respond round)
Action: `tests/test_gsm2tree_rs.py:1762–1775` — test calls `_make_two_rule_grammar("foo", "foo_child")` and `_make_two_rule_grammar("bar", "bar_child")`, merges `rules` and `identifiers` into a `gsm.Grammar`. No inline blobs.
Severity assessment: Would have signalled inattention to an existing helper; resolved; no correctness impact.

---

## slop-2

Finding: The `_RESERVED_CLASS_NAMES` invariant (no reserved name starts with "Py", ends with "Child" or "Label") was stated in prose only; nothing machine-checked it.

Disposition: Fixed (in 4f66083, predating this respond round)
Action: `fltk/fegen/gsm2tree_rs.py:47–53` — module-level `assert` verifies the invariant at import time; violation message instructs seeding the offending name into the claims dict. Prose comment updated to "Machine-checked:".
Severity assessment: Without the assert a future editor adding e.g. `"PyNode"` to `_RESERVED_CLASS_NAMES` would silently lose cross-rule collision coverage for that identifier; now fails fast at startup.

---

## slop-3

Finding: `test_prediction_vs_output_consistency` contained a redundant local `from fltk.fegen.gsm2tree_rs import RustCstGenerator as _Gen  # noqa: PLC0415` suppressing a false-positive lint for a problem that didn't exist, given the module-level import.

Disposition: Fixed (in 4f66083, predating this respond round)
Action: `tests/test_gsm2tree_rs.py:1785–1811` — test uses module-level `RustCstGenerator` directly (imported at line 20); no local re-import or `noqa` suppression present.
Severity assessment: Cosmetic; would have flagged careless copy-paste; no correctness impact.

---

## scope notes

Reviewer noted that `test_prediction_vs_output_consistency` uses a pure-regex grammar rather than one with node-typed children (as the design phrased test plan item 3). Reviewer assessed this does not weaken the drift guard for the collision check itself; no gap.

Disposition: No action required
Action: No change.
Severity assessment: No coverage gap; the four identifier families (including `{CN}Child`) are still asserted in generated output.
