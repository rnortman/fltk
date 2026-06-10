# Judge verdict — design review (rust-cst-pyi)

Phase: design. Doc: `docs/adr/2026/06/06-rust-cst-pyi/design.md` (revised in place). Round 1.
Notes: `notes-design-design-reviewer.md` (8 findings). Dispositions: `dispositions-design.md`.
Style: concise, precise, no padding. Audience: smart LLM/human.

## Findings walk

### design-1 — Fixed (no-cast conformance infeasible with stub-local nominal types)
Claim: §2.1's stub-local `Label`/`NodeKind`/self-referential node types can never pass the bare no-cast `CstModule` assignment; T2b (`test_cst_protocol.py:365-382`) proves the analogous assignment must error; consequence: Part 2 acceptance criterion structurally unsatisfiable, likely "fixed" by a cast that abandons the request's core requirement.
Verified premise: T2b exists at the cited lines and asserts `errors` non-empty on `_m: cstp.CstModule = fltk_cst`.
Fix in design: §1 gains "Conformance is impossible with stub-local nominal types (feasibility constraint)" enumerating all four blockers (nested-`Label` nominal identity, `kind` Literal enum identity, `children` invariance, parameter contravariance) and citing T2b. §2.1 rewritten against reviewer option (a): member presence from `_rule_info`, type identities qualified against the committed protocol module via new `--protocol-module` parameter. Surfaced as OQ-0 (USER DECISION REQUIRED) with options (a)/(b)/(c) and recommendation (a) — not silently adopted, matching the reviewer's "needs a user decision" demand. §2.2 additionally corrects the Part 2 framing (pyright never imports the compiled extension; the no-cast static check moves to Part 1).
Assessment: fix fully addresses the finding, including the surface-as-decision requirement. Accept.

### design-2 — Fixed (stub `Span: type[Span]` describes a nonexistent module attribute)
Claim: `_register_classes_fn` registers no `Span`; `CstModule.Span` is promised public API (`gsm2tree.py:670-672`); the original stub would certify a runtime `AttributeError`.
Verified: `register_classes` emission (`gsm2tree_rs.py:908-921`) adds only `NodeKind`, label enums, node classes; `gsm2tree.py:670-672` adds the `Span` property "for out-of-tree consumers"; `src/lib.rs` fegen registration likewise lacks `Span`.
Fix in design: §1 table gains the module-level-`Span` row; §2.1 specifies "No module-level `Span`" with dangerous-direction rationale; §3 gains a "Module-level `Span` (real surface gap)" entry; OQ-A (USER DECISION REQUIRED) offers honest-omission (recommended), fix-`.rs`-now (non-goal waiver), declare-anyway (rejected); §4 whole-module fixture asserts the exact expected `Span` diagnostic instead of zero errors.
Assessment: fix addresses both the stub honesty problem and the underlying product gap, with the non-goal collision routed to the user. Accept.

### design-3 — Fixed (OQ-2 prebuilt recommendation targeted wrong module, skipped stub-packaging/blast-radius)
Claim: fegen classes live in `fltk._native.fegen_cst` (`src/lib.rs:33-47`), not top-level; submodule stubs need a stub package; any `fltk._native` stub makes currently-Unknown `Span`/`SourceText`/`UnknownSpan` references concrete repo-wide.
Verified: `lib.rs` registers PoC classes top-level and fegen classes in the `fegen_cst` submodule with manual `sys.modules` insertion.
Fix in design: OQ-2 rewritten — names `fltk._native.fegen_cst` as the surface under test, spells out the `fltk/_native/__init__.pyi` + `fegen_cst.pyi` stub-package layout, states the repo-wide pyright blast radius, and flips the recommendation to compile-on-the-fly (or defer per OQ-1 (ii)).
Assessment: all three sub-points addressed; recommendation change is justified in-text. Accept.

### design-4 — Fixed (missing `fltk.fegen.pyrt.span` import)
Claim: reused annotation machinery emits `fltk.fegen.pyrt.span.Span` for terminal children; the specified header never imports it; every realistic grammar's stub fails the §4 self-check.
Verified: `fltk_cst_protocol.py:197,199,202,207` use `fltk.fegen.pyrt.span.Span`; the protocol generator emits the matching import (`gsm2tree.py` TYPE_CHECKING block, ~l.495).
Fix in design: §2.1 header bullet now derives the import list from emitted annotations (as `gen_protocol_module` does) and lists `import fltk.fegen.pyrt.span` in the expected set with the source citations.
Assessment: addressed. Accept.

### design-5 — Fixed (wrong TODO.md line range)
Claim: `## rust-cst-pyi` is at `TODO.md:23-25`, not 27-29 (which is `cst-protocol-label-free`).
Verified: `TODO.md` shows `cst-protocol-label-free` immediately after the rust-cst-pyi entry, in the 27-29 region.
Fix in design: §2.1 CLI wiring says "the `## rust-cst-pyi` section — locate by slug, not line number"; §2.3 says "(by slug)". No line-number reference remains.
Assessment: addressed per the suggested fix. Accept.

### design-6 — Fixed (plain-class `NodeKind` option invalid in `Literal`)
Claim: `typing.Literal` accepts only enum members and int/str/bytes/bool/None; the "class (or `enum.Enum` subclass)" wording offered an option that fails on every node class.
Fix in design: wording gone; under OQ-0(a) the stub emits `NodeKind = _proto.NodeKind` (alias to the protocol's real enum), so `Literal[_proto.NodeKind.X]` is valid by construction. No plain-class option remains anywhere in the doc.
Assessment: addressed (subsumed by the design-1 restructure, and independently correct). Accept.

### design-7 — Fixed (self-check overclaim; protocol conformance unverified in Part 1)
Claim: the `.pyi`-only self-check performs no comparison against `CstModule`; recommendation (ii) would defer the request's load-bearing verification while claiming it was mostly in hand.
Fix in design: overstated claim removed; §4 self-check now explicitly "verifies internal well-typedness only — it performs no protocol comparison". New Part-1-scoped stub-vs-protocol conformance fixtures added (whole-module no-cast fixture with exact expected diagnostic set; per-class no-cast fixtures asserting zero errors), enabled by §2.2's observation that pyright needs only the stub. OQ-1 (ii) restated on the corrected basis: what remains unverified until Part 2 is runtime-vs-stub agreement only.
Assessment: addressed beyond the minimum — the load-bearing verification now lands in Part 1. Accept.

### design-8 — Fixed (line-cite drift, informational)
Fix in design: `RustCstGenerator.generate` → `gsm2tree_rs.py:114-130` (verified: `generate` body spans those lines at HEAD); `_protocol_class_for_model` → `gsm2tree.py:540-641`; Rust-path cast → `plumbing.py:173-175`. All three appear corrected in the revised §1/§2.1.
Assessment: addressed. Accept.

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified (design-1 and design-2 also correctly surfaced as user decisions OQ-0/OQ-A rather than silently resolved).

---

## Verdict: APPROVED

All dispositions acceptable. Round 1; no rework required. The revised design carries two new USER DECISION REQUIRED items (OQ-0 conformance strategy, OQ-A module-level `Span` gap) plus the pre-existing OQ-1/OQ-2 — these are correctly framed as decisions for the user at design sign-off, not defects in the dispositions.
