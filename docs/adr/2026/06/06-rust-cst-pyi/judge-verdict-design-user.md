# Judge verdict — design review (rust-cst-pyi), user-notes round

Phase: design. Doc: `docs/adr/2026/06/06-rust-cst-pyi/design.md` (revised in place).
Round: user-response round following approved round 1.
Notes: `notes-design-user.md` (4 user decisions, authoritative). Dispositions:
`dispositions-design-user.md`.
Style: concise, precise, no padding. Audience: smart LLM/human.

## Findings walk

(Doc phase; no TODO dispositions — all four items are Fixed.)

### user-OQ-0 — Fixed (conformance strategy = (a) protocol-typed)
User decision: adopt option (a), the design's own recommendation.
Evidence in design: §2 intro records all four decisions as resolved; §1 closes with
"adopted strategy (OQ-0(a), decided by the user — §5)"; §5 OQ-0 records "(a)
protocol-typed annotations. As recommended." §2.1 is written unconditionally against
(a) (`--protocol-module`, `_proto`-qualified identities); no alternative-option text
remains anywhere in the doc.
Assessment: decision applied faithfully; nothing to dispute. Accept.

### user-OQ-A — Fixed (common single `Span`; protocol corrected, not backends)
User decision (verbatim): "Don't we have a common single Span defined somewhere? We
should I think? that's how Python works — the Span clas is not part of the generated
CST module; it lives in a common lib."
Premise verified against source by me:
- `fltk/fegen/fltk_cst.py` top level: only `import fltk.fegen.pyrt.span` /
  `terminalsrc` (lines 5-6); no module-level `Span` binding. Confirmed.
- Common-lib `Span`s: `terminalsrc.Span` (pure Python), the
  `fltk/fegen/pyrt/span.py` backend selector, and `fltk._native.Span` registered once
  in `src/lib.rs` `#[pymodule]` (`m.add_class::<Span>()` plus `UnknownSpan`). Confirmed.
- So `mod.Span` on a `CstModule`-typed binding raises `AttributeError` on **both**
  backends today — the design's "no working consumer code can exist" safety argument
  holds at runtime. Confirmed.
Evidence in design: §1 reframes ("`CstModule.Span` is a protocol overclaim, not a
Rust-backend gap"); new §2.1a deletes the `span_prop` emission from
`_cst_module_protocol` (verified present in `gsm2tree.py`, the
"Span property... out-of-tree consumers" block) while keeping the module-level
`class Span(Protocol)`; regenerates the four committed protocol modules; updates
`test_cst_protocol.py` expected property set (verified: the property-set assertion
adds `"Span"` to `expected_class_names` at ~177-178; the class-set test at ~108-110
keeps `Span` — exactly the split the design states). §3 explicitly rejects the prior
round's per-generated-module registration direction as contrary to the user's model.
Conformance target updated to zero errors (§2.2, §4, §5).
On the protocol edit exceeding the user's literal words: the user asserted "the Span
class is not part of the generated CST module" — `CstModule` is the protocol *of the
generated module*, so removing its `Span` promise is the direct application of the
user's model, not an overreach. The disposition honestly flags the specific edit for
sign-off, and the design calls it out as a deliberate public-API change per CLAUDE.md
(removal loosens implementer requirements; consumer-side `.Span` reads already crash
at runtime on every backend, so the CLAUDE.md out-of-tree caution is met with a
runtime argument, not an absence-of-in-tree-consumer argument). The flagged fallback
(honest omission + one expected diagnostic) is preserved in the dispositions doc for
the user to invoke at sign-off.
Assessment: premise verified, application faithful, public-API change deliberately
called out with a sound safety argument and surfaced for sign-off. Accept.

### user-OQ-1 — Fixed (Part 2 scope = both now)
User decision overrides the design's defer recommendation.
Evidence in design: scope line names Part 1 + Part 2; §2.2 item 2 routes to §2.3; §2.3
exists with the B4 runtime-agreement test, committed-stub static conformance fixture,
gencode wiring, and packaging; §4 gains the Part 2 test items; `TODO(rust-cst-pyi)`
(verified at `genparser.py:279`) and the `TODO.md` entry (verified `## rust-cst-pyi`,
referenced by slug, not line) are removed outright with no narrowed follow-up — correct
given both parts now land in one workflow.
Assessment: user override applied in full. Accept.

### user-OQ-2 — Fixed (Part 2 strategy = prebuilt `fltk._native.fegen_cst`)
User decision overrides the compile-on-the-fly recommendation; the round-1 objection
(undesigned repo-wide `fltk._native` stub) is discharged by designing it in §2.3.
Source-verified claims:
- Surface under test: `src/lib.rs` registers fegen classes in the `fegen_cst`
  submodule with manual `sys.modules` insertion; `tests/test_fegen_rust_cst.py:11-12`
  already imports `fltk._native.Span/UnknownSpan` and the node classes from
  `fltk._native.fegen_cst`. Confirmed.
- `__init__.pyi` member list: matches the real `#[pymethods]` surface at
  `crates/fltk-cst-core/src/span.rs:188+` (`with_source`, `text`, `text_or_raise`,
  `has_source`, `len`, `is_empty`, `merge`, `intersect`, getters `start`/`end`/`kind`);
  the `kind` getter returns the *shared* `terminalsrc.SpanKind.SPAN` object via
  `SPAN_KIND_SPAN_CACHE`, so the `Literal[terminalsrc.SpanKind.SPAN]` annotation is
  exact. Confirmed.
- PoC omission cross-ref `TODO(gencode-poc-fltkg)`: slug exists (`TODO.md:32`,
  `Makefile:78`). Confirmed.
- Shadowing analysis: `fltk/_native/` with only `.pyi` files is at most a
  namespace-package portion; CPython's `FileFinder` prefers the regular extension
  module `_native.abi3.so` over a namespace portion, while an `__init__.py` would make
  it a regular package and shadow the extension. Analysis is correct. No `fltk/_native`
  directory or any `.pyi` exists at HEAD, as the design assumes. Confirmed.
- Build-cost claim: `maturin develop` is mandatory before tests (CLAUDE.md), so
  prebuilt adds no machinery. Confirmed.
- Stem/import mismatch motivating `--pyi-output`: `make gencode` writes
  `src/cst_fegen.rs` (Makefile gencode target) backing import name `fegen_cst`.
  Confirmed.
- Blast radius: the `fltk._native` import in `fltk/fegen/pyrt/span.py` carries
  `# type: ignore[assignment]` and all three names exist in the planned stub.
  Confirmed — one nit: the design cites it as `span.py:10`; the `fltk._native` import
  with the ignore is at line 13 (line 10 is the `terminalsrc` import). Claim content
  correct; cite off by three lines. Nit, no consequence beyond navigation.
Assessment: user override applied with the previously-missing design work actually
done, every load-bearing claim source-true. Accept.

## Disputed items

None. The OQ-A protocol-API removal is flagged for user sign-off inside the
dispositions doc with a preserved fallback — that is the correct handling, not a
dispute.

## Approved

4 user decisions: 4 Fixed verified (OQ-A includes a deliberately called-out,
sign-off-flagged public-API correction; OQ-2 includes one nit-level line-cite drift,
`span.py:10` → :13, not verdict-affecting). No Won't-Do, no TODOs, no open questions
remain in §5.

---

## Verdict: APPROVED

All four user decisions applied faithfully to `design.md`; every factual claim in the
dispositions checked out against source. The single carry-forward for design sign-off
is the OQ-A `CstModule.Span` protocol removal, already flagged with its fallback in
`dispositions-design-user.md`.
