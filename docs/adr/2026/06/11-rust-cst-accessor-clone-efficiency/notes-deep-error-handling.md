No findings.

Commit reviewed: 1eb2580

Notes:

- `child_<label>` emitter (`gsm2tree_rs.py:1461`): the `first.expect("invariant: ...")` call is sound. It is guarded by `if count != 1 { return Err(...) }`, so `expect` is only reached when `count == 1`, which implies `first == Some(...)` by the loop's `if count == 1 { first = Some(...) }` assignment. The invariant message names the class and label; if somehow reached (impossible barring logic bug in the loop), the panic message is diagnosable. Correct.

- Lock discipline: all four changed emitters (`child`, `children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`) drop the read guard before all Python work (`to_pyobject`, `into_pyobject`, `PyValueError::new_err`, `format!`). The guard scope is a plain Rust block whose last statement is a tuple not involving Python; the guard drops at block end. No Python call inside any lock scope in the changed code.

- `set_span` pymethod (`cst_generated.rs:392-394`): calls `extract_span(py, value)` — a Python method call — while the write guard is live on the same line (`self.inner.write().span = ...`). This is a pre-existing lock-discipline violation not introduced by this diff; out of scope for this review.

- `extend` pymethod loop (`cst_generated.rs:471-476`): acquires and drops the write lock per iteration while the outer `py` handle is held. Pre-existing; not changed in this diff.

- `children_<lbl>`: on `to_pyobject` failure mid-list the partial `PyList` is discarded and the error propagated via `?`. No silent partial result.

- `maybe_<lbl>`: `count > 1` check raises without converting `first`. Error type and message are unchanged from before (design §Edge cases confirms this is deliberate and unobservable). The `count == 0` → `None` branch cannot return a stale `first` because the loop only sets `first` when `count == 1`, and `count == 0` means the loop never matched.

- Error messages all carry necessary context: class name in `expect` messages, label name and count in `PyValueError` messages. Errors propagate directly to Python caller via `PyResult`; no wrapping needed.
