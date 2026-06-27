# Judge verdict — deep pass 2, rework round (post-arbitration)

Phase: deep. Base 762bbced..HEAD 78eacab. Round 2 (APPROVED or ESCALATE only).
Scope of adjudication (per user arbitration, `notes-deep2-user.md`, which governs):
only whether the rework satisfies the user's direction. The
`TODO(fltkfmt-integration-tests)` deferrals (test-2 / test-3 + §2.3 check-gating) are
user-ACCEPTED and are NOT re-litigated here. The sole required fix is test-4:
`write_atomic`'s cleanup branch must be genuinely exercised.

## Item walk

### test-4 — Fixed (rework, supersedes prior round-1 Fixed)

User's governing direction (verbatim): "add a test that actually reaches a cleanup
branch — e.g. rename failure by targeting a directory ... that's a 'the test is supposed
to work but doesn't' problem, so that should be fixed."

Change under review (`96c9c1f..78eacab`, the only code change): one added test,
`write_atomic_cleans_up_temp_when_rename_fails` (`crates/fltk-fmt-cli/src/lib.rs:928-951`).

Trace against `write_atomic` (`lib.rs:177-221`):
- Test sets `target = dir/subdir`, `fs::create_dir(&target)` — target is an existing
  directory; `dir` is a fresh isolated `temp_dir` (`lib.rs:570`) containing only `subdir`.
- `create_temp(dir, "subdir")` (`lib.rs:186` → `:140`) succeeds — parent dir exists, so the
  sibling temp is created. Past `create_temp` (this is exactly the gap the prior
  missing-dir test fell into: it returned at `create_temp` before any cleanup branch).
- write/flush (`lib.rs:194-197`) succeeds — temp is a regular file. Branch (a)
  (write-failure cleanup) not taken; control reaches the rename.
- `fs::rename(&tmp, path)` (`lib.rs:210`) fails with EISDIR — renaming a file over an
  existing directory. Control enters branch (b), the rename-failure cleanup
  (`lib.rs:211` `fs::remove_file(&tmp)`), then returns `Err`.

Assertion quality:
- `res.is_err()` — confirms the error propagates.
- `entries == ["subdir"]` — mutation-sensitive on the cleanup itself: if the branch's
  `remove_file` were broken (wrong path, early return before removal), the orphan temp
  would remain and `dir` would hold two entries, failing this assertion. This is a genuine
  check that the cleanup ran, not a vacuous assertion.
- `target.is_dir()` — confirms the original target is untouched (the `--in-place`
  atomicity invariant).

Verified by execution: `cargo test -p fltk-fmt-cli write_atomic` → 3 passed
(`write_atomic_cleans_up_temp_when_rename_fails ... ok`), confirming EISDIR fires on this
platform and the branch is reached.

Assessment: the test now genuinely reaches a cleanup branch and asserts the cleanup
occurred — exactly the fix the user required, via the user's own suggested mechanism
(rename failure by targeting a directory). The prior `write_atomic_fails_cleanly_when_dir_missing`
(error-propagation only) and `write_atomic_preserves_no_temp_on_success` (happy path) are
retained; the new test closes the cleanup-branch gap. Satisfied.

Note (not a defect for this round): branch (a) (write/flush-failure cleanup) remains
unreached. The user's governing direction narrowed the required fix to "a cleanup branch —
e.g. rename failure by targeting a directory" (singular, with that exact example), which
the implementer matched precisely; branch (a) coverage was not required by the arbitration
and is out of scope here.

## Disputed items

None. The single required fix is satisfied; the accepted TODO deferrals are untouched per
user direction.

## Approved

1 reworked item (test-4) verified. The 13 other deep2 dispositions were judge-approved in
round 1 and the two TODO deferrals are user-accepted; none re-walked.

---

## Verdict: APPROVED

The rework satisfies the user's arbitration. test-4's new test
(`write_atomic_cleans_up_temp_when_rename_fails`) genuinely reaches the rename-failure
cleanup branch and asserts the orphan temp is removed (mutation-sensitive), via the user's
own suggested mechanism; verified passing by execution. The user-accepted
`TODO(fltkfmt-integration-tests)` deferrals stand untouched.
