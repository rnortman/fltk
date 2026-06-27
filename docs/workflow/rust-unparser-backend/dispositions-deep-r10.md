# Dispositions — deep review batch 10 (respond round 1)

Base: `028583414d5943b6e134a78c922868f45cb59361`
Reviewed HEAD: `fa22e182702d3ea1c1ec5e464345ab006941c9e9`

Scope of this batch: §4 cross-backend parity + native test code
(`tests/unparser_parity.py`, `tests/test_rust_unparser_parity_fixture.py`,
`tests/rust_parser_fixture/src/native_tests.rs`). No `scope-N` findings; no
escalation. Security review found nothing.

Verification: native fixture cargo tests `native_unparse*` (10 passed),
cross-backend parity suite (168 passed = 42 corpus × 2 configs × 2 backends),
`ruff check` + `pyright` clean on both Python files, `rustfmt --check` clean on
`native_tests.rs`.

---

errhandling-1:
- Disposition: Fixed
- Action: `tests/rust_parser_fixture/src/native_tests.rs` `render_native!` macro —
  replaced `.expect("native unparse must succeed")` with
  `.unwrap_or_else(|| panic!("native unparse failed for {src:?} (method {}): returned None", stringify!($unparse)))`,
  matching the diagnostic context the parse-failure arm already captures.
- Severity assessment: Low. No behavior change on the happy path; only improves the
  panic message when a native unparse regression fires, removing the
  guess-which-call step (several calls share one `#[test]` body).

errhandling-2:
- Disposition: Fixed (same fix as test-2; both reviewers flagged the mutual-None gap)
- Action: `tests/unparser_parity.py:assert_unparse_parity` — added
  `assert py_str is not None, ...` immediately after computing the Python result,
  before the success-agreement check. The Python backend is the reference; every
  corpus entry is a complete valid parse that must unparse.
- Severity assessment: Medium. Previously a regression that silenced both backends
  (e.g. a label-enum mismatch making every child check fail) passed all parity
  tests green; the signal the test exists to provide was lost for that case.

correctness-1:
- Disposition: Fixed
- Action: `tests/rust_parser_fixture/src/native_tests.rs` `render_native!` macro —
  changed `Parser::new(src, None, false)` to `Parser::new(src, None, true)` so the
  native path matches the parity corpus (`capture_trivia=True`), making the
  block comment's "parity-validated reference" justification airtight. All native
  expected strings are unchanged (the only internal-trivia input, `"x = y"`,
  coincides under `ws_required: nbsp`; the rest carry no internal trivia). Tests
  still pass.
- Severity assessment: Low. No prior false pass — the native test only asserts its
  own Rust-only pipeline. The defect was that the cited cross-reference held by
  coincidence of input/config; aligning the flag makes it hold by construction.

test-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_parity_fixture.py:_CORPUS` — added
  `("lval","hello")`, `("lval","42!")`, `("rval","123")`, `("rval","hello?")`.
  Verified parseable/unparseable on both backends (all 168 cells pass).
- Severity assessment: Medium. Indirect mutual recursion is a structurally distinct
  generated shape (two methods, two match arms) from the self-referencing `expr`
  path; previously it had zero cross-backend unparser coverage, so an
  alt-ordering/label-check regression there would pass silently.

test-2:
- Disposition: Fixed (deduplicated with errhandling-2 — same assertion)
- Action: see errhandling-2.
- Severity assessment: Medium (as errhandling-2).

test-3:
- Disposition: Fixed
- Action: `tests/rust_parser_fixture/src/native_tests.rs` — added
  `native_unparse_default_config_links`, a GIL-free `#[test]` that drives
  `crate::unparser_default::Unparser` (`unparse_num` on `"123"`) through
  `fltk-unparser-core`. Previously native tests only exercised the fltkfmt-baked
  `crate::unparser` module.
- Severity assessment: Medium. A compile/link failure in `unparser_default.rs`
  under the no-`python` feature configuration was undetected by the native suite
  (the module is otherwise reached only behind `#[cfg(feature = "python")]`).

test-4:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_parity_fixture.py:_CORPUS` — added
  `("opt_item","")` (optional item absent). Renders to `""` on both backends.
- Severity assessment: Medium. The absent-`?` path (`if let Some` arm skipped,
  `Some(empty doc)` returned) is a distinct generated path from both the present-`?`
  case and the `*`-loop-never-entered case (`zero_items ""`); a regression there
  was uncovered.

reuse-1:
- Disposition: Fixed
- Action: `tests/unparser_parity.py:unparse_python` — now delegates the
  unparse→resolve stage to `fltk.plumbing.unparse_cst` (catching its `ValueError`
  as the None outcome) and renders via `render_doc`, removing the duplicated
  instantiate/dispatch/`resolve_spacing_specs` pipeline and the direct
  `resolve_specs` import. Keeps the test path in lock-step with the production
  Python rendering path.
- Severity assessment: Low/medium. The duplicated pipeline could drift from
  `unparse_cst` (accumulator/resolve API changes), yielding a stale-pipeline
  false parity result. Note: a missing unparse method now surfaces as a None
  parity outcome rather than `AttributeError`, but the new errhandling-2/test-2
  assert makes that surface loudly as "reference returned None", so programming
  errors are still not silently swallowed.

quality-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_parity_fixture.py` — replaced the four
  module-level `None` globals + identically-structured `_*_cached()` functions with
  four `@functools.cache`-decorated plain functions (`_grammar`,
  `_py_parser_result`, `_py_unparser_result`, `_py_unparser_result_default`);
  removed the `# noqa: PLW0603` suppressions.
- Severity assessment: Low. Boilerplate/maintainability; each new baked config no
  longer needs a fresh global + accessor pair.

quality-2:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_parity_fixture.py` — merged
  `test_unparse_parity_fltkfmt` / `test_unparse_parity_default` into a single
  `test_unparse_parity` parametrized over a new `_BACKEND_CONFIGS` axis
  (`fltkfmt`/`default`), matching the `test_rust_parser_parity_fixture.py` precedent.
  Lambda-wrapped Rust class refs defer the import.
- Severity assessment: Low. Removes a copy-paste-per-config pattern; same 168 cells
  run.

efficiency-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_parity_fixture.py` — added `@functools.cache`
  to `_py_cst` and `_rust_node`, so each `(rule, text)` is parsed once per backend
  instead of once per `(config × backend)` cell (CSTs are read-only to the
  unparser, so sharing across cells is safe).
- Severity assessment: Low. Reviewer rated magnitude negligible at current input
  sizes; the cache removes the redundant re-parses cheaply and matters as the
  corpus grows.

security (notes-deep-security-r10):
- Disposition: no findings reported; no action.
