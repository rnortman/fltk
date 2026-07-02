# Dispositions — deep review (round 1)

Reviewers with no findings: error-handling, correctness, security, test, reuse, efficiency.
All findings below are from the quality reviewer. Fact-checked against source; all four are
accurate. Fixes are test-only + doc-comment refactors with no behavioral change. Committed at
HEAD `fb5352bd3ce878f291b3b3c2498dc03ab739581b`.

## quality-1:
- Disposition: Fixed
- Action: Removed all three no-op `_run_script` `@staticmethod` wrappers
  (`tests/test_rust_span.py` — former `TestSpanPathAbiGate`, `TestForgedSourceTextRejected`,
  and the new `TestForgedSpanRejected`) and switched every call site from
  `self._run_script(script)` to the module-level `_run_script(script)` (`tests/test_rust_span.py:17`).
- Severity assessment: Cosmetic/maintainability — the wrappers were pure delegation with no
  behavior; leaving them would entrench a cargo-culted pattern for future subprocess-test
  classes. No correctness impact.

## quality-2:
- Disposition: Fixed
- Action: In `get_span_type`'s doc comment (`crates/fltk-cst-core/src/cross_cdylib.rs`),
  replaced the duplicated padded-forge "Residual" paragraph with a one-line pointer to its
  canonical homes (`check_instance_layout` doc + the `extract_span` SAFETY comment), and
  replaced the cross-language `TestSpanPathAbiGate` name with the generic phrasing
  "the existing subprocess tests that pin `check_abi_pair` error messages" (mirroring the
  SourceText comment). The design-mandated content (§2.2: second gate, ordering rationale,
  dual-gate invariant) is retained; only the non-mandated residual restatement was trimmed.
- Severity assessment: Documentation-drift risk near an `unsafe` block — four synchronized
  copies of the residual/ordering prose meant a future narrowing of the residual could leave a
  stale safety claim. No runtime impact.

## quality-3:
- Disposition: Fixed
- Action: Added module-level `_assert_forge_rejected_cleanly(result, context)`
  (`tests/test_rust_span.py`, after `_run_script`) holding the three-assert
  `returncode != -11` / `== 0` / `"OK" in stdout` contract, and replaced all four
  copied epilogues (two SourceText forge tests, two new Span forge tests) with a single
  call each.
- Severity assessment: This is the safety-relevant "forge rejected cleanly, no UB" assertion
  contract; four divergent copies risked uneven future hardening. Consolidating keeps it single-
  sourced. Behavior of the assertions is unchanged (still catches SIGSEGV recurrence explicitly).

## quality-4:
- Disposition: Fixed
- Action: Rewrote the `TestForgedSpanRejected` class docstring
  (`tests/test_rust_span.py`) to correctly attribute subprocess isolation to `_run_script`
  and separately note that the tests drive the gate via the `fegen_rust_cst` module-level
  import-or-skip.
- Severity assessment: Documentation accuracy — the garbled causal claim (isolation "via
  fegen_rust_cst") would mislead the next forge-test author who copies this template. No
  functional impact.
