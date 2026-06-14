# Recommended Actions — Rust Backend Assessment (planning extraction)

This file is a **planning extraction** of every recommended thing-to-do in the
2026-06-14 Rust-backend production-readiness assessment (`ASSESSMENT.md`, with its
supporting `a1`–`a8` dimension reviews and `u1`–`u7` maps). It exists so that the
discrete actions called for by §5 (Blocking Items & Major Risks), §6 (the Strategic
Question), and §7 (Recommended Path Forward) can be referenced **by name** during
planning.

Each action below is identified by a **slug** — the slug is the unique identifier and
the join key for planning discussions. Unlike the repo's `TODO.md` convention, these
slugs have **no `TODO(slug)` code-comment counterparts**; they are purely a planning
device and impose no in-code marker requirement.

Items are ordered to make dependencies easy to follow (roughly Phase A → D), but the
slug, not the position, is the identity. Each item records the assessment Phase it came
from (A/B/C/D where applicable), a priority/class derived from the assessment
(blocker / major / cleanup / strategic), a `Depends on:` line citing prerequisite slugs,
and a `Refs:` line citing the relevant assessment finding id(s).

---

## `fix-forged-abi-segfault`

- **Phase:** A (step 1) · **Class:** blocker
- **Depends on:** none
- **Refs:** `a4-correctness-safety:F1-forged-abi-markers-segfault`; ASSESSMENT §5 (sole blocker), §7 item 1

Fix the one true correctness blocker. The public `#[classmethod]`
`Span._with_source_unchecked` (`crates/fltk-cst-core/src/span.rs:444`) reaches a
`cast_unchecked` (via `extract_source_text` / `crates/fltk-cst-core/src/cross_cdylib.rs`)
from a pure-Python forged object whose two ABI marker attributes were copied off a real
`SourceText`, producing a reproducible SIGSEGV (verified live 4/4) and a type-confusion
primitive. Add a real native-instance check before the cast — one that rejects
plain-Python objects with forged attributes while still accepting a genuine
foreign-cdylib `SourceText` (a checked-but-not-identity downcast; a same-type identity
check is too strict for the multi-cdylib case). Add the segfault repro as a
subprocess-isolated regression test. This is a hard no-ship: a public method on a
near-drop-in span class that segfaults the interpreter on pure-Python input, where the
Python backend it replaces is memory-safe.

## `gencode-drift-gate`

- **Phase:** A (step 2) · **Class:** major (highest-leverage process fix)
- **Depends on:** none
- **Refs:** `a1:no-automated-gencode-drift-gate`, `a5:no-regen-drift-gate` (§3), `a6-tests:no-gencode-drift-gate`, `a8-build-release-4`; ASSESSMENT §5, §7 item 2

Add the regenerate-and-diff gate. Append one step to `Makefile` `check-common`
(around line 39/40): run `gencode` (or a fast subset) then `git diff --exit-code`,
failing on any diff (on a clean worktree / copy). Both `check` and `check-ci` inherit
it, so it lands in CI via `.github/workflows/ci.yml`. ~75,670 LoC of committed generated
Rust — the public product — is currently never checked against its generators in
`make check` or CI, so it can silently diverge in either direction (stale generator
output, or an unreproducible hand-patch) and stay green. This class of drift has already
bitten once historically. This single step closes four convergent findings, is the
cheapest high-leverage fix in the assessment, and is the load-bearing integrity control
that ties the dual-generator bet together — and makes future incremental
emission-paydown safe.

## `cst-generated-header`

- **Phase:** A (step 3) · **Class:** major
- **Depends on:** none
- **Refs:** `a5:no-generated-header-cst` (§4); ASSESSMENT §7 item 3

Emit a `@generated` / "Do not edit" header from `gsm2tree_rs.py` `_preamble`, mirroring
`gsm2parser_rs.py:249-251` which already does this for `parser.rs`. Every committed
`cst.rs` (the 15,515-line `crates/fegen-rust/src/cst.rs` and the four fixtures) currently
starts headerless with `use fltk_cst_core::CstError;`, so a 15K-line machine-generated
public-API file carries no in-file signal that it is generated. Combined with the absence
of a drift gate this actively invites the silent hand-patch failure mode; the project
already knows the right pattern (parser.rs has it) and the CST generator just never
adopted it.

## `cargo-deny-in-ci`

- **Phase:** A (step 4) · **Class:** major
- **Depends on:** none
- **Refs:** `a8-build-release-5`; ASSESSMENT §5, §7 item 4

Put the supply-chain gate in CI. `cargo-deny` (RustSec advisory enforcement,
yanked-crate detection, license/source allow-listing) runs only on the local-only `check`
lane via an uncommitted pre-commit hook — never in CI — so a fresh clone, a CI-only
contributor, or a `--no-verify` commit all skip it. Add a CI job (e.g.
`taiki-e/install-action` for cargo-deny, plus a scheduled/weekly run) that runs
`make cargo-deny` on PRs, and add `cargo` and `pip`/`uv` ecosystems to
`.github/dependabot.yml` (which currently covers only `github-actions`), so a new RustSec
advisory in a transitive dep is no longer invisible to all automation.

## `differential-property-harness`

- **Phase:** B (step 5) · **Class:** major
- **Depends on:** gencode-drift-gate
- **Refs:** `a2-parity:no-property-testing`, `a6-tests:no-property-or-fuzz-testing`; ASSESSMENT §5, §7 item 5

Build a differential/property harness to validate cross-backend parse equivalence
beyond the closed 63-entry corpus over 2 grammars (the entire current parse-equivalence
surface, with no property/fuzz/differential testing). Wire random valid+invalid input
generation — and ideally a small grammar corpus including Clockwork's — through the
existing `tests/parser_parity.py` `run_parity_corpus_entry` →
`assert_cst_equal` / `assert_error_equiv`. Add `cargo-fuzz` or a Python-side generator.
Gate it. A real trivia divergence already slipped the hand-picked corpus during
development; for arbitrary out-of-tree grammars the current corpus is sized for fixture
confidence, not parity confidence.

## `regex-portability-lint`

- **Phase:** B (step 6) · **Class:** major
- **Depends on:** none
- **Refs:** `a2-parity:posix-class-divergence`; ASSESSMENT §5, §7 item 6

Add a generation-time regex-portability lint in `gsm2parser_rs.py` that rejects
non-portable constructs (POSIX classes like `[[:alpha:]]`, `\p{}` Unicode property
classes, nested sets, lookaround) at generation time with a clear error. Python `re` and
`regex-automata` are two different engines that produce *different parse trees* for these
constructs with no generation-time error and no test — the compile-only
`all_regex_patterns_compile` gate passes them. Also reword the `gsm2parser_rs.py:6-15`
docstring to describe the engine difference as a hard semantic boundary, not merely a
compile-time restriction, and expand the parity corpus with portable-but-tricky regex
cases.

## `perf-harness`

- **Phase:** B (step 7) · **Class:** major
- **Depends on:** none
- **Refs:** `a7-performance:no-end-to-end-perf-validation`, `a7:per-child-boundary-tax-unmeasured`, `a7:perf-debt-todos-deadlocked`, `a7:sole-bench-is-unwired-stale-pure-rust`; ASSESSMENT §5, §7 item 7

Build a real end-to-end performance harness. The backend exists for speed, yet after
~3 months there is zero Rust-vs-Python measurement and no infrastructure to produce one;
the sole bench (`crates/fltk-cst-spike/benches/traverse.rs`) is pure-Rust, never crosses
the pyo3 boundary, runs against a stale `cp`-duplicated spike CST, and is wired into no
target. Parse a representative grammar/input on both backends, measure wall-time + peak
RSS **end-to-end including Python-side CST traversal** (repeated `children` access, deep
walk — the exact per-child boundary tax the exploration warned could negate the gain,
present and unmeasured), establish a baseline, and wire a loose perf smoke check into a
non-CI lane. This unblocks the perf-debt TODOs (e.g. `extend-children-owned`) that are
self-deadlocked on profiling evidence that is never produced.

## `remove-dead-duplicate-crate`

- **Phase:** C (step 8) · **Class:** cleanup
- **Depends on:** none
- **Refs:** `a8-build-release-3`, `a1:dead-duplicate-crate-and-accreted-inventory`; ASSESSMENT §5, §7 item 8

`git rm -r tests/rust_cst_fegen/` — a fully git-tracked, byte-identical (`cst.rs`
IDENTICAL to `crates/fegen-rust/`) ~17K-LoC dead duplicate with a package/lib/pymodule
**name collision** (`fegen-rust-cst` / `fegen_rust_cst`), on zero build/test/deny/gencode
lanes. It fell off every lane during a refactor and no gate noticed — concrete proof the
hand-maintained per-crate fan-out is itself a drift surface, and a latent module-shadowing
hazard. Fix the stale references it left behind: `CHANGELOG.md:22` (claims gencode
regenerates the orphan's path) and `docs/rust-cst-extension-guide.md:174`.

## `demote-cst-spike`

- **Phase:** C (step 8) · **Class:** cleanup
- **Depends on:** perf-harness
- **Refs:** `a8-build-release-9`, `a1:dead-duplicate-crate-and-accreted-inventory` (spike portion), `u7:merge-demote-spike`; ASSESSMENT §7 item 8

Demote/merge `crates/fltk-cst-spike` into `tests/rust_poc_cst` to kill the
`cp`-duplicated `cst.rs` (kept in sync only by `cp tests/rust_poc_cst/src/cst.rs
crates/fltk-cst-spike/src/cst.rs` in the Makefile) and remove the workspace member whose
`criterion` dev-dep already leaks into the downstream-facing Bazel crate hub
(`TODO(bazel-cst-spike-hub)`). The spike is not dead — it owns the sole traversal bench
and exercises the python-off lane — so this depends on the perf work having relocated any
benchmark worth keeping (perf-harness) before the spike is folded away.

## `document-scope-boundary`

- **Phase:** C (step 9) · **Class:** cleanup (honest scoping)
- **Depends on:** none
- **Refs:** `u7:unparser-absence`, `a2-parity:fixture-feature-gaps`, `a8-build-release-2`; ASSESSMENT §6, §7 item 9

Document the real scope boundary in the consumer guide and CLAUDE.md/TODO.md as
explicit, called-out decisions (not implicit cuts): the Rust backend is **parse + CST
only — no unparser** (`gsm2unparser_rs.py` does not exist; the Python unparser is a
headline `[0.2.0]` feature); the regex subset is a **permanent semantic boundary**; and
INLINE disposition / Invocation terms are unsupported on **both** backends (the Python
parser generator refuses them too at `gsm2parser.py:782-784`), not a Rust-only gap. None
of these currently has a TODO. Also reconcile the three-way version skew
(wheel `0.1.1` vs `fltk-native` `0.1.0` vs runtime crates `0.2.0`) and make the consumer
guide's git/Bazel pin the primary documented path rather than the non-resolving
`version = "0.2"` example.

## `accept-publicapi-divergences`

- **Phase:** C (step 10) · **Class:** cleanup (migration-guide + hardening tests)
- **Depends on:** none
- **Refs:** a3 cluster (`a3:F1-children-snapshot-noop`, `a3:F2-iterator-vs-list`, `a3:F4-span-hand-in`, `a3:F5-positional-match`, `a3:F6-span-union-cast`), `a4-correctness-safety:F3-deep-tree-drop-eq-untested`, `a6-tests:deep-tree-drop-eq-untested`, `a6-tests:children-snapshot-trap-untested-as-divergence`; ASSESSMENT §7 item 10

Accept the adversarially-downgraded public-API divergences as **migration-guide items,
not code changes**: children-snapshot in-place no-op, `children_<label>` iterator-vs-list,
span hand-in asymmetry, positional `match` break, and the span-union cast. Optionally
tighten the protocol `children` annotation toward a read-only sequence type — a
deliberate, called-out change — to steer consumers toward the sanctioned
insert/remove_at/replace_at/clear mutators. Add the cheap hardening tests the verified
findings recommend: a deep-tree (~50–100k node) Drop/eq/Debug stack-safety regression test
(the iterative worklist machinery exists precisely to prevent an uncatchable
stack-exhaustion abort on attacker-controlled depth, yet no test exercises it at depth, so
a regression to naive recursion would pass CI green), and pinned tests for the known
divergences so each becomes a contract rather than an accident.

## `clockwork-committed-pin-proof`

- **Phase:** D (step 11) · **Class:** major (the actual drop-in proof)
- **Depends on:** fix-forged-abi-segfault, gencode-drift-gate
- **Refs:** `a8-build-release-6` (`verify-pyo3-ext-module`), `a8-build-release-7`; ASSESSMENT §7 item 11

Flip Clockwork from its temporary `local_path_override` (a live local checkout, marked
`TODO(fltk-pin-finalize)`) to a **committed git pin** and run its
`clockwork_rust_roundtrip_test` against it once, end-to-end, as the actual drop-in proof
— the Rust-Bazel path has never run through the git-fetch code path real consumers use.
Add a minimal Bazel CI smoke job (`bazel build //:native` plus
import-under-clean-interpreter / `ldd | grep -v libpython`) to close
`verify-pyo3-ext-module`: it is currently unproven that the Bazel-built cdylib has
`extension-module` active and therefore does not link libpython, and Bazel has zero CI.

## `ship-opt-in-first-consumer`

- **Phase:** D (step 12) · **Class:** strategic (the ship decision)
- **Depends on:** fix-forged-abi-segfault, gencode-drift-gate, cst-generated-header, cargo-deny-in-ci, differential-property-harness, regex-portability-lint, perf-harness, clockwork-committed-pin-proof
- **Refs:** ASSESSMENT §1 verdict (`refine-then-ship`), §7 item 12

Ship the Rust backend **opt-in to a deliberate first consumer**, with the Python
backend remaining co-equal and first-class, as a parse+CST backend (unparser explicitly
out of scope). This is the realization of the `refine-then-ship` verdict and depends on
the Phase-A blocker/integrity gates, the Phase-B validation foundations, and the Phase-D
committed-pin drop-in proof being in place. Cleanup items (Phase C) are release-engineering
quality, not hard ship gates, but should accompany the rollout.

## `emission-ir-decision`

- **Phase:** D (deferred strategic decision) · **Class:** strategic (deferred)
- **Depends on:** gencode-drift-gate
- **Refs:** ASSESSMENT §6 (the Strategic Question), §2(c), §7 item 12; `a1:dual-string-emitting-generators`, `a5:string-emission-no-iir` (§1/§2)

**Decide the emission-IR question — deferred to its natural forcing function: the day
the Rust unparser is scheduled.** The dual string-emitting generators with no shared IR
are real debt (the per-label accessor quintet is hand-emitted three times in Rust vs once
in Python; the Rust tree generator is 2,351 LoC vs 1,026 for the same semantic output;
direct emission manufactured a ~250-line collision subsystem and pervasive lint-suppression
emission) but were adversarially **downgraded to minor** — the public type-annotation axis
is mechanically pyright-gated against the single-sourced protocol, and grammar
interpretation is single-sourced. The IR was rejected twice (2026-05-25, 2026-06-10) on
cost. **Do not refactor it as part of shipping.** Revisit precisely when the Rust unparser
is started: that is when a third string-emitting generator would otherwise triple the
duplication, and the moment to either pay down the duplication incrementally or build the
IR once, whichever the cost analysis then favors. The deferral is safe only **because the
gencode-drift gate exists** — that gate is the refactor's own safety precondition, which is
why this item depends on `gencode-drift-gate` and is otherwise held until the unparser
forcing function arrives.
