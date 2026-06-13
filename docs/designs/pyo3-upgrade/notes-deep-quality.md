# Quality findings — pyo3-upgrade branch

Commit reviewed: 6df2369

---

quality-1

File: `crates/fltk-cst-core/src/span.rs:380,565`

Stale `GILOnceCell` mentions in doc comments that were not updated alongside the class F migration.

- Line 380: `/// Checked once in ``get_span_type``'s ``GILOnceCell`` init (``cross_cdylib.rs``)…`
- Line 565: `/// Uses a ``GILOnceCell`` cache to avoid a Python attribute lookup on every call.`

Both describe `PyOnceLock` cells post-migration but still name the old type.

**Consequence**: doc comments describe the wrong pyo3 API. Future readers cross-referencing the pyo3 docs will search for a removed type and waste time. Propagation risk is low (doc-only), but the pattern of half-updated comments introduces noise that undermines trust in the surrounding documentation.

Fix: replace `GILOnceCell` with `PyOnceLock` at both sites.

---

quality-2

File: `tests/test_rust_span.py:470–478`

`TestSpanPathAbiGate` class docstring names `GILOnceCell` three times after the migration to `PyOnceLock`:

```
(subprocess tests for GILOnceCell init)
The ABI check fires once in get_span_type's GILOnceCell init
Note: GILOnceCell does NOT cache errors
```

The behavior claim ("does NOT cache errors") is still accurate for `PyOnceLock::get_or_try_init` (verified: on failure the cell is left uninitialized, as shown by the vendored test at `pyo3-0.29.0/src/sync/once_lock.rs:227–233`). But the type name is wrong.

**Consequence**: test docstrings are the first place a developer looks to understand test intent. Stale type names here create the same confusion as quality-1, and because this is a test file the reader may assume it reflects actual runtime behavior.

Fix: replace `GILOnceCell` with `PyOnceLock` at all three occurrences in the class docstring. The behavioral note ("does NOT cache errors") requires no change — the semantics are identical.

---

quality-3

File: `fltk/fegen/test_genparser.py:75`

Test docstring: `no GILOnceCell cache, no fltk._native.UnknownSpan runtime import`. The `GILOnceCell` reference was the design note calling out that the generated preamble deliberately avoids introducing a `GILOnceCell`-based cache. That note is still accurate as a "we don't emit this" assertion, but now names the old type.

**Consequence**: same as quality-1/2 — minor, but the test doc no longer names the API that would be emitted if the design changed.

Fix: change `GILOnceCell` to `PyOnceLock` in that docstring.

---

No other findings.
