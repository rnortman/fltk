## Increment 4 — fixture grammar nest/nest_sum rules + parity corpus + T5/T6 binding tests + TODO cleanup (commit ac48b11)

- `fltk/fegen/test_data/rust_parser_fixture.fltkg`: appended `nest` (right-recursive) and `nest_sum` (left-recursive growth-step) rules (§5).
- `tests/rust_parser_fixture/src/cst.rs` + `parser.rs`: regenerated; `make fix` + `make check` clean; 1300 pytest + all cargo tests pass.
- `tests/test_rust_parser_parity_fixture.py`: 6 new corpus entries (nest×3 SUCCESS, nest_sum×3 SUCCESS) → 12 new parametrized parity tests.
- `tests/test_rust_parser_fixture_bindings.py` (new): T5 (small limit raises RecursionError, larger limit succeeds, nest_sum flag-outranks-Some, getters, spent-instance) + T6 (default limit fires before native overflow on depth = DEFAULT_MAX_DEPTH + 100); 8 tests total; own `importorskip("rust_parser_fixture")` guard.
  - Deviation: `fltk_parser_core` is a Rust crate, not a Python module; `DEFAULT_MAX_DEPTH` is read via `Parser("0").max_depth` helper instead of import.
- `TODO.md`: removed `apply-depth-limit` and `parser-depth-limit` entries.
- `fltk/fegen/test_gsm2parser_rs.py:213`: added `set_max_depth`, `max_depth`, `depth_exceeded` to `_EXPECTED_NON_APPLY_PUB_FNS` (allowlist gap from increment 3).

## Increment 2 — T1-T4 cargo depth tests in memo_toy.rs (commit 349c3e7)

- `crates/fltk-parser-core/tests/memo_toy.rs`: added `DepthParser` struct with `nest` (right-recursive, depth ∝ nesting) and `nest_sum` (left-recursive, growth step calls `nest`) toy rules.
- T1 (`test_depth_limit_t1_basic`): input nested 3 deep with max_depth=2 → `None` + flag true; same input with max_depth=10 → `Some(pos=7)` + flag false.
- T2 (`test_depth_limit_t2_unwind`): two sibling `(1)` parses at max_depth=4 both succeed, proving counter decrements between them.
- T3 (`test_depth_limit_t3_sticky`): after overflow, trivial subsequent `apply` returns `None` with flag still set.
- T4 (`test_depth_limit_t4_some_with_flag`): `nest_sum` on `1+(((9)))` with max_depth=4 returns `Some(pos=1)` (seed) with flag set, pinning the §2 truncated-Some premise.
- All 12 cargo tests (8 existing + 4 new) pass.

## Increment 3 — gsm2parser_rs.py depth-limit surface (commit 31d60f2)

- `fltk/fegen/gsm2parser_rs.py`:
  - `_gen_header` (§7): replaced stale hazard warning + `TODO(parser-depth-limit)` with bounded-depth description.
  - `_gen_parser_struct` (§3): added `set_max_depth`, `max_depth`, `depth_exceeded` methods with contract doc comments (file:line 388-399).
  - `_gen_python_bindings` (§4 + §7):
    - `PyRecursionError` imported alongside `PyValueError`.
    - `#[pyo3(signature)]` gains optional `max_depth: Option<u32>` kwarg; `Some(d)` → `inner.set_max_depth(d)`.
    - `max_depth` and `depth_exceeded` getters added to `PyParser`.
    - PyParser doc updated (§7).
    - Per-rule `apply__parse_X` methods: capture result, check `depth_exceeded()`, raise `PyRecursionError` if set, then match result — enforces flag-outranks-result (§2, §4).
- `tests/rust_parser_fixture/src/parser.rs`, `tests/rust_cst_fegen/src/parser.rs`: regenerated; both carry the new surface + flag-check in per-rule binding methods.
- All 44 `rust_parser_fixture` cargo tests, 7 `rust_cst_fegen` cargo tests, and 830 pytest tests pass.

## Increment 1 — PackratState depth fields + apply guard (commit d402973)

- `crates/fltk-parser-core/Cargo.toml`: bumped version `0.1.0` → `0.2.0` (semver-breaking per design §2 Versioning).
- `crates/fltk-parser-core/src/memo.rs`:
  - Added `DEFAULT_MAX_DEPTH: u32 = 1000` (public const).
  - `PackratState`: added `pub max_depth: u32`, private `depth: u32`, private `depth_exceeded: bool`; dropped `#[derive(Default)]`; manual `Default` impl sets `max_depth = DEFAULT_MAX_DEPTH`, others to zero/false.
  - Added `PackratState::depth_exceeded(&self) -> bool` accessor with §2 contract doc.
  - Renamed old `apply` body to `apply_inner` (private, signature unchanged except name).
  - New `apply`: thin guard — checks `depth_exceeded || depth >= max_depth` (sets flag, returns `None`), increments `depth`, calls `apply_inner`, decrements `depth`; doc rewritten to describe limit and lockstep-regeneration note; `TODO(apply-depth-limit)` removed.
- `crates/fltk-parser-core/src/lib.rs`: re-exports `DEFAULT_MAX_DEPTH`.
- All 55 existing cargo tests pass.
