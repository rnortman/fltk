# Dispositions — Requirements review (round 1)

Requirements doc: `/home/rnortman/src/fltk/.claude/work/clockwork-rust-packaging/requirements.md`

requirements-1:
- Disposition: Fixed
- Action: Reworded "In scope" (the FLTK-side-changes bullet) and "User-visible
  surface" (the FLTK MODULE/BUILD/rules.bzl bullet) to state behavior rather than
  invented rule/macro names. Removed mandated `generate_rust_parser` /
  `fltk_pyo3_cdylib` / file-name commitments from normative text and moved the
  illustrative shape (including those example names and the `lib.rs`/`cst.rs`/
  `parser.rs` sketch) into a new "Implementation notes (non-normative)" appendix
  marked as the designer's choice. Kept `gen-rust-cst`/`gen-rust-parser` cited as
  existing CLI subcommands (real per exploration-fltk:225-226).
- Severity assessment: Real leak — invented macro names in normative scope would
  be read as mandated, over-constraining the designer and inviting false
  scope-drift flags. Medium.

requirements-2:
- Disposition: Fixed
- Action: Rewrote acceptance criterion 3 to assert the observable outcome — the
  canonical `fltk._native.Span` is resolved through the native path and the
  span object returned via accessors is the native-backed type with correct
  offsets. Demoted the `warnings.warn` call site and the verbatim
  `RuntimeError` string to parenthetical "diagnostic hints, not pass/fail
  gates."
- Severity assessment: Coupling a done-gate to an internal warning site / exact
  message would spuriously fail a correct implementation that reworks the
  fallback signaling, or force a brittle string-grep test. Medium.

requirements-3:
- Disposition: Fixed
- Action: Removed the standalone criterion 5 (cross-backend equivalence) whose
  bar was simultaneously a done-gate and an unresolved open question. Folded the
  *minimal* bar (same parse success/failure + top-level `module` structure for
  one input) into criterion 4 as the concrete proof of "works in context."
  Renumbered the former criteria 6/7. TODO(equivalence-surface) now explicitly
  states the minimal bar is the default and only a stronger bar changes scope.
- Severity assessment: A "done" gate defined by an unresolved user decision is
  unactionable — implementer could over-build a differential harness or treat
  the gate as a near-duplicate of criterion 4. Medium.

requirements-4:
- Disposition: Fixed
- Action: Added a "resolve this first, before any Bazel plumbing" directive to
  TODO(grammar-regex-subset) with the cheap-derisking rationale (run
  `gen-rust-parser` once) and a "hard blocker if incompatible" framing. Added a
  parenthetical to acceptance criterion 1 noting it assumes regex-automata
  compatibility and is unreachable until the grammar is adjusted otherwise.
- Severity assessment: If the grammar is incompatible and this is discovered
  late, criteria 1-5 become unreachable mid-project after the Bazel plumbing is
  built — wasted effort and a stall pending an unapproved Clockwork-source
  change. Medium; cheap to derisk early.

requirements-5:
- Disposition: Fixed
- Action: Added a bolded "Premise correction (lead with this in the
  recommendation)" paragraph at the top of TODO(dep-mechanism): Clockwork uses
  `git_override`, not a git submodule (`.gitmodules` absent per
  exploration-clockwork:26), so the real choice is git_override-source vs.
  wheel/pip, not submodule-vs-pip. Asks to confirm the corrected framing before
  choosing.
- Severity assessment: Low — substance was already present; this prevents the
  user approving under a wrong mental model.

requirements-6:
- Disposition: Fixed
- Action: Added a "Note on scope of the FLTK-side work" paragraph to "In scope"
  stating the FLTK changes are genuine product/feature work whose new Bazel
  surface (rule/macro names, visibility) becomes public API per CLAUDE.md, and
  that approving this approves shipping that surface with the same compatibility
  care CLAUDE.md demands of generated symbols.
- Severity assessment: Low/informational — the scope was defensible as drawn;
  the note makes the public-API implication of the FLTK-side surface explicit so
  it gets appropriate care.

requirements-7:
- Disposition: Fixed
- Action: Removed criterion 7 (ABI mismatch diagnosable) from the numbered
  acceptance list and folded it into the Constraints "Single fltk-cst-core rlib
  version" bullet as an invariant: the guard must remain effective (mismatch =
  typed error, never silent wrong answer), the chosen mechanism should make
  matched-version the default, and constructing a deliberate mismatch is out of
  POC scope.
- Severity assessment: Low — default mechanism (A) makes a mismatch effectively
  unproducible, so listing it as a testable gate risks wasted effort on a
  deliberate-mismatch test or quiet omission. Better stated as an invariant.
