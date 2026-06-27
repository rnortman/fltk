# Dispositions — deep review round 7

Reviewed commit: 1fcae0bbe0063b83b1883eb439ababc9da6916d4
Fixes committed: cc336c54a519b74922d10bfeb8eac640ceaa7555 (base 72ea1e4)

Scope note: the security review reported **no findings** — nothing to disposition there.

---

## correctness-1 (non-trivia `preserve_blanks == 0` forces a HardLine, diverging from Python)

- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` `_gen_non_trivia_rule_processing` (no-preservable
  `else` arm) now emits the configured default separator spec *unconditionally* for
  `preserve_blanks == 0` — no `newline_count` read, no `>= 1` HardLine branch — matching the
  Python non-trivia arm (`gsm2unparser.py:1392-1399`). The trivia-rule branch keeps its
  single-newline HardLine (`preserve_line_at_zero=True`). The shared
  `_gen_newline_separator_ladder` helper encodes the difference. `newline_count` is bound only
  when the ladder reads it (`preserve_blanks > 0`), so the corrected path has no unused binding;
  `#[allow(dead_code)]` was added to the trivia helpers so the now-uncalled
  `_count_newlines_in_trivia` stays clippy-clean in the default config (it is public API for
  downstream grammars). The locked-in tests
  (`test_non_trivia_rule_emits_trivia_preservation_branch`,
  `test_non_trivia_rule_ws_allowed_uses_required_false_and_nil_default`) and the
  `_gen_non_trivia_rule_processing` docstring were updated to the corrected (default-only) output.
- Severity assessment: Real cross-backend divergence in the **default-config common case** —
  every non-trivia inter-token gap whose source contained a newline would render differently
  (Rust forced a line break; Python collapsed to the configured default), violating the design's
  rendered-string parity goal for out-of-tree consumers. Verified against the Python source.

## errhandling-1 (silent swallow when `unparse__trivia` returns None after `_has_preservable_trivia`)

- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Off-the-happy-path only — fires when a Trivia node the parser accepted
  cannot be re-unparsed (a generator bug or a sourceless span), which never occurs for CSTs from
  the Rust parser (they always carry source). Output would lack one inter-item separator; no
  data loss, no crash.
- Rationale (Won't-Do): The proposed fix (fall back to default/newline spacing in this arm)
  would make the Rust backend **diverge from the Python backend**, whose `if_trivia_success` has
  no `orelse` (`fltk/unparse/gsm2unparser.py:1321`) — it is equally silent and emits nothing. The
  reviewer's own note confirms this is "a faithful port … parity was the goal." The entire design
  is an explicit faithful parity port (design §2.2, §3) whose cross-backend contract is
  rendered-string equivalence (design §2.4), enforced by the parity tests (§4). Changing only the
  Rust side here would break that contract in exactly the edge case it claims to harden. Per the
  design's own precedent (§2.2, the group/nest/join separator case), any behavioral change to
  trivia-failure handling must be a deliberate **both-backends** change, out of scope for this
  Rust-port milestone and not appropriate to introduce unilaterally in respond mode.

## test-1 (no assertion that `#[pymethods]` is emitted)

- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py::test_python_bindings_module_and_pyclass` now
  asserts `"#[pymethods]" in src` and `"impl PyUnparser {" in src`.
- Severity assessment: A dropped/misspelled `#[pymethods]` would compile but yield runtime
  `AttributeError` for Python callers; the gap let that slip past generator tests.

## test-2 (`use super::cst;` assertion satisfiable by the top-level import)

- Disposition: Fixed
- Action: same test now asserts the 4-space-indented inner-module forms `"    use super::cst;"`,
  `"    use super::Unparser;"`, and `"    use super::{Renderer, RendererConfig,
  resolve_spacing_specs};"`, which the top-level header import cannot satisfy.
- Severity assessment: A dropped inner `use` would fail to compile but pass the loose assertion;
  tightening closes the false-positive.

## test-3 (dispatch unit test only checks truthiness)

- Disposition: Fixed
- Action: `test_gen_trivia_processing_unit_no_ws_and_dispatch` now fingerprints each branch —
  `if let (None, cst::TriviaChild::Span(span))` for the trivia-rule branch and
  `!acc.last_was_trivia()` for the non-trivia branch — instead of asserting non-empty output.
- Severity assessment: An inverted `is_trivia_rule` dispatch would have passed the old truthiness
  check; the fingerprints catch it.

## test-4 (multi-variant `_count_newlines_in_trivia` catch-all untested)

- Disposition: Fixed
- Action: added `test_count_newlines_in_trivia_multi_variant_emits_catchall` using a
  multi-variant `_trivia` grammar; asserts `"_ => {}" in body`.
- Severity assessment: A dropped `num_variants > 1` guard would be a `non-exhaustive patterns`
  compile error only surfaced at fixture-compile time; now caught at generator-test time.

## test-5 (per-rule spacing override path unexercised)

- Disposition: Fixed
- Action: added `test_default_separator_uses_per_rule_spacing_override` with
  `FormatterConfig(rule_configs={"r": RuleConfig(ws_required_spacing=comb.hardline())})`; asserts
  the emitted default separator carries the configured `Doc::HardLine` and not the global
  `Doc::Line`.
- Severity assessment: A wrong `rule_name` passed to `get_spacing_for_separator` would silently
  ignore per-rule overrides while all tests passed; this pins the lookup path.

## reuse-1 (duplicated `preserve_blanks` newline-branching block)

- Disposition: Fixed
- Action: extracted `_gen_newline_separator_ladder` (the `newline_count` -> `SeparatorSpec`
  ladder) in `gsm2unparser_rs.py`; both `_gen_trivia_rule_processing` and
  `_gen_non_trivia_rule_processing` call it, parameterised by indents and `preserve_line_at_zero`.
  Byte-identical output for the unchanged paths (verified by the existing generator tests).
- Severity assessment: Maintenance hazard — two ~40-line copies ~150 lines apart could drift.
  Folded naturally with the correctness-1 fix.

## quality-1 (reaching into private `_child_variants_for_rule`)

- Disposition: Fixed
- Action: added public `RustCstGenerator.child_class_names_for_rule` (parallel to
  `num_child_variants`) in `fltk/fegen/gsm2tree_rs.py`; `_gen_has_preservable_trivia_method` now
  calls it instead of the private `_child_variants_for_rule`.
- Severity assessment: Porous abstraction boundary — a refactor of the private helper would
  silently break the unparser generator; the public wrapper restores the boundary.

## quality-2 (copy-pasted `preserve_blanks` extraction)

- Disposition: Fixed
- Action: extracted `_get_preserve_blanks()` in `gsm2unparser_rs.py`; both trivia branches call
  it.
- Severity assessment: Minor duplication; eliminated alongside reuse-1.

## efficiency-1 (newline counting allocates a String per inter-token gap)

- Disposition: Fixed
- Action: added an allocation-free `Span::text_str(&self) -> Option<&str>` to
  `crates/fltk-cst-core/src/span.rs` (with `text()` now delegating to it) plus six unit tests; the
  generator emits `span.text_str().map(...)` in the trivia-rule newline binding and
  `_count_newlines_in_trivia` (`gsm2unparser_rs.py`). The regex term body keeps `.text()` (it
  retains an owned `String`). This is a minor, documented deviation from design §2.2, which
  literally specified `.text()` (noted in the implementation log).
- Severity assessment: Inter-token-gap hot path — every WS gap (capture_trivia=True, the
  formatting case) paid one heap allocation + memcpy of the gap text purely to scan for `\n`. The
  borrowing accessor removes that allocation. The residual O(end) codepoint→byte prefix scan
  inside `text_str` is unchanged (a byte-offset cache is out of scope, per the reviewer).

## efficiency-2 (trivia children walked twice per gap when `preserve_node_names` is set)

- Disposition: Won't-Do
- Action: no change.
- Severity assessment: Minor and bounded by trivia size; only in the configured-preserve-names
  case. The reviewer flagged it "for completeness" and noted the efficiency-1 `text_str` fix
  already neutralises the allocating half of the double walk.
- Rationale (Won't-Do): The two-pass structure (`_has_preservable_trivia` then
  `unparse__trivia` / `_count_newlines_in_trivia`) is a faithful mirror of the Python backend's
  control flow (`fltk/unparse/gsm2unparser.py:1306` ff.); collapsing it into a single pass would
  diverge structurally from the parity port for a bounded, minor saving, contrary to the design's
  faithful-port intent (design §2.2). The allocation cost the finding is most concerned with is
  already removed by efficiency-1.
