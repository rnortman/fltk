# Error Handling Review — Phase 2 Nested Enum PoC

Commit reviewed: 5ee6eb4

## errhandling-1

- **File:line**: `src/cst_poc.rs:180`, `src/cst_poc.rs:251`, `src/cst_poc.rs:350`, `src/cst_poc.rs:421`, `src/cst_poc.rs:493`, `src/cst_poc.rs:565`, `src/cst_poc.rs:637` (every `child_<label>` and generic `child` method)
- **Broken path**: `found.unwrap()` after a branch that guarantees `count == 1`. If `count == 1`, `found` is set to `Some(...)` on the first matching tuple. The logic is correct under the assumption that no iteration error occurs mid-loop and that the loop body runs atomically. However, the invariant is implicit and not asserted — if a future refactor makes `found` reachable as `None` with `count == 1` (e.g., short-circuiting or an off-by-one in a clone), the `unwrap()` panics with a non-diagnostic message.
- **Why**: The `?` in the loop body can propagate an error early, but only before `count` is incremented; if it propagated after count increment but before `found` assignment, `count` and `found` would disagree. Currently the two statements are adjacent and this can't happen, but the code does not document or assert the invariant. The `unwrap()` itself is safe today; the issue is that the only indication of why it is safe is the reader tracing the logic manually.
- **Consequence**: Latent: if the invariant breaks in a future edit, the panic message is "called `Option::unwrap()` on a `None` value" with no context about which node type, which label, or what the actual child count was — completely non-diagnostic for on-call.
- **Required change**: Replace `found.unwrap()` with `found.expect("invariant: count==1 but found==None; logic error in child_<label>")`, or refactor to eliminate the separate `found`/`count` variables by returning early on the first hit and erroring if a second is seen. The latter removes the `unwrap` entirely and is the correct fix.

---

## errhandling-2

- **File:line**: `src/cst_poc.rs:76-88`, `src/cst_poc.rs:246-258` (`new` constructors for `Identifier` and `Items`)
- **Broken path**: When `span` is `None`, the constructor imports `fltk._native` and calls `getattr("UnknownSpan")`. Both `py.import(...)` and `.getattr(...)` can fail with `PyErr`. The `?` propagates those as `PyResult::Err`, which surfaces to Python as an `ImportError` or `AttributeError` on `Identifier()` / `Items()` construction. That is technically correct behavior — PyO3 propagates `PyResult::Err` to the Python caller.
- **Why this is a finding**: The error message the Python caller receives ("No module named 'fltk._native'" or "module 'fltk._native' has no attribute 'UnknownSpan'") carries no context indicating that it occurred while constructing the default span for `Identifier`. A caller that catches `ImportError` expecting it to come from their own import, not from inside a `Identifier()` constructor, will be confused. The import happens at construction time (not module load time), so the error is deferred and unexpected.
- **Consequence**: If the native module is partially initialized or `UnknownSpan` is renamed, every `Identifier()` / `Items()` call with no `span` argument raises an opaque `ImportError`/`AttributeError` with no mention of "default span" or which node type triggered it. Diagnostic time increases.
- **Required change**: Wrap the import/getattr block to add context: propagate as `PyRuntimeError` with message like `"Identifier.__new__: failed to obtain default UnknownSpan from fltk._native: {original}"`. Alternatively, cache `UnknownSpan` at module registration time in `lib.rs` and pass it into the constructors, eliminating the per-call import.

---

## errhandling-3

- **File:line**: `src/cst_poc.rs:154` (and all `children_<label>` methods: lines ~221, ~320, ~391, ~463, ~535, ~607)
- **Broken path**: In `children_name`, `children_item`, etc., each element of `self.children` is accessed via `item.downcast::<PyTuple>()`. If any element is not a `PyTuple` — which is possible because `children` is a `Py<PyList>` with `#[pyo3(get)]` exposing a mutable reference to Python code (the test at line 769 explicitly appends a raw Python tuple `("x", "y")` directly to `node.children`) — the `?` propagates a `PyDowncastError` as `PyErr`. The error message from PyO3's downcast failure is "expected tuple, got <type>", with no indication of the node type, the method name, the index in the list, or what the actual element was.
- **Why**: `children` is exposed as a settable list (`#[pyo3(get)]` allows Python code to replace or mutate the list contents arbitrarily). The code assumes every element is a 2-tuple but does not enforce this. When the invariant is violated, the `?` propagates a terse internal PyO3 error.
- **Consequence**: A caller that incorrectly mutates `node.children` gets a `TypeError: expected tuple, got X` with no stack context pointing to the node type or method. Misuse that corrupts a CST mid-parse would surface only when a label accessor is called, not at the point of insertion, making root-cause location hard.
- **Required change**: On downcast failure, propagate a `PyTypeError` with context: `"Identifier.children_name: children list element at index {i} is not a tuple (got {type}); the children list must not be mutated with non-tuple elements"`. Alternatively, validate in `append`/`extend` that the child is not itself already a `(label, child)` tuple when appended without explicit label — but the downcast guard in accessors is the safety net and must carry context.

---

No findings of silent swallowing, `let _ =` on `Result`, empty `catch`, or default-on-error fallback without log. All `PyResult` errors propagate to the Python caller. The three findings above concern: (1) a latent `unwrap` that would give a non-diagnostic panic, (2) context-free import errors surfaced from constructors, and (3) context-stripped downcast errors from corrupted children lists.
