# Judge verdict — design review

Phase: design. Doc: `design.md` (cross-backend label equality + NodeKind). Round 1.
Notes: 1 reviewer file; 6 findings (design-1..6), all dispositioned Fixed. No TODOs (design phase).

> Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

Verified independently against working tree: union annotation `Item | Trivia | Span` (`fltk_cst_protocol.py:102`); `Span` frozen dataclass has no `kind` (`terminalsrc.py:8-13`, fields `start`/`end`/`_source`); node `_eq_method` is a plain `fn __eq__(&self, py, other: &Bound<PyAny>) -> PyResult<PyObject>` returning `py.NotImplemented()` for foreign operands (`gsm2tree_rs.py:431-446`); node `__hash__` raises (`gsm2tree_rs.py:448-454`); `richcmp`/`CompareOp` absent from `src/*.rs` (grep, 0 hits); `visit_items` isinstance sites present (`fltk2gsm.py:69,80`); requirements AC scope confirmed (`requirements.md:21-23,91-98,126`).

## Other findings walk

### design-1 — Fixed
Claim: §2.5 `kind`-guard over `visit_items` union `Item | Trivia | Span` does not type-check (`Span` has no `kind`); consequence — the prescribed narrowing fix fails `make check` (pyright gate, §4), blocking the cycle; `kind`/`NodeKind` does no work at its only in-tree consumer.
Disposition action: rewrote §2.5 to use `typing.cast("cst.Item", item)` at the two isinstance sites, NOT a `kind`-guard; tightened §2.4 to a homogeneous-union scope limit; updated §5 empirical bullets (b)/(c).
Evidence: design body §2.5 and §2.4 now state the `cast` decision and the scope limit explicitly; §5(b)/(c) record the pyright 1.1.402 result (`Item|Trivia|Span` → 2 errors; `cast` → 0; homogeneous `Item|Term` → 0). Source facts driving the claim independently confirmed: union at `fltk_cst_protocol.py:102` includes `Span`; `Span` (frozen dataclass, `terminalsrc.py:8`) has no `kind`. The `cast` targets the `TYPE_CHECKING` Protocol type, needs no `self.cst` → AC10 full-removal (`requirements.md:103`) stays closed.
Assessment: fix addresses the consequence; the failing guard is removed at the named site and replaced with the validated `cast`. Accept.

### design-2 — Fixed
Claim: `NodeKind`/`kind` ships with zero exercised in-tree consumer this cycle (AC10 routes around it via `cast`); risk is a sequencing/expectation gap, not a defect to remove (user-settled, `notes-design-user.md:2,11-13`).
Disposition action: added a §2.4 "Scope note" stating `kind` ships as forward infrastructure for out-of-tree homogeneous-union narrowing, not the AC10 mechanism; its only validation is the dedicated `NodeKind` matrix + pyright fixture; parity tests do not cover `kind`.
Evidence: §2.4 Scope note present and says exactly this. Reviewer itself classified this as non-rejectable (user steer governs the mechanism). Requirements scope confirmed `Label`-only (`requirements.md:21-23`); steer mandates `NodeKind` as a framework feature emitted for every grammar (`notes-design-user.md:4,7,11-13`) — so building it this cycle without an in-tree consumer is the settled direction, not over-build. Documentation-only finding, documentation-only fix.
Assessment: consequence (false assumption that parity tests cover `kind`) is neutralized by the explicit note. Accept.

### design-3 — Fixed
Claim: §2.1 (`"<ClassName>"`) and §2.4 (`"NodeKind.<MEMBER>"`-or-`"<ClassName>"`) give two canonical forms for `NodeKind`, left as an in-body "pick one" fork; consequence — implementer/backends could diverge → AC8-style cross-crate `NodeKind` equality breaks, or a `NodeKind` accidentally `==` a `Label`.
Disposition action: pinned `"NodeKind.<MEMBER>"` once in §2.1 (added "Family disjointness" para) and §2.4 (removed the fork).
Evidence: §2.1 now states the family-prefixed form as a hard requirement and proves disjointness by construction — every `Label` string contains `".Label."`, no `NodeKind` string does. §2.4 emits "this exact form identically on both backends." The "pick one" fork is gone. This is the reviewer's own recommended form (family-prefixed). The shared §2.1 marker-based eq path means disjoint canonical strings is the correct cure for cross-family accidental equality.
Assessment: the deferred-into-code decision is now pinned; both divergence axes (cross-crate and cross-family) closed. Accept.

### design-4 — Fixed
Claim: §2.3 prescribed `__richcmp__`-with-`CompareOp` but §5 cited a plain `fn __eq__` (`gsm2tree_rs.py:431-446`) as compile proof — different PyO3 slot shapes; `__richcmp__`/`CompareOp` is absent from the codebase (unvalidated). Consequence — §5 compile-feasibility evidence overstated.
Disposition action: changed §2.3 to prescribe a plain `fn __eq__(&self, py, other) -> PyResult<PyObject>` matching the validated precedent; corrected §5 to "exactly the slot shape §2.3 prescribes"; noted `__richcmp__`/`CompareOp` 0 hits; rationale — no AC covers ordering (`requirements.md:91-98`), Python derives `!=` from `__eq__`.
Evidence: independently confirmed — node `_eq_method` IS a plain `fn __eq__` returning `py.NotImplemented()` for foreign operands (`gsm2tree_rs.py:431-446`), not a `__richcmp__`; grep for `richcmp`/`CompareOp` in `src/*.rs` = 0 hits. Design §2.3/§5 now reflect the plain-`__eq__` shape. AC matrix (`requirements.md:91-98`) covers only `==`/`!=`/hash/membership — no ordering, so dropping `__richcmp__` loses nothing required.
Steer check: `notes-design-user.md:8` and `requirements.md:122` say "richcmp." The steer's load-bearing intent is hand-written, foreign-operand-tolerant equality (the parenthetical: "derived `#[pyclass(eq,hash)]` is same-type only"); "richcmp" names the PyO3 mechanism, and a PyO3 `fn __eq__` generates the same `tp_richcompare` slot. No ordering was required by the steer. Switching to the in-codebase-validated `__eq__` shape realizes the steer's intent and is surfaced explicitly (§2.3, §5) — the steer instructs designing-within and working out details, exactly this. Not a silent divergence.
Assessment: overstated evidence corrected; prescribed shape is the validated one. Accept.

### design-5 — Fixed
Claim: §2.2 replaced same-backend identity `==` with unconditional canonical-string compare on the hot `children_X` per-child path (`gsm2tree.py:201`), while claiming to honor the perf SHOULD (`requirements.md:126`). Consequence — measurable same-backend traversal regression risk on the exact path §126 flags.
Disposition action: added a same-type fast path to Python `__eq__` in §2.2 — `if other is self: return True`; then `if type(other) is type(self): return self.name == other.name` (no string build), mirroring the Rust own-type fast path; reconciled §2.2 filter-compat/empirical and §3.7.
Evidence: §2.2 now states the fast path first, cross-type falls through to canonical-string compare only. The fast path is `enum.Enum`'s own identity/name semantics restated → same-backend results preserved by construction, pinned by AC3 (`requirements.md:93`) and existing same-backend filter tests (§3.7). The Rust side already had its own-type fast path (§2.3); the asymmetry the reviewer flagged is closed. SHOULD is non-gated, but the fix matches the design's own stated honoring of §126.
Assessment: hot-path string work removed on the same-backend path; consequence addressed. Accept.

### design-6 (minor) — Fixed
Claim: AC8 (`requirements.md:98`) hash agreement spans two distinct Rust crates (`fltk._native.fegen_cst` ↔ `fegen_rust_cst`); §3.1 frames the argument only py↔rust; the two-crate runtime agreement is asserted, not tested.
Disposition action: extended §5 "Not yet built/run" to call out the AC8 two-crate case explicitly (distinct cdylibs linking the same abi3 CPython, both routing `__hash__` through `PyString::hash`), and to instruct pinning AC8 hash equality with an actual cross-crate test early rather than inferring it from §3.1.
Evidence: §5 now contains the two-crate callout and the early-test instruction. `PyAnyMethods::hash` confirmed present by the reviewer (`any.rs:860`); the mechanism (route through CPython's salted hash) is correct, and the residual is purely the deferred test — which the design flags honestly. Reviewer rated this Low. Fix is a documentation sharpening of an already-flagged deferral, which is the right disposition for a deferred-but-unbuilt design item.
Assessment: the riskier two-crate case is now explicitly surfaced for early test pinning. Accept.

## Disputed items

None.

## Approved

6 findings: 6 Fixed verified (design-1 load-bearing narrowing→`cast`; design-2 scope note; design-3 canonical form pinned; design-4 slot shape corrected to validated `__eq__`; design-5 Python same-type fast path; design-6 AC8 two-crate deferral sharpened).

---

## Verdict: APPROVED

All six dispositions acceptable. design-1 (load-bearing, blocks `make check` if unfixed) corrected to the validated `cast` with source facts independently confirmed. design-4's switch from `__richcmp__` to plain `__eq__` realizes the user steer's intent (hand-written foreign-tolerant equality) using the only in-codebase-validated slot shape, and is surfaced explicitly — not a silent divergence. No scope-N pile, no fundamental disagreement.
