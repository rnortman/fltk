# Deep error-handling review — spanprotocol-native-linecol

Commit reviewed: ca06929cd0c5f8589fe9589e7d4135f907b1f9d6 (base 8adf9e3)

No findings.

Scope of diff: `span_protocol.py` is a pure static-type-surface change (retyped
`line_col`/`line_col_or_raise` return annotations, new `LineColPosProtocol`, re-export of
`LineColPos`). No runtime behavior, no new error paths. The rest is test code
(`test_span_protocol_assignability.py`, new `test_span_protocol_native_free.py`).

Examined and cleared:
- `test_span_protocol_native_free.py::_identifiers_in_string_annotation` swallows `SyntaxError`
  and returns `set()`. This is a deliberate, commented fallback for non-annotation string
  constants (docstrings). It does not create a real evasion of the alias-channel guard: any
  valid annotation string (e.g. `"_RustLineColPos | None"`) parses cleanly under
  `mode="eval"`, so a genuinely-leaked native alias would still be detected. Acceptable.
- `ast.parse(_SOURCE_PATH.read_text(...))` at module import fails loudly on a malformed
  `span_protocol.py` — correct crash-on-invariant-violation for a guard test.
- Both protocol classes are asserted present before the other guards run, so the guard cannot
  pass vacuously via rename.
