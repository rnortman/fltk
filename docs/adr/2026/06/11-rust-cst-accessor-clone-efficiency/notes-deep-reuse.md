Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 1eb2580

## reuse-1

File: `fltk/fegen/gsm2tree_rs.py:1442-1455` and `1474-1487`

The `(count, first)` lock-scope scan block — 13 lines including the lock acquire, loop, and tuple return — is emitted verbatim in both `child_<label>` (lines 1442-1455) and `maybe_<label>` (lines 1474-1487) inside `_per_label_methods`. The only interpolated value in those 13 lines is `{label_enum_name}::{rust_variant}`, which is identical across both call sites. No existing helper factors this out.

Existing function: none — the duplication is new in this commit.

Consequence: the two emitters will diverge if the lock-scope comment wording, variable names, or loop structure change for one but not the other. Already happened in a minor form: the lock-scope comments at lines 1440-1441 and 1472-1473 are textually identical and copied rather than shared. Any future edit to the scan shape (e.g. an early-exit optimization at count == 2) must be applied in two places or it silently affects only one of the two generated methods.

A private helper such as `_emit_count_first_scan_lines(label_enum_name: str, rust_variant: str) -> list[str]` returning the 13-line block would eliminate the duplication and make future modifications single-site.
