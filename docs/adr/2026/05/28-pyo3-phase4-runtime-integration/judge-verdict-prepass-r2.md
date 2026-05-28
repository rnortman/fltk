# Judge verdict — prepass (round 2)

Phase: prepass. Base f8a2fe1..HEAD cdffac4. Round 2 (APPROVED or ESCALATE only).
Note carried into this doc: concise, precise, source-backed. No padding.

Round 1 (verdict at `judge-verdict-prepass.md`) issued REWORK on a single disputed item: **scope-2**, Won't-Do rejected because its rationale ("CI runs `make build-*` before pytest") was false against repo state — CI ran only `make check`, which never built the three Rust artifacts, so every Tier-2 suite (incl. binding ACs AC3/AC5/AC8) silently skipped. The five other findings (slop-1..4, scope-1) were accepted and are not re-walked.

## Disputed item — re-adjudication

### scope-2 — now Fixed
Round-1 ask (verbatim from prior disputed-items): wire `make build-native`, `make build-test-user-ext`, `make build-fegen-rust-cst` into `ci.yml` before the pytest step so Tier-2 suites run rather than skip.

Diff at HEAD (commit cdffac4 "Wire Rust artifact builds into CI before pytest"):
- `.github/workflows/ci.yml`: new step `Build Rust artifacts` → `run: make build-native build-test-user-ext build-fegen-rust-cst`, placed **before** the `Run checks` step (`make check`, which runs `test`→`pytest`). Step ordering verified in the YAML: Build precedes Run checks.
- All three targets exist in `Makefile` at HEAD and resolve to real builds: `build-native` (`maturin develop`), `build-test-user-ext` (`cd tests/rust_cst_fixture && maturin develop` → module `phase4_roundtrip_cst`), `build-fegen-rust-cst` (`cd tests/rust_cst_fegen && maturin develop` → module `fegen_rust_cst`).
- Both crate dirs present with `Cargo.toml` (`tests/rust_cst_fixture/`, `tests/rust_cst_fegen/`) — targets are not no-ops.

Assessment: this is exactly the fix the prior verdict prescribed, and it is the correct form (CI wiring, not a pytest-shells-to-make test, which the responder rightly never adopted). The false premise the round-1 Won't-Do rested on is now true: the artifacts the Tier-2 `skipif(not importable)` guards depend on are built before pytest, so the binding ACs execute in CI rather than skip. The design's "a CI skip is a failure signal" contract (design lines 442/559) is discharged. The this-iteration regression (skip-when-absent policy + CI-builds-first contract) is no longer silently deferred. Accept.

## Approved

6 findings: 6 Fixed verified (slop-1..4, scope-1 from round 1; scope-2 this round).

Out-of-scope note (no verdict impact, carried from round 1): `TODO(rust-cst-abi-pinning)`'s `TODO.md` entry has its code marker in `docs/rust-cst-extension-guide.md`, not at a source work site. Not a dispositioned finding; flagged for a future author, not adjudicated here.

---

## Verdict: APPROVED

The sole round-1 dispute (scope-2) is resolved by the prescribed CI wiring, verified in the HEAD diff: three `make build-*` targets run before pytest; targets and crates exist. All other dispositions were accepted in round 1.
