# Efficiency review — nullable-loop guard

Reviewed: 61f9384..6ac52d5 (HEAD 6ac52d5). Style: concise, precise, complete, unambiguous.

Runtime cost of the fix itself is sound: one integer compare per repetition iteration in both backends, unavoidable for the guard semantics. Validator change runs only at generation time and rides existing `_can_be_nil` memoization. No findings against the production code paths.

## efficiency-1: cargo test crate rebuilds all deps cold every pytest session

`tests/test_nullable_loop_guard.py:364-394` (`test_rust_backend_guard`). The throwaway crate is created under `tmp_path` with no `CARGO_TARGET_DIR`, so its `target/` is unique per run. Every pytest session therefore cold-compiles `fltk-cst-core`, `fltk-parser-core`, and — dominating the cost — `regex-automata` with full default features (dfa-build/dfa-search; flagged as compile-heavy in `crates/fltk-parser-core/Cargo.toml` under `TODO(regex-automata-features)`).

**Consequence:** tens of seconds of redundant compilation added to every full-suite run (and every CI job) that has cargo on PATH — the design's "one small debug cargo build per test session" understates it because nothing is ever reused; the 300 s timeout exists precisely to absorb this. Cost recurs forever, scales with regex-automata compile time.

**Fix:** pass `env={**os.environ, "CARGO_TARGET_DIR": str(<persistent cache dir>)}` to the `cargo build` call — e.g. `_repo_root / "target" / "nullable-loop-guard-test"` (repo `target/` is already gitignored). Generated `parser.rs`/`cst.rs`/`main.rs` still recompile fresh each run (they're the artifact under test); only dep compilation is reused. Adjust the binary path to the shared target dir.

## efficiency-2: duplicate Python-backend generation — "parity" test repeats the subprocess test's work

`tests/test_nullable_loop_guard.py:241-261` (`test_python_backend_guard`) and `:416-444` (`test_cross_backend_parity`) both build the same trigger grammar, bypass the validator, run full `generate_parser` (IIR codegen + compile + exec), and assert the identical outcomes (`"aab"` → pos 2, `"b"` → None). The parity test consults no Rust output — it cannot detect a cross-backend divergence; the Rust expectations live only as constants inside `_RUST_MAIN_RS`.

**Consequence:** one redundant end-to-end parser generation + exec per session, plus the subprocess test's own generation — pure duplicate work with no added coverage. Bites on every test run; small now, but it's the pattern that accretes.

**Fix:** either delete `test_cross_backend_parity` (its assertions are a strict subset of the subprocess test's) or make it earn its name: have `test_rust_backend_guard` record its observed outcomes (e.g. via a module-scoped fixture or parsed stdout) and compare those against the Python outcomes instead of regenerating the Python parser.

Reviewed commit: 6ac52d5.
