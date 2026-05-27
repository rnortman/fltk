Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 6a0553c. Rework commit: 5f89161.

Disputed items only.

---

## errhandling-1

- Disposition: Fixed
- Action: `src/cst_poc.rs` — replaced `found.unwrap()` with `found.expect("invariant: count==1 but found==None; logic error")` in all five `child_*` methods (`child_name`, `child_item`, `child_no_ws`, `child_ws_allowed`, `child_ws_required`).
- Severity assessment: Without this, a broken `count`/`found` invariant in a future refactor produces a zero-context panic. The expect message identifies the class of bug immediately.

---

## errhandling-3

- Disposition: Fixed
- Action: `src/cst_poc.rs` — added `.map_err(|e| PyTypeError::new_err(format!("NodeType.method_name: children[{idx}] is not a tuple: {e}")))` to all `downcast::<PyTuple>()` calls in `children_*`, `child_*`, and `maybe_*` methods for both `Identifier` (3 methods) and `Items` (12 methods). Loop variable changed from `item` to `(idx, item)` via `.enumerate()`.
- Severity assessment: Without this, a corrupted children list (non-tuple element) surfaces a terse PyO3 downcast error with no node type, method name, or index. The fix makes misuse diagnosable at the point of the accessor call.

---

## efficiency-3

- Disposition: Fixed
- Action: `src/cst_poc.rs` — added `else { break; }` branch after `count == 1` capture in all `child_*` and `maybe_*` methods (10 methods total). Changed `"have {count}"` to `"have at least 2"` in the `maybe_*` error paths (5 methods), using a string literal instead of `format!` to satisfy clippy. Updated `tests/test_rust_cst_poc.py:124` to match new error message.
- Severity assessment: Without this, every `child_*`/`maybe_*` call scans the full children list even after `count >= 2`. Phase 3 generated code with N node types each accessed per grammar match inherits this O(n) scan per accessor call.
