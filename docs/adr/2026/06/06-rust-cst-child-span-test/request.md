# Request: rust-cst-child-span-test

Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

**Type of work:** add a focused regression test; small. Reframed from the original TODO (its premise was partly wrong — see below).

**Background.** `fltk2gsm.Cst2Gsm` slices source text via `span.start`/`span.end` on the objects returned by child accessors:
- `visit_identifier` (`fltk/fegen/fltk2gsm.py:24-26`): `span = identifier.child_name(); self.terminals[span.start:span.end]`
- `visit_literal` (`:145-147`): `span = literal.child_value(); ...span.start:span.end`
- `visit_regex` (`:149-151`): `span = regex.child_value(); ...span.start:span.end`

No focused test asserts that a Rust-backed CST node's child accessors return objects exposing `.start`/`.end`. The AC8 equality tests exercise it only indirectly; a regression in accessor return *type* would surface as a confusing `AttributeError` deep in the visitor rather than a localized failure.

**CRITICAL correction (the TODO's premise is wrong — do NOT follow the original wording).** The Rust `fltk._native.Span` *intentionally* does NOT expose `.start`/`.end` as Python attributes (`src/span.rs:54-56`; `tests/test_rust_span.py:61-69` asserts `AttributeError`). The objects the Rust node's `child_name()`/`child_value()` actually return are Python `fltk.fegen.pyrt.terminalsrc.Span` dataclasses (stored as children inside the Rust node's `Py<PyList>`), and *those* carry `.start`/`.end` as normal fields. The test MUST assert `.start`/`.end` on the returned `terminalsrc.Span`, NOT on a Rust span. Asserting on a Rust span would test a contract that deliberately does not exist.

**Fix shape (chosen).** Add one focused test in `tests/test_phase4_fegen_rust_backend.py` (which already `pytest.importorskip("fegen_rust_cst")` at line 29). Construct a Rust-backed fegen node (e.g. `Identifier` and a value-bearing node), `append_<label>` a `terminalsrc.Span(start, end)` child, call `child_name()` / `child_value()`, and assert the returned object's `.start`/`.end` equal what was appended.

**Load-bearing constraints.**
- Assert on `terminalsrc.Span` instances (the real child type), never on `fltk._native.Span`.
- Use the existing `fegen_rust_cst` extension + `importorskip` skip pattern; mirror the existing `TestAppendChildRoundtrip` style in `tests/test_fegen_rust_cst.py:132-144`.
- Pick node/accessor pairs that genuinely have `child_name`/`child_value` in the fegen Rust CST surface.

**Non-goals.** Not changing any source — test-only. Not adding `.start`/`.end` to the Rust `Span` (deliberately absent). Not testing the full parse path (that is the indirect coverage we are localizing).

**Verification.** `uv run pytest tests/test_phase4_fegen_rust_backend.py` passes with the new test; the test fails (cleanly, at its own assertion) if a child accessor were made to return an object lacking `.start`/`.end`. `TODO.md` entry and the `TODO(rust-cst-child-span-test)` comment (`tests/test_phase4_fegen_rust_backend.py:111-112`) removed.

**Exploration:** `exploration.md` in this dir (establishes the corrected contract with source citations).
