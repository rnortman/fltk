# Dispositions: user notes (round 2)

Concise. Precise. Unambiguous. No padding. Audience: smart LLM/human.

Round 1's correction (scope wrongly narrowed to "span") was already applied in the prior revise pass
(Goals + Scope notes now state span is one instance of a general "no Python-object reference" rule);
no further action. Round 2 disposition below.

## requirements-user-round2-generated-not-handwritten

- Disposition: Fixed
- Action: Corrected the requirements doc in two places.
  - In scope: replaced "Rust CST node struct (hand-written and generated)" with a statement that
    ALL affected structs are **generated** by `RustCstGenerator` (`fltk/fegen/gsm2tree_rs.py`) and
    checked in; enumerated the four generated-into-repo files (`src/cst_generated.rs`,
    `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`);
    stated there are zero hand-written CST node structs and the fix lives in the generator +
    regeneration.
  - System behavior → Native node state: rewrote the audit acceptance criterion to drop "and
    hand-written" and to assert all structs are generator output.
- Severity assessment: The exploration mislabeled `src/cst_generated.rs` and `src/cst_fegen.rs` as
  "hand-written" (exploration lines 10, 15), and the doc inherited that error. Left uncorrected it
  would misdirect implementation: an implementer might hand-edit those two files instead of fixing
  the generator and regenerating, leaving the generator emitting `span: PyObject` and re-breaking
  on next regen. The user is authoritative on their own codebase and explicitly corrected the
  exploration; the fix is mandatory.
