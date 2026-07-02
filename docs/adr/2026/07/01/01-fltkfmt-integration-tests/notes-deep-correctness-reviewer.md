# Deep correctness review — fltkfmt integration tests

Commit reviewed: 2728a78246ccadcb6c34b1430188603ef82bcf28 (base 9233540d)

No findings.

Verification performed (all clean):
- Ran `cargo test -q --manifest-path crates/fltkfmt/Cargo.toml`: 4/4 integration tests pass against the current binary.
- `run()` subprocess helper: no pipe deadlock — the binary (`run_inner`, `crates/fltk-fmt-cli/src/lib.rs`) drains stdin to EOF via `read_to_string` before producing any stdout, and the parent closes stdin before `wait_with_output`; corpus files (≤18 KB) are below pipe-buffer size regardless.
- Rust `CORPUS` (cli.rs:77-86) is byte-for-byte in sync with `tests/test_fltkfmt_parity.py:42-51` (`_CORPUS`), and `CONFIGS` matches `_CONFIGS` (80/2, 40/4).
- Golden fixture `crates/fltkfmt/tests/golden/fegen.fltkg.golden` is byte-identical to `fltk/fegen/fegen.fltkg`, matching the design's claim that the source is already canonically formatted.
- Carve-out logic (cli.rs:130-152): the `rust_parser_fixture.fltkg` × (40,4) branch correctly pins `out2 != out1` and `out3 == out2`, so a formatter fix trips `assert_ne!` and forces carve-out removal; all other 15 cases keep the strict `out2 == out1` check. Tuple/string comparisons are exact matches against the loop variables — no aliasing or copy-paste slip.
- Test 4 stderr assertion (`contains(path_str)`) holds because `run_inner` prefixes errors with the path exactly as passed on the command line (absolute temp path here); exit-2 and empty-stdout assertions match the `run_inner` contract (`worst = 2` on format error, error `continue`s before the stdout write).
- Trailing-newline test: strip-loop (`while base.last() == Some(&b'\n')`) is correct for the 1-newline source file; the `ends_with(b"\n")` / `!ends_with(b"\n\n")` pair correctly pins "exactly one trailing newline".
- TODO slugs in sync: `TODO(fltkfmt-integration-tests)` fully removed from code and `TODO.md`; new `formatter-group-idempotency` entry exists in both `TODO.md` and cli.rs:123.
- Temp-file names use pid + atomic counter; parallel test threads cannot collide; corpus reads are read-only. (Nit, below finding threshold: test 4's `remove_file` cleanup is skipped if an assertion panics first, so a *failing* run can leave a tiny file in the OS temp dir — standard Rust test behavior, no impact on passing runs or other tests.)
