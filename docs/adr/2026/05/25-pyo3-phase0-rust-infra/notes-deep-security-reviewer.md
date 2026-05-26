# Deep Security Review — Phase 0 PyO3/Rust Infra

Commit reviewed: d650cfafd331ae531a38d8b1479b7a539a058cfd (base f1e2a98)

Scope: build-infra only. No request handling, no auth surface, no user-input data flow, no crypto, no secrets in diff. `src/lib.rs` is a trivial `Ping`/`pong` pyclass with no input, no `unsafe`. Most findings are supply-chain / CI trust-boundary observations, not exploitable application bugs.

---

## security-1

File: `.github/workflows/ci.yml:21`

Issue: CI step `uses: dtolnay/rust-toolchain@stable` pins to a mutable git ref (`@stable`), not an immutable commit SHA.

Trust boundary / data flow: A GitHub Actions third-party action runs with the workflow's token and full access to the CI runner. The `@stable` tag is mutable — the action author (or anyone who compromises that account/repo) can repoint it to arbitrary code, which then executes in CI on every push to this repo. This is the classic GitHub Actions supply-chain trust boundary: untrusted-but-trusted-by-reference code executing in your CI context.

Consequence: If `dtolnay/rust-toolchain` is compromised or the `stable` ref is moved to malicious code, an attacker gets code execution on the CI runner — able to exfiltrate `GITHUB_TOKEN`, repo secrets, or tamper with build artifacts (the compiled `.so` that downstream installs trust). For a parser/compiler toolkit distributed to other projects, build-artifact tampering is the higher-value target. Note: `dtolnay/rust-toolchain` deliberately does not publish version tags, only branch refs, so SHA-pinning is the only immutable option.

Suggested fix: Pin to a full commit SHA with a version comment, e.g. `uses: dtolnay/rust-toolchain@<40-char-sha>  # stable, <date>`. Update via Dependabot (which can manage SHA-pinned actions). Same applies to any other unpinned actions in the file (`actions/checkout`, `astral-sh/setup-uv` — outside this diff but worth a pass).

---

## security-2

File: `fltk/test_native.py:1-7` (informational)

Issue: Test module placed inside the shipped `fltk` package (`python-packages = ["fltk"]` in `pyproject.toml`), so `test_native.py` is packaged into the wheel and installed on end users' machines.

Trust boundary / data flow: Not an injection or input-flow issue. The test imports `fltk._native` and calls `Ping().pong()` — no untrusted input. The concern is purely that test code ships in the distributable.

Consequence: Minimal here (the test is benign and side-effect-free at import beyond `importorskip`). Flagging because the pattern — co-locating test modules with shipped package source — means any future test that performs side effects at import time, embeds fixtures/credentials, or imports heavy/unsafe helpers would also ship to users and run in their `import` path. No action required for this file; note for the convention going forward (consider a top-level `tests/` dir or excluding `test_*` from the wheel).

---

## security-3

File: `Cargo.lock` / `uv.lock` (informational)

Issue: New dependency trees added — PyO3 0.23.5 + transitive Rust crates, and maturin 1.13.3 + tomli.

Trust boundary / data flow: New third-party code entering the build/runtime trust boundary. All entries carry checksums (Cargo.lock SHA-256, uv.lock sha256 per wheel), so lockfile integrity is intact and tampering on re-fetch would be detected.

Consequence: No known-vulnerable versions in this set as of the review date; pinned + checksummed, so this is low-concern. Listed only so the dependency expansion is on record — future `cargo update` / `uv lock` changes to these trees should get a fresh look, since the Rust extension is `cdylib` loaded into the Python process (a memory-safety bug in a future PyO3 or transitive crate version would execute in-process with no sandbox).

---

No application-level injection, auth, path-traversal, SSRF, deserialization, secret-exposure, or crypto issues in this diff. The single actionable item is security-1 (SHA-pin the CI action).
