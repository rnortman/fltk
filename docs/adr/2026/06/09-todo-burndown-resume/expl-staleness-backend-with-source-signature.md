# Staleness check: `backend-with-source-signature` design

Concise. Precise. Token-dense — no fluff, full information. No preamble. No padding.

## Summary verdict

**The design's problem is fully solved.** Commit `4c8f0ad` implemented every change the design prescribed, plus more (it wired source-bearing spans through the parse path too). The `backend-with-source-signature` slug is gone from TODO.md and gone from code. Nothing from the design remains undone.

## What commit 4c8f0ad did (verified against diff)

The commit message explicitly names this: "backend-with-source-signature prerequisite folded in: SourceText now real on the Python backend."

### Design edit 1 — Add `SourceText` to `terminalsrc.py`

Implemented exactly as designed.

- `fltk/fegen/pyrt/terminalsrc.py:8-22`: `@dataclass(frozen=True, slots=True) class SourceText` with `_text: str` field and `__init__(self, text: str)` using `object.__setattr__`. Matches design shape (frozen dataclass, private `_text`, construct-only portable contract).

### Design edit 2 — Make Python `with_source` accept `str | SourceText`

Implemented exactly as designed.

- `fltk/fegen/pyrt/terminalsrc.py:131-149`: `with_source(cls, start: int, end: int, source: "str | SourceText") -> "Span"`. Unwraps `SourceText._text` if `SourceText`, stores `str` directly if `str`, raises `TypeError` eagerly for any other type (design open question 2, resolved as eager TypeError). Existing `str` callers preserved.

### Design edit 3 — Export `SourceText` from the selector on the Python path

Implemented exactly as designed.

- `fltk/fegen/pyrt/span.py:10`: `from fltk.fegen.pyrt.terminalsrc import SourceText, Span, UnknownSpan` — `SourceText = None` line deleted entirely.
- `fltk/fegen/pyrt/span.py:1-6`: Docstring updated: `TODO(backend-with-source-signature)` line removed; text now states "The portable form is always `Span.with_source(s, e, SourceText(text))`."
- `fltk/fegen/pyrt/span.py:13`: Rust path `from fltk._native import SourceText, Span, UnknownSpan` still overwrites on the Rust path.

### TODO cleanup

- `TODO.md`: `backend-with-source-signature` entry absent from current working tree (verified by reading full `TODO.md`).
- No `TODO(backend-with-source-signature)` comment anywhere in codebase (verified: `span.py:7` comment replaced by new docstring prose).

## What was done beyond the design's scope

The design explicitly excluded parse-path wiring as out of scope. Commit 4c8f0ad did it anyway as part of the larger Rust-CST-native-Span work:

- `fltk/fegen/fltk2gsm.py` was updated (25 lines changed) to consume source-bearing spans.
- Generated parsers now produce source-bearing spans through the parse path.

These were out of scope for `backend-with-source-signature` but are now done.

## What `span-source-as-py-crosscdylib` is and how it relates

`span-source-as-py-crosscdylib` is a **distinct, residual efficiency problem** introduced by (not solved by) the Rust-CST-native-Span work. It is not a renamed version of `backend-with-source-signature`.

### The problem it tracks

`crates/fltk-cst-core/src/span.rs:138-161` — `Span::source_as_py` clones only the `Arc` (O(1)) and returns a `SourceText` registered with the current cdylib's type system. For cross-cdylib use (out-of-tree consumer crates), this locally-registered `SourceText` is a different type object than `fltk._native.SourceText`, so it cannot be passed to `fltk._native.Span.with_source`.

The workaround currently used in generated code (`gsm2tree_rs.py`):
- `gsm2tree_rs.py:200-212`: static `FLTK_NATIVE_SOURCE_TEXT_TYPE: GILOnceCell<Py<PyType>>` + `get_source_text_type(py)` helper that imports `fltk._native.SourceText` at runtime.
- `gsm2tree_rs.py:415-417`: `if let Some(full_text) = s.source_full_text_str()` — calls `source_full_text_str()` which clones the full source string (`src/span.rs:168-170`: `arc.text.clone()`), then `get_source_text_type(py)?.call1((full_text.as_str(),))` — constructs a new `fltk._native.SourceText` by calling its Python constructor. Two O(source_length) operations per accessor call.
- Same pattern at `gsm2tree_rs.py:593-598` (span getter on nodes).

### What the fix would look like

`TODO.md:52-54` describes it: add an `extract_source_text` helper to the generated preamble (analogous to `extract_span`) that uses `downcast_unchecked` to reinterpret the locally-registered `SourceText` as `fltk._native.SourceText`, exploiting the shared-rlib invariant. This would replace the `source_full_text_str` + full-string copy path with `source_as_py` (O(1) Arc clone).

The fix location: `fltk/fegen/gsm2tree_rs.py` preamble and span-getter/to_pyobject emission; `crates/fltk-cst-core/src/span.rs:source_as_py` (already implemented, just not wired cross-cdylib).

### Relationship to `backend-with-source-signature`

`backend-with-source-signature` was about the **Python adapter layer** (make `SourceText` a real class on the Python side; unify `with_source` signature). That is fully done.

`span-source-as-py-crosscdylib` is about **Rust-to-Python object conversion efficiency** in generated out-of-tree consumer crates. It presupposes `backend-with-source-signature` is done (it needs `SourceText` to exist cross-cdylib), but addresses a new problem the Rust-CST-native-Span work introduced. It has no analogue in the earlier design.

## Open design questions — resolution status

1. **Should Python `SourceText` expose text publicly?** Resolved as private (`_text`): `terminalsrc.py:18`. Matches design default.
2. **Behavior of `with_source` on unrecognized type?** Resolved as eager `TypeError`: `terminalsrc.py:143-148`. Matches design default.
