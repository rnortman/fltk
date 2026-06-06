# Test Review: Clean Protocol-Only Consumer API

Commit range reviewed: 1e78b73..bc42280 (HEAD: bc42280).
Production changes: `terminalsrc.py`, `fltk_cst_protocol.py`, `fltk2gsm.py`, `src/span.rs`, `pyproject.toml`, `gsm2tree.py`, `fltk2gsm.py`.
Test files: `tests/test_clean_protocol_consumer_api.py`, `fltk/fegen/test_cst_protocol.py`.

---

## Findings

### test-1

**File:** `tests/test_clean_protocol_consumer_api.py:233–242` (`test_shapes_fixture_no_forbidden_patterns`)

**What's wrong — missing coverage.** The test scans `_SHAPES_FIXTURE` for `typing.cast`, `cast(`, `runtime_checkable`, and `# noqa: S101`, but does NOT check for `TYPE_CHECKING`. Requirements §gating criterion and both shape specs forbid `TYPE_CHECKING` shadow imports. An editor adding `from typing import TYPE_CHECKING` to the fixture would not be caught by this test; the pyright/ruff cleanliness tests (`test_shapes_fixture_pyright_clean`, `test_shapes_fixture_ruff_clean`) would not catch it either, since a `TYPE_CHECKING`-guarded block is valid Python and clean under both tools.

**Consequence:** A regression reintroducing a `TYPE_CHECKING` shadow in the protocol-only consumer shapes fixture would pass all tests. The gating criterion would be violated without detection.

**Fix:** Add `assert "TYPE_CHECKING" not in code_text` alongside the existing forbidden-pattern assertions.

---

### test-2

**File:** `tests/test_clean_protocol_consumer_api.py:407–411` (`test_nodekind_nonmatching_neq`)

**What's wrong — incomplete coverage.** The nonmatching `!=` test for `NodeKind` exercises only the Python backend (`py_cst.NodeKind.GRAMMAR`) in the second operand. `test_label_proto_nonmatching_neq` (line 447–453) covers both `embedded_rust_cst` and Python for labels, but `test_nodekind_nonmatching_neq` omits `embedded_rust_cst.NodeKind` and `fegen_rust_cst.NodeKind` in the wrong-value `!=` direction. AC 7 explicitly requires the `False` (nonmatching) case; design §2.3c flags `NotImplemented` return for foreign operands as load-bearing specifically for the `!=` semantics.

**Consequence:** A broken `__eq__` that returns `True` for cross-backend non-matching NodeKind members (e.g., always returns `True` when the canonical string is absent) would pass the existing `test_nodekind_nonmatching_neq` but fail the Rust backends. Only hash + set-collapse tests provide indirect coverage, and they only exercise matching pairs.

**Fix:** Extend `test_nodekind_nonmatching_neq` (or add a parallel test) to assert `proto_cst.NodeKind.ITEMS != embedded_rust_cst.NodeKind.GRAMMAR` and `proto_cst.NodeKind.ITEMS != fegen_rust_cst.NodeKind.GRAMMAR`, both operand orders.

---

### test-3

**File:** `tests/test_clean_protocol_consumer_api.py:53` (`PROTOCOL_MODULE_PATH` declared but unused)

**What's wrong — vacuous declaration / missing coverage.** `PROTOCOL_MODULE_PATH` is defined at module scope but is never read by any test. Design §3 ("no new file-level suppressions") requires that the generated protocol module not acquire new `# ruff: noqa` or `# type: ignore` entries as a side effect. The actual file (`fltk_cst_protocol.py`) carries the pre-existing `# ruff: noqa: N802` (permitted) and no new ones; `terminalsrc.py` (hand-written shared library, not generated) now carries `# type: ignore[attr-defined]` at line 29. Neither is verified by any test. The path constant suggests a test was intended.

**Consequence:** A generator regression introducing a new file-level suppression into `fltk_cst_protocol.py` would not be caught. The `# type: ignore[attr-defined]` on `terminalsrc.py:29` (a hand-written file, not generated) is also untested — it gates the `SpanKind.SPAN._fltk_canonical_name` assignment and could silently suppress a real type error if the attribute definition changes.

**Fix:** Add a test using `PROTOCOL_MODULE_PATH` that asserts `# ruff: noqa: N802` appears exactly once (pre-existing, permitted) and no other file-level noqa/type-ignore lines appear. Separately, add an assertion or note that `terminalsrc.py` contains exactly one `# type: ignore` and it is specifically `[attr-defined]` on the canonical-name assignment line.

---

### test-4

**File:** `tests/test_clean_protocol_consumer_api.py:604–622` (`test_span_kind_narrows_rust_backend_span_children`)

**What's wrong — conditional behavior / weak assertion for the Rust-separator case.** The test comment (lines 607–613) notes that "the Rust fegen_cst parser… still uses Python terminalsrc.Span instances for separator children" — meaning the test does NOT actually exercise the `fltk._native.Span.kind` path (Rust `#[pyclass]` Span as a separator), only Python `terminalsrc.Span` inside a Rust-backend tree. The design's primary concern for AC 12 is that a *Rust `fltk._native.Span`* separator child is correctly dispatched via `case cst.Span.kind:`. The test `test_rust_native_span_kind_also_matches` (line 624–629) checks that `RustSpan(1, 5).kind == proto_cst.Span.kind` as a standalone instance, but no test exercises `case cst.Span.kind:` (i.e., match dispatch) against a `fltk._native.Span` acting as a separator child inside a real tree traversal.

**Consequence:** The load-bearing AC 12 claim — "Shape 2 `case cst.Span.kind:` matches a Rust `fltk._native.Span` separator" — is not demonstrated end-to-end through the dispatch mechanism. A bug where `fltk._native.Span.kind` returns an object that satisfies `==` but not Python's `match`/`case` value-pattern dispatch (which uses `==` but in a specific evaluation order) would be missed.

**Fix:** Add a test that constructs a `match`/`case` dispatch against a standalone `RustSpan` instance (or inject one into a child list), asserts it hits the `cst.Span.kind` arm, and does not fall through to `case _:`. This directly exercises Shape 2 against a `fltk._native.Span` object.

---

### test-5

**File:** `tests/test_clean_protocol_consumer_api.py` — no test for the acyclicity invariant

**What's wrong — missing coverage for a load-bearing constraint.** Design §2.2 marks the acyclicity invariant (`terminalsrc` must never import `fltk._native`) as load-bearing: if it breaks, `Span.kind` access on a Rust span causes an import cycle at runtime. The import-isolation test (`test_protocol_import_does_not_import_concrete_backends`, line 347) checks that importing the *protocol module* doesn't pull in `fltk._native`, but it does not verify the converse: that `terminalsrc` itself does not import `fltk._native`. These are different checks — the protocol module imports `terminalsrc`, and if a future change adds `fltk._native` to `terminalsrc`, the test at line 347 would still pass (because importing the *protocol module* goes through `terminalsrc`, and `terminalsrc` loading `fltk._native` would register `fltk._native` in `sys.modules` by the time the assert runs, causing the test to *fail* — wait, actually no: the subprocess test would catch this because `fltk._native` would be in `sys.modules` after `import fltk.fegen.fltk_cst_protocol`). On re-examination: the line-347 subprocess test WOULD catch a `terminalsrc → fltk._native` import because it checks `'fltk._native' not in sys.modules`. So this is NOT a gap in detection of the cycle itself. However, the acyclicity is never directly stated as an invariant in a test docstring, making it invisible to future maintainers. This is a documentation/clarity gap rather than a strict coverage gap.

**Consequence:** Low; the line-347 test would catch the regression. No code-correctness finding.

**Disposition:** Informational only; not a numbered blocking finding. Omitted from the numbered list.

---

## Summary

Four numbered findings: test-1 (TYPE_CHECKING not checked in forbidden-patterns test), test-2 (NodeKind nonmatching `!=` doesn't cover Rust backends), test-3 (PROTOCOL_MODULE_PATH unused; no file-level suppression guard on the generated module), test-4 (AC 12 Rust `fltk._native.Span` separator not exercised through `match`/`case` dispatch end-to-end).

The canonical-string invariant (§4 item 7) is well-covered for `NodeKind` and `SpanKind`; `Label` canonical strings cover `Items.Label` members across all three backends. Cross-backend equality/hash for matching members is thorough. Shape 1 and Shape 2 pyright+ruff cleanliness tests are structurally sound — the fixture contains both traversal patterns and the subprocess-based tools run from the project root with the live package available.
