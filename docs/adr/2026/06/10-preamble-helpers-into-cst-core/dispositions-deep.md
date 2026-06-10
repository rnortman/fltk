Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 5e29293. Fixes committed at: e7f8f88.

---

errhandling-1:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/cross_cdylib.rs:44-57` — added `.map_err(|e| PyRuntimeError::new_err(format!("cross-cdylib Span type lookup failed (fltk._native.Span): {e}")))` inside `get_span_type`'s `get_or_try_init` closure, matching the existing pattern in `get_source_text_type`.
- Severity assessment: Without the wrapping, a failed `fltk._native` import in `get_span_type` propagates a bare `ModuleNotFoundError` with no cross-cdylib context, making span-type initialization failures indistinguishable from unrelated import errors. Diagnostic impact only; no correctness or safety consequence.

errhandling-2:
- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/cross_cdylib.rs:37-43` — replaced `obj.get_type().name()?` with `obj.get_type().name().map(|n| n.to_string()).unwrap_or_else(|_| "<unknown type>".to_string())` so the error branch always emits `PyTypeError` regardless of whether `__name__` is accessible on the rejected object.
- Severity assessment: Narrow window (requires a genuinely malformed Python type object), but when triggered the secondary `?`-propagated error would surface as an `AttributeError` with no indication of the span-validation context. Fix is trivial and eliminates the secondary failure path.

security-1:
- Disposition: TODO(crosscdylib-abi-sentinel)
- Action: Added `TODO(crosscdylib-abi-sentinel)` comment to `crates/fltk-cst-core/src/cross_cdylib.rs:32-34` (inside the INVARIANT VIOLATION block) and a corresponding entry in `TODO.md` describing the ABI sentinel mechanism. No runtime behavior changed — behavior-preservation is a stated design constraint for this change.
- Severity assessment: Version skew between the consumer's pinned `fltk-cst-core` revision and the installed `fltk._native` wheel converts a packaging error into in-process memory corruption rather than a clean error. The risk is real but pre-existing (moved verbatim per design), and the correct fix (ABI sentinel in `get_span_type`'s `GILOnceCell` init) is non-trivial enough to warrant a dedicated follow-up rather than a respond-mode patch.

test-1:
- Disposition: Fixed (partial — slow positive path deferred)
- Action: Added `TestExtractSpanErrorPaths` class in `tests/test_phase4_rust_fixture.py:375-416` with four tests covering the `extract_span` error branch (integer, string, None wrong types + message content check). The true positive slow path (cross-cdylib `isinstance` succeeding against a Span from a *different* cdylib) requires a two-cdylib in-process fixture that does not exist in-tree and is not in scope for respond mode.
- Severity assessment: The error branch contains safety-relevant code (PyTypeError emission after both fast and slow paths fail). The added tests verify the branch is reachable and produces the correct exception type and message. The uncovered positive slow path is a genuine gap but requires a multi-cdylib test harness.

test-2:
- Disposition: Fixed
- Action: `tests/test_gsm2tree_rs.py:191-196` — added a comment scoping the `import_count == 0` assertion to the preamble-helpers absence specifically, with an explicit note that future intentional `py.import("fltk._native")` usage in generated code would require updating this check.
- Severity assessment: Without the comment, the assertion reads as "no fltk._native imports ever," which is broader than intended and would cause false failures if a future generator feature legitimately uses the import. Documentation/intent only; no runtime consequence.

test-3:
- Disposition: Fixed
- Action: Covered by the `TestExtractSpanErrorPaths` class added for test-1. `test_set_span_integer_raises_typeerror`, `test_set_span_string_raises_typeerror`, `test_set_span_none_raises_typeerror`, and `test_set_span_wrong_type_message_mentions_span` collectively exercise the wrong-argument error path and verify the expected exception type and message content.
- Severity assessment: Without these tests, a regression that silently accepts wrong-typed span arguments (or raises the wrong exception) would not be caught by CI. The specific error message "expected fltk._native.Span" is now pinned by `test_set_span_wrong_type_message_mentions_span`.
