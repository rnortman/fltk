# Error-handling review notes — cst-python-feature-gate

Commit range reviewed: e6a9117..431ab53

---

## errhandling-1

**File:** `crates/fltk-cst-core/src/span.rs:417`

**Path:** `Span::text_or_raise` (python-gated `#[pymethods]` block)

```rust
let byte_end = src.char_indices().nth(end).map(|(b, _)| b).unwrap_or(src.len());
```

**Why:** `end == char_count` is the valid "slice to end-of-string" case and is handled here correctly via `unwrap_or(src.len())`. However `end < char_count` but no valid char boundary at that index is also caught by this same `unwrap_or`, silently returning `src.len()` instead of raising. That path is unreachable given well-formed UTF-8 (every codepoint has a start byte), but the `unwrap_or` destroys the signal: if the logic ever regresses or a wrong `end` slips through, `text_or_raise` silently returns a longer-than-requested slice instead of raising `ValueError`.

**Consequence:** A caller expecting an error for an out-of-bound end index gets a wrong (too-long) string back with no indication. Distinguishable from the native `text()` fallback only by comparing return lengths.

**What must change:** Replace the bare `unwrap_or(src.len())` with an explicit branch:

```rust
let byte_end = if end == char_count {
    src.len()
} else {
    src.char_indices().nth(end).map(|(b, _)| b).ok_or_else(|| {
        PyValueError::new_err(format!(
            "Span({}, {}) end index has no char boundary (logic error)",
            self.start, self.end
        ))
    })?
};
```

The `end > char_count` guard immediately above already validates the only other out-of-bounds case, so this branch strictly covers the residual "equal to char_count" vs "something unexpected" split, making the `unwrap_or` disappear.

---

## errhandling-2

**File:** `crates/fltk-cst-core/src/span.rs` and all generated `cst.rs` files

**Path:** Python `py_merge` / `py_intersect` wrappers

```rust
fn py_merge(&self, other: &Span) -> PyResult<Span> {
    self.merge(other)
        .map_err(|_| PyValueError::new_err("cannot merge spans from different sources"))
}
fn py_intersect(&self, other: &Span) -> PyResult<Span> {
    self.intersect(other)
        .map_err(|_| PyValueError::new_err("cannot merge spans from different sources"))
}
```

**Why:** The `SpanError` value is discarded with `|_|`. `SpanError` is `#[non_exhaustive]` so future variants will never reach Python with any identifying information. Currently there is only one variant (`SourceMismatch`) and the message text is correct, but any additional error kind added later will be silently mapped to the same "cannot merge spans from different sources" text regardless of its actual meaning.

**Consequence:** When a new `SpanError` variant is introduced, every Python caller—including out-of-tree downstream consumers—will receive a misleading `ValueError` message. The on-call engineer cannot distinguish error kinds from the Python exception alone.

**What must change:** Map on the concrete variant rather than discarding it:

```rust
.map_err(|e| PyValueError::new_err(e.to_string()))
```

`SpanError` already implements `Display` with correct per-variant messages. This also future-proofs new variants automatically.

---

## errhandling-3

**File:** `crates/fltk-cst-core/src/span.rs:237–260` (native `Span::text`)

**Path:** Edge case in `byte_end` computation for `end == 0`

```rust
let byte_end = if end == 0 {
    Some(0)
} else {
    src.char_indices().nth(end).map(|(b, _)| b).or_else(|| {
        if src.chars().count() == end { Some(src.len()) } else { None }
    })
};
match (byte_start, byte_end) {
    (Some(bs), Some(be)) => Some(src[bs..be].to_owned()),
    (None, Some(0)) if start == 0 => Some(String::new()),
    _ => None,
}
```

The `(None, Some(0)) if start == 0` arm is only reachable when `start == 0` and `end == 0` simultaneously, because `byte_start` comes from `src.char_indices().nth(0)` which returns `Some((0, _))` for any non-empty string and `None` only for an empty string. For an empty source string with `start == 0` and `end == 0`, this arm correctly returns `Some("")`. However, the symmetry with `byte_start` being `None` while `byte_end` is `Some(0)` for non-zero `start` is silently masked by `_ => None`. That silent path is logically correct (returns `None` for an out-of-bounds start on an empty string), but the match structure does not assert that `byte_start == None` here means "empty source, start out of bounds" — it is implicit and the second arm has a narrow guard that passes only when `start == 0`. Any future refactor that changes how `byte_start` is computed for the `start == 0` / empty-source case will silently regress to `None` without compiler warning.

This is a latent correctness/observability issue rather than an immediate failure; noted for awareness but does not require an immediate change. The test suite covers the empty-span-on-sourced-text case.

No separate action required unless `text()` is changed.

---

## Summary

One actionable issue of real consequence (errhandling-1: silent wrong return in `text_or_raise`), one correctness-under-extension issue (errhandling-2: discarded error discriminant in Python wrappers). errhandling-3 is a latent structural smell, not a current failure.
