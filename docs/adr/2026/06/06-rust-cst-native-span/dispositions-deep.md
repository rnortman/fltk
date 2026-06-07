# Dispositions — deep review, Rust CST native span

Commit reviewed: 1b54878. Fixes applied at: 99e276a.

---

correctness-1:
- Disposition: Fixed
- Action: crates/fltk-cst-core/src/span.rs — rewrote `text()` and `text_or_raise()` to
  translate `start`/`end` codepoint indices to byte offsets via `char_indices().nth()` before
  slicing. Removed `text_str` (dead + same bug). Updated all doc comments to say "codepoint".
  Updated `test_rust_span.py::test_unicode_codepoint_indices` (was `test_unicode_byte_indices`)
  to assert codepoint semantics. Added non-ASCII regression test in
  `tests/test_phase4_rust_fixture.py::test_rust_backend_node_span_text_non_ascii`.
- Severity assessment: Introduced regression — any non-ASCII grammar source would produce
  wrong identifier/literal/regex text under the Rust backend, silently with no error. All
  existing tests used ASCII-only source, so the regression was invisible until this fix.

errhandling-1:
- Disposition: Fixed
- Action: fltk/fegen/fltk2gsm.py:_span_text — added guard: if `span.has_source()` is true
  and `text()` returns None, raises ValueError with diagnostic message instead of silently
  falling back to terminals slice with wrong byte/codepoint semantics.
- Severity assessment: Low after correctness-1 fix (codepoint semantics now correct); guard
  remains as defense-in-depth for any future path where indices go out of range.

errhandling-2:
- Disposition: Fixed
- Action: fltk/unparse/pyrt.py:extract_span_text — same guard as errhandling-1: raises
  ValueError for source-bearing spans whose text() returns None instead of silently slicing
  by byte offset with wrong results.
- Severity assessment: Same as errhandling-1; guard prevents silent wrong output in unparser.

errhandling-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Low-severity observability gap; adding logging here would require
  introducing a logging infrastructure decision (level, logger name) that is out of scope
  for this respond round. The None branch is now reached only for genuinely sourceless spans
  (correctness-1 fix ensures sourced spans return correct text); the "loss" is not surprising.
- Rationale: Adding debug logging for a non-error branch in a hot accessor path would
  pollute traces for the common case (sourceless spans constructed without source are expected).
  The fix for correctness-1 eliminates the ambiguity this note was warning about.

errhandling-4:
- Disposition: Won't-Do
- Action: no change (finding confirmed correct, no action required per the notes themselves)
- Severity assessment: The `expect` is correct; panicking on invariant violation is appropriate.
- Rationale: The finding itself states "No change required. Confirmed correct."

errhandling-5:
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py — updated SAFETY comment in the generated `extract_span`
  preamble to explicitly state "memory corruption (not merely a wrong result)" as the
  consequence of the single-rlib invariant violation (layout skew → UB → OOB Arc deref).
- Severity assessment: The UB is real but requires version-skew in the dependency graph, not
  a runtime input. The expanded comment makes the severity visible to future maintainers.

errhandling-6:
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py — wrapped the `py.import("fltk._native")` error in
  `get_source_text_type` with a `PyRuntimeError` context message: "span source preservation
  requires fltk._native (SourceText): {e}".
- Severity assessment: Low; aids on-call diagnosis when fltk._native is absent in a test
  environment. No behavioral change.

security-1:
- Disposition: Fixed (via errhandling-5)
- Action: SAFETY comment updated with memory-corruption consequence. The `downcast_unchecked`
  pattern itself is retained (it is the only sound approach for cross-cdylib type unification
  given shared-rlib invariant); replacing with checked downcast would not help because checked
  downcast also fails cross-cdylib (different type objects).
- Severity assessment: Low attacker leverage (requires controlling the build/dependency graph),
  but UB on skew. The comment change makes the invariant and its consequence explicit.

test-1:
- Disposition: Fixed
- Action: tests/test_phase4_rust_fixture.py — added two tests to TestAC7BothBackends:
  (1) `test_rust_backend_node_span_is_native_and_text_works`: after a live Rust-backend parse,
  asserts `isinstance(cst_root.span, Span)` and `span.text() is not None`.
  (2) `test_rust_backend_node_span_text_non_ascii`: non-ASCII input regression guard asserting
  span.text() contains the non-ASCII content (catches byte/codepoint regression).
- Severity assessment: Without these tests, a regression silently dropping node-span source
  after a parse would not be caught by any test; child-span fltk2gsm tests would not exercise
  node.span.text().

test-2:
- Disposition: Fixed
- Action: fltk/fegen/test_cst_protocol.py — added `_PYTHON_BACKEND_UNCASTED_CALLSITE_FIXTURE`
  and `test_python_backend_uncasted_callsite_annotation_churn`. The fixture calls
  `accept_python_span(node.span)` without a cast, with a `type: ignore[arg-type]` suppressor.
  The test asserts the suppressor works (zero pyright errors). This documents explicitly that
  uncast call sites DO require annotation changes after widening — the backward-compatibility
  claim applies to code using `typing.cast`, not to bare uncast assignments. The prior tests
  hid this by using cast everywhere.
- Severity assessment: Clarifies the true scope of the backward-compatibility guarantee;
  downstream consumers who relied on "no annotation changes needed" for bare call sites
  would see pyright errors after widening. Now documented with a test.

reuse-1:
- Disposition: Fixed
- Action: crates/fltk-cst-core/src/span.rs — removed `text_str` (dead, duplicated `text()`
  body with same logic). Retained `source_as_py` and updated its doc comment with an explicit
  explanation of why it cannot be used in generated code yet (cross-cdylib type registration),
  a TODO(span-source-as-py-crosscdylib) reference, and guidance for future maintainers.
- Severity assessment: `text_str` was dead API that would cause divergence from `text()` on
  any future boundary-logic change. `source_as_py` is retained as the correct O(1) API for
  when the cross-cdylib issue is resolved.

reuse-2:
- Disposition: Fixed (via reuse-1)
- Action: `text_str` removed; the duplication no longer exists. `text()` is the single
  implementation.
- Severity assessment: The divergence risk is eliminated.

reuse-3:
- Disposition: TODO(gencode-poc-fltkg)
- Action: Added TODO.md entry for `gencode-poc-fltkg`. The `Makefile:83-88` comment already
  referenced the slug; the TODO.md entry was missing. Entry describes: create a `.fltkg`
  source file for the PoC grammar so `make gencode` drives it through the standard
  `gen-rust-cst` path.
- Severity assessment: Low; the current inline Python one-liner diverges from the standard
  path but is functionally correct. The TODO tracks the cleanup.

quality-1:
- Disposition: Fixed (via reuse-1)
- Action: `text_str` removed; `source_as_py` retained with corrected doc comment.
- Severity assessment: Eliminates dead public API that confused the source-preservation strategy.

quality-2:
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py:392 — replaced stale "source_as_py requires py token"
  comment with accurate "get_source_text_type(py) is called in the source-bearing branch".
- Severity assessment: Low; stale comment pointed to abandoned approach, misleading maintainers.

quality-3:
- Disposition: Won't-Do
- Action: `_span_text` fallback retained.
- Severity assessment: The fallback IS unreachable for Rust-backend spans after correctness-1
  fix (text() now works correctly for all valid codepoint indices). For Python-backend spans,
  the shim is still needed for any pre-regen parser that produced sourceless spans. Removing
  it now would break any in-flight bootstrap scenario where an old parser is combined with
  the new fltk2gsm. The errhandling-1 guard already prevents silent wrong text; the fallback
  is now safe-or-raises. Removal is a follow-on once the bootstrap scenario is confirmed closed.
- Rationale: Removing live fallback code that may still be exercised in bootstrap scenarios
  is an active harm risk; the guard added by errhandling-1 makes the fallback safe without
  removing it.

quality-4:
- Disposition: Fixed
- Action: fltk/fegen/gsm2parser.py:_make_span_expr — replaced `VarByName(name="fltk.fegen.pyrt.span.Span")`
  hardcoded string with `self.context.python_type_registry.lookup(self.TerminalSpanType).import_name()`.
  The path is now derived from the registered TypeInfo, so a future module rename only requires
  updating the registry entry. `make gencode` + `make check` pass after the change.
- Severity assessment: Low; the hardcoded path was stable but bypassed the registry that already
  held the correct module/name. The fix eliminates a manual-update hazard on any future rename.

---

## Rework outcome (quality-4)

quality-4 was previously disposed as TODO(span-make-span-expr-registry) — a phantom defer with no
TODO.md entry and no code comment. Judge ruled: mechanical, single-file, in-scope → do it now.

Fix applied at rework commit: derived Span class path in `_make_span_expr` from
`self.context.python_type_registry.lookup(self.TerminalSpanType).import_name()` instead of
hardcoded `"fltk.fegen.pyrt.span.Span"` string. `make gencode` regenerated generated files;
`make check` exits 0 (939 Python tests pass, cargo check + clippy + test pass).

quality-5:
- Disposition: Fixed
- Action: TODO.md — added `gencode-poc-fltkg` entry describing the work and pointing to
  Makefile:83-88.
- Severity assessment: Without the TODO.md entry, the slug comment in the Makefile was
  invisible to the master tracking list; the deferred work would be forgotten.

quality-6:
- Disposition: Fixed
- Action: fltk/fegen/gsm2tree_rs.py:518 — changed generator to emit
  `pub fn children_native(&self) -> &[(label_type, enum_name)]` with body
  `self.children.as_slice()` instead of `&Vec<(...)>`. Regenerated all four CST files.
- Severity assessment: `&Vec<T>` return type is non-idiomatic Rust (clippy lint) and locks
  downstream code to the concrete container type. The fix is a source-compatible change
  (Vec coerces to &[T] via Deref) with no breakage.

efficiency-deep-1:
- Disposition: TODO(span-source-as-py-crosscdylib)
- Action: Added TODO.md entry `span-source-as-py-crosscdylib` describing the O(N·M) regression
  and the fix path (add `extract_source_text` preamble helper analogous to `extract_span`).
  `source_as_py` doc comment updated to explain the cross-cdylib constraint and reference the TODO.
- Severity assessment: Per-accessor cost is O(source length) instead of O(1); full traversal of
  an N-node tree over M-byte source is O(N·M) byte copies. On a 100 KB grammar file with
  thousands of nodes this is hundreds of MB of transient allocation per pass. The fix requires
  a generator preamble change to add `extract_source_text` with the shared-rlib invariant.
  Deferred because it is a performance regression, not a correctness bug, and the fix requires
  careful cross-cdylib safety reasoning.
