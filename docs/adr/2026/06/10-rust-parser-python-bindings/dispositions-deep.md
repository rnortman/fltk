Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

# Dispositions — Phase 3 deep review (round 2)

Reviewed commit: b107645. Base: b668897. Fix commits: a06a422 (round 1), see HEAD (round 2).

---

## errhandling-1

- Disposition: Fixed
- Action: `tests/parser_parity.py` `assert_error_equiv`: on the no-error path (`py_pos == -1`), now calls `py_errors.format_error_message` on the Python side and `rust_parser.error_message()` on the Rust side and passes both through `_assert_messages_equiv`. Previously exited early without comparing messages. Both backends emit the same stub form (`"Syntax error at line 1 col 0:\n\n^\nExpected:\n"`) on a no-error parse, not an empty string.
- Severity assessment: A Rust regression that emits a structurally different no-failure message (e.g., from a leftover error state) would previously pass `assert_error_equiv` silently. Now caught by structural comparison.

---

## errhandling-2

- Disposition: Fixed
- Action: `tests/parser_parity.py` `_parse_error_message`: after parsing, counts lines in the raw message containing `'From rule "'` and asserts that count equals `len(rule_sections)`. Any indentation drift that causes `_parse_error_message` to misclassify `From rule "..."` lines produces a mismatch and fails loudly. The no-failure stub form (zero `From rule "..."` lines) correctly yields an empty `rule_sections` and the assert passes. Removed `TODO(parity-test-error-msg-format-validation)` from `TODO.md` and the docstring.
- Severity assessment: Indentation drift between backends silently produced empty `rule_sections` dicts that compared equal on both sides, masking structural divergence — exactly the class of regression the comparator exists to catch. Now fails loudly at parse time.

---

## errhandling-3

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Reviewer self-downgraded to diagnostic-quality only. The FAIL branch correctly catches outcome disagreement; the error message `"Error position: Python=5 but Rust=None"` is admittedly confusing when Rust actually succeeded, but a separate `assert rust_result is None or rust_result.pos < len(text)` (already present at line 135/136) fires first with the clearer message. No correctness gap.
- Rationale (Won't-Do): Finding is diagnostic clarity only, not a broken error path. Reviewer explicitly withdrew it.

---

## errhandling-4

- Disposition: Fixed
- Action: `tests/test_rust_parser_parity_fixture.py` PARTIAL branch replaced with the strict unconditional form matching `test_rust_parser_parity_fegen.py`: `assert py_result is not None`, `assert rust_result is not None`, position and tree equality asserts. Removed the `expected.pos == 0 and py_result is None` special case (which was FAIL semantics misplaced in PARTIAL). See also correctness-1, quality-1, test-3 — same finding.
- Severity assessment: A PARTIAL corpus entry with `expected.pos > 0` silently passed when the Python parser returned None, masking Python regressions and cross-backend divergence. Now fails loudly.

---

## correctness-1

- Disposition: Fixed
- Action: Same fix as errhandling-4. Single code change at `tests/test_rust_parser_parity_fixture.py:126-133`.
- Severity assessment: Design §2.4 invariant "an entry where backends disagree on outcome always fails" was violated for PARTIAL entries with non-zero expected position. Silent vacuous green.

---

## correctness-2

- Disposition: Fixed
- Action: FAIL branch in both `tests/test_rust_parser_parity_fegen.py` and `tests/test_rust_parser_parity_fixture.py` now asserts `(py_result is None) == (rust_result is None)` and, when both are non-None, `py_result.pos == rust_result.pos` before calling `assert_error_equiv`. Both files updated symmetrically.
- Severity assessment: Backend outcome disagreement in the FAIL branch (one None, one partial; or both partial at different positions) was undetected as long as the farthest-failure trackers coincided. This is precisely the drift class the parity suite is the contract against (design §2.7).

---

## correctness-3

- Disposition: TODO(parser-bindings-name-collision)
- Action: Added `TODO(parser-bindings-name-collision)` to `TODO.md` and added the TODO comment with rationale at `fltk/fegen/gsm2parser_rs.py` `_gen_python_bindings` docstring.
- Severity assessment: A grammar with a rule named `parser` or `apply_result` generates a CST class that silently shadows the `PyParser`/`PyApplyResult` binding class in the module — the CST node class becomes unreachable. Real risk for downstream grammars (fltk is a parser toolkit; `parser` is a plausible rule name). Deferred as the fegen grammar is safe and adding a generation-time check is a straightforward follow-up.

---

## security-1

- Disposition: TODO(parser-depth-limit) [depth limit deferred]; stack warning Fixed (interim)
- Action: `TODO(parser-depth-limit)` and `TODO(apply-depth-limit)` remain in `TODO.md` tracking the full fix. Interim: `_gen_python_bindings` now emits five `///` doc comment lines above the `#[pyclass(name = "Parser")]` struct declaration, warning about the stack-depth risk. pyo3 surfaces these as Python `__doc__` on the generated `Parser` class. Generated artifacts (`tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`) updated via `make gencode`.
- Severity assessment: Stack exhaustion on deeply nested input causes uncatchable process abort, strictly worse than Python's catchable `RecursionError`. The warning is now visible to Python callers via `Parser.__doc__`. The full fix (configurable depth counter) remains deferred under `TODO(parser-depth-limit)`.

---

## test-1

- Disposition: Fixed
- Action: `fltk/fegen/test_gsm2parser_rs.py` `test_python_bindings_apply_methods_per_rule`: extracted `bindings_block` via `src.split("mod python_bindings {", 1)[1].split("\n}", 1)[0]` before asserting. All three assertions now scope to the bindings block, not the whole file.
- Severity assessment: A generator regression that omits the per-rule methods from the bindings block would still pass (the native pub `apply__parse_*` fn exists at file scope). Now correctly fails on missing-from-bindings regressions.

---

## test-2

- Disposition: Fixed
- Action: Added `test_python_bindings_apply_methods_use_correct_class_names` to `fltk/fegen/test_gsm2parser_rs.py`: extracts the bindings block, then asserts `"cst::PyItems::to_py_canonical" in bindings_block` and `"cst::PyItem::to_py_canonical" in bindings_block` using `_make_two_rule_grammar()` (two distinct rules with distinct class names). Also asserts the count of `to_py_canonical` occurrences covers all rules including trivia.
- Severity assessment: A copy-paste bug in the per-rule loop writing the wrong class name (e.g., `PyItems` for the `item` rule) would produce wrong-type handles at runtime, only caught after building the extension. Now fails fast in pure-Python generator unit tests.

---

## test-3

- Disposition: Fixed
- Action: Same fix as errhandling-4/correctness-1. `tests/test_rust_parser_parity_fixture.py`.
- Severity assessment: See errhandling-4.

---

## test-4

- Disposition: Fixed
- Action: `tests/test_rust_parser_bindings.py`:
  - `test_error_message_on_fresh_parser`: replaced `isinstance(msg, str)` with a cross-backend equality check — constructs the Python parser on empty text, calls `format_error_message`, asserts `rust_msg == py_msg`. Pins the exact no-failure form.
  - `test_error_message_after_failed_parse`: replaced `assert "Syntax error" in msg or "Expected" in msg` with two separate asserts: `assert "Syntax error" in msg` and `assert "Expected" in msg`.
- Severity assessment: No-failure form content was unverified (just `isinstance`); after-failure `or` allowed one required pattern to be absent. Both weaknesses could mask Rust regressions in error message formatting.

---

## test-5

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: `test_assert_cst_equal_fails_for_different_inputs` uses two trees from different-length inputs; it likely fails at root span before child recursion. Reviewer notes this is redundancy (overlaps `test_assert_cst_equal_fails_span_mismatch`) rather than a gap. All targeted comparator self-tests (kind, span, label, child-count, deep-child, species) are covered by the other self-tests; this entry provides no path coverage not already present.
- Rationale (Won't-Do): The reviewer explicitly marked this as non-blocking redundancy. Renaming the test is cosmetic; won't change.

---

## reuse-1

- Disposition: Fixed
- Action: Extracted `run_parity_corpus_entry(py_p, rust_p, ts, rule, text, expected)` into `tests/parser_parity.py`. Both `tests/test_rust_parser_parity_fegen.py` and `tests/test_rust_parser_parity_fixture.py` `test_parity` bodies now delegate to it (3 lines each: construct parsers, TerminalSource, call helper). Removed `TODO(parity-test-corpus-deduplication)` from `TODO.md` and TODO comments from both files. Unused imports (`PARTIAL` in fegen, `assert_cst_equal`/`assert_error_equiv` in fixture) cleaned up.
- Severity assessment: Contract changes (PARTIAL strictness, new assertions) now only need to be made in one place. The errhandling-4/correctness-2 fixes that were applied to both files in round 1 would have been a single edit under this structure.

---

## quality-1

- Disposition: Fixed
- Action: Same fix as errhandling-4/correctness-1/test-3.
- Severity assessment: See errhandling-4.

---

## quality-2

- Disposition: Fixed
- Action: Added `assert_messages_equiv(msg_a: str, msg_b: str) -> None` public wrapper to `tests/parser_parity.py`. Callers (currently `test_rust_parser_parity_fegen.py`) that import `_assert_messages_equiv` can continue doing so (internal repr not changed); new callers should use the public wrapper. The `_` prefix on `_assert_messages_equiv` now accurately signals its internal role.
- Severity assessment: `_assert_messages_equiv` was underscore-prefixed (internal) but imported externally from test modules, creating a leaky abstraction. Future refactors of internal representation would break external callers with no indication they held a contract. The public wrapper removes the leakage.

---

## quality-3

- Disposition: Fixed
- Action: Added explanatory comments above `cargo-check` and `cargo-clippy` in `Makefile` documenting the policy. Also applied efficiency-1 fix (removed redundant per-fixture `cargo check` lines). See efficiency-1 for the mechanical change; quality-3's documentation concern is addressed by the comments.
- Severity assessment: Low. Inconsistent placement of test crates across `cargo-check` and `cargo-clippy` added cognitive overhead for future crate additions. Now documented.

---

## quality-4

- Disposition: Fixed
- Action: Refactored `_gen_python_bindings` in `fltk/fegen/gsm2parser_rs.py`. Non-parametric boilerplate (ApplyResult struct, PyParser struct with doc warnings, check_pos, #[pymethods] header methods, register_classes) replaced with two multi-line template strings (`boilerplate` and `closing`). The per-rule `apply__parse_<rule>` methods remain as a loop between them. Removed `TODO(gen-python-bindings-template-style)` from `TODO.md` and docstring. Verified `make gencode` produces stable output; all generator unit tests pass.
- Severity assessment: `_gen_python_bindings` was the only append-per-line method in the generator; now matches the style of all other methods. Future structural changes to the boilerplate are a single template edit.

---

## efficiency-1

- Disposition: Fixed
- Action: `Makefile` `cargo-check` target: removed the two per-fixture `cargo check` lines (`tests/rust_cst_fegen` and `tests/rust_parser_fixture --features python`). `cargo-clippy` already runs both at the same feature sets and is a strict superset; running both in `make check` double-compiled each fixture crate on every commit. Added policy comments above both targets.
- Severity assessment: Recurring duplicate compile work on every `make check` / CI run. Each fixture crate (and its path-dep workspace members) was type-checked twice per gate run with no benefit. Fixed.
