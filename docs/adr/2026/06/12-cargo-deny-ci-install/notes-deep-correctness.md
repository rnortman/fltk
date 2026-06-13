# Deep Correctness Review — cargo-deny CI split

Commit reviewed: edb782c (base 604dab1). Scope: Makefile check-family split + ci.yml.

No findings.

Traced:
- Step set: original `check` = 11 common steps + `cargo-deny` (12). New `check-common` runs the
  same 11 in same order; new `check: check-common` recipe runs `cargo-deny` last. Equivalent;
  `check-ci: check-common` drops only `cargo-deny`, matching ADR intent.
- Ordering / parallelism: `check`'s `cargo-deny` recipe runs only after prerequisite `check-common`
  completes (make orders prereqs before recipe even under `-j`); no race, no reordering.
- Failure propagation: `check-common` failure (inner `for` loop `exit 1`) aborts make before the
  `check` recipe runs, so `cargo-deny` is skipped and `check` exits non-zero. `check-ci` (empty
  recipe) propagates `check-common`'s exit status. Both correct.
- Removed `failed=0` var was dead (never read; loop exits 1 directly) in the original — its removal
  changes nothing.
- tmpfile lifecycle unchanged; cleaned on both success and failure paths.
- `.PHONY` updated to include check-ci/check-common.
