# Deep error-handling review — native-span-init-error-context

Commit reviewed: b60f8c7873249598fc4486b49a676b3c35e9a1cb (base f8f34288)

## Findings

No findings.

## Notes

The diff's substance *is* an error-handling improvement, and it is done correctly:

- `src/lib.rs:17-23` / `gsm2lib_rs.py:200-208`: `Py::new(m.py(), Span::unknown())`
  now `.map_err`-wrapped into a `PyRuntimeError` that embeds the original error text
  (`{e}`) plus the module-init context. Context is preserved, not lost; the error
  propagates via `?` to pyo3's import machinery, which surfaces it as a failed
  `import` — a real handler. Reporting improved (previously a bare error with no
  sentinel-creation context, per the resolved TODO).
- `m.add("UnknownSpan", ...)?` (lib.rs:24) left unwrapped — deliberately scoped out
  in the design (§Edge cases, double-wrap asymmetry). Still propagates loudly via `?`;
  OOM-bound only. Acceptable.
- `UNKNOWN_SPAN.set(...).expect("... module initialized twice")` (lib.rs:25-27):
  this is a genuine invariant violation (pyo3 initializes a module once); panicking
  with a descriptive message is the correct "unexpected invariant" response, and the
  message is diagnosable by on-call. Correct classification.
- Brace escaping (`{{e}}` in the Python f-string, gsm2lib_rs.py:204) is correct so
  `{e}` survives into Rust; `spec.module_name` is a Rust identifier, so no `format!`
  malformation / compile risk.
- Exception type shift MemoryError -> RuntimeError is import-time-OOM-only and cannot
  be meaningfully depended on; not an error-response regression.
