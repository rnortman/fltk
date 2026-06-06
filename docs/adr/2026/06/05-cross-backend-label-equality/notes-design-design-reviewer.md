# Design review — Cross-Backend Label Equality + NodeKind

Reviewer notes. Style: concise, precise, source-backed. Consequence stated per finding for severity weighting.

Base: a5cffc5 (working tree at HEAD 2258b08; `git merge-base --is-ancestor a5cffc5 HEAD` = yes; `git diff a5cffc5 -- fltk/fegen/fltk2gsm.py` empty, so file matches base). Verified design claims against working tree.

Most load-bearing claims hold. Verified: PyO3 0.23 (`Cargo.toml:15`); `PyAnyMethods::hash() -> PyResult<isize>` present (`~/.cargo/.../pyo3-0.23.5/src/types/any.rs:860`); `#[pyclass(eq,hash,frozen)]` + `#[derive(...)]` on every label enum (`gsm2tree_rs.py:152-153`); `eq` generates a `tp_richcompare` slot (`pyo3-macros-backend-0.23.5/src/pyclass.rs:422-429`), so a hand-written `__richcmp__`/`__eq__` slot conflicts — §2.3 "drop eq,hash to hand-write richcmp" is sound. `__repr__` canonical string `"{class_name}.Label.{NAME}"` confirmed (`gsm2tree_rs.py:166-172`). Python `Label(enum.Enum)` with `enum.auto()` confirmed (`gsm2tree.py:112-115`). `fltk2gsm.py` line refs (52-56,58,60,69,71-76,80,122-126,133-137) all match. isinstance-vs-label investigation §1 (ITEM↔Item 1:1, isinstance redundant) confirmed against `fltk_cst.py` `append_item`. `fltk._native.fegen_cst` submodule exists (`src/lib.rs:43`). Test files referenced all exist. Node `__eq__` hand-written pattern exists (`gsm2tree_rs.py:431-446`).

---

## design-1 — `child.kind` narrowing over a union containing non-node `Span` is unverified and likely a pyright error

**Section:** §2.5 ("Restore that narrowing with a `child.kind == NodeKind.Item` guard … falling back to a `typing.cast` only if narrowing is structurally unavailable"); §2.4 narrowing validation.

**What's wrong:** The design's load-bearing pyright validation (§2.4, §5) narrowed a `Union[Item, Term]` of two Protocols *both* carrying `kind: Literal[...]`. But the actual blocker site is `visit_items` (`fltk2gsm.py:68`), where `item` is destructured from `items.children` and statically typed `Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]` (`fltk_cst_protocol.py:102`; `fltk_cst.py:181`). `Span` (`fltk/fegen/pyrt/terminalsrc.py:8`) is a hand-written dataclass with **no `kind` attribute** and is not generator-emitted, so it will not receive one from this design. Writing `item.kind == NodeKind.Item` over that union makes pyright report attribute access on the `Span` (and `Trivia`, unless `Trivia` is generator-emitted with `kind`) arm where `.kind` is absent — i.e. the guard itself may not type-check, not just fail to narrow.

**Why:** Source: union annotation at `fltk_cst_protocol.py:102` / `fltk_cst.py:181`; `Span` has no `kind` (`terminalsrc.py`). The §2.4 pyright run did not include a non-`kind`-bearing union member, so it does not cover this case. The design validated the easy union and asserted the hard one by analogy.

**Consequence:** The primary in-tree demonstration (AC10, `self.cst` removal) runs through exactly this site. If the `kind` guard doesn't type-check over `Item | Trivia | Span`, the design's stated narrowing fix fails and the fallback becomes `typing.cast` at both sites — which is fine functionally but means the `NodeKind`/`kind` discriminant does **no** work at the only in-tree consumer it was introduced to serve (see design-2). `make check` (pyright) is a gate (§4); a guard that errors blocks the cycle until reworked.

**Suggested fix:** State explicitly that at `visit_items` the narrowing is done by `typing.cast` (the union includes non-node `Span`), and reserve the `kind`-guard pattern for unions of homogeneous node Protocols. Confirm with a pyright run on the actual `Item | Trivia | Span` union before committing to the `kind`-guard wording.

---

## design-2 — `NodeKind` + per-node `kind` is large generator surface with no exercised in-tree consumer this cycle

**Section:** §2.4 (entire `NodeKind` enum + `kind` discriminant on every node, Python concrete + Protocol + Rust getter + register); §2.6 files-touched.

**What's wrong:** Per the isinstance investigation (confirmed) the two `isinstance(item, self.cst.Item)` sites are *pure redundancy* — `item_label == cst.Items.Label.ITEM` is a total equivalence, so deletion + label check alone satisfies AC10. The `kind` discriminant is therefore not required to remove `self.cst`; and per design-1 it likely cannot even be used at those sites (union includes `Span`), so the in-tree fallback is `typing.cast`. That leaves `NodeKind`/`kind` with **zero** exercised in-tree consumer this cycle — it is built, type-checked, and tested (§4 NodeKind cross-backend matrix + pyright fixture) purely as standalone infrastructure.

**Why:** `notes-design-user.md:2,11-13` is the authority for `NodeKind` — it is a settled user steer, not reviewer-rejectable. But the steer settles the *mechanism*; it does not assert `NodeKind` is exercised by `fltk2gsm.py` this cycle. The design itself concedes the union case "does not arise at the current `fltk2gsm.py` blocker sites" (§2.4 caveat; `isinstance-vs-label-investigation.md:120-121`). Requirements.md never mention `NodeKind` (scope is `Label` members only — `requirements.md:21-23`).

**Consequence:** Not a defect to remove (user-settled), but flag the scope/sequencing: a substantial cross-cutting generator feature ships with its only validation being self-referential tests, while the requirements' actual demonstration (AC10) routes around it via `cast`. If `kind` codegen has a bug, nothing in the in-tree pipeline catches it beyond the bespoke NodeKind tests. Worth an explicit note that `kind` is delivered as forward infrastructure for out-of-tree union-narrowing (`notes-design-user.md:19`), not as the AC10 mechanism — so reviewers/implementers don't assume the parity tests cover it.

---

## design-3 — `NodeKind` canonical-name form unresolved in design body; introduces a collision axis not analyzed

**Section:** §2.1 ("`<ClassName>` for NodeKind members"); §2.4 ("Canonical name = `"NodeKind.<MEMBER>"` (or `"<ClassName>"`; pick one and emit identically on both sides)").

**What's wrong:** Two sections give two different canonical forms for `NodeKind` (`"<ClassName>"` in §2.1 vs `"NodeKind.<MEMBER>"`-or-`"<ClassName>"` in §2.4). This is left as "pick one" inside the design body — an unresolved implementation fork, not an open question. The two forms have different collision behavior: `"NodeKind.ITEM"` vs `"Item"` differ in whether a `NodeKind` member could ever collide with a `Label` canonical name or across the two enum families.

**Why:** Internal inconsistency between §2.1 and §2.4 (both this doc). Cross-grammar/cross-family collision for `Label` is analyzed (§3.8, Open Q §6.4) but the `NodeKind` canonical form — and whether `NodeKind` and `Label` members can compare equal to each other if their canonical strings ever coincide — is not. Since both families share the *same* §2.1 marker-based eq path, a `NodeKind` member and a `Label` member with equal canonical strings would compare `==`.

**Consequence:** Implementer must guess the canonical form; the two backends could pick differently → AC8-style cross-crate `NodeKind` equality silently breaks, or a `NodeKind` accidentally equals a `Label`. Low likelihood but the design explicitly defers the decision into code without pinning it.

**Suggested fix:** Pick the form (recommend a family-prefixed one, e.g. `"NodeKind.<MEMBER>"`, so `NodeKind` and `Label` canonical strings are disjoint by construction) and state it once. Note explicitly that the two families' canonical-name spaces must not overlap.

---

## design-4 — §2.3 conflates hand-written `__eq__` with `__richcmp__`; existing in-codebase precedent is `__eq__`, not `__richcmp__`

**Section:** §2.3 ("Hand-write … `__richcmp__(&self, other, op)`"); §5 ("The node-level hand-written `__eq__` already in the generator (`gsm2tree_rs.py:431-446`) demonstrates the richcmp-style pattern compiles").

**What's wrong:** The cited precedent (`gsm2tree_rs.py:431-446`, confirmed) is a plain `fn __eq__(&self, py, other: &Bound<PyAny>) -> PyResult<PyObject>` returning `NotImplemented` for foreign operands — it is **not** a `__richcmp__` with a `CompareOp`. The design prescribes `__richcmp__` for the label enum (to handle `Eq`/`Ne` and reject `Lt/Le/Gt/Ge`). These are different PyO3 slot shapes. The "demonstrates the pattern compiles" claim is therefore weaker than stated: it demonstrates the `__eq__`-returning-`NotImplemented` shape compiles, not the `__richcmp__`-with-`CompareOp` shape. `grep` confirms zero `__richcmp__`/`CompareOp` usage anywhere in `src/*.rs`.

**Why:** `gsm2tree_rs.py:431-446` (read) uses `fn __eq__`, no `CompareOp`. No `richcmp`/`CompareOp` in `src/cst_fegen.rs`/`cst_generated.rs` (grep, 0 hits). The node `__eq__` already deliberately omits hash (node `__hash__` raises — `gsm2tree_rs.py:448-454`), so it does not exercise the hash-slot interplay either.

**Consequence:** §2.3's compile-feasibility evidence is overstated. A plain `fn __eq__` would suffice for the label enum (Eq/Ne via Python's automatic `!=` from `__eq__`; `Lt/Le/Gt/Ge` simply absent → Python raises `TypeError` on ordering, which no requirement forbids — AC only covers `==`/`!=`/hash/membership). The `__richcmp__` route is more code and is the *unvalidated* shape. Recommend matching the existing `__eq__` precedent (which IS validated to compile) unless ordering rejection is actually needed — it is not per requirements §6/§7. If `__richcmp__` is kept, drop the claim that the node `__eq__` proves it compiles; it doesn't.

---

## design-5 — Performance SHOULD (same-backend hot path) only partly addressed for the Python side

**Section:** §2.2 (Python `__eq__` "compare canonical strings"); §2.3 (Rust "own-type fast path … variant compare, no string build"); requirements §Constraints Performance (`requirements.md:126`).

**What's wrong:** The Rust side gets an explicit own-type fast path (variant `PartialEq`, no string build) for the hot `children_X` filter. The Python side §2.2 describes `__eq__` as "compare canonical strings" with no same-type fast path — every same-backend `label == Class.Label.X` (run per child in `children_X`, `gsm2tree.py:201`) would build/compare the canonical string instead of an identity check. Requirements `requirements.md:126` is an explicit SHOULD: "avoid introducing per-comparison Python-object allocation or string formatting on the same-backend path."

**Why:** `gsm2tree.py:198-204` (read) emits `label == Class.Label.X` inside the `children_X` generator, invoked per child. §2.2 as written replaces identity `==` with string compare unconditionally. The design's own harness (§2.2) validated correctness but not that it avoids string work on the same-backend path.

**Consequence:** Measurable same-backend regression risk on CST traversal — the exact hot path requirements §126 flags. Non-gated (SHOULD), but the design claims to honor it ("Cross-backend path is O(canonical-name length)") while leaving the Python same-backend path doing string compares. Add a same-type fast path on the Python `__eq__` (e.g. `if other is self: return True` / `if type(other) is type(self): return self.name == other.name` before falling to the canonical-string path), mirroring the Rust own-type fast path.

---

## design-6 (minor) — AC8 third-module hash claim rests on per-process CPython salted hash; deferred, not validated

**Section:** §3.1; §5 ("Not yet built/run … the per-process hash agreement").

**What's wrong:** Correctly identified mitigation (route Rust hash through `PyString::hash` so both sides use the same salted CPython hash). But this is explicitly deferred/unbuilt (§5), and AC8 (`requirements.md:98`) additionally requires it across **two distinct Rust crates** (`fltk._native.fegen_cst` ↔ `fegen_rust_cst`). Both crates building a `PyString` and hashing via CPython in the same process will agree — but that relies on both crates linking the same CPython under abi3 and neither caching a Rust-side hash. The design asserts agreement without a built test.

**Why:** §5 lists it as deferred. `PyAnyMethods::hash` confirmed present (any.rs:860), so the API exists; the runtime agreement is the unproven part. Flagged honestly by the design itself.

**Consequence:** Low — it is correctly flagged as gated by the AC4/AC8 test. Noting only that AC8 (two Rust crates) is the riskier case and the §3.1 discussion only frames py↔rust; an implementer should pin AC8 hash equality with an actual test early, not assume it from the §3.1 py↔rust argument.

---

## Coverage check

Every requirements AC maps to a design section: AC1-AC7 → §2.2/§2.3 + §4; AC8 → §2.3 hash routing + §4; AC9/AC10 → §2.5 + §4; AC11 → §2.2 filter-compat + §3.7. Open questions §6.1-§6.5 map to requirements OQ 1-5. No requirement left uncovered. No bonus features beyond the user-settled `NodeKind` (design-2 flags it as unexercised-this-cycle, not out-of-scope). Constraints (no IntEnum, hash/eq lockstep, symmetry/non-raising, co-generation) all reflected.
