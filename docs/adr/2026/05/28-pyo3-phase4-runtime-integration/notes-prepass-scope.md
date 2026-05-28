Concise. Precise. Audience: smart LLM/human. No padding.

## scope-1

**`test_cst2gsm_default_namespace_unchanged` not implemented.**

Design Test Plan §Tier 1: "assert `Cst2Gsm(terminals)` with no `cst` arg uses `fltk_cst` and produces identical `gsm.Grammar` output to today on a sample grammar (guards the DI refactor's default behavior)."

No test of this name (or equivalent) exists in the diff. `fltk/test_plumbing.py` additions cover `TestRustBackendUnavailableError`, `TestLoadRustCstClasses`, `TestGenerateParserRustBackend`, and `TestParseGrammarRustBackend` — none explicitly isolates `Cst2Gsm(terminals)` with no `cst` arg and compares its `gsm.Grammar` output to a baseline.

**Consequence:** the DI refactor's backward-compatibility guarantee for `Cst2Gsm` is not independently guarded at the unit level. A regression in the default-`cst` path in `fltk2gsm.py` would need to surface through integration paths rather than a focused unit test.

**Suggested fix:** add a `TestCst2GsmDefaultNamespace` (or equivalent) to `fltk/test_plumbing.py` or a dedicated `fltk/fegen/test_fltk2gsm.py` that parses a small grammar via the Python path, constructs `Cst2Gsm(terminals.terminals)` (no `cst=`), calls `visit_grammar`, and asserts the `gsm.Grammar` round-trips identically to the pre-DI baseline.

---

## scope-2

**`test_makefile_builds_rust_cst` (AC6) not implemented.**

Design Test Plan §Tier 2: "`test_makefile_builds_rust_cst` (AC6): `make build-test-user-ext` produces importable `phase4_roundtrip_cst`; `make build-fegen-rust-cst` produces importable `fegen_rust_cst`; `make build-native` produces `fltk._native`. Assert no cargo/maturin is invoked from any Python parse path."

No such test exists in the diff. `test_plumbing_imports_no_subprocess_or_build_tools` covers the "no build tool invocation from Python" half, but the Makefile build verification is absent.

**Consequence:** CI has no automated assertion that the committed Makefile targets actually produce importable artifacts. Drift between Makefile targets and the crate layouts would only be caught manually.

**Suggested fix:** add a test (or CI step) that invokes each `make build-*` target and asserts the resulting module is importable. This is naturally a CI concern rather than a pytest test; acceptable to record as a CI gap rather than a code gap if the project's CI already runs these before pytest (the design anticipated exactly that — "CI runs `make build-native`, `make build-test-user-ext`, and `make build-fegen-rust-cst` before `pytest`"). If CI does not yet run these, the gap is real.

---

## Deviations noted in implementation log — scope assessment

- **`fltk2gsm.visit_items` Trivia-filter fix** (Increment 7): additive bug fix, consistent with design intent, explicitly documented. Not a scope gap.
- **AC Contract item 3 span attribute deviation** (Increment 6): pre-existing design constraint (`pub(crate)` Rust fields), explicitly documented. Not a scope gap.
- All design-mandated files (modified and new) are present in the diff.
- Both TODO entries (`rust-cst-shared-rlib`, `rust-cst-abi-pinning`) have both `TODO.md` entries and code-comment placements in the diff — compliant with CLAUDE.md TODO System.

---

## Aggregate assessment

Two missing items (one Tier-1 unit test, one Tier-2/CI test) are small, self-contained additions — not net new implementation. No escalation warranted.
