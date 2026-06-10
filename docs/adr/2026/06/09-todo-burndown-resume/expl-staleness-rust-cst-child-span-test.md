# Staleness check: rust-cst-child-span-test design

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human. Facts + file:line only.

## Summary verdict

The design is **substantially stale**. Commit 4c8f0ad rewrote the child-accessor contract so that
`append_name`/`child_name` (and `append_value`/`child_value`) now store and return **native Rust
`Span` objects** (`fltk-cst-core::Span`), not `terminalsrc.Span` Python dataclasses. The design's
central factual premise — that the Rust node's `child_name()` / `child_value()` return a
`terminalsrc.Span` with `.start`/`.end` — is no longer true. The design also cited specific line
numbers for `fltk2gsm.py` visitors that have since moved. The `rust-cst-child-span-test` TODO slug
is still live in both `TODO.md` (line 39) and
`tests/test_phase4_fegen_rust_backend.py` (line 111-113), so the work item is not yet done.

---

## 1. What the design claimed about child accessor return type

**design.md:21-24** stated:

> "With the Rust fegen backend the nodes are Rust objects but the *children stored in them* are
> pure-Python `fltk.fegen.pyrt.terminalsrc.Span` dataclasses (`start: int`, `end: int` as normal
> fields). The Rust `child_name()`/`child_value()` accessors return whatever PyObject was
> appended, unchanged (`cst_fegen.rs:3419-3443`, `:3656-3680`: `tup.get_item(1)?.unbind()`)..."

This was true at the time of writing (before 4c8f0ad). It is now false.

---

## 2. What commit 4c8f0ad changed about child storage and accessors

**`src/cst_fegen.rs:4295-4296`** — `IdentifierChild` enum now holds a *native* `Span`:

```rust
pub enum IdentifierChild {
    Span(Span),  // fltk-cst-core::Span, not a Python object
}
```

**`src/cst_fegen.rs:4307-4323`** — `IdentifierChild::to_pyobject` constructs a **Rust
`fltk._native.Span`** via `span_type.call1((s.start(), s.end()))` (sourceless) or
`span_type.call_method1("with_source", ...)` (source-bearing). `span_type` is the
`fltk._native.Span` Python type object (cached as `FLTK_NATIVE_SPAN_TYPE`, loaded at
`cst_fegen.rs:45-54`). The returned Python object is therefore an `fltk._native.Span`, not a
`terminalsrc.Span`.

**`src/cst_fegen.rs:4325-4338`** — `IdentifierChild::extract_from_pyobject` accepts either a
locally-registered `Span` or an `fltk._native.Span` (cross-cdylib path via `extract_span`), and
stores both as native `Span`. It does **not** accept `terminalsrc.Span` at all.

Same structure for `RawStringChild` (`cst_fegen.rs:4674-4728`) and `LiteralChild`
(`cst_fegen.rs:5051-5110`).

**`src/cst_fegen.rs:4564-4581`** — `Identifier.child_name` calls
`child.to_pyobject(py, &span_type)?` on the stored `IdentifierChild`, which returns an
`fltk._native.Span` Python object. Not a `terminalsrc.Span`.

**Consequence:** `child_name()` and `child_value()` on a Rust-backed fegen node now return
`fltk._native.Span` objects. `fltk._native.Span` intentionally does **not** expose `.start`/`.end`
as Python attributes (`src/span.rs:54-56`; confirmed by `tests/test_rust_span.py:61-69`). The
design's proposed test (`assert result.start == 3`) would now **raise `AttributeError`** at that
line — the test would fail for the wrong reason (wrong object type, not accessor breakage).

---

## 3. How fltk2gsm.py now reads span text (no longer uses .start/.end)

Commit 4c8f0ad rewrote `fltk2gsm.Cst2Gsm` to go through `_span_text(span)` which calls
`span.text()` first (`fltk/fegen/fltk2gsm.py:24-45`). The `.start`/`.end` terminals-slice fallback
at line 41 is only reached for sourceless Python-backend spans (bootstrap path). The three
visitors now read:

- `visit_identifier` — `fltk2gsm.py:43-45`: `span = identifier.child_name(); return gsm.Identifier(self._span_text(span))`
- `visit_literal` — `fltk2gsm.py:164-166`: `span = literal.child_value(); return gsm.Literal(ast.literal_eval(self._span_text(span)))`
- `visit_regex` — `fltk2gsm.py:168-170`: `span = regex.child_value(); return gsm.Regex(self._span_text(span))`

**Line numbers in design.md:10** (`fltk2gsm.py:24-26`, `:145-147`, `:149-151`) are stale.
Current lines are 43-45, 164-166, 168-170.

The design's concern — "a regression in accessor return type would surface as `AttributeError` in
`visit_identifier`" — has changed character. The accessor now returns `fltk._native.Span` which
exposes `.text()` (the Rust `text()` method, `src/span.rs:268`). A regression where the accessor
returned something without `.text()` would still be an `AttributeError`, but at `span.text()` in
`_span_text`, not at `span.start`. The diagnostic value of a focused test remains, but the
contract to assert has changed.

---

## 4. What the correct test contract now is

If a focused regression test is still desired, it must:

1. Call `append_name(span)` where `span` is a **Rust `fltk._native.Span`** (or `fltk-cst-core Span`
   directly via `fegen_rust_cst`), not a `terminalsrc.Span` (which `extract_from_pyobject` at
   `cst_fegen.rs:4325-4338` now rejects — it only accepts Span subclasses).
2. Assert `child_name().text()` returns expected text (the method `fltk._native.Span` exposes), not
   `.start`/`.end`.
3. Optionally assert `isinstance(result, fltk._native.Span)`.

The existing `TestAppendChildRoundtrip` in `tests/test_fegen_rust_cst.py:142-155` uses `_span()`
which returns `terminalsrc.Span(0, 1)` — this would now fail `extract_from_pyobject`'s type check
unless the test uses a native span. (The test fixture behavior needs verification against the
rebuilt extension.)

---

## 5. New TODO slug: rust-cst-child-node-identity

`TODO.md:44-46` — added by commit 4c8f0ad. States that native child storage (`Box<ChildNode>` in
native `Vec`) means a child returned twice wraps a fresh `Py<ConcreteNode>` per call; tests in
`tests/test_phase4_rust_fixture.py:242,276,291,350,371` relaxed from `is` to `==`. This is
separate from the `rust-cst-child-span-test` work.

---

## 6. TODO slug live status

- **`TODO.md:39`** — `rust-cst-child-span-test` entry is still present, unchanged text.
- **`tests/test_phase4_fegen_rust_backend.py:111-113`** — `TODO(rust-cst-child-span-test)` comment
  is still present, unchanged.
- The slug **does not** appear in any other code file. No test implementing this TODO has been
  added.

---

## 7. Design citations that are stale or now wrong

| Design claim | Status |
|---|---|
| Children are `terminalsrc.Span` Python dataclasses | **Wrong** — children are native `fltk-cst-core::Span`; accessors return `fltk._native.Span` |
| `cst_fegen.rs:3419-3443`, `:3656-3680` (old line refs for `tup.get_item(1)?.unbind()`) | **Wrong** — those line numbers no longer exist; child model is entirely rewritten |
| `fltk2gsm.py:24-26`, `:145-147`, `:149-151` (visitor lines) | **Wrong** — now at lines 43-45, 164-166, 168-170; also `_span_text` abstraction added |
| Test should assert `result.start == 3` and `result.end == 9` | **Wrong** — `fltk._native.Span` raises `AttributeError` on `.start`/`.end` |
| Test should assert `isinstance(result, tsrc.Span)` | **Wrong** — result is `fltk._native.Span`, not `tsrc.Span` |
| `terminalsrc.Span(start=3, end=9)` as the appended child | **Wrong** — `extract_from_pyobject` rejects non-Span types; only accepts `fltk._native.Span`/`fltk-cst-core Span` |
| `tests/test_fegen_rust_cst.py:36-52` `CLASS_LABEL_INFO` as reference | **Stale line ref** — CLASS_LABEL_INFO is now at lines 43-61 |

---

## 8. What remains valid in the design

- The gap (no focused test for child accessor return type) is still real.
- Location (`tests/test_phase4_fegen_rust_backend.py`) and skip gate (`importorskip` at line 29)
  are still correct.
- The diagnostic rationale (localize failure to the accessor rather than burying it in a visitor)
  still applies.
- The three (class, accessor) pairs (`Identifier/name`, `Literal/value`, `RawString/value`) are
  still the right targets — same method names, same line numbers in `cst_fegen.rs` as the grep
  confirms.
