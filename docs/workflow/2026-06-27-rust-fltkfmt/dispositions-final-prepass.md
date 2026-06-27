# Dispositions — final pre-pass QA (round 1)

Commit reviewed: 7a699c396903a618711132240392279d52bcbc51
Notes: notes-final-slop.md, notes-final-scope.md

slop-1:
- Disposition: Fixed
- Action: Added `check_with_output_is_rejected` unit test in `crates/fltk-fmt-cli/src/lib.rs` (alongside the other rejection tests, before `output_with_multiple_inputs_is_rejected`). Confirmed the `validate()` `--check`+`--output` branch (lib.rs:104-106) exits 2. `cargo test -p fltk-fmt-cli` passes (33 tests).
- Severity assessment: Low. The behavior was already correct; this was a missing regression guard for one of six `validate()` rejection branches. Without it a future change to dispatch order in `run_inner` could silently regress unnoticed.

slop-2:
- Disposition: Fixed
- Action: Replaced the hollow `identity` stub docstring ("returns the source unchanged") with a why-focused one ("No-op transform: used to verify `--check` exits 0 when input is already formatted") in `crates/fltk-fmt-cli/src/lib.rs:580`.
- Severity assessment: Trivial. Cosmetic comment quality; no behavioral impact.

(notes-final-scope.md: no findings.)
