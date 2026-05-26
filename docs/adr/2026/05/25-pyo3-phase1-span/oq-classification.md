# OQ Classification: Phase 1 Span Open Questions

Concise. Precise. No padding. Audience: smart human/LLM.

---

## OQ1: Single type vs. two types for source-bearing spans

**Classification: REQUIREMENTS**

This is a product/behavior decision: it determines whether user-facing Python code sees one type (`Span`) that optionally carries source, or two types (`Span` + `SourceSpan`). The choice has direct consequences for:

- Whether `isinstance(x, Span)` in the generated unparser dispatch (`gsm2unparser.py:983`) covers source-bearing spans without any change to generated code.
- Whether downstream user code can hold a single type and call `.text()` on it, or must track which of two types it has.
- The "always access source text of a CST node" user requirement (request.md verbatim): "you cannot even generate good compiler errors without access to the TerminalSource... we should expose... a *better* Python API, one which allows you to always access the source text of a CST node." The word "always" is the user's — it implies the method is unconditionally present on whatever type you hold, which points at Option A but does not foreclose Option B (where you only hold `SourceSpan` in code paths that have source). Only the user can confirm which mental model they want.

User input needed: Confirm Option A (extend `Span`) or Option B (separate `SourceSpan`). The requirements doc's proposal of Option A is a reasonable default, but "unless user redirects" explicitly tags it as unconfirmed. Cannot defer because the choice affects the PyO3 struct signature, class registration, and `isinstance` contract — all of which are Phase 1 design decisions that depend on this answer.

---

## OQ2: Source reference type — `Arc<str>` vs. `Arc<TerminalSource>` vs. `Py<PyAny>`

**Classification: DESIGN**

This is a how-to-build decision. It does not affect the observable Python API surface for Phase 1: `span.text()` returns `str | None` regardless of whether the backing store is `Arc<str>` or a richer Rust type. The choice affects internal Rust struct layout and future refactor cost, which are design concerns.

Deferrable because:
- Phase 1's conditional better API (OQ5) is not yet confirmed in scope.
- If OQ5 resolves to "defer API," this question has no Phase 1 impact at all.
- If OQ5 resolves to "ship now," the designer can choose `Arc<str>` as the minimum viable implementation. Upgrading from `Arc<str>` to `Arc<TerminalSource>` later is an internal Rust change — Python-visible behavior is unchanged, and the struct layout change does not break any compiled Python extension (maturin rebuild required, but no source changes anywhere else).
- The exploration doc (section 5) correctly identifies this as a future phase concern once TerminalSource is Rust-backed.

---

## OQ3: Deferred implementation vs. full implementation of better API in Phase 1

**Classification: REQUIREMENTS**

This is a scope decision: whether Phase 1 ships user-visible `text()` / `with_source()` or only lays out struct fields internally. Scope decisions are product-owner calls, not implementer calls.

User input needed: Confirm whether Phase 1 should expose `text()` / `with_source()` (shipping value now, incurring early API commitment) or defer the API to the TerminalSource phase (shipping only struct layout). The requirements doc flags this explicitly as "User: confirm or redirect" (OQ5, which is the same decision restated — see OQ5 classification below). The distinction from OQ5 is minor: OQ3 frames it as implementation depth; OQ5 frames it as phase scope. Both collapse to the same user decision.

Cannot defer because once Phase 1 is built and shipped without the API, adding it later requires a new phase and a new backward-compatibility surface. Conversely, shipping it now creates obligations that may not fit the TerminalSource design finalized in a later phase.

---

## OQ4: Should `UnknownSpan` be identity-comparable (`is` singleton)?

**Classification: EXPLORABLE**

Answered by code search.

Evidence:
- `grep -rn "UnknownSpan is\b\|is UnknownSpan\b"` across the entire repo finds **zero** production code using `is` identity checks on `UnknownSpan`. All matches are in the ADR docs themselves (requirements.md:75, dispositions-requirements.md:34, judge-verdict-requirements.md:37-38).
- `terminalsrc.py:15`: `UnknownSpan: Final = Span(-1, -1)` — a module-level constant; Python's module import caches mean `UnknownSpan is UnknownSpan` is trivially true in current Python code by module identity, but no code relies on this property.
- The requirements doc (line 75) already resolved this: "singleton preferred, but not a hard requirement." Acceptance criteria (lines 86-95) require only value equality (`UnknownSpan == Span(-1, -1)`), not identity.

**Answer:** No `is`-comparison code exists. Singleton is a nice-to-have, not a constraint. This question was already answered by the requirements review process (dispositions-requirements.md finding requirements-6); it is not an open question.

---

## OQ5: Should Phase 1 ship the "better API" or only struct layout?

**Classification: REQUIREMENTS**

Same decision as OQ3 (scope of Phase 1), restated from a phase-planning angle. It is a product-owner call because:

- The phase plan (`phase-plan.md`) explicitly limits Phase 1 to `Span` replacement — no TerminalSource, no `text()` API. Expanding scope requires owner sign-off.
- Shipping `text()` / `with_source()` in Phase 1 creates a backward-compatibility obligation on the Python API before the Phase 2 TerminalSource Rust design is finalized. If TerminalSource ends up needing a different source-reference architecture, the Phase 1 API may need to change — which would be a breaking change.
- The requirements doc explicitly requests user confirmation: "User: confirm or redirect."

User input needed: Yes or no — does Phase 1 expose `text()` and `with_source()` to Python callers?

Note: OQ5 subsumes OQ3. Both are the same REQUIREMENTS question asked twice from different angles. Resolving one resolves the other.
