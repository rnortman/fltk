# Position Paper — The Pragmatic Long-Term Owner

**Lens:** I will own this code for years and ship it to real out-of-tree consumers. My job is
to pick the path with the best risk-adjusted total cost of ownership, weighting downstream-compat
risk and the reversible/irreversible boundary. I do not get to walk away after the demo.

**Verdict: `refine-then-ship`.**

Concretely: this is a sound foundation carrying a thin layer of removable prototype residue and two
genuine, narrow correctness defects. The architecture is *not* the problem — the safety property
gaps and the missing reproducibility gate are, and both are cheap relative to the asset they protect.
Restarting or doing a large refactor would burn the one expensive, irreversible thing that already
exists (a working, tested, native-Rust CST + parser with a load-bearing cross-backend equality
contract) to chase costs that are small and bounded.

---

## 1. Why not `restart`, and why not `targeted-refactor`

The single most important fact for an ownership decision is **what is expensive and irreversible**,
because that is what a restart throws away and a refactor risks. Three things here are expensive and
already paid for:

1. **A working native Rust runtime with no safe-code UB.** Per the runtime audit (u2-runtime-arch),
   `shared.rs`, `registry.rs`, `span.rs`, `memo.rs`, `terminalsrc.rs`, and all of `fltk-native/src`
   contain **zero `unsafe`**; the entire unsafe surface is *3* `cast_unchecked` blocks confined to
   `cross_cdylib.rs`. The python / no-pyo3 feature split is real and mechanically proven
   (`check-no-pyo3`, Makefile:155-175). This is the part that is genuinely hard to get right in Rust,
   and it is right.

2. **A load-bearing, *tested-and-gated* cross-backend drop-in contract.** The single generated
   protocol module (`fltk_cst_protocol.py`) is the one source of truth both backends conform to,
   and conformance is enforced at the pyright gate, not by hope (verified in the adversarial note on
   `a1-architecture:dual-generator-no-shared-emission-abstraction` — the `.pyi` is regenerated from
   the live generator and asserted to produce zero pyright errors against the single-sourced
   protocol). The annotation surface — the axis CLAUDE.md cares most about — is mechanically anchored.

3. **A green, well-instrumented gate.** `make check` passes end-to-end (u6-build-health): 1700 Python
   tests, ~220 Rust tests, clippy `-D warnings` clean across the full python-on/python-off matrix,
   cargo-deny clean on 5 manifests. This is not "green because nothing runs."

A **restart** would re-derive all three from scratch and re-introduce the risk that they are currently
*known* to be free of. There is no finding in the entire corpus that says the architecture is
structurally unsound — the harshest architecture finding
(`a1-architecture:dual-generator-no-shared-emission-abstraction`) was downgraded to **minor** on
adversarial verification precisely because the most dangerous failure mode it posited (silent
annotation drift) is refuted by the conformance gate. You do not restart a codebase whose worst
architecture critique is "minor, code-duplication / maintainability."

A **targeted-refactor** (e.g. retrofitting the rejected "Path 3" neutral codegen spec to single-source
the duplicated emission) is the *seductive wrong answer* for an owner. The dual-generator duplication
is real (the per-label quintet is hand-emitted 3x in Rust vs 1x in Python), but:
- It is a **maintenance tax, not a correctness hole** — severity minor after verification.
- The IIR-rejection that produced it was argued *twice* on the merits (05/25 and 06/10), and the
  06/10 `design.md` concretely refutes the "RefType for free" premise the refactor would rely on
  (u1-intent-history §2.1). Re-litigating a twice-decided, well-reasoned architecture bet is high-cost,
  high-churn work that touches the most stable, most tested surface in the project.
- The refactor's payoff is *future* maintainability; its cost is *present* risk to a working public-API
  generator. For an owner, that trade is backwards until the cheaper controls (below) are in place to
  catch any regression the refactor itself introduces.

So: refine the prototype into a product. Do not rebuild it, and do not re-architect the part that works.

---

## 2. What "refine" must contain before I ship (the must-fix list)

These are the items I would block a release on, ordered by severity. All are narrow and bounded.

### 2.1 The one true blocker — fix it, it's cheap (`a4-correctness-safety:F1-forged-abi-markers-segfault`)
A pure-Python object with two forged attributes, passed to the **public** `Span._with_source_unchecked`
classmethod, reaches `cast_unchecked` and produces a **reproducible SIGSEGV** (verified live, 4/4 runs,
`span.rs:444-453` → `cross_cdylib.rs:112`). The pure-Python backend it replaces is memory-safe here;
this is a *new* public-method UB surface on the normal generated-code path, in exactly the multi-cdylib
scenario that is FLTK's stated primary use case. For a library shipped to out-of-tree consumers — where
a buggy downstream caller or a fuzzer, not just a malicious actor, hits the public API — a publicly
reachable segfault is not shippable. The fix is a defensive native-instance check before the cast (the
ADR for the span path establishes that a naive isinstance check is wrong because a legitimate *foreign*
cdylib SourceText has a distinct type object, but a "is this an actual pyo3 native pyclass, not a plain
Python object whose markers live in `__dict__`" check closes the pure-Python forgery path while still
accepting genuine foreign objects). Days of work, not weeks.

### 2.2 The reproducibility gate — the highest-leverage process fix
Multiple independent findings converge on the same missing control:
`a1-architecture:no-automated-gencode-drift-gate`, `a5-quality:no-regen-drift-gate`,
`a6-tests:no-gencode-drift-gate`, `a8-build-release-4` — all **major**, all verified. ~75,670 LoC of
committed generated Rust (I confirmed: `git ls-files | grep -E '(cst|parser)\.rs$' | xargs wc -l` →
75670) is the *public product*, yet neither `make check` nor CI ever runs `gencode` + `git diff
--exit-code`. The gencode target's own comment (Makefile:245-246) concedes drift detection is manual.
This is the control that ties the whole dual-generator bet together: it is the only thing that makes
"the committed artifact equals what the generator produces" a *guaranteed* property instead of a hoped
one. It defends both directions — generator regression against stale committed code, and unreproducible
hand-patches. The fix is one step appended to `check-common` so both lanes inherit it (the Makefile's
own anti-drift rule, lines 27-32, already enforces that discipline). This is the cheapest
high-leverage fix in the entire assessment and I would not ship without it.

### 2.3 The differential-testing gap — close it before claiming "drop-in for arbitrary grammars"
`a2-parity:no-property-testing` / `a6-tests:no-property-or-fuzz-testing` (both **major**, verified):
cross-backend equivalence rests on **63 hand-picked corpus entries over 2 grammars**, with no
property/fuzz/differential harness. This matters because every *concrete* divergence the assessment
found is exactly the kind a differential harness surfaces automatically and a fixed corpus
structurally cannot — and the project's own ADR record shows a real trivia divergence already shipped
and was caught by manual investigation, not a test. The remediation is additive (a gated differential
test that generates conforming + malformed inputs per grammar and runs the existing
`assert_cst_equal` / `assert_error_equiv`), and it directly de-risks the near-drop-in claim that is
the backend's entire reason to exist. This is the finding most likely to *promote* a latent
correctness defect into the open before a consumer hits it.

### 2.4 The regex-engine divergence — guard it at generation time (`a2-parity:posix-class-divergence`, **major**)
Two regex engines (`re` vs `regex-automata`) silently produce different parse trees for POSIX classes,
Unicode property classes, and some `\d/\w/\b` cases — empirically reproduced (`[[:alpha:]]+` matches
"hello" on Rust, `None` on Python), with no generation-time error and no parity coverage. The
documented mitigation (the parity corpus) provably does not exercise the divergent surface. The fix is
a generation-time lint that rejects non-portable regex constructs with a clear error, turning a silent
wrong-parse into a loud "this grammar is not portable to the Rust backend." Bounded and well-understood.

### 2.5 Delete the dead duplicate and fix the stale pointers (`a8-build-release-3`, **major**; `a1-architecture:dead-duplicate-crate-and-accreted-inventory`)
`tests/rust_cst_fegen/` is a git-tracked, byte-identical (I confirmed `diff -q` reports IDENTICAL) dead
duplicate of `crates/fegen-rust/` — ~17K LoC, on zero build lanes, with a latent package+lib+pymodule
name collision and a committed `Cargo.lock` outside every cargo-deny scan. `CHANGELOG.md:22` points at
the wrong path. This is `git rm -r` plus two one-line doc fixes. It is the clearest possible signal that
the hand-maintained per-crate fan-out is itself a drift surface, and it is free to remove.

### 2.6 Honestly document the scope boundary (synthesizes u7-completeness-cruft)
The backend is **parse-only**: there is no Rust unparser (`gsm2unparser_rs.py` does not exist), and the
parser rejects INLINE disposition, Invocation terms, and lookahead/lookbehind regex with
`NotImplementedError`. *Note carefully:* the INLINE and Invocation "gaps" were **refuted** as
parity claims — the Python parser backend also rejects them, and Invocation is never produced by any
grammar loader (see the two refuted `a2-parity:fixture-feature-gaps` /
`a1-architecture:rust-parser-hard-feature-holes` notes). So the real, owner-relevant boundary is
narrower than the raw understanding-index suggests: **(a)** no unparser, so consumers who use FLTK for
formatting/source-rewriting cannot migrate; **(b)** the documented-permanent regex subset. Both are
legitimate, defensible scope cuts — but per CLAUDE.md they must be *called-out decisions*, not implicit
surprises. The fix is a published compatibility matrix + TODO(slug) entries, so a consumer reading the
ledger does not underestimate the parity distance. This costs words, not code.

---

## 3. What I explicitly accept as residual (ship with these, with notes)

An owner ships with documented residual risk rather than gold-plating. The following are real but
correctly calibrated to **minor/nit** and do not block:

- **The cross-cdylib unsafe sentinel** (`a1-architecture:multicdylib-unsafe-rests-on-unenforced-invariant`,
  downgraded to minor): the size-preserving layout-reorder residual is *proven non-constructible* for
  these frozen/abi3 types, the gate fails closed and is tested on the real two-cdylib path, and it went
  through a dedicated security ADR. This is a documented accepted-risk, not a live hole. (2.1 is the
  separate, genuinely-live forgery path on `_with_source_unchecked` — fix that one.)
- **Public-API behavioral divergences** — children in-place mutation no-op
  (`a3-publicapi:children-inplace-mutation-noop`), `children_<label>()` list-vs-iterator
  (`a3-publicapi:children-label-iterator-vs-list`), span hand-in asymmetry
  (`a3-publicapi:span-handin-asymmetry`), missing `__match_args__`
  (`a3-publicapi:positional-match-args-missing`): **all four were adversarially downgraded to minor**
  because each is a documented, deliberate decision with a sanctioned alternative path, and the
  idiomatic / annotated consumer path works cross-backend. They belong in a migration guide, not a
  release blocker. I would, however, tighten the protocol's `children` annotation toward a read-only
  type and pin each divergence with an asserting test
  (`a6-tests:children-snapshot-trap-untested-as-divergence`) so it becomes a *contract* rather than an
  accident — cheap hardening, not gating.
- **No end-to-end performance measurement** (`a7-performance:no-end-to-end-perf-validation`, major but
  non-blocking): the motivating premise is unvalidated and there is no infrastructure to validate it.
  This is real, but the deliverable was *re-scoped to backend selectability* (verified against the
  Phase-4 requirements), and a co-equal Python backend remains. I would build the comparative harness
  early in the post-ship backlog so a consumer migrating "for speed" can self-serve the answer — but I
  would not hold a *correctness-complete* selectable backend hostage to a benchmark.
- **Supply-chain (`a8-build-release-5`) and Bazel/multi-platform CI gaps (`a8-build-release-6/7/8`):**
  real posture gaps (cargo-deny runs nowhere in CI; the only downstream consumer pins via a temporary
  `local_path_override`). These are pre-1.0 release-engineering items, cheaply fixed (add cargo-deny to
  a CI job; flip Clockwork to a committed SHA and run its roundtrip once), and appropriate to sequence
  *as part of* the first real release rather than gate the decision.

---

## 4. Concrete sequencing

**Gate 1 — Correctness & integrity (block release):**
1. Fix the `_with_source_unchecked` forgery → segfault (2.1).
2. Add `gencode && git diff --exit-code` to `check-common` (2.2). Do this *first among the cheap items*
   so every subsequent change is protected by it.
3. `git rm -r tests/rust_cst_fegen/`; fix `CHANGELOG.md:22` and the guide reference (2.5).
4. Generation-time regex-portability lint (2.4).
5. Emit a `// @generated … Do not edit.` header from `gsm2tree_rs.py` to match the parser generator
   (`a5-quality:no-generated-header-cst`).

**Gate 2 — Confidence (block "drop-in for arbitrary grammars" claim, not the prototype ship):**
6. Gated differential/property harness over multiple grammars incl. Clockwork's (2.3).
7. Add the deep-tree Drop/eq/Debug stack-safety regression test
   (`a4-correctness-safety:F3` / `a6-tests:deep-tree-drop-eq-untested`) — the worklist defense is
   correct but unguarded against regression; one cheap test makes it a contract.
8. Pin the known cross-backend divergences with asserting tests; publish the compatibility matrix (2.6).

**Gate 3 — Release engineering (concurrent with first real downstream pin):**
9. cargo-deny in CI + Dependabot for cargo/pip; a minimal Bazel build + import smoke job; flip
   Clockwork to a committed pin and run its roundtrip once end-to-end.
10. Resolve version skew (`a8-build-release-2`), demote the spike, build the perf harness.

**Deliberately deferred:** the neutral-codegen-spec refactor. Re-evaluate *only after* Gates 1-2 give
us the drift gate + differential tests that would make such a refactor safe — and even then, only if the
maintenance tax is empirically biting, not preemptively.

---

## 5. Strongest counterargument against my own position

The honest case against `refine-then-ship` is the **scope-and-discipline trajectory** documented in
u1-intent-history, and it is not weak. This project *silently re-scoped* far beyond its disciplined
5-phase plan: the "nominal/throwaway" CST was re-architected mid-flight (4c8f0ad), a whole unplanned
parser subsystem appeared, a third generated artifact was invented to repair a self-inflicted
annotation regression (214dbe1, a real CLAUDE.md violation that shipped before recovery), the stated
primary deliverable (general user-facing Rust CST via plumbing) was deferred to a test-only selector,
Phase 5 dogfooding never ran, and the structural churn continued *right up to HEAD* (the `_native`
relocation is dated 06/14). A pragmatic owner should be alarmed when a subsystem is still
re-shaping its own boundaries on the day of the assessment: it suggests the design has not converged,
and "refine-then-ship" risks blessing a moving target. The drift surface has *grown, not shrunk*, over
three months — and my "cheap, bounded" fix list assumes that trajectory stops, when the evidence is
that it keeps generating new deferred work (the TODO burndowns repeatedly found accreting items). A
defensible alternative reading is `targeted-refactor`: pay down the dual-generator duplication and
collapse the crate sprawl *now*, while the institutional memory is fresh, rather than locking in the
duplication as permanent foundation and accepting an ever-growing N-site hand-edit tax for the life of
the product.

**Why I still hold refine-then-ship:** the counterargument is about *process trajectory and
maintainability*, not *present soundness*. Every architecture finding that survived adversarial
verification is minor; every major finding is either a narrow correctness defect with a bounded fix, a
missing *process control* (the drift gate — which is itself the convergence-forcing mechanism the
counterargument wants), or a release-engineering gap. The churn is the signature of a prototype
*finishing*, and the correct response to "the boundaries are still moving" is to **install the gates
that stop them moving silently** (the drift gate, the differential harness, the compat matrix), not to
restart the part that already works or to bet a large refactor on a twice-rejected architecture before
those gates exist. Refine-then-ship *is* the convergence plan; the refactor is a wager I'd only place
after the prototype has been made honest.
