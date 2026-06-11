# Adversarial Validation: `abi-gate-test-consolidation` TODO

Concise. Precise. No fluff, no prescriptions — facts grounded in file:line.

## Subprocess count: the TODO's claim is wrong

The TODO at `tests/test_rust_span.py:427` says "three separate subprocesses (one per scenario:
ABI-string mismatch, layout mismatch, control)."

The actual class `TestSpanPathAbiGate` (line 417) has **five** test methods, each spawning one
subprocess via `_run_script` (line 432–440):

| Line | Method | Scenario |
|------|--------|----------|
| 442 | `test_control_no_patch_passes` | no patch, success |
| 466 | `test_abi_string_mismatch_raises_type_error` | wrong `_fltk_cst_core_abi` string |
| 501 | `test_layout_mismatch_raises_type_error` | wrong `_fltk_cst_core_abi_layout` integer |
| 539 | `test_missing_abi_marker_raises_type_error` | `_fltk_cst_core_abi` absent entirely |
| 578 | `test_missing_layout_attr_raises_type_error` | `_fltk_cst_core_abi_layout` absent entirely |

Five subprocesses, not three. The TODO was written when only three scenarios existed; two were added
later without updating the TODO text.

## GILOnceCell error-caching premise: correct

`get_or_try_init` source at
`~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/pyo3-0.23.5/src/sync.rs:205–232`:

```rust
pub fn get_or_try_init<F, E>(&self, py: Python<'_>, f: F) -> Result<&T, E> {
    if let Some(value) = self.get(py) {
        return Ok(value);
    }
    self.init(py, f)
}

fn init<F, E>(&self, py: Python<'_>, f: F) -> Result<&T, E> {
    let value = f()?;   // early-return on Err — cell NOT written
    let _ = self.set(py, value);
    Ok(self.get(py).unwrap())
}
```

If `f()` returns `Err`, the `?` propagates and `set` is never called — the cell stays uninitialised.
The premise is accurate: `GILOnceCell::get_or_try_init` does **not** cache errors.

The relevant cell is `FLTK_NATIVE_SPAN_TYPE` (cross_cdylib.rs:249), populated by `get_span_type`
(line 292–362) via `get_or_try_init` (line 294). An ABI-mismatch `TypeError` from the closure
leaves this cell empty, so the next call to `get_span_type` re-runs the full check.

`IS_CANONICAL_CDYLIB` (line 191) is also populated by `get_or_try_init` (line 209); it calls
`get_span_type` as a sub-step, so it too remains unpopulated if the ABI check fails.

## What each subprocess actually does — startup cost

`_run_script` (line 432–440) invokes `sys.executable -c <script>` with a 30-second timeout.
Each script:

1. Imports `fltk._native` (loads the `.so`, runs pyo3 module init).
2. Optionally patches `native.Span` with a `FakeSpan`.
3. Imports `phase4_roundtrip_cst` (loads a second `.so`).
4. Constructs a node, reads `node.span` (triggers `get_span_type` and the ABI gate).
5. Checks the outcome, prints "OK" or "FAIL".

Both `.so` loads happen in every subprocess. Python startup + two extension-module loads is the
dominant cost. There is no database, network, or heavy computation.

## Would consolidation actually work?

In a single subprocess you could:
1. Run the first error scenario (patch → `node.span` → expect `TypeError`). `FLTK_NATIVE_SPAN_TYPE`
   remains unpopulated.
2. Re-patch with a different `FakeSpan`, run again — each `node.span` triggers the full check fresh.
3. Run remaining error scenarios in any order.
4. Remove the patch, run the success scenario last — `FLTK_NATIVE_SPAN_TYPE` populates on success
   and stays populated for subsequent accesses.

The test class docstring (lines 424–428) already describes this sequence explicitly.

Complication: `native.Span` is replaced at module level (`native.Span = FakeSpan`). Restoring it
requires keeping a reference to the original (`orig = native.Span`) and re-assigning after each
scenario. The scripts do not currently do this.

A second complication: `phase4_roundtrip_cst` is imported once per subprocess, before patching in
some scripts (lines 484–485 import it *after* patching `native.Span`; others import it before
constructing the node but after patching). The consumer cdylib resolves `fltk._native.Span`
at its own module import time or at first use — the exact interaction would need verification. In
the current per-subprocess structure this is not an issue because each subprocess starts fresh.

## Readability: would consolidation be more complex?

Each current subprocess script is ~15 lines with a single clear assertion. A consolidated script
would need to restore `native.Span` between scenarios and handle import ordering carefully (since
`phase4_roundtrip_cst` can only be imported once per process). That is a non-trivial control-flow
increase for a test whose job is to verify ABI-failure isolation behaviour.

## Deeper structural observation

The need for subprocess isolation is architectural: `GILOnceCell` statics are process-global and
cannot be reset from Python. There is no API to clear `FLTK_NATIVE_SPAN_TYPE`. Consolidation would
work only because errors don't cache — a subtle invariant. If that property ever changed (e.g.,
caching errors for performance), the consolidated test would silently become incorrect. The
per-subprocess structure is immune to that risk.

## Any blockers to consolidation?

No hard blockers. The `get_or_try_init`-doesn't-cache-errors invariant holds in pyo3 0.23.5.
The practical obstacle is the import-ordering subtlety with `phase4_roundtrip_cst` and the need
to restore `native.Span` between scenarios within a single process — doable but fragile.

## Summary

- Subprocess count in the TODO: **wrong** — 5, not 3.
- "GILOnceCell does not cache errors" premise: **correct** (pyo3 0.23.5 sync.rs:228 — `f()?` on
  error never calls `set`).
- Startup cost per subprocess: two `.so` loads + Python init; modest but real.
- Readability claim: **correct** — consolidation requires within-process `native.Span` state
  restoration and import-order coordination, increasing test complexity non-trivially.
- Deeper issue: the per-subprocess structure provides immunity to the invariant being broken; the
  consolidation depends on a subtle property of `get_or_try_init` that is not under this project's
  control.
