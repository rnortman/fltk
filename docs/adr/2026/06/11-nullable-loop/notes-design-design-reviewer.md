# Design review findings: nullable-loop

Concise. Precise. Complete. Unambiguous. No padding.

Verification performed against source at base commit 7ddec4a, plus two empirical re-checks of the design's load-bearing claims:

- Trigger grammar `rule := (r"a*" .)+` (built as GSM objects) passes current `validate_no_repeated_nil_items` and hangs the current Python backend on `"aab"` (killed at 10s timeout). Design §1 empirical claim **confirmed**.
- Term-aware `Item.can_be_nil` (`quantifier.is_optional() or term_can_be_nil(term, grammar)`) applied via monkeypatch: all eight in-tree `.fltkg` grammars (fegen, bootstrap, fltk, toy, unparsefmt, poc_grammar, phase4_roundtrip, rust_parser_fixture) pass `classify_trivia_rules` validation. Design §1 claim **confirmed**.

All cited code locations verified accurate: `Item.can_be_nil` gsm.py:108-111 (with `# noqa: ARG002`); `term_can_be_nil` gsm.py:166-173; `validate_no_repeated_nil_items` gsm.py:340-356; `validate_trivia_rule_not_nil` gsm.py:328-337; validator calls gsm.py:297-299; `Rule._computing_nil` cycle guard gsm.py:39-40; invalid-regex conservatism gsm.py:147-154; Rust loop + TODO gsm2parser_rs.py:669-698 (guard insertion point before line 677, post-loop check 695-698); Python loop gsm2parser.py:555-585 (assign at 564-567, post-loop `+` check 581-585); `iir.Break` model.py:707-709; compiler lowering compiler.py:218-220; `iir.Equals` model.py:760-762; `Block.return_` pattern for the proposed `break_` helper model.py:199-201; `gsm.classify_trivia_rules` call sites gsm2parser.py:33 and gsm2tree_rs.py:48; `_trivia` guard gsm2parser.py:87-89; flipping assertions test_nil_validation.py:168-206 (`Literal("")` + REQUIRED at 173-179, + ONE_OR_MORE at 200-206); `_run_script` precedent tests/test_rust_span.py:432; `RustCstGenerator.generate` gsm2tree_rs.py:239; Makefile `gencode`/`fix`/`check` targets. The proposed IIR construction in §2.3 type-checks against the model (`Load` is `Expr` → has `.fld`; `FieldAccess` is `ValRef` → has `.load()`; `compile_expr` unwraps `Load`, renders `BinOp` as `(lhs) op (rhs)`). No other callers of `can_be_nil`/`term_can_be_nil` exist outside gsm.py and its tests, so the §2.1 tightening affects only the validators as claimed. Requirements coverage is complete (failing-test-first both backends with stop-and-escalate path, lockstep guard with placement detail, validator root fix, parity, behavior-change callout, two-layer testing, TODO bookkeeping).

## design-1

- **Section:** §2.3, quoted post-fix generated loop: "`while (one_result := <consume>) is not None:`".
- **What's wrong:** The Python compiler emits a bare-truthiness walrus loop, not an `is not None` comparison. Actual committed generated code: `while one_result := self.apply__parse_rule(pos=pos):` (fltk_parser.py:134; `compile_while` at compiler.py:277-282 emits only `({var} := {expr})`). Exploration §1 carries the same wrong form.
- **Consequence:** An implementer writing the §5.4 emitted-source assertion (or the §5.1 subprocess expectations) against the quoted form — e.g. matching `is not None` in `ast.unparse` output — produces a test that can never pass and burns a debugging cycle during the mandated TDD-first phase. The §5.4 if/break assertion itself is unaffected.
- **Fix:** Correct the quoted loop to `while one_result := <consume>:`.

## design-2

- **Section:** §5.1, Rust hang test: "Cargo.toml with path deps on the in-repo `fltk-parser-core` and `fltk-cst-core` crates (no pyo3 — `python` feature off)".
- **What's wrong:** "Feature off" understates what is required. `fltk-cst-core`'s `python` feature is **default-on** (crates/fltk-cst-core/Cargo.toml: `default = ["python"]`), so merely not enabling it still links pyo3; the dep must be declared `default-features = false` (precedent: fltk-parser-core's own dependency, crates/fltk-parser-core/Cargo.toml). Also `fltk-parser-core` has no `python` feature at all (its manifest explicitly documents "No `python` feature").
- **Consequence:** A test crate written per the design's literal wording pulls pyo3 into a standalone binary build — at best a pointless pyo3 compile inflating the already-accepted per-session build cost, at worst a libpython link failure in the binary, blocking the mandatory pre-fix hang demonstration with a misleading error.
- **Fix:** Specify `fltk-cst-core = { path = ..., default-features = false }` in §5.1.

## design-3

- **Section:** §2.5: "every `+`/`*` loop in `fltk_parser.py`, `fltk_trivia_parser.py`, `unparsefmt_parser.py`, fixture `parser.rs`, fegen `parser.rs` gains one guard line."
- **What's wrong:** The enumeration is presented as the set of affected committed artifacts but is incomplete: `make gencode` (Makefile:148-180) also regenerates `bootstrap_parser.py`, `bootstrap_trivia_parser.py`, `toy_parser.py`, `toy_trivia_parser.py`, and `unparsefmt_trivia_parser.py`, whose repetition loops gain the same guard.
- **Consequence:** Diff-size expectations are understated; a scope reviewer comparing the actual regen diff against the design's list could flag the additional regenerated files as out-of-scope changes, or an implementer regenerating only the listed files leaves committed generated code stale, failing `make check`.
- **Fix:** Either enumerate all regenerated parser files or state the list is illustrative and `make gencode` output is authoritative.
