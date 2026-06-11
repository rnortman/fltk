Style: concise, precise, complete, unambiguous. No padding.

## scope-1 — Missing benchmark sanity gate (§6 item 8)

File: missing — design §6 item 8 not implemented.

Expected: an informational micro-benchmark in the spike crate measuring traverse performance before/after the `Box`→`Shared` switch (§6 item 8), treated as a gate before Phase 2 builds on the new ownership. Design calls it an "informational gate" and explicitly names the spike crate as the location.

Actual: no benchmark added to `crates/fltk-cst-spike/` in this range or the prior Phase 1 range visible through base (Cargo.toml has no criterion dependency; no bench files).

Consequence: the design's stated pre-condition for Phase 2 ("A surprising regression reopens the parking_lot question before Phase 2 builds on the new ownership") was never evaluated. Phase 2 is now committed on top of unvalidated lock-overhead assumptions. If uncontended `RwLock` overhead is unexpectedly high for the actual grammar shapes, reworking the ownership model post-Phase 2 is significantly more expensive.

Suggested fix: add a `[[bench]]` target in `crates/fltk-cst-spike/Cargo.toml` with a criterion micro-benchmark traversing a non-trivial tree (reads + child access); run it and record the result in the ADR or a comment. Declare the gate passed or note the parking_lot decision explicitly.

---

## scope-2 — Rustdoc docstring emits literal `{enum_name}` instead of the actual enum name

File: `fltk/fegen/gsm2tree_rs.py` line emitting `"/// Rust consumers use the CamelCase \`{enum_name}\` name."` (plain string, not f-string); manifests in every generated output (`src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs`).

Expected (design §4.3 item 6): rustdoc on every generated public item including the label enum, e.g. `/// Rust consumers use the CamelCase \`IdentifierLabel\` name.`

Actual: the line is a plain string literal, not an f-string. All generated label-enum rustdoc blocks contain the literal text `{enum_name}` verbatim.

Consequence: generated rustdoc is wrong — `cargo doc` renders `{enum_name}` as the type name. Incorrect documentation ships in every generated crate.

Suggested fix: change the offending line to an f-string: `lines.append(f"/// Rust consumers use the CamelCase \`{enum_name}\` name.")` and regenerate.

---

## scope-3 — Label-enum rename is a Rust-API breaking change; design authorization verified as present

File: `fltk/fegen/gsm2tree_rs.py` and all five generated outputs — `Identifier_Label` → `IdentifierLabel` (and analogues for every rule).

Noted for auditability per CLAUDE.md's instruction to verify every generated-symbol rename is explicitly design-sanctioned. Design §4.3 item 5 explicitly authorizes the rename, names the `#[pyclass(name = "Identifier_Label")]` preservation mechanism for Python consumers, and §8 records the consequence for Rust-only consumers. The Python-visible name is unchanged; `#[allow(non_camel_case_types)]` is dropped as designed. No finding.

---

## Non-finding notes

- §6 item 7 reserved-label test: `test_children_label_rejected` / `test_non_reserved_label_accepted` are present in the diff at `tests/test_gsm2tree_rs.py` lines 1230–1240 — contrary to the previous notes-prepass-scope.md entry. That earlier file was written before the full diff was reviewed; finding is retracted.
- §6 item 3 identity restorations (`tests/test_phase4_rust_fixture.py`): file not touched in Phase 2 range — consistent with scope (Phase 1 work).
- Makefile `gencode` target includes the `rust_cst_fegen` step — present at HEAD.
- `TODO(rust-cst-children-list-view)` added to `TODO.md` per user A4 — present.
- Per-label native accessors (§4.3 item 2): all five method shapes generated with correct count-before-type-check precedence.
- `CstError` (§4.3 item 4): `error.rs` added, `#[non_exhaustive]`, `Display` + `Error` — all present.
- `Debug` (§4.3 item 1): derived on all generated types; manual `Span` impl eliding source text — present.
- Generic native accessors `kind()`, `set_span()`, `child()`, `extend_children()` (§4.3 item 3): all present on data structs.
