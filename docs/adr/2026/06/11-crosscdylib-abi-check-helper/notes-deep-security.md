# Security review — crosscdylib-abi-check-helper

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: `git diff 1963894..912b285` (HEAD 912b285). Scope: `crates/fltk-cst-core/src/cross_cdylib.rs`, `tests/test_rust_span.py`.

## Gate-equivalence verification (the load-bearing question)

This diff refactors the safety gate guarding two `unsafe downcast_unchecked` calls. Verified no semantic weakening:

- `check_abi_pair<T>` performs the identical 7-step sequence (marker getattr → str extract → string compare → layout compute → layout getattr → usize extract → layout compare), same order, same operands, fail-closed at every step. Accept set unchanged: an object passes iff both attrs are present, correctly typed, and equal to this module's values — exactly as before.
- `expected_layout` is computed from the helper's generic `T` (`size_of::<PyClassObject<T>>()`), not a fixed type. Both call sites instantiate `T` consistent with their downcast target: `check_abi_pair::<SourceText>` guards `downcast_unchecked::<SourceText>` (cross_cdylib.rs:93,110); `check_abi_pair::<Span>` in `get_span_type` guards `downcast_unchecked::<Span>` in `extract_span` (cross_cdylib.rs:333,303).
- The deleted generic "expected fltk._native.SourceText, got {type}" path was a rejection path; its replacement (template 1) is also a rejection. No new acceptance.
- `getattr` failures of any exception type (including raising metaclass `__getattr__`) map to rejection — fails closed; same swallow as the old `if let Ok(...)` / `map_err` patterns. Pre-existing, unchanged.
- Pointer-identity cache (`FLTK_FOREIGN_SOURCE_TEXT_TYPE`) and `GILOnceCell` init semantics untouched; the validated-type-then-cache-then-downcast sequence runs under the GIL with the object's type fixed throughout — no new TOCTOU.
- Documented residuals (pure-Python forgery of both attrs; size-preserving layout skew) carry over verbatim in the SAFETY comments and remain accurately described. No change in exposure.

## Findings

### security-1

- File: `crates/fltk-cst-core/src/cross_cdylib.rs:129-133` (`py_type_obj_name`), interpolated as `{subject}` into templates at lines 166, 174, 181, 193, 200, 207.
- Issue: attacker-influenced type identity flows unescaped into exception messages. `fully_qualified_name()` reads `__module__` and `__qualname__`, which are arbitrary Python `str`s settable by the caller (e.g. `FakeSource.__qualname__ = "x\x1b[2J\nSpan ABI OK"`); the result is embedded verbatim in six `PyTypeError` messages.
- Trust boundary / data flow: any Python caller of `Span._with_source_unchecked` (underscore-private but Python-reachable, and invoked by generated consumer code on arbitrary objects routed to it) → `extract_source_text` slow path → `py_type_obj_name(&obj_type)` → error string → exception propagated to downstream application, typically logged or rendered.
- Consequence: log injection / terminal escape-sequence injection. An attacker who can get a crafted class to this entry point can forge multi-line log entries or emit ANSI escapes into terminals/log viewers of whoever inspects the downstream app's error output. Requires the downstream app to surface these TypeError messages in logs or terminals; no memory-safety or gate-bypass impact. Note the asymmetry with commit 0cc7a7f, which escapes control chars in parse error messages — this error path predates that policy (`py_type_name`/`py_attr_type_name` have the same exposure) but the diff adds a new, wider instance (`fully_qualified_name` includes `__module__`, and the subject now appears in six templates instead of one).
- Suggested fix: route type/attr names through the same control-char escaping used by the error-msg-escape change (0cc7a7f) — e.g. a shared `escape_for_error(&str) -> String` applied in `py_type_obj_name`, `py_type_name`, and `py_attr_type_name`. Cheap, failure-path-only.

## No-finding observations

- Hardcoded `"fltk._native.Span"` subject on the Span path: no untrusted interpolation there; correct choice.
- `FLTK_CST_CORE_ABI` (crate version) disclosure in error messages: pre-existing, intentional, diagnostic by design.
- Test changes pin the gate's rejection behavior (missing marker, bogus marker, missing/non-int/mismatched layout) — they strengthen, not weaken, regression coverage of the security gate.
