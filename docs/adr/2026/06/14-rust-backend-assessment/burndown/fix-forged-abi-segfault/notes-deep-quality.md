# Quality review: fix-forged-abi-segfault

Commit reviewed: 79460b6

---

## quality-1

**File:line** `crates/fltk-cst-core/src/cross_cdylib.rs:280,288,295`

**Issue** `check_instance_layout<T>` is generic over `T: PyClassImpl` — designed to be reusable
for any type (the design explicitly says "The helper is generic so it could later be reused for
`extract_span`"). But all three of its error messages hard-code the literal string
`"SourceText instance layout check failed:"`, with no reference to the generic type `T`. If the
helper is ever called for `Span` (or any other `T`), the error message will name `SourceText` even
though the object being checked is a `Span`, making the diagnostic actively misleading.

**Consequence** A future caller applying the helper to `Span` (the `TODO(forged-abi-extract-span-uniformity)` path) will produce messages that say `"SourceText instance layout check failed:"` when a `Span` is what was checked. Callers and users will be misled, and the misdiagnosis will propagate to every test that pins the error message for non-SourceText types. The generic type parameter signals intent to generalize; the hard-coded string is an inconsistency that will grow into a real observability gap as soon as a second call site exists.

**Fix** Accept a `type_label: &str` parameter (matching `check_abi_pair`'s own convention at
`cross_cdylib.rs:185`) and substitute it into the format strings:

```rust
fn check_instance_layout<T: PyClassImpl>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()> {
```

Then replace every `"SourceText instance layout check failed:"` prefix with
`"{type_label} instance layout check failed:"`. The single existing call site at line 122 passes
`"SourceText"` and is unchanged in behavior. The doc comment should note the convention matches
`check_abi_pair`.

---

## quality-2

**File:line** `tests/test_rust_span.py:877-885` vs `tests/test_rust_span.py:488-497`

**Issue** `_run_script` is copy-pasted verbatim into `TestForgedSourceTextRejected` (new code)
and `TestSpanPathAbiGate` (existing code). The two static methods have identical signatures,
identical bodies, and even near-identical docstrings ("return the completed process" vs "return
the completed process."). The only difference is one has a return-type annotation spelled as a
quoted string forward reference while the other does not.

**Consequence** Any future change to the subprocess invocation (timeout, encoding, security
allow-list annotation) must be applied in both places. The next test class that needs a subprocess
will copy the method a third time. The file already has this pattern duplicated; the new code
propagates it rather than arresting it.

**Fix** Hoist the helper to module level (or a shared base class) and remove both copies:

```python
def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    """Run a Python script in a subprocess; return the completed process."""
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
```

Both `TestSpanPathAbiGate` and `TestForgedSourceTextRejected` become callers of the module-level
function. No behavioral change; no duplication.
