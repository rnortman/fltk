# Judge verdict — design (rerun)

Phase: design. Doc: `design.md` (cross-backend-label-equality). Round 1.
Notes: `notes-design-design-reviewer-rerun.md` (3 findings: design-1/2/3).

> Style: concise, precise, unambiguous. No padding.

**Input note:** the prompt named `dispositions-design-rerun.md`; no such file exists in the dir. The only dispositions doc on disk is `dispositions-design.md`, which is the **round-1** dispositions keyed to the *original* `notes-design-design-reviewer.md` (design-1..6), not the rerun notes (design-1..3, distinct findings). Adjudication therefore runs each rerun finding directly against the design as ground truth (design-phase mode: doc is the source). Result is unaffected — the design already incorporates every fix the rerun review prescribes.

## Findings walk

### rerun design-1 — `ClassVar` concrete `kind` fails the Protocol (pyright-verified)
Reviewer claim: §2.4 offered `ClassVar` as a/the form for concrete `kind`; pyright rejects a `ClassVar` concrete attr against an instance-attr Protocol member (`error: "kind" is not defined as a ClassVar in protocol`), breaking `fltk_cst ⊨ cst.CstModule` and the `fltk2gsm.py:18` cast. Consequence: hard `make check` gate failure. Fix: mandate instance-attr (dataclass field with default), state it so it isn't "optimized" back to `ClassVar`.
Evidence (design as ground truth): §2.4 line 99 reads "an **instance attribute** (dataclass field) `kind: typing.Literal[NodeKind.<Rule>] = NodeKind.<Rule>`. **MUST NOT be `ClassVar`**" — quotes the exact pyright error, names the broken cast (`fltk2gsm.py:18`), records the `__init__`/`__eq__` side effects (harmless: keyword default; parser builds via `node_type()` no-args, `gsm2parser.py:448`), and closes with "Do not 'optimize' this to `ClassVar`." The "or instance attr" interchangeable wording the reviewer flagged is **absent** from the current text.
Assessment: finding is real (pyright reasoning sound — `ClassVar`-vs-instance Protocol mismatch is a genuine reportArgumentType failure) and the design fully adopts the prescribed fix, including the anti-optimization warning. Resolved.

### rerun design-2 — marker mechanism: type-level lookup vs member value (self-inconsistent)
Reviewer claim: §2.2 read off `type(other)` (class-level staticmethod) then "compare strings" conflates a type-level lookup with a member-specific value; the call/resolution step was omitted; Python and Rust emitters could assume different conventions → silent `NotImplemented`/`False` cross-backend, surfacing only in not-yet-built tests. Fix: pin one convention — instance-resolved read, identical read+invoke shape both generators emit.
Evidence: §2.1 lines 54-57 now pin **`_fltk_canonical_name`** as "an **instance-resolved read returning the member's own canonical string**" read off "the **operand instance `other`, never `type(other)`**"; "a `staticmethod`/classmethod is **forbidden** — it would not be member-specific"; "no separate call ... is needed" (value/property, not method). Line 57 states "the **identical** read shape both generators emit" and §2.3 line 87 has the Rust side doing the same `getattr(other, "_fltk_canonical_name")` attribute read, "not a method call." The type-vs-member ambiguity and the staticmethod fork are explicitly closed.
Assessment: finding is real (the cross-backend marker contract is exactly the surface where silent divergence hides) and the design pins one unambiguous convention identically on both emitters. Resolved.

### rerun design-3 — marker scope unstated; node `kind` family collision
Reviewer claim: marker read by duck typing off arbitrary operands; design never stated nodes (which now all carry a `kind` enum and participate in user `==`) do not expose the marker. Risk: a shared mixin exposing the marker on nodes routes `node == label` through the canonical path. Fix: state explicitly the marker is on `Label`/`NodeKind` members only, never node classes; node `__eq__` stays structural.
Evidence: §2.1 line 64 ("Marker scope") states `_fltk_canonical_name` is "emitted **only** on `Label` and `NodeKind` enum members — **never on node classes**," walks `node == label → getattr(node, ...) → None → NotImplemented → False`, and adds "Implementers MUST NOT add the marker via a shared base/mixin that node classes also inherit." §3.3 line 141 cross-confirms. The node-family distinction the reviewer asked for is now explicit.
Assessment: finding is real (low-likelihood but previously unstated invariant a reviewer could not confirm) and the design states it explicitly with an implementer prohibition. Resolved.

## Disputed items

None.

## Approved

3 rerun findings (design-1/2/3): all real, all resolved in the revised design.md. design-1 pyright-grounded; design-2/3 close cross-backend marker-contract spec gaps. No groundedness failures, no scope creep beyond user-settled framework features (`notes-design-user.md`).

---

## Verdict: APPROVED

All three rerun findings are sound and the revised `design.md` adopts each prescribed fix verbatim-in-spirit (instance-attr `kind`, instance-resolved `_fltk_canonical_name` pinned identically both backends, marker scoped off nodes). No disposition wrong; nothing disputed.
