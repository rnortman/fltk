# Judge verdict — deep review

Phase: deep. Base 72ea1e4..HEAD cc336c5. Round 1.
Notes: 7 reviewer files (security: no findings); 12 dispositioned findings.

## Added TODOs walk

No `TODO(...)` comments added in the diff (`git diff 72ea1e4..cc336c5` finds none). No TODO dispositions to score.

## Other findings walk

### correctness-1 — Fixed
Claim: `_gen_non_trivia_rule_processing` no-preservable `else` arm reads `newline_count` and forces a `HardLine` on a bare newline when `preserve_blanks == 0`, diverging from the Python non-trivia branch (`gsm2unparser.py:1392-1399`, which emits the default separator unconditionally). Consequence: in the default config (`preserve_blanks=0`) every non-trivia inter-token gap whose source held a newline renders differently across backends — violates the rendered-string parity goal. Real cross-backend divergence in the common case → blocker.
Evidence: Python source confirmed — `gsm2unparser.py:1392-1399` is `else:` → unconditional `_add_default_separator_spec`, no newline check; `newline_count` (`:1346`) is read only inside the `preserve_blanks > 0` arm. Fix: the no-preservable arm now calls the new shared `_gen_newline_separator_ladder(..., preserve_line_at_zero=False)`. That helper's `preserve_blanks == 0` / no-`preserve_line_at_zero` path (`gsm2unparser_rs.py` ladder `else:` branch) emits `_add_default_separator_spec_lines` unconditionally — no `if newline_count` test. `newline_count` is bound only when `preserve_blanks > 0` (guarded `if preserve_blanks > 0:` ahead of the ladder), so no unused binding. The trivia-rule branch keeps `preserve_line_at_zero=True` (single-newline `HardLine` for comments), matching `gsm2unparser.py:1216-1242`. The previously-locked-in tests now assert the corrected output: `test_non_trivia_rule_emits_trivia_preservation_branch` asserts `"let newline_count" not in body`, `"Doc::HardLine" not in body`, and `separator_spec(Some(Doc::Line), None, true)` present.
Assessment: fix addresses the consequence at the named site, matches the Python branch, and the lock-in test now pins the corrected (default-only) behavior. Accept.

### errhandling-1 — Won't-Do
Claim: when `_has_preservable_trivia` is true but `unparse__trivia` returns `None`, the generated Rust advances `pos` past the Trivia child, emits no separator and no diagnostic. Consequence: a separator is silently dropped; on-call has nothing to diagnose.
Evidence: the reviewer's own note states this is "a faithful port of Python's `if_trivia_success` having no `orelse`." Confirmed at `gsm2unparser.py:1321`: `if_trivia_success = if_has_preservable.block.if_(trivia_result_var.load())` — `.if_()` with no `orelse`; on falsy `trivia_result` nothing is emitted and `pos` advances at `:1402`. The Python backend is equally silent. Responder's rationale: the design is an explicit faithful-parity port (design §2.2/§3) whose cross-backend contract is rendered-string equivalence (§2.4); a Rust-only `else` fallback would diverge from Python in exactly this case, breaking the parity contract; the path fires only for a Trivia node the parser accepted but cannot re-unparse (generator bug / sourceless span) which never occurs for Rust-parser CSTs (they always carry source). Any change must be a both-backends change, out of scope for the port milestone.
Assessment: consequence is genuinely off-happy-path (impossible for Rust-parser CSTs), and the Won't-Do argues active harm of the fix — unilateral Rust divergence breaks the milestone's stated parity contract. This is a Won't-Do with a sourced active-harm rationale, not a silent defer. Accept.

### test-1 — Fixed
Claim: no test asserts `#[pymethods]` is emitted; a dropped/misspelled attribute would compile but yield runtime `AttributeError`. Consequence: silent runtime breakage past generator tests.
Evidence: `test_python_bindings_module_and_pyclass` now asserts `"#[pymethods]" in src` and `"impl PyUnparser {" in src`.
Assessment: closes the gap at the named test. Accept.

### test-2 — Fixed
Claim: `assert "use super::cst;" in src` is satisfied by the top-level header import, so a dropped inner-module `use` is undetected (would fail to compile).
Evidence: same test now asserts the 4-space-indented inner forms `"    use super::cst;"`, `"    use super::Unparser;"`, and `"    use super::{Renderer, RendererConfig, resolve_spacing_specs};"`, which the unindented header import cannot satisfy.
Assessment: false-positive closed. Accept.

### test-3 — Fixed
Claim: dispatch unit test asserts truthiness only; an inverted `is_trivia_rule` dispatch would still pass since both branches emit non-empty for WS.
Evidence: `test_gen_trivia_processing_unit_no_ws_and_dispatch` now fingerprints each branch — trivia-rule via `any("if let (None, cst::TriviaChild::Span(span))" ...)`, non-trivia via `any("!acc.last_was_trivia()" ...)` — both branch-unique.
Assessment: fingerprints catch an inverted dispatch. Accept.

### test-4 — Fixed
Claim: multi-variant `_count_newlines_in_trivia` `_ => {}` catch-all untested; a dropped `num_variants > 1` guard surfaces only as a fixture compile error.
Evidence: added `test_count_newlines_in_trivia_multi_variant_emits_catchall` with a multi-variant `_trivia` (`ws` Span + node-typed `comment`); asserts `"_ => {}" in body`. The single-variant test still asserts its absence.
Assessment: both arms of the guard now pinned at generator-test time. Accept.

### test-5 — Fixed
Claim: per-rule spacing override path through `_add_default_separator_spec_lines` unexercised; a wrong `rule_name` to `get_spacing_for_separator` would silently ignore overrides.
Evidence: added `test_default_separator_uses_per_rule_spacing_override` with `FormatterConfig(rule_configs={"r": RuleConfig(ws_required_spacing=comb.hardline())})`; asserts the emitted spec carries `Doc::HardLine` and `"Doc::Line" not in body`.
Assessment: pins the per-rule lookup path. Accept.

### reuse-1 — Fixed
Claim: the `preserve_blanks` newline-branching block is duplicated ~150 lines apart in `_gen_trivia_rule_processing` and `_gen_non_trivia_rule_processing`; drift hazard.
Evidence: extracted `_gen_newline_separator_ladder` (the `newline_count` → `SeparatorSpec` ladder), parameterised by indents and `preserve_line_at_zero`; both branches call it (trivia-rule with `preserve_line_at_zero=True`, non-trivia with `False`). Folded with the correctness-1 fix.
Assessment: single source of truth for the ladder; the parity-relevant difference is encoded in one flag. Accept.

### quality-1 — Fixed
Claim: `_gen_has_preservable_trivia_method` reached into private `RustCstGenerator._child_variants_for_rule`; a refactor there would silently break the unparser generator.
Evidence: added public `child_class_names_for_rule(rule_name)` to `gsm2tree_rs.py` (parallel to `num_child_variants`). `grep` confirms the only live call in `gsm2unparser_rs.py` is now `self._cst.child_class_names_for_rule(...)` (line 1314); the remaining `_child_variants_for_rule` mention (line 1297) is docstring text only.
Assessment: abstraction boundary restored. Accept.

### quality-2 — Fixed
Claim: `preserve_blanks` extraction copy-pasted into both trivia branches.
Evidence: extracted `_get_preserve_blanks()`; both `_gen_trivia_rule_processing` and `_gen_non_trivia_rule_processing` call it.
Assessment: duplication removed. Accept.

### efficiency-1 — Fixed
Claim: the generated newline counter calls `Span::text() -> Option<String>`, heap-allocating an owned copy of each inter-token gap purely to scan for `\n`; inter-token-gap hot path in the formatting case.
Evidence: added allocation-free `Span::text_str(&self) -> Option<&str>` to `crates/fltk-cst-core/src/span.rs`, with `text()` now delegating (`self.text_str().map(str::to_owned)`) plus six unit tests (ascii, multibyte codepoint indexing, slice-to-end, empty-on-empty-source, none-for-sourceless, newline-count-without-allocating). Generator emits `span.text_str().map(...)` at both newline-scan sites (trivia-rule binding and `_count_newlines_in_trivia`); the regex term body retains owned `.text()` at `gsm2unparser_rs.py:953` (it keeps a `String`), as the disposition states.
Assessment: per-gap allocation removed; the borrowing accessor is correct (lifetime tied to `&self` holding the source `Arc`) and tested. The residual O(end) prefix scan is explicitly out of scope per the reviewer. Accept.

### efficiency-2 — Won't-Do
Claim: trivia children walked twice per gap when `preserve_node_names` is set (`_has_preservable_trivia` then `unparse__trivia` / `_count_newlines_in_trivia`). Consequence: an extra O(trivia-children) pass per gap, only in the configured-preserve-names case; bounded by trivia size.
Evidence: the reviewer flagged it "for completeness" and noted efficiency-1's `text_str` already neutralises the allocating half. Responder's rationale: the two-pass structure is a faithful mirror of the Python control flow (`gsm2unparser.py:1306` ff.); collapsing it would diverge structurally from the parity port for a bounded, minor saving.
Assessment: bounded, configured-case-only micro-cost the reviewer self-classified as a completeness note → nit. Parity rationale sound. Accept.

## Disputed items

None.

## Approved

12 findings: 8 Fixed verified (correctness-1, test-1..5, reuse-1, quality-1, quality-2, efficiency-1 — that is 9 Fixed), 2 Won't-Do sound (errhandling-1, efficiency-2). Security: no findings. No added TODOs.

---

## Verdict: APPROVED

All dispositions acceptable. Both parity claims (correctness-1 fix, errhandling-1 Won't-Do) verified against the Python source at `gsm2unparser.py:1321`/`:1392-1399`. All five test tightenings present; all four quality/reuse/efficiency refactors verified in the diff. No added TODOs. Round 1.
