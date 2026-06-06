# Requirements Review — Cross-Backend Label Equality

Adversarial review of `requirements.md` against request + `exploration.md`. Big-picture sanity check.
Style note (for any agent editing this doc): concise, precise, unambiguous. No padding.

---

## requirements-1 — §Constraints / "Performance" pin over-specifies implementation

**Quote:** "(Pin: precompute/intern the canonical key rather than formatting it on each `__eq__`.)" and §107 "equality is computed from the canonical name each side already knows."

**What's wrong:** The performance section states a real observable constraint (no meaningful same-backend regression; cross-backend O(len) at worst), which is legitimate. But the parenthetical "Pin: precompute/intern the canonical key rather than formatting it on each `__eq__`" prescribes the mechanism — that the designer must precompute/intern rather than format-on-demand. That is a design decision. The request explicitly says "Mechanism is design's call."

**Why:** Request: "Mechanism is design's call." Requirements §108 names a specific caching strategy.

**Consequence:** Designer is boxed into intern/precompute even if e.g. a static `match`-based string return (already what Rust `__repr__` does — a `&'static str`, zero allocation, exploration §84-96) or a cheaper integer-keyed scheme satisfies the perf budget. The observable budget (no meaningful regression) is the real requirement; the technique should not be.

**Fix:** Keep the perf budget as observable behavior; delete or demote the "Pin:" mechanism note to a non-binding design hint, or move it to the design doc.

---

## requirements-2 — Performance budget lacks a falsifiable threshold

**Quote:** §108 "Same-backend comparison must not regress meaningfully"; §70 AC11 "continue to return the same results."

**What's wrong:** "must not regress meaningfully" is the only perf criterion and it is not an acceptance criterion — there is no AC for it, and "meaningfully" is undefined. Exploration §54, §70 establish that `children_X` filters run `==` per child during traversal (hot path). A correctness-only AC set (AC1-9) lets a design pass review while silently adding, e.g., a Python `__eq__` that does string formatting per comparison on the hottest path.

**Why:** §108 calls these "hot paths ... run per child during CST traversal" but no AC measures it; AC11 only checks result-equivalence, not cost.

**Consequence:** A functionally-correct but slow design (per-comparison allocation/formatting) passes all ACs. The one constraint that motivated the "no IntEnum / precompute" discussion is unenforceable. Either the perf concern is real (then make it measurable/an AC) or it is not (then drop the mechanism pin in requirements-1).

**Fix:** Either add a coarse, testable perf AC (e.g. same-backend filter on N children within X% of baseline) or explicitly downgrade perf to "design SHOULD avoid per-comparison allocation," acknowledging it is non-blocking.

---

## requirements-3 — Symmetry depends on Python-enum side, not just Rust richcmp; requirement under-covers it

**Quote:** §50 "Equality is symmetric ... (`py == rust` and `rust == py`)"; §104 "the Rust `#[pyclass(eq, hash, frozen)]` derive ... must be replaced/supplemented with a custom richcmp."

**What's wrong:** The doc frames symmetry as primarily a Rust-richcmp problem. But exploration §38, §233 establish the Python side is a plain `enum.Enum` whose `__eq__` is identity-based and returns `NotImplemented`/`False` against foreign types. For `py == rust` to be `True`, the **Python** label's `__eq__` must also be overridden (a bare `enum.Enum` will never delegate to a canonical name). The requirement correctly demands the symmetric behavior (AC1, AC7), so this is not a behavioral gap — but the rationale text in §104 names only the Rust side as needing change, which could mislead the designer into a Rust-only fix that fails AC1 in the `py == rust` direction (Python evaluates its own `__eq__` first and short-circuits to `False` before Rust's reflected richcmp is consulted... unless Python returns `NotImplemented`).

**Why:** Exploration §240-242: "Python `enum.Enum.__eq__` compares by identity/class membership." A Rust-only change cannot make `py.NO_WS == rust.NO_WS` return `True` unless the Python `__eq__` yields `NotImplemented` (it returns `False` for same-enum-class mismatch? — actually returns `NotImplemented` for non-members, letting reflected op run). This subtlety is load-bearing for AC1 and is not surfaced.

**Consequence:** Designer reads §104 ("replace the Rust derive"), implements custom Rust richcmp only, and AC1's `py == rust` direction silently fails because Python's `enum.Enum.__eq__` short-circuits. Caught only at test time, possibly mis-diagnosed.

**Fix:** In §104, note that BOTH generators must emit custom `__eq__` (Python enum override + Rust richcmp); symmetry requires the Python side to yield `NotImplemented` (not `False`) so the reflected Rust comparison runs. Behavior is already correctly specified in ACs; only the rationale needs the both-sides note.

---

## requirements-4 — AC7 "`== False`" wording collides with the "returns `NotImplemented`" allowance

**Quote:** §56 "It returns `False` for `==` (equivalently, returns `NotImplemented` from `__eq__` so Python falls back to identity → `False`)"; AC7 §84 "All `==` are `False`."

**What's wrong:** This is internally consistent for the *unrelated-object* case (None, int, object()) where identity fallback gives `False`. But for the `== rust.Disposition.Label.INCLUDE` case (different rule, AC7 §84) and `== "Items.Label.NO_WS"` (AC7 §84) the design must return `False` *as a value*, not `NotImplemented` — because for a cross-backend label pair, returning `NotImplemented` from both sides would fall back to identity, which is correctly `False` here, fine — but the parenthetical "equivalently returns NotImplemented" is only safe when identity-fallback yields the same answer. For two labels that SHOULD be equal but the eq logic returns `NotImplemented`, the fallback gives `False` (wrong). The doc treats `False` and `NotImplemented` as interchangeable; they are only interchangeable for the not-equal cases.

**Why:** §56 explicitly equates them ("equivalently"). They are equivalent only when the correct answer is `False`. For the equal-cases (AC1) `NotImplemented`-from-both would be a bug.

**Consequence:** Low risk (AC1 forces the equal case to be `True`), but the "equivalently" framing invites a designer to return `NotImplemented` uniformly, which breaks AC1 if the *other* side also returns `NotImplemented`. Worth a clarifying sentence: `NotImplemented` is acceptable ONLY for the not-a-label / different-canonical-name cases.

**Fix:** Constrain the parenthetical: returning `NotImplemented` is acceptable only where the correct result is `False`; the equal case must return `True` from at least one side's `__eq__`.

---

## requirements-5 — Premise check: is this worth building? Exploration says the real consumer never triggers it.

**Quote (exploration):** §146 "cross-backend equality is NOT required for `fltk2gsm.py` with `self.cst = fegen_rust_cst`"; §202 "currently, same-backend comparisons always work; the cross-backend equality goal is about a DIFFERENT scenario"; §204 "user code that holds a label from one backend ... and then tests it against a constant from the other backend ... This is the 'drop-in goal'."

**What's wrong:** Exploration repeatedly establishes that the primary internal consumer (`fltk2gsm.py`, `bootstrap2gsm.py`, generated `children_X` filters, all current tests) is **same-backend by construction** and does not need cross-backend equality. The only scenario that needs it is hypothetical external "user code that explicitly mixes backends" (§204, §258). The requirements doc does not surface this — it presents AC9 (`Cst2Gsm` mixed-backend) as a real consumer, but exploration §146/§201 says `Cst2Gsm` stores labels and compares constants from the *same* `self.cst`, so AC9's mixed scenario (`self.cst = B` while CST built with `A`) is a *synthetic* test, not a real usage path.

This is a request-spirit question, not a veto: the request explicitly asks for the drop-in property "so existing downstream comparisons keep working regardless of backend." That is a reasonable forward-looking robustness goal. But the requirements doc should state plainly that **no current in-tree consumer exercises the cross-backend path** (per exploration), so the value is future-proofing / external-consumer ergonomics, and AC9 is a constructed demonstration rather than a regression guard. Hiding this risks the project being scoped/sold as fixing a present bug when exploration says there is none today.

**Why:** Exploration §178 "No existing test checks cross-backend label equality"; §218 "Zero tests verify cross-backend label equality today"; §146, §201-202.

**Consequence:** Without stating the premise, a reader (or future maintainer) assumes this fixes a live breakage. If priorities shift, the work could be deprioritized correctly — or over-invested in (e.g. the perf pin) — based on a false sense of urgency. Also affects open-question 4 (cross-grammar collision): if no real consumer mixes backends, the collision risk is even more theoretical.

**Fix:** Add one line under Goals or a "Motivation/premise" note: per exploration, no current in-tree consumer requires cross-backend equality (all are same-backend by construction); this requirement future-proofs the drop-in contract for external/mixed-backend consumers. AC9 is a constructed demonstration of the property, not a guard against a current regression.

---

## requirements-6 — Open question 4 (cross-grammar collision) has a buried correctness consequence

**Quote:** §128-130 open question 4; §38 "two members from different grammars ... are not equal even if `<LABEL_NAME>` coincides, because `<ClassName>` ... differ — except where two distinct rules legitimately share the same `<ClassName>.Label.<LABEL_NAME>`."

**What's wrong:** §38 asserts different grammars produce non-equal labels "because `<ClassName>` ... differ" — but that is false in general: two unrelated grammars can both define a rule named `Items` with label `NO_WS`, giving identical canonical name `"Items.Label.NO_WS"` and thus spurious equality. §38 states the safe case and open-question 4 admits the unsafe case; they contradict in tone. The definition section (§38) should not assert non-equality "because ClassName differs" when OQ4 concedes ClassName can collide.

**Why:** §128 "Two unrelated grammars could each define `Items.Label.NO_WS`; their canonical names would be identical and thus compare equal." This directly contradicts §38's reassurance.

**Consequence:** If the design is built on §38's framing (ClassName disambiguates grammars) and OQ4 is later resolved "accept collision," a single process loading two grammars' CSTs gets silently-wrong label equality with no error. Low practical likelihood but a genuine soundness hole the definition currently papers over.

**Fix:** Align §38 with OQ4: state plainly that canonical name is rule+label scoped and does NOT encode grammar identity, so cross-grammar collision is possible and is explicitly accepted (or resolved per OQ4) — do not imply ClassName provides grammar-level disambiguation.

---

## requirements-7 — AC9 leans on `Cst2Gsm` internals contradicted by the isinstance coupling

**Quote:** AC9 §86 "`Cst2Gsm` ... produces identical `gsm.Grammar` output when a CST parsed/built with backend `A`'s labels is processed with `self.cst = B`'s module, for any `A`/`B`."

**What's wrong:** Exploration §182-195 (the isinstance constraint, explicitly in-scope-as-unchanged per request) shows `fltk2gsm.py:69,80` does `isinstance(item, self.cst.Item)` alongside the label compare. If a CST is built with backend `A` and `self.cst = B`, the `isinstance` check against `B`'s native PyO3 type returns `False` even after labels compare equal — so `Cst2Gsm` will NOT produce identical output "for any `A`/`B`"; it will assert-fail or mis-dispatch on the isinstance line. AC9 as written ("for any `A`/`B`") is unachievable given the explicitly-out-of-scope isinstance behavior.

**Why:** Request: "does NOT eliminate self.cst isinstance dispatch (out of scope)." Exploration §192 "If `item` came from the Python backend, this would be `False`"; §195 "cross-backend label equality is only meaningful when nodes AND their stored labels come from the SAME backend."

**Consequence:** AC9 is a contradiction: it demands a mixed-backend `Cst2Gsm` round-trip that the unchanged isinstance dispatch makes impossible. A designer either (a) wastes effort trying to satisfy an unsatisfiable AC, or (b) reads AC9 as license to touch isinstance dispatch (explicitly out of scope). The realistic AC9 is the *same-backend* `Cst2Gsm` path (labels + nodes + `self.cst` all from one backend), which is what exploration §197-202 describes as the actual scenario.

**Fix:** Narrow AC9: `Cst2Gsm` output is identical across backends when CST, its stored labels, and `self.cst` are all from one backend `B` (the real injection pattern), AND when external code holds a label from `A` and compares to `B`'s constant the label compare succeeds. Drop the "for any `A`/`B`" mixed CST-vs-`self.cst` claim, or explicitly note it is bounded by the unchanged isinstance dispatch (the parenthetical in §86 "no longer depend on backend matching" overstates this).

---

## Big picture

Core contract (AC1-8: cross-backend eq/hash/membership keyed on canonical name, non-raising, hash-consistent) is sound, well-specified, and matches the request faithfully. The canonical-name key already exists on the Rust side (exploration §94), so the mechanism is plausible and cheap. Main issues are (a) the premise is undersold — exploration says no current consumer needs this (requirements-5), worth stating so the work is scoped as future-proofing; (b) AC9 overreaches into a mixed scenario the unchanged isinstance dispatch forbids (requirements-7); (c) the perf "Pin" over-specifies mechanism against the request's "design's call" (requirements-1/2); (d) the symmetry rationale undersells the Python-side override (requirements-3). None are vetoes. Fixing AC9's scope and stating the premise are the two that most affect whether the right thing gets built.
