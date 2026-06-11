# Request: GC/eviction/ABA tests for the CST handle registry

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Test-only. REFRAMED from TODO.md slug `registry-unit-tests` per user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 10, USER DECISION: Do (reframed)).

**Reframe (binding):** The original TODO's goal (Rust unit tests, with three build-workaround options for the libpython linking problem) is DROPPED. Validation showed every registry function irreducibly requires a live Python interpreter (all take `py: Python<'_>`; the registry IS a Python `weakref.WeakValueDictionary` held in a `GILOnceCell` — `registry.rs:34-44`), so Python-side tests are the natural harness, and the linking "blocker" was mostly a missing dev symlink anyway. Do NOT build test cdylibs, ctypes harnesses, or auto-initialize embedding.

## Background

Registry: `crates/fltk-cst-core/src/registry.rs` — guarantees at most one live Python handle per node Arc address (`node is node` identity). Existing Python identity tests (`tests/test_phase4_rust_fixture.py:383-505`, also AC-contract tests at lines 233-335) cover the hit paths well. Validated coverage gaps (see `exploration.md`, this dir, §4 and §6):

1. **Eviction/ABA — the registry's core safety claim (`registry.rs:18-22`) is completely untested.** No test creates a handle, drops all references, forces GC, verifies the weak entry is evicted, then allocates a new node (potentially at the same address) and verifies no stale-handle resurrection. This is exactly the scenario where a subtle bug would be invisible to the existing tests (GC never runs at the right moment in them).
2. **`force_register` overwrite semantics** — invoked from generated `py_new`, never tested as "overwrites an existing entry."
3. **`register_if_absent` false branch** — `registry.rs:121` labels it "unreachable in practice" under single-threaded Python; test if practically forceable, otherwise document why not in the test file.
4. **`snapshot()`** (`registry.rs:137-142`) — a test-gated introspection helper built for exactly these tests and never called. Use it. Check how/whether it is exposed to Python (it is `#[cfg(test)]`-adjacent Rust — the design/test work must determine the access path; exposing it to the Python test build is in scope if needed).

## Fix shape

Python tests (against the existing fixture extension, e.g. `phase4_roundtrip_cst`) that:
- Create node handles; assert registry occupancy via `snapshot()` (or an equivalent observable); drop all Python references; `gc.collect()`; assert eviction.
- After eviction, create new nodes / re-read children; assert fresh handles with correct identity behavior and no resurrection of dead handles.
- Pin `force_register` overwrite semantics.
- Stress variant: loop create/drop cycles to give address reuse a chance to occur naturally (cannot force same-address ABA deterministically from Python; the test should exercise the path and assert invariants hold, not assert address reuse happened).
- Rewrite the TODO.md entry's framing if any residue remains; otherwise resolve the slug and remove the comment at `registry.rs:128-130`.

## Constraints / non-goals

- No production-code behavior changes; test-enabling plumbing (e.g. exposing `snapshot()` to the test build) is allowed and must be clearly test-only.
- Tests must be deterministic: rely on CPython refcounting + explicit `gc.collect()`; no timing dependence.
- Non-goal: Rust-side `#[test]` functions, cargo test infrastructure changes, CI toolchain changes.

## Verification expectations

- New tests fail if eviction handling is broken (sanity-check by inspection/mutation reasoning, not necessarily an actual injected bug).
- Full suite passes; `make fix`; `uv run pytest` clean.
