# Deep correctness review — document-scope-boundary

Commit reviewed: 0adf385 (base 440b4ed). Diff: version bump 0.1.x→0.2.0 across
`pyproject.toml`, root `Cargo.toml`, `Cargo.lock`, `uv.lock`, plus a doc rewrite of the
`[dependencies]` pin block in `docs/rust-cst-extension-guide.md`.

No logic, control flow, or data flow in this diff. Reviewed for version-string consistency
and for any latent assertion/invariant the bump could violate.

## No findings.

Verification performed (all clean):

- The four shipping artifacts are now uniformly 0.2.0:
  - `pyproject.toml:9` = 0.2.0; `uv.lock` `fltk` entry = 0.2.0 (in sync).
  - root `Cargo.toml:7` (`fltk-native`) = 0.2.0; `Cargo.lock` `fltk-native` = 0.2.0 (in sync).
  - `crates/fltk-cst-core` and `crates/fltk-parser-core` already 0.2.0 in both Cargo.toml and
    Cargo.lock — untouched, consistent with the spec table.
- No stale 0.1.0/0.1.1 reference remains for any shipping artifact. Remaining 0.1.0 strings are
  legitimately out of scope: `crates/fegen-rust` (separate workspace, internal), `crates/fltk-cst-spike`
  (internal), and throwaway test-crate templates (`test_nullable_loop_guard.py:309`, guide example
  crate `my-grammar-cst` at guide line 45). None are part of the three-runtime/shipping decision.
- ABI-marker non-impact: the cross-cdylib ABI string is
  `concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))` (cross_cdylib.rs:20), sourced from
  `fltk-cst-core`'s own version (0.2.0, unchanged). The bumped crate (`fltk-native`, root) does NOT
  feed the marker. The string is `fltk-cst-core/0.2.0` before and after — no ABI skew introduced.
- Test assertions in `tests/test_rust_span.py` (555-556, 633) match version-agnostic substrings
  (`"fltk-cst-core/"` with trailing slash; `"wrong/0.0.0"` is a hardcoded fake) — they do not pin
  the real version and are unaffected by the bump.
- No Python `__version__` attribute and no `importlib.metadata`/`pkg_resources` runtime version
  lookup exists, so no code path can read a now-stale version.
- Dependency resolution unaffected: root `fltk-native` depends on `fltk-cst-core` via `path` with no
  version constraint, so bumping `fltk-native` cannot create a resolution mismatch.
- Lockfile integrity: `fegen-rust` and the test crates are intentionally separate workspaces and
  correctly absent from the root `Cargo.lock` (grep count 0) — the bump does not orphan or duplicate
  any lock entry.
- Doc rewrite is non-executable prose; the removed `version = "0.2"` crates.io example (which did not
  resolve) is gone, and the surviving path/git/Bazel options are accurate. The git URL
  `github.com/rnortman/fltk` matches the owner used in CHANGELOG.md. No broken example remains.
