# Requirements Review: Phase 2 Nested Enum PoC

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## requirements-1

**Section:** "Generic methods" — `node.child()` returns `node.children[0]`

**What's wrong:** The requirements doc says `node.child()` returns `node.children[0]` (the tuple), but it omits the return type — `(label, child)` tuple — from the description. More importantly, the **Python CST `child()` method** (`explore-cst-interface.md` section 5, `gsm2tree.py`) returns the *tuple* `self.children[0]`. This is correct. However, Acceptance Criterion 19 says "With exactly one child, returns the `(label, child)` tuple" — which is consistent. No actual bug, but the system-behavior section uses imprecise language ("returns `node.children[0]`" without saying what that *is*) while AC 19 is precise. Minor clarity issue.

**Consequence:** Implementer might return only the child value instead of the tuple if they read the system-behavior section in isolation.

**Suggested fix:** In "Generic methods," change to: `node.child()` returns the single element of `node.children` — a `(label, child)` 2-tuple — if `len(node.children) == 1`, otherwise raises `ValueError`.

---

## requirements-2

**Section:** "Per-label methods (`Items`)" — missing `extend_<label>` from AC 25

**What's wrong:** Acceptance Criterion 25 lists `append_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>` — but omits `extend_<label>`. The system-behavior section ("Same five-method pattern for each label") correctly specifies five methods, and the in-scope section lists all five. AC 25 silently drops one.

**Why:** The five-method pattern is stated in multiple places: in-scope bullet, system-behavior section, and Identifier per-label section (ACs 10-15 cover them individually). For Items, AC 25 tries to compress all four labels into one criterion but loses `extend_<label>`.

**Consequence:** An implementer treating ACs as the sole checklist might skip `extend_item`, `extend_no_ws`, `extend_ws_allowed`, `extend_ws_required` — or a reviewer might pass a PR that lacks them.

**Suggested fix:** Add `extend_<label>` to AC 25's method list.

---

## requirements-3

**Section:** "Rust source files" — `src/cst_poc.rs` or similar

**What's wrong:** This is implementation direction (file naming, file structure). Requirements should specify the observable surface — that the types are accessible from `fltk._native` — not where the Rust source lives or how modules are organized internally.

**Why:** "Requirements, not design" principle. The exploration already suggests `src/cst_poc.rs` and registration in `lib.rs`; restating it in requirements over-constrains the implementer.

**Consequence:** Minimal — the "or similar" hedge makes it non-binding. But it sets an expectation that could cause unnecessary review friction if the implementer chooses a different layout.

**Suggested fix:** Remove the "Rust source files" subsection from "User-Visible Surface." It's not user-visible.

---

## requirements-4

**Section:** "Constraints" — `children_<label>()` return type: "Returns a Python list (not a generator/iterator)"

**What's wrong:** This is a design decision, not a requirement. The observable contract is: "the return value supports iteration and `list()` wrapping." Whether the implementation returns a list or an iterator is invisible to callers, since all call sites either iterate or call `list()`. Constraining the return type to list precludes a lazy approach if the implementer finds one convenient, and it contradicts the Python CST's behavior (which returns a generator).

**Why:** Exploration section 6 acknowledges this is a simplification. The requirements doc should state the behavioral contract (iterable, supports `list()`, supports `for x in ...`), not the implementation choice.

**Consequence:** Low — the implementer probably would choose a list anyway. But it's over-specification.

**Suggested fix:** Change to: "Returns an iterable that supports `for x in ...` and `list(...)`. Returning a list is acceptable; returning an iterator/generator is also acceptable."

---

## requirements-5

**Section:** "Constraints" — Error message format: `"Expected one name child but have 0"`

**What's wrong:** The Python CST's actual error messages (from `gsm2tree.py:224-232`) are: `f"Expected one {label} child but have {n}"` and `f"Expected at most one {label} child but have {n}"`. The requirements doc mandates this same format. This is fine for the per-label methods. But for the generic `child()`, the requirements say: `"Expected one child but have {n}"` — and the Python CST's generic `child()` (`gsm2tree.py:175-178`) has a different message format: `f"Expected one child but have {n}"` (no label name). These are consistent, so no actual error. This finding is retracted — no issue.

**Consequence:** None.

---

## requirements-6

**Section:** Overall — `__hash__` on label enums vs. `#[pyclass(eq, hash, frozen)]`

**What's wrong:** The requirements specify label enums as `#[pyclass(eq, hash, frozen)]` (in-scope section) AND specify `__hash__` must work (AC 5). This is consistent. However, the requirements also say `__eq__` between unrelated types should return `NotImplemented` or `False` (label enum semantics, inter-class discrimination). PyO3's derived `#[pyclass(eq)]` uses Rust's `PartialEq` which only compares same-type variants. Cross-type comparison behavior depends on PyO3's dispatch — it may return `NotImplemented` automatically for different types, which is correct. The requirements correctly flag `OQ-none-label-eq` for `None` comparison. But the requirements do NOT explicitly state what `Identifier.Label.NAME == Items.Label.ITEM` should return — they say `!=` is `True` (AC 4), but not whether `__eq__` returns `False` vs. `NotImplemented`.

**Consequence:** Practically none — `NotImplemented` and `False` both make `!=` return `True`. But if the implementer writes a custom `__richcmp__` (per OQ-none-label-eq), they need to know the expected behavior for cross-type `__eq__`.

**Suggested fix:** Add a note: "Cross-type `__eq__` (e.g., `Identifier.Label.NAME == Items.Label.ITEM`) may return `False` or `NotImplemented`; both are acceptable as long as `!=` returns `True`."

---

## requirements-7

**Section:** "Acceptance Criteria" 6 — `id(node.children) == id(node.children)`

**What's wrong:** `id()` identity comparison is fragile in CPython and may not hold in all cases. The real requirement is mutation visibility (AC 7 and AC 8), not object identity. In CPython, `id(x) == id(x)` where `x` is a property getter can return `True` even for copies if the first reference is garbage collected before the second `id()` call (same memory reused). Conversely, if `#[pyo3(get)]` on `Py<PyList>` returns the same Python object (which it should), `id()` equality holds. But testing with `id()` in a single expression like `id(node.children) == id(node.children)` is unreliable because the first `node.children` result may be GC'd before the second call.

**Why:** The correct test is: `a = node.children; b = node.children; assert a is b` — holding both references prevents GC.

**Consequence:** The test might pass or fail non-deterministically depending on GC timing, giving a false sense of validation or false failures.

**Suggested fix:** Change AC 6 to: "Holding two references: `a = node.children; b = node.children; assert a is b` — same object on repeated access."

---

## requirements-8

**Section:** Overall — missing `child()` return for the generic `child()` when called on `Items` with heterogeneous labels

**What's wrong:** The generic `child()` method is specified to return `node.children[0]` as a tuple when there's exactly one child. AC 19 tests this. But the requirements never specify what happens when `child()` is called and there are zero children. The Python CST's `child()` raises `ValueError` (per `gsm2tree.py:175-178`). The requirements say "With zero or more than one, raises `ValueError`" in AC 19 — this is correct. No issue.

**Consequence:** None. Retracted.

---

## requirements-9

**Section:** Overall — big picture sanity

**What's wrong:** Nothing fundamental. This is a well-scoped PoC that validates exactly the two assumptions identified in the phase plan (nested-enum workaround and `Py<PyList>` mutation semantics). The acceptance criteria are thorough and align with the phase plan's done-when criteria plus the exploration's minimum assertions list. The requirements correctly exclude production wiring, which is Phase 3+ territory.

**Consequence:** N/A — affirmative finding.

---

## requirements-10

**Section:** "Acceptance Criteria" 16-18 — generic `append`/`extend` with label parameter

**What's wrong:** AC 16 says `node.append(child)` stores `(None, child)`. AC 17 says `node.append(child, label=Identifier.Label.NAME)` stores `(Identifier.Label.NAME, child)`. But the Python CST's `append` signature is `def append(self, child, label=None)` — positional `child` first, keyword `label` second. The requirements correctly mirror this. However, the requirements don't specify whether `label` should be keyword-only or positional. In PyO3 `#[pymethods]`, parameter handling matters: `#[pyo3(signature = (child, label=None))]` makes both positional, while `#[pyo3(signature = (child, *, label=None))]` makes `label` keyword-only.

**Why:** The Python CST allows both `node.append(child, some_label)` (positional) and `node.append(child, label=some_label)` (keyword). The parser code uses keyword: `result.append(child=..., label=...)` in some generated contexts. The requirements should specify positional-or-keyword to avoid breaking callers.

**Consequence:** If the implementer makes `label` keyword-only but some caller passes it positionally (or vice versa), the PoC passes its tests but Phase 3+ integration breaks.

**Suggested fix:** Add: "`append(child, label=None)` — both parameters are positional-or-keyword (not keyword-only)."

---

## requirements-11

**Section:** "Acceptance Criteria" — missing test for `None`-label filtering

**What's wrong:** No AC verifies that `children_name()` correctly skips children with `label=None`. This is the core filtering behavior. AC 10 tests `append_name` + `child_name` (which implicitly tests filtering when there's only one child), but no AC adds a mix of labeled and unlabeled children and then verifies `children_name()` returns only the labeled ones. This is exactly the scenario flagged in `OQ-none-label-eq` — whether `None == Identifier_Label::NAME` evaluates to `False` without panicking.

**Why:** Exploration section 13, question 5: "When `children` contains `(None, child)` tuples... the filter must evaluate to `False`." This is one of the two PoC goals (label discrimination), yet no AC explicitly tests it.

**Consequence:** The PoC could pass all ACs while the `None`-label filtering is broken — which would only surface in Phase 3+ when the parser uses generic `append` alongside labeled `append_name`, and consumers call `children_name()`.

**Suggested fix:** Add an AC: "After `node.append(unlabeled_child)` followed by `node.append_name(labeled_child)`, `list(node.children_name())` returns `[labeled_child]` only (the unlabeled child is excluded)."

---

## requirements-12

**Section:** "Open Questions" — `OQ-extend-iterable`

**What's wrong:** This is flagged as an open question, but the requirements already constrain it via the system-behavior section: `extend(children, label=None)` says "for each `child` in the iterable." This implies any iterable. The OQ recommends accepting `&Bound<'_, PyAny>` and calling `.iter()`. That's an implementation detail in a requirements doc. The OQ should either be resolved (state the requirement: "must accept any Python iterable") or removed.

**Consequence:** Minimal — the implementer will likely accept any iterable anyway. But leaving an open question about something already decided in the behavioral spec creates confusion.

**Suggested fix:** Resolve OQ-extend-iterable: "The `extend` and `extend_<label>` methods accept any Python iterable, not only lists."
