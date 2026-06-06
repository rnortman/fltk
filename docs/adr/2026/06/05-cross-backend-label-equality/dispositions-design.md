# Dispositions — Design Review (round 1)

**Date:** 2026-06-05
**Design:** `design.md` (this dir). **Notes:** `notes-design-design-reviewer.md`.

> Style note (for any agent editing this doc): concise, precise, unambiguous. No padding. State the disposition, the action + location, and the severity.

Each finding fact-checked against working tree / pyright / requirements before disposition. Empirical re-verification of the load-bearing design-1 claim performed (pyright 1.1.402, project env).

---

design-1:
- Disposition: Fixed
- Action: Rewrote §2.5 isinstance-site narrowing to use `typing.cast` (NOT a `kind`-guard); tightened §2.4 "Pyright narrowing" to a homogeneous-union scope limit; updated §5 empirical bullet (b)/(c) and §2.4 union-narrowing caveat. The `kind`-guard is now explicitly reserved for unions of homogeneous `kind`-bearing node Protocols; the `Span`-bearing `visit_items` union uses `cast`.
- Severity assessment: Load-bearing — runs through the only in-tree AC10 demonstration site (`visit_items`). Empirically confirmed against pyright 1.1.402 (not by analogy): `item.kind == NodeKind.ITEM` over the real `Item | Trivia | Span` union (`fltk_cst_protocol.py:102`) produces `error: Cannot access attribute "kind" for class "Span"` and does not eliminate `Span` from the narrowed branch (revealed `Item | Span`), so the body access also errors. `typing.cast("cst.Item", item)` over the same union: 0 errors. Homogeneous `Item | Term`: `kind`-guard narrows cleanly (0 errors). An uncorrected design would have specified a guard that fails `make check` (a §4 gate), blocking the cycle. The fix is functional and keeps the AC10 full-removal escape (`requirements.md:103`) closed: `cast` targets the `TYPE_CHECKING` Protocol type and needs no `self.cst`.

design-2:
- Disposition: Fixed
- Action: Added a "Scope note" block in §2.4 stating `NodeKind`/`kind` ships as forward infrastructure for out-of-tree homogeneous-union narrowing, NOT as the AC10 mechanism (which routes around it via `cast`); its only validation this cycle is the dedicated `NodeKind` matrix + pyright fixture (§4), and the `test_*_rust_equals_python` parity tests do not cover `kind`.
- Severity assessment: Not a defect to remove — `NodeKind` is user-settled (`notes-design-user.md:2,11-13`), so it is not reviewer-rejectable; the steer settles the mechanism but does not claim in-tree exercise this cycle. Confirmed requirements scope is `Label` members only (`requirements.md:21-23`). The risk is a sequencing/expectation gap: a cross-cutting generator feature whose in-tree consumer routes around it via `cast`. The added note prevents implementers/reviewers from assuming parity tests cover `kind` codegen. Low consequence, documentation-only.

design-3:
- Disposition: Fixed
- Action: Pinned the `NodeKind` canonical form to `"NodeKind.<MEMBER>"` once, in §2.1 (added a "Family disjointness" paragraph) and §2.4 (removed the "pick one" fork). The two families' canonical-name spaces are now disjoint by construction: every `Label` string contains `".Label."`, no `NodeKind` string does, so no `NodeKind` member can ever `==` a `Label` member.
- Severity assessment: Real internal inconsistency — §2.1 said `"<ClassName>"`, §2.4 said `"NodeKind.<MEMBER>"`-or-`"<ClassName>"`, left as an in-body "pick one" fork rather than a decision. Both backends co-generate the key; divergent choices would silently break AC8-style cross-crate `NodeKind` equality, and `"<ClassName>"` (e.g. `"Item"`) risks no overlap with `Label` but provides weaker disjointness guarantees than the family-prefixed form. Pinning eliminates the implementer guess and the cross-family accidental-equality axis. Low likelihood, but the design had genuinely deferred a decision into code.

design-4:
- Disposition: Fixed
- Action: Changed §2.3 to prescribe a plain `fn __eq__(&self, py, other) -> PyResult<PyObject>` (matching the validated in-codebase precedent `gsm2tree_rs.py:431-446`), NOT a `__richcmp__`-with-`CompareOp`. Rationale added: no AC covers ordering (AC1–AC11 only `==`/`!=`/hash/membership, `requirements.md:91-98`); Python derives `!=` from `__eq__`; ordering operators remain absent (TypeError on `<`, forbidden by no requirement). Corrected the overstated §5 claim — the node `__eq__` precedent now demonstrates "exactly the slot shape §2.3 prescribes," and the doc notes `__richcmp__`/`CompareOp` appears nowhere in `src/*.rs` (grep, 0 hits). Updated §2.3 heading, §2.6, §3.6, §3.7, and the §2.1/§2.2 cross-references from "richcmp" to "`__eq__`".
- Severity assessment: The original §5 compile-feasibility evidence was overstated — it cited a plain `fn __eq__` (verified at `gsm2tree_rs.py:431-446`) as proof a `__richcmp__`-with-`CompareOp` compiles; those are different PyO3 slot shapes, and `__richcmp__`/`CompareOp` is verified absent from all Rust sources (grep, 0 hits), i.e. unvalidated in this codebase. Switching to the plain-`__eq__` shape adopts the validated route and is less code. Functional consequence of the original: implementer writes an unvalidated slot shape; if it failed to compile, the build gate catches it, but the design's evidence would have been a false positive.

design-5:
- Disposition: Fixed
- Action: Added a same-type fast path to the Python `__eq__` in §2.2: `if other is self: return True`; then `if type(other) is type(self): return self.name == other.name` (member-name compare, no canonical-string build), mirroring the Rust own-type fast path. Only the cross-type case falls through to the canonical-string compare. Reconciled the §2.2 "Filter compatibility" and "Empirical validation" paragraphs (which had said same-backend "compares canonical strings") and §3.7 to match.
- Severity assessment: Non-gated SHOULD (`requirements.md:126`), but the original §2.2 replaced same-backend identity `==` with unconditional canonical-string compare on the hot `children_X` per-child path (`gsm2tree.py:201`) — a measurable same-backend traversal regression risk, and the design claimed to honor the perf SHOULD while doing so. The fast path is `enum.Enum`'s own identity/name semantics restated, so it preserves same-backend results by construction (pinned by AC3 + existing same-backend filter tests). Correctness-neutral, perf-positive.

design-6:
- Disposition: Fixed
- Action: Extended §5 "Not yet built/run" to call out the AC8 two-crate case explicitly (`fltk._native.fegen_cst` ↔ `fegen_rust_cst`, distinct cdylib crates linking the same abi3 CPython): both routing `__hash__` through `PyString::hash` will agree in-process, but this is unproven without a built test; instruct pinning AC8 hash equality with an actual cross-crate test early, not inferring it from the §3.1 py↔rust argument.
- Severity assessment: Low — the mitigation (route Rust hash through `PyString::hash` so both sides use the same salted CPython hash) is correct and `PyAnyMethods::hash` is confirmed present (`any.rs:860`); the design already flagged it as deferred/gated by the AC4/AC8 test. The only gap was that §3.1 framed the argument py↔rust while AC8 additionally spans two Rust crates; the runtime agreement there is the riskier unproven case. Now explicitly flagged for early test pinning.
