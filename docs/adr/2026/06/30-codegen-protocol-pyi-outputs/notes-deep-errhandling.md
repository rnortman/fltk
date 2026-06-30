errhandling-1

File: fltk/fegen/genparser.py:494, in `gen_rust_cst`.

Broken error path: the write guard for `--protocol-output` is
`if protocol_output is not None and protocol_text is not None:`, using a double
condition. `protocol_text` starts as `None` and is set by
`protocol_text = gen.generate_protocol()` inside the try-except. At the write
point, if `protocol_output is not None`, then either `protocol_text` was
successfully assigned (so the second condition is redundant) or an exception
was raised and the caller already exited — meaning the double guard can never
produce a diagnostic exit; it silently skips the write with no log message and
exits 0 instead.

Why this matters: the parallel `init_pyi_text` write uses
`assert init_pyi_text is not None` (lines 505–506), which would at least surface
as an `AssertionError` on a control-flow defect. The `protocol_text` path has no
such guard. If a future change introduces an error-recovery branch inside the
try block that sets `protocol_text = None` rather than raising, the function
exits 0 with the `.rs` and `.pyi` written but `cst_protocol.py` absent and
nothing logged. The Bazel action succeeds; the `generate_protocol` output is
simply not on disk.

Consequence: a silent partial-output failure: Bazel reports success, downstream
consumers that import the generated protocol module get `ModuleNotFoundError` at
runtime (or a missing `cst_protocol.py` that was declared as a Bazel output),
with no log at the generation step to point on-call to the cause.

What must change: replace the double condition with an assertion mirroring the
`init_pyi_text` pattern — `assert protocol_text is not None` before the write —
so the invariant violation surfaces immediately rather than silently eliding the
write. The `if protocol_output is not None:` alone is the necessary guard; the
`and protocol_text is not None` arms the silent-skip trap.
