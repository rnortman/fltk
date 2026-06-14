# A8 — BUILD / PACKAGING / RELEASE READINESS & SUPPLY CHAIN (adversarial)

Dimension verdict: **WEAK** (shippable in a narrow, hand-held, single-consumer mode; NOT
releasable as a clean drop-in artifact to arbitrary out-of-tree consumers).

All citations are file:line at HEAD c0182064. Live measurements re-run on this machine.

---

## What is genuinely solid (do not re-litigate)

The cargo-side engineering is real and disciplined, and I verified it live:

- **No-pyo3 isolation is real and mechanically proven.** `cargo tree -p fltk-parser-core`
  and `fegen-rust --no-default-features` show no pyo3 node (re-confirmed live). The
  `check-no-pyo3` guard (`Makefile:155-175`) tests 6 python-off graphs with a positive control
  before each negative assertion — a correctly-constructed negative test. The feature-matrix split
  (`fltk-cst-core` pyo3 behind default-on `python`; `fltk-parser-core` has *no* python feature at
  all — structural absence, `crates/fltk-parser-core/Cargo.toml:11-13`) is correct.
- **The check-target anti-drift family** (`Makefile:7-76`) is rigorous: one sanctioned divergence
  (cargo-deny), structurally enforced by `check: check-ci`.
- **The Bazel `fltk_pyo3_cdylib` macro is complete, not stubbed** (`rust.bzl:200-391`): it handles
  real subtleties — Bazel-crate-feature non-forwarding (`rust.bzl:346-352`), cross-repo `Label()`
  resolution (`rust.bzl:353-362`), abi3 rename, recursion_limit injection, runtime `fltk._native`
  dep. It is driven by a real external consumer (Clockwork, `clockwork/dsl/BUILD.bazel`).
- **`make check` is green end-to-end** (exit 0, 5 cargo-deny manifests pass, clippy `-D warnings`
  clean across the matrix). This is not a "green because nothing runs" gate.

The findings below are the build/packaging/release gaps that block a *clean downstream release*,
in roughly descending severity.

---

## FINDING a8-build-release-1 — No registry release; the runtime crates downstream links against are unpublished, version-unpinnable, and the consumer guide leads with a non-working `version = "0.2"` example  [MAJOR]

`fltk-cst-core` and `fltk-parser-core` are the two crates that EVERY downstream Rust CST/parser
extension must link against (the generated `cst.rs`/`parser.rs` `use fltk_cst_core::…` and the
parser runtime). They are versioned **0.2.0** (`crates/fltk-cst-core/Cargo.toml:3`,
`crates/fltk-parser-core/Cargo.toml:3`) and — unlike every other first-party crate — carry **no
`publish = false`** key and a real `license = "MIT"`, i.e. they look like they are *meant* to be
published. They are **not on crates.io or anywhere else** (no publish job exists; the only workflow
is `ci.yml`, which only runs `make check-ci`).

Consequence chain for an out-of-tree consumer:
- The downstream consumer guide (`docs/rust-cst-extension-guide.md:59`) leads with
  `fltk-cst-core = { version = "0.2", default-features = false, features = ["python"] }` as the
  "if using a published release" example. **This line does not resolve today** — there is no
  published 0.2. The working forms are the two commented-out path/git lines below it
  (`:61-62`). The headline example in the official guide is non-functional.
- Every in-tree consumer (all 4 fixtures + `crates/fegen-rust`) depends on the runtime crates via
  `path = "../../crates/fltk-cst-core"` (verified across all manifests). There is **zero**
  version-based dependency anywhere in the tree, so the 0.2.0 version number is effectively
  decorative — it is never used to resolve anything.
- A real maturin consumer must therefore git-pin or path-pin FLTK. There is no reproducible
  registry artifact, no semver contract a consumer can rely on, and the version number a consumer
  *would* write (`0.2`) is the one that fails.

Why it matters: the whole point per CLAUDE.md is a near-drop-in backend for out-of-tree apps. "Add
a Cargo dependency on the runtime crate" is step 2 of the documented workflow, and the documented
happy-path form is currently broken. This is the single largest gap between "works in this repo"
and "shippable to someone else."

Remediation: either (a) publish `fltk-cst-core`/`fltk-parser-core` to crates.io and add a release
job, or (b) if registry release is deliberately deferred, mark both `publish = false`, demote the
`version = "0.2"` example in the guide to a commented-out "once published" line, and make the
git-pin form the primary documented path. Decide deliberately; do not leave them in the limbo of
"published-looking but unpublished."

---

## FINDING a8-build-release-2 — Three-way version skew across the artifacts a consumer sees  [MINOR]

The version numbers are inconsistent across the surfaces a consumer touches:
- `pyproject.toml:9` → `version = "0.1.1"` (the PyPI/maturin wheel)
- root `Cargo.toml:7` (`fltk-native`) → `version = "0.1.0"`
- `crates/fltk-cst-core` / `fltk-parser-core` → `version = "0.2.0"`

So the same checkout simultaneously claims to be FLTK 0.1.1 (wheel), 0.1.0 (native cdylib), and
ships 0.2.0 runtime crates. CHANGELOG.md has `## [0.2.0]` as a *past* release but `[Unreleased]`
on top, and the version-skew makes it impossible to answer "what version of the Rust backend is
this?" There is no single source of version truth.

Consequence: a downstream consumer pinning "FLTK 0.1.1" (the wheel version) gets runtime crates
labeled 0.2.0; an ABI-compat conversation ("rebuild against fltk-cst-core 0.2",
`docs/rust-cst-extension-guide.md:64-66`) references a version that does not match the wheel. Minor
on its own, but it compounds finding 1 — the version a consumer reads off the wheel is not the
version they must write in Cargo.toml.

Remediation: pick one versioning policy (e.g. workspace-version) and align, or document the
intended independent-versioning scheme explicitly in the release/ABI docs.

---

## FINDING a8-build-release-3 — `tests/rust_cst_fegen/` is an orphaned, git-tracked, byte-identical dead duplicate of `crates/fegen-rust/` with a NAME COLLISION; built/checked/deny-scanned/regenerated by nothing  [MAJOR]

`tests/rust_cst_fegen/` is fully git-tracked (Cargo.toml, Cargo.lock, `src/cst.rs` [15,515 LoC],
lib.rs, parser.rs, native_parser_tests.rs — verified via `git ls-files`). Its `cst.rs` and
`parser.rs` are **byte-identical** to `crates/fegen-rust/src/` (`diff -q` = no output). It was
"Promoted from tests/rust_cst_fegen/" (`crates/fegen-rust/Cargo.toml:3`) but the original was
never deleted.

It is referenced by **no Makefile target**: not built (`grep rust_cst_fegen Makefile` = 0 hits),
not in `cargo-test-no-python`, not clippy'd, **not in the `cargo-deny` manifest list**
(`Makefile:181-186` lists root + fegen-rust + rust_cst_fixture + rust_parser_fixture + rust_poc_cst,
NOT rust_cst_fegen), and not regenerated by `gencode` (`Makefile:247-298` regenerates
`crates/fegen-rust/src/cst.rs`, never the orphan). So its 645KB generated `cst.rs` and its
committed `Cargo.lock` can rot forever, and its lockfile is outside every supply-chain scan.

**Worse — name collision.** The orphan's `Cargo.toml` declares the **same crate name AND lib name**
as the canonical crate: package `fegen-rust-cst`, `[lib] name = "fegen_rust_cst"`
(`tests/rust_cst_fegen/Cargo.toml` vs `crates/fegen-rust/Cargo.toml`). If anyone runs
`maturin develop` in the orphan dir (it still has the old `build-fegen-rust-cst`-style invocation
documented in ADRs), it installs a Python module `fegen_rust_cst` that *collides with and shadows
the canonical one* — and since its `cst.rs` can silently diverge after a `gencode`, a developer
could end up testing stale generated CST without noticing.

`CHANGELOG.md:22` is **stale** and points consumers/maintainers at the wrong path: it claims "`make
gencode` now regenerates `tests/rust_cst_fegen/src/cst.rs`" — gencode does no such thing anymore;
it regenerates `crates/fegen-rust/src/cst.rs`. The `TODO(fegen-cst-rs-single-source)` slug that
tracked this hazard across ~10 ADR files is **no longer in TODO.md** — the tracking was dropped when
the crate was promoted, but the dead copy was left behind.

Consequence: ~17,171 LoC of unverified, unscanned, drift-prone generated code in the shipped tree;
a latent module-name collision; and stale release notes. For a project whose generated output *is*
the product, an orphaned generated artifact that no lane can regression-check is exactly the failure
mode the gencode-drift discipline exists to prevent.

Remediation: `git rm -r tests/rust_cst_fegen/`; fix `CHANGELOG.md:22` and the prose references in
`docs/rust-cst-extension-guide.md:174`.

---

## FINDING a8-build-release-4 — No automated gencode-drift gate; ~75k LoC of committed generated Rust (the public product) can silently diverge from its generators and pass CI  [MAJOR]

`gencode` (`Makefile:247-298`) is the only thing that regenerates the committed Rust CST/parser
files, and it is **not in `check-common`'s step list** (`Makefile:40`) — so neither `make check`
nor CI runs `gencode` followed by `git diff --exit-code`. The Makefile itself admits the gate is
manual: "`git diff --stat` reveals any drift between committed generated files and what the
generators actually produce" (`Makefile:245`). `grep gencode .github/` = the workflow never
mentions it.

Because the Rust generators emit `.rs` as raw strings with no IIR (per u3), the *only* place the
correctness of the committed generated output is enforced is rustc/clippy/parity-tests over the
committed bytes — none of which detect that the committed bytes differ from what the current
generator would now emit. So:
- A generator regression that changes output is invisible if the committed files are stale.
- A hand-patch to a committed generated `.rs` passes CI while being unreproducible from the
  generator.

This is high-impact precisely because, per CLAUDE.md, the generated output is the public API for
out-of-tree consumers. A consumer regenerating from the same grammar with the same FLTK could get
output that differs from what FLTK shipped, with no in-repo signal.

Remediation: add a `check-gencode-clean` step to `check-common` that runs `gencode` and
`git diff --exit-code` (in a clean worktree / on a copy), failing on any drift. This is the missing
control that converts "manual discipline" into an enforced invariant.

---

## FINDING a8-build-release-5 — cargo-deny (the ONLY supply-chain / RustSec / yanked-crate / license gate) runs nowhere in CI; and Dependabot does not cover Cargo or pip deps  [MAJOR]

`cargo-deny` is on the local-only `check` lane, never `check-ci` (`Makefile:53-76`,
`ci.yml:30-35`), by deliberate design (the runner doesn't install it). So RustSec advisory
enforcement, yanked-crate detection (`deny.toml:7` `yanked = "deny"`), license allow-listing, and
source allow-listing depend **entirely on a developer having the local pre-commit hook installed
and not using `--no-verify`**. A CI-only contributor flow, a fresh clone with no hook, or a bypassed
commit all skip the supply-chain gate, and a PR review never sees it.

Compounding this: `.github/dependabot.yml` covers **only `github-actions`** — NOT `cargo` and NOT
`pip`/`uv`. So there is no automated mechanism to even surface a new advisory in a transitive Rust
dep (pyo3, regex-automata, and the ~79-crate graph) or a Python dep. The combination —
no-deny-in-CI + no-dependabot-for-cargo — means a newly-published RustSec advisory against a
pinned transitive dependency is invisible to the entire automated pipeline until a human happens to
run a local `make check`.

`deny.toml:27` also sets `multiple-versions = "warn"` (not deny), so duplicate-version bloat is
tolerated silently across the six independent lockfiles.

Consequence: for a "production-ready" supply-chain posture, the advisory gate is effectively
opt-in and human-dependent. The runner-doesn't-have-cargo-deny rationale is solvable
(`taiki-e/install-action@cargo-deny`, or a separate scheduled job), so this is a fixable hole, not
a fundamental constraint.

Remediation: add a CI job (or a step using a cargo-deny install action) that runs `make cargo-deny`
on PRs and on a weekly schedule; add `cargo` and `pip` ecosystems to dependabot.

---

## FINDING a8-build-release-6 — The entire downstream-facing Bazel surface has ZERO CI coverage; the only abi3/no-libpython property remains empirically unverified (verify-pyo3-ext-module)  [MAJOR]

`make check-ci` is pure cargo + pytest + ruff. **Nothing runs `bazel build` in CI** — not the
`:native` cdylib, not the `bootstrap_native` smoke target (`BUILD.bazel:117-126`), not
`generate_rust_parser`. The Bazel path — which is one of the two documented downstream consumption
mechanisms and the one Clockwork actually uses — fires only when a human runs Bazel locally. It can
silently break (a rules_rust bump, a crate_universe resolution change, a Label-resolution
regression) with no signal in this repo.

The unresolved `verify-pyo3-ext-module` TODO (`MODULE.bazel:42-48`, `TODO.md:13-15`) is the
load-bearing unknown: it is **unproven** that the Bazel-built cdylib actually has `extension-module`
active on `@fltk_crates//:pyo3` and therefore does **not** link libpython. If crate_universe drops
the feature, the `.so` links libpython and fails to import as a CPython extension. There is **no
wheel/import smoke test anywhere** (no test does `ldd`/import-and-assert on a built `.so`; the
python-feature test lane deliberately links libpython for *unit tests* — the opposite property).
Combined with the unverified Bazel path, the "is the shipped extension a real abi3 no-libpython
module?" question is answered by neither CI nor any test.

Consequence: the downstream build path most likely to be used by a Bazel consumer is both
uncovered and resting on an unverified linking assumption. "It builds on my machine and Clockwork's
machine" is the entire evidence base.

Remediation: add a minimal Bazel CI job that builds `:native` + `:bootstrap_native` and a smoke
test that imports the produced module under a non-build-host Python; resolve verify-pyo3-ext-module
with a `bazel build //:native` + `ldd | grep -v libpython` (or import-under-clean-interp)
assertion.

---

## FINDING a8-build-release-7 — The only real downstream consumer pins FLTK via a TEMPORARY local_path_override; no consumption against a committed/published ref has ever been validated  [MAJOR]

Clockwork (`clockwork/MODULE.bazel:34-39`) consumes FLTK via a `local_path_override` to
`/home/rnortman/src/fltk`, explicitly marked TEMPORARY with `TODO(fltk-pin-finalize)`: "MUST be
reverted to the real git pin (bumped to the reviewed FLTK HEAD) before merging." So the
"drop-in replacement works downstream" evidence is: *one* consumer building against a *live local
working copy of this exact checkout*. The Bazel path has never been validated against a committed
git pin, let alone a published artifact.

Consequence: there is no proof that a consumer who pins FLTK at a committed SHA (the only
reproducible way to consume it today, given no registry release) gets a working build. Combined with
finding 1 (no registry release) and finding 6 (no Bazel CI), the production-readiness claim "a
downstream app can adopt the Rust backend" is supported only by an irreproducible local setup.

Remediation: flip Clockwork to a committed git pin and run its `clockwork_rust_roundtrip_test`
against it once, end-to-end, as the actual drop-in proof. Until that happens, the downstream story
is unproven.

---

## FINDING a8-build-release-8 — Single-platform / single-Python CI vs an advertised 3.10–3.12 + CPython/PyPy support matrix  [MINOR]

`ci.yml:10,21` runs ubuntu-latest, Python 3.10 only, single job. `pyproject.toml:19-24` advertises
3.10/3.11/3.12 and both CPython and PyPy. The wheel is built `abi3-py310` (`Cargo.toml:24`), which
is forward-compatible *in principle* on 3.10+, but **nothing in CI exercises 3.11/3.12 at runtime**,
no macOS/Windows build is tested, and PyPy (which interacts very differently with pyo3/abi3) is never
exercised at all.

Consequence: a consumer on 3.12 or macOS or PyPy is relying on properties that the project asserts
but never tests. The abi3-py310 forward-compat claim is plausible but unverified for this codebase's
actual extension surface (which crosses cdylib boundaries via the ABI sentinel — a place where ABI
assumptions matter more than usual).

Remediation: add a CI matrix dimension (at minimum 3.10/3.11/3.12 on ubuntu; ideally macOS) that
builds the wheel and runs the Rust-parity test subset; either test PyPy or drop the PyPy classifier.

---

## FINDING a8-build-release-9 — `bazel-cst-spike-hub` leakage is live: the leftover spike's criterion dev-dep is already in the root lockfile feeding the Bazel crate hub  [NIT]

`crates/fltk-cst-spike` is a root workspace member (`Cargo.toml:2`) carrying a `criterion`
dev-dependency. The `fltk_crates` Bazel hub seeds `from_cargo` off the root manifest + lockfile
(`MODULE.bazel:33-50`), and `criterion 0.5.1` is present in the root `Cargo.lock` (verified). So the
`TODO(bazel-cst-spike-hub)` concern (`MODULE.bazel:31-32`) is not hypothetical — the spike's
benchmark deps already flow into the downstream-facing crate hub. It is benign today (criterion is
dev-only and not referenced by any Bazel target), but it is dead weight in the hub graph and a
latent conflict surface, and the spike is itself a "leftover proof-of-concept" still kept as a
workspace member. This couples cruft (the spike should arguably be removed) to the packaging
surface.

Remediation: exclude `fltk-cst-spike` from the workspace members feeding the hub (or remove the
spike entirely per the cruft assessment), per the existing TODO.

---

## FINDING a8-build-release-10 — Six independent Cargo workspaces × ~18.3 GiB build cache, six lockfiles; reproducibility tax and multi-lockfile drift surface  [NIT]

The layout is the root workspace + 5 standalone crates (fegen-rust + 3 tests fixtures +
rust_cst_fegen orphan), each with its own `[workspace]` and `Cargo.lock`, each recompiling its own
pyo3. Measured build cache ≈ 18.3 GiB across six `target/` trees (per u6). The detachment is
*justified* (workspace feature unification would re-enable pyo3 in the python-off graphs,
`Makefile:133-134`), so this is an accepted trade, but it carries two real costs:
- **Reproducibility / CI time & disk**: six independent dependency resolutions, six pyo3 compiles.
- **Multi-lockfile drift**: each standalone crate's `Cargo.lock` is pinned independently; a security
  bump must touch all of them, and the per-crate cargo-deny fan-out is hand-maintained in 4
  separate Makefile targets (clippy / clippy-no-python / test-no-python / cargo-deny). That fan-out
  has **already drifted once** — `rust_cst_fegen` fell off every lane (finding 3).

Consequence: not a blocker, but the layout multiplies the hand-maintained per-crate lists that are
the project's demonstrated drift surface.

Remediation: longer-term, consider a second workspace for the python-off fixtures (one lockfile,
one target) rather than N detached crates; at minimum, generate the per-crate Makefile lists from a
single list variable so a crate cannot silently fall off one lane.

---

## Bottom line for this dimension

The cargo *engineering* is production-grade (feature isolation proven, gate disciplined, Bazel macro
complete). But **release readiness is weak**: there is no registry artifact, the runtime crates a
consumer must link are unpublished-yet-version-labeled with a non-working documented example, the
supply-chain gate and the downstream Bazel path and the abi3-no-libpython property are all
CI-invisible/unverified, the only real consumer pins via a temporary local override, and the tree
ships an orphaned name-colliding 17k-LoC dead duplicate plus ~75k LoC of generated code with no
automated drift gate. None of these is unfixable, and none indicts the runtime architecture — they
are packaging/release/CI omissions. But collectively they mean the backend is **not yet shippable as
a clean drop-in to an arbitrary out-of-tree consumer**; it is shippable only in the current
hand-held, single-consumer, local-checkout mode.
