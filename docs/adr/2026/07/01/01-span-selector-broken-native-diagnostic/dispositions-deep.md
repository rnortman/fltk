# Dispositions — deep review, span-selector-broken-native-diagnostic (round 1)

Base f71a765 → new HEAD 16e15fe04a1c5307030a38781a3f2f582d17b1c0.

Five reviewers (error-handling, correctness, security, test, efficiency) returned
**No findings** and independently confirmed the change is correct: `except Exception:` →
`except ImportError:` at both lockstep sites, the broken-native tests genuinely fail
against the pre-fix code (non-vacuous), and the full test file passes. Nothing to
disposition from those five.

Two reviewers (reuse, quality) raised the **same** finding about duplicated test
boilerplate. Handled together below.

---

reuse-1 / quality-1:
- Disposition: Fixed
- Action: Extracted a `_native_replaced(fake, module_to_reload)` context manager in
  `tests/test_span_protocol.py:20-47` and routed all four backend-reload tests through it
  (`test_reload_without_native_emits_no_warning`,
  `test_span_selector_broken_native_propagates`,
  `test_span_protocol_broken_native_propagates`,
  `test_span_protocol_absent_native_falls_back_silently`). The load-bearing PyO3
  double-init invariant (restore the saved original module object before the restorative
  reload; never delete-and-reimport) now lives once, in the helper's docstring, instead of
  being implied by four hand-copied `finally` blocks and documented only in the design.
  The roundabout one-key dict-comprehension is replaced by `sys.modules.get`. 49 tests
  pass; ruff clean; the pre-existing pyright error at line 556
  (`fegen_rust_cst.parser` attribute, untouched by this change) is unrelated.
- Severity assessment: Both reviewers correctly identified that the next person adding a
  backend-reload test would copy a block and could "simplify" the cleanup to
  pop + fresh import, detonating the whole pytest session with a `BaseException`-derived
  `PanicException` far from the offending test. Real maintainability hazard around a
  non-obvious safety invariant; worth fixing now while the pattern has just three copies.
  Test-only refactor, behavior-preserving (assertions and the exercised paths unchanged),
  and aligned with the design test plan's own stated intent of a "shared fixture/helper."
