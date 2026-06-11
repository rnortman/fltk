# Scope review: Phase 2 — Rust Parser Generator

Commit reviewed: 261fa5e (base: 490bccf)
Implementation report: none (incremental log at implementation-log.md covers increments 1–3).

---

## scope-1: CLI tests for `gen-rust-parser` not present

**Location:** design §4 item 2 — "CLI tests (extend `fltk/fegen/test_genparser.py`): `gen-rust-parser` happy path writes the file; missing grammar file → exit 1; generation error → exit 1, no partial file."

**Expected:** `fltk/fegen/test_genparser.py` extended with at least three CLI-level tests for the new `gen-rust-parser` command.

**Actual:** `test_genparser.py` is not in the diff at all. Zero occurrences of `gen-rust-parser` or `gen_rust_parser` in that file. No CLI tests exist for the new command.

**Consequence:** The CLI contract (missing-file error, generation-error exit code, no-partial-file guarantee) is untested. A regression in error handling or partial-output suppression would ship silently.

**Suggested fix:** Add tests to `fltk/fegen/test_genparser.py` covering (a) happy-path write, (b) missing grammar file → exit 1, (c) generation error → exit 1 with no output file created, (d) invalid `--cst-mod-path` → exit 1 with no output file created.

---

## scope-2: `--cst-mod-path` validation test missing from Python unit tests

**Location:** design §4 item 1 — "Validation: invalid rule name / label rejected (via composed `RustCstGenerator`); invalid `--cst-mod-path` rejected."

**Expected:** A test in `test_gsm2parser_rs.py` (or `test_genparser.py`) that asserts an invalid `--cst-mod-path` raises an appropriate error (the CLI validates against `_CST_MOD_PATH_RE` in `genparser.py`, but the generator itself accepts any string; the validation is only at the CLI layer).

**Actual:** `test_gsm2parser_rs.py` contains `test_cst_mod_path_custom` and `test_cst_mod_path_non_cst_suffix` (valid path shapes) but no test asserting that an invalid path (e.g. `"not::valid::123"` or `"has spaces"`) is rejected. No such test exists in `test_genparser.py` either.

**Consequence:** The regex-gate `_CST_MOD_PATH_RE` in `genparser.py` is unexercised by the test suite; a typo in the regex would not be caught.

**Suggested fix:** Add a test in `test_genparser.py` (or as a CLI test per scope-1) that invokes `gen-rust-parser` with `--cst-mod-path "123bad"` and asserts exit code 1 with no output file.

---

## scope-3: Union-label append path untested in Python unit tests

**Location:** design §4 item 1 — "union-label append uses child enum" as a structural assertion on generated text.

**Expected:** A Python unit test in `test_gsm2parser_rs.py` that constructs a grammar with a label mapped to two different node types (a union label) and asserts the generated code contains `cst::<X>Child::<ClassName>(…)` rather than a bare `append_<lbl>` call.

**Actual:** The fixture grammar `rust_parser_fixture.fltkg` has `atom := num:num | name:name` (the `atom` label in `items`/`expr` rules is a union: `Num` or `Name`), but no Python-level unit test directly asserts the union-label code path. The Rust fixture tests parse `atom` successfully but do not inspect child enum variants (no `AtomChild::Num(…)` or `AtomChild::Name(…)` assertions). The design states §4 item 1 this structural assertion belongs in the Python generator unit tests.

**Consequence:** A generator regression on the union-label append path would not be caught at the Python level. The Rust compile step would catch it, but only after full fixture generation, which is slower feedback.

**Suggested fix:** Add a test in `test_gsm2parser_rs.py` asserting that a grammar with a union-typed label emits `cst::<X>Child::<ClassName>(itemN.result)` in the generated source.

---

## scope-4: `capture_trivia` on/off tree-delta test not present in Rust fixture tests

**Location:** design §4 item 3 — "capture_trivia on/off tree delta; Fixture tests assert the only tree difference between flag settings is the unlabeled `Trivia`/`Span` children."

**Expected:** A Rust test in `tests/rust_parser_fixture/src/native_tests.rs` that parses the same input twice (once `capture_trivia=false`, once `capture_trivia=true`), then asserts that labeled child accessors return identical results while `children()` (or equivalent) differs in the unlabeled trivia entries.

**Actual:** `test_capture_trivia_false` and `test_capture_trivia_true` both assert parse success and correct `pos`, but neither compares labeled vs. unlabeled children between the two modes. The tree-delta assertion from the design is absent.

**Consequence:** A bug that silently drops (or inserts) labeled children under `capture_trivia=true` would not be caught.

**Suggested fix:** Add a test that parses a grammar with a WS_ALLOWED separator (e.g. `stmt`) under both `capture_trivia` settings and asserts: (a) labeled children identical, (b) `capture_trivia=true` result has more total children (the trivia entries).

---

## scope-5: SUPPRESS-absent / INCLUDE-span-present child assertions missing from Rust fixture tests

**Location:** design §4 item 3 — "SUPPRESS absent from children / INCLUDE span present unlabeled."

**Expected:** A Rust test asserting that a suppressed item (e.g. `paren_expr`'s `"("` and `")"` literals) does not appear in children, and that a `$`-included item's span does appear as an unlabeled child.

**Actual:** `test_parse_paren_expr` and `test_parse_paren_expr_with_ws` assert parse success and `pos`, but do not inspect the node's children to verify suppressed literals are absent. No `$`-included item exists in the fixture grammar (all non-suppressed items have labels; `paren_expr`'s inner is labeled `inner`), so the "INCLUDE span present unlabeled" row of design §2.3 table is not covered by fixture tests.

**Consequence:** A generator bug that mistakenly appends suppressed items, or fails to emit unlabeled-INCLUDE appends, would go undetected.

**Suggested fix:** (a) Add assertions on `paren_expr` node children count with `capture_trivia=false` to confirm parens are absent. (b) Add a grammar rule with an explicitly `$`-included unlabeled item to the fixture and test that it appears as an unlabeled child.

---

## Bonus work (no finding, for awareness)

The implementation added `build-fegen-rust-parser`, `test-native-parser`, and `test-rust-parser-fixture` convenience Makefile targets (lines 107-115) not mentioned in design §2.7. These are low-risk ergonomic additions; no design concern.

`fltk/fegen/fegen.fltkg` `block_comment` regex was changed (implementation-log.md increment 1) to remove a lookahead unsupported by the `regex` crate. This is a valid necessary fix, called out in the log with a TODO. Not a scope deviation.
