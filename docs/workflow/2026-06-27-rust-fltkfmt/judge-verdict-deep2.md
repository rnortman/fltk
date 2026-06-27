# Judge verdict — deep pass 2 (increments 4-6)

Phase: deep. Base 762bbced..HEAD 96c9c1f. Round 1.
Notes: 7 reviewer files; 16 findings (12 Fixed, 2 Won't-Do, 2 TODO).
Code under review: `crates/fltk-fmt-cli/src/lib.rs`, `crates/fltkfmt/src/main.rs`, `TODO.md`.

## Added TODOs walk

### test-2 + test-3 — TODO(fltkfmt-integration-tests) at crates/fltkfmt/src/main.rs:13 (+ TODO.md entry)

Both findings fold into one TODO. test-2: `fltkfmt` has zero integration tests; design §4's
four end-to-end tests (idempotency, golden/canonical, trailing-newline, parse-error) are
entirely unverified. test-3: the macro's two error branches (`fully_consumed`-false partial
parse; `unparse` → `None`) are uncovered. TODO mechanics are correct — slug present, `TODO(slug)`
comment at `main.rs:13`, matching `TODO.md` entry; slug is the join key.

**Q1 (worth doing):** yes — design §4 names these as the deliverable's tests, and idempotency
(`format(format(x)) == format(x)`) is called out as "the core correctness invariant" for a
self-applicable formatter. Unambiguously worth doing.

**Q2 (design cycle / owner input required before doing):** **NO.** Design §4 already specifies
exactly what each test asserts. The `fltkfmt` binary exists and runs the full pipeline end to
end — the dispositions and implementation-log Increment 6 both record a manual smoke test
("`fltkfmt fltk/fegen/fegen.fltkg` formats end-to-end, exit 0"), i.e. parse → unparse → resolve
→ render already works against the real Rust parser+unparser. Nothing about authoring these
tests needs a design cycle or product-owner input; they are writable now. The deferral is a
self-chosen increment boundary (implementation-log Increment 6: "the `crates/fltkfmt/tests/`
integration tests ... are not in this increment"), not a design dependency.

**Furthermore:** this iteration (Increment 6, commit c52d998) *created* the untested binary.
Per the rubric, a problem this iteration created cannot be silently deferred via TODO — it must
be fixed or escalated for visibility.

**Compounding (design-mandated work also deferred):** design §2.3 requires `crates/fltkfmt/` to
be wired into `make check` via `--manifest-path` lines in `cargo-test-no-python`,
`cargo-clippy-no-python`, `check-no-pyo3` (the "zero Python" proof for the binary), and
`cargo-deny`. The Makefile carries none of these for `crates/fltkfmt/Cargo.toml` (verified —
the only `fltkfmt` mentions in the Makefile are generation comments at :282-283), and the
implementation-log Increment 6 confirms the gating is deferred to the same future increment. So
the headline §2.3 deliverable is shipping **neither tested nor CI-covered**. (`fltk-fmt-cli` is
a root-workspace member and *is* covered by root cargo-test/clippy/deny — 31 tests; the gap is
specifically the standalone `fltkfmt` binary crate.)

**Assessment:** Q1 yes / Q2 NO. A clear NO to Q2 means the work is doable now without further
input — it does not qualify as a legitimate design-deferral TODO. The aggregate deferred work
is non-trivial (four design §4 integration tests + the cross-backend parity pytest + four
Makefile check-gating targets), and this iteration created the gap. This is the scope-calibration
case: a respond-mode TODO retroactively narrows the increment to "binary builds + manual smoke
test," parking the design-mandated verification and CI gating behind a single comment. Per the
scope rule this is **ESCALATE on round 1, not REWORK** — human arbitration on the increment
boundary. See escalation section.

## Other findings walk

### correctness-1 — Fixed
Claim: `fltk_formatter_main!` never calls `parser.depth_exceeded()`; a depth-rejected parse can
surface as `Some` with a wrong CST (left-recursive seed), so a fully-consuming wrong parse is
silently formatted — under `--in-place`, silent source corruption — diverging from the Python
backend CLAUDE.md requires equivalence with. Consequence stated; high severity (correctness +
data corruption).
Verified: contract is real — `memo.rs:160-164` states verbatim that callers must check
`depth_exceeded()` and discard if set; `depth_exceeded()` exists (`memo.rs:144`, generated
`parser.rs:117`). Fix (`lib.rs:291-300`) binds `result = parser.$parse(0)`, then
`if parser.depth_exceeded() { return Err(parser.error_message()) }` *before* the `Some`/`None`
match. Matches the suggested fix and the Python binding's unconditional post-parse check.
Assessment: addresses the consequence at the named site. Accept.

### security-1 — Fixed
Claim: predictable temp name + `File::create` (create-or-truncate, follows symlinks) gives an
attacker with directory-write access a symlink/TOCTOU arbitrary-file-overwrite primitive
(CWE-59/377/367). Consequence stated; trust boundary (local attacker writing the target's dir)
is real for the in-place write path.
Verified: new `create_temp` (`lib.rs:140-167`) opens with `OpenOptions::write(true).create_new(true)`
(O_EXCL) — a planted symlink/file makes creation fail rather than be followed/truncated — with
an unpredictable suffix (pid + `AtomicU64` counter + sub-second nanos), retrying on `AlreadyExists`.
O_EXCL closes the overwrite vector. Accept.

### security-2 — Fixed
Claim: in-place write drops the original's permissions (temp gets default 0644), widening a 0600
source. Consequence stated; low (`.fltkg` rarely holds secrets) but a real over-permissive-default
regression in a write-back path.
Verified: `write_atomic` (`lib.rs:190-192`) copies `fs::metadata(path).permissions()` onto the
temp via `set_permissions` (best-effort) before rename. Accept.

### errhandling-1 — Fixed
Claim: both cleanup `let _ = fs::remove_file(&tmp)` sites silently discard removal errors; on a
double failure an orphan temp accumulates with no diagnostic. Consequence stated; low (double-
failure only).
Verified: both sites (`lib.rs:198-207`, `:210-219`) now emit
`warning: failed to remove temp file <path>: <err>` to the injected stderr; the primary error is
still returned unchanged. `write_atomic` gained a `stderr: &mut dyn Write` param routing through
the injectable stream. Accept.

### errhandling-2 — Fixed
Claim: `validate` does not reject `--check` + `--output`; the `check` branch wins by dispatch
order and `--output` is silently dropped (exit 0/1, file never written, no indication). Consequence
stated; low-moderate (silent treatment of expected-bad input).
Note: the correctness reviewer classified this same combination as "intended, not a bug" because
the design's conflict list omits it. The design also states `--check` "write[s] nothing," which
makes `--output` structurally meaningless with it; rejecting a nonsensical combination breaks no
valid use. The responder chose the more defensive reading and fixed it.
Verified: `validate` (`lib.rs:104-106`) now returns `"error: --check cannot be combined with
--output"`. Accept (defensible; no valid behavior regressed).

### quality-1 — Fixed
Claim: shared scaffolding hardcodes the first consumer's name in the temp suffix
(`.fltkfmt.tmp.`); other formatter binaries mis-brand their temps, breaking cleanup/gitignore
filters. Consequence stated; low/cosmetic-operational.
Verified: `create_temp` (`lib.rs:152`) uses the generic crate marker `.fltk-fmt.tmp.`. Accept.

### quality-2 — Fixed
Claim: macro-support re-exports (`Renderer`, `resolve_spacing_specs`) lack `#[doc(hidden)]`, so
they appear as first-class public API in rustdoc; downstream may depend on them and break if the
macro is reimplemented. Consequence stated; low (API hygiene).
Verified: split (`lib.rs:16-26`) — `RendererConfig` stays a plain `pub use` (in the public
`run_main` signature); `Renderer`/`resolve_spacing_specs` are `#[doc(hidden)] pub use`, still
resolvable via `$crate::`. Accept.

### efficiency-1 — Fixed
Claim: `--in-place` rewrites already-formatted files unconditionally, bumping mtime and
re-triggering watchers/incremental builds on a stable tree. Consequence stated; low-moderate.
Verified: in-place branch (`lib.rs:414`) now guards `if formatted != content { write_atomic(...) }`;
`content` is already in hand. Design §3 names this as the intended optimization. Accept.

### reuse-1 — Won't-Do
Claim: `fltk_formatter_main!` duplicates the parse→guard→unparse→resolve→render pipeline from
`render_native!` (test fixture). The reviewer's *own* note concludes "De-duplication is not
straightforwardly possible" — different return types (`String` panic vs `Result<String,String>`),
no shared trait on generated `Parser`/`Unparser`, intentionally divergent consumed-checks.
Rationale argues active harm: unifying couples a `tests/` fixture to the production crate and
re-introduces the intentional divergence as a parameter. The finding states no consequence
demanding action and the reviewer concedes infeasibility.
Assessment: Won't-Do rationale meets the bar (active harm of forcing dedup). Accept.

### efficiency-2 — Won't-Do
Claim: per-file pipeline is serial; cross-file parallelism is available since each file's `Rc`
stays thread-local. The reviewer explicitly classifies this as "a deliberate-tradeoff call, not
a clear defect." Rationale: design §3 "Concurrency / Send" decides "No threading is introduced";
parallelizing is net-new architecture (changes `run_main` to `Fn + Send + Sync`, adds a worker
pool + ordered output buffering) contradicting a frozen design decision — a design revision, not
respond-mode patching.
Assessment: Won't-Do argues active harm (contradicting a deliberate frozen decision) and the
reviewer agrees it is not a defect. Accept.

### test-1 — Fixed
Claim: the stdin code path (display `<stdin>`, `None` filename, read-error handling) is entirely
uncovered. Consequence stated; moderate (explicit design requirement, likely production path).
Verified: `stdin_default_writes_transformed_to_stdout` (`lib.rs:800`) and
`stdin_read_error_exits_2_with_stdin_display` (`lib.rs:821`, via a `FailingReader`) cover both.
Accept.

### test-4 — Fixed (overclaim — cleanup branches still untested)
Claim: `write_atomic`'s two cleanup branches — (a) write/flush fails → `remove_file` + return;
(b) rename fails → `remove_file` + return — are untested; a broken `remove_file` (wrong var,
early return) would go undetected. Consequence stated; moderate (atomicity is the `--in-place`
invariant), though the specific gap is error-path-of-error-path robustness → should-fix.
Verified: the added `write_atomic_fails_cleanly_when_dir_missing` (`lib.rs:902`) targets a
nonexistent parent — but after the security-1 refactor that fails inside `create_temp` (the
`create_temp(dir,...)?` at `lib.rs:186` returns `NotFound`), which returns *before* either
cleanup branch. `write_atomic_preserves_no_temp_on_success` is a success-path test. So neither
new test exercises the `remove_file` cleanup branches the finding is about; the disposition's
claim "the failure/cleanup path now has coverage" is inaccurate for those branches. Branch (b)
is trivially testable (point `write_atomic` at an existing directory → rename fails → cleanup
runs). The responder did follow the reviewer's literal suggestion ("nonexistent directory"),
which the refactor invalidated.
Assessment: incomplete. Secondary item (should-fix) folded into the escalation below.

### test-5 — Fixed
Claim: the `filename` argument to `format_fn` is never asserted; a regression to always-`None`
or a hardcoded value would be undetected, and filename is load-bearing for error messages.
Consequence stated; moderate.
Verified: `filename_is_path_for_file_and_none_for_stdin` (`lib.rs:834`) records `filename` via a
`RefCell` stub and asserts `Some(<path>)` for file input, `None` for stdin. Accept.

### test-6 — Fixed
Claim: multi-file `--check` `worst.max(1)` accumulation is exercised only with one file. Consequence
stated; low-moderate.
Verified: `check_multi_file_reports_only_changed_and_exits_1` (`lib.rs:872`) uses one clean + one
dirty file, asserts exit 1 with only the dirty path in stderr. Accept.

## Escalation

Two items need human arbitration; the first is the driver.

### Primary — test-2 / test-3 + design-mandated check-gating (TODO(fltkfmt-integration-tests))

- **Reviewers' claim/consequence:** the `fltkfmt` binary — the §2.3 "proof of life" pure-Rust
  formatter that is the entire point of this work — has zero integration tests; design §4's
  idempotency/golden/trailing-newline/parse-error tests (and the macro's error branches) are
  unverified. Independently, design §2.3 mandates wiring `crates/fltkfmt/` into four `make check`
  targets (including the `check-no-pyo3` "zero Python" proof), and none of that is in the Makefile.
- **Responder's disposition/rationale:** TODO(fltkfmt-integration-tests) — tests "require the real
  Rust parser+unparser and land with the planned §2.3 increment that also wires `crates/fltkfmt/`
  into `make check`." Tracked via `TODO(slug)` comment + `TODO.md` entry + implementation log.
- **Why human arbitration is needed:** the TODO fails rubric Q2 — the tests require no design cycle
  or owner input (design §4 fully specifies them; the binary already runs end to end), so they are
  doable now and do not qualify as a legitimate design-deferral. This iteration created the untested
  binary, which the rubric says cannot be silently deferred. The deferred work is non-trivial in
  aggregate (4 integration tests + cross-backend parity pytest + 4 Makefile gating targets), and the
  increment split that parks it was the implementer's choice, not a design decision — the frozen
  design treats tests + gating as part of the §2.3/§4 deliverable. Approving increments 4-6 as-is
  marks the headline binary "done" while it is neither tested nor CI-covered, with only a comment
  forcing the follow-up. This is precisely the scope-calibration ESCALATE case: the human should
  decide whether the increment boundary (defer all `fltkfmt` tests + CI gating to a future increment)
  is acceptable, or whether the binary increment must include its design-mandated tests and
  `make check` gating before approval.

### Secondary — test-4 (cleanup branches untested)

- **Reviewer's claim/consequence:** `write_atomic`'s `remove_file` cleanup on write-failure and
  rename-failure is untested; a broken cleanup would go undetected (atomicity is the `--in-place`
  invariant). Should-fix.
- **Responder's disposition/rationale:** Fixed — added a missing-dir failure test + a success test.
- **Why flagged:** the missing-dir test fails at `create_temp` (pre-refactor it would have hit the
  write branch; post-refactor it returns before either cleanup branch), so the cleanup branches
  remain uncovered and the "failure/cleanup path now has coverage" claim is inaccurate. On its own
  this is a round-1 REWORK item (add a test that actually reaches a cleanup branch — e.g. rename
  failure by targeting a directory). Folded here so the implementer addresses it alongside the
  primary scope decision.

## Approved

13 findings sound: correctness-1, security-1, security-2, errhandling-1, errhandling-2, quality-1,
quality-2, efficiency-1, test-1, test-5, test-6 (11 Fixed verified) + reuse-1, efficiency-2
(2 Won't-Do sound).

---

## Verdict: ESCALATE

The §2.3 `fltkfmt` binary is shipping with zero tests and zero `make check` gating — both
design-mandated (§4 + §2.3) and both deferred via TODO(fltkfmt-integration-tests). The TODO fails
the acceptability rubric's Q2 (the tests need no design cycle / owner input — they are writable now
against the working binary), this iteration created the untested binary, and the aggregate deferred
work (4 integration tests + parity pytest + 4 Makefile gating targets) is non-trivial. Per the
scope-calibration rule this is ESCALATE on round 1, not REWORK: human arbitration on the increment
boundary. test-4 is a secondary should-fix (cleanup branches still untested) to address alongside.
All 13 other dispositions are acceptable.
