Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: af7dc6e

---

test-1
File: tests/test_fegen_rust_cst.py:102-106
`test_label_variant_accessible` asserts `variant is not None`. Every Python object satisfies `x is not None` unless it literally is `None`; a missing attribute would raise `AttributeError` before the assert, and a wrong-type return would still pass. The only load-bearing assertion is `repr(variant) == ...`. The `is not None` guard is vacuous — it adds no coverage and misleads readers into thinking there is a meaningful null-check.
Consequence: a bug where `getattr(label_enum, variant_name)` returns an unrelated Python object would pass this assertion silently as long as it has the right repr.
Fix: drop the `assert variant is not None` line; the repr assertion already guarantees a real value was returned.

test-2
File: tests/test_fegen_rust_cst.py:50-52
`test_class_is_type` asserts `isinstance(cls, type)`. The test is exercised only because `cls` is already imported at module load time (lines 6011-6025). The `isinstance(cls, type)` check would pass for any imported Python class, including a misimported one. The import success itself (or `ImportError`) is the real AC-7 check; the body assertion adds nothing.
Consequence: a class accidentally aliased to another type still passes. The test name "all classes importable" is accurate but the assertion body is weaker than the claim requires.
Fix: either remove the body and use `@pytest.mark.smoke` to signal import-only validation, or assert something class-specific (e.g., that constructing `cls()` succeeds without raising).

test-3
File: tests/test_gsm2tree_rs.py:521-531 (TestDeterministicOutput)
Both determinism tests call `generate()` on the same in-memory grammar and check string equality. This correctly tests determinism across calls. However, neither test involves any non-deterministic source (e.g., dict iteration order from a grammar loaded from `fegen.fltkg`). The fegen fixture uses `scope="module"` and generates once; a determinism test over the fegen grammar would expose ordering bugs that the PoC grammar (only two rules) cannot trigger.
Consequence: a label ordering bug in a multi-label fegen rule (e.g., `Item` has many labels) would not be caught by the determinism test — it would only be caught if two separately generated strings were compared, which no test currently does.
Fix: add a test that instantiates two separate `RustCstGenerator` instances from the fegen grammar and asserts their outputs are equal, or reuse the `fegen_source` fixture in a dedicated determinism test for fegen.

test-4
File: tests/test_gsm2tree_rs.py:489-495 (TestMinimalGrammar.test_minimal_grammar_does_not_crash)
`assert source` tests that the output is non-empty but asserts nothing about what the output contains — labeled "does not crash" which is honest, but the three sibling tests (`test_minimal_grammar_produces_numbers_class`, `test_minimal_grammar_produces_numbers_label`, `test_minimal_grammar_has_preamble`) each reconstruct the grammar from scratch instead of using a shared fixture, making four separate generator invocations for the same grammar. This is redundant without shared state: the sibling tests already confirm "non-empty and meaningful content," making the smoke test redundant.
Consequence: no behavior is unverified, but the duplication slows the suite without benefit, and future modifications to `_make_minimal_grammar` must be propagated to four independent calls.
Fix: consolidate into a `minimal_source` module-scoped fixture (same pattern as `poc_source`) and drop the standalone crash test — its only assertion (`assert source`) is subsumed by the other three.

test-5
File: tests/test_gsm2tree_rs.py:378-381 (TestPocGrammarLabels)
`test_allow_non_camel_case_types` and `test_derive_clone_partialeq_eq_hash` both assert `count >= 2` (one per label enum). The PoC grammar has two label-bearing rules (`Identifier`, `Items`) plus auto-inserted `Trivia`, so the count is 3. The `>= 2` threshold would still pass if one enum were accidentally dropped (count = 2 with three expected). Using `>= 2` instead of `>= 3` makes the test silently accept a regression where Trivia's enum is missing.
Consequence: if the `_trivia` rule stops generating a label enum (regression in OQ-empty-label-enum handling or in `add_trivia_rule_to_grammar`), this test will not catch it.
Fix: assert `count >= 3` to match the actual number of label-bearing rules in the PoC grammar, or assert exact equality (`== 3`) with a comment explaining the grammar has 3 label-bearing rules.

test-6
File: tests/test_fegen_rust_cst.py (no test for `extend_{label}` / `maybe_{label}`)
The fegen smoke tests cover `append_{label}` + `child_{label}` + `children_{label}` round-trips but have no test for `extend_{label}` or `maybe_{label}` on any fegen class. These are exercised for the PoC classes in `test_rust_cst_poc.py`, but the fegen classes are separate compiled objects. A code-generation bug affecting only `extend_*` or `maybe_*` for fegen classes would not be caught by the smoke tests.
Consequence: a generator bug in `_per_label_methods` that corrupts `extend_{label}` or `maybe_{label}` bodies goes undetected for the 14 fegen classes.
Fix: add a parameterized test in `test_fegen_rust_cst.py` for `extend_{label}` (append two children via extend, verify count) and one for `maybe_{label}` (returns `None` on empty, returns child on one match, raises on two matches). This does not need to cover all 14 labels exhaustively — one representative per method is sufficient.

test-7
File: tests/test_gsm2tree_rs.py:553-560 (TestEmptyLabelEnumOmitted.test_zero_label_rule_omits_label_classattr)
The test extracts `impl Token {` ... `\n}` using `source.index()` and `source.index("\n}", impl_start)`. The `\n}` pattern will match the first closing `}` on its own line after `impl Token {`, which is correct for this specific generated structure. However, if the Trivia rule (auto-inserted after Token) generates its `impl` block and happens to be formatted differently, the `\n}` could match an inner closing brace rather than the end of the `impl Token` block, producing a truncated slice that falsely excludes `fn Label(`. This is fragile parsing of generated text.
Consequence: the test may false-pass if the brace-matching silently truncates the extracted block before `fn Label(` would have appeared.
Fix: either use a regex that captures everything between `impl Token {` and the next `^}` at column 0 (`re.search(r'impl Token \{(.+?)\n\}', source, re.DOTALL)`), or assert more directly that `Token_Label` does not appear anywhere in the source (already done by `test_zero_label_rule_omits_label_enum`) and that the Token struct is present, removing the need for block-extraction entirely.
