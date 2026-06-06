# TODO Burndown Triage — 2026-06-06

Style: concise, precise, no padding. Audience: decision-maker who has not read the code.

All 18 real TODOs (excluding `example-placeholder`) validated against source by parallel explorers; orchestrator read every exploration in full and second-guessed framing. Per-candidate explorations live alongside this file as `expl-<slug>.md`.

Recommendation summary (if you say "accept all," this is what happens):

| # | Slug | Recommendation |
|---|------|----------------|
| 1 | pin-ci-actions | **Do** |
| 2 | fegen-cst-rs-single-source | **Do** |
| 3 | extract-rule-name-to-class-name | **Do** |
| 4 | test-class-is-type-body | **Do** |
| 5 | rust-cst-child-span-test | **Do** (reframed) |
| 6 | protocol-label-member-private | **Do** (reframed: option a) |
| 7 | cst-protocol-label-free | **Do** (reframed — fix Python concrete backend) |
| 8 | rust-cst-pyi | **Do** (largest item — consider deferring) |
| 9 | parse-result-typed | **Delete** |
| 10 | cst-protocol-generator-refactor | **Delete** |
| 11 | protocol-label-member-bridge-unify | **Delete** |
| 12 | perf-label-identity-comparison | **Delete** |
| 13 | canonical-name-cache | **Delete** |
| 14 | kind-field-dataclass-eq | **Delete** |
| 15 | rust-cst-shared-rlib | **Delete** |
| 16 | rust-cst-abi-pinning | **Delete** |
| 17 | backend-with-source-signature | **Do** (reframed — unify construction API only) |
| 18 | bazel-rules-rust | **Blocked** |

Net: 9 Do, 8 Delete, 1 Blocked.

Two cross-cutting observations surfaced during validation, independent of any single TODO — see "Loose ends" at the bottom.

---

## DO

### 1. `pin-ci-actions` — **Do**

**Problem.** CI uses three GitHub Actions pinned to mutable refs (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `dtolnay/rust-toolchain@stable`). A mutable ref means "whatever that tag/branch points at when CI runs."

**Why it matters.** If any of those action repos is compromised (or a tag is force-moved), arbitrary code runs in CI and can tamper with build artifacts. `@stable` is a branch — it moves on every Rust release — so it's the worst offender. This is the standard supply-chain hardening every CI should have.

**What the work looks like.** Resolve each ref to its current 40-char commit SHA (`git ls-remote` — needs network), replace the three refs with `@<sha>  # v4` style, and add a `.github/dependabot.yml` with the `github-actions` ecosystem so Dependabot keeps the SHAs updated. The TODO comments already sit at the three sites.

**Case for skipping.** The threat is generic, not specific to FLTK. If you never run untrusted PRs through CI, the urgency is lower.

**Recommendation: Do.** Cheap, real hygiene, no design questions.

USER DECISION: Do.

---

### 2. `fegen-cst-rs-single-source` — **Do**

**Problem.** Two files — `src/cst_fegen.rs` and `tests/rust_cst_fegen/src/cst.rs` — are byte-for-byte identical (confirmed: same md5, 5080 lines) but committed independently. Only the first has a regeneration command; the second must be hand-resynced.

**Why it matters.** After a grammar change you regenerate the first file. Nothing regenerates the second. They silently diverge, and the test crate then tests stale generated code — a drift foot-gun exactly of the "robust as fuck" kind you care about.

**What the work looks like.** Make one the single source of truth. Cleanest option validated: replace `tests/rust_cst_fegen/src/cst.rs` with a one-line Rust `include!("../../../src/cst_fegen.rs")` (resolves at file level, no Cargo workspace, no symlink/Windows/git issues). Symlink and Makefile-copy also work but each has a downside (Windows symlink support; copy step needed from clean checkout).

**Case for skipping.** Only two files, and a `make check` diff-guard would catch divergence without restructuring. If you'd rather a guard than a refactor, that's the lower-touch alternative.

**Recommendation: Do** (via `include!`). Eliminates the drift vector outright instead of merely detecting it.

USER DECISION: Do.

---

### 3. `extract-rule-name-to-class-name` — **Do**

**Problem.** The underscore-snake-case → CamelCase name transform is reimplemented in four places (`gsm2tree.py`, two in `gsm2unparser.py`, `gsm2tree_rs.py`). Three are identical; the fourth (`_rust_variant_name`) silently omits `.lower()`.

**Why it matters.** A behavior change (digit handling, consecutive underscores) must be made in four spots. They've *already* drifted — copy four diverges on uppercase input. Today no input exercises the difference (rule names are lowercase), so it's latent, but it's a live inconsistency.

**What the work looks like.** Extract one helper into a new `fltk/fegen/naming.py` (clean import boundary; `gsm2unparser` is in a different package and shouldn't import `gsm2tree`). Decide the canonical behavior re: `.lower()` and route all four call sites through it. Call sites stay trivial — a function call.

**Case for skipping.** It's a one-liner ×4; some would say four copies of a one-liner isn't worth a module. But the existing drift makes the consolidation more than cosmetic.

**Recommendation: Do.** Reframe: canonicalize the `.lower()` behavior as part of the extraction.

USER DECISION: Do.

---

### 4. `test-class-is-type-body` — **Do**

**Problem.** A test asserts `isinstance(cls, type)` for 14 generated classes. That assertion passes for literally any class — including a wrong/misimported one — so it proves nothing beyond "the import statement ran."

**Why it matters.** It's a test that looks like it checks something (AC-7: classes are real types) but adds zero signal: import success is already enforced by the module-level imports, and construction (`cls()`) is already covered by the AC-8a tests for all 14 classes. Dead-weight tests erode trust in the suite.

**What the work looks like.** Remove the redundant assertion (or the whole `test_class_is_type` method); import + AC-8a already cover both AC-7 and construction. Trivial, no cross-test dependencies.

**Case for skipping.** Harmless as-is; removing it is pure noise reduction, not a fix.

**Recommendation: Do.** Remove the redundant test.

USER DECISION: Do.

---

### 5. `rust-cst-child-span-test` — **Do (reframed)**

**Problem.** No focused test confirms that child-accessor results on a Rust-backed CST node expose `.start`/`.end` — the attributes `fltk2gsm` relies on to slice source text. **The TODO's premise is partly wrong:** the Rust `fltk._native.Span` *intentionally* has no `.start`/`.end`. The objects the accessors actually return are Python `terminalsrc.Span` dataclasses (stored as children), which *do* have them.

**Why it matters.** The end-to-end equality tests exercise this path indirectly. But if a regression changed the *type* returned by `child_name()`/`child_value()` to something lacking `.start`/`.end`, it would surface as a confusing `AttributeError` deep inside the visitor rather than a clean failure. A focused test localizes the regression.

**What the work looks like.** Add one test in `tests/test_phase4_fegen_rust_backend.py`: append a `terminalsrc.Span` child to a Rust-backed node, call the accessor, assert `.start`/`.end` on the **returned `terminalsrc.Span`** (not on a Rust span). Reframing matters — testing the wrong contract would be misleading.

**Case for skipping.** Coverage already exists indirectly; this is a diagnostic-quality improvement, not a gap in correctness.

**Recommendation: Do**, with the corrected contract.

USER DECISION: Do.

---

### 6. `protocol-label-member-private` — **Do (reframed: option a)**

**Problem.** The generated public protocol module emits a class named `_ProtocolLabelMember` at module level. The leading underscore signals "private," but it sits in a file consumers import, shows up in IDE autocomplete, and would be swept in by `from ..._cst_protocol import *`.

**Why it matters.** A downstream consumer could accidentally depend on it, making an internal helper de-facto public API subject to your breaking-change rules. Generated code is public API here, so leaking internals is a real foot-gun.

**What the work looks like.** Option (a): emit an `__all__` in the generated module listing only intended public symbols (the Protocol classes, `NodeKind`, `Span`, `CstModule`), suppressing `_ProtocolLabelMember` from wildcard import. Low blast radius, keeps the generated module self-contained. Option (b) — move the class to a new `fltk.fegen.pyrt.bridge` — breaks the generated module's self-containment (adds a runtime dependency every consumer inherits) and is not recommended.

**Case for skipping.** No in-tree wildcard imports exist today; the risk is latent. The underscore already documents intent.

**Recommendation: Do** option (a) (`__all__`). Cheap, preserves self-containment.

USER DECISION: Do.

---

### 7. `cst-protocol-label-free` — **Do (reframed: fix the Python concrete backend)**

> **This entry was rewritten after investigation.** The original TODO — and the first
> draft of this triage — had the fix direction backwards. Three independent checks
> (a pyright spike, the Protocol generator, and the Rust backend) settle it. Backing
> facts: `expl-cst-protocol-label-free.md`, `expl-label-free-followup.md`,
> `spike-label-free-pyright.md`, `spike-label-free-rust.md`.

**Problem.** For a *label-free* node (a rule whose only included items are `$`-disposition
literals/regexes with no label prefix — e.g. `foo := $"x" , $"y";`; rule references
auto-label, bare terminals suppress, so this is the only way to get one), the three
generated surfaces disagree:

| | `Label` class emitted? | label-slot type | runtime label value |
|---|---|---|---|
| Protocol | no | `None` | — |
| Rust backend | no | opaque, `None` | `None` |
| **Python concrete** | **yes — an empty, memberless `enum.Enum`** | **`Optional[Label]`** | `None` |

The label slot is *always* `None` at runtime (there are no `append_<label>` helpers for a
label-free node). So the Protocol's `None` is the precise type, and the Rust backend agrees.
The **Python concrete backend is the lone outlier**: it emits a dead, uninhabited `Label`
enum and the imprecise `Optional[Label]` annotation.

**Why it matters.** This is a genuine **cross-backend divergence**, which CLAUDE.md treats as
load-bearing — not a cosmetic Protocol asymmetry (the original framing, that "generic
consumers must case-split," does not hold: under a node-type union the label slot resolves
cleanly to `Label | None` and `None` is already handled). Concretely:
- The Python concrete class does not structurally satisfy its own generated Protocol on the
  label-free `children`/`child()` surface (`tuple[Optional[Label], T]` vs `tuple[None, T]`,
  under `list` invariance / return covariance). In the production consumption pattern
  (`cast(CstModule, module)` + member access) this is masked and produces 0 pyright errors —
  so it's latent, not loud — but the surfaces genuinely disagree.
- A pure-Python-backend consumer can reference the vestigial `Foo.Label`; the same code
  breaks on the Rust backend, where no such attribute exists. That's a drop-in-replacement
  hazard against the explicit goal of the Rust work.

**What the work looks like.** Align the **Python concrete generator** (`py_class_for_model`,
`gsm2tree.py`) with what the Protocol generator and the Rust generator already do: guard the
nested `Label` enum on `if labels:` and emit `tuple[None, T]` / `label: None` for the
zero-label case. The Protocol generator already has exactly this conditional; the Rust
generator's `_label_enum_block` explicitly returns `""` for zero labels (noting "Rust enums
cannot have zero variants"). So the fix is porting that established pattern into the one
generator that lacks it. **Rust generator needs no change.** Empirically validated: after the
change the concrete module passes pyright (0 errors), imports, and the label-free
`children`/`child()` mismatch against the Protocol disappears (the only residual is a
pre-existing, label-independent cross-module `kind`/`NodeKind` mismatch handled by the
`CstModule` cast — out of scope here). Good TDD candidate.

**Public-API note (favorable direction).** The change *removes* the generated `Foo.Label`
symbol and *narrows* the `children` annotation for label-free nodes — technically a
generated-symbol removal, so it must be a deliberate, called-out decision per CLAUDE.md. But
the removed symbol is an empty, uninhabited, unreferenced enum, and removing it makes the
Python backend *match* the Rust backend, so the change *improves* cross-backend drop-in
compatibility rather than threatening it. No in-tree grammar produces a label-free node, so
in-tree churn is zero; only out-of-tree label-free grammars are affected.

**Case for skipping.** The path is latent in-tree and masked by the boundary cast in the
production pattern, so nothing is visibly broken today. If you'd rather not touch the
generated public surface for label-free grammars at all, it can wait — but it's a real
cross-backend inconsistency that will bite a Python→Rust migration of code referencing
`Foo.Label`.

**Recommendation: Do.** Small, localized fix to `py_class_for_model`; triple-confirmed
reference behavior (Protocol + Rust); favorable compatibility direction. Not the TODO's
"add a vacuous `Label` to the Protocol" — that's the wrong direction (it would widen the
precise side to match the imprecise one and re-introduce the dead enum). The TODO comment
itself sits in the Protocol generator and should be moved/rewritten to point at the concrete
generator as part of this work.

USER DECISION: Do

---

### 8. `rust-cst-pyi` — **Do (largest item; reasonable to defer this batch)**

**Problem.** There's no static type surface (`.pyi`) emitted for the generated Rust CST extension, and no test that the real compiled PyO3 surface actually satisfies the shared `CstModule` Protocol. Today the Rust nodes cross into typed code via a `cast(...)` that the type checker takes on faith.

**Why it matters.** The cast can mask a genuine mismatch between the Rust extension's real surface and what consumers' typed code expects — a silent type-safety hole on the Rust backend that the Python backend doesn't have.

**What the work looks like.** Two parts: (1) a `.pyi` emitter driven from the same grammar model (~100–200 lines, all needed info is already in the model); (2) a verification test that compiles + imports a Rust extension and runs pyright asserting the surface satisfies `CstModule` without a cast — this part needs the Rust toolchain in the test path and a decision on compile-on-the-fly vs. reuse of a prebuilt extension. Part 2 is the heavier half.

**Case for skipping.** This is the biggest item in the batch and its payoff is "verify a cast isn't hiding a gap." Validation also found the surrounding ADR text overstates the current wiring (see Loose ends), so the area is a little murky — worth cleaning that up first.

**Recommendation: Do**, but it's clearly the largest. Entirely reasonable to defer it out of this batch, or to do only the `.pyi` emitter (part 1) now and file part 2 as a follow-up.

USER DECISION: Do.

---

## DELETE

### 9. `parse-result-typed` — **Delete**

**Problem (as written).** "Make `ParseResult` generic so `result.result` is typed instead of `Any`, eliminating five `cast(...)` calls."

**Why delete.** The TODO is wrong on the facts. The five casts are on `ApplyResult.result` (returned by runtime-`exec`'d parser classes), **not** on `ParseResult.cst` — they're different classes. Making `ParseResult` generic would **not** remove any of those five casts. Worse, `ParseResult` is returned by the public `parse_text()`; making it `ParseResult[T]` forces every out-of-tree consumer who annotates `ParseResult` to rewrite to `ParseResult[SomeNode]` — exactly the wholesale annotation churn CLAUDE.md forbids. And `T` can't even be inferred at the constructor (rule name is a runtime string), so callers would have to supply it manually.

**The real (separate, minor) issue.** The five casts exist because the exec'd parser variable is `Any`. Fixing that is a small, local typing concern unrelated to `ParseResult` and not worth pursuing on its own.

**Recommendation: Delete.** The proposed fix is ineffective and breaks public API.

USER DECISION: Delete

---

### 10. `cst-protocol-generator-refactor` — **Delete**

**Problem (as written).** Unify two pairs of generator functions ("~120 lines of parallel code") behind a shared skeleton.

**Why delete.** Validation found the two class-generators diverge in **seven** structural ways (different base classes, conditional field shapes, different label sub-class kinds, different post-class assignment types, etc.), not just "method bodies." A shared skeleton would need 7+ strategy/mode parameters and would be **harder to read and modify** than the current duplication — the textbook awkward multi-mode helper the burndown guidance warns against. The annotation-pair functions likewise diverge in dispatch logic; unifying saves ~10 lines at the cost of a callback with heavy context needs.

**Narrow alternative (optional).** There's one genuinely shareable piece — the per-label "quintet" accessor loop — which could be extracted on its own to save ~40 lines without the mode-parameter mess. Offer this only if you want it.

**Recommendation: Delete** the unification as framed. (Optional narrow quintet-loop extraction available if you'd rather a small Do.)

USER DECISION: Do the more narrow version.

---

### 11. `protocol-label-member-bridge-unify` — **Delete**

**Problem (as written).** Two cross-backend eq/hash implementations exist (one pygen-based, one via raw `ast.parse` string); unify them so future changes propagate.

**Why delete.** Their cross-type logic is already identical; their same-type fast paths differ **by design** (enum uses `.name`; the non-enum `_ProtocolLabelMember` uses `_fltk_canonical_name` because it has no `.name`). Unifying requires adding parameters (`same_type_attr`, `emit_init`) that make the shared helper **longer** than either current function — no LOC win, more coupling. The only real drift risk is the literal string `_fltk_canonical_name` appearing in both, which is trivial.

**Recommendation: Delete.** Unification is net-negative.

USER DECISION: Delete

---

### 12. `perf-label-identity-comparison` — **Delete**

**Problem (as written).** Label accessors do an O(children) scan with equality compares; identity comparison or pre-grouped storage would be O(1). TODO itself says "defer until profiling."

**Why delete.** No profiling data exists. Worse, the proposed "identity comparison" fix is **incorrect as stated**: the label objects compared are freshly allocated per call, so `is` would match nothing — making it work needs per-variant object caching *and* introduces a cross-backend correctness hazard (a Python-backend label passed via the public `append` would silently fail to match). The pre-grouped-storage alternative breaks the public `children` shape. This is premature optimization with a correctness trap and no evidence.

**Recommendation: Delete.** Re-file with a correct fix shape only if profiling ever shows a bottleneck.

USER DECISION: Delete

---

### 13. `canonical-name-cache` — **Delete**

**Problem (as written).** Rust `__hash__` allocates a fresh `PyString` every call; cache the computed hash per variant via `GILOnceCell`. TODO is explicitly defer-until-bottleneck.

**Why delete.** All claims are accurate, but it's unmeasured perf. The fix adds real codegen complexity — one static per enum variant per grammar (46 in the fegen fixture). Paying ongoing generator complexity for an allocation nobody has shown matters is the wrong trade.

**Recommendation: Delete.** Re-file with profiling evidence if hashing ever shows up hot.

USER DECISION: Delete

---

### 14. `kind-field-dataclass-eq` — **Delete**

**Problem (as written).** The invariant `kind` field participates in node `__eq__`; mark it `compare=False, repr=False` for a small perf win.

**Why delete.** The perf gain is one singleton identity check per same-type equality — negligible (and `kind` doesn't even participate in `__hash__`; nodes aren't hashable). Meanwhile `repr=False` is an **observable change to the generated repr surface**, which CLAUDE.md treats as public-API-adjacent. Not worth a public-surface change for a non-measurable gain.

**Recommendation: Delete.** (See Loose ends for a *separate*, more interesting finding this validation turned up about repr.)

USER DECISION: Delete

---

### 15. `rust-cst-shared-rlib` — **Delete**

**Problem (as written).** "If user extensions ever need to link Rust-level shared types, a `fltk-cst-common` rlib + Cargo workspace is the clean answer. Revisit when that need arises."

**Why delete.** This is a design musing, not actionable work. Validation confirms there is no current trigger: spans cross as opaque Python objects, crates are cdylib-only, and nothing links FLTK's Rust types. It's a "revisit when X" with no X. The idea is preserved in git history / this triage if X ever materializes.

**Recommendation: Delete.** Nothing to do; not worth carrying as a tracked item.

USER DECISION: Delete

---

### 16. `rust-cst-abi-pinning` — **Delete**

**Problem (as written).** No version handshake between a user's Rust CST extension and `fltk._native`; a skewed extension could misbehave silently.

**Why delete.** The framing ("built against an older FLTK") is wrong: user extensions don't link `fltk._native` at compile time at all — they fetch the sentinel at runtime from whatever's installed, so there's **no binary ABI skew vector**. The only residual risk is an ordinary Python-semantic change to `Span`/`UnknownSpan`, and the proposed ABI check would require `fltk._native` to expose a version attribute it doesn't have. Low-urgency, misframed, and the TODO marker isn't even at the cited source site (docs only).

**Recommendation: Delete.** Re-file concretely if/when `Span`'s Python surface actually changes.

USER DECISION: Delete

---

### 17. `backend-with-source-signature` — **Do (reframed — unify construction API only)**

**Problem.** `Span.with_source(...)` takes a raw `str` on the Python backend but a `SourceText` handle on the Rust backend, so the same call can't work against both. A consumer cannot write backend-agnostic span construction today.

**Why it matters.** Calling `with_source` through the backend-selector import hits a `TypeError` when the Rust backend is active — a genuine cross-backend API divergence that cuts directly against the project's "near-drop-in replacement" goal (downstream should not have to branch on which backend is active). Out-of-tree consumers who construct source-bearing spans by hand are the affected parties, and per CLAUDE.md they exist and matter.

**What the work looks like (scoped).** Two things were tangled in the original TODO; only the first is in scope:
1. *Construction-API unification (in scope, do now).* Add a `SourceText` class to the Python backend (`terminalsrc.py`) — a thin wrapper over `str` — and export it from the `span.py` selector (currently `None` on the Python path). Make Python `with_source` accept `str | SourceText` (keeps existing `str` callers working; adds the portable form). **Rust unchanged** — stays `SourceText`-only, per user direction. The portable cross-backend subset becomes `SourceText`. Self-contained, non-breaking.
2. *Source-bearing spans through the parse path + the `.start`/`.end` exposure divergence (OUT of scope).* This is separate, larger future work. It is **not** a blocker for (1) — I previously conflated the two and propagated the TODO's own deferral framing. Decoupled out.

**USER DIRECTION (verbatim):** "I don't understand why we can't just fix backend-with-source-signature right now? The Rust code can keep taking SourceText and the python adapter layer can fix that?" — Rust stays `SourceText`-only; the Python adapter grows the matching `SourceText`. Do not re-litigate the parse-path deferral.

**Constraint / non-goal to carry into the request.** Rust `Span` is `#[pyclass(eq, hash)]` over its fields including `source`. **Cross-backend equality/hash of source-bearing spans is an explicit non-goal** for this slice (Rust `Arc<SourceInner>` vs a Python str-wrapper need not compare equal). No source-bearing spans flow anywhere today, so this is latent — but the implementer must not assume cross-backend source-span equality holds.

**Case for skipping.** No in-tree caller exercises `with_source` today, so the immediate in-tree payoff is zero; the benefit accrues to out-of-tree consumers and to API hygiene. If you'd rather not touch a public constructor signature at all until a real caller appears, defer.

**Recommendation: Do**, scoped to the construction-API unification (item 1). Move the parse-path/`.start`-`.end` work out as separate future work (no longer tracked as a blocker on this TODO).

USER DECISION: Do

---

## BLOCKED

### 18. `bazel-rules-rust` — **Blocked**

**Problem.** Bazel builds don't include the Rust extension; `MODULE.bazel` has no `rules_rust`.

**Why it matters.** Bazel consumers silently fall back to the pure-Python span backend (with a warning) and can't get the Rust CST path.

**What blocks it.** The TODO undersells the scope: there are three independent cdylib crates (not one), no Cargo workspace, and `rules_rust` + PyO3 integration in Bazel is non-trivial (requires `pyo3_bazel` or manual shared-library + feature-flag wiring, plus a new Bazel macro mirroring the generated-Rust-CST workflow). Combined with no current Bazel consumer demand, this is a real chunk of build-system work gated on external `rules_rust`/PyO3 maturity.

**Recommendation: Blocked** on a decision to invest in Bazel-Rust support (and on `rules_rust` PyO3 ergonomics). Existing Python fallback means nobody is hard-broken meanwhile.

USER DECISION: Leave in place

---

## Loose ends (independent of any single TODO)

Two things validation surfaced that aren't owned by any TODO above. Flagging for your call — not part of "accept all."

**A. Stale references around the Rust-CST DI wiring.** ADR `05-cst-type-annotations-regression` (and a comment in `test_cst_protocol.py`) describe a dependency-injection wiring — `Cst2Gsm(..., cst=pr.cst_module)` and a `_DEFAULT_CST` symbol in `fltk2gsm.py` — that **does not exist in the shipped code**. `Cst2Gsm.__init__` takes only `terminals`; both backends just cast and call `visit_grammar`. Either the DI was planned and never implemented, or implemented and removed. Worth a small cleanup of the stale ADR/test text regardless of what you decide on `rust-cst-pyi` (#8), whose framing leans on this wiring.

**B. Cross-backend repr divergence for CST nodes.** The Python backend's node `repr` includes `kind=<NodeKind.X: N>`; the Rust backend's node `repr` omits `kind` entirely. No test enforces cross-backend repr equivalence. This is a latent inconsistency in observable output across backends — a different (and arguably more real) issue than the `kind-field-dataclass-eq` perf TODO (#14). Direction is ambiguous (add `kind` to Rust repr, or drop it from Python), so it needs a decision, not a mechanical fix. Flag only.
