# Deep security review — remove-dead-duplicate-crate

Commit reviewed: f1e1fef (base 9f96d43)

No findings.

Scope: pure deletion of the dead/unbuilt duplicate crate `tests/rust_cst_fegen/`
(6 tracked files: Cargo.lock, Cargo.toml, src/{cst.rs,lib.rs,parser.rs,native_parser_tests.rs})
plus three textual fixups to stale references (CHANGELOG.md, docs/rust-cst-extension-guide.md,
crates/fegen-rust/Cargo.toml provenance comment).

Security assessment:
- No new code, endpoints, input-handling, deserialization, filesystem/network ops, or auth
  surface introduced. Deletions cannot add a vulnerability class.
- No secrets/credentials/keys present in the diff (deletions and doc text only).
- Verified no surviving references to `rust_cst_fegen` in main-tree build/config
  (Makefile*, *.toml, *.bazel, MODULE.bazel, TODO.md, deny.toml) that would point a
  build at a now-absent path. Remaining hits are confined to an unrelated git worktree
  (.claude/worktrees/agent-ab295be24eef6e7ce/) and ADR docs — outside this change's scope.
- deny.toml advisory-ignore posture (RUSTSEC-2025-0020 / RUSTSEC-2026-0177, pyo3) is
  unchanged by this diff; the deleted manifest is simply no longer one of the manifests
  the pending pyo3 bump must touch. Not a regression from this change.
