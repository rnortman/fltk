# Dispositions — deep pass 2 (increments 4-6)

Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a
Reviewed HEAD: 0718645d66cec435752a28094f0cd7631712b058

All fixes are confined to `crates/fltk-fmt-cli/src/lib.rs`, `crates/fltkfmt/src/main.rs`,
and `TODO.md`. `cargo test -p fltk-fmt-cli` = 31 pass; clippy `-D warnings` + fmt clean for
both crates; `fltkfmt fltk/fegen/fegen.fltkg` formats end-to-end, exit 0.

---

errhandling-1:
- Disposition: Fixed
- Action: `write_atomic` (`crates/fltk-fmt-cli/src/lib.rs`, both cleanup sites) now writes a
  `warning: failed to remove temp file <path>: <err>` line to the injected `stderr` when the
  post-failure `fs::remove_file` itself fails; the primary write/rename error is still
  returned unchanged. `write_atomic` gained a `stderr: &mut dyn Write` parameter so the
  warning routes through the same injectable stream as the rest of the CLI.
- Severity assessment: Low. Only triggers on a double failure (primary op fails AND cleanup
  fails); without the line an orphaned temp could accumulate silently with no diagnostic
  hint for on-call.

errhandling-2:
- Disposition: Fixed
- Action: Added `if args.check && args.output.is_some()` rejection to `validate`
  (`lib.rs:104`) returning `"error: --check cannot be combined with --output"` (exit 2),
  plus a doc-comment update. The design states `--check` "write[s] nothing", which makes
  `--output` structurally incompatible; this closes the silent-drop where the `check` branch
  won by dispatch order.
- Severity assessment: Low-moderate. A user passing `--check --output out` previously got
  exit 0/1 with `out` silently never written and no indication `--output` was ignored.

correctness-1:
- Disposition: Fixed
- Action: `fltk_formatter_main!` (`lib.rs`, macro body) now binds `let result =
  parser.$parse(0)` then checks `parser.depth_exceeded()` and returns
  `Err(parser.error_message())` (which renders the depth-limit diagnostic) *before*
  inspecting `Some`/`None`. This honors the parser-core contract
  (`crates/fltk-parser-core/src/memo.rs:158-164`) and matches the Python binding's
  unconditional post-parse depth check (`fltk/fegen/gsm2parser_rs.py:991-996`).
- Severity assessment: High. Without it, a depth-rejected parse that still fully consumes
  could yield silent wrong output (and, under `--in-place`, silent source corruption) and
  diverge from the Python backend that CLAUDE.md requires equivalence with.

security-1:
- Disposition: Fixed
- Action: Replaced `fs::File::create` (create-or-truncate, follows symlinks) with a new
  `create_temp` helper (`lib.rs`) that opens via
  `OpenOptions::new().write(true).create_new(true)` (`O_EXCL`) and uses an
  unpredictable suffix (pid + monotonic `AtomicU64` counter + sub-second nanos), retrying on
  `AlreadyExists`. O_EXCL removes the arbitrary-file-overwrite primitive: a pre-planted
  symlink/file makes creation fail rather than be followed/truncated. Chose std-only over the
  `tempfile` crate to avoid adding a dependency to the root workspace / cargo-deny tree; the
  O_EXCL open fully closes the symlink-overwrite vector (the randomized name is
  defense-in-depth + collision avoidance).
- Severity assessment: Moderate (local). Required an attacker with write access to the
  target's directory; previously enabled clobbering arbitrary victim-writable files via a
  predicted temp path.

security-2:
- Disposition: Fixed
- Action: `write_atomic` now copies the source file's permissions onto the temp before rename
  (`fs::metadata(path).permissions()` → `fs::set_permissions(&tmp, ...)`, best-effort) so an
  in-place format no longer widens a restricted file (e.g. `0600` → default `0644`).
- Severity assessment: Low. `.fltkg` files rarely hold secrets, but silently widening a
  write-back target's mode is an over-permissive-default regression worth closing.

quality-1:
- Disposition: Fixed
- Action: The temp-file marker is now the generic crate name `.fltk-fmt.tmp.` (in the new
  `create_temp`), not the first consumer's binary name `.fltkfmt.tmp.`. `fltk-fmt-cli` is
  shared scaffolding, so its artifacts no longer mis-brand temps left by other formatter
  binaries.
- Severity assessment: Low. Cosmetic/operational; affected cleanup-script and gitignore
  filtering for non-`fltkfmt` consumers.

quality-2:
- Disposition: Fixed
- Action: Split the re-export (`lib.rs:16-26`): `RendererConfig` stays a plain `pub use` (it
  is in the public `run_main`/`format_fn` signature); `Renderer` and `resolve_spacing_specs`
  are now `#[doc(hidden)] pub use`, keeping them out of rustdoc as macro-support detail while
  remaining resolvable via `$crate::` in expansions.
- Severity assessment: Low. API-hygiene; prevents downstream from treating macro-support
  re-exports as supported entry points.

reuse-1:
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Low. The two macros share a pipeline shape but the duplication is not
  cheaply removable.
- Rationale (Won't-Do): The reviewer's own note concludes "De-duplication is not
  straightforwardly possible" — `render_native!`
  (`tests/rust_parser_fixture/src/native_tests.rs:1008`) is a test-harness macro that
  *panics* and returns `String`, while `fltk_formatter_main!` returns `Result<String, String>`
  through `run_main`, and the generated `Parser`/`Unparser` types share no trait that would
  permit a common callable. Unifying them would couple a test fixture in
  `tests/rust_parser_fixture` to the production `fltk-fmt-cli` crate, and the two consumers'
  consumed-checks differ intentionally (strict `pos == len` for the round-trip fixture vs.
  whitespace-tolerant `fully_consumed` for real files), so a shared helper would have to
  re-introduce the divergence as a parameter. Forcing dedup adds coupling and complexity for
  no behavioral gain.

efficiency-1:
- Disposition: Fixed
- Action: The `--in-place` branch in `run_inner` (`lib.rs`) now guards
  `if formatted != content { write_atomic(...) }`, skipping the temp+rename (and the mtime
  bump) for already-formatted files. The design (§3, "`--in-place` on an unchanged file")
  names this as the intended optimization; `content` is already in hand.
- Severity assessment: Low-moderate. Avoids needless writes and mtime churn that re-trigger
  watchers / incremental builds on the steady-state (already-formatted) tree.

efficiency-2:
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Low. Serial processing scales linearly with file count; cores idle on
  large batches.
- Rationale (Won't-Do): The design explicitly decides "No threading is introduced." (§3,
  "Concurrency / Send"). The design is frozen; introducing cross-file parallelism is net-new
  architecture — it changes the public `run_main` bound to `Fn + Send + Sync`, adds a worker
  pool and per-file output buffering to preserve gofmt-style ordering — and would contradict
  a deliberate design decision. The reviewer themselves classifies it as "a
  deliberate-tradeoff call, not a clear defect." Changing it belongs to a design revision,
  not respond-mode patching.

test-1:
- Disposition: Fixed
- Action: Added two `run_inner` tests (`lib.rs` test module):
  `stdin_default_writes_transformed_to_stdout` (empty `files` ⇒ stdin read, transformed to
  stdout, exit 0) and `stdin_read_error_exits_2_with_stdin_display` (a `FailingReader` ⇒ exit
  2 with `<stdin>` in stderr).
- Severity assessment: Moderate. The stdin path (display name, `None` filename, read-error
  handling) is an explicit design requirement and was entirely uncovered.

test-2:
- Disposition: TODO(fltkfmt-integration-tests)
- Action: TODO comment at `crates/fltkfmt/src/main.rs` and a `TODO.md` entry
  (`fltkfmt-integration-tests`). The four design §4 end-to-end tests (idempotency, golden,
  trailing-newline, parse-error) require the real Rust parser+unparser and land with the
  planned §2.3 increment that also wires `crates/fltkfmt/` into `make check`; the
  implementation log already records this deferral.
- Severity assessment: Moderate. End-to-end correctness (notably idempotency) is unverified
  until that increment; it is a hard prerequisite before the binary is check-gated.

test-3:
- Disposition: TODO(fltkfmt-integration-tests)
- Action: Folded into the same TODO (the parse-error integration test exercises the macro's
  `fully_consumed`-false and `unparse`→`None` error branches). These branches live inside the
  macro and cannot be unit-tested in `fltk-fmt-cli` without a real consumer; the `fltkfmt`
  integration-test increment is the covering work.
- Severity assessment: Low-moderate. The partial-parse guard and unparser-None mapping are
  untested until the integration tests land; both are now explicitly tracked.

test-4:
- Disposition: Fixed
- Action: Added `write_atomic_fails_cleanly_when_dir_missing` (nonexistent parent ⇒ `Err`, no
  panic/partial state) and `write_atomic_preserves_no_temp_on_success` (success rewrites
  content and leaves exactly one dir entry) as direct unit tests of the now-`pub(self)`
  helper.
- Severity assessment: Moderate. The atomicity guarantee ("a crash leaves the original
  intact") was verified only on the happy path; the failure/cleanup path now has coverage.

test-5:
- Disposition: Fixed
- Action: Added `filename_is_path_for_file_and_none_for_stdin`, which records the `filename`
  argument via a `RefCell`-capturing stub and asserts file input delivers `Some(<path>)` and
  stdin delivers `None`.
- Severity assessment: Moderate. The filename is load-bearing for the design requirement that
  parser error messages name the input file; a regression to a hardcoded/`None` value was
  previously undetectable.

test-6:
- Disposition: Fixed
- Action: Added `check_multi_file_reports_only_changed_and_exits_1`: two files (one already
  formatted, one would change) ⇒ exit 1, only the would-change path in stderr.
- Severity assessment: Low-moderate. The `worst.max(1)` accumulation across `--check` files
  was previously exercised only with a single file.
