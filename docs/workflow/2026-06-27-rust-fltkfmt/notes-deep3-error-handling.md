## errhandling-1

**File:line**: `tests/test_fltkfmt_parity.py:129`

**Broken error path**: `proc.stdout.decode("utf-8")` — no `errors=` argument — raises
`UnicodeDecodeError` if `fltkfmt` produces output bytes that are not valid UTF-8. This
exception is raised before the intended `assert py_out == rust_out` on line 130 can
execute.

**Why**: The caller on line 127 correctly uses `proc.stderr.decode('utf-8', 'replace')`
(errors='replace'), demonstrating that the author was aware of encoding risk in process
output. The stdout path on line 129 does not carry the same protection. A `UnicodeDecodeError`
raised at line 129 propagates out of `test_fltkfmt_matches_python` with no domain context: the
exception message gives only a byte-position and "invalid start byte" or similar, with no
mention of which corpus file (`fltkg.name`), which render config (`w=`, `i=`), or what
bytes were actually emitted.

**Consequence**: If `fltkfmt` ever produces non-UTF-8 output — a Rust bug, a memory
safety issue surfacing as garbage bytes, or an encoding regression — the test crashes with
an opaque `UnicodeDecodeError` rather than the `[filename w=X i=Y] formatter output
mismatch: Python: ... Rust: ...` message the assertion is designed to produce. An on-call
engineer cannot determine which file triggered it, cannot see the actual binary output
bytes, and cannot immediately distinguish "bad bytes from the binary" from "test
infrastructure breakage". The mismatch that caused the failure is undiagnosable without
manually reproducing the run.

**What must change**: Pass `errors='replace'` (or `errors='surrogateescape'`) to
`proc.stdout.decode(...)` consistently with the stderr path. Replacing invalid bytes with
the replacement character allows the `assert py_out == rust_out` comparison to run and
produce a full mismatch report including the corrupted bytes as visible `�`
placeholders, giving on-call the file name, config, and both outputs in a single failure
message.
