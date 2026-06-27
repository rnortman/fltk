# Dispositions — deep pass 2, rework round (post-arbitration)

Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a
Prior HEAD: 96c9c1f1af0f2a433bbd44d8d4b2bdf7e4b6a5ca
New HEAD: 78eacab318a0d30e43a469dee2269b29cef0875d

The deep2 judge ESCALATED; the user arbitrated (notes-deep2-user.md, which governs).
Outcome of arbitration:

- **Primary (test-2 / test-3 + §2.3 check-gating, TODO(fltkfmt-integration-tests)):**
  the TODO deferrals are ACCEPTED as-is for a future iteration. No change made; the
  TODO(slug) comment (`crates/fltkfmt/src/main.rs`) and `TODO.md` entry stand.
- **Secondary (test-4):** the only item to actually fix — the prior `write_atomic`
  failure test never reached a cleanup branch, so the atomicity invariant for
  `--in-place` was unverified. Fixed this round.

Only test-4 is reworked below; all 13 other deep2 dispositions were judge-approved and
the two accepted TODO deferrals are left untouched per the user's direction.

---

test-4:
- Disposition: Fixed (rework — supersedes the prior round-1 Fixed)
- Action: Added `write_atomic_cleans_up_temp_when_rename_fails`
  (`crates/fltk-fmt-cli/src/lib.rs`, tests module) that targets an existing directory.
  This gets past `create_temp` (the parent dir exists, so the sibling temp is created)
  and past the write/flush step, then `fs::rename(tmp, target)` fails with EISDIR
  (renaming a file over a directory), genuinely reaching the rename-failure cleanup
  branch. The test asserts `write_atomic` returns `Err`, that the directory afterward
  contains *only* `subdir` (proving the cleanup `remove_file` removed the sibling temp —
  a broken cleanup would leave the temp and fail this assertion), and that the original
  target is untouched. The prior `write_atomic_fails_cleanly_when_dir_missing` test is
  retained (it covers `create_temp` error propagation) but, as the judge noted, returns
  before any cleanup branch; the new test closes that gap.
- Severity assessment: Moderate. Atomicity ("a crash/failure leaves the original
  intact") is the primary correctness invariant of `--in-place`; the cleanup branch that
  removes the orphan temp on a failed rename is now exercised, so a regression in that
  branch (wrong path to `remove_file`, early return) would be caught.

---

Verification: `cargo test -p fltk-fmt-cli` = 32 pass (was 31); `cargo clippy
-p fltk-fmt-cli --all-targets -D warnings` clean; `cargo fmt --check` clean; the
pre-commit `make check` (full gate incl. cargo-deny, check-no-pyo3) passed on the
commit.
