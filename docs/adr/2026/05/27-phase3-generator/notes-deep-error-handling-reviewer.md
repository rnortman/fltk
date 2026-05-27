Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

**errhandling-1**

File: `fltk/fegen/gsm2tree_rs.py:51`

Path: `generate()` indexes `self._py_gen.rule_models[rule.name]`.

`rule_models` is a `dict[str, ItemsModel]` populated by `CstGenerator.__init__`. If a rule in `self.grammar.rules` is absent from `rule_models` — possible if `CstGenerator` silently skips rules it cannot model (e.g., rules with no types hit `RuntimeError` at `gsm2tree.py:117-122`, but the generator could be extended or there could be a mismatch between the grammar passed to `CstGenerator` and `self.grammar`) — this raises an unadorned `KeyError` with only the rule name as context, no indication that this is a generator internal error vs bad grammar input. Same pattern repeated at line 405 in `_register_classes_fn`.

Consequence: on-call sees a bare `KeyError: 'some_rule'` with no stack annotation indicating it came from the Rust generator, no mention of which grammar, and no guidance on whether the grammar is malformed or the generator has a bug. In practice the error propagates up through pytest as an unhandled exception but without context about what failed in the generation pipeline.

Fix: either catch `KeyError` and re-raise with `RuntimeError(f"No model for rule {rule.name!r}; grammar analysis produced: {list(self._py_gen.rule_models)}")` or assert the invariant explicitly. Since the two loops over `self.grammar.rules` use the same `_py_gen`, the invariant that every rule has a model should hold by construction — making this an invariant violation (assert/panic territory), not expected bad input.

---

**errhandling-2**

File: generated Rust (template in `gsm2tree_rs.py:177-188`), present in every `new()` in `cst_generated.rs` and `cst_fegen.rs`.

Path: `UNKNOWN_SPAN.get(py).expect("UNKNOWN_SPAN not initialized; fltk._native module not loaded")`

`GILOnceCell::get` returns `Option<&T>`; `.expect` on `None` panics with an abort that terminates the Python interpreter — unrecoverable from Python. This occurs when a CST node class is constructed before the `_native` module's `#[pymodule]` initializer has run (e.g., in a test that imports a class from `fltk._native.fegen_cst` before importing `fltk._native`, or if the module is embedded in a larger app where init ordering differs).

The panic message is adequate for diagnosis (`"UNKNOWN_SPAN not initialized; fltk._native module not loaded"`). The real question is whether this should be a panic or a `PyResult` error. Panicking in a `#[new]` method that is `PyResult<Self>` causes PyO3 to convert the panic to a Python `PanicException`, which is catchable — this is therefore recoverable from Python's perspective and arguably should be `Err(PyRuntimeError::new_err(...))` instead of a panic, so calling Python code can handle it without crashing. However, this is inherited from the Phase 2 hand-written code and is intentional design. The consequence is a hard crash if module init ordering is wrong, rather than a graceful `RuntimeError`. Low risk given the current import structure, but a latent footgun for future embedders.

No immediate fix required unless the "crash on init-order mistake" behavior is deemed unacceptable; if it is, replace `expect` with `ok_or_else(|| PyRuntimeError::new_err(...))` and propagate via `?`.

---

**errhandling-3**

File: `src/lib.rs:26-28`

Path: `UNKNOWN_SPAN.set(m.py(), unknown_span_obj).expect("UNKNOWN_SPAN already set; module initialized twice")`

`GILOnceCell::set` returns `Err` if the cell is already occupied. The `.expect` panics, aborting the interpreter if the module is re-initialized (e.g., sub-interpreter, extension reloading, or a bug in the embedding). The error message is accurate. This is an invariant violation (module-init-twice is a programming error, not expected input), so panicking is arguably correct. However, PyO3's `#[pymodule]` framework should prevent this from occurring in normal use; the panic is effectively dead code in practice.

No change needed unless the embedding context requires graceful recovery from double-init, in which case: return `Err(PyRuntimeError::new_err("UNKNOWN_SPAN already initialized"))` instead.

---

**errhandling-4**

File: generated Rust (template in `gsm2tree_rs.py:323`), present in every `child_{label}` in `cst_generated.rs` and `cst_fegen.rs`.

Path: `found.expect("invariant: count==1 but found==None; logic error")` at the bottom of every `child_{label}` method.

The invariant (`count == 1 implies found.is_some()`) holds by construction: `found` is set exactly when `count` becomes 1. The `expect` is a correct sentinel for this invariant and the message is informative. This is appropriate panic-on-invariant-violation.

The concern: in the generated Rust, the `expect` message does not include `class_name` or `label`, making it hard to identify which method panicked if this ever fires. The message `"invariant: count==1 but found==None; logic error"` appears identically in every generated method across every class. A backtrace will distinguish them at the Rust level, but it adds diagnostic work.

Not a blocking issue; consider embedding class and label in the message: `"invariant: {ClassName}.child_{label}: count==1 but found==None"`.

---

**errhandling-5**

File: `tests/test_gsm2tree_rs.py:208-213` (fixture `fegen_source`)

Path: `assert result is not None, "fegen.fltkg failed to parse"` followed by un-guarded `cst2gsm.visit_grammar(result.result)`.

The assert is appropriate for a test. However, if `visit_grammar` raises (grammar semantic errors), the exception propagates as an unadorned `Exception` from within the `fegen_source` fixture, which pytest will surface as a fixture-setup error with full traceback. This is adequate for tests — not an error handling issue in production code.

No finding here; test infrastructure is out of scope unless it masks real errors. It does not.

---

**errhandling-6**

File: `src/lib.rs:42-44`

Path:
```rust
let sys = m.py().import("sys")?;
sys.getattr("modules")?.set_item("fltk._native.fegen_cst", &fegen_sub)?;
```

`import("sys")` failing is practically impossible in CPython but theoretically possible in embedded or stripped interpreters. `getattr("modules")` failing on `sys` is equally pathological. Both errors propagate via `?` as `PyResult::Err` back to the `#[pymodule]` initializer, causing module import to fail with a `PyErr`. The error from `import("sys")` or `getattr("modules")` would be a `ModuleNotFoundError` or `AttributeError` with no added context about what was being attempted (registering the fegen submodule in `sys.modules`).

Consequence: if this path fails, Python import of `fltk._native` fails entirely, with an error that does not mention `fltk._native.fegen_cst` or submodule registration. The on-call engineer sees `AttributeError: module 'sys' has no attribute 'modules'` with no context. This is a corner-case embedded scenario but the error path should wrap with context.

Fix: add `.map_err(|e| PyRuntimeError::new_err(format!("Failed to register fltk._native.fegen_cst in sys.modules: {e}")))` on the `set_item` call.
