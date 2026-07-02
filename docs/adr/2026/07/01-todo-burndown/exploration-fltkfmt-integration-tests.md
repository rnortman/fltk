# Exploration: `TODO(fltkfmt-integration-tests)`

Base commit: `8fd5ecf` (HEAD, `main`, clean working tree). All facts below verified against
this state.

## TODO occurrences

- `TODO.md:93-95` — section header `## \`fltkfmt-integration-tests\`` (line 93), body (line
  95, verbatim in task).
- `crates/fltkfmt/src/main.rs:13-16` — the sole `TODO(fltkfmt-integration-tests)` code
  comment:
  ```
  // TODO(fltkfmt-integration-tests): add the design §4 end-to-end tests under
  // `crates/fltkfmt/tests/` (idempotency, golden, trailing-newline, parse-error) — they also
  // cover the `fltk_formatter_main!` partial-parse and unparse-None error branches, which need
  // a real consumer like this binary. Landing with the §2.3 `make check` gating increment.
  ```
- No other `TODO(fltkfmt-integration-tests)` comments exist in code. All other hits are
  prose references inside `docs/workflow/2026-06-27-rust-fltkfmt/*.md` (review-chain
  workflow artifacts from the crate's original implementation), not TODO markers.

## Does `crates/fltkfmt` exist? Does it have tests?

Yes, it exists: `crates/fltkfmt/{Cargo.toml,Cargo.lock,src/main.rs}` (plus `target/` build
output). Added in a single commit, `1e9e402` ("rust-fltkfmt: standalone pure-Rust .fltkg
formatter binary") — `git log --oneline -- crates/fltkfmt/` shows only this one commit.

`crates/fltkfmt/tests/` (the directory the TODO says the four tests belong in) **does not
exist** — confirmed via `find crates/fltkfmt -type f` (only `Cargo.lock`, `Cargo.toml`,
`src/main.rs`, and `target/**` build artifacts) and `test -d crates/fltkfmt/tests` (false).
`src/main.rs` itself has no `#[cfg(test)]` module — it is 23 lines, entirely the crate
doc-comment, the TODO, and one `fltk_fmt_cli::fltk_formatter_main! { ... }` invocation.

Executed directly: `cargo test -q --manifest-path crates/fltkfmt/Cargo.toml` →
`running 0 tests` / `test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered
out`. The crate currently has zero tests of any kind.

## Is `crates/fltkfmt` wired into `make check`?

Yes, already wired — and has been since the same commit `1e9e402` that created the crate
(`git log --oneline -S "crates/fltkfmt/Cargo.toml" -- Makefile` → only `1e9e402`). Four
`Makefile` steps reference `crates/fltkfmt/Cargo.toml` by explicit `--manifest-path` (the
pattern used for all standalone non-workspace crates, per `crates/fltkfmt/Cargo.toml`'s own
top comment explaining it keeps its own `[workspace]` rather than joining the root one):

- `Makefile:141` — `cargo-test-no-python`: `cargo test -q --manifest-path
  crates/fltkfmt/Cargo.toml` (currently compiles + runs 0 tests, per above).
- `Makefile:149` — `cargo-clippy-no-python`: `cargo clippy -q --manifest-path
  crates/fltkfmt/Cargo.toml --all-targets -- -D warnings`.
- `Makefile:172-174` — `check-no-pyo3`: builds a `cargo tree` for the crate, asserts
  `fltk-parser-core` is present (positive control) and `pyo3` is absent.
- `Makefile:187` — `cargo-deny`: `cargo deny --manifest-path crates/fltkfmt/Cargo.toml
  check --config deny.toml`.

`cargo-test-no-python`, `cargo-clippy-no-python`, and `check-no-pyo3` are all in the
`check-common` step list (`Makefile:40`), which both `check` (local/precommit) and
`check-ci` (CI) depend on (`Makefile:61`, `Makefile:76`). `cargo-deny` is a `check`-only
step (`Makefile:61-70`), run locally but not in CI per the documented CI/local split
(`Makefile:17-25`). So: **the `fltkfmt` binary crate is already check-gated today**, for
build-breakage, clippy-cleanliness, pyo3-absence, and supply-chain — just not for the four
design-specified integration tests, which don't exist to be gated.

## Which of the four design §4 tests exist, and where?

Design source: `docs/workflow/2026-06-27-rust-fltkfmt/design.md:268-305` ("## 4. Test
plan"), which specifies four independent test surfaces:

1. `fltk-fmt-cli` unit/integration tests (pure Rust, stub `format_fn`, no real grammar) —
   design.md:272-283.
2. `fltkfmt` integration tests (`crates/fltkfmt/tests/`, pure Rust) — design.md:285-294 —
   idempotency, golden/canonical, trailing-newline robustness, parse-error path. This is
   the exact list the TODO defers.
3. Cross-backend parity (pytest, "recommended") — design.md:296-301.
4. Drift guard (`make gencode` + `git diff --stat`) — design.md:303-305.

Ground truth per item:

- **Item 1 (`fltk-fmt-cli` unit tests) — exists.** `crates/fltk-fmt-cli/src/lib.rs` has an
  extensive `#[cfg(test)]` module: 38 `#[test]` functions found via `grep -n '#\[test\]'`
  (lines 444 through 1051), covering `fully_consumed` edge cases, stdin default/read-error
  paths, `--check`/`--in-place`/flag-conflict behavior, and `write_atomic` including a
  rename-failure cleanup branch (`write_atomic_cleans_up_temp_when_rename_fails`,
  `lib.rs:928-951`, confirmed by `docs/workflow/2026-06-27-rust-fltkfmt/judge-verdict-deep2-rework.md`
  to reach `write_atomic`'s branch (b) rename-failure cleanup via `cargo test -p
  fltk-fmt-cli write_atomic` → 3 passed). This item is unrelated to the TODO (it's a
  different crate, `fltk-fmt-cli` not `fltkfmt`) and is not what the TODO defers.

- **Item 2 (the four `crates/fltkfmt/tests/` tests) — do not exist anywhere.** No
  idempotency test, no golden/canonical fixture test, no trailing-newline test, and no
  parse-error-path test for the `fltkfmt` binary exist in the repo, in
  `crates/fltkfmt/tests/` or elsewhere. This is exactly what `TODO.md:95` and
  `main.rs:13-16` claim is missing, and the claim is accurate: these four tests are absent.

- **Item 3 (cross-backend parity pytest) — exists, but is not one of the four deferred
  tests.** `tests/test_fltkfmt_parity.py` (145 lines) exists: for a pinned corpus of 8 real
  `.fltkg` files × 2 render configs (80/2, 40/4) = 16 parametrized cases
  (`test_fltkfmt_matches_python`), it builds the `fltkfmt` binary via `cargo build`, runs it
  as a subprocess on each corpus file, and asserts byte-for-byte equality against an
  in-process Python reference pipeline (`plumbing.parse_text` → `unparse_cst` →
  `render_doc`). This satisfies design.md's item 3 exactly (single-pass byte-equality
  parity), but does **not** exercise idempotency (double-format), a golden/pinned-output
  fixture, trailing-newline variants, or the parse-error path — it always feeds well-formed
  `.fltkg` corpus files and only checks that a single format pass matches Python. It does
  not count toward closing the TODO's four items.

- **Item 4 (drift guard) — pre-existing, unrelated to this TODO**, not investigated further
  (not part of the TODO's scope).

## Is the §2.3 increment (test increment + `make check` wiring) done, pending, or abandoned?

**Split status — this is the key finding.** The TODO text (`TODO.md:95`,
`main.rs:13-16`) frames both halves — "wires `crates/fltkfmt/` into `make check`" and the
four integration tests — as a single not-yet-landed future increment ("Deferred to the
planned §2.3 increment that also wires crates/fltkfmt/ into make check; this test increment
is a hard prerequisite before the binary is check-gated" / "Landing with the §2.3 `make
check` gating increment").

Ground truth: the `make check` wiring half is **already done**, committed in the same
commit (`1e9e402`) that created the crate and the TODO itself — see the Makefile section
above. Only the four-test half remains outstanding, and it lives in
`crates/fltkfmt/tests/`, a directory that does not exist.

This is corroborated by the crate's own workflow log,
`docs/workflow/2026-06-27-rust-fltkfmt/implementation-log.md`:
- Lines 149-151: "Note: §2.3's Makefile check-gating (...), the `crates/fltkfmt/tests/`
  integration tests, and the cross-backend parity pytest are not in this increment" —
  written at an intermediate point before increment 7.
- Lines 153-175 ("## Increment 7 — Wire `crates/fltkfmt` into `make check` gating
  (§2.3)"): explicitly logs adding the four Makefile lines above, and states at line
  160-162: "binary crate has no tests yet — integration tests deferred under
  TODO(fltkfmt-integration-tests) — so this compiles the crate and runs 0 tests; it still
  gates build breakage." This log entry itself already treats "check-gated" and "has the
  four integration tests" as separable, decoupled facts — contradicting the TODO's own
  framing that the tests are "a hard prerequisite before the binary is check-gated."
- Lines 177-186 ("## Increment 8 — Cross-backend parity pytest (§4)"): logs adding
  `tests/test_fltkfmt_parity.py` as "the last §4 test-plan item that was neither
  implemented nor deferred under TODO(fltkfmt-integration-tests)" — i.e., the log's own
  author considered the parity pytest a separate, now-closed §4 item, distinct from the
  TODO's four items.

The review-chain artifacts for this crate (`docs/workflow/2026-06-27-rust-fltkfmt/
dispositions-deep2.md:135-145`, `judge-verdict-deep2.md`, `judge-verdict-deep2-rework.md`)
show the TODO was an explicit, user-arbitrated disposition for two review findings
("test-2" and "test-3") — user-accepted as a deferral, not silently dropped, and judge-approved
in the deep-2 rework round (`judge-verdict-deep2-rework.md`: "the two `TODO(fltkfmt-integration-tests)`
... deferrals ... are user-ACCEPTED and are NOT re-litigated"). Nothing in the workflow
history suggests the four-test increment was abandoned — no later note retracts or
supersedes it — but nothing in the repository shows it has been picked up either. Status:
**pending** (not started), not abandoned, with the check-gating half of the original
two-part deferral already completed out of band.

## Summary of facts (no prescriptions)

| Question | Answer |
|---|---|
| `crates/fltkfmt` exists? | Yes (`Cargo.toml`, `Cargo.lock`, `src/main.rs`); one commit, `1e9e402`. |
| `crates/fltkfmt` has any tests? | No — zero tests, no `tests/` dir, no `#[cfg(test)]` in `main.rs`; verified by running `cargo test`. |
| Wired into `make check`? | Yes, already, since `1e9e402`: `Makefile:141,149,172-174,187` (`cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3`, `cargo-deny`). |
| Idempotency test | Does not exist. |
| Golden/canonical test | Does not exist. |
| Trailing-newline test | Does not exist. |
| Parse-error-path test | Does not exist. |
| §2.3 "wire into `make check`" increment | Done (in `1e9e402`). |
| §2.3 four-test increment | Pending, not abandoned. |
| TODO's framing accuracy | The claim that the four tests are missing is accurate. The claim that check-gating is a future increment gated on the tests ("hard prerequisite before the binary is check-gated") is stale/inaccurate — check-gating already happened, independently, in the same commit. |
