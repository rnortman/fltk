## reuse-1

**File:line** `tests/test_rust_span.py:877–885` (new `TestForgedSourceTextRejected._run_script`)

**What's duplicated** Identical static method body as `TestSpanPathAbiGate._run_script` at `tests/test_rust_span.py:488–497`. The two methods differ only in the return-type annotation quoting style (`"subprocess.CompletedProcess[str]"` vs `subprocess.CompletedProcess[str]`); logic is byte-for-byte the same: `subprocess.run` with `[sys.executable, "-c", script]`, `capture_output=True`, `text=True`, `timeout=30`, `check=False`.

**Existing function** `TestSpanPathAbiGate._run_script` at `tests/test_rust_span.py:488`.

**Consequence** Two class-private copies of the same subprocess harness. Any future change (e.g. increasing timeout, adding an env arg for isolation, or fixing the `# noqa: S603` handling) must be applied to both sites; missing one produces silent divergence in subprocess test behaviour across the two test classes.
