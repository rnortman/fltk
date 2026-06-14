# Position Paper — The Restart/Rework Advocate

**Author lens:** Restart/Rework Advocate (3-person decision panel)
**Recommended verdict:** `targeted-refactor`
**Date:** 2026-06-14

---

## Headline

The prototype was a success — as a prototype. It proved the hard things are
possible (pyo3-wrapped native CST, a no-libpython parser runtime, byte-equal
cross-backend behavior) and, more valuably, it surfaced the *one* architectural
decision that is now generating compounding debt: **direct string emission with
no shared IR across two independently-maintained generators.** That decision was
rejected-for-now twice on schedule grounds, accreted a string of Rust-only
subsystems and drift hazards that no one would design on purpose, and is the
common root of nearly every structural finding in this review. The honest move
is not to ship the duplication as permanent load-bearing architecture, and not
to throw away the working runtime — it is a **scoped, deliberate refactor that
unifies the emission layer behind a backend-neutral IR before the public-API
surface grows any further.** We have already paid the tuition; spend it.

---

## Why `targeted-refactor`, not `ship-as-is` / `refine-then-ship` / `restart`

- **Not `ship-as-is` / `refine-then-ship`:** The verified findings are not a list
  of independent polish items — they are *symptoms of one structural cause*
  (string emission + no shared IR + no drift gate). "Refine-then-ship" treats them
  as a checklist; doing so leaves the generator architecture intact and the
  duplication tax compounding with every new node method, disposition, or accessor.
  You cannot "refine" your way out of an emission layer that is hand-written
  three-to-five times per surface.
- **Not `restart`:** A from-scratch rewrite would discard the genuinely sound and
  hard-won parts — the runtime crates, the python/no-pyo3 feature split, the shared
  *model* layer, the parity-test harness — for no benefit. The restart advocate's
  honest conclusion is that the *generators* need re-architecting, not the
  *runtime*. That is a targeted refactor, not a restart.
- **`targeted-refactor` is the calibrated call:** Unify the emission layer behind
  a small backend-neutral codegen IR (the exploration's twice-deferred "Path 3"),
  add the missing drift gate, and prune the accreted prototype residue. Bounded,
  high-leverage, and it preserves the working substrate.

---

## Key points (grounded in verified findings)

### 1. The dual-generator emission layer is structural debt, not incidental duplication

The semantic/model layer is correctly single-sourced — `RustCstGenerator` wraps a
real `CstGenerator` and delegates every grammar decision
(`a1-architecture:dual-generator-no-shared-emission-abstraction`,
`u3-generators`). But the **emission** layer is hand-duplicated with *no shared
abstraction*: the per-label accessor quintet is emitted **three times inside the
Rust backend alone** (native impl `gsm2tree_rs.py:1738`, pyo3 pymethods `:2039`,
`.pyi` stub `:377`) versus **once** in Python (`_emit_label_quintet`
`gsm2tree.py:820`). Add the Python concrete class and the generated protocol and
a single accessor-surface change is a **1-Python + 3-Rust + protocol = 5-site hand
edit**, kept in lockstep "by convention plus pinned tests"
(`a5-quality:n-site-emission-duplication`). The parser generators share *nothing
but a comment* (`gsm2parser_rs.py:697`). This is why the Rust tree generator is
**2,351 LoC versus the Python backend's 1,026** for the *same semantic output* —
2.3x, dominated by string volume the IR would absorb. The maintenance tax is not
hypothetical; it grows monotonically with the public-API surface, which per
CLAUDE.md is the entire product.

### 2. Direct string emission manufactured two Rust-only subsystems a structured IR would have absorbed

`a1-architecture:string-emission-forces-rust-only-subsystems` is the clearest
"we built the wrong thing" evidence in the review. Because the generator emits
into a *flat Rust namespace* with no symbol table, it had to grow a **~250-line
identifier-collision subsystem** (`gsm2tree_rs.py:17-249`): reserved-name tables,
a module-load `if/raise` invariant, a cross-rule claims dict, and the chilling
comment at `:42` / `:108-117` that a *future reserved pyo3/runtime name must be
manually seeded into the tables or a rule name could silently shadow it.* That is
a hand-maintained correctness invariant guarding against uncompilable or
mis-bound output — exactly the class of problem an IIR symbol table solves *for
free, structurally.* On top of that sits **pervasive lint-suppression conditional
emission** (`gsm2tree_rs.py:768-938`): match arms, `Drop` impls, `_` wildcards
emitted-or-omitted by variant count to satisfy `clippy -D warnings`. None of this
complexity is in the problem domain; it is all an artifact of the emission choice.
And because the generator bypasses the IIR, **it cannot verify its own output** —
malformed Rust surfaces as a rustc error pointing into a 15,515-line
header-less generated file with no grammar back-mapping
(`a5-quality:no-machine-verification-of-emitted-rust`).

### 3. The integrity control that ties the dual-generator bet together does not exist

The duplication is "backstopped by tests" — but there is **no automated
regenerate-and-diff gate** anywhere in `make check` or CI
(`a1-architecture:no-automated-gencode-drift-gate`, `a5-quality:no-regen-drift-gate`,
`a6-tests:no-gencode-drift-gate`, `a8-build-release-4`). ~75,670 LoC of committed
generated Rust — the public product — can silently diverge from its generators in
*both* directions: a generator regression passes CI against stale committed code,
and a hand-patched committed `.rs` passes CI while being unreproducible. The
`gencode` target's own comment concedes drift detection is a manual
`git diff --stat`. For a codegen product whose architecture *deliberately
duplicates emission*, byte-level reproducibility from the generator is the load-
bearing integrity property — and it is unenforced. This is not a refinement item;
it is the missing structural control that the dual-generator architecture *requires*
to be safe, and its absence is itself an argument that the architecture is under-
engineered for what it's being asked to carry.

### 4. The drift hazard has already materialized as accreted, un-checkable residue

We don't have to speculate about whether the hand-maintained fan-out drifts — it
*has*. `tests/rust_cst_fegen/` is a **byte-identical, git-tracked, ~17K-LoC dead
duplicate** of `crates/fegen-rust/` (verified: `cst.rs` reports IDENTICAL), with a
package + lib + pymodule **name collision** against the canonical crate, on **zero
build/test/clippy/cargo-deny/gencode lanes**, with a stale `CHANGELOG.md` pointer
(`a8-build-release-3`, `a1-architecture:dead-duplicate-crate-and-accreted-inventory`,
`u7-completeness-cruft`). It fell off every lane during a "promotion" refactor and
no gate noticed — direct evidence that the per-crate hand-maintained Makefile
fan-out (`a8-build-release-10`) is itself a drift surface. The spike crate is
cp-duplicated (`Makefile:288`) and leaks its `criterion` dev-dep into the Bazel
hub (`a8-build-release-9`). Six independent Cargo workspaces, six lockfiles,
~18.3 GiB of build cache. This is prototype sediment that a refactor should clear
and a unified architecture would not have produced.

### 5. The backend is half-built, and the unbuilt half is the hard half — refactor *before* doubling down

The Python backend ships **three** generators: CST + parser + **unparser**. The
Rust backend ships **two** — there is **no `gsm2unparser_rs.py`**, no in-progress
work, and no TODO for one (`u7-completeness-cruft`, verified: file absent). The
Python unparser is a *large* subsystem — `gsm2unparser.py` plus
`combinators/renderer/accumulator/resolve_specs/fmt_config` — and it is a
documented headline [0.2.0] feature. Building the Rust unparser is the next major
push. **That is precisely the moment to fix the emission architecture**, before a
*third* string-emitting generator is hand-written on top of the same flawed
foundation, tripling the duplication tax and the drift surface rather than
doubling it. Refactoring now is cheap relative to refactoring after the unparser
is also duplicated. Layer on the silent feature cuts in what *does* exist —
`INLINE` disposition and `Invocation` terms raise `NotImplementedError`
(`gsm2parser_rs.py:824-826`, `:768-770`), none tracked in `TODO.md` — and the
"near-drop-in" claim is, today, scoped to a subset nobody wrote down.

### 6. The motivating premise was never measured, so we can't even amortize the debt against a payoff

After three months, there is **zero end-to-end Rust-vs-Python measurement** and
**no infrastructure capable of producing one**
(`a7-performance:no-end-to-end-perf-validation`; the sole bench is unwired, stale,
and pure-Rust, `a7-performance:sole-bench-is-unwired-stale-pure-rust`). The
per-child pyo3 boundary tax over an O(n) snapshot clone — the exact cost the
exploration warned could *negate* the speedup — is present and unmeasured
(`a7-performance:per-child-boundary-tax-unmeasured`). A refactor decision is the
right forcing function to also build the harness: you should not pour more
duplicated emission code into a backend whose central justification is unvalidated.
A unified IR makes the eventual answer ("is it worth it?") actionable, because
optimizations stop being 5-site hand edits.

### Sole legitimate blocker is a regression the runtime introduced, not the architecture

For completeness: the one verified **blocker**
(`a4-correctness-safety:F1-forged-abi-markers-segfault`) is a reproducible SIGSEGV
from pure-Python input to a public `_with_source_unchecked` method — a *runtime*
defect, not a generator one. It must be fixed regardless of verdict. I flag it to
be honest, not to inflate the restart case: it argues for fixing the unsafe
surface, which a targeted refactor of the runtime's cross-cdylib story
(`a1-architecture:multicdylib-unsafe-rests-on-unenforced-invariant`) naturally
encompasses.

---

## What `targeted-refactor` concretely means here

1. **Unify emission behind a backend-neutral codegen IR** for the highest-churn,
   most parity-critical surfaces (per-label quintet, mutators incl. byte-equal
   error text, cross-backend eq/hash). Thin Python-AST and Rust-string renderers
   off one spec; the model front-end is already shared, so grammar interpretation
   is untouched. Collapses 5-site fan-out to 1-spec + 2-renderers and gives the
   Rust side a symbol table that makes the collision subsystem structural.
2. **Add the regenerate-and-diff gate** (`gencode && git diff --exit-code`) to
   `check-common` so both lanes catch generator/committed drift and hand-patches.
3. **Prune the residue:** delete `tests/rust_cst_fegen/`, demote/merge the spike,
   generate the per-crate Makefile lists from one variable, emit `@generated`
   headers.
4. **Fix the F1 unsafe blocker** and tighten the cross-cdylib invariant.
5. **Build the perf harness** so the unparser/optimization decisions are evidence-
   driven — *then* write the Rust unparser against the unified IR, not a fourth
   string emitter.

---

## Strongest counterargument against my own position

**The honest rebuttal is that everything I'm calling "structural debt" is, today,
*green and tested* — and a refactor of working code is the riskiest thing you can
do to a system that demonstrably works.** `make check` passes end-to-end (1,700
Python tests, ~220 Rust tests, clippy clean, `u6-build-health`); the annotation
surface — the public-API axis CLAUDE.md cares most about — is *mechanically*
conformance-gated against a single-sourced protocol via pyright, not just
"convention," which is exactly why the lead reviewer **downgraded the flagship
duplication finding to *minor*** (`a1-architecture:dual-generator-...`,
verify-note). The runtime split is *sound*; the parity corpus *runs in the gate*;
the F1 blocker is a localized runtime fix, not an architecture verdict. A
disciplined team can pay down the emission duplication *incrementally* — one
shared quintet driver here, a drift gate there — without a refactor program that
risks regressing a public API consumed by out-of-tree apps who, per CLAUDE.md,
*we cannot even see to test against*. "Refine-then-ship" preserves that working
substrate and de-risks delivery; "targeted-refactor" bets that the duplication
tax will outgrow the team's ability to manage it by hand — a forecast, not a
measured fact. And the most damning point against me: **two ADRs already rejected
the IR approach on cost grounds, twice**, with reasons that refuted the "RefType
for free" claim — so the IR I'm prescribing may be more expensive than the
duplication it replaces, and the team has *already decided* it isn't worth it.

My answer: the rejections were *schedule* calls made when the surface was small
and the unparser unwritten. The surface has tripled, the unparser is still
unwritten, and the drift gate that would make incremental paydown *safe* still
doesn't exist. "Refine-then-ship" without that gate is shipping the duplication as
permanent load-bearing architecture while it's still cheapest to change. The
window to refactor closes the day the third generator is hand-written.
