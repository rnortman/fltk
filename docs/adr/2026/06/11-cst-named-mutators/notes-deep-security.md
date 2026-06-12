# Security review — item 11 cst-named-mutators

Style: concise, precise, complete, unambiguous. No padding.

Commit reviewed: f904540 (base dd52073). Scope: generated CST mutators (insert / remove_at / replace_at / clear) on Python + Rust backends, plus a test-introspection registry-snapshot pyfunction.

No findings.

## Boundaries examined

- **Trust boundary**: Python callers pass `index`/`child`/`label` into generated Rust pymethods. Index goes through `__index__` then sign-aware clamp; `child`/`label` validated via existing `extract_from_pyobject` / `_label_from_pyobject_match` before any mutation. No raw `as`-cast of an untrusted index into unchecked Vec indexing — every `Vec::insert/remove`/`mem::replace` index is either clamped to `[0,n]`/`[0,n)` (insert) or bounds-resolved to `Some(i)` with `i < n` (remove_at/replace_at). No OOB indexing reachable from Python.
- **Native (GIL-free) mutators** (`insert_child`/`remove_child`/`replace_child`/`clear_children`) intentionally panic on OOB per Vec convention; documented; reachable only by in-process Rust callers (no trust boundary). Panic is a controlled abort, not memory unsafety.
- **Integer overflow**: `n as i64` is safe (children counts are far below i64). Beyond-i64 indices: insert uses `raw_idx.lt(0i64)` to pick clamp direction; remove/replace treat as out-of-range. No wraparound into a valid index.
- **Lock discipline**: all Python work (extraction, wrap-out, tuple build, old-entry drop) happens outside the RwLock guard; insert re-acquires the write lock after clamping. No reentrancy deadlock or torn state reachable; failed validation occurs before any mutation, so no partial-mutation corruption.
- **Registry / identity**: removal/replace/clear drop Arc clones only; weak-valued registry self-evicts; no use-after-free (a live Python handle holds its own Arc). No new corruption pathway.
- **Injection / format**: error messages interpolate `class_name` (generator-controlled, not attacker input) and the caller's index rendered via `str()`/`__index__` into a Rust `format!` — not an eval/log-injection sink. No SQL/command/path/template sinks introduced.
- **Secrets / crypto / SSRF / deserialization / redirects**: not applicable; none present in the diff.

## Note (not a finding) — verify gating holds, no action required from diff

`_registry_snapshot` pyfunction and its `register_classes` registration are both gated `#[cfg(feature = "test-introspection")]`, and that feature is NOT in maturin's build features (`pyproject.toml` `[tool.maturin] features = ["pyo3/extension-module"]`), nor in any default feature set. The production wheel therefore does not expose `_registry_snapshot`. This is correct: the snapshot exposes only int Arc-addresses → handles for the cdylib under test, and even if exposed would leak process-internal pointer addresses (minor info-disclosure) — but it is unreachable in shipped builds. No change needed; flagged only so a future change that adds `test-introspection` to a default/shipped feature set is recognized as a (minor) regression.
