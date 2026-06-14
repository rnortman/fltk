# Position Paper — Ship-It Advocate

**Author lens:** Ship-It Advocate (one of three panelists)
**Verdict:** `refine-then-ship`
**HEAD:** c0182064e2f6906fb5cf836b025980beca44cab3

---

## Headline

The Rust backend is a real, working, well-instrumented system that is one bounded
safety fix and a short list of mechanical CI/cleanup chores away from production —
**not** a prototype to throw away. The bones are sound: a single shared grammar
model, a green-everywhere gate, a genuine cross-cdylib pyo3 isolation story, and a
tested cross-backend parity surface. Restarting or refactoring the architecture
would discard a large amount of verified-correct engineering to chase risks that the
panel's own adversarial pass repeatedly down-graded from "blocker/major" to "minor."
Fix the one true blocker, close the cheap process gaps, scope the parser honestly,
and ship.

---

## The case for shipping (grounded in verified findings)

### 1. The thing actually works, and the gate proves it — today, reproducibly.

This is not "green because nothing runs." The live ground-truth measurement
(`u6-build-health.md`) found `make check` passing **exit 0 in ~59s**, with **1700/1700
Python tests passed, 0 skipped, 0 xfail, 0 warnings**, **~220 Rust tests** across the
python-on and python-off lanes, **zero `#[ignore]`d tests**, and **zero clippy warnings
under `-D warnings`** across the full feature matrix — verified against a *cache-busted
recompile*, not a stale cache. A cold `cargo clean` + rebuild reproduces green. The
pyo3-absence proof (`check-no-pyo3`) mechanically confirms the parser runtime never
links pyo3. For a 3-month prototype, "everything builds and everything is green,
reproducibly" is the single most important production signal, and it is present.

### 2. The architecture is not the duplicated-string-soup it looks like — the semantic layer is genuinely single-sourced.

The scariest-sounding risk is "two parallel generators that drift." But the verified
record refutes the dramatic version of that claim. The **grammar interpretation lives
once**: `RustCstGenerator` wraps a real Python `CstGenerator` and delegates every model
decision — rule models, class naming, node-kind members, protocol annotations
(`a1-architecture:dual-generator-no-shared-emission-abstraction`, verify note). Only
the *target syntax* is emitted twice. And the panel **downgraded that finding from
major to minor** on verification, because the most consumer-critical surface — the
**type-annotation/public-API contract** — is *mechanically* conformance-gated: the Rust
`.pyi` is regenerated from the live generator, checked against the single-sourced
`fltk_cst_protocol.py` with pyright asserting **zero errors**
(`test_gsm2tree_rs.py:2329`). Annotation drift produces a *type error*, not a silent
divergence. The behavioral surface is covered by a real cross-backend parity suite that
**actually runs in the gate** (`a4-parity`/`u4`: `make check` builds the fixtures before
pytest, so `importorskip` guards are satisfied). The two refuted "already drifted"
findings (`a1-architecture:dual-generators-have-already-drifted`,
`a1-architecture:rust-parser-hard-feature-holes`) confirm the headline drift narrative
did **not** survive scrutiny: the one cited drift was a private, non-API cache-field
name, and the "Rust refuses INLINE/Invocation" gap is **symmetric** — the *Python parser
generator refuses them too* (`gsm2parser.py:782-784`). There is no Python-vs-Rust parity
asymmetry there.

### 3. The pyo3 isolation and safety engineering is real and disciplined.

The runtime split is sound and verified (`u2-runtime-arch`): `fltk-parser-core` has **no
python feature and structurally never links pyo3**; `fltk-cst-core` gates pyo3 behind a
default-on feature. **All unsafe in the entire runtime is exactly 3 `cast_unchecked`
blocks in one file** (`cross_cdylib.rs:86,112,331`) — everything else (shared.rs,
registry.rs, span.rs, memo.rs, terminalsrc.rs, all of fltk-native) is **zero unsafe**.
The stack-safety design is deliberate: iterative worklist-based Drop/eq/Debug to defend
against attacker-controlled deep-tree stack exhaustion, empirically confirmed working to
80k+ depth (`a4-correctness-safety:F3` verify note). The cross-cdylib ABI sentinel
**fails closed**: the verification of
`a1-architecture:multicdylib-unsafe-rests-on-unenforced-invariant` reproduced that every
realistic skew (wrong ABI string, wrong layout int, missing marker) raises a **clean
`TypeError` before any cast**, and the one residual (size-preserving field reorder) was
shown *non-constructible* for these frozen/abi3 types by a dedicated ADR layout analysis.
That finding was **downgraded to minor**. This is reviewed, tested, accepted-risk
engineering — not a house of cards.

### 4. Parser feature coverage is broad, and the real gaps are honest, documented, and symmetric.

Within parse scope, Rust covers literals, regex, all quantifiers, all separators,
SUPPRESS/INCLUDE dispositions, sub-expressions, direct+indirect left recursion, union
labels, multibyte spans, trivia capture, depth limits, and **byte-for-byte error-message
parity** (`u7-completeness-cruft`). The genuine limitations — INLINE disposition,
Invocation terms, lookahead-regex — are either **symmetric with the Python backend**
(INLINE/Invocation refused on both) or a **deliberate, ADR-documented permanent
decision** enforced by a generated compile test (lookahead-regex). The two parity
findings that tried to frame these as Rust-specific drop-in holes were **both refuted**
(`a2-parity:fixture-feature-gaps`, `a1-architecture:rust-parser-hard-feature-holes`).

### 5. The drop-in contract holds for the idiomatic consumer path.

Every cross-backend "trap" finding was **downgraded to minor on verification** once the
idiomatic path was examined: children in-place mutation
(`a3-publicapi:children-inplace-mutation-noop` — documented, sanctioned mutator API
exists, divergent Python behavior was itself accidental), `children_<label>`
iterator-vs-list (`a3-publicapi:children-label-iterator-vs-list` — the `for`/`list()`
patterns work identically on both backends; only `next()` differs), span hand-in
(`a3-publicapi:span-handin-asymmetry` — the backend-selecting alias works on both;
only a direct `terminalsrc.Span` import breaks), and positional `match` args
(`a3-publicapi:positional-match-args-missing` — the protocol *and* the Rust stub both
reject it at pyright time, and the supported `.kind` idiom works). The `__repr__` and
cycle-leak findings were **refuted outright**. Class names carry **no `Node` suffix**,
label namespaces match, and `==`/hash work across the two enum families. The historical
annotation-strip regression (`214dbe1`) was **already repaired** and is now a nit. The
drop-in promise is intact for a consumer following the documented contract.

---

## What must be fixed before ship (and why it's bounded)

This is `refine-then-ship`, not `ship-as-is`, because of a small, well-defined set:

1. **THE BLOCKER — `a4-correctness-safety:F1`**: `_with_source_unchecked` is a *public*
   classmethod on `fltk._native.Span` that **reproducibly SIGSEGVs** when handed a
   pure-Python object with forged ABI markers. This is a real production blocker — a
   shipping C-extension must not segfault from pure-Python input to a public method.
   But it is **bounded and well-understood**: it is one method, on the cross-cdylib slow
   path, and the fix is a known defensive check (verify the object is a genuine native
   pyclass instance before the cast, not merely that two attributes match). The verify
   note establishes a safe fix exists. This is hours of work, not an architecture
   problem.

2. **The cheapest, highest-leverage process gap — the gencode-drift gate**
   (`a1-architecture:no-automated-gencode-drift-gate`, `a5-quality:no-regen-drift-gate`,
   `a6-tests:no-gencode-drift-gate`, `a8-build-release-4`, all **major**, all the same
   fix): add `make gencode && git diff --exit-code` to `check-common`. One Makefile line
   ties the dual-generator bet together and makes committed-vs-generator divergence a CI
   failure. This is the single best ROI item in the whole assessment.

3. **Supply-chain gate in CI** (`a8-build-release-5`, major): run `cargo-deny` in CI (it
   currently runs only via an uncommitted local pre-commit hook). One CI step.

4. **Mechanical cleanup** (`a8-build-release-3` major + `a1-architecture:dead-duplicate-crate`
   minor): `git rm -r tests/rust_cst_fegen/` (a byte-identical dead duplicate on zero
   build lanes), fix the stale CHANGELOG pointer, add the missing `@generated` header to
   `cst.rs` (`a5-quality:no-generated-header-cst`). All pure deletion/templating.

5. **Honest scope statement**: the Rust backend is **parse + CST only — there is no Rust
   unparser** (`u7`). This is the one place I will not spin: a consumer who uses FLTK for
   *formatting* cannot migrate. The fix is not code — it is **labeling**. Ship the Rust
   backend as a near-drop-in *parser/CST* backend with the unparser explicitly out of
   scope, and the "near-drop-in" claim becomes true for the audience it serves.

Everything else in the verified set is `minor`/`nit`: add a differential/property test
(`a2-parity:no-property-testing`, `a6-tests:no-property-or-fuzz-testing` — real major
test-coverage gaps, but *additive hardening*, not blockers; no live defect demonstrated),
build a perf harness (`a7-performance:*` — the premise is unvalidated, but the backend is
*selectable*, so a consumer can A/B it themselves; nothing is broken), and tighten a few
annotation/representation edges.

---

## The cost of NOT shipping

Restarting (`restart`) throws away a green, reproducible, parity-tested, pyo3-isolated
system over risks the panel itself rated minor. A `targeted-refactor` to introduce a
shared Rust IR (the rejected Path 3) is a *months-long* rewrite of the emission layer to
buy a maintainability improvement the conformance gate already partly delivers — it would
re-litigate a decision rejected twice with documented reasons, and it stops shipping
value for a quarter. Both options pay a large, certain cost to chase uncertain, already-
mitigated risk. The verified findings are dominated by *process* gaps (missing CI steps)
and *additive* gaps (more tests, a perf number) — exactly the class of work you do
*while* a product is in production, not as a precondition for it. The forward-leaning,
honest verdict is: fix the one segfault, add the drift gate and the CI deny step, delete
the dead crate, scope the docs to parse+CST, and ship.

---

## Strongest counterargument against my own position

The most honest case against `refine-then-ship` is the **combination of an unmeasured
premise and a thin oracle**. The backend exists *for performance*
(`a7-performance:no-end-to-end-perf-validation`, major) and after three months **there is
no measurement, and no infrastructure capable of producing one** — so a consumer migrating
"for speed" has zero evidence it pays off, and the per-child pyo3 boundary tax over an
O(n) snapshot (`a7-performance:per-child-boundary-tax-unmeasured`) is exactly the cost most
likely to negate it. Worse, the *only* thing standing between two hand-maintained string
generators and a silent "works-on-Python/wrong-on-Rust" divergence shipped to invisible
out-of-tree consumers is **63 hand-picked corpus entries over 2 grammars with no
property/fuzz/differential testing** (`a2-parity:no-property-testing`,
`a6-tests:no-property-or-fuzz-testing`, both major-and-survived) — and a real trivia
divergence *already slipped that exact net* during development. If you concede that the
backend's entire reason to exist is unvalidated *and* its core correctness guarantee rests
on an admittedly-undersized closed corpus, then "production-ready" is a claim the evidence
cannot yet support, and the defensible verdict slides toward `targeted-refactor`: build the
perf harness and the differential-fuzz gate *first*, prove the premise and the parity, and
only then ship.

My rebuttal: that argument confuses *adopt-it-blindly-for-speed* readiness with
*production-ready-as-a-selectable-backend* readiness. The backend is **opt-in and
co-equal** — nobody is forced onto it, the Python backend remains first-class, and a
consumer can A/B perf themselves with the selector. The perf harness and the differential
test are real, valuable, and should be built — but they are *additive hardening on a
working, green, parity-tested system*, and the right place to do additive hardening is in
production with a deliberate consumer, not as a gate that keeps a finished system on the
shelf for another quarter. Fix the segfault, add the drift gate, scope the docs honestly,
and the system is ready for its first real consumer.
