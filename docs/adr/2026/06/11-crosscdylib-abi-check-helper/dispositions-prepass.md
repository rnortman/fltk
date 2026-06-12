slop-1:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: no findings reported; nothing to address.

scope-1:
- Disposition: Fixed
- Action: deleted lines 78–79 (`// TODO(crosscdylib-abi-check-helper): the two-step ABI pair check below duplicates / // \`get_span_type\`'s validation; extract a generic helper to unify them.`) from `crates/fltk-cst-core/src/cross_cdylib.rs`. All three TODO comment sites now removed; finding was correct that one survived.
- Severity assessment: stale TODO comment after completed work misleads future readers and breaks TODO-burndown tooling by showing a done item as outstanding.
