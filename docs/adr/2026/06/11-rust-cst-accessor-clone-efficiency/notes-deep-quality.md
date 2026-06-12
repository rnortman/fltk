Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 1eb2580

## quality-1

File: `fltk/fegen/gsm2tree_rs.py:1436-1466` (`child_<label>`) and `1468-1500` (`maybe_<label>`)

The 16-line `(count, first)` lock-scope block — 2-line comment plus 14-line scan — is emitted verbatim in both `child_<label>` and `maybe_<label>` inside `_per_label_methods`. The only interpolated token in those 16 lines is `{label_enum_name}::{rust_variant}`, which is identical at both call sites. This duplication is new in this commit; the prior `snapshot` approach had an analogous but distinct structure at each site.

Consequence: any future modification to the scan shape (e.g., an early-exit at `count == 2` for `maybe_<label>`, changes to the invariant-panic message format, or rewording the lock-scope comment) must be applied in two generator locations. Divergence is silent — the generated methods compile and pass tests even when one site is updated and the other is not; only behavioral regression tests covering both methods would catch it. The risk is low today but compounds as the emitter evolves; the `child_<label>` and `maybe_<label>` comment blocks at lines 1440-1441 and 1472-1473 are already textually identical copies.

Fix: extract a private helper, e.g. `_emit_count_first_scan_lines(self, label_enum_name: str, rust_variant: str) -> list[str]`, returning the 16-line block. Both `child_<label>` and `maybe_<label>` call it; the two methods diverge only after the `};` (error condition and conversion differ). The helper is trivially testable: run the emitter and assert the scan block appears identically in both emitted methods.

No findings.
