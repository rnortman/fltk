# Error-handling review — increments 4-6

Commit reviewed: 0718645d66cec435752a28094f0cd7631712b058
Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a

---

## errhandling-1

**File:** `crates/fltk-fmt-cli/src/lib.rs:141` and `:146`

**Broken error path:** In `write_atomic`, both the post-write-failure and post-rename-failure cleanup calls `let _ = fs::remove_file(&tmp)` silently discard any error from the cleanup.

**Why:** When `write_all`/`flush` fail (after `File::create` succeeded), or when `rename` fails, the code attempts `fs::remove_file(&tmp)` to clean up the temp file. If that secondary removal also fails (e.g., a permission change between create and rename, or the filesystem is read-only by the time cleanup runs), the failure is discarded. The primary error (write or rename) is correctly propagated to the caller and reported to stderr by `run_inner`.

**Consequence:** If both the rename and the subsequent `remove_file` fail, a `.<filename>.fltkfmt.tmp.<pid>` file is left on disk in the same directory as the source. The error reported to stderr names the rename failure but gives no hint that an orphaned temp file now exists. On-call diagnosing a persistent `--in-place` write failure cannot determine from the error output whether a temp file is accumulating in the target directory. Over repeated failures (e.g., a disk that periodically exhausts space), orphan files grow silently.

**What must change:** When `remove_file` fails in either cleanup site, log to stderr with context: `eprintln!("{}: warning: failed to remove temp file {}: {rm_err}", display, tmp.display())`, emitted before returning the primary error. The primary error is still returned unchanged; this only adds a secondary diagnostic line so on-call knows to look for the orphan.

---

## errhandling-2

**File:** `crates/fltk-fmt-cli/src/lib.rs:89-115` (`validate`) and `:324-343` (`run_inner` dispatch)

**Broken error path:** `validate` does not reject the combination `--check` and `--output`. In `run_inner`, the dispatch is `if args.check { … } else if … output { … }`, so when both are set the `check` branch unconditionally wins and the `output` branch is never reached.

**Why:** The design's explicit conflict list (`--in-place`+`--output`, `--in-place`+`--check`, `--in-place`+no-file, `--output`+multi-input) omits `--check`+`--output`. The design also states `--check` "write[s] nothing" — a definition that makes `--output` structurally incompatible. The validate function only enforces the four listed conflicts; `--check`+`--output` falls through to the dispatch silently.

**Consequence:** A user running `fltkfmt --check --output out.fltkg file.fltkg` receives no error, no warning, and exit code 0 or 1 (from the check result). The `out.fltkg` file is never created or modified. From the user's perspective the `--output` flag was accepted and acted on; from the code's perspective it was silently dropped. On-call diagnosing "why wasn't `out.fltkg` produced?" sees only a successful (exit 0) or check-diff (exit 1) run with no indication that `--output` was ignored. This is a silent treatment of expected-bad-input that should instead be validated and rejected with exit 2.

**What must change:** Add to `validate`:
```rust
if args.check && args.output.is_some() {
    return Err("error: --check cannot be combined with --output".to_string());
}
```
This follows the existing pattern for other incompatible pairs and makes the combination a usage error (exit 2, message to stderr).
