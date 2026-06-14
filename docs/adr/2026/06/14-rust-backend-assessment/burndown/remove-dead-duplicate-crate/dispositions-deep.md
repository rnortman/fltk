# Dispositions — remove-dead-duplicate-crate deep review

Commit reviewed: f1e1fef (base 9f96d43dc613308332d00bdf7d2436a2abca5416)
Respond commit: 5bc28c3

## errhandling

No findings.

## correctness

No findings.

## security

No findings.

## test

No findings.

## reuse

No findings.

## quality

quality-1:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Self-resolved by reviewer — `build-fegen-rust-cst` is still a valid, wired target; `.PHONY` and `build-test-fixtures` references are correct, not stale. No action warranted.
- Rationale (Won't-Do): The reviewer's own conclusion is "No issue here." The target exists and is correct. Treating this as a finding would be actively wrong.

quality-2:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Self-resolved by reviewer — the stale reference lives in a worktree agent artifact, not on main-branch `TODO.md`. No issue on main.
- Rationale (Won't-Do): The reviewer's own conclusion is "No issue on main." Changing main-branch files to fix a worktree artifact would be incorrect.

quality-3:
- Disposition: Fixed
- Action: CHANGELOG.md:22-28 — replaced vague `etc.` parenthetical with explicit list of all eight Rust outputs produced by `make gencode`, plus a pointer to the Makefile target for the authoritative list. Verified against Makefile lines 268-288.
- Severity assessment: Without the full list, future commits that drop an output from `gencode` can't be caught by changelog drift — the same pattern this burndown item was created to fix. Low severity but correct to address.

quality-4:
- Disposition: Fixed
- Action: docs/rust-cst-extension-guide.md:174-178 — added sentence directing users to `crates/fegen-rust/` as a more complete example (`.pyi` stub, `extension-module`/`python` feature split), built via `make build-fegen-rust-cst`. Updated trailing sentence from singular to plural ("These are FLTK-internal").
- Severity assessment: Users following the guide as their entry point to building a consumer extension miss the only in-tree example that demonstrates the recommended feature-flag pattern. Low severity (fixture still works as a minimal example), but trivial to correct.

## efficiency

No findings.
