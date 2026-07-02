# Judge verdict — prepass

Phase: prepass (slop + scope). Base 9233540..HEAD 2728a78. Round 1.
Notes: 2 reviewer files (`notes-prepass-slop.md`, `notes-prepass-scope.md`); 1 finding total.

## Added TODOs walk

No findings were dispositioned as TODO. (The diff does add `TODO(formatter-group-idempotency)` at `crates/fltkfmt/tests/cli.rs` with a matching `TODO.md` entry, but that TODO is specified by the approved design — §2.2/§2.3 — not a review disposition, so it is not adjudicated here.)

## Other findings walk

### slop-1 — Fixed
Claim: doc comment for `parse_errors_report_filename_and_position` at `crates/fltkfmt/tests/cli.rs:270` cites "the original design specified" as authority; consequence is an in-code reference to an ephemeral planning artifact that won't resolve for future readers.
Diff: fix commit `2728a78` rewords the comment to "Assertions bind only to the stable contract — exit code 2, empty stdout, and a stderr carrying the filename plus the `Syntax error at line … col …` skeleton — not the full error text, whose expected-token lists may change with the grammar." The contract is now stated directly with no design-document citation. `git grep "original design"` over `crates/fltkfmt/` at HEAD returns nothing.
Severity: nit (cosmetic, no behavioral impact) — responder's own "Cosmetic" assessment matches.
Assessment: fix addresses the finding exactly as suggested. Accept.

### scope (notes-prepass-scope.md) — no findings
The scope reviewer reported no findings and verified: all 4 designed tests present and passing, golden fixture byte-identical to `fltk/fegen/fegen.fltkg`, TODO.md §2.3 closure exact (slug pair `formatter-group-idempotency` in both `TODO.md` and `cli.rs`), `main.rs` diff limited to the TODO-comment deletion, no Makefile/Bazel changes. Spot-checked against the diff: matches (`TODO.md` swaps `fltkfmt-integration-tests` → `formatter-group-idempotency`; `main.rs` loses only the 4-line TODO block; `cli.rs` + golden fixture are the only additions).
The reviewer's informational note (the closed TODO entry's `--help`/`about`-string assertion not being in design.md's four-test scope) is explicitly marked not-a-finding and is a design-scope question already through design review, not a diff-vs-design gap. Responder's "nothing to act on" is correct.
Assessment: no disposition required. Accept.

## Approved

1 finding: 1 Fixed verified. Scope notes carried no findings.

---

## Verdict: APPROVED

All dispositions acceptable. Round 1, nothing disputed.
