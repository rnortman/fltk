# Deep correctness review: fix-forged-abi-segfault

Commit reviewed: 79460b6 (base d82e82f). Diff scope: `crates/fltk-cst-core/src/cross_cdylib.rs`,
`crates/fltk-cst-core/src/span.rs`, `tests/test_rust_span.py`, implementation-log.md.

Mandate: does the code do what it appears to do — logic, control flow, data flow.

## Findings

No findings.

## Logic traced (for the record)

The change adds `check_instance_layout::<SourceText>` (a `__basicsize__` vs
`size_of::<<SourceText as PyClassImpl>::Layout>()` gate) into the cross-cdylib slow path of
`extract_source_text`. I traced every control/data-flow path that the diff touches:

- **Cache-hit branch** (`cross_cdylib.rs:104-110`) — left unchanged, as the design requires.
  `cast_unchecked` on a cached type is sound only if the cache can hold nothing but a
  basicsize-validated type. That invariant is established by the seeding order below, so the
  hit branch needs no re-check. Correct.

- **Cache-miss ordering** (`cross_cdylib.rs:118-127`) — `check_abi_pair` runs first, then
  `check_instance_layout`, then `get_or_init`, then `cast_unchecked`. This is exactly the
  load-bearing order the design (§2.B/§2.D) mandates: the gate runs *before* seeding, so the
  cell can only ever hold a basicsize-validated type. `check_abi_pair` running first preserves
  the pinned ABI/layout diagnostic messages for the existing direct-call suite. No reordering
  bug, no early-return that skips a gate.

- **Accept-branch soundness (genuine foreign SourceText)** — `check_instance_layout`'s
  `expected` is `size_of::<<SourceText as PyClassImpl>::Layout>()`, the *same* expression that
  backs both the `_fltk_cst_core_abi_layout` classattr (`span.rs:137`) and `check_abi_pair`'s
  `expected_layout` (`cross_cdylib.rs:223-224`). A genuine foreign `SourceText` whose
  `__basicsize__` equals `size_of::<Layout>()` (empirically 24, verified in design and pinned by
  the new `test_foreign_source_text_basicsize_matches_native_layout`) passes. No risk of the gate
  spuriously rejecting the legitimate consumer path it must keep working.

- **Trivial-forge rejection** — the §1.1 `Forge` copies the genuine ABI string and the genuine
  layout int (24), so `check_abi_pair` passes; its `__basicsize__` is 32 ≠ 24, so
  `check_instance_layout` returns `TypeError`. Control reaches `TypeError`, never
  `cast_unchecked`. The crash is converted to a clean error. Correct.

- **No-panic discipline** — `check_instance_layout` maps both the `getattr` failure and the
  `extract::<usize>()` failure to a diagnostic `TypeError` via `map_err`; no `unwrap`/`expect` on
  the Python-controlled path. An exotic type with a raising `__getattr__` or a non-int
  `__basicsize__` yields `TypeError`, not a panic. Mirrors `check_abi_pair`. Correct.

- **`extract::<usize>()` on `__basicsize__`** — pyo3 type `tp_basicsize` is non-negative for
  these classes, so the unsigned extract cannot spuriously fail for a genuine type. No data-flow
  hazard.

## Tests

- The only test that can crash on a regression (`test_forged_source_text_raises_type_error`)
  is correctly subprocess-isolated and asserts `returncode == 0` + `"OK"`. A recurrence shows up
  as a crashing subprocess, not a suite takedown.
- `test_forged_source_text_message_is_diagnostic` runs in-process but never reaches
  `cast_unchecked` (the trivial forge is rejected at the gate), so no in-process UB. Its
  `"basicsize" in msg or "layout" in msg` assertion is satisfied by the helper's message
  ("...instance layout check failed: object type __basicsize__ is 32, expected 24...").
- `test_padded_forge_passes_basicsize_gate_boundary` correctly pins only the gate boundary
  (basicsize equality) and explicitly does NOT call `_with_source_unchecked` on the padded
  forge — the right call, since crossing the gate there is UB with no stable outcome to assert.

No off-by-one, wrong-operator, wrong-variable, race, leak, control-flow, or data-flow defect
found in the diff. The `extract_span` path is deliberately left ungated (§2.C); that path is
unreachable by forged objects (its `is_instance`-against-canonical gate plus
`check_abi_pair::<Span>` in `get_span_type`), so omitting the gate there introduces no hazard.
