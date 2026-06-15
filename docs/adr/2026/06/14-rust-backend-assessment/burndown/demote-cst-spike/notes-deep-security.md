# Deep security review — demote-cst-spike

Commit reviewed: be08c47 (base e813764).
Scope: deletion of `crates/fltk-cst-spike/` (duplicate of `tests/rust_poc_cst`), `benches/traverse.rs`,
and the `criterion` dev-dep; config cleanup in `Cargo.toml`, `MODULE.bazel`, `Makefile`, `TODO.md`,
`deny.toml`, `Cargo.lock`; move of spike tests into `tests/rust_poc_cst/src/spike_tests.rs`.

This is a deletion/cleanup change with no new untrusted-input data flow, no new endpoints, no auth
surface, no crypto, no filesystem/network sinks. The diff was reviewed against the prompt's catch list
with particular attention to the deny.toml supply-chain gate.

## Findings

No findings.

## Notes on the deny.toml change (per prompt's explicit ask)

Confirmed the `deny.toml` edit does NOT weaken license/advisory enforcement for the remaining crates:

- The only change is to the human comment above `[licenses.private]`; the active directive
  `ignore = true` is unchanged. cargo-deny's `licenses.private.ignore` applies to every workspace-local
  crate with `publish = false` (and unpublished sources) — it is keyed on the `publish`/registry status
  of each crate, NOT on the crate names listed in the comment. So dropping `fltk-cst-spike` from the
  comment text changes documentation only, not enforcement behavior.
- The crate being exempted is itself deleted, so there is nothing left for that exemption to cover.
- The remaining first-party exemptions (`fltk-native`, `tests/*` fixtures) keep exactly the same
  treatment as before. The `[advisories]` (yanked = "deny", fail on unfixed vulns), `[licenses].allow`
  allowlist, `[bans]`, and `[sources]` (deny unknown registry/git) blocks are all untouched.
- The `criterion` dev-dependency — the only nontrivial third-party crate the spike pulled in, and the
  one that leaked into the downstream-facing `@fltk_crates` Bazel hub — is fully removed from
  `Cargo.lock`, `Cargo.toml`, and all crate manifests. This shrinks the supply-chain attack surface
  rather than expanding it; no advisory/license exception was added to compensate, and none is needed.
  (The lone surviving "criterion" string is an unrelated word in a Python test comment.)

## Other checks (all negative)

- No hardcoded secrets/creds/keys/tokens introduced; no secrets in the deleted code or new test move.
- `tests/rust_poc_cst/src/lib.rs`: `mod spike_tests` is gated behind `#[cfg(test)]` — test-only code is
  not compiled into the shipped library/extension; no new runtime surface.
- `MODULE.bazel` / root `Cargo.toml` workspace-member removal narrows what feeds the Bazel crate hub;
  resolves `TODO(bazel-cst-spike-hub)` (the concern that the spike's deps could leak downstream). Net
  reduction in downstream-facing dependency surface.
- Stale doc comment in the moved `spike_tests.rs` still references `cargo test -p fltk-cst-spike`
  (now run via `rust_poc_cst`). Documentation-only staleness, not a security issue — noted for the
  quality reviewer's lane, not actioned here.
