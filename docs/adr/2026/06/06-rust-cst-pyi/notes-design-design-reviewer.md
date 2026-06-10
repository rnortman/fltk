# Design review findings: rust-cst-pyi

Reviewer: design-reviewer. Base: af6e6f3. Style: concise, precise, no padding.

---

## design-1 — Part 2 no-cast conformance is infeasible with the §2.1 stub shape; the "two reconciliations" claim is wrong

**Where:** §1 ("The `.pyi` must be authored so pyright accepts the Rust module as a
structural subtype of `CstModule`... Two specific reconciliations (see §3):
`children_<label>` return type, and the `span` type"), §2.2 ("binds the **real compiled
Rust module** to `CstModule` **without a cast**, asserting zero pyright errors"), §4
("B4 no-cast conformance test... assert zero errors").

**What's wrong:** A stub whose classes carry their own nested `Label` classes, their own
`NodeKind` enum, and self-referential node types in `children`/method signatures —
exactly what §2.1 specifies — cannot satisfy `CstModule` without a cast. The two §3
reconciliations are nowhere near sufficient. At minimum these also block conformance:

- **Nested `Label` nominal identity.** The protocol's `Label` is a plain nominal class
  per node (`fltk_cst_protocol.py:85-87` etc.). Protocol conformance requires the
  implementing class's `Label` attribute be assignable to `type[<proto>.Label]` —
  nominal, so a stub-local `Label` class always fails.
- **`kind` Literal enum identity.** Proto declares
  `kind: typing.Literal[NodeKind.GRAMMAR]` against the *protocol module's* `NodeKind`
  (`fltk_cst_protocol.py:88`). A `Literal` of the stub's own `NodeKind` member is a
  different type; the attribute is mutable hence invariant — fails.
- **`children` invariance.** `children: list[tuple[Label|None, <union>]]` is an invariant
  mutable attribute whose element types are the proto's own classes; a stub annotating it
  with stub-local classes fails bidirectional assignability (protocol types are not
  assignable to nominal stub classes).
- **Parameter contravariance.** `append(child: Rule | Trivia, label: Label | None)`,
  `extend_children(other: Grammar)` — proto types are not assignable to the stub's
  nominal parameter types.

**Why (source-backed):**
- In-repo proof the design ignores: `test_boundary_probe_documents_label_mismatch`
  (T2b, `test_cst_protocol.py:354-382`) asserts the bare no-cast assignment
  `_m: cstp.CstModule = fltk_cst` **must produce pyright errors** ("nested-Label nominal
  mismatch... confirms the cast is *required* (not optional)"). The design cites the T2a
  fixture two sections away (`test_cst_protocol.py:195-276`) but never engages T2b,
  which directly contradicts the Part 2 premise for a module whose surface the stub is
  designed to mirror ("reuse the Python protocol-class machinery", §2.1).
- Empirically re-confirmed at HEAD: pyright on the bare assignment reports
  `Type "Module(fltk.fegen.fltk_cst)" is not assignable to declared type "CstModule" |
  "Span" is not present | "Grammar" is an incompatible type | ... "fltk.fegen.fltk_cst.Grammar.Label"
  is not assignable to "fltk.fegen.fltk_cst_protocol.Grammar.Label"`.
- Internal inconsistency: §3 correctly invokes attribute invariance to argue the `span`
  stub annotation must be the exact protocol union, then fails to apply the same
  invariance rule to `kind`, `children`, and `Label`, which are invariant for the same
  reason and *cannot* be made to match with stub-local types.

**Consequence:** The Part 2 acceptance criterion ("assert zero errors", no cast) can
never pass as designed; an implementer builds the emitter and harness, then discovers
the test is structurally red. Worse, the natural "fix" (adding a cast, or loosening the
fixture) silently abandons the request's core requirement ("pyright asserting the
surface satisfies `CstModule` WITHOUT a cast", request.md Part 2). The §1 framing also
misleads Part 1: the stub as specified does not "close the gap the cast hides".

**Suggested fix:** Surface this as a feasibility blocker alongside OQ-1 — it likely
changes the user's scope decision. Viable directions to lay out: (a) the stub imports
the grammar's committed `*_cst_protocol` module and reuses its `NodeKind` / nested
`Label` / node-protocol types in all annotations (requires a new `gen-rust-cst`
parameter for the protocol module import path; stub then deliberately types runtime PyO3
enums as protocol types — same "checker-favorable lie" category as the
`children_<label>` decision); (b) redefine Part 2 acceptance as an expected-diagnostics
snapshot (mirrors T2b) rather than zero-errors; (c) per-member conformance fixtures
instead of whole-module assignment. Any of these needs a user decision, not silent
adoption.

---

## design-2 — Stub's module-level `Span: type[Span]` describes an attribute the generated extension does not have

**Where:** §2.1 ("Module-level class attributes: one `<Class>: type[<Class>]` per rule
plus `Span: type[Span]`, so the **module object** structurally satisfies `CstModule`"),
§2.1 ("`Span` stub class mirroring `_protocol_span_class`... so a `CstModule.Span`
property has a target").

**What's wrong:** The generated `.rs` registers no `Span` class:
`_register_classes_fn` (`gsm2tree_rs.py:908-921`) adds only `NodeKind`, the per-node
`Label` enums, and the node classes. Spans come from `fltk._native` at runtime
(`get_span_type`, `gsm2tree_rs.py:182-191`). The prebuilt fegen surface likewise lacks
it: `cst_fegen::register_classes` populates the `fltk._native.fegen_cst` submodule
(`src/lib.rs:33-35`) with no `Span`. So the stub asserts a module attribute that raises
`AttributeError` at runtime on every extension `gen-rust-cst` produces. (The pyright
probe in design-1 shows even `fltk_cst` lacks a module-level `Span` — `"Span" is not
present` — so this gap is real on both backends, and `CstModule.Span` was added
explicitly for out-of-tree consumers, `gsm2tree.py:670-672`.)

**Consequence:** The `.pyi`'s entire stated purpose (request.md: "the `.pyi` must
reflect the *actual* PyO3 surface the Rust generator emits") is inverted for this
member: the stub *masks* a real surface gap instead of revealing it, and the Part 2
test would certify `mod.Span` as safe for downstream consumers (public API per
CLAUDE.md) when it crashes at runtime. This is a stub/runtime lie in the dangerous
direction, unlike the flagged `children_<label>` case.

**Suggested fix:** Make this an explicit decision point: either omit `Span` from the
stub and document that the generated extension does not satisfy `CstModule.Span` (the
honest stub — Part 2 then fails on this member too, see design-1), or propose adding
`Span` registration to `register_classes` — which collides with the request's "Keep the
existing `gen-rust-cst` `.rs` output unchanged" non-goal and therefore needs the user.

---

## design-3 — OQ-2 "prebuilt" recommendation targets the wrong module and skips the stub-placement/masking problem

**Where:** §5 OQ-2 ("**Prebuilt:** reuse... `fltk._native` exists (`fltk/_native.abi3.so`)
but is the **fegen-specific** Rust CST"; "Recommendation... prebuilt against
`fltk._native` + the fegen `fltk_cst_protocol`... needs no new build harness").

**What's wrong:**
- The fegen Rust CST classes are not at the top level of `fltk._native`: `src/lib.rs:28-35`
  registers the *PoC grammar* classes top-level and the fegen classes in the
  `fltk._native.fegen_cst` submodule (manually inserted into `sys.modules`,
  `src/lib.rs:37-47`). "Prebuilt against `fltk._native`" as written checks the wrong
  grammar's surface against the fegen protocol.
- §2.2 requires "the `.pyi` must sit next to the importable extension so pyright
  resolves the extension's types from the stub". For a submodule of a single-file
  compiled extension (`fltk/_native.abi3.so`), that means introducing a stub package
  (`fltk/_native/__init__.pyi` + `fegen_cst.pyi`) — not the `with_suffix(".pyi")`
  co-location the design specifies. Nothing in the design covers this.
- Today `fltk._native` has **no stub** (no `.pyi` anywhere under `fltk/`), so pyright
  treats its attributes (`Span`, `SourceText`, `UnknownSpan`) as Unknown — which is why
  `fltk._native.Span` in `fltk_cst_protocol.py:89` et al. currently typechecks.
  Introducing any `fltk._native` stub makes those references concrete repo-wide; the
  stub must then also declare `Span` (with `.start`/`.end`/`kind`/`with_source`),
  `SourceText`, and `UnknownSpan`, or `uv run pyright` (the design's own gate, §4)
  breaks outside the new tests. The generated grammar-derived `.pyi` declares none of
  these.

**Consequence:** If the user picks Part 2 with the design's recommended build strategy,
the implementer lands in an undesigned area: wrong target module, no stub layout, and a
repo-wide pyright regression risk that the "no new build harness, minimal thing" framing
hides.

**Suggested fix:** OQ-2's prebuilt option must name `fltk._native.fegen_cst` as the
surface under test and include the stub-packaging plan plus the
`Span`/`SourceText`/`UnknownSpan` coverage question; otherwise recommend
compile-on-the-fly or defer (consistent with OQ-1 recommendation (ii)).

---

## design-4 — Stub header omits `fltk.fegen.pyrt.span`, which the reused annotation machinery emits

**Where:** §2.1 ("Header: `from __future__ import annotations`; `import typing`;
`import fltk.fegen.pyrt.terminalsrc`; `import fltk._native`").

**What's wrong:** The design mandates producing child-union / per-label element types
via `self._py_gen.protocol_annotation_for_model_types(...)` (§2.1). For terminal
(Span-typed) children that machinery emits `fltk.fegen.pyrt.span.Span` — see the
committed protocol output (`fltk_cst_protocol.py:197,199,408,462,514,...`) and the
protocol generator's matching import (`gsm2tree.py:495`, with the registration-path
comment at `gsm2tree.py:177-180`). The stub header as specified never imports
`fltk.fegen.pyrt.span`.

**Consequence:** Every grammar with a literal/regex child (i.e. essentially all of
them) produces a `.pyi` with unresolved `fltk.fegen.pyrt.span` references; the design's
own "`.pyi` pyright self-check" test (§4) fails immediately.

**Suggested fix:** Add `import fltk.fegen.pyrt.span` to the header list (or derive the
import list from the annotations actually emitted, as `gen_protocol_module` does).

---

## design-5 — Wrong TODO.md line range

**Where:** §2.1 CLI wiring ("Remove the `TODO(rust-cst-pyi)` comment (`genparser.py:279`)
and the `TODO.md` entry (l.27-29)").

**What's wrong:** At HEAD af6e6f3 the `## rust-cst-pyi` entry is `TODO.md:23-25`. Lines
27-29 are the `cst-protocol-label-free` entry. (The `genparser.py:279` cite is correct.)

**Consequence:** An implementer following the cited lines deletes the wrong TODO entry,
leaving the `rust-cst-pyi` entry orphaned and breaking the slug-join invariant of the
TODO system (CLAUDE.md).

**Suggested fix:** Reference the entry by slug, not line number.

---

## design-6 — Stub `NodeKind` "class (or enum.Enum subclass)" — the plain-class option is invalid

**Where:** §2.1 ("`NodeKind`: a class (or `enum.Enum` subclass) with one member per
rule... typed so the per-node `kind` annotation `Literal[NodeKind.X]` resolves").

**What's wrong:** `typing.Literal[...]` only accepts enum members (and
int/str/bytes/bool/None literals). If the stub's `NodeKind` is a plain class with
class attributes, `typing.Literal[NodeKind.GRAMMAR]` is an invalid Literal form and
pyright rejects it. Only the `enum.Enum` option works.

**Consequence:** An implementer taking the first listed option produces a `.pyi` that
fails the §4 self-check on every node class.

**Suggested fix:** Drop "a class (or" — require an `enum.Enum` subclass.

---

## design-7 — OQ-1 recommendation overstates what the `.pyi`-only self-check verifies

**Where:** §5 OQ-1 ("the `.pyi`-only pyright self-check, which already catches most
stub/protocol mismatches"); §2.1/§4 test plan.

**What's wrong:** The self-check (§4: "run pyright over the emitted `.pyi` alone, assert
zero errors (the stub is internally well-typed)") performs **no comparison against
`CstModule`** — it cannot catch any stub/protocol mismatch, only internal type errors in
the stub. No other §4 test (short of the possibly-deferred Part 2) relates the stub to
the protocol either; the content unit tests check names/shapes the emitter itself
produced. The claim is unsupported by anything in the design.

**Consequence:** If the user accepts recommendation (ii) on this stated basis, Part 1
lands with zero verification of the request's load-bearing constraint ("the `.pyi`'s
job is to let pyright confirm the real Rust surface matches that Protocol",
request.md), under the false impression that most of that assurance is already in hand.

**Suggested fix:** Either add a Part-1-scoped protocol-relation test (e.g. per-class
expected-diagnostics or cast-based member-access fixture over stub-typed nodes,
analogous to T2a) or state plainly that protocol conformance is entirely unverified
until Part 2.

---

## design-8 — Minor line-cite drift (informational)

- §1 cites `RustCstGenerator.generate` at `gsm2tree_rs.py:97-112`; actual `:114-130`.
- §2.1 cites `_protocol_class_for_model` at `gsm2tree.py:540-615`; actual `:540-641`
  (per-label accessor emission spans to 641).
- §1 cites the Rust-path cast at `plumbing.py:174-177`; actual `:173-175`.

**Consequence:** Low — methods exist and claims about them hold; drift only costs
implementer navigation time. Listed so the next revision can correct them.
