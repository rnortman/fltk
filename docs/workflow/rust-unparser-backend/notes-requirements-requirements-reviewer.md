# Requirements review: Rust Unparser Backend

Scope: adversarial check of the refined request (`requirements.md`) against the original
request and `exploration.md`. The user directive in `notes-requirements-user.md` (full
formatting pipeline must be reproduced, not "string tokens together") is treated as
binding and is correctly honored by the doc.

---

## requirements-1

**Section:** "What the user is asking for" → "What a generated Rust unparser does"
(Runtime library bullet) and "What matters in the codebase" → "Build system integration
points".

**What's wrong:** The refined request states, as hard requirements, several *new* design
artifacts and their structure that the exploration explicitly flagged as undetermined:

- A new runtime crate named `fltk-unparser-core`, located under `crates/`, with a
  prescribed decomposition ("Doc combinator types, the DocAccumulator (or equivalent
  builder), the spacing-resolution pass ..., and the Wadler-Lindig renderer").
- A new CLI subcommand `gen-rust-unparser` "would be added here."
- A `with_unparser` parameter on `LibSpec` (hedged with "or similar").
- Adding `fltk-unparser-core` as a Cargo workspace member; adding an unparser fixture.

These are module-structure / file-path / build-step decisions that the designer should
own. The exploration's own "Open Factual Questions" #4 (subcommand shape) and #5 (LibSpec
extension) call these *undetermined*, and it notes the runtime could even be "just a
String output abstraction" rather than a full crate.

**Why:** Refined doc: "Runtime library (`fltk-unparser-core` crate): Grammar-independent
Rust implementations ... This is the shared runtime that all generated Rust unparsers link
against." Exploration: "A `fltk-unparser-core` crate **would be** a parallel new crate
under `crates/` ... — or alternatively just a String output abstraction." The request only
constrains "the pattern is the same"; it does not name crates, subcommands, or params.

**Consequence:** The designer may treat the crate name, crate boundary, subcommand
surface, and lib.rs parameter as fixed and skip evaluating alternatives (e.g. whether the
runtime warrants its own crate, where the renderer belongs, the actual CLI/lib surface).
Mitigating factor: "the pattern is the same" makes a parallel runtime strongly implied, so
the *existence* of analogous artifacts is fair enrichment — it is the naming/structure
stated as settled that intrudes on design.

**Suggested fix:** Keep the parser-backend artifacts as context ("the parser has
`fltk-parser-core`, `gen-rust-parser`, a `LibSpec` submodule, a workspace member, a
fixture; the unparser will need the equivalents"), and explicitly defer the names,
boundaries, and exact surfaces to the design phase.

---

## requirements-2

**Section:** "What the user is asking for" (intro) — "The Rust unparser must produce
equivalent `Doc` trees and include the full formatting pipeline in Rust."

**What's wrong:** Resolving the *user-intent* half of exploration Open Question #1 (do the
full formatting pipeline vs. emit raw strings) is correct and is mandated by the user
directive. But the phrasing also resolves the *representation* half — "produce equivalent
`Doc` trees" reads as pinning the internal IR. Whether the Rust side literally materializes
a Doc-tree enum, and whether the Python-facing PyO3 path returns a Doc vs. a rendered
string, is a design call (exploration #1 lists output type as "not determined").

**Why:** Exploration #1: "Whether the Rust unparser would output `String` directly, a new
`fltk-unparser-core::Doc` enum, or something else is not determined by existing code." The
user's intent is "use the sophisticated formatting algorithm" (behavior), not a specific IR.

**Consequence:** Minor — designer may assume a literal `Doc` enum is mandated even if an
equivalent representation yields identical formatted output. (In practice reproducing
`resolve_specs` + Wadler-Lindig naturally wants a Doc-like IR, so the risk is small.)

**Suggested fix:** State the requirement as reproducing the formatting *behavior* (width-
aware breaking, nesting, grouping, joining, trivia preservation, spacing control) with the
internal representation left to design.

---

## requirements-3 (overall / big picture)

**Section:** overall.

The refinement is, on balance, a faithful and intuitive framing: the verbatim original
request opens the doc; the two-layer architecture, the Rust-CST-only operation, the
optional PyO3 wrapper, and the "must pair Rust unparser with Rust parser" constraint are
all captured accurately and without distortion; the full-formatting-pipeline requirement
correctly reflects the user directive rather than refiner overreach. No genuine
user-intent question was left silently guessed, and the doc does not pester with
contrived questions. The single open question the refiner did raise (formatting pipeline
vs. raw strings) was, per project philosophy ("the formatting pipeline is the core value
of the unparser"), one it should have resolved itself rather than asking — now resolved
and moot. The only systematic weakness is the lean toward stating *new* artifact names and
build/test steps as settled requirements (requirements-1), which nudges into design
territory the user did not constrain beyond "same pattern."
