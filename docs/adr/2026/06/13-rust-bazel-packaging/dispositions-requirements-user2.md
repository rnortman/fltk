# Dispositions — requirements user notes, round 2

Source: `notes-requirements-user.md` ("User notes round 2", three notes).
Requirements doc: `requirements.md`. All three notes are authoritative user
direction and applied as Fixed.

## user2-1 — "Bazel must build Rust" is not a differentiator; native-Rust is an assumed motivation

- Disposition: Fixed
- Action:
  - Goals: added an "Assumed motivation" paragraph stating a consumer adopts the
    Rust backend in part to write its own native Rust alongside the PyO3
    bindings, and the integration must not preclude that.
  - Open questions / "Design space": added an explicit note that *every* path
    requires Clockwork's Bazel build to build Rust, so "needs a Rust toolchain /
    `rules_rust`" is a baseline given, not a factor to weigh between options;
    what differs is only where core rlibs come from and how the ABI pin stays
    matched.
  - Removed the strawman framing from the (former) TODO(dep-mechanism) option
    list — option (A) no longer lists "build now compiles Rust + needs a Rust
    toolchain" as a downside.
  - Constraints → "Toolchain": reframed as a baseline given, present on every
    path, explicitly "not a factor that distinguishes one path from another."
- Severity assessment: Without this, the requirements bias the downstream design
  by presenting a universal precondition as a per-option cost, skewing the
  packaging-path evaluation the user explicitly wants left open.

## user2-2 — Regex / rust-regex-crate compatibility is incidental; assumption only, not a gate

- Disposition: Fixed
- Action:
  - Acceptance criterion 1: removed the parenthetical that made grammar
    regex-automata compatibility a precondition / "resolve first" blocker.
  - Constraints → "Regex subset": reframed as "(assumption, not a gate)" —
    states the work assumes `clockwork.fltkg` is already in the compatible
    subset, and that any needed grammar/FLTK fix is a separate out-of-scope
    effort that does not change these requirements and is not a pass/fail gate.
  - Open questions: deleted the entire TODO(grammar-regex-subset) entry (it had
    demanded resolving compatibility first and flagged a hard blocker).
- Severity assessment: Treating an incidental assumption as a gating blocker
  would mis-scope the project, which is about packaging/integration, and could
  stall the design on a question the user has explicitly deprioritized.

## user2-3 — Do not force a packaging-path decision in requirements; that is DESIGN

- Disposition: Fixed
- Action:
  - Goals: replaced "a ratified decision on *how* FLTK should be consumed" with
    an explicit statement that the packaging path (build-in-Bazel vs. wheel/pip)
    and `rules_rust` placement are **design** decisions to be resolved
    downstream; requirements state only what must work.
  - In scope: the deliverable bullet now requires only that the chosen mechanism
    be recorded in an ADR, not that a particular mechanism be selected up front;
    "obtains FLTK" sub-bullet notes the mechanism is a design choice.
  - Open questions: replaced the three decision-forcing entries
    (TODO(dep-mechanism), TODO(rules-rust-placement), TODO(core-crates-distribution),
    TODO(rust-toolchain-host)) with a single non-binding "Design space" section
    that scopes the options for the designer and explicitly states the choice is
    not forced before design begins. Removed the "Proposed default to validate
    first / Confirm" language that asked the user to ratify a direction.
- Severity assessment: Forcing the packaging decision in the requirements doc
  inverts the project's requirements-vs-design separation, pre-empts the
  designer, and asks the user to ratify a call they have said belongs downstream.

## Note on the round-1 "Bazel submodule" correction

The earlier user correction (verbatim, top of notes file) about "Bazel
submodule" vs "git submodule" remains correctly reflected: exploration-clockwork
§1 and the requirements' Open-questions "Design space" describe FLTK as a Bazel
module resolved by `bazel_dep` + `git_override` (not a git submodule). No
further change needed for this round.
