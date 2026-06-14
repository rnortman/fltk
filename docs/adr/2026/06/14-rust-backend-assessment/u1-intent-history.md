# U1 — Rust Backend: Original Intent, Goals, Rejected Alternatives, and Prior-Review History

Map produced for the production-readiness retrospective. All claims anchored to ADR docs and
current source (file:line). Scope: recover what the Rust backend was SUPPOSED to be, the design
bets made, what was rejected and why, and where the code-now has DRIFTED from the plan.

---

## 0. One-paragraph TL;DR

The Rust backend began (2026-05-25) as a deliberately-scoped, 5-phase, **incremental** project
with one stated primary deliverable: `plumbing.generate_parser()` producing **selectable
PyO3-wrapped Rust CST nodes for any user grammar**, explicitly characterized as a "**nominal**"
thin wrapper over Python objects (`span: PyObject`, `children: Py<PyList>`) and an **intermediate
step** — *the parser stays Python, no Rust parser was planned*, Phase 5 ("dogfooding") would
replace `fltk_cst.py`, and there was **no Phase 6**. The codegen approach chosen up front was
**direct string emission** (a parallel `gsm2tree_rs.py`), and the **IIR-based backend was
explicitly rejected** (re-confirmed at 06/10). Over ~3 months the project **silently re-scoped
into a much larger thing**: native Rust CST storage (a full re-architecture of the CST internals
mid-flight, 4c8f0ad), a brand-new **Rust parser runtime + parser generator** (`fltk-parser-core`,
`gsm2parser_rs.py`, never in the original plan), a new **third generated artifact** (the
936-line `fltk_cst_protocol.py` + a load-bearing cross-backend equality contract), several
build-system relocations, and ~10 generated `.rs` copies across fixtures. The **original primary
deliverable was abandoned/transformed** (plumbing AOT-compile workflow was deferred; `fltk_cst.py`
was *never* dogfooded to Rust), while **performance — the implicit original justification — was
never quantified, before or after**. The recurring, never-retired themes across the entire review
chain are: **dual/triple-generator drift**, **the nominal-vs-real Rust backing question**, and
**cross-backend drop-in fidelity under three distinct enum identities**.

---

## 1. Stated success criteria & explicit design principles (original)

### 1.1 The foundational exploration (05/25-rust-backend-exploration)
`synthesis.md` is explicitly decision-support only: "No recommendations -- tradeoffs presented for
human judgment" (`synthesis.md:3`). It laid out **four paths**:
- **Path 1** — Add a Rust IIR compiler backend (reuse `gsm2parser.py`/`gsm2unparser.py` unchanged;
  ~3.3-4.6k new LoC). *Analysis 1's* recommendation (`synthesis.md:51-77`).
- **Path 2** — Per-language generators from GSM ("ANTLR approach"): parallel `gsm2*_rs.py` emitting
  Rust strings; ~5.2-6k LoC; **"~2,550 lines of generator logic duplicated"** and **"dual
  maintenance burden"** flagged up front (`synthesis.md:78-99`, key-numbers table line 148-149).
- **Path 3** — Shared codegen plan + thin renderers (cleanest long-term, but refactors working
  code for no immediate benefit) (`synthesis.md:101-121`).
- **Path 4** — Full Rust reimplementation (10.9-14.8k LoC; rejected as near-impossible to deliver
  incrementally) (`synthesis.md:123-138`).

The synthesis explicitly named **cross-cutting risks that recur for the entire project life**
(`synthesis.md:155-219`): PyO3 nested-enum classes, heterogeneous `children` fidelity, `op="is"`
special-casing, the global `_type_registry` duplicate-key latent risk, and — critically — two
**"Missing from all analyses"** gaps: **(a) no performance characterization / baseline**
(`synthesis.md:213-216`) and **(b) the cost of "near-identical CST interfaces via PyO3" — every
child access crosses the boundary, possibly negating speedup** (`synthesis.md:217-219`).

### 1.2 The chosen first deliverable & its principles (05/25-pyo3-cst-plan/phase-plan.md)
The exploration's chosen first deliverable was **PyO3-wrapped Rust CST nodes** (`phase-plan.md:8`).
Stated principles:
- **Primary deliverable (verbatim):** "`plumbing.generate_parser()` produces Rust-backed CST nodes
  for ANY user grammar." (`phase-plan.md:12`). The self-hosted `fltk_cst.py` replacement was
  **"secondary ... not the goal"** (`phase-plan.md:11`).
- **Permanent Python fallback:** "The fallback is permanent, not a transitional crutch ... The Rust
  path is opt-in for performance." (`phase-plan.md:139`).
- **No forced annotation/call-site churn for consumers** — the whole project inherits CLAUDE.md's
  drop-in mandate.
- **Strictly linear 5-phase plan** (`phase-plan.md:190-211`): Phase 0 infra → Phase 1 Span → Phase 2
  nested-enum PoC → Phase 3 generator → **Phase 4 runtime integration (THE primary deliverable)** →
  Phase 5 dogfood `fltk_cst.py`. **"There is no Phase 6"** for a Rust parser
  (`06-rust-cst-nominal-backend-forensics/README.md:88, 228-229`).

### 1.3 The Rust parser codegen criteria (06/10-rust-parser-codegen) — a LATER, separate goal
A wholly separate effort, two weeks later, set parser goals:
- "fltk generates Rust parsers usable from pure Rust (no pyo3 linked) or from Python."
  (`06/10-rust-parser-codegen/design.md:13`).
- **The CST crosses the language boundary; the parser does NOT** (`README.md:15`). This freed the
  Rust parser API to diverge (deliberate divergences listed: `Parser::new(text, capture_trivia)`,
  `error_message()`/`error_position()` instead of an `error_tracker` field — `README.md:70-82`).
- **Pure-Rust consumers pay no cost for Python**: pyo3 gated behind a `python` feature;
  `fltk-parser-core` **never links pyo3** (structural guarantee, `design.md:81`).
- **No annotation churn**: "the generated CST API (the thing that crosses boundaries) is
  unchanged" (`README.md:79-82`).

### 1.4 The drop-in/cross-backend equality criteria (06/05-clean-protocol-consumer-api + 06/05-cross-backend-label-equality)
- HARD gating criterion (verbatim, `clean-protocol-consumer-api/requirements.md:10-15`): out-of-tree
  consumers must be able to write **clean** code — "No double-importing, no TYPE_CHECKING hacks, no
  `cast`, no `noqa`" forced by the CST. **Substitution of one suppression for another fails the
  gate** (`requirements.md:15`).
- Cross-backend equality contract (`cross-backend-label-equality/design.md`): label/`NodeKind`
  members compare `==` **iff canonical names match**, identically whether the runtime node came from
  the **Python** backend or the **Rust** backend (`requirements.md`/`design.md §2.1`). This is the
  literal "drop-in" promise made mechanically testable.

---

## 2. Alternatives considered and WHY rejected

### 2.1 IIR-based Rust backend vs. direct string emission — REJECTED TWICE
The single most consequential architecture decision. Direct string emission won; the IIR path lost.

- **At exploration (05/25):** `analysis-iir-adaptation.md` argued the IIR could be reused almost
  as-is (~500 lines new Rust compiler, "2,305 lines of generator code reused AS-IS",
  `analysis-iir-adaptation.md:240-243`), and that "RefType becomes meaningful for free"
  (`synthesis.md:13`). The competing `analysis-separate-reimplementation.md` priced direct emission
  (Option A) at 3.65-4.95k LoC but flagged **dual maintenance** ("every IIR evolution must be
  mirrored in both backends", `analysis-separate-reimplementation.md:135, 207`).
- **At parser-codegen decision (06/10):** the IIR path was **formally rejected** with four
  "load-bearing" reasons (`06/10-rust-parser-codegen/README.md:24-44`, `design.md §2`):
  1. **IIR encodes the *Python* CST API** (`RefType`, `NodeRef`, `Optional[NodeRef]` have no Rust
     equivalent) — "the headline benefit (reuse 2,305 generator lines unchanged) evaporates"
     (`design.md:35`).
  2. **Python-shaped ownership** — the literal IIR memoizer body is "three simultaneous `&mut self`
     borrows ... cannot compile" in Rust (`design.md:39-45`).
  3. **"RefType becomes meaningful for free" is FALSE in practice** — `consume_literal` is declared
     `mutable_self=False` yet mutates `self.error_tracker`; an IIR path "requires auditing and
     fixing annotations across the working Python-path generators — exactly the 'untouched existing
     code' the path was supposed to guarantee" (`design.md:48-49`). **This directly refutes the
     exploration's own central claim.**
  4. **Rust needs constructs the IIR cannot represent** (regex `OnceLock` static tables, memo cache
     fields, the `#[cfg(feature="python")]` pyo3 block) (`design.md:51-55`).
- **The accepted cost (acknowledged honestly):** "Two generators that can drift"
  (`README.md:66-68`); ~830 lines of `gsm2parser.py` structural logic re-expressed in
  `gsm2parser_rs.py` (`design.md §2.7`). **Mitigation = parity tests as the contract** ("Drift
  becomes a test failure, not a latent divergence", `design.md:69`).
- **Net:** the project committed to **Path 2 (per-language generators)** — precisely the path the
  exploration flagged as carrying the largest duplication and dual-maintenance burden. This was a
  conscious, reasoned choice, not an accident; but the cost the exploration warned about is now real
  (Section 4).

### 2.2 `children` representation — Option B (Py<PyList>) chosen, then THROWN AWAY mid-project
- **Original choice (analysis-rust-cst-first.md:88-97):** Option B, `children: Py<PyList>`, was
  "the only one that preserves semantics without reimplementing the Python list protocol. The
  performance cost is real but acceptable **for an intermediate step**." The analysis itself called
  the result **"nominal"** ("the 'Rust backing' is nominal", `:223`) and **explicitly predicted it
  was throwaway**: "the Option B approach ... is **throwaway work** for the `children` field"
  (`:234`).
- **What happened (4c8f0ad, ~06/06):** exactly as predicted, the CST was re-architected from
  Python-object storage (`span: PyObject`, `children: Py<PyList>`) to **native** storage
  (`span: Span`, `children: Vec<(Option<Label>, Child)>`)
  (`06/09-todo-burndown-resume/state-of-the-world.md:21`). The forensics report
  (`06/06-rust-cst-nominal-backend-forensics/README.md`) is the full archaeology of this. The
  throwaway prediction came true; the rework was substantial and unplanned in the original 5 phases.

### 2.3 Rejected (and BANNED) consumer-API shapes
- **Per-traversal accessor (e.g. `children_items_with_separators()`) — REJECTED TWICE by the user,
  explicitly "banned", "do not re-propose under a new name"**
  (`clean-protocol-consumer-api/requirements.md:74-77`). Rationale: it solves only the in-tree
  `fltk2gsm.py` walk and leaves out-of-tree consumers without a clean path — "a point solution
  masquerading as generality." The requirements doc documents **why this keeps recurring** (the
  in-tree consumer is the only visible evidence, so authors keep cutting the accessor to its shape).
  → This is a documented **recurring-error pattern** the process had to actively guard against.
- **`@typing.runtime_checkable` + `isinstance`** — rejected (data-member protocols not usefully
  runtime-checkable) (`requirements.md:78`).
- **`TypeIs`/`TypeGuard` predicates as the primary narrowing surface** — rejected for this work;
  native `.kind` discrimination chosen instead (`requirements.md:79`).

### 2.4 Build-backend & misc
- setuptools → **maturin** chosen (standard PyO3 tool) (`phase-plan.md:28`).
- **Bazel Rust support deferred from Phase 0** (`phase-plan.md:30`); `TODO(bazel-rules-rust)` — still
  open/in-progress at HEAD (`TODO.md`, ADR `06/13-rust-bazel-packaging/`).
- Regex: **subset-only** (common subset of Python `re` and Rust `regex` crate; no
  lookaround/backreferences), enforced by a generated `#[cfg(test)]` compile test. `fancy_regex`
  deferred until a concrete need (user A1, `06/10-rust-parser-codegen/README.md:49-61`).

---

## 3. Promises about drop-in compatibility & performance

### 3.1 Drop-in compatibility — the central promise, taken seriously
- CLAUDE.md mandate: near-drop-in; consumers may update imports but **must not** be forced to rewrite
  annotations/call sites; renaming generated public symbols = breaking.
- The cross-backend equality machinery is the concrete realization. It is **intricate and
  load-bearing**: a duck-typed `_fltk_canonical_name` sentinel read off the operand instance, eq/hash
  routed through CPython's *salted* string hash so Python and Rust agree in-process
  (`cross-backend-label-equality/design.md §2.3, §3.1`), and correctness across **THREE distinct enum
  classes** (protocol-module, Python-concrete, Rust-concrete), where `==`/`!=` agreement rests on a
  **single load-bearing invariant**: all three emit the identical canonical string
  (`clean-protocol-consumer-api/requirements.md:100-108`). Object identity (`is`) is explicitly **not**
  part of the contract (`requirements.md:108`).
- **Drop-in regression already occurred** (06/05-cst-type-annotations-regression): the Phase 4 DI
  refactor (214dbe1) **intentionally removed CST-typed parameter annotations from ~11 `visit_*`
  methods** in `fltk2gsm.py` (`README.md` item 2). Restoring them was punted to "a separate, larger
  piece of work" (`README.md:62-72`) — i.e., a real annotation-surface regression was knowingly
  deferred. This is the kind of churn CLAUDE.md warns against, and it drove the invention of the
  protocol module.

### 3.2 Performance — promised in spirit, NEVER quantified (before OR after)
- The implicit justification was always "Rust speed", but the exploration flagged **no baseline
  exists** (`synthesis.md:213-216`) and warned PyO3 boundary-crossing could **eat** the speedup
  (`synthesis.md:217-219`).
- The phase plan's **Risk R5** conceded Rust CST nodes "may be *slower* than Python dataclasses due to
  FFI overhead ... No baseline profiling data exists ... **trades performance for infrastructure
  establishment**" (`phase-plan.md:243-245`).
- The forensics report confirms: "**No analysis quantifies the current Python performance bottleneck
  or estimates the speedup**" (`06/06-rust-cst-nominal-backend-forensics/README.md:231-235`).
- **Assessment:** after ~3 months, there is still no evidence in the ADR record of a measured
  end-to-end speedup. Performance was the motivating premise and remains unvalidated. (Several
  later items — `rust-cst-accessor-clone-efficiency`, `span-source-as-py-crosscdylib`,
  `extend-children-owned` — are *micro*-efficiency fixes, not end-to-end perf validation; the last
  is even gated "Re-open only with profiling evidence" in `TODO.md`.)

---

## 4. Where reality (code now) has DRIFTED from the plan

| Original plan | Reality at HEAD c018206 | Evidence |
|---|---|---|
| **Primary deliverable: `plumbing.generate_parser()` makes selectable Rust CST for ANY user grammar** via an AOT compile workflow | plumbing.py gained only a `rust_fegen_cst_module=` selector that **loads a pre-built fegen-CST extension**; its only callers are **tests** (`fltk/test_plumbing.py`); no general `genparser compile-rust-cst` AOT user workflow exists. A2 explicitly deferred general plumbing adoption (`06/10-rust-parser-codegen/design.md:167-169`). | `grep rust_fegen_cst_module` → all non-def hits in `test_plumbing.py`; `plumbing.py:120-168` |
| **Phase 5: dogfood — replace `fltk_cst.py` with a Rust re-export** ("FLTK eats its own cooking") | **NOT DONE.** `fltk/fegen/fltk_cst.py` is still hand-/generator-produced **Python dataclasses**; production self-host runs on Python. The Rust fegen CST is a *separate* artifact used only as a **build-test fixture** and in self-hosting *tests*. | `fltk_cst.py:1-20` (dataclasses, no `_native` runtime import); Makefile `gencode:248-251` regenerates `fltk_cst.py` **as Python** from `fegen.fltkg` |
| **"Parser stays Python; no Rust parser phase; there is no Phase 6"** | A **whole new parser subsystem** was built later: `fltk-parser-core` runtime crate (memo/terminalsrc/errors), `gsm2parser_rs.py` (1036 LoC), parser Python bindings, parity tests. | `06/10-rust-parser-*` ADRs; `crates/fltk-parser-core/`; `fltk/fegen/gsm2parser_rs.py` |
| **CST = "nominal" thin wrapper** (`span: PyObject`, `children: Py<PyList>`), throwaway by design | Re-architected to **native storage** (`span: Span`, `children: Vec<...>`) mid-project; throwaway prediction realized; not in the 5-phase plan | `state-of-the-world.md:21`; forensics README |
| Two generators (Python concrete + Rust) | **THREE generated artifacts per grammar**: `fltk_cst.py` (Python concrete, 1026 LoC gen), `fltk_cst_protocol.py` (**936 LoC — a surface invented mid-project** to fix the annotation regression), and Rust `crates/fegen-rust/src/cst.rs`. Plus the Python parser, Rust parser, Python unparser. | `wc -l fltk_cst_protocol.py` = 936; Makefile `gencode` |
| `gsm2tree.py` ~303 LoC (per exploration) | `gsm2tree.py` is now **1026 LoC** and `gsm2tree_rs.py` is **2351 LoC** — the Rust CST generator is **>2x** the Python one and ~7.7x the original estimate. Direct-emission verbosity is real. | `wc -l` |
| Single canonical generated `.rs` (`src/cst_fegen.rs`, with `include!` single-source fix in 06/06-fegen-cst-rs-single-source) | The canonical location **moved again** to `crates/fegen-rust/src/cst.rs` (06/14 native-lib-shape made `_native` runtime-only and relocated fegen CST/parser). There are now **~10 generated `.rs` copies** (cst.rs/parser.rs/collision_*) across `crates/` + `tests/`, incl. a literal `cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs` in the Makefile. | `find ... -name cst.rs/parser.rs`; Makefile `gencode:286` |
| Rust **unparser** runtime + generator were a major planned piece (1.5-2k Rust LoC, the bulk of the work per every analysis) | **NOT BUILT.** No `gsm2unparser_rs.py`; unparser is Python-only. The Rust backend is **parser + CST only**; the largest/hardest runtime piece (`resolve_specs`, Wadler-Lindig renderer, `op="is"`) is entirely unaddressed. | `ls fltk/fegen/gsm2*rs.py` (no unparser); `06/10-rust-parser-codegen/design.md §2.6` commits the future unparser to `gsm2unparser_rs.py` |
| `fltk-cst-spike` was the original PoC | Still a **workspace member** at HEAD; its `cst.rs` is a literal `cp` of the poc fixture; leftover. | root `Cargo.toml` members; Makefile `cp` line |

---

## 5. Recurring / unresolved themes across the per-feature review chain

Mined from ~50 ADR dirs of `judge-verdict-*` / `notes-deep-*` / `dispositions-*` / escalations.

1. **Dual-/triple-generator drift — the dominant, never-eliminated theme.** "Drift" and
   "dual maintenance"/"can diverge" appear in the review artifacts of essentially every CST/parser
   ADR. It was knowingly accepted at the architecture gate (parity tests as the only backstop,
   `06/10-rust-parser-codegen/README.md:66-69`) and keeps re-surfacing structurally: byte-identical
   committed copies (`06/06-fegen-cst-rs-single-source`), the gencode step that *regenerates a
   duplicate*, the `.lower()` divergence across four copies (`extract-rule-name-to-class-name`), a
   Python/Rust **trivia-capture behavioral divergence** that needed root-cause investigation
   (`06/05-cst-type-annotations-regression/trivia-divergence-rootcause-v2.md`). The drift surface
   has grown, not shrunk.

2. **The "nominal vs. real Rust backing" question** — recurred from the first analysis
   (`analysis-rust-cst-first.md:223`) through the forensics report and forced a mid-project
   re-architecture (4c8f0ad). The honest answer for a long stretch was "the Rust backing is nominal";
   it is now native, but at the cost of unplanned rework and span-access API changes that broke
   in-flight assumptions (`state-of-the-world.md` items 5 & 7: `rust-cst-child-span-test` needed a
   full redesign because accessors no longer return `terminalsrc.Span`).

3. **Cross-backend drop-in fidelity is fragile and rests on one invariant.** The whole drop-in
   promise hangs on three distinct enum classes all emitting an identical canonical string and on
   per-process CPython-hash agreement across two distinct cdylib crates — the design itself flags the
   **AC8 two-crate hash agreement as "unproven without a built test ... do not infer it"**
   (`cross-backend-label-equality/design.md §5`). `is`-identity is explicitly sacrificed.

4. **Escalations reveal design-specified work shipped incompletely.** The parser generator's deep
   review escalated **four scope findings** — the generated **regex-compile test was missing**, the
   **left-recursion + multibyte fixture coverage was absent**, **`make check` didn't gate the fixture
   crates**, and key Rust test cases (`Shared::ptr_eq` memo-sharing, `error_position`, boundary
   `pos`) were unwritten (`06/10-rust-parser-generator/escalation-respond.md`). I.e. the
   highest-risk correctness areas (left recursion, multibyte, regex-subset enforcement) were the ones
   initially not tested. They were subsequently addressed, but the pattern — "design specified it,
   implementation skipped it, review caught it" — is notable for a production-readiness judgment.

5. **TODO burndowns repeatedly find stale designs and accreting deferred work.** The 06/09 state-of-
   the-world found **"0 of 8 accepted items implemented"**, one done "by accident", one premise
   already false, and **two brand-new TODOs spawned by the side-quest rework**
   (`span-source-as-py-crosscdylib` — a real cross-cdylib efficiency bug, two O(source-length) ops per
   span accessor; and `rust-cst-child-node-identity` — fresh wrapper per accessor call, which forced
   **5 tests to relax `is` → `==`**). `TODO.md` at HEAD still carries ~9 live Rust/Bazel items.

6. **Out-of-tree-consumer reasoning is a constant, deliberate corrective.** Multiple ADRs and judge
   verdicts repeatedly re-assert that the absence of an in-tree consumer is not safety evidence
   (the banned per-traversal accessor; the protocol-label additive-vs-breaking analysis; the Bazel
   `lib-rs-no-cst` "no current consumer trips it" defer). The process was self-aware about this risk
   but it required continuous vigilance — a sign the architecture makes it easy to optimize for the
   visible in-tree case.

7. **Subsystem keeps getting re-shaped at the build/packaging layer.** Span source as cross-cdylib
   (06/10), crosscdylib ABI sentinel + helper (06/11), bindings module split (06/11), preamble helpers
   into cst-core (06/10), cargo-deny CI split (06/12), bazel packaging (06/13), and finally the
   `_native` runtime-only relocation (06/14) — a long tail of structural churn around how the Rust
   pieces are packaged and exposed, continuing right up to HEAD. This is consistent with a prototype
   still settling its boundaries, not a stabilized subsystem.

---

## 6. Net read for the retrospective (intent vs. outcome)

- **Was the original intent coherent?** Yes — the 5-phase plan was unusually disciplined,
  incremental, and honest about its "nominal/intermediate-step" nature and its unquantified
  performance premise.
- **Did the build follow the intent?** **Substantially no.** The scope expanded well beyond the plan
  (native CST + full Rust parser subsystem + protocol module), the stated primary deliverable
  (general user-facing Rust CST via plumbing) was deferred/transformed into a test-only selector,
  the dogfooding finale (Phase 5) was never executed, and the biggest planned runtime piece (the Rust
  unparser) was never started. The throwaway parts were, as predicted, thrown away — at real cost.
- **Were the bets defensible?** The IIR-rejection / direct-emission bet is well-argued and
  internally consistent; but it locked in the dual/triple-generator drift problem that dominates the
  review history, mitigated only by parity tests. The cross-backend drop-in mechanism is clever but
  fragile and rests on unproven-at-design-time invariants.
- **The single most important unanswered question, unchanged since 05/25:** *does any of this
  actually go faster end-to-end, for a real consumer, by enough to justify the dual-maintenance and
  build complexity?* No measurement appears in the entire ADR record.

---

### Key source anchors
- `docs/adr/2026/05/25-rust-backend-exploration/{synthesis.md, analysis-iir-adaptation.md,
  analysis-separate-reimplementation.md, analysis-rust-cst-first.md}`
- `docs/adr/2026/05/25-pyo3-cst-plan/phase-plan.md`
- `docs/adr/2026/06/06-rust-cst-nominal-backend-forensics/README.md` (the central drift archaeology)
- `docs/adr/2026/06/09-todo-burndown-resume/state-of-the-world.md`
- `docs/adr/2026/06/10-rust-parser-codegen/{README.md, design.md, notes-design-design-reviewer.md}`
- `docs/adr/2026/06/10-rust-parser-generator/escalation-respond.md`
- `docs/adr/2026/06/05-clean-protocol-consumer-api/requirements.md`
- `docs/adr/2026/06/05-cross-backend-label-equality/design.md`
- `docs/adr/2026/06/05-cst-type-annotations-regression/README.md`
- `docs/adr/2026/06/06-fegen-cst-rs-single-source/{request.md, design.md}`
- Code: `fltk/fegen/{gsm2tree.py, gsm2tree_rs.py, gsm2parser.py, gsm2parser_rs.py, gsm2lib_rs.py,
  genparser.py, fltk_cst.py, fltk_cst_protocol.py, plumbing.py}`; `crates/fegen-rust/src/`;
  root `Cargo.toml`; `Makefile` (`gencode`); `TODO.md`
