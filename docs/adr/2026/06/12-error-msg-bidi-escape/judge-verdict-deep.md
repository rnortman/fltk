# Judge verdict — deep review (error-msg-bidi-escape)

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Phase: deep. Base 108ee61..HEAD ad6c51c (reviews taken at 65279b7; respond commit ad6c51c). Round 1.
Notes: 7 reviewer files (error-handling and efficiency: no findings); 12 findings, 12 dispositions.

## Added TODOs walk

### reuse-1 — TODO(rust-escape-sweep-oracle), claimed at `crates/fltk-cst-core/src/escape.rs:36`

Disposition is labeled "Fixed" but is in substance a TODO deferral: the Rust sweep predicate duplication at `crates/fltk-parser-core/src/errors.rs:397-405` remains, and the action text claims a TODO was added.

**Artifact check:** the TODO does not exist. `grep rust-escape-sweep-oracle` over `TODO.md`, `escape.rs`, `errors.rs`, and the whole tree (excluding this ADR dir) finds nothing. No `TODO(slug)` comment, no `TODO.md` entry — the project TODO system requires both. The disposition asserts an action that was not taken.

**Rubric Q1 (worth doing):** yes. The inline `is_escaped_set` predicate at `errors.rs:397-405` re-implements the 9-condition membership check; drift on a future escape-set extension silently removes sweep coverage for the new class — the same drift pattern (`escape_control_chars_for_msg`) this commit exists to fix.

**Rubric Q2 (design/owner input required):** no. The responder's rationale — `needs_escape` is private and unreachable across the crate boundary — is true but irrelevant. The sweep does not need `needs_escape`: `escape_control_chars` itself is the oracle (`escape_control_chars(&s) != s`, with the 0x0A carve-out), and it is already in scope in `errors.rs` via the `pub use` at line 89. This is exactly the technique the responder just applied on the Python side for test-3 (`test_pyrt_errors.py:199-202`). ~5 mechanical lines in one test fn; no visibility change, no public-API question, no design input.

**Furthermore:** the duplicated predicate is new in this iteration (the sweep test was added by this change) — a problem this iteration created cannot be silently deferred.

**Assessment:** fails Q2 → do-now. Disposition wrong on three counts: mislabeled Fixed, claimed TODO artifacts absent, and the deferral itself fails the rubric.

## Other findings walk

### correctness-1 — Fixed
Claim: raw invisible C1 bytes (0xC2 0x9B etc.) in `tests/test_pyrt_errors.py:25-27` and the extended-set input; consequence: cross-language pin unverifiable by inspection.
Verification: lines 25-27 now read `""` / `""` / `""` as visible escape sequences; full-file codepoint scan (`grep -P` over U+0080–U+009F, bidi, zero-width, LS/PS sets) finds zero raw escape-set chars in the file. Accept.

### correctness-2 — Fixed
Claim: raw U+009B silently removed from `no_raw_controls_in_output` input, making the C1 clause vacuous vs the Rust twin.
Verification: input at `test_pyrt_errors.py:178` now contains visible ``, matching Rust twin `errors.rs:369` (`\u{009b}`). The responder's counter-narrative (byte present but invisible, vs reviewer's "removed") is immaterial — the fixed state is exactly what both reviewers asked for, and the C1 clause is no longer vacuous. Accept.

### security-1 — Fixed
Same fix as correctness-1. Claim: raw CSI (U+009B) in source is live terminal escape injection when displayed. Codepoint scan confirms no raw C0/C1/bidi/zero-width chars remain anywhere in `tests/test_pyrt_errors.py`. The optional repo-lint suggestion was not taken; it was optional. Accept.

### security-2 — Fixed
Claim: two `{e}` interpolations of PyErr text unescaped at `cross_cdylib.rs:278` and `:356`.
Verification: `escape_control_chars(&e.to_string())` now wraps the `_with_source_unchecked` lookup failure (`cross_cdylib.rs:279`), the Span type lookup failure (`:358`), and a third structurally identical SourceText lookup site (`:392`) the reviewer did not cite. Exceeds the asked fix. Accept.

### security-3 — Won't-Do
Claim: TAB in CST-bridge TypeError text now passes through (was escaped); consequence limited to TSV/column spoofing in log pipelines.
Verification: design §Part (a) (design.md:61) explicitly calls out "TAB in type/attribute names now passes through (was escaped)" as a deliberate, approved alignment decision; the reviewer itself recorded the finding "so the disposition is on the record, not as a defect demanding change" and stated "Fix: None required if the design disposition stands." Rationale cites the approved design, not mere scope. Accept.

### test-1 — Fixed
Same fix as correctness-2; C1 coverage in the Python sweep restored with a visible escape. The sweep is no longer vacuous on the C1 branch. Accept.

### test-2 — Fixed
Claim: U+206A (one above the LRI–PDI range) untested as passthrough.
Verification: `escape.rs:204-205` adds the `\u{206a}` passthrough assertion in `passthrough_boundary_chars`; `test_pyrt_errors.py:109` mirrors it. Both backends fenced. Accept.

### test-3 — Fixed
Claim: Python sweep hardcodes the escape-set predicate, duplicating `_needs_escape`; drift hazard.
Verification: `test_pyrt_errors.py:199-202` now uses `_needs_escape` as the oracle (`assert not (_needs_escape(cp) and cp != 0x0A)`), imported at line 8. The 0x0A carve-out is correct: LF is in the escape set but appears raw as the message's line separator. Accept.

### reuse-2 — Fixed
Same change as test-3; the duplicated Python predicate is gone. Accept.

### quality-1 — Fixed
Claim: `escape_control_chars_table` / `escape_control_chars_empty` duplicated in `errors.rs` after the move to `escape.rs`.
Verification: both deleted from `errors.rs`; pointer comment at `errors.rs:312-313`; re-export still exercised by the `format_error_message_*` tests (56 pass in `fltk-parser-core`). Accept.

### quality-2 — Fixed
Claim: `pub mod escape` creates an unintended second published API path on `fltk-cst-core`.
Verification: `#[doc(hidden)]` with explanatory comment at `lib.rs:4-5` — the reviewer's own stated pragmatic fix (hidden marker without breaking the inter-crate `pub use`). Accept.

### Test gates
`uv run pytest tests/test_pyrt_errors.py`: 25 passed. `cargo test -p fltk-cst-core --no-default-features`: 38 passed. `cargo test -p fltk-parser-core`: 56 + 13 passed.

## Disputed items

- **reuse-1 / TODO(rust-escape-sweep-oracle):** disposition fails on artifact check (claimed TODO does not exist in code or `TODO.md`) and on the rubric (Q2 no — `escape_control_chars` is usable as the oracle in `errors.rs` today, no visibility change needed, same technique as the Python fix). Need: rewrite the `is_escaped_set` predicate in `format_error_message_no_raw_extended_set_in_output` (`crates/fltk-parser-core/src/errors.rs:397-405`) to use `escape_control_chars` as oracle and remove the duplication — OR, if there is a concrete reason this cannot be done now, state it and create the actual TODO artifacts (both `TODO.md` entry and `TODO(slug)` comment). Either way the disposition label must reflect what was actually done.

## Approved

11 of 12 findings: 9 Fixed verified, 1 Won't-Do sound (security-3), 1 Fixed-beyond-ask (security-2 covered a third uncited site).

---

## Verdict: REWORK

One disposition wrong (reuse-1: phantom TODO, fails do-now rubric). Round 1.
