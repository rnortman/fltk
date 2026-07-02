# Quality review — forged-abi-extract-span-uniformity

Reviewed: `a330940..aa9a5f2` (HEAD aa9a5f27d4d307a43bfc9115857a9e52e4a384cb).

Overall: the substantive change is the right one — one-line gate at the cache-seeding
point, direct fix of the real hole rather than a workaround, no public-API impact, and the
test plan is faithfully executed. Findings below are all in the "keep the codebase from
accreting" category; none block the change.

## quality-1: third copy of the no-op `_run_script` staticmethod wrapper

- `tests/test_rust_span.py:1106-1109` (`TestForgedSpanRejected._run_script`)
- The new class adds a `@staticmethod _run_script` whose entire body is
  `return _run_script(script)` — a delegation to the module-level helper that already
  exists (`tests/test_rust_span.py:17-25`). This is the third such copy
  (`TestSpanPathAbiGate:499`, `TestForgedSourceTextRejected:881`). The wrapper adds no
  behavior, no docs beyond a restated one-liner, and no seam anyone overrides.
- **Consequence**: the pattern is now entrenched — every future subprocess-test class will
  cargo-cult a fourth and fifth copy, and a change to subprocess invocation (e.g. adding an
  env var or timeout) invites someone to edit one wrapper and miss the fact that all three
  are the same function anyway.
- **Fix**: in the new class, call the module-level `_run_script(script)` directly and drop
  the staticmethod. Ideally delete the other two wrappers in the same pass (mechanical,
  `self._run_script` → `_run_script` at each call site).

## quality-2: padded-forge residual prose duplicated 4x; the diff adds two near-identical copies

- `crates/fltk-cst-core/src/cross_cdylib.rs:443-449` (extract_span SAFETY, "Residual: ...")
  and `crates/fltk-cst-core/src/cross_cdylib.rs:485-488` (get_span_type doc,
  "**Residual (documented, not closed)**: ...")
- The `__slots__`-padded-forge residual is already documented in full at
  `check_instance_layout`'s doc comment (lines 287-291, the canonical home for a property
  of that helper) and in `extract_source_text`'s doc (lines 67-73). This diff adds two more
  full restatements ~40 lines apart. The copy at the `unsafe` site (extract_span SAFETY) is
  justified — Rust convention wants the complete soundness argument at the
  `cast_unchecked`, and the Span-specific "un-padded subclass also passes `is_instance`"
  nuance genuinely lives there. The copy in `get_span_type`'s doc comment is pure
  duplication of the SAFETY comment directly below it plus the helper doc.
- Same pattern with the "**Ordering is load-bearing**" paragraph (get_span_type doc,
  lines 470-477), which restates `extract_source_text`'s ordering paragraph (lines 56-62)
  nearly verbatim. One added wrinkle: the new copy names the Python test class
  `TestSpanPathAbiGate` from Rust source — a cross-language reference that silently rots on
  a test rename (the SourceText counterpart deliberately says only "existing tests that pin
  `check_abi_pair` error messages").
- **Consequence**: four synchronized copies of safety prose. When the residual is ever
  narrowed/closed (the SourceText tests already anticipate re-evaluation:
  `test_padded_forge_passes_basicsize_gate_boundary`), someone must find and edit all four;
  a missed one leaves a stale safety claim next to an `unsafe` block — the worst place for
  documentation drift.
- **Fix**: in `get_span_type`'s doc, replace the residual paragraph and the ordering
  paragraph bodies with one-liners referencing the canonical homes ("gate ordering and the
  padded-forge residual: see `check_instance_layout` and the SAFETY comment in
  `extract_span`"), keeping only the invariant statement that is genuinely about this
  function (`FLTK_NATIVE_SPAN_TYPE` only ever holds a dual-gated type). Drop the
  `TestSpanPathAbiGate` name in favor of the SourceText comment's phrasing.

## quality-3: subprocess result-assertion block copy-pasted a 3rd and 4th time

- `tests/test_rust_span.py:1141-1149` and `tests/test_rust_span.py:1186-1194`
- The three-assert epilogue (`returncode != -11` with SIGSEGV-recurrence message,
  `returncode == 0` with stdout/stderr dump, `"OK" in result.stdout`) is byte-for-byte
  identical modulo the one-line context string, and already appears twice in
  `TestForgedSourceTextRejected` (lines 909-917, 1049-1056). The diff makes it four copies.
- **Consequence**: this is the assertion contract for "forge rejected cleanly, no UB" — the
  most safety-relevant assertion in the file. Four divergent copies means a future
  hardening of the contract (e.g. also rejecting returncode 139, or asserting stderr is
  empty) gets applied unevenly, and each new forge test pastes ~10 more lines.
- **Fix**: module-level `def _assert_forge_rejected_cleanly(result, context: str)` holding
  the three asserts; each test becomes `result = _run_script(script)` +
  `_assert_forge_rejected_cleanly(result, "forged Span")`. Migrating the two SourceText
  call sites at the same time is a small mechanical win.

## quality-4: garbled isolation claim in `TestForgedSpanRejected` class docstring

- `tests/test_rust_span.py:1102-1103`: "All forge tests are subprocess-isolated (via
  fegen_rust_cst, a module-level import-or-skip) so a regression segfaults the child, not
  the suite."
- Subprocess isolation is provided by `_run_script`, not by `fegen_rust_cst`; the
  parenthetical is actually about a different fact (the fixture is a module-level
  import-or-skip, so these tests need no per-test `importorskip`). As written it reads as
  if importing `fegen_rust_cst` is the isolation mechanism.
- **Consequence**: the class docstring is the template the next forge-test author copies
  from; a wrong causal claim about the isolation mechanism propagates confusion about
  what actually protects the suite from a SIGSEGV regression.
- **Fix**: split the two facts: "All forge tests run in subprocesses (`_run_script`) so a
  regression segfaults the child, not the suite. They drive the gate via `fegen_rust_cst`,
  a module-level import-or-skip of this file."
