# Deep error-handling review — unparser-source-helper

Commit reviewed: f07852a5ebb26c6c3534be0457f07ac5f13b4041 (base 007401ed)
Scope: fltk/plumbing.py, fltk/test_plumbing.py, fltk/unparse/test_is_span_guard.py

No findings.

The change is a behavior-preserving refactor: the assembly pipeline is factored into a
private `_assemble_unparser_module` helper, and `generate_unparser` now execs the string that
helper returns instead of re-unparsing the module inline. No error-handling surface changed.

Notes on what was checked and why it is clean:
- `exec_globals["Unparser"]` (plumbing.py:338) is a pre-existing KeyError-on-missing-class
  access, unchanged by this diff — it relies on the generator always emitting a class named
  `Unparser` (a code-generation invariant, not user input). Not introduced here.
- `formatter_config or FormatterConfig()` coalescing moved into the shared helper; both entry
  points now get identical None-handling. No swallowed error, no divergence.
- `exec(source, ...)` (plumbing.py:335) — any exception from generated code still propagates to
  the caller exactly as before; the refactor did not wrap or suppress it.
- Test additions (test_plumbing.py) exercise the exec contract; the test-file refactor removes
  duplicated pipeline code with no error-path implications.
