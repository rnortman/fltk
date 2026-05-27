# Deep Correctness Review — Phase 2 Nested Enum PoC

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 5ee6eb4 (base 0f9b786).
Scope: `src/cst_poc.rs`, `src/lib.rs`, `tests/test_rust_cst_poc.py`.

## No findings.

Logic traced; control/data flow correct. Verified by reasoning + compilation (pyo3 0.23.5, clean) + 44 PoC tests + 7 untested-edge-case probes + full suite (497 passed).

## Trace notes (verification, not defects)

- `child_name`/`child_*`: `count != 1` → error; capture `found` only at `count == 1`. `maybe_*`: `count > 1` → error; both branches correct, no off-by-one. Confirmed empty/one/two-child paths.
- `__eq__`: non-same-type → `NotImplemented` → Python identity fallback → `False`. Confirmed `Identifier == Items`, `Identifier == 5`, `!=` all correct. Children/span compared via Python `==`; recurses into nested-node `__eq__` (no hash needed). Confirmed nested-node equality.
- `Py<PyList>` `#[pyo3(get)]`: same object across accesses; external `ref.append(...)` visible to per-label accessors; `child()` tuple identity-shared with `children[0]`. Central hypothesis holds.
- None-label filtering: `tup.get_item(0).eq(&label_obj)` with stored `None` → `False`; cross-enum-variant (`item` vs `no_ws`) correctly excluded. Both directions confirmed.
- `extend`/`extend_*`: iterate input only, append to backing list; no iterate-and-mutate on same list. `clone_ref` of `None` per iteration correct. Accepts any iterable (generator, str); non-iterable → `TypeError`.
- All methods `&self`; mutation via `Py::bind`. No `&mut self` reentrancy/borrow hazard.
- `Items` per-label methods (20) mechanically identical to `Identifier`; label constants and error-message stems substituted correctly per variant. Spot-checked all four labels.
- `lib.rs`: registration order irrelevant to `type_object`-based `#[classattr]`; existing Span/SourceText registration unchanged, no regression.
