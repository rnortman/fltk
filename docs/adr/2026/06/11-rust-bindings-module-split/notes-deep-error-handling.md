Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 4fe645d

---

## errhandling-1

**File:** `crates/fltk-cst-core/src/py_module.rs:77`

**Broken error path:** `parent.name()?` propagates a `PyErr` when pyo3 cannot retrieve the module's `__name__`. The `?` exits `register_submodule` with that error, and in `src/lib.rs:32-35` the caller chains `?` again, aborting the entire `#[pymodule]` init with a bare pyo3 Python exception.

**Why:** The `parent.name()` failure path is silent — no context is attached. The caller at `src/lib.rs:32` writes:

```rust
register_submodule(m, "poc_cst", cst_generated::register_classes)?;
```

If `parent.name()` returns an error, Python sees whatever low-level pyo3/CPython exception `name()` internally raises (likely `AttributeError` or an empty string failure), with no indication of which submodule registration was in progress, which crate, or what the parent was expected to be. The `PyRuntimeError` with context is only wrapped around the final `set_item` call (line 93-96); the earlier `?` on `parent.name()` (line 77) has no wrapping at all.

**Consequence:** On-call cannot distinguish "module name retrieval failed" from "class registration failed" from "sys.modules insertion failed". The error message Python surfaces will be pyo3-internal, not actionable. The failure is deterministic (build-time bug category), so diagnosis is theoretically possible by reading source, but the error message provides no path to that source.

**What must change:** Wrap the `parent.name()?` failure with a contextual `PyRuntimeError`:

```rust
let raw_parent_name: String = parent
    .name()
    .map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "register_submodule({name:?}): failed to get parent module name: {e}"
        ))
    })?
    .to_string();
```

---

## errhandling-2

**File:** `crates/fltk-cst-core/src/py_module.rs:81-82`

**Broken error path:** `register(&sub)?` and `parent.add_submodule(&sub)?` both propagate raw pyo3 errors with no context about which submodule or parent was involved.

**Why:** Both `?` operators sit inside `register_submodule` where the `name` and `parent_name` context variables are in scope. If `register` (i.e., `cst::register_classes` or `parser::register_classes`) fails — e.g., a `#[pyclass]` type cannot be registered due to a pyo3/CPython type-creation error — the error propagates with the internal pyo3 message only. The caller in `tests/rust_cst_fegen/src/lib.rs:21-22` adds no context:

```rust
register_submodule(m, "cst", cst::register_classes)?;
register_submodule(m, "parser", parser::register_classes)?;
```

**Consequence:** A class-registration failure surfaces as an opaque exception with no indication of which submodule (`"cst"` vs `"parser"`), which parent module (`"fegen_rust_cst"`, `"rust_parser_fixture"`, etc.), or which class failed. The doc-comment (lines 64-67) acknowledges partial-init state but does not address the diagnostic gap.

**What must change:** Wrap both `register` and `add_submodule` failures:

```rust
register(&sub).map_err(|e| {
    pyo3::exceptions::PyRuntimeError::new_err(format!(
        "register_submodule: register fn for submodule {qualified_name:?} failed: {e}"
    ))
})?;
parent.add_submodule(&sub).map_err(|e| {
    pyo3::exceptions::PyRuntimeError::new_err(format!(
        "register_submodule: add_submodule({qualified_name:?}) failed: {e}"
    ))
})?;
```

Note: `qualified_name` must be constructed before these calls (currently it is constructed after `add_submodule` succeeds on line 88). Reorder to construct it immediately after `raw_parent_name` is resolved.

---

## errhandling-3

**File:** `src/lib.rs:28`

**Broken error path:** `UNKNOWN_SPAN.set(m.py(), unknown_span_obj).expect("UNKNOWN_SPAN already set; module initialized twice")` — panics on double-init.

**Why:** This panic path existed before this diff; the diff leaves it unchanged. The `expect` message is accurate: double-init is an invariant violation, not a user-input error, and a panic/crash is the correct response. The message includes the reason. This is correctly classified.

**Assessment:** Not a finding — correctly handled invariant violation. Listed for completeness to confirm the diff did not introduce a regression here.

---

## errhandling-4

**File:** `fltk/fegen/gsm2tree_rs.py:79-83`

**Broken error path:** `_RESERVED_CLASS_NAMES` check for `trivia` — the trivia rule is added by `add_trivia_rule_to_grammar` (called in `RustCstGenerator.__init__` on line 63) before validation runs on line 75. The trivia rule is named `"trivia"` (class name `"Trivia"`), which is not in `_RESERVED_CLASS_NAMES`. This is correct and not a problem.

However, the validation loop (lines 75-100) iterates `self.grammar.rules`, which includes the auto-added trivia rule. If any future expansion of `_RESERVED_CLASS_NAMES` adds `"Trivia"`, the trivia rule itself would trigger the check and block generation of any grammar. This is a latent fragility, not a current error-handling bug.

**Assessment:** No finding. The current reserved set is correct and the trivia rule name is not in it.

---

## errhandling-5

**File:** `fltk/plumbing.py:105-111`

**Broken error path:** `_load_rust_cst_classes` catches `ImportError` and re-raises as `RustBackendUnavailableError`, but the error message on line 111 loses the original import error detail:

```python
raise RustBackendUnavailableError(module_name) from exc
```

`RustBackendUnavailableError.__init__` (line 74-78) sets `detail=None`, producing the message `"Rust CST backend selected (module '...') but unavailable"` with no `from` chain visible unless the caller inspects `__cause__`.

**Why:** The `from exc` preserves the chain at the Python exception level, so a traceback will show the original `ImportError`. This is adequate for interactive debugging. For structured logging or programmatic error inspection, the `detail` is None. The docstring comment on line 108-110 explicitly justifies not catching broader `Exception`.

**Assessment:** The `from exc` chaining is sufficient — the original error is accessible via `__cause__`. This is not a finding; the propagation is correct.

---

## errhandling-6

**File:** `fltk/plumbing.py:113-116`

**Broken error path:** When `module_name` is the top-level extension name (e.g., `"fegen_rust_cst"`) rather than the cst submodule (e.g., `"fegen_rust_cst.cst"`), `importlib.import_module` succeeds (the top-level module loads), `classes` is empty (submodule attributes are not `type` instances), and `RustBackendUnavailableError` is raised with `detail="module loaded but exposes no CST classes"`. The docstring (lines 89-91) documents this as the expected behavior.

**Assessment:** Correctly handled. The error is raised with a diagnostic message. Not a finding.

---

## Summary

Two actionable findings (errhandling-1, errhandling-2): both are in `register_submodule` in `py_module.rs`. The `parent.name()?` failure and the `register()`/`add_submodule()` failure paths propagate raw pyo3 errors with no context identifying which submodule registration was in progress. These are build-time deterministic failures (not data-dependent), so the impact is diagnostic difficulty rather than silent corruption. The fix is straightforward context wrapping.

No other error-handling issues found in the diff. The `_RESERVED_CLASS_NAMES` validation, `ImportError` re-raise, and `UNKNOWN_SPAN` double-init panic are all correctly classified and handled.
