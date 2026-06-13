# Deep correctness review — pyo3 0.23 → 0.29 upgrade

Commit reviewed: 6df2369 (base 2919733). Design: docs/designs/pyo3-upgrade/design.md.

Style note (applies to this doc): concise, precise, complete, unambiguous; audience is a smart
LLM/human.

Verified clean (no findings): mechanical B/D/F migrations in `crates/fltk-cst-core/src/{span,registry,cross_cdylib}.rs`, `src/lib.rs`, both generators, and all tier-3 regenerated files (diffed changed lines after filtering mechanical patterns — only `PyObject`→`Py<PyAny>`, `downcast*`→`cast*`, `GILOnceCell`→`PyOnceLock`, `from_py_object` additions, and one append-signature line wrap remain); class-A probe rewrite (`<T as PyClassImpl>::Layout` at all four sites, consistent on both compare sides of `check_abi_pair`); `span_to_pyobject` arm-type changes (workspace `cargo check --all-features` green, run during review); fltk-cst-core 0.2.0 + pyo3 0.29.0 present in all four lockfiles (so the `FLTK_CST_CORE_ABI` string marker changes as designed); committed `src/cst_generated.rs` is byte-identical to fresh generator output and `crates/fltk-cst-spike/src/cst.rs` is byte-identical to it (regenerated to /tmp during review); `fegen_cst.pyi` untouched; no stale `PyObject`/`downcast`/`GILOnceCell` code tokens remain (doc-comment mentions only); no leftover `TODO(pyo3-upgrade)` markers outside `.claude/worktrees`.

## correctness-1 — new ABI-probe guard tests are never compiled or run by any `make check` lane

- File: `crates/fltk-cst-core/src/lib.rs:21-47` (new `abi_probe_tests` module, `#[cfg(all(test, feature = "python"))]`); `Makefile:46-47` (`cargo-test`), `Makefile:58-63` (`cargo-test-no-python`).
- What's wrong: the only test lanes are `make cargo-test` = `cargo test -q` at the repo root — which, because the root manifest is a package (not a virtual workspace), tests only the `fltk-native` package, a cdylib with zero test targets (observed during review: output is a single `running 0 tests`) — and `make cargo-test-no-python` = `cargo test -p fltk-cst-core --no-default-features`, which compiles the module out (`python` feature off). No clippy lane passes `--all-targets`, so the module is not even type-checked by the gate.
- Why: traced every `cargo test`/`cargo clippy` invocation in the Makefile; none reaches `fltk-cst-core` with the `python` feature and `--test` targets. The implementation log (increment 2) concedes only the no-default-features run executed ("python-feature tests require maturin (step 7)") — but step 7 is pytest, which never runs Rust unit tests. Additionally, on this dev box `cargo test -p fltk-cst-core --features python` fails at link (`unable to find library -lpython3.10`; only the versioned `libpython3.10.so.1.0` exists), so the tests have never executed anywhere in this branch's history.
- Consequence: the design's §2.A/§5 stub-regression guard ("kills constant-stub shortcuts", "prevents the scout's known-wrong `0usize` stub") provides zero protection: a future probe stub, or bit-rot of the test module itself, passes full `make check`. The §3 step-2 checkpoint "`cargo test -p fltk-cst-core` green" is unmet for the feature lane the tests live in.
- Note: the tests themselves are correct — when forced to link during this review (symlinked `libpython3.10.so` onto the linker path), both pass.
- Suggested fix: add `cargo test -q -p fltk-cst-core` (default features = python) to the `cargo-test` make target, and document/handle the libpython link requirement (e.g. `PYO3_PYTHON` + a `-L` from `sysconfig LIBDIR`, or require python3.10 dev libs); at minimum add `--all-targets` to a clippy lane so the module cannot silently stop compiling.

## correctness-2 — guard test asserts on a recomputed expression, not the probe it claims to guard

- File: `crates/fltk-cst-core/src/lib.rs:28,38` vs. `crates/fltk-cst-core/src/span.rs` (`_fltk_cst_core_abi_layout` classattrs) and `crates/fltk-cst-core/src/cross_cdylib.rs:199-200` (`check_abi_pair` step 4).
- What's wrong: the test computes `size_of::<<T as PyClassImpl>::Layout>()` itself and checks it against the floor. The actual probe values consumed at runtime are the bodies of the `_fltk_cst_core_abi_layout()` classattr fns and `check_abi_pair`'s `expected_layout`. The test never reads any of them.
- Why: the module doc (`lib.rs:23-26`) claims "the probe value exposed via `_fltk_cst_core_abi_layout` is >= ..." and design §5 specifies the test must assert the floor **and** equality with "the value the `_fltk_cst_core_abi_layout` classattr exposes (guards probe realism; kills constant-stub shortcuts)". The equality half was dropped — likely because the classattr fns are private to the `span` module and unreachable from `lib.rs` Rust code.
- Consequence: the exact failure mode the test exists to kill — replacing a classattr body (or `check_abi_pair`'s `expected_layout`) with a constant — passes the test, because the test's recomputed expression is correct by construction and independent of the probe sites. Combined with correctness-1, the probe currently has no effective regression guard at all.
- Suggested fix: make the two classattr fns `pub(crate)` and assert `Span::_fltk_cst_core_abi_layout() == size_of::<<Span as PyClassImpl>::Layout>()` (likewise SourceText) in addition to the floor check; or fetch the attr via `Span::type_object(py).getattr("_fltk_cst_core_abi_layout")` under an initialized interpreter.

## correctness-3 — `span: PyObject` negative assertions are vacuous after the spelling migration

- File: `tests/test_gsm2tree_rs.py:321` and `:925` (class `TestNoPyObjectAudit`).
- What's wrong: both assert `"span: PyObject," not in poc_source`. After class B, the generator's type spelling is `Py<PyAny>`; the regression these tests guard against ("§4 item 2: no generated node struct has a PyObject span field") would now manifest as `span: Py<PyAny>,`, which the assertions do not match.
- Why: these lines were left untouched while every positive `PyObject` assertion in the same file was migrated to `Py<PyAny>` (diff hunks at lines 238-331); the negative assertions silently became tautologies — `PyObject` can no longer appear in generator output under any code path (verified: zero `PyObject` tokens in the generators).
- Consequence: a future generator change reintroducing a Python-object span field on node structs passes both audit tests; the §2.2/§4 invariant (span stored as native `Span`, wrapped out via `span_to_pyobject`) loses its test enforcement.
- Suggested fix: assert `"span: Py<PyAny>," not in poc_source` (keep or drop the old spelling alongside).
