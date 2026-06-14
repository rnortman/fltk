# FLTK Rust Backend — Production-Readiness Assessment

**Date:** 2026-06-14
**Scope:** The Rust backend added to FLTK over ~3 months (baseline `d1d3452` → HEAD `c018206`).
**Method:** Meta-synthesis of a 7-subsystem deep read, ~40 adversarially-verified findings (every retained finding independently re-checked against source), and a 3-person panel (ship / restart / pragmatic-owner). All claims below are tied to verified findings or directly re-confirmed in source.

---

## 1. Executive Summary & Verdict

**Verdict: `refine-then-ship`. Confidence: medium-high.**

The FLTK Rust backend is **not a throwaway prototype, and it is not yet a product.** It is a genuinely healthy, well-instrumented, parity-tested system sitting on a sound architectural foundation, carrying **one true correctness blocker, a small cluster of cheap-but-mandatory process/release gaps, and a layer of removable prototype residue.** The expensive and hard-to-reverse parts — a zero-unsafe-in-safe-code runtime split along the pyo3 axis, a mechanically type-gated cross-backend drop-in contract, and a green `make check` across the full feature matrix — are done and verified clean. The cheap parts that remain are exactly the kind of work normally finished *during* a controlled production rollout, not before deciding whether to keep the system.

The decisive reasons against the two more drastic verdicts:

- **Not `restart`:** the runtime crates, the python/no-pyo3 structural split, the single-sourced grammar-interpretation layer, and the cross-backend parity harness are sound and hard-won. Nothing in the assessment argues they are wrong; discarding them buys nothing and costs a quarter.
- **Not `targeted-refactor` (yet):** the flagship "two string-emitting generators with no shared IR" complaint is real but was adversarially **downgraded to minor** — it is a maintenance tax, not a correctness hole, because grammar interpretation is single-sourced and the public type-annotation surface is mechanically pyright-gated against a single-sourced protocol. The IR alternative was rejected on the merits **twice** (2026-05-25 and 2026-06-10). Re-litigating it now — before the drift gate and differential tests that would make such a refactor *safe* even exist — is high-churn risk against the most stable surface in the system.

`refine-then-ship` means: fix the one blocker, install the missing gates and the cleanups (all named in §7), document the real scope boundary honestly, then ship as an **opt-in, co-equal, parse+CST** backend to a deliberate first consumer — with the Python backend remaining first-class.

The confidence is "medium-high" rather than "high" for two honest reasons that the verdict explicitly accepts as post-ship work rather than gates: the motivating **performance premise was never measured** end-to-end after three months, and the cross-backend correctness guarantee currently rests on a **closed 63-entry corpus over 2 grammars** with no property/fuzz/differential testing (a real divergence already slipped that net during development). Neither blocks a controlled, opt-in ship; both must be closed before "drop-in for arbitrary downstream grammars" can be claimed without an asterisk.

---

## 2. Direct Answers to the Lead's Three Questions

### (a) Did we build it right?

**Mostly yes on the substance, with one real architectural mis-bet and visible scope drift.**

What was built *right* and is worth defending:

- The **runtime layer** is disciplined. The entire unsafe surface is exactly **3 `cast_unchecked` blocks confined to one file** (`crates/fltk-cst-core/src/cross_cdylib.rs:86,112,331`); everything else — `shared.rs`, `registry.rs`, `span.rs`, `memo.rs`, `terminalsrc.rs`, all of `fltk-native` — is zero-unsafe (u2). The parser runtime **structurally cannot link pyo3** (no `python` feature at all, confirmed via `cargo tree`), so the no-pyo3 guarantee is real, not aspirational.
- The **public-API contract is single-sourced where it matters most.** Grammar interpretation lives once in the shared `CstGenerator` (the Rust generator wraps a real Python `CstGenerator`); the type-annotation surface is generated from one protocol module and **mechanically pyright-gated** (`test_gsm2tree_rs.py:2329`). Annotation drift is a type error, not silence — which is why the headline dual-generator finding was downgraded to minor.
- The **drop-in contract holds for idiomatic use.** Every cross-backend "trap" finding (children in-place mutation, `children_<label>` iterator-vs-list, span hand-in asymmetry, positional `match`) was adversarially **downgraded to minor**, because the documented/aliased/`for`-loop/`.kind` idioms work identically on both backends; the `__repr__` and cycle-leak divergence findings were **refuted**; and the alarming "INLINE/Invocation are Rust-only holes" framing was **refuted** because the *Python parser generator refuses them too* (`gsm2parser.py:782-784`).

Where the build was **not** right:

- **The one architectural mis-bet: direct string emission with no shared IR across two hand-maintained generators.** This is the deepest correct observation in the restart-advocate's case. It manufactured two Rust-only subsystems a structured IR would have absorbed (a ~250-line identifier-collision check with a hand-maintained must-seed-or-shadow invariant, `gsm2tree_rs.py:17-249`; pervasive lint-suppression conditional emission, `:768-938`), and it means the generator **cannot verify its own output** — malformed Rust surfaces as a `rustc` error in a 15,515-line header-less file with no grammar back-mapping. It is debt, not a defect (see §6).
- **Scope drift was real and is the strongest process critique (u1).** The project silently re-scoped past its disciplined 5-phase plan: a mid-flight CST re-architecture (`4c8f0ad`), an unplanned Rust parser subsystem, a third generated artifact (`fltk_cst_protocol.py`) invented to repair a self-inflicted annotation regression that *actually shipped* before recovery (`214dbe1`, a genuine CLAUDE.md violation), a deferred primary deliverable, a never-run Phase 5 dogfood, and structural churn continuing right up to HEAD. The drift surface grew, not shrank.

### (b) Is it production-ready?

**No — but it is close, and the gap is bounded and well-understood.** It is *not* production-ready today for three concrete reasons, in priority order:

1. **One true blocker:** `Span._with_source_unchecked` is a **public `#[classmethod]`** (re-confirmed in source: `span.rs:444`) that reaches `cast_unchecked` from a pure-Python forged object and **reproducibly SIGSEGVs** (verified live 4/4). The Python backend it replaces is memory-safe here. A C-extension that segfaults the interpreter from pure-Python input to a public method is not shippable. (`a4-correctness-safety:F1`)
2. **Missing integrity/process controls** that the architecture *requires*: no regenerate-and-diff gate anywhere (the ~75,670 LoC of committed generated Rust — the public product — is never checked against its generator in `make check` or CI; re-confirmed: no `gencode` in `check-common` or `ci.yml`), and the only supply-chain gate (`cargo-deny`) runs nowhere in CI.
3. **Two unvalidated foundations** behind the "drop-in for arbitrary grammars" claim: zero end-to-end performance measurement, and a closed parity corpus with no differential/property testing plus a known silent regex-engine divergence.

None of these is an *architecture* problem. (1) is hours-to-days. (2) is mechanical CI/Makefile work. (3) is additive (a harness, a lint, more tests) and the bulk of it is the kind of validation a controlled first rollout exists to produce.

### (c) Should we take the learnings and refactor/restart?

**Neither now.** Restart is unjustified — the costly, irreversible substrate is sound. A targeted-refactor of the emission layer is the *right eventual move* but is the **wrong move today**: the duplication is verified-minor, the IR was rejected twice on cost, and — most importantly — **the drift gate that would make incremental paydown safe does not yet exist.** The correct sequence is to install the gates and harnesses first (they are convergence-forcing mechanisms in their own right), ship the parse+CST backend, and **revisit the emission architecture at the natural forcing function: the day the Rust unparser is started.** That is when a third string-emitting generator would otherwise triple the duplication, and it is the moment to pay the IR cost if it is ever worth paying (§6).

---

## 3. Production-Readiness Scorecard

| Dimension | Rating | One-line justification |
|---|---|---|
| **Architecture** | **Adequate** | Runtime split and single-sourced model layer are strong; the no-shared-IR dual emission is real debt but verified *minor* (annotation surface is type-gated, grammar walk is shared). |
| **Cross-backend parity** | **Weak** | Equivalence rests on 63 hand-picked entries over 2 grammars with no property/fuzz/differential testing; a silent regex-engine divergence (POSIX/`\p{}` classes) is unguarded. A trivia divergence already slipped this net. |
| **Public API / downstream compat** | **Adequate** | Idiomatic drop-in holds and is type-gated; all divergences (children mutation, iterator-vs-list, span hand-in, positional match, span-union cast) survived only as *minor* migration-guide items, not churn-forcing breaks. |
| **Correctness / safety** | **Blocking** | One reproducible SIGSEGV from a public method (F1). Otherwise disciplined: 3 unsafe blocks in one file, fail-closed ABI sentinel, iterative worklist Drop/eq confirmed to 80k depth. Blocking solely on F1. |
| **Quality** | **Adequate** | Clean clippy `-D warnings` across the matrix; but no regen-drift gate, generated `cst.rs` lacks a `@generated` header, public surface emitted 3× in Rust, stale pyo3-0.23 workaround baked into the generator. |
| **Tests** | **Adequate→Weak** | `make check` genuinely green (1700/1700 Python, ~220 Rust, 0 skipped/ignored); but no property/fuzz, no Rust line coverage, no gencode-drift gate, and the parity surface silently skips under bare `pytest`. |
| **Performance** | **Weak** | The backend's *reason to exist* has zero end-to-end Rust-vs-Python measurement after 3 months and no infrastructure to produce one; the only bench is unwired, stale, pure-Rust; per-child boundary tax unmeasured. |
| **Build / release** | **Weak** | Reproducibly green locally and well-documented, but: no registry release, downstream pinned via a *temporary* `local_path_override`, zero Bazel CI, `cargo-deny` not in CI, single-platform/single-Python CI, a 17K-LoC dead duplicate crate, version skew across artifacts. |

No dimension is "strong" outright — correctness is gated by F1, and the two validation dimensions (parity, performance) are genuinely thin. But six of eight are "adequate" once the blocker is removed, which is the profile of a refine-then-ship system, not a restart candidate.

---

## 4. Top Strengths (genuinely good — keep these)

1. **The runtime is the crown jewel and is hard-won.** All unsafe is 3 `cast_unchecked` blocks in `cross_cdylib.rs`; the ABI sentinel **fails closed** (skew raises a clean `TypeError` before any cast, verified via subprocess tests injecting wrong version/layout); `fltk-parser-core` *structurally* never links pyo3. The iterative worklist Drop/eq is a real deep-tree-DoS defense, confirmed working to 80k depth. (u2)
2. **The drop-in annotation contract is mechanically enforced, not promised.** A single generated `fltk_cst_protocol.py` is the one source of truth both backends conform to under a pyright gate. This is why annotation drift is a *type error* — the single most important property for a public API consumed by out-of-tree apps, and the reason the dual-generator finding is minor. (u4)
3. **The grammar-interpretation layer is single-sourced.** The Rust generator delegates every model decision (class naming, node-kind members, label namespace, protocol annotations) to a real Python `CstGenerator`. The duplication is in *target syntax emission only*, never in grammar semantics. (u3)
4. **The gate is genuinely healthy.** `make check` exits 0 in ~59s; 1700/1700 Python tests pass with **0 skipped**, ~220 Rust tests pass, **0 `#[ignore]`d tests, 0 clippy warnings** under `-D warnings` across the full python-on/python-off matrix, verified on a cache-busted recompile and a cold rebuild. This is real health, not green-because-nothing-runs. (u6)
5. **The cross-backend equivalence is actually tested *and gated*.** `make check` builds the Rust fixtures before `pytest`, so the parity corpus, mutator-parity, and `python_gsm == rust_gsm` self-host check really run in the gate (the closed corpus is undersized, but it is not a no-op). (u4)

---

## 5. Blocking Items & Major Risks

### Blocking (must-fix before any production use)

| ID | Item | Why it blocks | Fix size |
|---|---|---|---|
| `a4-correctness-safety:F1-forged-abi-markers-segfault` | Public `Span._with_source_unchecked` reaches `cast_unchecked` from a pure-Python forged object → reproducible SIGSEGV (verified live 4/4) | A public method on a `near-drop-in` span class that segfaults the interpreter on bad input is a hard no-ship; reachable by any buggy downstream lib or fuzzer with no Rust-side barrier; the replaced Python backend is memory-safe here | Days — add a genuine native-instance check (not just two attribute values) before the cast; a checked-but-not-identity downcast that rejects plain-Python objects while still accepting genuine foreign-cdylib `SourceText` |

That is the **only** blocker. Everything else below is a major risk to be closed during the refine phase, not a hard stop on the architecture.

### Major risks (close before claiming "production-ready / drop-in for arbitrary grammars")

- **No regenerate-and-diff gate** — four convergent findings (`a1:no-automated-gencode-drift-gate`, `a5:no-regen-drift-gate`, `a6:no-gencode-drift-gate`, `a8-build-release-4`). ~75,670 LoC of committed generated Rust (the public product) can silently diverge from its generators in both directions; CI stays green on stale or hand-patched artifacts. This is the load-bearing integrity control that ties the entire dual-generator bet together. **Cheapest high-leverage fix in the assessment** (one step in `check-common`). This class of drift has already bitten once historically (a regen silently clobbered a hand-cleaned file).
- **Closed parity corpus, no differential/property testing** — `a2-parity:no-property-testing` + `a6-tests:no-property-or-fuzz-testing` (both major, both survived). Equivalence rests on 63 hand-picked entries over 2 grammars; a real trivia divergence already slipped this net during development. For arbitrary out-of-tree grammars this is sized for fixture confidence, not parity confidence.
- **Silent regex-engine divergence** — `a2-parity:posix-class-divergence`. Python `re` vs `regex-automata` produce *different parse trees* for POSIX classes / Unicode property classes / certain `\d`/`\w`/`\b` cases, with no generation-time error and no test. The compile-only gate passes them. Fix: a generation-time portability lint that rejects non-portable regex constructs, plus parity-corpus expansion.
- **Performance premise unvalidated** — `a7-performance:no-end-to-end-perf-validation` (+ `per-child-boundary-tax-unmeasured`, `sole-bench-is-unwired-stale-pure-rust`). The backend exists for speed; after 3 months there is no measurement and *no infrastructure to produce one*. The per-child pyo3 crossing over an O(n) snapshot — the exact cost the exploration warned could negate the gain — is present and unmeasured.
- **Supply-chain gate not in CI** — `a8-build-release-5`. `cargo-deny` runs only in a local pre-commit hook that is itself uncommitted; Dependabot covers only github-actions. A new RustSec advisory in a transitive dep is invisible to all automation.
- **Dead duplicate crate + drift residue** — `a8-build-release-3` / `a1:dead-duplicate-crate-and-accreted-inventory`. `tests/rust_cst_fegen/` is a byte-identical (re-confirmed: `cst.rs` IDENTICAL), git-tracked ~17K-LoC dead duplicate of `crates/fegen-rust/` with a package/lib/pymodule **name collision**, on zero build/test/deny/gencode lanes, with a stale CHANGELOG pointer. It fell off every lane during a refactor and no gate noticed — concrete proof the hand-maintained per-crate fan-out is itself a drift surface.
- **Downstream consumption never validated against a committed ref** — `a8-build-release-7`. The only real consumer (Clockwork) pins FLTK via a *temporary* `local_path_override` to a live local checkout (committed `TODO(fltk-pin-finalize)`); the Rust-Bazel drop-in path has never run through the git-fetch code path real consumers use, and Bazel has zero CI (`a8-build-release-6`).

---

## 6. The Strategic Question: Dual-Generator Tax & Direct-Emission vs Shared IR

**The reasoned call: keep the current dual-emission architecture for now; do NOT refactor it as part of shipping; revisit it precisely when the Rust unparser is started.**

**What is actually true about the tax.** The complaint is real and the restart-advocate states it accurately: the emission layer is duplicated with no shared abstraction. The per-label accessor quintet is hand-emitted **three times inside Rust alone** (`gsm2tree_rs.py:1738` native, `:2039` pymethods, `:377` pyi) versus **once** in Python (`_emit_label_quintet`, `gsm2tree.py:820`); the two parser generators share nothing but a comment; the Rust tree generator is **2,351 LoC vs 1,026** for the same semantic output. Direct string emission manufactured a ~250-line collision subsystem and pervasive lint-suppression emission a structured IR would have absorbed, and the generator cannot machine-verify its own output.

**Why it is nonetheless a `minor` finding, not a refactor trigger.** The adversarial verification is decisive here and corrects the restart-advocate's framing: the **public-API axis CLAUDE.md cares most about — type annotations — is not held "by convention + tests."** It is mechanically conformance-gated. One of the three Rust emissions (the `.pyi`) is regenerated from the live generator and pyright-checked to **zero errors** against the single-sourced protocol. Annotation drift produces a type error. The behavioral surface (native + pymethods) is held by enumerated parity tests — that is the genuine residual exposure, but it is "a missed runtime edge case caught later," not "silent latent public-API equivalence defect." Maintenance tax with a partial safety net is a maintainability concern, not a correctness-integrity hole.

**Reversible vs hard-to-reverse.**

- *Hard-to-reverse (and therefore must be preserved):* the runtime crates, the python/no-pyo3 structural split, the shared grammar-interpretation layer, the parity harness, and — critically — the **generated public symbol names and annotation surface** already consumed by out-of-tree apps. Renaming or re-annotating these is a breaking change per CLAUDE.md. A refactor that touches them is the single riskiest move available against the most stable surface.
- *Reversible (and therefore safe to defer):* the emission *strategy itself*. The grammar front-end is already shared, so a future neutral-spec/IR retrofit (the twice-deferred "Path 3") can target the highest-churn surfaces — the quintet, mutators with byte-equal error text, eq/hash — behind thin Python-AST and Rust-string renderers **without touching grammar interpretation or the public symbol surface.** That it is reversible is exactly why it does not need to be done now.

**Why the IR was rejected twice, and why that judgment should be respected — for now.** Two ADRs (2026-05-25, 2026-06-10) rejected the IR on cost, with the 2026-06-10 design explicitly refuting the exploration's "RefType for free" premise. Those were defensible schedule calls. The restart-advocate's strongest rebuttal is that they were made *when the surface was small and the unparser unwritten* — and the surface has since grown. That rebuttal is correct in principle but **answered by sequencing, not by acting now**: the thing that makes incremental paydown safe (a regenerate-and-diff gate) does not yet exist, and shipping it is item #2 below. Once the drift gate is in place, the duplication can be paid down incrementally and safely, exactly when there is a forcing reason to.

**The forcing function is the unparser.** Confirmed in source: there is **no Rust unparser** (`gsm2unparser_rs.py` does not exist), no TODO for one, while the Python unparser (`fltk/unparse/gsm2unparser.py`, ~73KB) is a large multi-file subsystem and a headline `[0.2.0]` feature. Building it is the next major push and would otherwise add a **third** hand-maintained string-emitting generator. **That is the moment to decide the IR question** — before the duplication triples — not as a precondition for shipping the parse+CST backend that already works. Until then, ship with the unparser explicitly out of scope (a labeling fix, not a code fix).

---

## 7. Recommended Path Forward (ordered, concrete)

Matched to `refine-then-ship`. Sequenced so that the safety blocker and the integrity gate come first, validation second, cleanup third, and the strategic IR decision is deferred to its natural trigger.

**Phase A — Blocker & integrity gates (must precede any production use)**

1. **Fix F1.** In `crates/fltk-cst-core/src/span.rs:444` (`_with_source_unchecked`) and the `extract_source_text`/`cross_cdylib.rs` cast path: add a real native-instance check before the cast that rejects pure-Python objects while still accepting genuine foreign-cdylib `SourceText` (the documented constraint that a same-type identity check is too strict still allows a "is this an actual pyo3 native instance, not a plain Python object with forged attributes" check). Add the segfault-repro as a (subprocess-isolated) regression test. (`a4:F1`)
2. **Add the regenerate-and-diff gate.** Append one step to `Makefile` `check-common` (line 39): run `gencode` (or a fast subset), then `git diff --exit-code`, failing on any diff. Both `check` and `check-ci` inherit it, so it lands in CI via `.github/workflows/ci.yml`. This single step closes four major findings and makes future incremental emission-paydown safe. (`a1/a5/a6:gencode-drift`, `a8-build-release-4`)
3. **Emit a `@generated` header** from `gsm2tree_rs.py` `_preamble` (mirroring `gsm2parser_rs.py:249-251`, which already does), so the 15K-line `cst.rs` files announce they are machine-generated. (`a5:no-generated-header-cst`)
4. **Put `cargo-deny` in CI** (e.g. `taiki-e/install-action` + a scheduled job), and add `cargo`/`pip` ecosystems to `.github/dependabot.yml`. (`a8-build-release-5`)

**Phase B — Validate the two unproven foundations (before claiming "drop-in for arbitrary grammars")**

5. **Build a differential/property harness.** Wire random valid+invalid input generation (and ideally a small grammar corpus including Clockwork's) through the existing `tests/parser_parity.py` `run_parity_corpus_entry` → `assert_cst_equal`/`assert_error_equiv`. Add `cargo-fuzz` or a Python-side generator. Gate it. (`a2/a6:no-property-testing`)
6. **Add a generation-time regex-portability lint** in `gsm2parser_rs.py` that rejects POSIX-class/`\p{}`/nested-set/lookaround constructs at generation time with a clear error, and reword the `gsm2parser_rs.py:6-15` docstring to describe the engine as a hard semantic boundary. Expand the parity corpus with portable-but-tricky regex cases. (`a2:posix-class-divergence`)
7. **Build a real perf harness.** Parse a representative grammar/input on both backends, measure wall-time + peak RSS **end-to-end including Python-side CST traversal** (repeated `children` access, deep walk), establish a baseline, and wire a loose perf smoke check into a non-CI lane. This unblocks the perf-debt TODOs that are currently self-deadlocked on profiling that is never produced. (`a7:no-end-to-end-perf-validation`, `per-child-boundary-tax-unmeasured`, `perf-debt-todos-deadlocked`)

**Phase C — Cleanup & honest scoping (release engineering)**

8. **`git rm -r tests/rust_cst_fegen/`** (byte-identical dead duplicate, name collision, on no lane) and fix the stale `CHANGELOG.md:22` + `docs/rust-cst-extension-guide.md:174` references. Demote/merge `crates/fltk-cst-spike` into `tests/rust_poc_cst` to kill the `cp`-duplicated `cst.rs` and remove the workspace member leaking into the Bazel hub. (`a8-build-release-3`, `a1:dead-duplicate-crate`, `a8-build-release-9`)
9. **Document the real scope boundary** in the consumer guide and CLAUDE.md/TODO.md: the Rust backend is **parse + CST only — no unparser** (an explicit, called-out decision, not an implicit cut); the regex subset is a **permanent semantic boundary**; INLINE/Invocation are unsupported on *both* backends (not a Rust-only gap). Reconcile the three-way version skew (`a8-build-release-2`) and make the consumer guide's git/Bazel pin the primary documented path. (u7, `a8-build-release-2`)
10. **Accept the downgraded public-API divergences as migration-guide items**, not code changes: children-snapshot no-op, `children_<label>` iterator-vs-list, span hand-in asymmetry, positional `match`, span-union cast. Optionally tighten the protocol `children` annotation toward a read-only sequence type (a deliberate, called-out change) to steer consumers to the sanctioned mutators. Add the cheap hardening tests the verified findings recommend: a deep-tree (~50–100k) Drop/eq/Debug stack-safety test (`a4:F3`, `a6:deep-tree-drop-eq-untested`), and pinned tests for the known divergences. (a3 cluster, `a4:F3`)

**Phase D — Controlled rollout & the deferred strategic decision**

11. **Flip Clockwork to a committed git pin** and run its roundtrip test against it once end-to-end as the actual drop-in proof; add a minimal Bazel CI smoke job (`bazel build //:native` + import-under-clean-interpreter / `ldd`-no-libpython) to close `verify-pyo3-ext-module`. (`a8-build-release-6/7`)
12. **Ship opt-in to a deliberate first consumer**, Python backend co-equal and first-class. **Defer the emission-IR refactor decision to the day the Rust unparser is scheduled** — that is the forcing function (§6); with the drift gate (item 2) already in place, the duplication can then be paid down incrementally and safely, or the IR built once, whichever the cost analysis favors at that point.

---

## Panel Adjudication (where they disagreed)

- **Ship-It (refine-then-ship) vs Restart-Advocate (targeted-refactor):** adjudicated **for refine-then-ship.** The restart-advocate's structural diagnosis is correct and is adopted wholesale in §6 — but its prescription (refactor *before* shipping) is rejected because (a) the duplication is verified-minor with the public annotation axis mechanically gated, (b) the IR was rejected twice on cost with the key premise refuted, and (c) crucially, *the refactor's own safety precondition (a drift gate) does not exist yet.* Installing that gate is item 2 here; doing the refactor before it would ship the riskiest possible change against the most stable, out-of-tree-consumed surface. The restart-advocate's real contribution is the **timing**: the IR question is genuinely live and is sequenced to its natural trigger (the unparser), not dismissed.
- **Restart-Advocate's "window closes when the third generator is written":** **accepted, and made concrete.** That is exactly why §6 and item 12 pin the IR decision to the unparser kickoff rather than to "someday." The disagreement is only whether that decision gates *this* ship (it does not) — the parse+CST backend works today and the unparser is unwritten.
- **Pragmatic-Owner (refine-then-ship):** adjudicated **as the spine of this verdict.** Its calibration — exactly one true blocker, the drift gate as highest-leverage fix, IR-refactor as the "seductive wrong answer" to defer, performance as post-ship — matches the verified-finding severities precisely. Its own strongest counterargument (scope drift / non-convergence) is acknowledged in §2(a) and answered the way the pragmatic-owner answers it: every surviving architecture finding is minor, every major one is a narrow defect / missing process control / release gap, and **installing the gates IS the convergence-forcing mechanism** — a better answer than a large refactor on a twice-rejected architecture before those gates exist.
- **The unanimous core across all three personas** — F1 is the one bounded blocker, the drift gate is the cheapest high-leverage fix, the dead duplicate must go, and the runtime/contract foundation is sound and worth keeping — is the high-confidence backbone of this report. The genuine residual uncertainty (reflected in "medium-high" not "high") is confined to the two unmeasured foundations (performance, differential parity), which the verdict deliberately treats as Phase-B refine work rather than ship gates, on the explicit basis that the backend is opt-in and co-equal.
