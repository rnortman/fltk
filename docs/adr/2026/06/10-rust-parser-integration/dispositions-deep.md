Style note: concise, precise, complete, unambiguous. No padding.

---

errhandling-1:
- Disposition: Fixed
- Action: `tests/test_phase4_fegen_rust_backend.py:258-261` — replaced bare `parser.error_message()` message with f-string that includes `result.pos`, `len(text)`, and the error tracker output. Partial-consume boundary is now always visible in the failure message.
- Severity assessment: operationally minor (test code only), but the design doc's own claim ("partial-consume failures surface a formatted error") was only half-true without the stall boundary in the message.

errhandling-2:
- Disposition: Fixed
- Action: `tests/test_phase4_fegen_rust_backend.py:277` — added `assert _FEGEN_FLTKG_PATH.exists(), f"fegen.fltkg not found at {_FEGEN_FLTKG_PATH}"` before `read_text(encoding="utf-8")`. Also added explicit `encoding="utf-8"` (fixes test-2 simultaneously).
- Severity assessment: without the guard, a missing file produces an unguarded `FileNotFoundError` indistinguishable from a pytest infrastructure failure; the guard gives actionable context about the path derivation at line 54.

correctness-1:
- Disposition: Fixed
- Action: `docs/adr/2026/06/10-rust-parser-codegen/README.md:67-68` — replaced `tests/test_rust_parser_parity.py` (nonexistent) with `tests/test_rust_parser_parity_fegen.py`, `tests/test_rust_parser_parity_fixture.py` (the actual files). Confirmed via `ls tests/ | grep parity`.
- Severity assessment: the ADR is treated as immutable per CLAUDE.md; a dangling reference to the "parity tests are the contract" mitigation would permanently mislead future readers who follow the pointer.

test-1:
- Disposition: Fixed
- Action: `tests/test_phase4_fegen_rust_backend.py:262` — added `assert isinstance(result.result, fegen_rust_cst.Grammar), type(result.result)` immediately after the `result.pos` assertion in `_assert_rust_parser_equals_python`. Pins the return type at the test boundary.
- Severity assessment: without the pin, a future binding change that changes the return type fails deep inside `Cst2Gsm` as an `AttributeError`, obscuring which layer broke.

test-2:
- Disposition: Fixed
- Action: `tests/test_phase4_fegen_rust_backend.py:278` — `read_text()` → `read_text(encoding="utf-8")`. Fixed together with errhandling-2.
- Severity assessment: non-UTF-8 CI locale would produce a garbled-input parse failure rather than an encoding error, making diagnosis hard; explicit encoding eliminates the ambiguity.

reuse-1:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: divergence risk is real but the design explicitly chose direct `fegen_rust_cst.Parser` invocation over `plumbing.parse_grammar` to test a different composition (the parser-direct path that `plumbing` wraps). Using `parse_grammar(text, rust_fegen_cst_module=...)` would test that `plumbing` calls the right things, not that the parser itself works end-to-end. The reuse reviewer's own note acknowledges the design's rationale.
- Rationale: design.md §2.2 states "Exercises `fegen_rust_cst.Parser` *directly* (not via `plumbing.parse_grammar`)"; collapsing to two `parse_grammar` calls would turn this into a duplicate of `TestAC8RealCst2GsmRustBackend`, leaving the parser-direct path untested. The maintained-duplicate concern is outweighed by the distinct test surface.
