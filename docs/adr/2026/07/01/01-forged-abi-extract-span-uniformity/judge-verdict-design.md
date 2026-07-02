# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/01/01-forged-abi-extract-span-uniformity/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings. Dispositions: `dispositions-design.md`.

## Findings walk

### design-1 — Fixed
Claim: declared base commit `8fd5ecf` inconsistent with the design's own citations (which match `c03a801`); consequence is an implementer branching from the wrong base finding wrong `TODO.md` cites and risking resurrection of already-deleted TODO entries on merge.
Design as written: header line 4 declares `Base commit: c03a801` with a parenthetical mapping the exploration's `TODO.md:37-44` (at `8fd5ecf`) to `TODO.md:15-22` here. §2.1 now cites `span.rs:287` (the previously mixed-coordinate cite).
Independent verification: repo HEAD is `c03a801`; `git show c03a801:TODO.md` lines 15-22 are exactly the `forged-abi-extract-span-uniformity` entry; `git show 8fd5ecf:TODO.md` lines 37-44 are the same entry at the old base; the `#[cfg_attr(... pyclass(frozen, eq, hash, from_py_object))]` attribute sits at `crates/fltk-cst-core/src/span.rs:287` at `c03a801`, with no `subclass` flag.
Assessment: fix addresses the consequence at the named lines; the provenance hazard is closed and the parenthetical preserves the exploration cross-reference. Accept.

### design-2 — Fixed
Claim: §4 test (c), as an in-process test, is not guaranteed to exercise the new `check_instance_layout` accept branch — earlier boundary-crossing tests populate `get_span_type`'s `PyOnceLock` first, silently degrading (c) to a cache-hit test; consequence is a future false-rejection regression surfacing in unrelated-looking tests rather than the test named for it.
Design as written: §4 test (c) is now explicitly **subprocess** (`_run_script`) so a fresh interpreter guarantees `PyOnceLock` init — and thus the gate's accept branch — executes inside (c) itself; the bullet records the in-process degradation mechanism, naming `TestSpanToPyobjectCaching.test_repeated_span_reads_from_consumer_cdylib` (`tests/test_rust_span.py:772-780`) as a cache-populating predecessor.
Independent verification: `_run_script` subprocess helper exists at `tests/test_rust_span.py:17-25`; `test_repeated_span_reads_from_consumer_cdylib` is at line 772 and crosses the consumer-cdylib span boundary (`node.span` reads) as cited.
Assessment: responder took the reviewer's first suggested option (subprocess) with a sound rationale for preferring it over the docstring-disclaimer option (order-independence vs. documented order-dependence). Fix addresses the consequence directly. Accept.

### design-3 — Fixed
Claim: gate list omitted the Rust lint/test lanes enforced by the precommit gate (`make check`); consequence is a clippy lint or `--no-default-features` compile break discovered at precommit instead of during implement, costing a second revision cycle.
Design as written: §4 gates now end with `make check`, enumerating the Rust lanes (`cargo-clippy`, `cargo-test`, `cargo-test-python-features`, `cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3`; `Makefile:40`) and noting they cover the edited `cross_cdylib.rs`/`span.rs` including the no-default-features compile.
Independent verification: `Makefile` `check-common` step list contains exactly those steps (plus the Python lanes), and `check` inherits via `check-ci` → `check-common`; CLAUDE.md names `make check` as the precommit gate.
Assessment: fix matches the suggested remedy and the enumerated lanes match the Makefile. Accept.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED

All three dispositions are Fixed and each fix is verified in the design text against source at `c03a801`. No disputed items.
