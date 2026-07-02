# Dispositions: design review round 1 — native-span-init-error-context

Findings from `notes-design-design-reviewer.md`. All three verified against source
before disposition.

design-1:
- Disposition: Fixed
- Action: Verified `fltk/fegen/test_genparser.py:1565` asserts the exact old use line
  `use span::{SourceText, Span};` inside `test_gen_rust_lib_span_only_output` — the
  finding is correct; that test breaks after the §1 drift fix. Added it to the design's
  "Updated" test list (design.md, Test plan) with the use-line update, an
  `m.add_class::<LineColPos>()` assertion, and the optional
  `assert "LineColPos" not in src` mirror in `test_gen_rust_lib_standard_output`.
  Reworded the test-plan header ("Primarily in `test_gsm2lib_rs.py` ... plus one
  CLI-level test in `test_genparser.py`") and changed "Unchanged tests" to "Remaining
  tests" so the keep-passing claim is no longer false.
- Severity assessment: Without the fix, an implementer following the plan verbatim would
  land the generator change with a red test in `make test`/`make check` and have to
  patch an unplanned file mid-implementation. Plan-completeness bug, not a design-shape
  bug.

design-2:
- Disposition: Fixed
- Action: Verified both sub-claims: `test: build-test-fixtures` → `build-native`
  (Makefile) rebuilds `fltk._native`, and `tests/test_rust_span.py:11` does
  `from fltk._native import LineColPos` at module scope — so a post-regen drop fails
  loudly in `make test`, not silently; and pyo3 `add_class` only exposes the module
  attribute, so `Span.line_col` return values would keep working. Rewrote the §1
  "Context / root cause" consequence paragraph (design.md) per the reviewer's suggested
  framing: the *divergence* is invisible until regen; post-regen the drop is caught by
  `make check` via the `test_rust_span` import but only after a full native rebuild;
  the drift pin moves detection to a pure-Python unit test.
- Severity assessment: No change to what gets built — drift fix and drift pin remain
  justified on the corrected narrower grounds. But the design doc is the durable
  justification record; leaving "nothing catches this / breaks every consumer of
  `Span.line_col` results" would misrecord the existing safety net and could be cited
  later to justify unnecessary "we have no gate" work.

design-3:
- Disposition: Fixed
- Action: Verified both surfaces: `LibSpec.register_span_types` docstring
  (`gsm2lib_rs.py:99`) and the `--register-span-types` CLI help (`genparser.py:789`)
  both say only "Span/SourceText". Added a fourth bullet to §1 of the design covering
  both one-line updates, and noted in the "Proposed approach" preamble that these two
  description updates ride along (the CLI help is how an out-of-tree `gen-rust-lib`
  user learns their `mod span;` must export `LineColPos`).
- Severity assessment: Minor doc rot only, but it lands exactly on the out-of-tree
  `--register-span-types` edge case the design itself calls out, so omitting it would
  undercut the design's own consumer-facing story. Two one-line changes.
