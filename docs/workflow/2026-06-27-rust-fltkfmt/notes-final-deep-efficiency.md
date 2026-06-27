# Deep efficiency review — rust-fltkfmt

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2 (base 6f975ebf3e4e102c256397337a5d11a21cc1ab7f)
Scope: `crates/fltk-fmt-cli/`, `crates/fltkfmt/`, `crates/fegen-rust/src/unparser.rs` (generated),
`crates/fegen-rust/src/lib.rs`, `fltk/unparse/gsm2unparser_rs.py`, `tests/test_fltkfmt_parity.py`,
`tests/unparser_parity.py`, Makefile/Cargo wiring. EDTC workflow records excluded.

The hand-written CLI scaffolding is efficient: streams are locked once in `run_main`, each input is
read exactly once, `--in-place` skips the temp+rename when output == input, and the parity test caches
the heavy pure-Python parse/unparse (`@functools.cache` on `_py_doc`) so it runs once per input rather
than once per render config. The `gsm2unparser_rs.py` diff is clippy-cosmetic (`match` → `if let`) plus
TODO comments — performance-neutral. `children()` returns a borrowed slice and `text_str()` is a
borrowing accessor, so the generated code's repeated `node.children()` / span scans are cheap.

## efficiency-1 — Multi-file formatting is sequential (deliberate, low payoff)

`crates/fltk-fmt-cli/src/lib.rs:364` (`run_inner` `for source in sources`).
The CLI formats inputs one at a time. Each file's parse → unparse → resolve → render pipeline is
fully independent of every other file, so a multi-file run (e.g. a repo-wide format/`--check`) is
embarrassingly parallel.

Consequence: wall-clock for an N-file invocation is N × single-file time. This bites only on large
batches; for the actual workload (a handful of small `.fltkg` files, each ms-scale) the per-process
and I/O fixed costs dominate and the gain would be marginal.

Note: this is a conscious, documented design choice — design.md §3 ("Concurrency / Send") records that
`fltk_unparser_core::Doc` uses `Rc` internally so each pipeline must stay on one thread, and states
"The CLI is sequential per file; this is not a constraint for the binary. No threading is introduced."
A correct parallelization would run each file's *entire* pipeline (through the final `String`) on its
own worker thread and only send the resulting `String` back, preserving input order for stdout
concatenation via indexed buffering. Recorded for completeness; not an action item given the accepted
design and the tiny-file workload.

## Non-findings considered

- `fully_consumed` (`lib.rs:80`) decodes the whole suffix via `chars().skip(pos)` on the common
  fully-consumed path — O(n) once per file, dwarfed by the preceding parse/render. Not worth changing.
- Generated `unparser.rs` scans each `Trivia` node's children up to twice per node
  (`_has_preservable_trivia` + one of `unparse__trivia` / `_count_newlines_in_trivia`). This is
  pre-existing base-commit generator behavior (mirrored in the fixture unparser and required for
  Python parity), not introduced here; children are few and `children()` is slice-cheap, so the cost
  is negligible. Out of this diff's introduced-cost lane.
- Parity test (`test_fltkfmt_parity.py`) builds the binary once (session fixture) and runs 16
  subprocess invocations (8 corpus × 2 configs); inherent to exercising a CLI binary, Python side
  is cached. Fine.
</content>
</invoke>
