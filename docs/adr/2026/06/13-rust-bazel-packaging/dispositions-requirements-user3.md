# Dispositions — User notes round 3

Source: `notes-requirements-user.md` ("User notes round 3"). These are
authoritative user directives applied directly to `requirements.md`.

user-round3-1 (crates.io is an available design option, not a blocker):
- Disposition: Fixed
- Action: Rewrote the "Core-crate distribution" sub-point under Open questions →
  Design space. It now states the crates are not currently published, that
  publishing to crates.io is a fully available design option the designer may
  choose if cleanest/most expedient (FLTK will publish if so), that source-only
  via the FLTK dep is the equal alternative, and that "not yet published" is
  explicitly **not** a constraint or blocker. The existing "Out of scope" line
  (publishing not a *requirement* but may be selected as the mechanism) already
  agrees with this framing and was left as-is.
- Severity assessment: Without this, the designer could read the prior
  "unverified whether published" phrasing as a hard limitation and rule out the
  crates.io path unnecessarily, narrowing the design space against the user's
  intent.

user-round3-2 (acceptance bar = produces a result, not correctness/equivalence):
- Disposition: Fixed
- Action: (a) Rewrote acceptance criterion 4 to "Bindings produce a result —
  round-trip parse": the bar is that the Bazel-built Rust parser + PyO3 bindings,
  invoked in context, produce *some* parse result/output read through the
  generated accessors without error; explicitly states this is NOT a
  parser-correctness test and NOT a Rust-vs-Python equivalence test, and that
  FLTK parsing correctness is out of scope. (b) Removed the
  Rust-vs-Python-agreement clause and Python-baseline comparison from criterion
  4. (c) Removed the entire `TODO(equivalence-surface)` open-question section.
  (d) Softened criterion 3's span-path wording from "carries correct offsets /
  positive assertion of correctness" to "the Rust path is actually wired up, not
  silently replaced by the fallback," keeping it as an integration check rather
  than a correctness gate.
- Severity assessment: Left unaddressed, the requirements would mandate a
  cross-backend differential/correctness harness the user explicitly rejected,
  expanding scope well beyond the packaging/integration POC and testing the wrong
  thing.
