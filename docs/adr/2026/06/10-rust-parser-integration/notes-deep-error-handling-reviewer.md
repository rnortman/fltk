Style note: concise, precise, complete, unambiguous. No padding.

Commit reviewed: f1423a2

---

## errhandling-1

**File**: `tests/test_phase4_fegen_rust_backend.py:258`

**Broken error path**: `assert result.pos == len(text), parser.error_message()`

**Why**: `parser.error_message()` reports the farthest-reached failure position recorded by the error tracker. When parse partially succeeds (`result is not None`) but stops short of `len(text)`, the error tracker reflects the farthest failure encountered *before* the partial match was accepted — which may be well before `result.pos`. The assertion message will show a position that precedes `result.pos`, not the actual stall point. Diagnostic is misleading: on-call sees "failed at offset X" when the parse actually succeeded to a later offset Y and then found nothing.

**Consequence**: When `test_fegen_grammar_self_hosted` fails with a partial-consume (the hardest case to diagnose, since fegen.fltkg is large), the failure message gives a misleading position, making it harder to locate the unmatched trailing input. Operationally minor since this is test code, but the test's own design doc (design.md §3) calls out "partial consume failures surface a formatted error rather than a bare assert" as a feature — the claim is only half-true when the partial result is further than the error tracker's best.

**What must change**: Augment the partial-consume message with both `result.pos` and `len(text)` so the stall boundary is always visible:
```python
assert result.pos == len(text), (
    f"Partial parse: consumed {result.pos}/{len(text)} chars. "
    f"Error tracker: {parser.error_message()}"
)
```

---

## errhandling-2

**File**: `tests/test_phase4_fegen_rust_backend.py:277`

**Broken error path**: `text = _FEGEN_FLTKG_PATH.read_text()` — unguarded, bare `Path.read_text()` in a test method body.

**Why**: `_FEGEN_FLTKG_PATH` is computed at module load time as a relative-to-`__file__` path; if the file is missing (e.g., a partial checkout, bad working directory, or path computation regression), `read_text()` raises `FileNotFoundError` with a path that contains the computed absolute path but no context about *why* the test expected it to exist or which constant is wrong. The other two test cases in the class use module-level string constants and cannot fail this way; only `test_fegen_grammar_self_hosted` has this exposure.

**Consequence**: A broken checkout or renamed grammar file produces an unguarded `FileNotFoundError` with no test-authored message, giving the same signal as a pytest infrastructure failure rather than "the self-hosting input file is missing." The failure is distinguishable from the parse assertions, but provides no on-call context about what to check (the path derivation in `_FEGEN_FLTKG_PATH` at line 54).

**What must change**: Either assert the path exists before reading, or wrap with a descriptive `pytest.fail`:
```python
assert _FEGEN_FLTKG_PATH.exists(), f"fegen.fltkg not found at {_FEGEN_FLTKG_PATH}"
text = _FEGEN_FLTKG_PATH.read_text()
```
This is the same pattern used defensively in `parse_grammar_file` (plumbing.py:194-196) for the same kind of "file expected to exist" read.

---

No other findings. The Makefile `check-no-pyo3` additions use `set -e` with positive controls before negative assertions — the established pattern; the vacuous-pass failure mode is correctly guarded. The `gsm2parser_rs.py` docstring change and the ADR README are documentation only.
