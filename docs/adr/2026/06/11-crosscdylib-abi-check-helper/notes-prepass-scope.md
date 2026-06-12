## scope-1

File: `crates/fltk-cst-core/src/cross_cdylib.rs` line 78 (HEAD)

Expected: design §4 — "Delete the three `TODO(crosscdylib-abi-check-helper)` comments (lines 36–37, 81–82, 304–307)". All three removed.

Actual: The comment at original lines 81–82 (`// TODO(crosscdylib-abi-check-helper): the two-step ABI pair check below duplicates / // \`get_span_type\`'s validation; extract a generic helper to unify them.`) survives in HEAD verbatim. The other two sites (36–37, 304–307) were correctly deleted.

Consequence: The TODO comment now refers to work that has already been done — the helper was extracted in this very commit. It is stale and misleading to any future reader, implying the duplication still exists when it does not. It will also cause TODO-audit tools or burndown checks to find a completed item as still outstanding.

Suggested fix: Delete lines 78–79 in HEAD (`crates/fltk-cst-core/src/cross_cdylib.rs`). The surrounding comment block (explaining the slow path and `FLTK_FOREIGN_SOURCE_TEXT_TYPE` caching) stands without these two lines.
