# Phase 3 Implementation Log

## Increment 1 — `gsm2tree_rs.py`: complete `RustCstGenerator` (commit c872b1c)

- `fltk/fegen/gsm2tree_rs.py`: new module with `RustCstGenerator` class and two module-level helpers (`_rust_variant_name`, `_python_label_name`).
- `__init__`: applies `add_trivia_rule_to_grammar` + `classify_trivia_rules`, instantiates `CstGenerator` with `py_module=pyreg.Builtins` to get `rule_models`.
- `generate()`: emits preamble, per-rule label enum + `#[pymethods]` + node struct + `#[pymethods]`, then `pub fn register_classes`.
- Label enums omitted for zero-label rules (Rust cannot have zero-variant enums); `#[classattr] Label` also omitted in that case.
- Sanity-checked against PoC grammar: produces `Identifier_Label` (NAME), `Items_Label` (ITEM, NO_WS, WS_ALLOWED, WS_REQUIRED), `Trivia_Label` (CONTENT), all `register_classes` calls; total 32201 chars.
- `uv run pytest`: 501 passed, no regressions.
- Deviation: shipped the complete generator (not just skeleton + label enum) as one atomic change; the full node struct + per-label methods follow the same pattern and splitting would have left a non-compilable intermediate.

## Increment 2 — generate `src/cst_generated.rs` for PoC grammar, delete `src/cst_poc.rs` (commit 7b08f18)

- `src/cst_generated.rs`: generated from the programmatic PoC grammar (identifier + items rules) via `RustCstGenerator`; produces `Identifier`, `Items`, `Trivia` classes with all expected labels.
- `src/lib.rs`: replaced `mod cst_poc;` + direct `add_class` calls with `mod cst_generated;` and `cst_generated::register_classes(m)?`.
- `src/cst_poc.rs`: deleted (AC-2 satisfied).
- All 48 tests in `tests/test_rust_cst_poc.py` pass; 501 total, no regressions (AC-1, AC-6, AC-12).

## Increment 3 — `tests/test_gsm2tree_rs.py`: generator unit tests (commit bdda28c)

- `tests/test_gsm2tree_rs.py`: 36 tests across 7 test classes covering all design test plan items.
- `_make_poc_grammar()`: programmatic 2-rule PoC grammar (identifier + items) used as the primary fixture.
- `_make_minimal_grammar()`: single-rule `numbers := digits+` grammar (AC-9).
- `_make_zero_label_grammar()`: single unlabeled-item rule to validate empty-label-enum omission (OQ-empty-label-enum).
- `TestPreamble`: preamble content + placement (AC-10).
- `TestPocGrammarLabels`: label enum variants, pyclass name, repr strings, derive/allow attrs (AC-1 precondition).
- `TestNodeStructure`: struct fields, classattr Label.
- `TestRegisterClasses`: function present, all add_class calls, label-before-struct order, Ok(()) (AC-5).
- `TestFegenGrammar`: all 14 fegen class names + register calls in generated source (AC-7 precondition).
- `TestMinimalGrammar`: no crash, correct class/label names, preamble (AC-9).
- `TestDeterministicOutput`: same-instance and different-instance determinism.
- `TestEmptyLabelEnumOmitted`: Token_Label absent, Token struct present, Label fn absent from Token impl block, no enum registration.
- Deviation: `test_zero_label_rule_omits_label_classattr` checks inside `impl Token {}` block rather than the whole file (the _trivia rule auto-added by the generator has labels, so `fn Label` appears elsewhere in the file).
- 537 tests total, all pass.

## Increment 4 — generate `src/cst_fegen.rs`, wire fegen submodule in `lib.rs`, add `tests/test_fegen_rust_cst.py` smoke tests (commit d22f3a7)

- `src/cst_fegen.rs`: generated from `fegen.fltkg` (14 classes: Grammar, Rule, Alternatives, Items, Item, Term, Disposition, Quantifier, Identifier, RawString, Literal, Trivia, LineComment, BlockComment); 164344 chars.
- `src/lib.rs`: added `mod cst_fegen;`, created `fegen_cst` submodule via `PyModule::new`, called `cst_fegen::register_classes(&fegen_sub)?`, inserted into `sys.modules["fltk._native.fegen_cst"]` for `from fltk._native.fegen_cst import X` support (AC-7).
- `tests/test_fegen_rust_cst.py`: 98 smoke tests across 5 test classes (TestAllClassesImportable, TestConstructionDefaultSpan, TestChildrenIsList, TestLabelAccess, TestAppendChildRoundtrip); parameterized over all 14 classes with one representative label per class (AC-8).
- Deviation: span tests use `node.span == UnknownSpan` (equality) rather than `.start`/`.end` attributes; the Python `Span` type does not expose start/end as Python-accessible attributes (validated by examining test_rust_cst_poc.py's TestSpanField pattern).
- 635 tests total, all pass (AC-12).
