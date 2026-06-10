# Dispositions: rust-cst-pyi — user answers to §5 open questions

Notes: `notes-design-user.md` (verbatim user decisions, authoritative). Design:
`design.md` (revised in place; cleanup-editor re-run). Round: user-response round
following judge-approved round 1 (`judge-verdict-design.md`, `dispositions-design.md`).
Style: concise, precise, no padding. Audience: smart LLM/human.

Each answer fact-checked against source before application. Key verifications:
`fltk_cst.py` top level has **no** `Span` binding (only `import fltk.fegen.pyrt.span` /
`terminalsrc`), so `CstModule.Span` is satisfied by *neither* backend; common-lib `Span`s
are `terminalsrc.Span`, the `fltk/fegen/pyrt/span.py` selector, and `fltk._native.Span`
registered once at `src/lib.rs:20-23`; the prebuilt fegen surface is the
`fltk._native.fegen_cst` submodule already statically imported by
`tests/test_fegen_rust_cst.py:11-12`; `make gencode` writes `src/cst_fegen.rs`
(`Makefile:105`) whose stem differs from the import name `fegen_cst`; native `Span.kind`
returns the shared `terminalsrc.SpanKind.SPAN` object
(`crates/fltk-cst-core/src/span.rs:378-394`); `maturin develop` is already mandatory
before any test run (CLAUDE.md), so the prebuilt route adds no build machinery.

---

user-OQ-0 (conformance strategy = option (a), protocol-typed):
- Disposition: Fixed
- Action: §2.1 was already written against (a); converted from conditional to adopted —
  §2 intro now records all decisions, §1 closing paragraph says "adopted strategy
  (OQ-0(a))", §5 records the decision. No alternative-option text remains.
- Severity assessment: Confirms the only strategy under which the request's no-cast
  zero-error criterion is achievable (§1 feasibility constraint, T2b); no design risk.

user-OQ-A (common single `Span` — premise of the "Rust surface gap" questioned):
- Disposition: Fixed
- Action: User's premise verified true and the design's framing corrected throughout.
  §1 gains "`CstModule.Span` is a protocol overclaim, not a Rust-backend gap" (the
  Python concrete module also lacks module-level `Span`; the common-lib model —
  `terminalsrc.Span` / `fltk.fegen.pyrt.span` selector / `fltk._native.Span`,
  `src/lib.rs:20-23` — is the actual design). New §2.1a resolves it on the protocol
  side: delete the `Span` property from `_cst_module_protocol` (`gsm2tree.py:668-676`),
  regenerate the four committed protocol modules, update
  `test_cst_protocol.py:177-178`; the module-level `class Span(Protocol)` stays. Called
  out as a deliberate public-API change with the safety argument (reading `.Span` off a
  `CstModule` binding raises `AttributeError` on every backend today, so no working
  consumer code can depend on it). §3's edge case now rejects per-generated-module
  `Span` registration (the prior follow-up direction) as wrong per this answer.
  Whole-module no-cast conformance target is now zero errors (§2.2, §4, §5).
- Severity assessment: The user's question invalidated the prior OQ-A resolution path
  (a follow-up to register `Span` in generated `.rs`), which would have produced N
  per-module aliases of a deliberately-common type and permanent expected-diagnostic
  snowflakes in the conformance fixtures. The corrected resolution achieves the
  request's zero-error criterion exactly. If the user objects to removing
  `CstModule.Span` (it is a committed-protocol API removal, albeit of a member no
  backend ever satisfied), the fallback is the previous honest-omission +
  one-expected-diagnostic assertion — flagging for sign-off since the user's note
  asserted the model but not this specific protocol edit.

user-OQ-1 (Part 2 scope = both now):
- Disposition: Fixed
- Action: Part 2 brought fully into scope. §2.2 item 2 now routes to new §2.3; §2.3
  designs the B4 runtime-agreement test, the committed-stub static conformance fixture,
  gencode wiring, and packaging. TODO handling simplified to outright removal of
  `TODO(rust-cst-pyi)` + the `TODO.md` entry (no narrowed follow-up) — §2.1 CLI wiring,
  §2.4, §5. Test plan §4 gains the Part 2 items.
- Severity assessment: Overrides the design's defer recommendation; cost is bounded
  because the static conformance work was already a Part 1 deliverable and the prebuilt
  route (OQ-2) eliminates per-test builds.

user-OQ-2 (Part 2 build strategy = prebuilt fegen_cst):
- Disposition: Fixed
- Action: Overrides the design's compile-on-the-fly recommendation; the objection that
  motivated it (the `fltk._native` stub package is a repo-wide typing change deserving
  deliberate design) is discharged by designing it in new §2.3: stub package layout
  (`fltk/_native/__init__.pyi` hand-written + `fltk/_native/fegen_cst.pyi` generated,
  committed), `__init__.pyi` member list mirroring the real PyO3 surface
  (`crates/fltk-cst-core/src/span.rs` `#[pymethods]`; `UnknownSpan: Span`; PoC top-level
  classes deliberately omitted with rationale, cross-ref `TODO(gencode-poc-fltkg)`),
  runtime non-shadowing analysis (`.pyi`-only directory loses to `_native.abi3.so`; an
  accidental `__init__.py` would shadow — guarded), repo-wide blast-radius enumeration
  (`span.py:10`, protocol span unions, `tests/test_fegen_rust_cst.py` imports) gated by
  `uv run pyright`, Makefile `gencode` wiring via the new `--pyi-output` option (stem
  `cst_fegen` ≠ import name `fegen_cst`), and wheel packaging note. §2.1 and the §5
  output-path decision updated for `--pyi-output`; §3 gains shadowing / blast-radius /
  hand-written-stub-drift edge cases; §4 gains the B4 tests and committed-stub sync.
- Severity assessment: The prebuilt choice is sound and cheaper than the design's own
  recommendation acknowledged — the extension is already built by the mandatory
  `maturin develop` step, and verification runs against the exact shipped artifact. The
  real cost (the `fltk._native` stub's repo-wide typing effects) is now an explicit,
  designed deliverable instead of a test-harness side effect.

---

No Won't-Do or TODO dispositions. No open questions remain in `design.md` §5.
