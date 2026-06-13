# Deep Security Review — cargo-deny CI split

Commit reviewed: edb782c (base 604dab1).
Scope: `.github/workflows/ci.yml`, `Makefile` (ADR + exploration docs are prose).
No application/runtime code changed. No secrets, injection surface, auth, crypto,
or network handling introduced. Findings concern supply-chain gate coverage only.

## security-1 — CI no longer detects RustSec advisories, yanked crates, or banned/unknown sources

- File: `.github/workflows/ci.yml:31` (`make check-ci`); `Makefile:68` (`check-ci` omits cargo-deny); `deny.toml` (the bypassed policy).
- Issue: `cargo-deny` is the only enforcement of `deny.toml` — advisories (`yanked = "deny"`, RustSec DB), license allow-list, and `[sources]` `unknown-registry = "deny"` / `unknown-git = "deny"`. Moving CI to `check-ci` removes that enforcement from the one gate that runs on untrusted/external input (PRs, fork branches, dependency bumps from bots like Dependabot).
- Trust boundary / data flow: dependency manifests (`Cargo.toml`/`Cargo.lock`) are attacker-influenceable via PRs and automated dependency-update PRs. The RustSec advisory DB and the source allow-list are exactly the controls that catch a malicious/compromised or vulnerable transitive crate. With this change those controls run only on a maintainer's local machine, *after* review, and only if that maintainer has cargo-deny installed.
- Consequence: A PR (or a merge from a contributor whose local hook is absent/bypassed) can introduce a crate with a known RustSec advisory, a yanked crate, a disallowed license, or a dependency pulled from an unknown registry/git source, and CI will pass green. The gate's value is precisely time-of-merge drift detection on input the maintainer did not hand-author; relocating it to local-only precommit removes it from the boundary where untrusted changes arrive. Local hooks are trivially bypassable (`git commit --no-verify`), not run on the merge commit, and not run by contributors lacking the tool — so the residual coverage is weaker than the ADR's "compensates" framing implies.
- This is the documented, accepted trade-off (ADR Consequences). Flagged so the security cost is explicit, not to block. Suggested mitigation if revisited: run `cargo-deny` in a dedicated CI job via `cargo install cargo-deny --locked` or `taiki-e/install-action`/`EmbarkStudios/cargo-deny-action` pinned by commit SHA — cost is ~30-60s, paid only on Rust-dep changes. A scheduled (cron) cargo-deny job would also catch newly-published advisories against the existing lockfile, which neither lane currently does.

## security-2 — Anti-drift between lanes relies solely on human review

- File: `Makefile:36-72`.
- Issue: `check` and `check-ci` both delegate to `check-common`, but the sanctioned divergence (cargo-deny on `check` only) plus the "MANDATORY" anti-drift comment is enforced only editorially. ADR Consequences confirms "No automated test enforces the anti-drift rule."
- Trust boundary / data flow: not an external-input boundary; internal maintenance hazard.
- Consequence: A future edit that adds a security-relevant step directly to `check` (mirroring the existing cargo-deny precedent) would silently never run in CI — the same blind spot as security-1, but for a future check, undetected. Low immediate severity; noted because it compounds security-1 over time. Suggested fix: a trivial CI/test assertion that `check-ci` and `check` differ only by the cargo-deny line, or have `check` invoke `check-ci` + cargo-deny so the relationship is structural rather than parallel.

## Non-findings (checked)

- No secrets/credentials/tokens in the diff or in `ci.yml`.
- No command injection: Makefile `$$step` values are a fixed literal list, not external input; `mktemp`/`cat` usage is on tool-controlled temp files.
- `dtolnay/rust-toolchain@stable` unchanged by this diff (not introduced here).
