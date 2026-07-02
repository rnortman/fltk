# slop-reviewer notes

Base: f8f34288ff30e175021866746fa3b28e6a65485c
HEAD: d9638deec5e58988e26930cfaf32cf277fbe419b

## slop-1

- File: fltk/fegen/test_gsm2lib_rs.py:222, 229, 304
- Quote: `"""Span-only lib.rs registers LineColPos as a Python class (drift fix §1)."""` / `"""Span-only lib.rs wraps Py::new sentinel creation with a structured RuntimeError (§2)."""` / `"""Drift pin (§4): committed src/lib.rs is byte-for-byte what the generator produces.`
- What's wrong: new test docstrings cite `§1`/`§2`/`§4` section numbers from an external design/workflow document rather than describing the test's behavior in self-contained terms.
- Consequence: these section references are meaningless to anyone reading the test file without the (ephemeral, non-committed-as-source) design doc open next to it; once that doc is gone the citations rot into noise. Reads as leftover workflow scaffolding rather than a finished PR.
- Suggested fix: drop the `§N` tags; let the docstring text stand on its own (it already does, e.g. "wraps Py::new sentinel creation with a structured RuntimeError").

Note: this diff continues a pre-existing convention already present elsewhere in the same file (lines 13, 81, 105, 160, 395 predate this change), so it's not a new pattern introduced here, but the newly added instances still fit the same problem.

No other issues found: the TODO.md removal correctly matches the fixed `native-span-init-error-context` TODO, the `map_err` wrapping is a real fix (not a workaround), generated `src/lib.rs` matches the generator template (verified against `test_committed_lib_rs_matches_generator`), and no empty catches / swallowed results / silent fallbacks are visible in the diff.
