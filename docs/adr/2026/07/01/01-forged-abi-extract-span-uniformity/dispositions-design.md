# Dispositions: design review round 1 (`forged-abi-extract-span-uniformity`)

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (this directory).
All three findings fact-checked against source at `c03a801` and confirmed accurate.

design-1:
- Disposition: Fixed
- Action: Design header line 4 now declares `Base commit: c03a801` with a parenthetical
  explaining the exploration's `TODO.md:37-44` cite maps to `TODO.md:15-22` after the
  intervening TODO-cleanup commit. Also corrected the one mixed-coordinate cite the
  reviewer identified: §2.1 `span.rs:290` → `span.rs:287` (verified: the
  `#[cfg_attr(... pyclass(frozen, eq, hash, from_py_object))]` attribute is at
  `crates/fltk-cst-core/src/span.rs:287` at `c03a801`).
- Severity assessment: Provenance/bookkeeping hazard only — an implementer branching from
  the declared `8fd5ecf` would find wrong TODO.md line cites and could resurrect
  already-deleted TODO entries on merge. No design logic depended on it. Verified: at
  `c03a801` the target entry is at `TODO.md:15-22`; at `8fd5ecf` it is at `TODO.md:37-44`;
  actual HEAD is `c03a801`.

design-2:
- Disposition: Fixed
- Action: §4 test (c) rewritten. It is now a subprocess test (`_run_script`) using
  `fegen_rust_cst` + a genuine `fltk._native.Span`, so a fresh interpreter guarantees
  `get_span_type`'s `PyOnceLock` init — and therefore the new `check_instance_layout`
  accept branch — provably executes inside (c) itself. The bullet records why in-process
  would silently degrade to a cache-hit test (earlier boundary-crossing tests such as
  `TestSpanToPyobjectCaching.test_repeated_span_reads_from_consumer_cdylib`,
  `tests/test_rust_span.py:772-780`, populate the consumer cdylib's cache first). Chose
  the reviewer's first suggested option (subprocess) over the docstring-disclaimer option
  because it makes the test's named property (gate accepts genuine type at first init)
  actually order-independent rather than merely documented as order-dependent; dropping
  the phase4 dependency also removes an `importorskip` from the core accept test.
- Severity assessment: Without the fix, no-false-rejection coverage still existed in
  aggregate (subprocess `test_control_no_patch_passes` plus every earlier span read), but
  test (c)'s stated purpose was order-dependent: a future false-rejection regression would
  have surfaced in unrelated-looking tests rather than the test named for it. Verified:
  `test_repeated_span_reads_from_consumer_cdylib` (`tests/test_rust_span.py:770-780`)
  crosses the consumer-cdylib span boundary before a later in-file (c) would.

design-3:
- Disposition: Fixed
- Action: §4 gate list now includes `make check`, naming the Rust lanes it adds
  (`cargo-clippy`, `cargo-test`, `cargo-test-python-features`, `cargo-test-no-python`,
  `cargo-clippy-no-python`, `check-no-pyo3`) and noting they cover the edited
  `cross_cdylib.rs`/`span.rs` including the `--no-default-features` compile.
- Severity assessment: Omission would have deferred discovery of a clippy lint on the new
  call/rewritten doc comments (or a no-default-features compile break) from the implement
  step to precommit, costing a second revision cycle. Verified: `Makefile:40` lists
  exactly those steps in `check-common`, and CLAUDE.md names `make check` as the
  precommit gate.
