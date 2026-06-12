## Increment 5 — regen committed generated parsers + TODO bookkeeping (design §2.5, commit 1c1c386)

- `make gencode`: regenerated all 8 committed Python parsers + 2 Rust parser.rs files — every +/* loop gained the guard line.
- `TODO.md`: removed `nullable-loop` entry (code comment was deleted in increment 4; this closes the tracking entry).
- `tests/test_nullable_loop_guard.py`: fixed lint issues (PLC0415, F401, ARG005, RUF002, N806, S607) to pass `make check`.
- `make check`: all steps passed (lint, format-check, typecheck, test, cargo-check, cargo-clippy, cargo-test, cargo-test-no-python, cargo-clippy-no-python, check-no-pyo3).

## Increment 4 — Rust backend per-iteration progress guard (design §2.2, commit 40b7c22)

- `fltk/fegen/gsm2parser_rs.py:699-707`: deleted `TODO(nullable-loop)` comment block; added guard comment + `lines.append("            if one_result.pos == pos { break; }")` before the `pos = one_result.pos;` line.
- `TestRustGuardPlacement` (3 tests): all pass.
- `test_rust_backend_guard`: passes (cargo build + run, guard terminates the loop).
- Full suite (1329 tests): green.

## Increment 3 — Python backend per-iteration progress guard (design §2.3, commit 7fcf341)

- `fltk/iir/model.py:199-202`: added `Block.break_()` helper after `Block.return_()`.
- `fltk/fegen/gsm2parser.py:564-573`: inserted guard before `loop.block.assign(...)` — looks up `one_result` in the loop scope, inserts `if_(Equals(one_result.pos, pos)).block.break_()`.
- `TestPythonGuardPlacement` (2 tests): both pass.
- `test_python_backend_guard` and `test_cross_backend_parity`: both pass.
- Full suite (1309 tests): green.

## Increment 2 — fix Item.can_be_nil to be term-aware (design §2.1, commit d0ee832)

- `fltk/fegen/gsm.py:108-111`: replaced `return self.quantifier.is_optional()` with `return self.quantifier.is_optional() or term_can_be_nil(self.term, grammar)`; removed `# noqa: ARG002`.
- `fltk/fegen/test_nil_validation.py:172-206`: updated two assertions in `test_item_nil_detection_with_quantifiers` that encoded the old buggy behavior (REQUIRED+empty-literal now True, ONE_OR_MORE+empty-literal now True).
- `tests/test_nullable_loop_guard.py::TestValidatorGap` (8 tests): all pass — validator gap confirmed closed.
- `tests/test_nullable_loop_guard.py::TestGeneratorRejection` (2 tests): both pass — both generators reject trigger grammar.
- `fltk/fegen/test_nil_validation.py` full suite: all pass.

## Increment 1 — failing tests for hang demonstration + validator gap (TDD first step, commit 7811133)

- `tests/test_nullable_loop_guard.py`: new file, 20 tests total.
- `test_python_backend_guard`: subprocess test; monkeypatches `validate_no_repeated_nil_items`, calls `generate_parser`, runs `apply__parse_rule("aab")` and `apply__parse_rule("b")`; 30s timeout → `TimeoutExpired` pre-fix (hang confirmed, §5.1 Python backend).
- `test_rust_backend_guard`: cargo-build + run with tmp-dir crate referencing `fltk-cst-core` (`default-features=false`) and `fltk-parser-core`; 10s run timeout → hang expected pre-fix.
- `test_cross_backend_parity`: in-process parity check (Python backend, validator bypassed); post-fix only.
- `TestValidatorGap` (6 tests): unit assertions on `Item.can_be_nil` (term-aware) + `validate_no_repeated_nil_items` for 3 trigger-grammar variants (regex, empty literal, nil rule ref). All fail pre-fix.
- `TestItemNilDetectionUpdated` (2 tests): updated assertions for REQUIRED+empty-literal and ONE_OR_MORE+empty-literal. Fail pre-fix (old test_nil_validation.py encodes the bug).
- `TestGeneratorRejection` (2 tests): `generate_parser` and `RustParserGenerator.__init__` reject trigger grammar. Fail pre-fix.
- `TestRustGuardPlacement` (3 tests): Rust source-text assertions for guard line placement and TODO removal. 2 fail pre-fix (guard absent), 1 passes vacuously (TODO never in generated output).
- `TestPythonGuardPlacement` (2 tests): `ast.unparse` assertions for guard before pos-update. Both fail pre-fix.
- Deviation: subprocess script uses `generate_parser` from `fltk.plumbing` (not manual IIR assembly) for cleaner isolation; semantics identical.
