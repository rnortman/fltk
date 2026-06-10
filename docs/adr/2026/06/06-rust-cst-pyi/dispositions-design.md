# Dispositions: rust-cst-pyi design review, round 1

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (revised in place).
Style: concise, precise, no padding. Audience: smart LLM/human.

All findings fact-checked against source before disposition. Key verifications: T2b
exists and requires the bare no-cast assignment to fail (`test_cst_protocol.py:365-382`);
`_register_classes_fn` registers no `Span` (`gsm2tree_rs.py:908-921`); fegen classes
live in the `fltk._native.fegen_cst` submodule (`src/lib.rs:33-47`); protocol child
annotations use `fltk.fegen.pyrt.span.Span` (`fltk_cst_protocol.py:197,219`; import
emitted at `gsm2tree.py:495`); no `.pyi` exists anywhere under `fltk/`; `## rust-cst-pyi`
is at `TODO.md:23-25`.

---

design-1:
- Disposition: Fixed
- Action: §1 gains "Conformance is impossible with stub-local nominal types
  (feasibility constraint)" enumerating all four blockers (nested-`Label` nominal
  identity, `kind` Literal enum identity, `children` invariance, parameter
  contravariance) and citing T2b. §2.1 is rewritten against reviewer option (a):
  member presence from `_rule_info`, type identities from the committed protocol module
  via a new `--protocol-module` CLI parameter, with `NodeKind`/`Label` typed as protocol
  types (deliberate checker-favorable divergence). The strategy choice is surfaced as
  OQ-0 (user decision, options (a)/(b)/(c) with recommendation (a)), not silently
  adopted. New §2.2 also corrects the Part 2 framing: pyright never imports the
  compiled extension, so the no-cast static check is a Part 1 deliverable; Part 2's
  residual value is runtime-vs-stub introspection.
- Severity assessment: Highest-severity finding; verified correct. As previously
  designed, the Part 2 acceptance criterion was structurally unsatisfiable (T2b proves
  the analogous Python-surface assignment must error), and the likely workaround (adding
  a cast) would have silently abandoned the request's core requirement.

design-2:
- Disposition: Fixed
- Action: §1 table gains a module-level-`Span` row (not registered;
  `_register_classes_fn`, `gsm2tree_rs.py:908-921`; `src/lib.rs:33-35`). §2.1 now says
  "No module-level `Span`" by default with rationale (dangerous-direction stub/runtime
  lie). §3 gains a "Module-level `Span` (real surface gap)" entry. New OQ-A (user
  decision): (i) honest omission + expected-diagnostic assertion + follow-up slug to
  register `Span` in `.rs` (recommended), (ii) fix `.rs` now with explicit non-goal
  waiver, (iii) declare-anyway rejected. §4 whole-module fixture asserts the exact
  expected `Span` diagnostic instead of zero errors.
- Severity assessment: Verified correct and is a genuine product finding, not just a doc
  bug — `CstModule.Span` is promised public API (`gsm2tree.py:670-672`) that every
  generated Rust extension fails to provide at runtime. The original design would have
  had the stub certify it as safe.

design-3:
- Disposition: Fixed
- Action: §5 OQ-2 rewritten: prebuilt option now names `fltk._native.fegen_cst` as the
  surface under test (`src/lib.rs:33-47`), spells out the stub-package layout
  (`fltk/_native/__init__.pyi` + `fegen_cst.pyi`) replacing `with_suffix(".pyi")`
  co-location, and states the repo-wide blast radius: any `fltk._native` stub must
  declare `Span`/`SourceText`/`UnknownSpan` or `uv run pyright` breaks, because those
  attributes currently typecheck only by being Unknown. Recommendation flipped from
  prebuilt to compile-on-the-fly (or defer per OQ-1 (ii)), since the `fltk._native`
  stub package is a repo-wide typing change that deserves its own decision.
- Severity assessment: Verified correct on all three sub-points. The old recommendation
  would have pointed Part 2 at the wrong grammar's surface and triggered an undesigned
  repo-wide pyright regression.

design-4:
- Disposition: Fixed
- Action: §2.1 header bullet now derives the import list from emitted annotations (as
  `gen_protocol_module` does) and lists `import fltk.fegen.pyrt.span` in the expected
  set, with the source citations (`fltk_cst_protocol.py:197,219`; `gsm2tree.py:495`).
- Severity assessment: Verified; without the import, essentially every grammar's stub
  has unresolved references and the design's own §4 self-check fails immediately.

design-5:
- Disposition: Fixed
- Action: §2.1 CLI-wiring paragraph and §2.3 now reference the `TODO.md` entry by slug
  (`## rust-cst-pyi`), not line numbers. Verified at HEAD the entry is at lines 23-25
  and lines 27-29 are `cst-protocol-label-free`, as the reviewer said.
- Severity assessment: Low but real — following the stale cite would delete the wrong
  entry and break the slug-join invariant.

design-6:
- Disposition: Fixed
- Action: The "class (or `enum.Enum` subclass)" wording is gone. Under OQ-0(a) the stub
  emits `NodeKind = _proto.NodeKind` (a module-level alias to the protocol's real enum),
  so `Literal[_proto.NodeKind.X]` is a valid Literal form by construction (§2.1). No
  plain-class option remains anywhere.
- Severity assessment: Verified; `typing.Literal` accepts only enum members and
  int/str/bytes/bool/None literals, so the plain-class option would fail the self-check
  on every node class.

design-7:
- Disposition: Fixed
- Action: The overstated claim ("self-check ... already catches most stub/protocol
  mismatches") is removed. §4 now states the self-check verifies internal
  well-typedness only, and adds Part-1-scoped **stub-vs-protocol conformance fixtures**
  (whole-module no-cast fixture with exact expected diagnostic set; per-class no-cast
  fixtures asserting zero errors) — enabled by the §2.2 observation that pyright needs
  only the stub, not the compiled extension. OQ-1's recommendation (ii) is restated on
  the corrected basis: what remains unverified until Part 2 is runtime-vs-stub
  agreement, not protocol conformance.
- Severity assessment: Verified; the original §4 had no test relating the stub to
  `CstModule`, so recommendation (ii) would have deferred the request's load-bearing
  verification while claiming it was mostly in hand.

design-8:
- Disposition: Fixed
- Action: Line cites corrected in place: `RustCstGenerator.generate` →
  `gsm2tree_rs.py:114-130` (§1); `_protocol_class_for_model` → `gsm2tree.py:540-641`
  (§2.1); Rust-path cast → `plumbing.py:173-175` (§1). All three verified at HEAD.
- Severity assessment: Informational; navigation cost only.
