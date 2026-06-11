# Request: stop cloning the full children Vec in Python-facing CST accessors

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Efficiency refactor — generator template edit in `fltk/fegen/gsm2tree_rs.py` + regeneration. No API or behavior change.

**Origin:** TODO.md slug `rust-cst-accessor-clone-efficiency`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 7, USER DECISION: Do). The user flagged possible interaction with the children-list-view/named-mutators question; resolved: the named-mutators work (`docs/adr/2026/06/11-cst-named-mutators/`) adds write methods only and does not touch these read paths — no conflict, no ordering dependency.

## Background

Scope is the `#[pymethods]` (Python-callable) accessors ONLY. The native GIL-free accessors were already made zero-alloc during the idiomatic-CST-API deep review (disposition `efficiency-1`); see `exploration-accessor-clone-archaeology.md` in this dir for the full history — this TODO is the deliberately deferred pymethod half, not a regression.

Current pattern (full facts in `exploration.md`): clone the ENTIRE children `Vec` under the read guard, drop guard, then filter/index the snapshot — O(total-children) Arc/Span/label clones per call regardless of match count:
- `_generic_child` (`gsm2tree_rs.py:1011-1036`) — generic `child()` pymethod.
- `_per_label_methods`: `children_<label>` (1387-1404), `child_<label>` (1410-1435), `maybe_<label>` (1440-1459).

All four carry `TODO(rust-cst-accessor-clone-efficiency)` comments; remove them with the fix.

## Fix shape — CORRECTED from the TODO text

The TODO says "filter inside the read guard" is mechanical. Validation found that is WRONG for the per-label methods: they must call `to_pyobject` per match, which performs Python work (Py::new / registry calls), and the project has a hard documented invariant — **no Python work while holding a node lock** (enforced and commented at `_span_getter_setter` `gsm2tree_rs.py:836-851`, `_children_getter` 887-909, `_generic_extend_children` 988-1009). The correct shapes:

- Per-label methods: under the read guard, compare labels (cheap) and clone ONLY matching entries; drop guard; call `to_pyobject` outside. O(matching) clones instead of O(total).
- `child()`: under the guard, check `len`; clone only `children[0]`; drop guard; convert outside. (For len != 1 error paths: count under guard, no cloning.)

Preserve the existing comment style documenting lock scope at each emitted site.

## Constraints / non-goals

- Zero behavior change: identical results, identical errors, identical API.
- Do not touch native accessors (`_native_per_label_methods`) — already fixed.
- The lock-discipline invariant is non-negotiable; reviewers should reject any Python call under a guard.

## Verification expectations

- Regenerate ALL generated outputs (in-tree `src/cst_*.rs`, fixture crates); `make fix`.
- Existing accessor/identity tests pass unchanged (`tests/test_phase4_rust_fixture.py` etc.).
- `uv run pytest` + `cargo test` clean. No new tests strictly required (no behavior change), but a test asserting accessor results on a node with many non-matching children is welcome as a regression pin.
